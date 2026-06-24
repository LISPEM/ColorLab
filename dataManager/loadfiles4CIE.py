# -*- coding: utf-8 -*-
"""ColorLab file loading + image generation."""

import os
import re
import sys
import traceback
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")  # non-interactive; safe to call savefig from any thread
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QFileDialog

from dataManager.CIE_XYZ import (
    CIElab, CIElab_batch, X_BAR, Y_BAR, Z_BAR, xyz_to_rgb255,
)
from ui.testgui2 import Ui_MainWindow


# Reuse the cached color matching arrays from CIE_XYZ throughout (no per-call
# list rebuild, no extra np.asarray copies).
_X_BAR = X_BAR
_Y_BAR = Y_BAR
_Z_BAR = Z_BAR


# ----------------------------------------------------------------------------
# Chromaticity-diagram backdrop (gamut RGBA + locus polygon).
#
# The backdrop is data-independent - same picture every Process click - so we
# build it lazily on first use and cache for the rest of the process.
# ----------------------------------------------------------------------------

_GAMUT_CACHE = {}


def _gamut_backdrop():
    """Return (rgba, locus_xy, extent) for the chromaticity diagram, cached."""
    if _GAMUT_CACHE:
        return (_GAMUT_CACHE["rgba"], _GAMUT_CACHE["locus"], _GAMUT_CACHE["extent"])

    denom = _X_BAR + _Y_BAR + _Z_BAR
    good = denom > 0
    locus_x = _X_BAR[good] / denom[good]
    locus_y = _Y_BAR[good] / denom[good]
    locus = np.column_stack([locus_x, locus_y])
    locus_closed = np.vstack([locus, locus[:1]])

    res = 256
    grid_x = np.linspace(0.0, 0.8, res)
    grid_y = np.linspace(0.0, 0.9, res)
    gx, gy = np.meshgrid(grid_x, grid_y)
    gz = 1.0 - gx - gy
    with np.errstate(divide="ignore", invalid="ignore"):
        X = np.where(gy > 0, gx / gy, 0.0)
        Y = np.ones_like(gy)
        Z = np.where(gy > 0, gz / gy, 0.0)
    R = X * 3.2410 + Y * -1.5374 + Z * -0.4986
    G = X * -0.9692 + Y * 1.8760 + Z * 0.0416
    B = X * 0.0556 + Y * -0.2040 + Z * 1.0570
    RGB = np.dstack([R, G, B])
    RGB = np.clip(RGB, 0.0, 1.0)
    below = RGB < 0.0031308
    RGB = np.where(below, 12.92 * RGB, 1.055 * np.power(RGB, 0.41666) - 0.055)
    peak = np.max(RGB, axis=2, keepdims=True)
    RGB = np.where(peak > 0, RGB / np.maximum(peak, 1e-6), RGB)
    RGB = np.clip(RGB, 0.0, 1.0)

    pts = np.column_stack([gx.ravel(), gy.ravel()])
    inside = MplPath(locus_closed).contains_points(pts).reshape(gx.shape)
    alpha = inside.astype(float)
    rgba = np.dstack([RGB, alpha])

    extent = (0.0, 0.8, 0.0, 0.9)
    _GAMUT_CACHE["rgba"] = rgba
    _GAMUT_CACHE["locus"] = locus_closed
    _GAMUT_CACHE["extent"] = extent
    return rgba, locus_closed, extent


def save_chromaticity_diagram(lab_values, image_title, image_name):
    """Save a CIE 1931 xy chromaticity diagram alongside the color strip."""
    rgba, locus_closed, extent = _gamut_backdrop()

    fig, ax = plt.subplots(1, 1, figsize=(7, 6.5))
    ax.imshow(rgba, origin="lower", extent=extent, aspect="auto",
              interpolation="bilinear")
    ax.plot(locus_closed[:, 0], locus_closed[:, 1], color="black", lw=1.0)

    d65_x, d65_y = 0.31271, 0.32902
    ax.plot(d65_x, d65_y, marker="o", markersize=6,
            markerfacecolor="white", markeredgecolor="black")
    ax.annotate("White (D65)", xy=(d65_x, d65_y),
                xytext=(d65_x + 0.015, d65_y - 0.01),
                fontsize=9, color="black")

    # Vectorize the data-point styling: clip RGB once, then iterate just for
    # the matplotlib calls (cheap for typical N ~= 13).
    if lab_values.size:
        valid = ~((lab_values[:, 0] == 0) & (lab_values[:, 1] == 0))
        pts = lab_values[valid]
        rgb = np.clip(pts[:, 3:] / 255.0, 0.0, 1.0)
        for (cx, cy), color in zip(pts[:, :2], rgb):
            color = tuple(color)
            ax.plot([d65_x, cx], [d65_y, cy], color=color, lw=1.2)
            ax.plot(cx, cy, marker="o", markersize=5,
                    markerfacecolor=color, markeredgecolor="black",
                    markeredgewidth=0.5)

    ax.set_xlim(0.0, 0.8)
    ax.set_ylim(0.0, 0.9)
    ax.set_xlabel("x co-ordinate")
    ax.set_ylabel("y co-ordinate")
    ax.set_title(image_title)
    ax.grid(True, color="gray", alpha=0.25, linewidth=0.5)

    if image_name.lower().endswith(".png"):
        out_path = image_name[:-4] + "_chromaticity.png"
    else:
        out_path = image_name + "_chromaticity.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------
