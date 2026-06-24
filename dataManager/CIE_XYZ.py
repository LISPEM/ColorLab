# -*- coding: utf-8 -*-
"""CIE 1931 colorimetry: tristimulus, Bradford chromatic adaptation, sRGB.

Designed so each spectrum costs roughly one (81,) dot product plus a 3x3
matmul. All constants - color matching functions, illuminant tables, white
points, Bradford matrices - load once at import time; per-call work is just
the trimmed transmission vector and a few cached matrix lookups.
"""

import functools
import pandas as pd
import numpy as np


# ----------------------------------------------------------------------------
# Constants (loaded once per process).
# ----------------------------------------------------------------------------

# CIE 1931 2-degree standard observer color matching functions, sampled at
# 5nm from 380nm to 780nm (length 81). Values from CIE-1931 standard tables.
X_BAR = np.array([
    0.001368, 0.002236, 0.004243, 0.00765, 0.01431, 0.02319, 0.04351, 0.07763,
    0.13438, 0.21477, 0.2839, 0.3285, 0.34828, 0.34806, 0.3362, 0.3187, 0.2908,
    0.2511, 0.19536, 0.1421, 0.09564, 0.05795, 0.03201, 0.0147, 0.0049, 0.0024,
    0.0093, 0.0291, 0.06327, 0.1096, 0.1655, 0.22575, 0.2904, 0.3597, 0.43345,
    0.51205, 0.5945, 0.6784, 0.7621, 0.8425, 0.9163, 0.9786, 1.0263, 1.0567,
    1.0622, 1.0456, 1.0026, 0.9384, 0.85445, 0.7514, 0.6424, 0.5419, 0.4479,
    0.3608, 0.2835, 0.2187, 0.1649, 0.1212, 0.0874, 0.0636, 0.04677, 0.0329,
    0.0227, 0.01584, 0.011359, 0.008111, 0.00579, 0.004109, 0.002899, 0.002049,
    0.00144, 0.001, 0.00069, 0.000476, 0.000332, 0.000235, 0.000166, 0.000117,
    8.3e-05, 5.9e-05, 4.2e-05,
], dtype=np.float64)

Y_BAR = np.array([
    3.9e-05, 6.4e-05, 0.00012, 0.000217, 0.000396, 0.00064, 0.00121, 0.00218,
    0.004, 0.0073, 0.0116, 0.01684, 0.023, 0.0298, 0.038, 0.048, 0.06, 0.0739,
    0.09098, 0.1126, 0.13902, 0.1693, 0.20802, 0.2586, 0.323, 0.4073, 0.503,
    0.6082, 0.71, 0.7932, 0.862, 0.91485, 0.954, 0.9803, 0.99495, 1, 0.995,
    0.9786, 0.952, 0.9154, 0.87, 0.8163, 0.757, 0.6949, 0.631, 0.5668, 0.503,
    0.4412, 0.381, 0.321, 0.265, 0.217, 0.175, 0.1382, 0.107, 0.0816, 0.061,
    0.04458, 0.032, 0.0232, 0.017, 0.01192, 0.00821, 0.005723, 0.004102,
    0.002929, 0.002091, 0.001484, 0.001047, 0.00074, 0.00052, 0.000361,
    0.000249, 0.000172, 0.00012, 8.5e-05, 6e-05, 4.2e-05, 3e-05, 2.1e-05,
    1.5e-05,
], dtype=np.float64)

Z_BAR = np.array([
    0.00645, 0.01055, 0.02005, 0.03621, 0.06785, 0.1102, 0.2074, 0.3713,
    0.6456, 1.03905, 1.3856, 1.62296, 1.74706, 1.7826, 1.77211, 1.7441, 1.6692,
    1.5281, 1.28764, 1.0419, 0.81295, 0.6162, 0.46518, 0.3533, 0.272, 0.2123,
    0.1582, 0.1117, 0.07825, 0.05725, 0.04216, 0.02984, 0.0203, 0.0134,
    0.00875, 0.00575, 0.0039, 0.00275, 0.0021, 0.0018, 0.00165, 0.0014, 0.0011,
    0.001, 0.0008, 0.0006, 0.00034, 0.00024, 0.00019, 0.0001, 5e-05, 3e-05,
    2e-05, 1e-05, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0,
], dtype=np.float64)

# Bradford chromatic adaptation transform (cone response basis).
_MA = np.array([
    [0.8951000,  0.2664000, -0.1614000],
    [-0.7502000, 1.7135000,  0.0367000],
    [0.0389000, -0.0685000,  1.0296000],
], dtype=np.float64)
_MA_INV = np.linalg.inv(_MA)

