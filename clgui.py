"""ColorLab entry point."""

from ui.app import ColorLabApp


def main() -> None:
    app = ColorLabApp()
    app.mainloop()


if __name__ == "__main__":
    main()