# Colormat builder helpers.
# ----------------------------------------------------------------------------

# Strip image is rendered at this fixed pixel height and re-aspected by
# matplotlib via the user's `image_aspect` arg. Square (NxN) was wasteful.
_STRIP_HEIGHT = 64


def _build_strip_from_gaps(rgb_per_band, gaps):
    """Build (H, W, 3) uint8 strip by repeating each color over `gaps[i]` cols.

    rgb_per_band : (n, 3) - color per band
    gaps         : (n-1,) integers - width per band (last band omitted because
                   the original kinetic logic indexes lab_values[i] for
                   i in range(n-1) and never writes lab_values[n-1])
    """
    gaps = np.asarray(gaps, dtype=int)
    width = int(gaps.sum())
    if width <= 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)
    out = np.zeros((_STRIP_HEIGHT, width, 3), dtype=np.uint8)
    start = 0
    for i, g in enumerate(gaps):
        if g <= 0:
            continue
        out[:, start:start + g] = rgb_per_band[i].astype(np.uint8)
        start += g
    return out


# ----------------------------------------------------------------------------
# Worker - runs the heavy compute off the GUI thread.
# ----------------------------------------------------------------------------

class _LoadFilesWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)  # final status message
    failed = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self._p = params

    def run(self):
        try:
            _process(self._p, self.progress.emit)
            self.finished.emit("Finished!")
        except Exception:
            traceback.print_exc()
            self.failed.emit("Error during processing - see console")


