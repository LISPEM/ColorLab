"""Left-hand controls: folder picker, illuminant, data type, action buttons."""

from __future__ import annotations

from tkinter import filedialog
from typing import Callable

import customtkinter as ctk


_DATATYPE_HELP = (
    "Absorbance: raw A(\u03bb) values. Standard UV-Vis CSV output.\n"
    "Transmission: %T values 0-100.\n"
    "AIPS: fractional transmission delta (internal format)."
)

_ILLUM_HELP = (
    "The reference light source used to compute the color.\n"
    "D65 = average daylight (most common). A = incandescent. "
    "F-series = fluorescent."
)

_ASPECT_HELP = (
    "Width-to-height ratio of the output image. 1 = square. "
    "Increase to stretch horizontally."
)


class _Tooltip:
    """Lightweight hover tooltip that avoids extra dependencies."""

    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._tip: ctk.CTkToplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self._tip is not None:
            return
        x = self.widget.winfo_rootx() + 24
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = ctk.CTkToplevel(self.widget)
        self._tip.overrideredirect(True)
        self._tip.geometry(f"+{x}+{y}")
        self._tip.attributes("-topmost", True)
        label = ctk.CTkLabel(
            self._tip,
            text=self.text,
            justify="left",
            wraplength=280,
            padx=10,
            pady=6,
            fg_color=("gray85", "gray20"),
            corner_radius=6,
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


def _help_badge(parent, text: str) -> ctk.CTkLabel:
    badge = ctk.CTkLabel(
        parent,
        text="?",
        width=20,
        height=20,
        corner_radius=10,
        fg_color=("gray75", "gray30"),
        text_color=("gray10", "gray90"),
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    _Tooltip(badge, text)
    return badge


class ControlsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        illuminants: list[str],
        on_preview: Callable[[], None],
        on_process: Callable[[], None],
        on_cancel: Callable[[], None],
        on_save: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_preview = on_preview
        self._on_process = on_process
        self._on_cancel = on_cancel
        self._on_save = on_save

        self.folder_var = ctk.StringVar(value="")
        self.selected_files: list[str] = []
        self.illum_var = ctk.StringVar(value=illuminants[0] if illuminants else "")
        self.datatype_var = ctk.StringVar(value="Absorbance")
        self.aspect_var = ctk.StringVar(value="1")
        self.title_var = ctk.StringVar(value="ColorLab result")

        self._build(illuminants)

    def _build(self, illuminants: list[str]) -> None:
        row = 0
        header = ctk.CTkLabel(
            self, text="Inputs", font=ctk.CTkFont(size=16, weight="bold")
        )
        header.grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 8))
        row += 1

        # File picker
        ctk.CTkLabel(self, text="Input files").grid(
            row=row, column=0, sticky="w", padx=16
        )
        row += 1
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16)
        file_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(file_frame, textvariable=self.folder_var, state="disabled").grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkButton(
            file_frame, text="Browse", width=80, command=self._pick_files
        ).grid(row=0, column=1, padx=(6, 0))
        row += 1

        # Illuminant
        ctk.CTkLabel(self, text="Illuminant").grid(
            row=row, column=0, sticky="w", padx=16, pady=(12, 0)
        )
        _help_badge(self, _ILLUM_HELP).grid(
            row=row, column=1, sticky="w", padx=(0, 16), pady=(12, 0)
        )
        row += 1
        ctk.CTkComboBox(
            self,
            values=illuminants,
            variable=self.illum_var,
            state="readonly",
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=16)
        row += 1

        # Data type
        ctk.CTkLabel(self, text="Data type").grid(
            row=row, column=0, sticky="w", padx=16, pady=(12, 0)
        )
        _help_badge(self, _DATATYPE_HELP).grid(
            row=row, column=1, sticky="w", padx=(0, 16), pady=(12, 0)
        )
        row += 1
        ctk.CTkSegmentedButton(
            self,
            values=["Absorbance", "Transmission", "AIPS"],
            variable=self.datatype_var,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=16)
        row += 1

        # Aspect
        ctk.CTkLabel(self, text="Aspect ratio").grid(
            row=row, column=0, sticky="w", padx=16, pady=(12, 0)
        )
        _help_badge(self, _ASPECT_HELP).grid(
            row=row, column=1, sticky="w", padx=(0, 16), pady=(12, 0)
        )
        row += 1
        ctk.CTkEntry(self, textvariable=self.aspect_var).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=16
        )
        row += 1

        # Title
        ctk.CTkLabel(self, text="Image title").grid(
            row=row, column=0, sticky="w", padx=16, pady=(12, 0)
        )
        row += 1
        ctk.CTkEntry(self, textvariable=self.title_var).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=16
        )
        row += 1

        # Separator spacing
        ctk.CTkFrame(self, fg_color=("gray80", "gray25"), height=1).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=16
        )
        row += 1

        # Action buttons
        self.preview_btn = ctk.CTkButton(
            self, text="Preview first file", command=self._on_preview
        )
        self.preview_btn.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=4)
        row += 1

        self.process_btn = ctk.CTkButton(
            self, text="Process all files", command=self._on_process,
            fg_color=("#2F6FEB", "#1F4FB7"),
            hover_color=("#2458C2", "#163B8A"),
        )
        self.process_btn.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=4)
        row += 1

        self.cancel_btn = ctk.CTkButton(
            self, text="Cancel", command=self._on_cancel,
            fg_color=("gray60", "gray40"),
            hover_color=("gray50", "gray30"),
            state="disabled",
        )
        self.cancel_btn.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=4)
        row += 1

        ctk.CTkFrame(self, fg_color=("gray80", "gray25"), height=1).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=16
        )
        row += 1

        self.save_btn = ctk.CTkButton(
            self, text="Save image as...", command=self._on_save, state="disabled"
        )
        self.save_btn.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=4)
        row += 1

        self.grid_columnconfigure(0, weight=1)

    def _pick_files(self) -> None:
        import os
        paths = filedialog.askopenfilenames(
            title="Select spectra files",
            filetypes=[
                ("Spectra files", "*.txt *.csv *.xls *.xlsx"),
                ("All files", "*.*"),
            ]
        )
        if paths:
            self.selected_files = list(paths)
            if len(self.selected_files) == 1:
                self.folder_var.set(os.path.basename(self.selected_files[0]))
            else:
                self.folder_var.set(f"{len(self.selected_files)} files selected")

    def set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.preview_btn.configure(state=state)
        self.process_btn.configure(state=state)
        self.cancel_btn.configure(state="normal" if running else "disabled")

    def set_save_enabled(self, enabled: bool) -> None:
        self.save_btn.configure(state="normal" if enabled else "disabled")

    def get_aspect(self) -> float | None:
        raw = self.aspect_var.get().strip()
        try:
            val = float(raw)
            return val if val > 0 else None
        except ValueError:
            return None
