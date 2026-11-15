<p align="center"> <img width="1000px" src="https://github.com/Forgotten-Hope-2-community-addons/.github/blob/cdf851d807b9bdd3c382b0ab12a1b4added553b2/media/fh2_banner.jpg"/> </p>

# Battlefield 2 Modern Mod Toolkit

The Battlefield 2 modern mod toolkit is a cross-platform python application designed to supersede the legacy win32 **BF2 Mod Toolkit**. It streamlines Battlefield 2 and Forgotten Hope 2 modification development by handling level organization, texture management, and heightmap processing.

## Prerequisites

* Python 3.9 or higher installed on your system (required by Pillow >= 11.2.1).
* Required python packages: `PyQt6`, `Pillow`, `NumPy`, and `PyYAML`.

## Installation

1. Download or clone the toolkit repository into your preferred mod tools directory.
2. Open a terminal or command prompt inside the toolkit folder.
3. Create a virtual environment and install the required python dependencies for your platform:

   **Windows (PowerShell or cmd):**
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   **Unix (Linux and macOS):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Running tests

The test suite verifies the texture format contracts the toolkit relies on: the DDS headers the BF2 editor expects (uncompressed 32-bit A8R8G8B8 and DXT5) and the lossless 16-bit PNG round trip for heightmaps. Run it from the toolkit folder with the virtual environment activated:

```bash
python -m unittest discover tests
```

## Features

### 1. Mod folder configuration and explorer

* Allows you to select and configure your main modification directory via the preferences menu or the main interface.
* Automatically scans and indexes all custom map levels located within the mod folder hierarchy (`/levels/`).

### 2. Level metadata and file inspection

* Displays real-time map metadata including level name, directory path, heightmap dimensions, and primary world scale extracted from configuration files.
* Provides a scrollable file browser listing all assets present in the selected level directory with precise file sizes.
* Supports opening any level directory directly in your system file explorer via a double-click action.

### 3. Texture export operations

* **Heightmaps**: Converts raw heightmap data files into editable png images, supporting both primary 16-bit and secondary 8-bit heightmaps.
* **Colormaps**: Stitches individual dds map tiles into a unified master colormap png image for global editing.
* **Detailmaps**: Assembles terrain detail layer patches into comprehensive png textures.
* **Lowdetailmaps**: Exports distant low-detail terrain patches into standard png files.

### 4. Texture import operations

* **Heightmaps**: Re-encodes modified png heightmaps back into raw binary formats for game engine compatibility.
* **Colormaps**: Automatically slices an updated master png colormap back into individual dds patches.
* **Detailmaps**: Breaks down edited detail layer images into synchronized patch files.
* **Lowdetailmaps**: Converts customized png low-detail textures back into dds format.

### 5. Interactive preview panel

* Features a dedicated texture type selector supporting heightmaps, colormaps, detailmap (1), detailmap (2), and lowdetailmap.
* Renders a responsive, resizable squared image viewer that dynamically loads exported png previews.
* Displays a clear placeholder notification prompting you to export textures if no preview image is found.

### 6. Automated utilities

* Includes an optional auto-flip setting to handle vertical y-axis orientation inversions automatically during texture conversion.
* Operates heavy texture processing tasks in background worker threads to keep the graphical user interface fully responsive with progress dialog tracking.
* Processes the 64 colormap and detailmap patches in parallel, with a fast reader for uncompressed dds files (see [texture processing performance](docs/texture_performance.md)).

## User instructions

### Getting started

1. Launch the application by executing `python main.py` in your terminal.
2. Upon first launch, you are prompted for your mod folder. If a Forgotten Hope 2 installation is found in its default location, you can use it with one click; otherwise browse to your mod folder. You can change it later with the browse mod folder button, or via the settings menu in the top bar (see [first boot mod folder prompt](docs/first_boot.md)).
3. Select any map level from the left-hand panel to view its metadata, file breakdown, and texture assets.

### Managing export operations

1. Click the heightmaps export button under the export operations section to transform raw heightmap files into editable png images.
2. Click the colormaps button to stitch individual dds map tiles into a unified master colormap png.
3. Click the detailmaps or lowdetailmaps buttons to assemble terrain layer patches into comprehensive png textures.

### Managing import operations

1. Place your edited png files inside the appropriate level directories.
2. Click the corresponding import button under the import operations section to re-encode and slice png images back into game-ready dds or raw binary files.

### Using the preview panel

1. Locate the preview panel positioned beneath the import operations section.
2. Use the texture type dropdown menu to select between heightmap, colormap, detailmap (1), detailmap (2), or lowdetailmap.
3. View the responsive and resizable squared image viewer which automatically renders the selected texture or displays a helpful placeholder notification if the export file is missing.

## Credits

* **Icons**: The user interface icons come from [Qlementine Icons](https://github.com/oclero/qlementine-icons) by Olivier Cléro, licensed under the MIT license. The license text is included in [icons/LICENSE](icons/LICENSE). New icons should be picked from the same set to keep a consistent style, browsable at the [Qlementine Icons gallery](https://oclero.github.io/qlementine-icons/).

## Future work

1. **App icon** (https://forum.qt.io/topic/162658/changing-the-taskbar-icon)
2. **Export destination toggle** (export as editor files or as game ready files). A textures re-save in the bf2editor is currently necessary to convert the editor files into game-ready files, after each import.
3. **DDS formats not covered by Pillow**. Pillow (>= 11.2.1) can save DXT1, DXT3, DXT5, BC2, BC3 and BC5 compressed DDS files, which covers every editor file format we currently write. However, it cannot generate mipmap chains (needed for game-ready colormaps and lowdetailmaps, and for the surrounding terrain `tx_s*.dds` colormaps), does not support BC7, and offers no control over compression quality. If those become necessary, the alternatives are:
   - [quicktex](https://pypi.org/project/quicktex/): pip-installable BC1-BC5 encoder based on RGBCX, one of the highest quality S3TC encoders (last updated mid-2023).
   - [texfury](https://pypi.org/project/texfury/): pip-installable BC1-BC7 encoder with a simple Pillow-friendly API (`Texture.from_pil(img, format=BCFormat.BC3).save_dds(...)`).
   - External CLI tools invoked via subprocess: `nvtt_export.exe` (NVIDIA Texture Tools Exporter) or Microsoft's `texconv`. Both handle every format plus mipmap generation, but reintroduce a dependency on external software.
4. **Preserve sizing**. Safe-keep window position, size and panels' sizes to preserve them between sessions.
5. **Executable packaging** ([pyinstaller](https://github.com/Forgotten-Hope-2-community-addons/fh2-mod-toolkit/tree/main)) for Windows, Linux and MacOS. The current distribution is a Python script that requires a Python interpreter and dependencies to be installed on the host system. Packaging the toolkit as a standalone executable would simplify installation and usage for end-users.