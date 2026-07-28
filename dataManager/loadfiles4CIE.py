"""Pure processing functions for ColorLab.

Refactored from the original PyQt5-coupled RGBImage class into callable
functions so any UI (customtkinter, CLI, notebook) can drive the pipeline.
All I/O, progress reporting, and error handling is pushed to the caller
via callbacks — this module never calls sys.exit.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

from dataManager.CIE_XYZ import CIElab


_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_ILLUMINANTS_PATH = os.path.join(_MODULE_DIR, "illuminants.csv")

DATATYPE_ABSORBANCE = 0
DATATYPE_TRANSMISSION = 1
DATATYPE_AIPS = 2

DATATYPE_LABELS = {
    "Absorbance": DATATYPE_ABSORBANCE,
    "Transmission": DATATYPE_TRANSMISSION,
    "AIPS": DATATYPE_AIPS,
}

X_BAR = [
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
]

Y_BAR = [
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
]

Z_BAR = [
    0.00645, 0.01055, 0.02005, 0.03621, 0.06785, 0.1102, 0.2074, 0.3713, 0.6456,
    1.03905, 1.3856, 1.62296, 1.74706, 1.7826, 1.77211, 1.7441, 1.6692, 1.5281,
    1.28764, 1.0419, 0.81295, 0.6162, 0.46518, 0.3533, 0.272, 0.2123, 0.1582,
    0.1117, 0.07825, 0.05725, 0.04216, 0.02984, 0.0203, 0.0134, 0.00875, 0.00575,
    0.0039, 0.00275, 0.0021, 0.0018, 0.00165, 0.0014, 0.0011, 0.001, 0.0008,
    0.0006, 0.00034, 0.00024, 0.00019, 0.0001, 5e-05, 3e-05, 2e-05, 1e-05, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]


class FileReadError(Exception):
    """Raised when a single input file cannot be parsed."""

    def __init__(self, filename: str, reason: str) -> None:
        super().__init__(f"{filename}: {reason}")
        self.filename = filename
        self.reason = reason


class NoValidDataError(Exception):
    """Raised when a batch produces zero usable files."""


@dataclass
class ProcessingParams:
    filepaths: list[str]
    datatype: int
    spec_illum: str
    title: str
    aspect: float
    only_first: bool = False


def load_illuminants_csv() -> pd.DataFrame:
    """Load the illuminant spectra table from the package directory."""
    return pd.read_csv(_ILLUMINANTS_PATH)


def list_illuminant_names() -> list[str]:
    """Return the column names in illuminants.csv excluding 'Wavelength'."""
    cols = list(load_illuminants_csv().columns)
    return [c for c in cols if c != "Wavelength"]


def _read_spectrum_file(full_path: str) -> pd.DataFrame:
    filename = os.path.basename(full_path)
    try:
        if filename.endswith(".csv"):
            return pd.read_csv(full_path, sep=None, engine="python")
        if filename.endswith((".xls", ".xlsx")):
            return pd.read_excel(full_path)
        return pd.read_table(full_path, sep=None, engine="python")
    except Exception as exc:
        raise FileReadError(filename, f"could not parse ({exc.__class__.__name__})") from exc


def iter_spectra_files(folder: str) -> Iterator[tuple[str, pd.DataFrame]]:
    """Yield (filename, dataframe) for each parseable file in folder.

    Raises FileReadError for individual unreadable files — the caller decides
    whether to skip or abort.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)
    entries = sorted(os.listdir(folder))
    for name in entries:
        full = os.path.join(folder, name)
        if os.path.isdir(full):
            continue
        df = _read_spectrum_file(folder, name)
        if len(df) == 0:
            raise FileReadError(name, "file is empty")
        yield name, df


