import os
import sys
import subprocess
import platform
import yaml
import logging
import struct
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolButton,
    QProgressDialog,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Standard Forgotten Hope 2 install location, only offered as a suggestion on first run
FH2_DEFAULT_MOD_FOLDER = "C:/Program Files (x86)/Forgotten Hope 2/mods/fh2"

# Colormaps and detailmaps are split into an 8x8 grid of 512x512 patches
PATCH_SIZE = 512
PATCH_GRID = 8

# Pillow releases the GIL while encoding/decoding DDS, so threads run patches truly in parallel
TEXTURE_WORKERS = max(1, min(8, os.cpu_count() or 1))

# Fast compression for the 4096x4096 canvases: ~35% faster saves for ~60% larger files
PNG_COMPRESS_LEVEL = 1

# Pixel format of uncompressed editor patches (A8R8G8B8), see docs/formats.md
_DDPF_RGB = 0x40
_A8R8G8B8_MASKS = (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)


def read_dds_rgba(path):
  """Read a DDS file as an RGBA image.

  Uncompressed A8R8G8B8 files are decoded with NumPy, because Pillow decodes
  bitmask formats in pure Python (~0.25 s per 512x512 patch). Any other
  format falls back to Pillow.
  """
  with open(path, "rb") as f:
    data = f.read()
  if len(data) >= 128 and data[:4] == b"DDS ":
    height, width = struct.unpack_from("<II", data, 12)
    pf_flags, fourcc, bitcount = struct.unpack_from("<I4sI", data, 80)
    masks = struct.unpack_from("<4I", data, 92)
    size = width * height * 4
    if (pf_flags & _DDPF_RGB and fourcc != b"DX10" and bitcount == 32
        and masks == _A8R8G8B8_MASKS and len(data) >= 128 + size):
      bgra = np.frombuffer(data, dtype=np.uint8, count=size, offset=128).reshape(height, width, 4)
      return Image.fromarray(np.ascontiguousarray(bgra[..., [2, 1, 0, 3]]), mode="RGBA")
  with Image.open(path) as img:
    return img.convert("RGBA")


def stitch_patches(patch_dir, name_fmt, auto_flip):
  """Assemble the 8x8 DDS patches named by name_fmt into one canvas (missing patches stay blank)."""
  full_size = PATCH_SIZE * PATCH_GRID
  master_img = Image.new("RGBA", (full_size, full_size))

  def load(col, row):
    patch_path = os.path.join(patch_dir, name_fmt.format(col=col, row=row))
    if not os.path.exists(patch_path):
      return None
    # DDS stores rows top-to-bottom, patches follow the bottom-left (OpenGL) UV origin
    return read_dds_rgba(patch_path).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

  cells = [(col, row) for col in range(PATCH_GRID) for row in range(PATCH_GRID)]
  with ThreadPoolExecutor(TEXTURE_WORKERS) as pool:
    patches = pool.map(lambda cell: load(*cell), cells)
    # Pasting stays on this thread, workers never touch the shared canvas
    for (col, row), p_img in zip(cells, patches):
      if p_img is not None:
        dst_row = PATCH_GRID - 1 - row
        master_img.paste(p_img, (col * PATCH_SIZE, dst_row * PATCH_SIZE))

  if auto_flip:
    master_img = master_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
  return master_img


def unstitch_patches(img, patch_dir, name_fmt, auto_flip, **save_kwargs):
  """Split a canvas into the 8x8 DDS patches named by name_fmt (inverse of stitch_patches)."""
  if auto_flip:
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

  def save(col, row):
    dst_row = PATCH_GRID - 1 - row
    box = (col * PATCH_SIZE, dst_row * PATCH_SIZE, (col + 1) * PATCH_SIZE, (dst_row + 1) * PATCH_SIZE)
    patch_img = img.crop(box).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    patch_img.save(os.path.join(patch_dir, name_fmt.format(col=col, row=row)), format="DDS", **save_kwargs)

  cells = [(col, row) for col in range(PATCH_GRID) for row in range(PATCH_GRID)]
  with ThreadPoolExecutor(TEXTURE_WORKERS) as pool:
    # list() surfaces the first worker exception, if any
    list(pool.map(lambda cell: save(*cell), cells))


def run_in_parallel(funcs):
  """Run independent callables concurrently and return their results in order."""
  with ThreadPoolExecutor(len(funcs)) as pool:
    futures = [pool.submit(f) for f in funcs]
    return [f.result() for f in futures]


def is_valid_mod_folder(path):
  """A mod folder is valid when it contains a 'levels' directory."""
  return bool(path) and os.path.isdir(os.path.join(path, "levels"))


class ResizablePreviewLabel(QLabel):
  """Custom QLabel that maintains and resizes the preview image dynamically."""

  def __init__(self, parent=None):
    super().__init__(parent)
    self.original_pixmap = None

  def setPixmap(self, pixmap: QPixmap):
    self.original_pixmap = pixmap
    super().setPixmap(self.get_scaled_pixmap())

  def get_scaled_pixmap(self):
    if self.original_pixmap and not self.original_pixmap.isNull():
      return self.original_pixmap.scaled(
          self.size(),
          Qt.AspectRatioMode.KeepAspectRatio,
          Qt.TransformationMode.SmoothTransformation
      )
    return QPixmap()

  def resizeEvent(self, event):
    super().resizeEvent(event)
    if self.original_pixmap and not self.original_pixmap.isNull():
      super().setPixmap(self.get_scaled_pixmap())


