"""ColorLab main window — customtkinter."""

from __future__ import annotations

import queue
from tkinter import filedialog, messagebox

import customtkinter as ctk

from dataManager.loadfiles4CIE import (
    DATATYPE_LABELS,
    ProcessingParams,
    list_illuminant_names,
)
from ui.controls_panel import ControlsPanel
from ui.log_panel import LogPanel
from ui.preview_panel import PreviewPanel
from ui.worker import (
    EVENT_CANCELLED,
    EVENT_DONE,
    EVENT_FATAL,
    EVENT_FILE_ERROR,
    EVENT_PROGRESS,
    ProcessingWorker,
)


class ColorLabApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("ColorLab")
        self.geometry("1200x760")
        self.minsize(1000, 600)

        self._event_queue: "queue.Queue[tuple]" = queue.Queue()
        self._worker = ProcessingWorker(self._event_queue)

        try:
            illuminants = list_illuminant_names()
        except Exception as exc:
            messagebox.showerror(
                "ColorLab",
                f"Could not load illuminants.csv:\n{exc}\n\n"
                "Make sure the dataManager folder is intact.",
            )
            illuminants = []

        self._build_layout(illuminants)
        self.after(50, self._drain_queue)

    def _build_layout(self, illuminants: list[str]) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=320)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.controls = ControlsPanel(
            self,
            illuminants=illuminants,
            on_preview=self._handle_preview,
            on_process=self._handle_process,
            on_cancel=self._handle_cancel,
            on_save=self._handle_save,
            corner_radius=8,
        )
        self.controls.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=(12, 6))

        self.preview = PreviewPanel(self, corner_radius=8)
        self.preview.grid(row=0, column=1, sticky="nsew", padx=6, pady=(12, 6))

        self.log = LogPanel(self, corner_radius=8)
        self.log.grid(row=0, column=2, sticky="nsew", padx=(6, 12), pady=(12, 6))

        self.status_var = ctk.StringVar(value="Ready")
        status_bar = ctk.CTkFrame(self, corner_radius=0, height=26)
        status_bar.grid(row=1, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(status_bar, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=12, pady=4
        )

    # ---- button handlers ----
    def _validate_and_build_params(self, only_first: bool) -> ProcessingParams | None:
        filepaths = getattr(self.controls, "selected_files", [])
        if not filepaths:
            messagebox.showwarning("ColorLab", "Please choose input files first.")
            return None
        illum = self.controls.illum_var.get().strip()
        if not illum:
            messagebox.showwarning("ColorLab", "Please choose an illuminant.")
            return None
        aspect = self.controls.get_aspect()
        if aspect is None:
            messagebox.showwarning(
                "ColorLab", "Aspect ratio must be a positive number."
            )
            return None
        datatype_label = self.controls.datatype_var.get()
        datatype = DATATYPE_LABELS.get(datatype_label, 0)
        title = self.controls.title_var.get().strip() or "ColorLab"
        return ProcessingParams(
            filepaths=filepaths,
            datatype=datatype,
            spec_illum=illum,
            title=title,
            aspect=aspect,
            only_first=only_first,
        )

    def _handle_preview(self) -> None:
        params = self._validate_and_build_params(only_first=True)
        if params is None:
            return
        self._start_worker(params, label="Previewing first file...")

    def _handle_process(self) -> None:
        params = self._validate_and_build_params(only_first=False)
        if params is None:
            return
        self._start_worker(params, label="Processing all files...")

    def _handle_cancel(self) -> None:
        if self._worker.is_running:
            self._worker.cancel()
            self.status_var.set("Cancelling...")
            self.log.info("Cancel requested")

    def _handle_save(self) -> None:
        fig = self.preview.current_figure
        if fig is None:
            messagebox.showinfo("ColorLab", "Generate a preview first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save image as",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg"), ("All files", "*.*")],
            initialfile="colorlab_result.png",
        )
        if not path:
            return
        try:
            fig.savefig(path, dpi=150, bbox_inches="tight")
            self.status_var.set(f"Saved: {path}")
            self.log.info(f"Saved image to {path}")
        except Exception as exc:
            messagebox.showerror("ColorLab", f"Could not save image:\n{exc}")

    # ---- worker lifecycle ----
    def _start_worker(self, params: ProcessingParams, label: str) -> None:
        if self._worker.is_running:
            return
        self.log.reset()
        self.log.info(label)
        self.preview.show_loading(label)
        self.controls.set_running(True)
        self.controls.set_save_enabled(False)
        self.status_var.set(label)
        self._worker.start(params)

    def _drain_queue(self) -> None:
        try:
            while True:
                event = self._event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(50, self._drain_queue)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == EVENT_PROGRESS:
            _, i, total, name = event
            self.log.set_progress(i, total, name)
            self.log.ok(name)
        elif kind == EVENT_FILE_ERROR:
            _, name, reason = event
            self.log.error(name, reason)
        elif kind == EVENT_DONE:
            _, figure = event
            self.preview.set_figure(figure)
            self.controls.set_running(False)
            self.controls.set_save_enabled(True)
            self.status_var.set("Done")
            self.log.info("Finished")
        elif kind == EVENT_CANCELLED:
            self.controls.set_running(False)
            self.preview.show_empty()
            self.status_var.set("Cancelled")
            self.log.info("Cancelled")
        elif kind == EVENT_FATAL:
            _, msg = event
            self.controls.set_running(False)
            self.preview.show_empty()
            self.status_var.set("Error")
            self.log.error("batch", msg)
            messagebox.showerror("ColorLab", msg)
