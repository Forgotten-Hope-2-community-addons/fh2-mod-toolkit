"""Tests for the DDS formats written by the texture import operations.

The BF2 editor only loads specific DDS formats (see docs/formats.md):
 - Colormaps (regular): DXT5/BC3 compressed, legacy header, no mipmaps.
 - Detailmaps and lowdetailmaps: uncompressed 32-bit A8R8G8B8, no mipmaps.

These tests verify that Pillow produces exactly those formats from the
save calls used in main.py, so a Pillow upgrade or a code change that
silently alters the output format is caught before it breaks levels.

Run with: python -m unittest discover tests
"""

import os
import struct
import tempfile
import unittest

from PIL import Image

# Expected bitmasks for the uncompressed editor format (A8R8G8B8),
# as captured by ddsinfo in docs/formats.md.
A8R8G8B8_MASKS = {
    "bits": 32,
    "r": 0x00FF0000,
    "g": 0x0000FF00,
    "b": 0x000000FF,
    "a": 0xFF000000,
}

DDPF_ALPHAPIXELS = 0x1
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40


def parse_dds_header(path):
  """Parse the fields of a legacy 128-byte DDS header we care about."""
  with open(path, "rb") as f:
    header = f.read(128)
  height, width = struct.unpack_from("<II", header, 12)
  mip_count = struct.unpack_from("<I", header, 28)[0]
  pf_flags, fourcc = struct.unpack_from("<I4s", header, 80)
  bits, r, g, b, a = struct.unpack_from("<IIIII", header, 88)
  return {
      "magic": header[:4],
      "width": width,
      "height": height,
      "mip_count": mip_count,
      "pf_flags": pf_flags,
      "fourcc": fourcc,
      "bits": bits,
      "r": r,
      "g": g,
      "b": b,
      "a": a,
  }


class DDSFormatTest(unittest.TestCase):
  """Verifies the DDS output contract main.py depends on."""

  @classmethod
  def setUpClass(cls):
    cls.tmp_dir = tempfile.TemporaryDirectory()
    cls.img = Image.new("RGBA", (512, 512), (120, 80, 40, 200))

  @classmethod
  def tearDownClass(cls):
    cls.tmp_dir.cleanup()

  def _path(self, name):
    return os.path.join(self.tmp_dir.name, name)

  def test_rgba_saves_as_uncompressed_a8r8g8b8(self):
    """RGBA mode + save(format="DDS") must yield 32-bit A8R8G8B8.

    This is the format used for detailmaps and lowdetailmaps.
    """
    path = self._path("uncompressed.dds")
    self.img.save(path, format="DDS")

    h = parse_dds_header(path)
    self.assertEqual(h["magic"], b"DDS ")
    self.assertEqual((h["width"], h["height"]), (512, 512))
    self.assertLessEqual(h["mip_count"], 1, "editor files must have no mipmap chain")
    self.assertTrue(h["pf_flags"] & DDPF_RGB, "DDPF_RGB flag missing")
    self.assertTrue(h["pf_flags"] & DDPF_ALPHAPIXELS, "DDPF_ALPHAPIXELS flag missing")
    self.assertFalse(h["pf_flags"] & DDPF_FOURCC, "must be uncompressed, not FourCC")
    self.assertEqual(h["bits"], A8R8G8B8_MASKS["bits"])
    self.assertEqual(h["r"], A8R8G8B8_MASKS["r"])
    self.assertEqual(h["g"], A8R8G8B8_MASKS["g"])
    self.assertEqual(h["b"], A8R8G8B8_MASKS["b"])
    self.assertEqual(h["a"], A8R8G8B8_MASKS["a"])

  def test_rgb_mode_would_break_the_format(self):
    """Guards against reintroducing the convert("RGB") bug.

    An RGB-mode image produces a 24-bit DDS without alpha, which the
    engine does not load.
    """
    path = self._path("rgb.dds")
    self.img.convert("RGB").save(path, format="DDS")

    h = parse_dds_header(path)
    self.assertNotEqual(h["bits"], 32)
    self.assertEqual(h["a"], 0)

  def test_dxt5_saves_as_legacy_bc3(self):
    """RGBA mode + pixel_format="DXT5" must yield a legacy DXT5 header.

    This is the format used for regular colormap patches. Requires
    Pillow >= 11.2.1.
    """
    path = self._path("dxt5.dds")
    self.img.save(path, format="DDS", pixel_format="DXT5")

    h = parse_dds_header(path)
    self.assertEqual(h["magic"], b"DDS ")
    self.assertEqual((h["width"], h["height"]), (512, 512))
    self.assertLessEqual(h["mip_count"], 1, "editor files must have no mipmap chain")
    self.assertTrue(h["pf_flags"] & DDPF_FOURCC)
    self.assertEqual(h["fourcc"], b"DXT5", "must be legacy DXT5, not a DX10 header")

  def test_uncompressed_round_trip_is_lossless(self):
    path = self._path("roundtrip_uncompressed.dds")
    self.img.save(path, format="DDS")
    back = Image.open(path).convert("RGBA")
    self.assertEqual(back.getpixel((0, 0)), (120, 80, 40, 200))
    self.assertEqual(back.getpixel((511, 511)), (120, 80, 40, 200))

  def test_dxt5_round_trip_preserves_alpha_and_color(self):
    path = self._path("roundtrip_dxt5.dds")
    self.img.save(path, format="DDS", pixel_format="DXT5")
    back = Image.open(path).convert("RGBA")
    pixel = back.getpixel((0, 0))
    # DXT5 is lossy on color (5:6:5 endpoints), so allow a small delta.
    for got, expected in zip(pixel[:3], (120, 80, 40)):
      self.assertAlmostEqual(got, expected, delta=8)
    # Alpha endpoints are 8-bit, a uniform alpha must survive exactly.
    self.assertEqual(pixel[3], 200)


if __name__ == "__main__":
  unittest.main()