class WorkerThread(QThread):
  finished = pyqtSignal(bool, str)

  def __init__(self, func, *args, **kwargs):
    super().__init__()
    self.func = func
    self.args = args
    self.kwargs = kwargs

  def run(self):
    try:
      self.func(*self.args, **self.kwargs)
      self.finished.emit(True, "")
    except Exception as e:
      logging.exception("Exception in background worker thread:")
      self.finished.emit(False, str(e))


class SettingsDialog(QDialog):

  def __init__(self, dark_mode_active, auto_flip_active, current_path, parent=None):
    super().__init__(parent)
    self.setWindowTitle("Settings")
    self.resize(450, 180)

    layout = QVBoxLayout(self)

    # Dark mode checkbox switch
    self.dark_mode_checkbox = QCheckBox("Dark mode")
    self.dark_mode_checkbox.setChecked(dark_mode_active)
    layout.addWidget(self.dark_mode_checkbox)

    # Auto flip checkbox switch
    self.auto_flip_checkbox = QCheckBox("Auto flip textures vertically (Y-axis)")
    self.auto_flip_checkbox.setChecked(auto_flip_active)
    layout.addWidget(self.auto_flip_checkbox)

    # Default Mod Folder selection
    path_layout = QHBoxLayout()
    path_layout.addWidget(QLabel("Default Mod Folder:"))
    self.path_input = QLineEdit(current_path)
    browse_btn = QPushButton("Browse")
    browse_btn.clicked.connect(self.browse_path)
    path_layout.addWidget(self.path_input)
    path_layout.addWidget(browse_btn)
    layout.addLayout(path_layout)

    # Save button
    save_btn = QPushButton("Save Settings")
    save_btn.clicked.connect(self.accept)
    layout.addWidget(save_btn)

  def browse_path(self):
    dir_path = QFileDialog.getExistingDirectory(
        self, "Select Default Mod Directory"
    )
    if dir_path:
      self.path_input.setText(dir_path)

  def get_settings(self):
    return (
        self.dark_mode_checkbox.isChecked(),
        self.auto_flip_checkbox.isChecked(),
        self.path_input.text().strip(),
    )