_D65_WHITE = np.array([0.95047, 1.0000, 1.08883], dtype=np.float64)
_D65_CR = _MA @ _D65_WHITE  # cone response for D65, computed once.

# sRGB conversion matrix (D65 white point).
_M_SRGB = np.array([
    [3.2410, -1.5374, -0.4986],
    [-0.9692, 1.8760,  0.0416],
    [0.0556, -0.2040,  1.0570],
], dtype=np.float64)

# Loaded once. Both files are bundled as PyInstaller datas and the entry
# point chdir's to the exe folder before this module is imported.
_WHITE_POINTS = pd.read_csv("dataManager/white_point.csv")
_ILLUM_DF = pd.read_csv("dataManager/illuminants.csv")

D65_NAME = "Standard Illuminant D65"


# ----------------------------------------------------------------------------
# Cached per-illuminant lookups.
# ----------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _trimmed_illum(spec_illum):
    """Illuminant power, trimmed to 380-780nm at 5nm step (length 81)."""
    wl = _ILLUM_DF["Wavelength"].to_numpy()
    i380 = int(np.where(wl == 380)[0][0])
    i780 = int(np.where(wl == 780)[0][0])
    # Illuminant table is at 5nm step already (matches the bar arrays).
    return _ILLUM_DF[spec_illum].to_numpy()[i380:i780 + 1]


@functools.lru_cache(maxsize=None)
def _bradford_matrix(spec_illum):
    """3x3 chromatic-adaptation matrix from spec_illum to D65.

    Returns None when spec_illum is already D65 (no transform needed).
    """
    if spec_illum == D65_NAME:
        return None
    src_white = np.array([
        _WHITE_POINTS[spec_illum][0],
        _WHITE_POINTS[spec_illum][1],
        _WHITE_POINTS[spec_illum][2],
    ], dtype=np.float64)
    src_cr = _MA @ src_white
    diag = np.diag(_D65_CR / src_cr)
    return _MA_INV @ diag @ _MA


# ----------------------------------------------------------------------------
# Vectorized inner kernels.
# ----------------------------------------------------------------------------

def _gamma_srgb(c):
    """sRGB gamma curve, vectorized."""
    return np.where(c < 0.0031308, 12.92 * c, 1.055 * np.power(c, 0.41666) - 0.055)


def xyz_to_rgb255(XYZ):
    """Convert (..., 3) XYZ -> (..., 3) sRGB rounded uint16 in [0, 255].

    Output dtype is float to match the existing return type from xyz2rbg
    (which used `round(R * 255, 0)` returning a Python float). Caller
    casts as needed.
    """
    XYZ = np.atleast_2d(np.asarray(XYZ, dtype=np.float64))
    rgb_lin = XYZ @ _M_SRGB.T
    rgb_lin = np.clip(rgb_lin, 0.0, 1.0)
    rgb = _gamma_srgb(rgb_lin)
    return np.round(rgb * 255.0)


def tristimulus_batch(T_matrix, spec_illum):
    """Compute D65-adapted CIE XYZ for one or many transmission spectra.

    Parameters
    ----------
    T_matrix : ndarray
        Shape (81,) for a single spectrum or (N, 81) for N spectra. Values
        in [0, 1] (fraction transmittance).
    spec_illum : str
        Illuminant column name (matches `dataManager/illuminants.csv`).

    Returns
    -------
    XYZ : ndarray
        Shape (3,) or (N, 3), in D65 reference white.
    """
    T = np.asarray(T_matrix, dtype=np.float64)
    illum_arr = _trimmed_illum(spec_illum)
    wx = X_BAR * illum_arr
    wy = Y_BAR * illum_arr
    wz = Z_BAR * illum_arr
    K = 1.0 / wy.sum()  # normalizing constant

    if T.ndim == 1:
        XYZ = np.array([np.dot(T, wx), np.dot(T, wy), np.dot(T, wz)]) * K
    else:
        weights = np.column_stack([wx, wy, wz])  # (81, 3)
        XYZ = (T @ weights) * K  # (N, 3)

    M = _bradford_matrix(spec_illum)
    if M is not None:
        XYZ = XYZ @ M.T
    return XYZ


# ----------------------------------------------------------------------------
# Public API.
# ----------------------------------------------------------------------------

def data_cleanup(loaded_data):
    loaded_data["Wavelength"] = loaded_data["Wavelength"].astype(int)
    return loaded_data.drop_duplicates(subset="Wavelength").reset_index()