def _extract_timestamp(filename: str) -> Optional[int]:
    """Parse trailing `_<seconds>.ext` from a filename. Returns seconds or None."""
    stem = filename.rsplit(".", 1)[0]
    tail = stem.rsplit("_", 1)[-1]
    digits = "".join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename common variations of column names to the expected standard."""
    col_map = {}
    for col in df.columns:
        scol = str(col).lower().strip()
        if scol in ["wavelength", "wavelength (nm)", "nm", "w"]:
            col_map[col] = "Wavelength"
        elif scol in ["absorbance", "abs", "a"]:
            col_map[col] = "Absorbance"
        elif scol in ["transmission", "%t", "t"]:
            col_map[col] = "Transmission"
    return df.rename(columns=col_map)


_TARGET_COLUMN_BY_DATATYPE = {
    DATATYPE_ABSORBANCE: "Absorbance",
    DATATYPE_TRANSMISSION: "Transmission",
    DATATYPE_AIPS: "FT",
}


def _iter_spectra_from_frame(
    filename: str, df: pd.DataFrame, datatype: int
) -> Iterator[tuple[str, pd.DataFrame]]:
    """Yield one (label, single-spectrum DataFrame) per spectrum in a file.

    Single-spectrum files (Wavelength + the expected data column) yield once
    with the original frame. Wide multi-spectrum sheets (Wavelength + multiple
    numeric columns) yield once per numeric column, with each frame reshaped
    to look like a standard single-spectrum file so CIElab stays unchanged.
    """
    df = normalize_columns(df)
    if "Wavelength" not in df.columns:
        raise FileReadError(filename, "no recognizable wavelength column")

    target = _TARGET_COLUMN_BY_DATATYPE.get(datatype, "Transmission")

    if target in df.columns:
        yield filename, df
        return

    numeric_cols = [
        c for c in df.columns
        if c != "Wavelength" and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not numeric_cols:
        raise FileReadError(
            filename, f"no '{target}' column or numeric data columns found"
        )

    for col in numeric_cols:
        sub = df[["Wavelength", col]].rename(columns={col: target})
        yield f"{filename} :: {col}", sub


def compute_rgb_row(
    spec_illum: str,
    illum_df: pd.DataFrame,
    datatype: int,
    uvvis_df: pd.DataFrame,
) -> tuple[float, float, float]:
    """Run a single spectrum through the CIE pipeline and return (R, G, B)."""
    uvvis_df = normalize_columns(uvvis_df)
    _, _, _, r, g, b = CIElab(
        spec_illum, illum_df, datatype, uvvis_df, X_BAR, Y_BAR, Z_BAR, True
    )
    return r, g, b


def build_color_matrix(
    rgb_rows: np.ndarray, timestamps: list[Optional[int]]
) -> tuple[np.ndarray, np.ndarray, str]:
    """Assemble the time-series color matrix.

    rgb_rows: (N, 3) array of RGB values.
    timestamps: list of integer seconds (one per row) or None entries.
    Returns (colormat, delta, units).
    """
    n = len(rgb_rows)
    if n == 0:
        raise NoValidDataError("no files produced valid color data")

    # Single file: emit a tiny 1x1 swatch.
    if n == 1:
        colormat = np.zeros((1, 1, 3), dtype=np.uint16)
        colormat[0, 0] = rgb_rows[0]
        return colormat, np.array([[0]]), "Minutes"

    valid_ts = [t for t in timestamps if t is not None]
    if len(valid_ts) < 2:
        # Fall back to uniform-spaced strips if filenames don't carry timestamps.
        colormat = np.zeros((n, n, 3), dtype=np.uint8)
        for i in range(n):
            colormat[:, i] = rgb_rows[i]
        return colormat, np.arange(n).reshape(1, -1), "Index"

    delta = np.zeros((1, n))
    first_t = valid_ts[0]
    use_hours = any(t - first_t > 3660 for t in valid_ts)
    seconds_convert = 3600 if use_hours else 60
    units = "Hours" if use_hours else "Minutes"
    for i, t in enumerate(timestamps):
        if t is None:
            delta[0, i] = delta[0, i - 1] if i > 0 else 0
        else:
            delta[0, i] = (t - first_t) / seconds_convert

    if seconds_convert == 3600:
        delta_for_strips = delta * 60
    else:
        delta_for_strips = delta

    delta_delta = np.around(np.diff(delta_for_strips))
    # Guard against zero/negative widths (out-of-order or duplicate timestamps).
    delta_delta = np.clip(delta_delta, 1, None)

    temp_dim = int(np.sum(delta_delta))
    if temp_dim < 1:
        temp_dim = n

    colormat = np.zeros((temp_dim, temp_dim, 3), dtype=np.uint8)
    curr_idx = 0
    first = True
    for i in range(n - 1):
        for _ in range(int(delta_delta[0, i])):
            if first:
                colormat[:, curr_idx] = rgb_rows[i]
                first = False
            else:
                curr_idx += 1
                if curr_idx >= temp_dim:
                    break
                colormat[:, curr_idx] = rgb_rows[i]
        if curr_idx >= temp_dim - 1:
            break

    colormat = colormat[: curr_idx + 1, : curr_idx + 1, :]
    return colormat, delta, units


_INVALID_TITLE_CHARS = set(r"<>/{}[]~`^$&#@!;,:")


def sanitize_title(title: str) -> str:
    """Strip filesystem-unfriendly characters from a user-provided title."""
    return "".join(ch for ch in title if ch not in _INVALID_TITLE_CHARS).strip()


def render_figure(
    colormat: np.ndarray,
    delta: np.ndarray,
    units: str,
    title: str,
    aspect: float,
) -> Figure:
    """Render a matplotlib Figure from a color matrix. Does NOT save to disk."""
    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.add_subplot(1, 1, 1)

    safe_title = sanitize_title(title) or "ColorLab"

    if len(colormat) > 1 and delta.size > 1:
        max_delta = np.max(delta)
        if units == "Hours":
            extent = [delta[0, 0], max_delta / 60, delta[0, 0], max_delta / 60]
        else:
            extent = [delta[0, 0], max_delta, delta[0, 0], max_delta]
        ax.imshow(colormat, extent=extent, aspect=aspect)
        ax.set_xlabel(units)
        ax.axes.get_yaxis().set_visible(False)
    else:
        ax.imshow(colormat, aspect=aspect)
        ax.axes.get_xaxis().set_visible(False)
        ax.axes.get_yaxis().set_visible(False)

    ax.set_title(safe_title)
    fig.tight_layout()
    return fig


ProgressCallback = Callable[[int, int, str], None]
FileErrorCallback = Callable[[str, str], None]
CancelCallback = Callable[[], bool]


def process_batch(
    params: ProcessingParams,
    on_progress: Optional[ProgressCallback] = None,
    on_file_error: Optional[FileErrorCallback] = None,
    should_cancel: Optional[CancelCallback] = None,
) -> Figure:
    """Run the full pipeline and return a rendered Figure.

    Callbacks:
        on_progress(i, total, filename) — called after each file succeeds.
        on_file_error(filename, reason) — called for files skipped due to errors.
        should_cancel() -> bool — polled between files; if True, aborts with
            whatever rows have been collected so far (if any).
    """
    illum_df = load_illuminants_csv()

    filenames = params.filepaths
    if params.only_first and filenames:
        filenames = filenames[:1]
    total = len(filenames)
    if total == 0:
        raise NoValidDataError("no files selected")

    rgb_rows: list[tuple[float, float, float]] = []
    timestamps: list[Optional[int]] = []

    for idx, path in enumerate(filenames):
        name = os.path.basename(path)
        if should_cancel and should_cancel():
            break
        try:
            df = _read_spectrum_file(path)
            if len(df) == 0:
                raise FileReadError(name, "file is empty")
            spectra = list(_iter_spectra_from_frame(name, df, params.datatype))
        except FileReadError as exc:
            if on_file_error:
                on_file_error(exc.filename, exc.reason)
            continue
        except Exception as exc:  # pragma: no cover - defensive
            if on_file_error:
                on_file_error(name, f"{exc.__class__.__name__}: {exc}")
            continue

        # Single-spectrum files keep the filename timestamp; wide multi-spectrum
        # files share no real time axis, so they fall through to equal-width
        # strips in build_color_matrix.
        file_ts = _extract_timestamp(name) if len(spectra) == 1 else None

        for label, sub_df in spectra:
            try:
                rgb = compute_rgb_row(
                    params.spec_illum, illum_df, params.datatype, sub_df
                )
            except FileReadError as exc:
                if on_file_error:
                    on_file_error(exc.filename, exc.reason)
                continue
            except Exception as exc:  # pragma: no cover - defensive
                if on_file_error:
                    on_file_error(label, f"{exc.__class__.__name__}: {exc}")
                continue

            rgb_rows.append(rgb)
            timestamps.append(file_ts)
            if on_progress:
                on_progress(idx + 1, total, label)

    if not rgb_rows:
        raise NoValidDataError("every file in the folder failed to process")

    rgb_array = np.array(rgb_rows)
    colormat, delta, units = build_color_matrix(rgb_array, timestamps)
    return render_figure(colormat, delta, units, params.title, params.aspect)
