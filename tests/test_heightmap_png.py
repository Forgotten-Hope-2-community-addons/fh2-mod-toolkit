"""Tests for the PNG formats used by the heightmap import and export operations.

The primary heightmap is 16-bit raw data, exported as a 16-bit grayscale
PNG (Pillow mode I;16) so no precision is lost in the round trip. The
secondary heightmaps are 8-bit, exported as regular grayscale PNG.

Run with: python -m unittest discover tests
"""

import os
import tempfile
import unittest

import numpy as np
from PIL import Image


class HeightmapPNGTest(unittest.TestCase):
  """Verifies the PNG round-trip contract main.py depends on."""

  @classmethod
  def setUpClass(cls):
    cls.tmp_dir = tempfile.TemporaryDirectory()

  @classmethod
  def tearDownClass(cls):
    cls.tmp_dir.cleanup()

  def _path(self, name):
    return os.path.join(self.tmp_dir.name, name)

  def test_16bit_round_trip_is_lossless(self):
    """uint16 data -> I;16 PNG -> uint16 data must be exact.

    This mirrors the export and import paths of the primary heightmap
    (1025x1025, 16-bit). A gradient covering the full 0-65535 range
    would be destroyed by any 8-bit truncation.
    """
    data = np.arange(1025 * 1025, dtype=np.uint32) % 65536
    data = data.astype(np.uint16).reshape((1025, 1025))

    path = self._path("heightmap16.png")
    # A uint16 array is saved as mode I;16 (Pillow infers it; passing
    # mode explicitly is rejected since Pillow 13).
    Image.fromarray(np.ascontiguousarray(data)).save(path)

    img = Image.open(path)
    self.assertIn(img.mode, ("I;16", "I;16B", "I"),
                  "16-bit PNG must load as a 16-bit or 32-bit integer mode")
    back = np.array(img).astype(np.uint16)

    self.assertEqual(back.dtype, np.uint16)
    self.assertEqual(back.shape, (1025, 1025))
    np.testing.assert_array_equal(back, data)

  def test_16bit_round_trip_survives_flip(self):
    """The auto_flip path (np.flipud) must not corrupt 16-bit data."""
    rng = np.random.default_rng(42)
    data = rng.integers(0, 65536, size=(257, 257), dtype=np.uint16)

    path = self._path("heightmap16_flip.png")
    flipped = np.flipud(data)
    Image.fromarray(np.ascontiguousarray(flipped)).save(path)

    back = np.array(Image.open(path)).astype(np.uint16)
    np.testing.assert_array_equal(np.flipud(back), data)

  def test_8bit_round_trip_is_lossless(self):
    """uint8 data -> L PNG -> uint8 data must be exact.

    This mirrors the export and import paths of the secondary
    heightmaps (257x257, 8-bit).
    """
    data = (np.arange(257 * 257, dtype=np.uint32) % 256)
    data = data.astype(np.uint8).reshape((257, 257))

    path = self._path("heightmap8.png")
    Image.fromarray(data, mode="L").save(path)

    back = np.array(Image.open(path).convert("L")).astype(np.uint8)
    np.testing.assert_array_equal(back, data)

  def test_8bit_source_scales_to_16bit_range(self):
    """An 8-bit PNG imported as a 16-bit heightmap is scaled, not truncated.

    This mirrors the import fallback for legacy 8-bit exports of the
    primary heightmap: values are shifted into the upper byte so the
    terrain keeps its overall height.
    """
    data = np.full((16, 16), 200, dtype=np.uint8)
    path = self._path("legacy8.png")
    Image.fromarray(data, mode="L").save(path)

    img = Image.open(path)
    scaled = np.array(img.convert("L")).astype(np.uint16) << 8
    self.assertEqual(scaled.dtype, np.uint16)
    self.assertTrue((scaled == 200 << 8).all())


if __name__ == "__main__":
  unittest.main()
