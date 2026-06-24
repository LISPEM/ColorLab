# -*- coding: utf-8 -*-
"""
ColorLab — main window UI definition.

Hand-authored Ui_MainWindow used by dataManager.loadfiles4CIE.RGBImage.
Preserves the historical widget attribute names (lineEdit, lineEdit_2,
lineEdit_3, comboBox, radioButton, radioButton_2, radioButton_3, pushButton,
pushButton_2, statusbar) so the controller in dataManager/ runs unchanged.
"""

import os

from PyQt5 import QtCore, QtGui, QtWidgets

from ui.theme import (
    PALETTES,
    apply_theme,
    app_font,
    font_family,
    load_mode,
)


ILLUMINANTS = [
    "Standard Illuminant D65",
    "Standard Illuminant A",
    "Illuminant C",
    "Illuminant D50",
    "Illuminant D55",
    "Illuminant D75",
    "F2",
    "F7",
    "F11",
]

DATATYPES = [
    ("Absorbance", "radioButton"),
    ("Transmission", "radioButton_2"),
    ("AIPS / FT", "radioButton_3"),
]


def _sanitize_title(text):
    """Mirror the title sanitization in dataManager/loadfiles4CIE.py:88-90."""
    chars_to_be_removed = r'^[^<>/{}[\]~`]*$&#@!;,:'
    return "".join(c for c in text if c not in chars_to_be_removed)


