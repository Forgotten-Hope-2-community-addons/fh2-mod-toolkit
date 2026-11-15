## DDS formats

The formats shown here were extracted from a level's colormaps and detailmaps DDS files using the `ddsinfo` tool from the [NVIDIA Texture Tools Exporter](https://developer.nvidia.com/texture-tools-exporter) standalone application.

The import operations of the toolkit must reproduce the editor file formats listed below. In summary:

| Texture type              | Editor DDS format                        | Written by the toolkit as                       |
| ------------------------- | ---------------------------------------- | ----------------------------------------------- |
| Colormaps (regular)       | BC3/DXT5 compressed, 1 mip               | `save(format="DDS", pixel_format="DXT5")`       |
| Colormaps (surrounding)   | BC1/DXT1 compressed, 10 mips             | not processed yet                               |
| Detailmaps                | Uncompressed 32-bit A8R8G8B8, 1 mip      | RGBA image + `save(format="DDS")`               |
| Lowdetailmaps             | Uncompressed 32-bit A8R8G8B8, 1 mip      | RGBA image + `save(format="DDS")`               |

Two requirements follow from this:

- Pillow >= 11.2.1 is required, since compressed DDS saving (the `pixel_format` argument) was added in that release.
- The alpha channel must be preserved through the whole round trip: images are loaded and exported as RGBA (not RGB), and the intermediate PNG files keep the alpha channel. Converting to RGB would make Pillow write a 24-bit DDS without alpha, which the engine does not load.

### Editor files

#### Colormaps

##### Regular
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
DXGI format: BC3_UNORM_SRGB (78)
Mips: 1
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

##### Surrounding terrain
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
DXGI format: BC1_UNORM_SRGB (72)
Mips: 10
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

#### Detailmaps
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
Format: Bitmasked
	RGB bit count: 32
	Red bitmask: 0xff0000
	Green bitmask: 0xff00
	Blue bitmask: 0xff
	Alpha bitmask: 0xff000000
	Is YUV: false
	Is luminance: false
	Has alpha: true
	Has RGB: true
	Is Bump DuDv: false
Mips: 1
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

#### Lowdetailmaps

##### Regular
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
Format: Bitmasked
	RGB bit count: 32
	Red bitmask: 0xff0000
	Green bitmask: 0xff00
	Blue bitmask: 0xff
	Alpha bitmask: 0xff000000
	Bytes per scanline: 1048576
	Is YUV: false
	Is luminance: false
	Has alpha: true
	Has RGB: true
	Is Bump DuDv: false
Mips: 1
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

##### Surrounding terrain
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
Format: Bitmasked
	RGB bit count: 32
	Red bitmask: 0xff0000
	Green bitmask: 0xff00
	Blue bitmask: 0xff
	Alpha bitmask: 0xff000000
	Bytes per scanline: 1048576
	Is YUV: false
	Is luminance: false
	Has alpha: true
	Has RGB: true
	Is Bump DuDv: false
Mips: 1
Array elements: 1
Cubemap: false
Alpha mode: Straight
```


### Game files

#### Colormaps

##### Regular
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
DXGI format: BC1_UNORM_SRGB (72)
Mips: 10
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

##### Surrounding terrain
```
DDS file, no DXT10 extension.
Extent: 512 x 512 x 1 px
DXGI format: BC1_UNORM_SRGB (72)
Mips: 10
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

#### Detailmaps
```
DDS file, no DXT10 extension.
Extent: 256 x 256 x 1 px
Format: Bitmasked
	RGB bit count: 16
	Red bitmask: 0xf800
	Green bitmask: 0x7e0
	Blue bitmask: 0x1f
	Alpha bitmask: 0x0
	Bytes per scanline: 131072
	Is YUV: false
	Is luminance: false
	Has alpha: false
	Has RGB: false
	Is Bump DuDv: false
Mips: 1
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

#### Lowdetailmaps

##### Regular
```
DDS file, no DXT10 extension.
Extent: 256 x 256 x 1 px
DXGI format: BC1_UNORM_SRGB (72)
Mips: 9
Array elements: 1
Cubemap: false
Alpha mode: Straight
```

##### Surrounding terrain
```
DDS file, no DXT10 extension.
Extent: 256 x 256 x 1 px
DXGI format: BC1_UNORM_SRGB (72)
Mips: 9
Array elements: 1
Cubemap: false
Alpha mode: Straight
```