class BF2ModToolkitApp(QMainWindow):

  def __init__(self):
    super().__init__()
    self.settings_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "settings.yml"
    )
    self.settings = self.load_settings()

    self.mod_path = self.settings.get("default_mod_folder") or ""
    self.dark_mode = self.settings.get("dark_mode", True)
    self.auto_flip = self.settings.get("auto_flip", False)
    self.levels_path = ""
    self.worker = None
    self.progress_dialog = None
    self.icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

    self.init_ui()

    if is_valid_mod_folder(self.mod_path):
      self.path_input.setText(self.mod_path)
      self.levels_path = os.path.join(self.mod_path, "levels")
      self.load_levels()
    else:
      # Defer the prompt until the event loop runs, so it shows over the main window
      QTimer.singleShot(0, self.prompt_for_mod_folder)

  def load_settings(self):
    default_settings = {
        "dark_mode": True,
        "auto_flip": True,
        "default_mod_folder": "",
    }
    if os.path.exists(self.settings_file):
      try:
        with open(self.settings_file, "r") as f:
          data = yaml.safe_load(f)
          if isinstance(data, dict):
            default_settings.update(data)
      except Exception as e:
        logging.warning(f"Could not load settings file: {e}")
    return default_settings

  def save_settings(self):
    try:
      with open(self.settings_file, "w") as f:
        yaml.safe_dump(self.settings, f)
    except Exception as e:
      logging.error(f"Could not save settings: {e}")
      QMessageBox.critical(self, "Error", f"Could not save settings: {e}")

  def get_icon(self, filename):
    icon_path = os.path.join(self.icons_dir, filename)
    if os.path.exists(icon_path):
      return QIcon(icon_path)
    return QIcon()

  def init_ui(self):
    self.setWindowTitle("BF2 Modern Mod Toolkit")
    self.resize(1200, 850)

    # Top Menu Bar
    menubar = self.menuBar()
    menubar.clear()  # Clear existing menus to prevent duplication on re-init
    settings_menu = menubar.addMenu("Settings")
    settings_action = settings_menu.addAction("Preferences...")
    settings_action.triggered.connect(self.open_settings)

    # Central Widget Layout
    central_widget = QWidget()
    self.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)

    # Top Bar: Mod Path Selection
    path_layout = QHBoxLayout()
    self.path_input = QLineEdit()
    self.path_input.setPlaceholderText(
        "Select your Battlefield 2 Mod folder..."
    )
    self.path_input.setReadOnly(True)

    browse_btn = QPushButton("Browse Mod Folder")
    browse_btn.clicked.connect(self.select_mod_folder)

    path_layout.addWidget(QLabel("Mod path:"))
    path_layout.addWidget(self.path_input)
    path_layout.addWidget(browse_btn)
    main_layout.addLayout(path_layout)

    # Main Horizontal Splitter for Levels List and Right Panel
    main_splitter = QSplitter(Qt.Orientation.Horizontal)

    # Left: Levels Table
    self.levels_table = QTableWidget()
    self.levels_table.setColumnCount(1)
    self.levels_table.setHorizontalHeaderLabels(["Level name"])
    self.levels_table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeMode.Stretch
    )
    self.levels_table.setSelectionBehavior(
        QTableWidget.SelectionBehavior.SelectRows
    )
    self.levels_table.itemSelectionChanged.connect(self.on_level_selected)
    self.levels_table.itemDoubleClicked.connect(self.on_level_double_clicked)
    main_splitter.addWidget(self.levels_table)

    # Right Panel containing Vertical Splitter to allow resizable sections
    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)

    vertical_splitter = QSplitter(Qt.Orientation.Vertical)

    # Top portion of right panel: Metadata & Files
    top_info_widget = QWidget()
    top_info_layout = QVBoxLayout(top_info_widget)
    top_info_layout.setContentsMargins(0, 0, 0, 0)

    top_info_layout.addWidget(QLabel("<b>Level metadata</b>"))
    self.metadata_label = QLabel(
        "Select a level from the list to view metadata."
    )
    self.metadata_label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
    )
    top_info_layout.addWidget(self.metadata_label)

    top_info_layout.addWidget(QLabel("<b>Files</b>"))
    self.files_content_widget = QWidget()
    self.files_layout = QVBoxLayout(self.files_content_widget)

    self.files_scroll_area = QScrollArea()
    self.files_scroll_area.setWidgetResizable(True)
    self.files_scroll_area.setWidget(self.files_content_widget)
    top_info_layout.addWidget(self.files_scroll_area)

    vertical_splitter.addWidget(top_info_widget)

    # Middle-Bottom portion of right panel: Operations & Preview Panel
    actions_widget = QWidget()
    actions_layout = QVBoxLayout(actions_widget)
    actions_layout.setContentsMargins(0, 0, 0, 0)

    # --- Section 1: Export Operations ---
    export_header = QToolButton()
    export_header.setText(" Export operations")
    export_header.setIcon(self.get_icon("export.svg"))
    export_header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    export_header.setStyleSheet("font-weight: bold; border: none; background: transparent;")
    actions_layout.addWidget(export_header)

    export_buttons_layout = QHBoxLayout()
    
    self.btn_export_height = QToolButton()
    self.btn_export_height.setText(" Heightmaps")
    self.btn_export_height.setIcon(self.get_icon("eq-medium-boost.svg"))
    self.btn_export_height.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_export_height.setToolTip("Export heightmaps to PNG")

    self.btn_export_color = QToolButton()
    self.btn_export_color.setText(" Colormaps")
    self.btn_export_color.setIcon(self.get_icon("paint-palette.svg"))
    self.btn_export_color.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_export_color.setToolTip("Export colormaps to PNG")

    self.btn_export_detail = QToolButton()
    self.btn_export_detail.setText(" Detailmaps")
    self.btn_export_detail.setIcon(self.get_icon("layers-3.svg"))
    self.btn_export_detail.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_export_detail.setToolTip("Export detailmaps to PNG")

    self.btn_export_lowdetail = QToolButton()
    self.btn_export_lowdetail.setText(" Lowdetailmaps")
    self.btn_export_lowdetail.setIcon(self.get_icon("paint-roll-brush.svg"))
    self.btn_export_lowdetail.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_export_lowdetail.setToolTip("Export lowdetailmaps to PNG")

    for btn in [self.btn_export_height, self.btn_export_color, self.btn_export_detail, self.btn_export_lowdetail]:
      btn.setIconSize(QSize(18, 18))
      export_buttons_layout.addWidget(btn)

    actions_layout.addLayout(export_buttons_layout)

    # --- Section 2: Import Operations ---
    import_header = QToolButton()
    import_header.setText(" Import operations")
    import_header.setIcon(self.get_icon("import.svg"))
    import_header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    import_header.setStyleSheet("font-weight: bold; border: none; background: transparent;")
    actions_layout.addWidget(import_header)

    import_buttons_layout = QHBoxLayout()

    self.btn_import_height = QToolButton()
    self.btn_import_height.setText(" Heightmaps")
    self.btn_import_height.setIcon(self.get_icon("eq-medium-boost.svg"))
    self.btn_import_height.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_import_height.setToolTip("Import heightmaps to DDS")

    self.btn_import_color = QToolButton()
    self.btn_import_color.setText(" Colormaps")
    self.btn_import_color.setIcon(self.get_icon("paint-palette.svg"))
    self.btn_import_color.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_import_color.setToolTip("Import colormaps to DDS")

    self.btn_import_detail = QToolButton()
    self.btn_import_detail.setText(" Detailmaps")
    self.btn_import_detail.setIcon(self.get_icon("layers-3.svg"))
    self.btn_import_detail.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_import_detail.setToolTip("Import detailmaps to DDS")

    self.btn_import_lowdetail = QToolButton()
    self.btn_import_lowdetail.setText(" Lowdetailmaps")
    self.btn_import_lowdetail.setIcon(self.get_icon("paint-roll-brush.svg"))
    self.btn_import_lowdetail.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    self.btn_import_lowdetail.setToolTip("Import lowdetailmaps to DDS")

    for btn in [self.btn_import_height, self.btn_import_color, self.btn_import_detail, self.btn_import_lowdetail]:
      btn.setIconSize(QSize(18, 18))
      import_buttons_layout.addWidget(btn)

    actions_layout.addLayout(import_buttons_layout)

    # --- Section 3: Preview Panel ---
    preview_header = QToolButton()
    preview_header.setText(" Preview")
    preview_header.setIcon(self.get_icon("picture.svg"))
    preview_header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    preview_header.setStyleSheet("font-weight: bold; border: none; background: transparent;")
    actions_layout.addWidget(preview_header)

    preview_controls_layout = QHBoxLayout()
    self.preview_combo = QComboBox()
    self.preview_combo.addItems([
        "Heightmap",
        "Colormap",
        "Detailmap (1)",
        "Detailmap (2)",
        "Lowdetailmap"
    ])
    self.preview_combo.currentIndexChanged.connect(self.update_preview)
    preview_controls_layout.addWidget(QLabel("    Texture type:"))
    preview_controls_layout.addWidget(self.preview_combo)
    preview_controls_layout.addStretch()
    actions_layout.addLayout(preview_controls_layout)

    # Resizable squared image viewer container
    self.preview_display = ResizablePreviewLabel()
    self.preview_display.setText("No PNG image found. Export the textures and try again.")
    self.preview_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.preview_display.setMinimumHeight(150)
    self.preview_display.setStyleSheet("border: 1px dashed #888888; border-radius: 4px; color: #888888;")
    actions_layout.addWidget(self.preview_display)

    all_action_buttons = [
        self.btn_export_height, self.btn_export_color, self.btn_export_detail, self.btn_export_lowdetail,
        self.btn_import_height, self.btn_import_color, self.btn_import_detail, self.btn_import_lowdetail
    ]
    for btn in all_action_buttons:
      btn.setEnabled(False)

    actions_layout.addStretch()
    vertical_splitter.addWidget(actions_widget)
    vertical_splitter.setSizes([200, 600])

    right_layout.addWidget(vertical_splitter)

    # Connect map operations
    self.btn_export_height.clicked.connect(lambda: self.run_async_operation(self.export_heightmaps, "Exporting heightmaps..."))
    self.btn_import_height.clicked.connect(lambda: self.run_async_operation(self.import_heightmaps, "Importing heightmaps..."))
    self.btn_export_color.clicked.connect(lambda: self.run_async_operation(self.export_colormap, "Exporting colormap..."))
    self.btn_import_color.clicked.connect(lambda: self.run_async_operation(self.import_colormap, "Importing colormap..."))
    self.btn_export_detail.clicked.connect(lambda: self.run_async_operation(self.export_detailmaps, "Exporting detailmaps..."))
    self.btn_import_detail.clicked.connect(lambda: self.run_async_operation(self.import_detailmaps, "Importing detailmaps..."))
    self.btn_export_lowdetail.clicked.connect(lambda: self.run_async_operation(self.export_lowdetailmaps, "Exporting lowdetailmaps..."))
    self.btn_import_lowdetail.clicked.connect(lambda: self.run_async_operation(self.import_lowdetailmaps, "Importing lowdetailmaps..."))

    main_splitter.addWidget(right_panel)
    main_splitter.setSizes([350, 850])

    main_layout.addWidget(main_splitter)
    self.apply_stylesheet()

  def run_async_operation(self, func, message):
    logging.info(f"Starting operation: {message}")
    self.progress_dialog = QProgressDialog(message, None, 0, 0, self)
    self.progress_dialog.setWindowTitle("Please Wait")
    self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.progress_dialog.setCancelButton(None)
    self.progress_dialog.setMinimumDuration(0)
    self.progress_dialog.setValue(0)
    self.progress_dialog.show()

    self.worker = WorkerThread(func)
    self.worker.finished.connect(lambda success, err: self.on_operation_finished(success, err, message))
    self.worker.start()

  def on_operation_finished(self, success, err, message):
    if self.progress_dialog:
      self.progress_dialog.close()
      self.progress_dialog = None

    if success:
      logging.info(f"Operation completed successfully: {message}")
      QMessageBox.information(self, "Success", f"Operation completed successfully:\n{message}")
    else:
      logging.error(f"Operation failed ({message}): {err}")
      QMessageBox.critical(self, "Error", f"Operation failed:\n{err}")

    self.on_level_selected()
    self.update_preview()

  def open_settings(self):
    dialog = SettingsDialog(self.dark_mode, self.auto_flip, self.mod_path, self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
      dark_active, auto_flip_active, path = dialog.get_settings()
      self.dark_mode = dark_active
      self.auto_flip = auto_flip_active
      self.mod_path = path
      self.settings["dark_mode"] = self.dark_mode
      self.settings["auto_flip"] = self.auto_flip
      self.settings["default_mod_folder"] = self.mod_path
      self.save_settings()
      self.init_ui()
      self.apply_stylesheet()
      self.on_level_selected()

      if self.mod_path:
        levels_dir = os.path.join(self.mod_path, "levels")
        if os.path.exists(levels_dir):
          self.levels_path = levels_dir
          self.path_input.setText(self.mod_path)
          self.load_levels()

  def apply_stylesheet(self):
    if not self.dark_mode:
      self.setStyleSheet("""
                QWidget { background-color: #f0f0f0; color: #1e1e1e; font-family: Segoe UI; font-size: 10pt; }
                QToolButton { background-color: #ffffff; border: 1px solid #cccccc; padding: 6px 10px; border-radius: 4px; color: #1e1e1e; min-width: 90px; }
                QToolButton:enabled { background-color: #ffffff; color: #1e1e1e; border: 1px solid #cccccc; }
                QToolButton:enabled:hover { background-color: #e5f3ff; border-color: #007acc; }
                QToolButton:disabled { color: #888888; background-color: #e5e5e5; }
                QPushButton { background-color: #e0e0e0; border: 1px solid #cccccc; padding: 6px; border-radius: 4px; }
                QPushButton:enabled { background-color: #007acc; color: white; border: none; }
                QPushButton:enabled:hover { background-color: #005999; }
                QPushButton:disabled { color: #888888; background-color: #e5e5e5; }
                QLineEdit, QComboBox { background-color: #ffffff; border: 1px solid #cccccc; padding: 4px; color: #000000; }
                QTableWidget { background-color: #ffffff; alternate-background-color: #f9f9f9; gridline-color: #dddddd; selection-background-color: #007acc; selection-color: white; }
                QHeaderView::section { background-color: #e1e1e1; color: #000000; padding: 4px; border: 1px solid #d0d0d0; }
                QMenuBar { background-color: #e1e1e1; color: #000000; }
                QMenuBar::item { background-color: transparent; padding: 4px 10px; }
                QMenuBar::item:selected { background-color: #007acc; color: white; }
                QMenu { background-color: #ffffff; color: #000000; border: 1px solid #cccccc; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #007acc; color: white; }
                QSplitter::handle { background-color: #cccccc; }
            """)
      self.metadata_label.setStyleSheet(
          "background-color: #ffffff; color: #1e1e1e; padding: 10px;"
          " border: 1px solid #cccccc; border-radius: 5px;"
      )
      self.files_content_widget.setStyleSheet(
          "background-color: #ffffff; border: 1px solid #cccccc;"
          " border-radius: 5px;"
      )
    else:
      self.setStyleSheet("""
                QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: Segoe UI; font-size: 10pt; }
                QToolButton { background-color: #2d2d2d; border: 1px solid #3f3f3f; padding: 6px 10px; border-radius: 4px; color: #d4d4d4; min-width: 90px; }
                QToolButton:enabled { background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #3f3f3f; }
                QToolButton:enabled:hover { background-color: #383838; border-color: #007acc; }
                QToolButton:disabled { color: #666666; background-color: #252525; }
                QPushButton { background-color: #333333; border: 1px solid #555555; padding: 6px; border-radius: 4px; }
                QPushButton:enabled { background-color: #007acc; color: white; border: none; }
                QPushButton:enabled:hover { background-color: #0098ff; }
                QPushButton:disabled { color: #666666; background-color: #252525; }
                QLineEdit, QComboBox { background-color: #2d2d2d; border: 1px solid #3f3f3f; padding: 4px; color: #ffffff; }
                QTableWidget { background-color: #252525; alternate-background-color: #2a2a2a; gridline-color: #333333; selection-background-color: #007acc; selection-color: white; }
                QHeaderView::section { background-color: #2d2d2d; color: #ffffff; padding: 4px; border: 1px solid #3f3f3f; }
                QMenuBar { background-color: #2d2d2d; color: #ffffff; }
                QMenuBar::item { background-color: transparent; padding: 4px 10px; }
                QMenuBar::item:selected { background-color: #007acc; color: white; }
                QMenu { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3f3f3f; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #007acc; color: white; }
                QSplitter::handle { background-color: #333333; }
            """)
      self.metadata_label.setStyleSheet(
          "background-color: #2b2b2b; color: #f0f0f0; padding: 10px;"
          " border-radius: 5px;"
      )
      self.files_content_widget.setStyleSheet(
          "background-color: #2b2b2b; border-radius: 5px;"
      )

  def prompt_for_mod_folder(self):
    """Ask for the mod folder when none is configured or the saved one is gone."""
    missing_path = self.mod_path
    detected_path = (
        FH2_DEFAULT_MOD_FOLDER
        if is_valid_mod_folder(FH2_DEFAULT_MOD_FOLDER)
        else None
    )

    while not is_valid_mod_folder(self.mod_path):
      box = QMessageBox(self)
      box.setIcon(QMessageBox.Icon.Information)
      box.setWindowTitle("Mod folder setup")
      if missing_path:
        box.setText("The saved mod folder could not be found.")
        details = f"{missing_path}\n\nPlease select your mod folder again."
      else:
        box.setText("Welcome to the BF2 Mod Toolkit.")
        details = (
            "Please select your mod folder"
            " (the one containing the 'levels' directory)."
        )
      if detected_path:
        details += (
            "\n\nA Forgotten Hope 2 installation was found at:"
            f"\n{detected_path}"
        )
      box.setInformativeText(details)

      detected_btn = None
      if detected_path:
        detected_btn = box.addButton(
            "Use detected folder", QMessageBox.ButtonRole.AcceptRole
        )
      browse_btn = box.addButton("Browse...", QMessageBox.ButtonRole.ActionRole)
      later_btn = box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
      box.setDefaultButton(detected_btn or browse_btn)
      box.setEscapeButton(later_btn)
      box.exec()

      clicked = box.clickedButton()
      if clicked == later_btn:
        logging.info("Mod folder setup postponed by the user.")
        return
      if clicked == detected_btn:
        self.set_mod_folder(detected_path)
      else:
        self.select_mod_folder()

  def select_mod_folder(self):
    dir_path = QFileDialog.getExistingDirectory(
        self, "Select Battlefield 2 Mod Directory", self.mod_path
    )
    if dir_path:
      if not is_valid_mod_folder(dir_path):
        QMessageBox.warning(
            self,
            "Invalid Folder",
            "The selected folder does not contain a 'levels' directory.",
        )
        return
      self.set_mod_folder(dir_path)

  def set_mod_folder(self, dir_path):
    """Make dir_path the active mod folder, persist it and list its levels."""
    self.mod_path = dir_path
    self.levels_path = os.path.join(dir_path, "levels")
    self.path_input.setText(dir_path)
    self.settings["default_mod_folder"] = dir_path
    self.save_settings()
    self.load_levels()

  def load_levels(self):
    self.levels_table.setRowCount(0)
    if not os.path.exists(self.levels_path):
      return

    levels = sorted([
        d
        for d in os.listdir(self.levels_path)
        if os.path.isdir(os.path.join(self.levels_path, d))
    ])
    self.levels_table.setRowCount(len(levels))

    for row, level_name in enumerate(levels):
      name_item = QTableWidgetItem(level_name)
      name_item.setFlags(
          Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
      )
      self.levels_table.setItem(row, 0, name_item)

  def get_selected_level_path(self):
    selected_items = self.levels_table.selectedItems()
    if not selected_items:
      return None
    row = selected_items[0].row()
    level_name = self.levels_table.item(row, 0).text()
    return os.path.join(self.levels_path, level_name)

  def on_level_selected(self):
    level_path = self.get_selected_level_path()
    has_selection = level_path is not None

    for btn in [
        self.btn_export_height,
        self.btn_import_height,
        self.btn_export_color,
        self.btn_import_color,
        self.btn_export_detail,
        self.btn_import_detail,
        self.btn_export_lowdetail,
        self.btn_import_lowdetail,
    ]:
      btn.setEnabled(has_selection)

    if not level_path:
      self.metadata_label.setText(
          "Select a level from the list to view metadata."
      )
      self.clear_files_list()
      self.preview_display.original_pixmap = None
      self.preview_display.clear()
      self.preview_display.setText("No PNG image found. Export the textures and try again.")
      return

    level_name = os.path.basename(level_path)
    size, scale = self.parse_map_metadata(level_path)

    meta_text = f"<b>Level Name:</b> {level_name}<br>"
    meta_text += f"<b>Directory:</b> {level_path}<br>"
    meta_text += f"<b>Heightmap Size:</b> {size}<br>"
    meta_text += f"<b>Terrain Scale:</b> {scale}"
    self.metadata_label.setText(meta_text)

    # Populate Files section inside scrollable layout
    self.clear_files_list()
    file_sizes = {}
    for filename in sorted(os.listdir(level_path)):
      fp = os.path.join(level_path, filename)
      if os.path.isfile(fp):
        file_sizes[filename] = os.path.getsize(fp)

    if file_sizes:
      for f, s in file_sizes.items():
        lbl = QLabel(f"• {f} ({s / 1024:.1f} KB)")
        lbl.setStyleSheet(
            "color: #d4d4d4;" if self.dark_mode else "color: #1e1e1e;"
        )
        self.files_layout.addWidget(lbl)
    else:
      lbl = QLabel("No files found in directory.")
      lbl.setStyleSheet(
          "color: #d4d4d4;" if self.dark_mode else "color: #1e1e1e;"
      )
      self.files_layout.addWidget(lbl)
    self.files_layout.addStretch()

    self.update_preview()

  def update_preview(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      self.preview_display.original_pixmap = None
      self.preview_display.clear()
      self.preview_display.setText("No PNG image found. Export the textures and try again.")
      return

    selection = self.preview_combo.currentText()
    png_path = None

    if selection == "Heightmap":
      png_path = os.path.join(level_path, "HeightmapPrimary.png")
    elif selection == "Colormap":
      png_path = os.path.join(level_path, "Editor", "Colormaps", "colormap.png")
    elif selection == "Detailmap (1)":
      png_path = os.path.join(level_path, "Editor", "Detailmaps", "detailmap_1.png")
    elif selection == "Detailmap (2)":
      png_path = os.path.join(level_path, "Editor", "Detailmaps", "detailmap_2.png")
    elif selection == "Lowdetailmap":
      png_path = os.path.join(level_path, "Editor", "lowdetailmaps", "tx_s0.png")

    if png_path and os.path.exists(png_path):
      pixmap = QPixmap(png_path)
      if not pixmap.isNull():
        self.preview_display.setPixmap(pixmap)
        return

    self.preview_display.original_pixmap = None
    self.preview_display.clear()
    self.preview_display.setText("No PNG image found. Export the textures and try again.")

  def on_level_double_clicked(self, item):
    level_path = self.get_selected_level_path()
    if level_path and os.path.exists(level_path):
      if platform.system() == "Windows":
        os.startfile(level_path)
      elif platform.system() == "Darwin":
        subprocess.run(["open", level_path])
      else:
        subprocess.run(["xdg-open", level_path])

  def clear_files_list(self):
    while self.files_layout.count():
      item = self.files_layout.takeAt(0)
      widget = item.widget()
      if widget:
        widget.deleteLater()

  def parse_map_metadata(self, level_path):
    size = "Unknown"
    scale = "Unknown"

    heightdata_file = os.path.join(level_path, "Heightdata.con")
    if os.path.exists(heightdata_file):
      try:
        with open(heightdata_file, "r", encoding="utf-8", errors="ignore") as f:
          for line in f:
            if "heightmapcluster.setHeightmapSize" in line:
              parts = line.strip().split()
              if len(parts) >= 2:
                size = parts[1]
                break
      except Exception as e:
        logging.warning(f"Error parsing heightmap metadata: {e}")

    terrain_file = os.path.join(level_path, "Terrain.con")
    if os.path.exists(terrain_file):
      try:
        with open(terrain_file, "r", encoding="utf-8", errors="ignore") as f:
          for line in f:
            if "terrain.primaryWorldScale" in line:
              parts = line.strip().split()
              if len(parts) >= 2:
                scale = parts[1]
                break
      except Exception as e:
        logging.warning(f"Error parsing terrain metadata: {e}")

    return size, scale

  # --- Texture Import / Export Operations ---

  def export_heightmaps(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    files_to_export = [
        ("HeightmapPrimary.raw", 1025, 1025, 16),
        ("HeightmapSecondary_D1.raw", 257, 257, 8),
        ("HeightmapSecondary_L1.raw", 257, 257, 8),
        ("HeightmapSecondary_L1D1.raw", 257, 257, 8),
        ("HeightmapSecondary_L1U1.raw", 257, 257, 8),
        ("HeightmapSecondary_R1.raw", 257, 257, 8),
        ("HeightmapSecondary_R1D1.raw", 257, 257, 8),
        ("HeightmapSecondary_R1U1.raw", 257, 257, 8),
        ("HeightmapSecondary_U1.raw", 257, 257, 8),
    ]

    count = 0
    for raw_name, width, height, bit_res in files_to_export:
      raw_path = os.path.join(level_path, raw_name)
      if not os.path.exists(raw_path):
        continue

      try:
        dtype = np.uint16 if bit_res == 16 else np.uint8
        data = np.fromfile(raw_path, dtype=dtype)
        if data.size != width * height:
          continue
        data = data.reshape((height, width))

        if self.auto_flip:
          data = np.flipud(data)

        if bit_res == 16:
          # A uint16 array becomes a 16-bit grayscale PNG (mode I;16),
          # preserving the full precision
          img = Image.fromarray(np.ascontiguousarray(data))
        else:
          img = Image.fromarray(data.astype(np.uint8), mode="L")

        png_name = raw_name.replace(".raw", ".png")
        out_path = os.path.join(level_path, png_name)
        img.save(out_path)
        count += 1
      except Exception as e:
        logging.error(f"Failed to export {raw_name}: {e}")
        raise e

    if count == 0:
      raise Exception("No heightmap files were found or successfully exported.")

  def import_heightmaps(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    files_to_import = [
        ("HeightmapPrimary.png", "HeightmapPrimary.raw", 1025, 1025, 16),
        ("HeightmapSecondary_D1.png", "HeightmapSecondary_D1.raw", 257, 257, 8),
        ("HeightmapSecondary_L1.png", "HeightmapSecondary_L1.raw", 257, 257, 8),
        ("HeightmapSecondary_L1D1.png", "HeightmapSecondary_L1D1.raw", 257, 257, 8),
        ("HeightmapSecondary_L1U1.png", "HeightmapSecondary_L1U1.raw", 257, 257, 8),
        ("HeightmapSecondary_R1.png", "HeightmapSecondary_R1.raw", 257, 257, 8),
        ("HeightmapSecondary_R1D1.png", "HeightmapSecondary_R1D1.raw", 257, 257, 8),
        ("HeightmapSecondary_R1U1.png", "HeightmapSecondary_R1U1.raw", 257, 257, 8),
        ("HeightmapSecondary_U1.png", "HeightmapSecondary_U1.raw", 257, 257, 8),
    ]

    count = 0
    for png_name, raw_name, width, height, bit_res in files_to_import:
      png_path = os.path.join(level_path, png_name)
      if not os.path.exists(png_path):
        continue

      try:
        img = Image.open(png_path)
        if img.size != (width, height):
          continue

        if bit_res == 16:
          if img.mode in ("I;16", "I;16B", "I"):
            data = np.array(img).astype(np.uint16)
          else:
            # 8-bit source: scale up to the 16-bit range
            data = np.array(img.convert("L")).astype(np.uint16) << 8
        else:
          data = np.array(img.convert("L")).astype(np.uint8)

        if self.auto_flip:
          data = np.flipud(data)

        raw_path = os.path.join(level_path, raw_name)
        np.ascontiguousarray(data).tofile(raw_path)

        count += 1
      except Exception as e:
        logging.error(f"Failed to import {png_name}: {e}")
        raise e

    if count == 0:
      raise Exception("No matching PNG heightmap files found in level folder to import.")

  def export_colormap(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    colormaps_dir = os.path.join(level_path, "Editor", "Colormaps")
    if not os.path.exists(colormaps_dir):
      raise Exception("Editor/Colormaps folder not found in level.")

    # Respect the auto_flip setting for the final canvas
    master_img = stitch_patches(colormaps_dir, "tx{col:02d}x{row:02d}.dds", self.auto_flip)
    master_img.save(os.path.join(colormaps_dir, "colormap.png"), compress_level=PNG_COMPRESS_LEVEL)

  def import_colormap(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    colormaps_dir = os.path.join(level_path, "Editor", "Colormaps")
    open_path = os.path.join(colormaps_dir, "colormap.png")
    if not os.path.exists(open_path):
      raise Exception("colormap.png not found inside Editor/Colormaps/")

    img = Image.open(open_path).convert("RGBA")
    if img.size != (4096, 4096):
      raise Exception("colormap.png must be exactly 4096x4096 pixels.")

    # The editor expects colormap patches as DXT5 (BC3), requires Pillow >= 11.2.1
    unstitch_patches(img, colormaps_dir, "tx{col:02d}x{row:02d}.dds", self.auto_flip, pixel_format="DXT5")

  def export_detailmaps(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    detailmaps_dir = os.path.join(level_path, "Editor", "Detailmaps")
    if not os.path.exists(detailmaps_dir):
      raise Exception("Editor/Detailmaps folder not found in level.")

    def export_layer(layer):
      master_img = stitch_patches(detailmaps_dir, f"tx{{col:02d}}x{{row:02d}}_{layer}.dds", self.auto_flip)
      master_img.save(os.path.join(detailmaps_dir, f"detailmap_{layer}.png"), compress_level=PNG_COMPRESS_LEVEL)

    # Both layers run concurrently so their PNG saves overlap
    run_in_parallel([lambda layer=layer: export_layer(layer) for layer in (1, 2)])

  def import_detailmaps(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    detailmaps_dir = os.path.join(level_path, "Editor", "Detailmaps")
    if not os.path.exists(detailmaps_dir):
      raise Exception("Editor/Detailmaps folder not found.")

    def import_layer(layer):
      png_path = os.path.join(detailmaps_dir, f"detailmap_{layer}.png")
      if not os.path.exists(png_path):
        return False

      img = Image.open(png_path).convert("RGBA")
      if img.size != (4096, 4096):
        return False

      # RGBA mode makes Pillow write uncompressed 32-bit A8R8G8B8, as the editor expects
      unstitch_patches(img, detailmaps_dir, f"tx{{col:02d}}x{{row:02d}}_{layer}.dds", self.auto_flip)
      return True

    # Both layers run concurrently so their PNG loads overlap
    imported = run_in_parallel([lambda layer=layer: import_layer(layer) for layer in (1, 2)])
    if not any(imported):
      raise Exception("No valid detailmap_1.png or detailmap_2.png found to import.")

  def export_lowdetailmaps(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    lowdetail_dir = os.path.join(level_path, "Editor", "lowdetailmaps")
    if not os.path.exists(lowdetail_dir):
      raise Exception("Editor/lowdetailmaps folder not found in level.")

    count = 0
    for i in range(8):
      patch_name = f"tx_s{i}.dds"
      patch_path = os.path.join(lowdetail_dir, patch_name)
      if os.path.exists(patch_path):
        try:
          img = read_dds_rgba(patch_path)
          if self.auto_flip:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
          img.save(os.path.join(lowdetail_dir, f"tx_s{i}.png"))
          count += 1
        except Exception as e:
          logging.warning(f"Could not export tx_s{i}.dds: {e}")

    if count == 0:
      raise Exception("No lowdetailmap files found to export.")

  def import_lowdetailmaps(self):
    level_path = self.get_selected_level_path()
    if not level_path:
      return

    lowdetail_dir = os.path.join(level_path, "Editor", "lowdetailmaps")
    if not os.path.exists(lowdetail_dir):
      raise Exception("Editor/lowdetailmaps folder not found.")

    count = 0
    for i in range(8):
      png_name = f"tx_s{i}.png"
      png_path = os.path.join(lowdetail_dir, png_name)
      if os.path.exists(png_path):
        try:
          img = Image.open(png_path).convert("RGBA")
          if img.size != (512, 512):
            continue
          if self.auto_flip:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

          patch_path = os.path.join(lowdetail_dir, f"tx_s{i}.dds")
          # RGBA mode makes Pillow write uncompressed 32-bit A8R8G8B8, as the editor expects
          img.save(patch_path, format="DDS")
          count += 1
        except Exception as e:
          logging.warning(f"Could not import tx_s{i}.png: {e}")

    if count == 0:
      raise Exception("No lowdetailmap PNGs found to import.")


if __name__ == "__main__":
  app = QApplication(sys.argv)
  toolkit = BF2ModToolkitApp()
  toolkit.show()
  sys.exit(app.exec())