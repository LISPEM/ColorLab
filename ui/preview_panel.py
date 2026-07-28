"""Matplotlib figure preview embedded in a customtkinter frame."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._mpl_canvas: Optional[FigureCanvasTkAgg] = None
        self._placeholder: Optional[ctk.CTkLabel] = None
        self._show_placeholder("Pick an input folder,\nthen click Preview or Process.")

    def _clear(self) -> None:
        if self._mpl_canvas is not None:
            self._mpl_canvas.get_tk_widget().destroy()
            self._mpl_canvas = None
        if self._placeholder is not None:
            self._placeholder.destroy()
            self._placeholder = None

    def _show_placeholder(self, text: str) -> None:
        self._clear()
        self._placeholder = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray70"),
            justify="center",
        )
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def set_figure(self, figure: Figure) -> None:
        self._clear()
        self._mpl_canvas = FigureCanvasTkAgg(figure, master=self)
        self._mpl_canvas.draw()
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def show_loading(self, text: str = "Processing...") -> None:
        self._show_placeholder(text)

    def show_empty(self) -> None:
        self._show_placeholder("Pick an input folder,\nthen click Preview or Process.")

    @property
    def current_figure(self) -> Optional[Figure]:
        return self._mpl_canvas.figure if self._mpl_canvas else None
