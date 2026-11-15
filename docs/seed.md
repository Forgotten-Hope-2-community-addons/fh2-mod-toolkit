## Battlefield 2 Mod Toolkit

We'll work on the map operations, specially on the export and import operations.

These operations are meant to export DDS and RAW files used by the engine to PNG files.

Every terrain texture in BF2 (heightmaps, colormaps, shadowmaps, detailmaps, minimap, etc) is stored flipped over the Y-axis  (vertically). This operations needs to be done on every export and import operation to do and undo the flipping. This is customizable in the settings, enable by default (`auto_flip: true|false`).

More details at view-source:https://forgottenhope.warumdarum.de/tutorials/heightmaps.php

## Heightmaps

| Game File                   | Exported File               |
| --------------------------- | --------------------------- |
| HeightmapPrimary.raw        | HeightmapPrimary.png        |
| HeightmapSecondary_D1.raw   | HeightmapSecondary_D1.png   |
| HeightmapSecondary_L1.raw   | HeightmapSecondary_L1.png   |
| HeightmapSecondary_L1D1.raw | HeightmapSecondary_L1D1.png |
| HeightmapSecondary_L1U1.raw | HeightmapSecondary_L1U1.png |
| HeightmapSecondary_R1.raw   | HeightmapSecondary_R1.png   |
| HeightmapSecondary_R1D1.raw | HeightmapSecondary_R1D1.png |
| HeightmapSecondary_R1U1.raw | HeightmapSecondary_R1U1.png |
| HeightmapSecondary_U1.raw   | HeightmapSecondary_U1.png   |

A heightmap is nothing more than a gray scale image. Each pixel of the image represents one point, or vertex, in the terrain mesh. The height of each vertex is determined by the value of its corresponding pixel in the image. In other words, the “whiter” the pixel, the higher the terrain at that point.

The heightmap sizes are described in the `Heightdata.con` file:

```lua
rem --- primary ---
heightmapcluster.addHeightmap Heightmap 0 0
heightmap.setSize 1025 1025
heightmap.setScale 2/0.00114441/2
heightmap.setBitResolution 16
heightmap.setModified 1
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapPrimary.raw
heightmap.setMaterialScale 1
heightmap.loadMaterialData Levels/cmp_t_raseiniai/HeightmapPrimary.mat

rem --- secondary ---
heightmapcluster.addHeightmap Heightmap -1 -1
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_L1U1.raw
heightmapcluster.addHeightmap Heightmap 0 -1
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_U1.raw
heightmapcluster.addHeightmap Heightmap 1 -1
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_R1U1.raw

heightmapcluster.addHeightmap Heightmap -1 0
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_L1.raw
heightmapcluster.addHeightmap Heightmap 1 0
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 1
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_R1.raw

heightmapcluster.addHeightmap Heightmap -1 1
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_L1D1.raw
heightmapcluster.addHeightmap Heightmap 0 1
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_D1.raw
heightmapcluster.addHeightmap Heightmap 1 1
heightmap.setSize 257 257
heightmap.setScale 8/0.292969/8
heightmap.setBitResolution 8
heightmap.setModified 0
heightmap.loadHeightData Levels/cmp_t_raseiniai/HeightmapSecondary_R1D1.raw
```

### Primary

- Channels count: 1
- Depth: 16 bits.
- Byte Order: IBM PC

### Secondary

In BF2 there are 8 “secondary meshes” that surround the main mesh of your map. The purpose of this is to provide the game with additional terrain that you can see, but never actually get to.

- Channels count: 1
- Depth: 8 bits
- Byte Order: None/IBM PC

## Colormaps

Present under the Editor/Colormaps folder. Every primary terrain DDS file there has these properties (see [formats.md](formats.md) for the full `ddsinfo` captures):

- Size 512x512. 
- DXT5 (BC3). 
- No mipmaps.

The secondary terrain files (`tx_s*.dds`) are DXT1 (BC1) with all mipmaps.

64 DDS files for the primary terrain.