def _process(p, emit):
    """Pure-compute pipeline. p is the params dict assembled by RGBImage.click().

    Emits status strings via `emit(msg)`.
    """
    filepath = p["filepath"]
    filelist = p["filelist"]
    datatype = p["datatype"]
    spec_illum = p["spec_illum"]
    image_title = p["image_title"]
    image_aspect = p["image_aspect"]
    calc_rgb = True
    image_name = p["image_name"]

    num_files = len(filelist)

    # Single-file wide-format detection.
    if num_files == 1:
        full_path = os.path.join(filepath, filelist[0])
        try:
            if full_path.lower().endswith((".xls", ".xlsx")):
                peek = pd.read_excel(full_path)
            else:
                peek = pd.read_csv(full_path, sep=None, engine="python")
        except Exception:
            traceback.print_exc()
            peek = None
        if peek is not None and peek.shape[1] > 2:
            _process_concentration_series(
                peek, datatype, spec_illum, image_title,
                image_aspect, image_name, calc_rgb, emit,
            )
            return

    # Kinetic / per-file path.
    if num_files > 1:
        first_time = filelist[0].split("_")[-1]
        first_t = [int(w) for w in first_time.split(".") if w.isdigit()]

    lab_values = np.zeros((num_files, 6))
    delta = np.zeros((1, num_files))
    seconds_convert = 60
    units = "Minutes"
    i = 0

    for file in filelist:
        full_path = os.path.join(filepath, file)
        if os.path.isdir(full_path):
            print("Skipping ", file, " it is a directory!")
            continue

        emit(f"Reading {file}")
        try:
            if file.endswith(".csv"):
                uvvis_data = pd.read_csv(full_path, sep=None, engine="python")
            elif file.endswith((".xls", ".xlsx")):
                uvvis_data = pd.read_excel(full_path)
            else:
                uvvis_data = pd.read_table(full_path, engine="python")
        except Exception:
            print(file + " is corrupt!")
            if file == filelist[-1] and i == 0:
                print("All files are corrupt!")
                sys.exit(0)
            continue

        if len(uvvis_data) == 0:
            continue

        try:
            cx, cy, _, rr, gg, bb = CIElab(spec_illum, datatype, uvvis_data, calc_rgb)
            lab_values[i] = [cx, cy, 0, rr, gg, bb]

            if num_files > 1:
                curr_time = file.split("_")[-1]
                curr_t = [int(w) for w in curr_time.split(".") if w.isdigit()]
                if curr_t[0] > 3660:
                    seconds_convert = 3600
                    units = "Hours"
                else:
                    seconds_convert = 60
                    units = "Minutes"
                delta[0, i] = (curr_t[0] - first_t[0]) / seconds_convert

            i += 1
        except Exception:
            print("Could not convert data in " + file)
            traceback.print_exc()

    # Drop unfilled rows.
    mask = ~np.all(lab_values == 0, axis=1)
    lab_values = lab_values[mask]
    delta = delta[:, mask]
    new_num_files = lab_values.shape[0]

    if new_num_files == 0:
        emit("No spectra could be converted")
        return

    if new_num_files == 1:
        # Single-spectrum strip.
        colormat = np.zeros((_STRIP_HEIGHT, _STRIP_HEIGHT, 3), dtype=np.uint8)
        colormat[:] = lab_values[0, 3:].astype(np.uint8)
        fig, ax = plt.subplots(1, 1)
        ax.imshow(colormat, aspect=image_aspect)
        ax.axes.get_xaxis().set_visible(False)
        ax.axes.get_yaxis().set_visible(False)
        ax.set_title(image_title)
        fig.savefig(image_name)
        plt.close(fig)
    else:
        # Kinetic strip - widths proportional to elapsed-time gaps.
        if seconds_convert == 3600:
            delta = delta * 60

        delta_delta = np.around(np.diff(delta))[0]  # shape (n-1,)
        delta_delta = np.maximum(delta_delta.astype(int), 1)

        # rgb_per_band aligns with the original loop's lab_values[i] for
        # i in range(n-1). The last band's color is never drawn (preserves
        # original behavior).
        rgb_per_band = lab_values[:-1, 3:]
        colormat = _build_strip_from_gaps(rgb_per_band, delta_delta)

        fig, ax = plt.subplots(1, 1)
        if seconds_convert == 3600:
            ax.imshow(colormat,
                      extent=[delta[0, 0], np.max(delta) / 60,
                              delta[0, 0], np.max(delta) / 60],
                      aspect=image_aspect)
        else:
            ax.imshow(colormat,
                      extent=[delta[0, 0], np.max(delta),
                              delta[0, 0], np.max(delta)],
                      aspect=image_aspect)
        ax.axes.get_yaxis().set_visible(False)
        ax.set_xlabel(units)
        ax.set_title(image_title)
        fig.savefig(image_name)
        plt.close(fig)

    try:
        save_chromaticity_diagram(lab_values, image_title, image_name)
    except Exception:
        traceback.print_exc()


