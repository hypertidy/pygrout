# grout

Grid tile indexing for chunked raster access.

Python counterpart to [hypertidy/grout](https://github.com/hypertidy/grout) (R).

## Installation

```bash
pip install grout

# With pandas support
pip install grout[pandas]

# With polars support
pip install grout[polars]

# Development install
pip install -e .[dev]
```

## Usage

```python
from grout import Grout, tile_index

# Create a grid index from dimensions and extent
g = Grout(
    dim=(86400, 43200),          # (ncol, nrow) - GDAL style
    extent=(-180, 180, -90, 90), # (xmin, xmax, ymin, ymax)
    blocksize=(512, 512)         # (block_width, block_height)
)

print(g)
# Grout(dim=(86400, 43200), blocksize=(512, 512), tiles=(169, 85))

print(len(g))
# 14365

#from osgeo import gdal
#ds = gdal.Open(<some dataset with the dim/extent properties we specfied>)
# Lazy iteration
for tile in g:
    # Access tile.offset_x, tile.offset_y, tile.ncol, tile.nrow
    # Access tile.xmin, tile.xmax, tile.ymin, tile.ymax
    #data = ds.GetRasterBand(1).Read(tile.offset_x, tile.offset_y, tile.ncol, tile.nrow)
    break

# Materialize to DataFrame
df = tile_index(g)
print(df.head())
#    col  row  offset_x  offset_y  ncol  nrow        xmin        xmax       ymin       ymax
# 0    0    0         0         0   512   512 -180.000000 -177.866667  87.866667  90.000000
# 1    1    0       512         0   512   512 -177.866667 -175.733333  87.866667  90.000000
# ...

# Or with polars
df_pl = tile_index(g, backend='polars')
```

## From GDAL geotransform

```python
from osgeo import gdal

ds = gdal.Open("raster.tif")
transform = ds.GetGeoTransform()
ncol, nrow = ds.RasterXSize, ds.RasterYSize
block_size = ds.GetRasterBand(1).GetBlockSize()

g = Grout(
    dim=(ncol, nrow),
    transform=transform,
    blocksize=tuple(block_size)
)
```

## TileSpec fields

Each tile is a `TileSpec` named tuple with:

| Field | Description |
|-------|-------------|
| `col` | Tile column index (0-based) |
| `row` | Tile row index (0-based) |
| `offset_x` | Pixel offset from left |
| `offset_y` | Pixel offset from top |
| `ncol` | Tile width in pixels |
| `nrow` | Tile height in pixels |
| `xmin` | Left coordinate bound |
| `xmax` | Right coordinate bound |
| `ymin` | Bottom coordinate bound |
| `ymax` | Top coordinate bound |

## License

MIT