- tx00x00.dds
- tx00x01.dds
- tx00x02.dds
- tx00x03.dds
- tx00x04.dds
- tx00x05.dds
- tx00x06.dds
- tx00x07.dds
- tx01x00.dds
- tx01x01.dds
- tx01x02.dds
- tx01x03.dds
- tx01x04.dds
- tx01x05.dds
- tx01x06.dds
- tx01x07.dds
- tx02x00.dds
- tx02x01.dds
- tx02x02.dds
- tx02x03.dds
- tx02x04.dds
- tx02x05.dds
- tx02x06.dds
- tx02x07.dds
- tx03x00.dds
- tx03x01.dds
- tx03x02.dds
- tx03x03.dds
- tx03x04.dds
- tx03x05.dds
- tx03x06.dds
- tx03x07.dds
- tx04x00.dds
- tx04x01.dds
- tx04x02.dds
- tx04x03.dds
- tx04x04.dds
- tx04x05.dds
- tx04x06.dds
- tx04x07.dds
- tx05x00.dds
- tx05x01.dds
- tx05x02.dds
- tx05x03.dds
- tx05x04.dds
- tx05x05.dds
- tx05x06.dds
- tx05x07.dds
- tx06x00.dds
- tx06x01.dds
- tx06x02.dds
- tx06x03.dds
- tx06x04.dds
- tx06x05.dds
- tx06x06.dds
- tx06x07.dds
- tx07x00.dds
- tx07x01.dds
- tx07x02.dds
- tx07x03.dds
- tx07x04.dds
- tx07x05.dds
- tx07x06.dds
- tx07x07.dds


8 DDS files for the secondary terrain (not processed yet).
- tx_s0.dds
- tx_s1.dds
- tx_s2.dds
- tx_s3.dds
- tx_s4.dds
- tx_s5.dds
- tx_s6.dds
- tx_s7.dds

| Game File                    | Exported File                 |
| ---------------------------- | ----------------------------- |
| Editor/Colormaps/<patch>.dds | -                             |
| -                            | Editor/Colormaps/colormap.png |
<!-- | -                            | Editor/Colormaps/colormap_big.png | -->

`colormap.png` is cover the primary terrain, composed by the 64 patches (matrix).
<!-- `colormap_big.png` is the full terrain, composed by the 64 primary patches and the 8 secondary patches. -->

<!-- Both files are exported and imported. -->

The export operation must:
 - Read the 64 patches for the primary terrain.
 - Compose the final image. Size is 512*8=4096x4096 pixels.
 - Write the final image (flipped).

The import operation must:
 - Read the `colormap.png` file.
 - Check the file size matches the heightmap size. Usually, 4096 (opposite operation as in export).
 - Flip the source image.
 - Divide the source image into 64 DDS patches.
 - Write the 64 DDS images to the game file location: `Editor/Colormaps/<patch>.dds`.

The image is composed as a matrix of the 64 DDS images, in the following order (before flipping):

00x00  ...  ... 00x07
 ...   ...  ...  ...
07x00  ...  ... 07x07
 
## Detailmaps

RGBA textures (the alpha channel carries data and must be preserved). Unlike colormaps, detailmaps use 6 layers, so they are _1 and _2 patch textures, and translate to

Present under the Editor/Detailmaps folder. Every DDS file there has these properties (see [formats.md](formats.md)):

- Size 512x512. 
- Uncompressed 32-bit A8R8G8B8. 
- No mipmaps.

128 DDS files for the primary terrain.