def _process_concentration_series(df, datatype, spec_illum, image_title,
                                  image_aspect, image_name, calc_rgb, emit):
    """Wide-format: 1 wavelength column + N spectrum columns. Vectorized."""
    wavelength_col = df.columns[0]
    spectrum_cols = list(df.columns[1:])

    header_re = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(\S.*?)?\s*$")
    parsed = []
    for c in spectrum_cols:
        m = header_re.match(str(c))
        if m:
            value = float(m.group(1))
            unit = (m.group(2) or "").strip()
            parsed.append((value, unit, c))

    if not parsed:
        emit("Could not parse concentration headers in selected file")
        return

    parsed.sort(key=lambda t: t[0])
    concentrations = np.array([p[0] for p in parsed])
    unit = parsed[0][1] or "concentration"
    cols_in_order = [p[2] for p in parsed]

    # De-duplicate wavelengths once (keep first occurrence).
    wl_int = df[wavelength_col].astype(int).to_numpy()
    _, unique_idx = np.unique(wl_int, return_index=True)
    unique_idx = np.sort(unique_idx)
    wl_int = wl_int[unique_idx]

    spectrum_block = df[cols_in_order].to_numpy(dtype=np.float64)
    spectrum_block = spectrum_block[unique_idx]  # (M, N)
    T_matrix = spectrum_block.T  # (N, M)

    # Auto-scale percent transmission to fraction (CIE math expects [0, 1]).
    if datatype == 1:
        sample_max = float(np.nanmax(T_matrix))
        if sample_max > 1.5:
            T_matrix = T_matrix * 0.01

    emit(f"Computing CIE for {T_matrix.shape[0]} spectra")
    lab_values = CIElab_batch(spec_illum, datatype, wl_int, T_matrix, calc_rgb)

    # Drop rows that came back zero (e.g. fully opaque).
    mask = ~np.all(lab_values == 0, axis=1)
    lab_values = lab_values[mask]
    concentrations = concentrations[mask]
    n = lab_values.shape[0]
    if n == 0:
        emit("No spectra could be converted")
        return

    if n > 1:
        gaps = np.maximum(np.around(np.diff(concentrations)), 1).astype(int)
        rgb_per_band = lab_values[:-1, 3:]
        colormat = _build_strip_from_gaps(rgb_per_band, gaps)

        fig, ax = plt.subplots(1, 1)
        ax.imshow(colormat,
                  extent=[concentrations[0], np.max(concentrations),
                          concentrations[0], np.max(concentrations)],
                  aspect=image_aspect)
        ax.axes.get_yaxis().set_visible(False)
        ax.set_xlabel(unit)
        ax.set_title(image_title)
        fig.savefig(image_name)
        plt.close(fig)
    else:
        colormat = np.zeros((_STRIP_HEIGHT, _STRIP_HEIGHT, 3), dtype=np.uint8)
        colormat[:] = lab_values[0, 3:].astype(np.uint8)
        fig, ax = plt.subplots(1, 1)
        ax.imshow(colormat, aspect=image_aspect)
        ax.axes.get_xaxis().set_visible(False)
        ax.axes.get_yaxis().set_visible(False)
        ax.set_title(image_title)
        fig.savefig(image_name)
        plt.close(fig)

    try:
        save_chromaticity_diagram(lab_values, image_title, image_name)
    except Exception:
        traceback.print_exc()


# ----------------------------------------------------------------------------
# Qt main window.
# ----------------------------------------------------------------------------

class RGBImage(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.gui = Ui_MainWindow()
        self.gui.setupUi(self)
        self.gui.pushButton.clicked.connect(self.click)
        self.gui.pushButton_2.clicked.connect(self.loadFiles)
        self._thread = None
        self._worker = None
        self.show()

    def click(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Spectra File(s)",
            "",
            "Spectra (*.csv *.xls *.xlsx);;All files (*)",
        )
        if not files:
            return
        self.filepath = os.path.dirname(files[0])
        self.filelist = sorted(os.path.basename(f) for f in files)
        self.gui.lineEdit.setText("; ".join(self.filelist))
        self.gui.lineEdit.setReadOnly(False)

    def loadFiles(self):
        if self._thread is not None and self._thread.isRunning():
            return  # already running

        self.statusBar().clearMessage()

        if self.gui.radioButton.isChecked():
            datatype = 0
        elif self.gui.radioButton_2.isChecked():
            datatype = 1
        elif self.gui.radioButton_3.isChecked():
            datatype = 2
        else:
            datatype = 0

        spec_illum = str(self.gui.comboBox.currentText())
        image_title = str(self.gui.lineEdit_2.text())
        image_aspect = float(self.gui.lineEdit_3.text())

        chars_to_be_removed = r'^[^<>/{}[\]~`]*$&#@!;,:'
        filtered_chars = filter(lambda item: item not in chars_to_be_removed, image_title)
        image_name_clean = "".join(filtered_chars)
        if not os.path.isdir("images/"):
            os.mkdir("images/")
        image_name = r"images/" + image_name_clean + ".png"

        params = {
            "filepath": self.filepath,
            "filelist": self.filelist,
            "datatype": datatype,
            "spec_illum": spec_illum,
            "image_title": image_title,
            "image_aspect": image_aspect,
            "image_name": image_name,
        }

        self.gui.pushButton_2.setEnabled(False)
        self.statusBar().showMessage("Working...")

        self._thread = QThread(self)
        self._worker = _LoadFilesWorker(params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_progress(self, msg):
        self.statusBar().showMessage(msg)

    def _on_finished(self, msg):
        self.gui.statusbar.showMessage(msg)
        self.gui.pushButton_2.setEnabled(True)

    def _on_failed(self, msg):
        self.gui.statusbar.showMessage(msg)
        self.gui.pushButton_2.setEnabled(True)

    def _cleanup_thread(self):
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