class Ui_MainWindow(object):

    # ------------------------------------------------------------------ setup

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 820)
        MainWindow.setMinimumSize(980, 700)
        MainWindow.setFont(app_font(10))

        self._main_window = MainWindow
        self._mode = load_mode()
        self._app = QtWidgets.QApplication.instance()

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("central")
        MainWindow.setCentralWidget(self.centralwidget)

        root = QtWidgets.QVBoxLayout(self.centralwidget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_preview_pane(), 1)
        root.addLayout(body, 1)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        self.statusbar.setSizeGripEnabled(False)
        MainWindow.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready.")
        self.statusbar.messageChanged.connect(self._on_status_changed)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Wire interactive bits.
        self.themeToggle.clicked.connect(self._toggle_theme)
        self.lineEdit.textChanged.connect(self._refresh_action_state)
        self.lineEdit_2.textChanged.connect(self._refresh_action_state)
        self.openFolderBtn.clicked.connect(self._open_image_folder)

        for label, attr in DATATYPES:
            seg = self._segments[attr]
            seg.clicked.connect(self._sync_segment_to_radio)

        self._refresh_action_state()

    # ------------------------------------------------------------------ header

    def _build_header(self):
        header = QtWidgets.QWidget()
        header.setObjectName("header")
        header.setFixedHeight(64)

        h = QtWidgets.QHBoxLayout(header)
        h.setContentsMargins(28, 0, 24, 0)
        h.setSpacing(10)

        brand = QtWidgets.QLabel("ColorLab")
        brand.setObjectName("brand")
        dot = QtWidgets.QLabel("•")
        dot.setObjectName("brandDot")
        tag = QtWidgets.QLabel("Spectra → sRGB")
        tag.setObjectName("tagline")

        h.addWidget(brand)
        h.addWidget(dot)
        h.addWidget(tag)
        h.addStretch(1)

        self.themeToggle = QtWidgets.QPushButton()
        self.themeToggle.setObjectName("themeToggle")
        self.themeToggle.setCursor(QtCore.Qt.PointingHandCursor)
        self.themeToggle.setMinimumWidth(110)
        h.addWidget(self.themeToggle)

        return header

    # ----------------------------------------------------------------- sidebar

    def _build_sidebar(self):
        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(400)

        wrap = QtWidgets.QVBoxLayout(sidebar)
        wrap.setContentsMargins(28, 28, 28, 28)
        wrap.setSpacing(20)

        section = QtWidgets.QLabel("CONFIGURATION")
        section.setObjectName("sectionTitle")
        wrap.addWidget(section)

        wrap.addWidget(self._build_directory_card())
        wrap.addWidget(self._build_datatype_card())
        wrap.addWidget(self._build_illuminant_card())
        wrap.addWidget(self._build_output_card())

        wrap.addStretch(1)

        self.pushButton_2 = QtWidgets.QPushButton()
        self.pushButton_2.setObjectName("primary")
        self.pushButton_2.setCursor(QtCore.Qt.PointingHandCursor)
        self.pushButton_2.setMinimumHeight(44)
        wrap.addWidget(self.pushButton_2)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setRange(0, 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.hide()
        wrap.addWidget(self.progressBar)

        return sidebar

    def _card(self, title):
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        if title:
            lbl = QtWidgets.QLabel(title)
            lbl.setObjectName("fieldLabel")
            v.addWidget(lbl)

        return card, v

    def _build_directory_card(self):
        card, v = self._card("DATA DIRECTORY")

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)

        self.lineEdit = QtWidgets.QLineEdit()
        self.lineEdit.setPlaceholderText("Choose a folder of spectra files…")
        self.lineEdit.setMinimumHeight(38)
        row.addWidget(self.lineEdit, 1)

        self.pushButton = QtWidgets.QPushButton("Browse")
        self.pushButton.setCursor(QtCore.Qt.PointingHandCursor)
        self.pushButton.setMinimumHeight(38)
        row.addWidget(self.pushButton)

        v.addLayout(row)
        return card

    def _build_datatype_card(self):
        card, v = self._card("DATA TYPE")

        track = QtWidgets.QFrame()
        track.setObjectName("segmentTrack")
        track_h = QtWidgets.QHBoxLayout(track)
        track_h.setContentsMargins(4, 4, 4, 4)
        track_h.setSpacing(2)

        # Real radio buttons (kept for controller compatibility, hidden).
        self._segments = {}
        self._segment_group = QtWidgets.QButtonGroup(card)
        self._segment_group.setExclusive(True)

        for idx, (label, attr) in enumerate(DATATYPES):
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName("segment")
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setMinimumHeight(32)
            track_h.addWidget(btn, 1)
            self._segment_group.addButton(btn, idx)
            self._segments[attr] = btn

            radio = QtWidgets.QRadioButton(label, card)
            radio.setObjectName(attr)
            radio.hide()
            setattr(self, attr, radio)

        # Default = Absorbance, matching prior UI.
        self._segments["radioButton"].setChecked(True)
        self.radioButton.setChecked(True)

        v.addWidget(track)
        return card

    def _build_illuminant_card(self):
        card, v = self._card("ILLUMINANT")

        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.setMinimumHeight(38)
        for item in ILLUMINANTS:
            self.comboBox.addItem(item)
        v.addWidget(self.comboBox)

        return card

    def _build_output_card(self):
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)

        title_label = QtWidgets.QLabel("IMAGE TITLE")
        title_label.setObjectName("fieldLabel")
        v.addWidget(title_label)

        self.lineEdit_2 = QtWidgets.QLineEdit()
        self.lineEdit_2.setPlaceholderText("e.g. sample-degradation")
        self.lineEdit_2.setMinimumHeight(38)
        v.addWidget(self.lineEdit_2)

        v.addSpacing(8)
        aspect_label = QtWidgets.QLabel("ASPECT RATIO")
        aspect_label.setObjectName("fieldLabel")
        v.addWidget(aspect_label)

        self.lineEdit_3 = QtWidgets.QLineEdit("1")
        self.lineEdit_3.setAlignment(QtCore.Qt.AlignCenter)
        self.lineEdit_3.setMaximumWidth(110)
        self.lineEdit_3.setMinimumHeight(38)
        self.lineEdit_3.setValidator(QtGui.QDoubleValidator(0.01, 99.99, 3))
        v.addWidget(self.lineEdit_3, 0, QtCore.Qt.AlignLeft)

        return card

    # ------------------------------------------------------------ preview pane

    def _build_preview_pane(self):
        pane = QtWidgets.QWidget()
        pane.setObjectName("previewPane")

        v = QtWidgets.QVBoxLayout(pane)
        v.setContentsMargins(28, 28, 28, 28)
        v.setSpacing(14)

        # Header row: section + status pill + open-folder.
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(10)

        title = QtWidgets.QLabel("PREVIEW")
        title.setObjectName("sectionTitle")
        head.addWidget(title)

        head.addStretch(1)

        self.statusLabel = QtWidgets.QLabel("Idle")
        self.statusLabel.setObjectName("statusLabel")
        head.addWidget(self.statusLabel)

        self.openFolderBtn = QtWidgets.QPushButton("Open folder")
        self.openFolderBtn.setObjectName("ghost")
        self.openFolderBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self.openFolderBtn.setEnabled(False)
        head.addWidget(self.openFolderBtn)

        v.addLayout(head)

        # The preview frame.
        self.previewFrame = QtWidgets.QFrame()
        self.previewFrame.setObjectName("previewFrame")
        pf = QtWidgets.QVBoxLayout(self.previewFrame)
        pf.setContentsMargins(20, 20, 20, 20)

        self.previewLabel = QtWidgets.QLabel()
        self.previewLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.previewLabel.setMinimumSize(360, 360)
        self.previewLabel.setObjectName("previewHint")
        self.previewLabel.setText(
            "No render yet.\n\nPick a directory, set an image title, then press Process."
        )
        pf.addWidget(self.previewLabel, 1)

        v.addWidget(self.previewFrame, 1)

        # Footer meta.
        self.previewMeta = QtWidgets.QLabel("")
        self.previewMeta.setObjectName("previewMeta")
        v.addWidget(self.previewMeta)

        # Resize hook so the preview rescales.
        self.previewFrame.installEventFilter(_PreviewResizer(self))

        # Cached unscaled pixmap.
        self._raw_preview = None
        self._last_image_path = None

        return pane

    # -------------------------------------------------------------- behaviour

    def retranslateUi(self, MainWindow):
        _ = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_("MainWindow", "ColorLab"))
        self.pushButton_2.setText(_("MainWindow", "Process"))
        self._update_theme_toggle_text()

    def _update_theme_toggle_text(self):
        next_label = "Dark" if self._mode == "light" else "Light"
        glyph = "☾" if self._mode == "light" else "☀"
        self.themeToggle.setText(f"{glyph}  {next_label}")

    def _toggle_theme(self):
        self._mode = "dark" if self._mode == "light" else "light"
        if self._app is not None:
            apply_theme(self._app, self._mode)
        self._update_theme_toggle_text()
        # Re-render the preview so the placeholder color follows the theme.
        if self._raw_preview is None:
            self.previewLabel.setText(self.previewLabel.text())

    def _sync_segment_to_radio(self):
        for attr, btn in self._segments.items():
            getattr(self, attr).setChecked(btn.isChecked())
        self._refresh_action_state()

    def _refresh_action_state(self):
        ready = bool(self.lineEdit.text().strip()) and bool(self.lineEdit_2.text().strip())
        self.pushButton_2.setEnabled(ready)

    def _on_status_changed(self, message):
        if not message:
            self.statusLabel.setText("Idle")
            self.progressBar.hide()
            return

        if message.lower().startswith("finished"):
            self.statusLabel.setText("Done")
            self.progressBar.hide()
            self._load_preview_from_inputs()
        else:
            self.statusLabel.setText(message)
            self.progressBar.show()

    def _expected_image_path(self):
        title = _sanitize_title(self.lineEdit_2.text())
        if not title:
            return None
        chromaticity = os.path.join("images", title + "_chromaticity.png")
        if os.path.isfile(chromaticity):
            return chromaticity
        return os.path.join("images", title + ".png")

    def _load_preview_from_inputs(self):
        path = self._expected_image_path()
        if not path or not os.path.isfile(path):
            self.previewMeta.setText("Finished, but the rendered image could not be located.")
            return

        pixmap = QtGui.QPixmap(path)
        if pixmap.isNull():
            self.previewMeta.setText(f"Could not load preview from {path}")
            return

        self._raw_preview = pixmap
        self._last_image_path = path
        self._rescale_preview()
        size = pixmap.size()
        self.previewMeta.setText(
            f"{path}    •    {size.width()}×{size.height()} px"
        )
        self.openFolderBtn.setEnabled(True)

    def _rescale_preview(self):
        if self._raw_preview is None:
            return
        target = self.previewLabel.size()
        if target.width() < 16 or target.height() < 16:
            return
        scaled = self._raw_preview.scaled(
            target,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.previewLabel.setPixmap(scaled)

    def _open_image_folder(self):
        folder = os.path.abspath("images")
        if not os.path.isdir(folder):
            return
        url = QtCore.QUrl.fromLocalFile(folder)
        QtGui.QDesktopServices.openUrl(url)


class _PreviewResizer(QtCore.QObject):
    """Rescales the cached preview pixmap when the frame resizes."""

    def __init__(self, ui):
        super().__init__()
        self._ui = ui

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Resize:
            self._ui._rescale_preview()
        return False
