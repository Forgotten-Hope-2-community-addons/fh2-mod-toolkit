## Texture processing performance

Colormaps and detailmaps are stored by the editor as an 8x8 grid of 512x512 DDS patches (`tx{col}x{row}.dds`). Exporting stitches the 64 patches into a single 4096x4096 PNG, and importing splits the PNG back into patches (see [formats](formats.md) for the DDS formats involved). These operations used to process each patch one after the other, and exporting detailmaps was especially slow.

### Results

Measured on a test level with a 4096x4096 colormap and both detailmap layers (24-core CPU, Pillow 13.0, Python 3.12):

| Operation          | Before  | After  | Speed-up |
| ------------------ | ------- | ------ | -------- |
| Import colormap    | 0.9 s   | 0.35 s | ~2.5x    |
| Import detailmaps  | 0.95 s  | 0.4 s  | ~2.4x    |
| Export colormap    | 2.5 s   | 0.8 s  | ~3x      |
| Export detailmaps  | 33.8 s  | 1.0 s  | ~34x     |

The files produced are unchanged: the DDS patches written by the imports are byte-identical to the previous version, and the exported PNGs have exactly the same pixels, with `auto_flip` both enabled and disabled.

### What was slow

Profiling each step separately showed three costs:

1. **Uncompressed DDS reads (the big one)**. Detailmaps and lowdetailmaps are uncompressed 32-bit A8R8G8B8. Pillow decodes this format (any DDS described by bitmasks) with `DdsRgbDecoder`, a decoder written in pure Python that processes the image pixel by pixel. That is about 0.25 s per 512x512 patch, so 128 patches took over 30 seconds. Because it is Python code, it also holds the GIL (global interpreter lock), so threads alone could not speed it up.
2. **Sequential patch processing**. DXT5 encoding and decoding run in Pillow's C code, about 10 ms per patch, but the 64 patches ran one at a time.
3. **Saving the 4096x4096 PNG**. About 1.4 s per canvas at Pillow's default compression level. This step cannot be split into patches.

### What was done

All changes are in [main.py](../main.py).

#### Fast reader for uncompressed DDS

`read_dds_rgba(path)` reads the 128-byte DDS header. When the file is uncompressed 32-bit with the exact A8R8G8B8 bitmasks (and no DX10 extension), it reads the pixel data directly with NumPy and reorders the channels from BGRA to RGBA. Any other format (DXT5 colormaps, for instance) falls back to Pillow. Reading a patch drops from ~0.25 s to a few milliseconds.

#### Patches processed in parallel

`stitch_patches(patch_dir, name_fmt, auto_flip)` and `unstitch_patches(img, patch_dir, name_fmt, auto_flip, **save_kwargs)` replace the four near-identical loops in the colormap and detailmap methods. They distribute the 64 patches across a `ThreadPoolExecutor` of up to 8 workers (`TEXTURE_WORKERS`).

- Threads (not processes) are enough because Pillow releases the GIL while encoding and decoding DDS, so patches really run at the same time. Threads also avoid the pitfalls of process pools in a PyQt application and in a PyInstaller build.
- Workers never touch the shared 4096x4096 canvas: on export they return the loaded patches and the calling thread pastes them, so no locking is needed. On import each worker writes its own file.
- An exception raised in any worker is passed back to the calling thread, so it still reaches the existing error dialog.
- The pool runs inside the existing `WorkerThread`, so the interface stays responsive as before.

The coordinate rules from [AGENTS.md](../AGENTS.md) are unchanged: columns are placed as-is, rows are inverted on the canvas (`dst_row = 7 - row`), and each patch is flipped vertically. The flip is now done with `transpose(FLIP_TOP_BOTTOM)` instead of a NumPy round trip, which gives the same result.

#### Detailmap layers in parallel

`export_detailmaps` and `import_detailmaps` process layers 1 and 2 at the same time through `run_in_parallel()`, so the two slow PNG saves (or loads) overlap.

#### Faster PNG compression

The 4096x4096 canvases are saved with `compress_level=1` (`PNG_COMPRESS_LEVEL`) instead of Pillow's default of 6. This cuts the save time by about 35% (1.39 s to 0.89 s), with files about 60% larger (37 MB to 61 MB on the test colormap). PNG is lossless at every level, so image quality is unaffected.

### Tests

[tests/test_parallel_textures.py](../tests/test_parallel_textures.py) covers the new helpers:

- `read_dds_rgba` returns exactly the same pixels as Pillow, for square and non-square uncompressed files and for the DXT5 fallback.
- Splitting a canvas into patches and stitching it back gives the original image, with `auto_flip` both enabled and disabled.
- Patch `tx00x00` contains the bottom-left tile of the canvas, flipped vertically.
- A missing patch leaves its tile blank instead of failing.

Run the whole suite with `python -m unittest discover tests`.