def _trim_to_5nm(df, datatype):
    """Convert datatype column -> Transmission, trim to 380-780nm at 5nm step.

    Returns the (81,) numpy array of transmission values.
    """
    if datatype == 0:
        sub = df[["Wavelength", "Absorbance"]].copy()
        sub["Absorbance"] = 10 ** (-sub["Absorbance"])
        sub.rename(columns={"Absorbance": "Transmission"}, inplace=True)
    elif datatype == 1:
        sub = df[["Wavelength", "Transmission"]].copy()
    elif datatype == 2:
        sub = df[["Wavelength", "FT"]].copy()
        sub["FT"] = (1 + sub["FT"]) * 100
        sub.rename(columns={"FT": "Transmission"}, inplace=True)
    else:
        raise ValueError(f"Unknown datatype {datatype!r}")

    sub = data_cleanup(sub)
    wavelength = sub["Wavelength"].to_numpy()

    data_step = abs(int(wavelength[0]) - int(wavelength[1]))
    illum_step = 5  # bar arrays are at 5nm; illuminant table matches
    step = max(1, illum_step // data_step)

    i380 = int(np.where(wavelength == 380)[0][0])
    i780 = int(np.where(wavelength == 780)[0][0])
    T = sub["Transmission"].to_numpy()[i380:i780 + 1:step]
    return T


def CIElab(spec_illum, datatype, df, calc_rgb=True, **_legacy_kwargs):
    """Single-spectrum CIE pipeline. Returns (cx, cy, 0.0, r, g, b).

    `**_legacy_kwargs` swallows the historical (illum, x_bar, y_bar, z_bar)
    positional parameters if any caller still passes them - they are now
    module-level constants.
    """
    T = _trim_to_5nm(df, datatype)
    XYZ = tristimulus_batch(T, spec_illum)
    CIE_X, CIE_Y, CIE_Z = float(XYZ[0]), float(XYZ[1]), float(XYZ[2])

    if calc_rgb:
        rgb = xyz_to_rgb255(XYZ).ravel()
        r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
    else:
        r = g = b = 0.0

    denom = CIE_X + CIE_Y + CIE_Z
    if denom:
        cx = CIE_X / denom
        cy = CIE_Y / denom
    else:
        cx = 0.0
        cy = 0.0

    return cx, cy, 0.0, r, g, b


def CIElab_batch(spec_illum, datatype, wavelength_arr, T_matrix, calc_rgb=True):
    """Batched CIE pipeline.

    Parameters
    ----------
    spec_illum : str
    datatype : int
        0 = Absorbance, 1 = Transmission, 2 = FT (matches the GUI radio).
    wavelength_arr : ndarray, shape (M,)
        Wavelength axis shared by all input spectra.
    T_matrix : ndarray, shape (N, M)
        Spectrum values in their native datatype (per `datatype`).

    Returns
    -------
    lab_values : ndarray, shape (N, 6)
        Columns: [cx, cy, 0, r, g, b].
    """
    wavelength_arr = np.asarray(wavelength_arr, dtype=np.float64)
    T_matrix = np.asarray(T_matrix, dtype=np.float64)
    if T_matrix.ndim != 2:
        raise ValueError("T_matrix must be 2D (N, M)")

    if datatype == 0:
        T = 10 ** (-T_matrix)
    elif datatype == 1:
        T = T_matrix
    elif datatype == 2:
        T = (1 + T_matrix) * 100
    else:
        raise ValueError(f"Unknown datatype {datatype!r}")

    # Trim to 380-780 at 5nm step.
    wl_int = wavelength_arr.astype(int)
    data_step = abs(int(wl_int[0]) - int(wl_int[1]))
    illum_step = 5
    step = max(1, illum_step // data_step)
    i380 = int(np.where(wl_int == 380)[0][0])
    i780 = int(np.where(wl_int == 780)[0][0])
    T_trimmed = T[:, i380:i780 + 1:step]

    XYZ = tristimulus_batch(T_trimmed, spec_illum)  # (N, 3)

    n = XYZ.shape[0]
    out = np.zeros((n, 6), dtype=np.float64)
    denom = XYZ.sum(axis=1)
    nonzero = denom > 0
    out[nonzero, 0] = XYZ[nonzero, 0] / denom[nonzero]
    out[nonzero, 1] = XYZ[nonzero, 1] / denom[nonzero]

    if calc_rgb:
        rgb = xyz_to_rgb255(XYZ)  # (N, 3)
        out[:, 3:] = rgb

    return out
