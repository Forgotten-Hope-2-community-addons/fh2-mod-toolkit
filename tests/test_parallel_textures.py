"""Tests for the parallel patch stitching helpers in main.py.

 - read_dds_rgba must return exactly what Pillow returns, both on the NumPy
   fast path (uncompressed A8R8G8B8) and on the Pillow fallback (DXT5).
 - unstitch_patches followed by stitch_patches must reproduce the canvas,
   with and without auto_flip, so threading never reorders or misplaces patches.

Run with: python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main  # noqa: E402

NAME_FMT = "tx{col:02d}x{row:02d}_1.dds"


def random_rgba(size, seed=0):
  rng = np.random.default_rng(seed)
  return Image.fromarray(rng.integers(0, 256, (size, size, 4), dtype=np.uint8), mode="RGBA")


class ReadDdsRgbaTests(unittest.TestCase):

  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)

  def assert_matches_pillow(self, path):
    expected = np.array(Image.open(path).convert("RGBA"))
    actual = main.read_dds_rgba(path)
    self.assertEqual(actual.mode, "RGBA")
    np.testing.assert_array_equal(np.array(actual), expected)

  def test_uncompressed_fast_path(self):
    path = os.path.join(self.tmp.name, "raw.dds")
    random_rgba(64).save(path, format="DDS")
    self.assert_matches_pillow(path)

  def test_non_square_uncompressed(self):
    path = os.path.join(self.tmp.name, "wide.dds")
    rng = np.random.default_rng(1)
    Image.fromarray(rng.integers(0, 256, (16, 48, 4), dtype=np.uint8), mode="RGBA").save(path, format="DDS")
    self.assert_matches_pillow(path)

  def test_dxt5_falls_back_to_pillow(self):
    path = os.path.join(self.tmp.name, "dxt5.dds")
    random_rgba(64).save(path, format="DDS", pixel_format="DXT5")
    self.assert_matches_pillow(path)


class StitchRoundTripTests(unittest.TestCase):

  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.canvas = random_rgba(main.PATCH_SIZE * main.PATCH_GRID, seed=2)

  def test_round_trip(self):
    for auto_flip in (False, True):
      with self.subTest(auto_flip=auto_flip):
        main.unstitch_patches(self.canvas, self.tmp.name, NAME_FMT, auto_flip)
        result = main.stitch_patches(self.tmp.name, NAME_FMT, auto_flip)
        np.testing.assert_array_equal(np.array(result), np.array(self.canvas))

  def test_patch_placement(self):
    # Patch tx00x00 is the bottom-left tile of the canvas, stored vertically flipped
    main.unstitch_patches(self.canvas, self.tmp.name, NAME_FMT, auto_flip=False)
    size = main.PATCH_SIZE
    full = size * main.PATCH_GRID
    expected = np.array(self.canvas)[full - size:, :size][::-1]
    patch = np.array(main.read_dds_rgba(os.path.join(self.tmp.name, "tx00x00_1.dds")))
    np.testing.assert_array_equal(patch, expected)

  def test_missing_patches_stay_blank(self):
    main.unstitch_patches(self.canvas, self.tmp.name, NAME_FMT, auto_flip=False)
    os.remove(os.path.join(self.tmp.name, "tx03x05_1.dds"))
    result = np.array(main.stitch_patches(self.tmp.name, NAME_FMT, auto_flip=False))
    size = main.PATCH_SIZE
    dst_row = main.PATCH_GRID - 1 - 5
    tile = result[dst_row * size:(dst_row + 1) * size, 3 * size:4 * size]
    self.assertFalse(tile.any())


if __name__ == "__main__":
  unittest.main()
