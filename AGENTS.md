# AGENTS.md - BF2 Mod Toolkit Development Guide

Welcome! This document provides context, architecture guidelines, and instructions for AI coding assistants and developers working locally on the **BF2 Mod Toolkit** (`main.py`).

---

## Project Overview

The **BF2 Mod Toolkit** is a modern, cross-platform Python desktop application built with `PyQt6`, `Pillow`, `NumPy`, and `PyYAML`. It supersedes the legacy Win32 BF2 Mod Toolkit, streamlining level asset inspection, heightmap conversions, and texture atlas stitching for *Battlefield 2* and *Forgotten Hope 2* modding projects.

---

## Tech Stack & Core Libraries

* **GUI Framework**: `PyQt6` (featuring dark/light theme switching, dynamic splitters, custom tool buttons, and custom `QLabel` widgets for scalable preview rendering).
* **Image Processing**: `Pillow` (PIL) for image manipulations, scaling, cropping, and saving into standard PNG or DDS formats.
* **Array Processing**: `NumPy` for raw binary heightmap data manipulation (`.raw`) and efficient per-tile vertical pixel-flipping (`arr[::-1]`).
* **Configuration**: `PyYAML` for persisting user preferences (`settings.yml`).
* **Concurrency**: `QThread` combined with `QProgressDialog` to prevent UI freezing during heavy file I/O operations.

---

## Architecture & Code Structure

The entire application resides within a single file (`main.py`) for ease of distribution:
1. **`ResizablePreviewLabel`**: Custom `QLabel` subclass that preserves aspect ratio and dynamically redraws scaled pixmaps on window resizing and splitter adjustments.
2. **`WorkerThread`**: Handles asynchronous background tasks and signals completion status back to the main GUI thread.
3. **`SettingsDialog`**: Modal dialog for managing preferences (dark mode, auto-flip toggle, default mod path).
4. **`BF2ModToolkitApp`**: The main `QMainWindow` class managing directory parsing, file lists, metadata reading, preview rendering, and all texture import/export routines.

---

## Key Coordinate & Texture Systems

When developing or modifying texture handlers, strict adherence to the coordinate system is required:

* **Heightmaps**: 
  - Primary: `1025x1025` 16-bit raw binary (`HeightmapPrimary.raw`).
  - Secondary: `257x257` 8-bit raw binaries.
* **Colormaps & Detailmaps Atlas Assembly**:
  - Tiling format uses `tx{col}x{row}.dds` (where `col` is `X` west-to-east [0-7], and `row` is `Y` north-to-south [0-7]).
  - **Stitching/Unstitching Rule**: 
    - Columns go left-to-right as-is (`col * patch_size`).
    - Rows are inverted on the canvas (`dst_row = 7 - row`) so row 0 sits at the bottom and row 7 sits at the top.
    - Each patch tile's pixel data must be vertically flipped (`arr = arr[::-1, :, :]`) to align DDS top-to-bottom pixel storage with the bottom-left OpenGL UV origin.
    - Master canvas inversion (`master_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)`) is applied conditionally based on the global `auto_flip` setting.
* **Path Safety**: Always use `os.path.join()` when constructing file paths to prevent Windows escape character issues (such as `\t` interpreting as a tab).

---

## Development Guidelines for AI Agents

1. **Sentence-Level Capitalization**: In documentation, markdown notes, and user-facing descriptions, capitalize **only** the first letter of each sentence, not every word.
2. **Preserve Threading**: Any new I/O-heavy operations or batch processing tasks must be dispatched through `WorkerThread` to maintain UI responsiveness.
3. **Icon Assets**: UI buttons rely on SVG icon files located in the `icons/` directory (e.g., `export.svg`, `import.svg`, `picture.svg`, etc.). Ensure UI components check for icon existence gracefully. All icons come from [Qlementine Icons](https://github.com/oclero/qlementine-icons) (MIT license, gallery at https://oclero.github.io/qlementine-icons/); pick new icons from that set to keep a consistent style, and keep `icons/LICENSE` alongside them. Text labels for buttons using an icon are capitalized and start with a whitespace to provide a visual separation (margin) from the icon.
4. **Error Handling**: Log exceptions explicitly using Python's `logging` module and present user-friendly error messages via `QMessageBox`.