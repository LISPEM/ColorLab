# -*- coding: utf-8 -*-
"""ColorLab entry point."""

import os
import sys

# When frozen as a PyInstaller bundle, anchor the working directory to the
# exe's folder so the calc layer's relative paths
# ('dataManager/illuminants.csv', 'dataManager/white_point.csv') resolve and
# generated images land in a writable spot next to the exe.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from PyQt5.QtWidgets import QApplication

from dataManager.loadfiles4CIE import RGBImage
from ui.theme import apply_theme, app_font, load_mode

app = QApplication(sys.argv)
app.setApplicationName("ColorLab")
app.setOrganizationName("ColorLab")
app.setStyle("Fusion")
app.setFont(app_font(10))
apply_theme(app, load_mode())

window = RGBImage()

sys.exit(app.exec_())
