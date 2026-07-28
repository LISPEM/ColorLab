"""Right-hand log panel: progress bar + scrolling color-coded log."""

from __future__ import annotations

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._build()

    def _build(self) -> None:
        header = ctk.CTkLabel(
            self, text="Progress", font=ctk.CTkFont(size=16, weight="bold")
        )
        header.pack(anchor="w", padx=16, pady=(16, 8))

        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=16)
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(
            self, text="Idle", text_color=("gray40", "gray70"), anchor="w"
        )
        self.progress_label.pack(fill="x", padx=16, pady=(4, 12))

        self.textbox = ctk.CTkTextbox(
            self, wrap="word", font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.textbox.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.textbox.configure(state="disabled")
        self.textbox.tag_config("ok", foreground="#2E8B57")
        self.textbox.tag_config("err", foreground="#D64545")
        self.textbox.tag_config("info", foreground="#4A7FBF")

    def _append(self, text: str, tag: str | None = None) -> None:
        self.textbox.configure(state="normal")
        if tag:
            self.textbox.insert("end", text, tag)
        else:
            self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def info(self, msg: str) -> None:
        self._append(f"  {msg}\n", tag="info")

    def ok(self, filename: str) -> None:
        self._append(f"  OK   {filename}\n", tag="ok")

    def error(self, filename: str, reason: str) -> None:
        self._append(f"  ERR  {filename} \u2014 {reason}\n", tag="err")

    def set_progress(self, i: int, total: int, filename: str = "") -> None:
        fraction = 0 if total == 0 else min(1.0, i / total)
        self.progress.set(fraction)
        if filename:
            self.progress_label.configure(text=f"{i}/{total}  {filename}")
        else:
            self.progress_label.configure(text=f"{i}/{total}")

    def reset(self) -> None:
        self.progress.set(0)
        self.progress_label.configure(text="Idle")
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