- tx00x00_1.dds
- tx00x00_2.dds
- tx00x01_1.dds
- tx00x01_2.dds
- tx00x02_1.dds
- tx00x02_2.dds
- tx00x03_1.dds
- tx00x03_2.dds
- tx00x04_1.dds
- tx00x04_2.dds
- tx00x05_1.dds
- tx00x05_2.dds
- tx00x06_1.dds
- tx00x06_2.dds
- tx00x07_1.dds
- tx00x07_2.dds
- tx01x00_1.dds
- tx01x00_2.dds
- tx01x01_1.dds
- tx01x01_2.dds
- tx01x02_1.dds
- tx01x02_2.dds
- tx01x03_1.dds
- tx01x03_2.dds
- tx01x04_1.dds
- tx01x04_2.dds
- tx01x05_1.dds
- tx01x05_2.dds
- tx01x06_1.dds
- tx01x06_2.dds
- tx01x07_1.dds
- tx01x07_2.dds
- tx02x00_1.dds
- tx02x00_2.dds
- tx02x01_1.dds
- tx02x01_2.dds
- tx02x02_1.dds
- tx02x02_2.dds
- tx02x03_1.dds
- tx02x03_2.dds
- tx02x04_1.dds
- tx02x04_2.dds
- tx02x05_1.dds
- tx02x05_2.dds
- tx02x06_1.dds
- tx02x06_2.dds
- tx02x07_1.dds
- tx02x07_2.dds
- tx03x00_1.dds
- tx03x00_2.dds
- tx03x01_1.dds
- tx03x01_2.dds
- tx03x02_1.dds
- tx03x02_2.dds
- tx03x03_1.dds
- tx03x03_2.dds
- tx03x04_1.dds
- tx03x04_2.dds
- tx03x05_1.dds
- tx03x05_2.dds
- tx03x06_1.dds
- tx03x06_2.dds
- tx03x07_1.dds
- tx03x07_2.dds
- tx04x00_1.dds
- tx04x00_2.dds
- tx04x01_1.dds
- tx04x01_2.dds
- tx04x02_1.dds
- tx04x02_2.dds
- tx04x03_1.dds
- tx04x03_2.dds
- tx04x04_1.dds
- tx04x04_2.dds
- tx04x05_1.dds
- tx04x05_2.dds
- tx04x06_1.dds
- tx04x06_2.dds
- tx04x07_1.dds
- tx04x07_2.dds
- tx05x00_1.dds
- tx05x00_2.dds
- tx05x01_1.dds
- tx05x01_2.dds
- tx05x02_1.dds
- tx05x02_2.dds
- tx05x03_1.dds
- tx05x03_2.dds
- tx05x04_1.dds
- tx05x04_2.dds
- tx05x05_1.dds
- tx05x05_2.dds
- tx05x06_1.dds
- tx05x06_2.dds
- tx05x07_1.dds
- tx05x07_2.dds
- tx06x00_1.dds
- tx06x00_2.dds
- tx06x01_1.dds
- tx06x01_2.dds
- tx06x02_1.dds
- tx06x02_2.dds
- tx06x03_1.dds
- tx06x03_2.dds
- tx06x04_1.dds
- tx06x04_2.dds
- tx06x05_1.dds
- tx06x05_2.dds
- tx06x06_1.dds
- tx06x06_2.dds
- tx06x07_1.dds
- tx06x07_2.dds
- tx07x00_1.dds
- tx07x00_2.dds
- tx07x01_1.dds
- tx07x01_2.dds
- tx07x02_1.dds
- tx07x02_2.dds
- tx07x03_1.dds
- tx07x03_2.dds
- tx07x04_1.dds
- tx07x04_2.dds
- tx07x05_1.dds
- tx07x05_2.dds
- tx07x06_1.dds
- tx07x06_2.dds
- tx07x07_1.dds
- tx07x07_2.dds

| Game File                     | Exported File                     |
| ----------------------------- | --------------------------------- |
| Editor/Detailmaps/<patch>.dds | -                                 |
| -                             | Editor/Detailmaps/detailmap_1.png |
| -                             | Editor/Detailmaps/detailmap_2.png |

Both files are exported and imported.

The export operation must:
 - For both, the `_1` and `_2` images, do:
 - Read the corresponding 64 patches for `_x`.
 - Compose the final image. Size is 512*8=4096x4096 pixels.
 - Write the final image `detailmap_x.png` (flipped).

The import operation must:
 - Read the `detailmap_x.png` file.
 - Check the file size matches the heightmap size. Usually, 4096.
 - Flip the source image.
 - Divide the source image into 64 DDS patches.
 - Write the 64 DDS images to the game file location: `Editor/Detailmaps/<patch>_x.dds`.

The image is composed as a matrix of the 64 DDS images, in the following order (before flipping):

00x00  ...  ... 00x07
 ...   ...  ...  ...
07x00  ...  ... 07x07

## Lowdetailmaps

RGBA textures (the alpha channel carries data and must be preserved).

Present under the Editor/lowdetailmaps folder. Every DDS file there has these properties (see [formats.md](formats.md)):

- Size 512x512. 
- Uncompressed 32-bit A8R8G8B8. 
- 1 mipmap.

8 DDS files for the primary terrain.

- tx_s0.dds
- tx_s1.dds
- tx_s2.dds
- tx_s3.dds
- tx_s4.dds
- tx_s5.dds
- tx_s6.dds
- tx_s7.dds

| Game File                     | Exported File                     |
| ----------------------------- | --------------------------------- |
| Editor/lowdetailmaps/<patch>.dds | -                                 |
| -                             | Editor/lowdetailmaps/<patch>.png |

The export operation must:
 - Read the 8 patches for the secondary terrain.
 - Write the 8 patches in PNG (flipped).

The import operation must:
 - Read each `<patch>.png` file.
 - Check the file size is 512.
 - Flip the source image.
 - Write the DDS image to the game file location: `Editor/lowdetailmaps/<patch>.dds`.
