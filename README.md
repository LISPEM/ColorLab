# ColorLab

The latest release of ColorLab can always be found with the associated DOI below:

[![DOI](https://zenodo.org/badge/427246845.svg)](https://zenodo.org/badge/latestdoi/427246845)

## About ColorLab
ColorLab uses internationally-defined illuminants to translate absorbance spectra into RGB colorspace.

## Running ColorLab

ColorLab now ships with a modern customtkinter GUI. Python 3.9+ is required.

1. Download or clone this repository.
2. Open a terminal in the ColorLab folder.
3. Install dependencies: `pip install -r requirements.txt`
4. Launch the app: `python clgui.py` (or `python3 clgui.py` on macOS/Linux).

### Using the app

- **Input folder** — pick a folder containing UV-Vis spectra files (`.csv`, `.xls`, or tab-separated). Filenames ending in `_<seconds>.ext` enable the time-series color matrix; without timestamps, files render as uniform-width strips.
- **Illuminant** — reference light source. D65 is standard daylight and is the most common choice.
- **Data type** — Absorbance (raw A values), Transmission (%T), or AIPS (internal format).
- **Aspect ratio** — width-to-height ratio of the output image.
- **Image title** — shown on the rendered figure.
- **Preview first file** — fast check that your parameters make sense before running a full batch.
- **Process all files** — runs the whole folder; progress and per-file errors stream to the log on the right.
- **Save image as...** — writes the current preview to a PNG/JPEG of your choice.

[More information about ColorLab](https://arizona.box.com/s/jh7vkxpwik3q5xojpfgcho5ijw0rthgy)
