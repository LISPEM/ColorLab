"""ColorLab theming: light/dark palettes and QSS generation."""

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QFont, QFontDatabase

LIGHT = {
    "bg":          "#F5F6FA",
    "surface":     "#FFFFFF",
    "surface_alt": "#EEF0F7",
    "border":      "#E0E3EC",
    "border_soft": "#EDEFF5",
    "text":        "#1B1F2A",
    "text_muted":  "#6B7180",
    "text_dim":    "#9AA0AE",
    "accent":      "#6E5BFF",
    "accent_hover":"#5A47F0",
    "accent_soft": "#EEEAFF",
    "success":     "#1FA971",
    "danger":      "#E5484D",
    "shadow":      "rgba(20, 24, 40, 0.08)",
    "track":       "#E6E8F0",
    "is_dark":     False,
}

DARK = {
    "bg":          "#0F1115",
    "surface":     "#161922",
    "surface_alt": "#1C202B",
    "border":      "#262B38",
    "border_soft": "#1F2330",
    "text":        "#E6E8EE",
    "text_muted":  "#9AA1B2",
    "text_dim":    "#6B7180",
    "accent":      "#8B7CFF",
    "accent_hover":"#A294FF",
    "accent_soft": "#23223C",
    "success":     "#3DD68C",
    "danger":      "#FF6369",
    "shadow":      "rgba(0, 0, 0, 0.5)",
    "track":       "#222735",
    "is_dark":     True,
}

PALETTES = {"light": LIGHT, "dark": DARK}


def font_family():
    available = set(QFontDatabase().families())
    for candidate in ("Inter", "Segoe UI Variable", "Segoe UI", "SF Pro Text",
                      "Helvetica Neue", "system-ui"):
        if candidate in available:
            return candidate
    return "Sans Serif"


def app_font(size=10, weight=QFont.Normal):
    f = QFont(font_family(), size)
    f.setWeight(weight)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def build_qss(p):
    arrow = "▾"  # used as combobox indicator via image-less style
    return f"""
* {{
    font-family: "{font_family()}", "Segoe UI", system-ui, sans-serif;
    color: {p['text']};
}}

QMainWindow, QWidget#central {{
    background: {p['bg']};
}}

QWidget#header {{
    background: {p['surface']};
    border-bottom: 1px solid {p['border_soft']};
}}

QWidget#sidebar {{
    background: {p['surface']};
    border-right: 1px solid {p['border_soft']};
}}

QWidget#previewPane {{
    background: {p['bg']};
}}

QFrame#card {{
    background: {p['surface']};
    border: 1px solid {p['border_soft']};
    border-radius: 14px;
}}

QFrame#previewFrame {{
    background: {p['surface']};
    border: 1px solid {p['border_soft']};
    border-radius: 16px;
}}

QLabel {{
    background: transparent;
}}

QLabel#brand {{
    color: {p['text']};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel#brandDot {{
    color: {p['accent']};
    font-size: 18px;
    font-weight: 800;
}}

QLabel#tagline {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: 500;
}}

QLabel#sectionTitle {{
    color: {p['text']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}

QLabel#fieldLabel {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QLabel#previewHint {{
    color: {p['text_dim']};
    font-size: 13px;
    font-weight: 500;
}}

QLabel#previewMeta {{
    color: {p['text_muted']};
    font-size: 11px;
}}

QLabel#statusLabel {{
    color: {p['text_muted']};
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    background: {p['surface_alt']};
    border-radius: 10px;
}}

QLineEdit {{
    background: {p['surface_alt']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 9px 12px;
    color: {p['text']};
    selection-background-color: {p['accent']};
    selection-color: white;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {p['accent']};
    background: {p['surface']};
}}

QLineEdit:disabled {{
    color: {p['text_dim']};
}}

QComboBox {{
    background: {p['surface_alt']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 9px 12px;
    color: {p['text']};
    font-size: 13px;
    min-height: 18px;
}}

QComboBox:hover {{
    border: 1px solid {p['accent']};
}}

QComboBox:focus {{
    border: 1px solid {p['accent']};
    background: {p['surface']};
}}

QComboBox::drop-down {{
    width: 24px;
    border: none;
    background: transparent;
}}

QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
}}

QComboBox QAbstractItemView {{
    background: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 4px;
    outline: 0;
    selection-background-color: {p['accent_soft']};
    selection-color: {p['text']};
    color: {p['text']};
}}

QPushButton {{
    background: {p['surface_alt']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background: {p['surface']};
    border: 1px solid {p['accent']};
    color: {p['accent']};
}}

QPushButton:pressed {{
    background: {p['accent_soft']};
}}

QPushButton:disabled {{
    color: {p['text_dim']};
    background: {p['surface_alt']};
    border: 1px solid {p['border_soft']};
}}

QPushButton#primary {{
    background: {p['accent']};
    color: white;
    border: 1px solid {p['accent']};
    padding: 12px 18px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}

QPushButton#primary:hover {{
    background: {p['accent_hover']};
    border: 1px solid {p['accent_hover']};
    color: white;
}}

QPushButton#primary:pressed {{
    background: {p['accent_hover']};
}}

QPushButton#primary:disabled {{
    background: {p['track']};
    color: {p['text_dim']};
    border: 1px solid {p['border']};
}}

QPushButton#segment {{
    background: transparent;
    color: {p['text_muted']};
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#segment:hover {{
    color: {p['text']};
}}

QPushButton#segment:checked {{
    background: {p['surface']};
    color: {p['accent']};
    border: 1px solid {p['border']};
}}

QPushButton#ghost {{
    background: transparent;
    border: 1px solid {p['border']};
    color: {p['text_muted']};
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#ghost:hover {{
    color: {p['accent']};
    border: 1px solid {p['accent']};
}}

QPushButton#themeToggle {{
    background: {p['surface_alt']};
    border: 1px solid {p['border']};
    border-radius: 18px;
    padding: 6px 14px;
    color: {p['text']};
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#themeToggle:hover {{
    border: 1px solid {p['accent']};
    color: {p['accent']};
}}

QFrame#segmentTrack {{
    background: {p['surface_alt']};
    border: 1px solid {p['border_soft']};
    border-radius: 11px;
}}

QProgressBar {{
    background: {p['track']};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: {p['accent']};
    border-radius: 4px;
}}

QStatusBar {{
    background: {p['surface']};
    border-top: 1px solid {p['border_soft']};
    color: {p['text_muted']};
    font-size: 12px;
    padding: 4px 12px;
}}

QStatusBar::item {{
    border: none;
}}

QToolTip {{
    background: {p['surface']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 6px;
    padding: 4px 8px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {p['border']};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p['accent']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


_SETTINGS_KEY = "ColorLab/theme"


def load_mode():
    s = QSettings("ColorLab", "ColorLab")
    return s.value(_SETTINGS_KEY, "light")


def save_mode(mode):
    s = QSettings("ColorLab", "ColorLab")
    s.setValue(_SETTINGS_KEY, mode)


def apply_theme(app, mode):
    palette = PALETTES.get(mode, LIGHT)
    app.setStyleSheet(build_qss(palette))
    save_mode(mode)
    return palette
