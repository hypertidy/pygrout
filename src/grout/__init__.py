"""
grout: Grid tile indexing for chunked raster access.

Create explicit tabular indices of grid tiles with offsets, counts,
coordinate ranges, and tile positions.
"""

from typing import NamedTuple, Iterator, Literal
import math

__version__ = "0.1.0"


class TileSpec(NamedTuple):
    """Specification for a single tile in a grid.
    
    Attributes:
        col: Tile column index (0-based)
        row: Tile row index (0-based)
        offset_x: Pixel offset from left (column start)
        offset_y: Pixel offset from top (row start)
        ncol: Tile width in pixels
        nrow: Tile height in pixels
        xmin: Left coordinate bound
        xmax: Right coordinate bound
        ymin: Bottom coordinate bound
        ymax: Top coordinate bound
    """
    col: int
    row: int
    offset_x: int
    offset_y: int
    ncol: int
    nrow: int
    xmin: float
    xmax: float
    ymin: float
    ymax: float


class Grout:
    """Grid tile index generator.
    
    Creates a lazy index of tiles for a raster grid, with pixel offsets
    and coordinate bounds for each tile.
    
    Parameters
    ----------
    dim : tuple of (int, int)
        Grid dimensions as (ncol, nrow) - GDAL style (width, height)
    blocksize : tuple of (int, int)
        Tile dimensions as (block_width, block_height)
    extent : tuple of (float, float, float, float), optional
        Coordinate extent as (xmin, xmax, ymin, ymax)
    transform : tuple of 6 floats, optional
        GDAL-style geotransform (xmin, xres, 0, ymax, 0, -yres)
        
    Must provide either extent or transform.
    
    Examples
    --------
    >>> g = Grout(
    ...     dim=(86400, 43200),
    ...     extent=(-180, 180, -90, 90),
    ...     blocksize=(512, 512)
    ... )
    >>> len(g)
    14196
    >>> next(iter(g))
    TileSpec(col=0, row=0, offset_x=0, offset_y=0, ncol=512, nrow=512, ...)
    """
    
    def __init__(
        self,
        dim: tuple[int, int],
        blocksize: tuple[int, int],
        extent: tuple[float, float, float, float] | None = None,
        transform: tuple[float, float, float, float, float, float] | None = None,
    ):
        self.ncol, self.nrow = dim
        self.block_width, self.block_height = blocksize
        
        if extent is not None:
            xmin, xmax, ymin, ymax = extent
            self.xres = (xmax - xmin) / self.ncol
            self.yres = (ymax - ymin) / self.nrow
            self.xmin = xmin
            self.ymax = ymax
        elif transform is not None:
            self.xmin, self.xres, _, self.ymax, _, yres = transform
            self.yres = -yres
        else:
            raise ValueError("Must provide extent or transform")
        
        self.tile_cols = math.ceil(self.ncol / self.block_width)
        self.tile_rows = math.ceil(self.nrow / self.block_height)
    
    def __iter__(self) -> Iterator[TileSpec]:
        """Iterate over all tiles in row-major order."""
        for tr in range(self.tile_rows):
            for tc in range(self.tile_cols):
                offset_x = tc * self.block_width
                offset_y = tr * self.block_height
                
                ncol = min(self.block_width, self.ncol - offset_x)
                nrow = min(self.block_height, self.nrow - offset_y)
                
                tile_xmin = self.xmin + offset_x * self.xres
                tile_xmax = tile_xmin + ncol * self.xres
                tile_ymax = self.ymax - offset_y * self.yres
                tile_ymin = tile_ymax - nrow * self.yres
                
                yield TileSpec(
                    col=tc, row=tr,
                    offset_x=offset_x, offset_y=offset_y,
                    ncol=ncol, nrow=nrow,
                    xmin=tile_xmin, xmax=tile_xmax,
                    ymin=tile_ymin, ymax=tile_ymax
                )
    
    def __len__(self) -> int:
        """Total number of tiles."""
        return self.tile_rows * self.tile_cols
    
    def __repr__(self) -> str:
        return (
            f"Grout(dim=({self.ncol}, {self.nrow}), "
            f"blocksize=({self.block_width}, {self.block_height}), "
            f"tiles=({self.tile_cols}, {self.tile_rows}))"
        )
        
    def __getitem__(self, idx):
        """Get tile by linear index or (col, row) tuple."""
        if isinstance(idx, tuple):
            tc, tr = idx
        else:
            # Linear index to (col, row)
            tr, tc = divmod(idx, self.tile_cols)
        
        if not (0 <= tc < self.tile_cols and 0 <= tr < self.tile_rows):
            raise IndexError(f"Tile index out of range: {idx}")
        
        offset_x = tc * self.block_width
        offset_y = tr * self.block_height
        ncol = min(self.block_width, self.ncol - offset_x)
        nrow = min(self.block_height, self.nrow - offset_y)
        
        tile_xmin = self.xmin + offset_x * self.xres
        tile_xmax = tile_xmin + ncol * self.xres
        tile_ymax = self.ymax - offset_y * self.yres
        tile_ymin = tile_ymax - nrow * self.yres
        
        return TileSpec(
            col=tc, row=tr,
            offset_x=offset_x, offset_y=offset_y,
            ncol=ncol, nrow=nrow,
            xmin=tile_xmin, xmax=tile_xmax,
            ymin=tile_ymin, ymax=tile_ymax
        )

    def index_partition(self, n: int):
        """Yield n index ranges (start, stop) — no tiles materialized."""
        per_chunk = math.ceil(len(self) / n)
        for i in range(n):
            start = i * per_chunk
            stop = min(start + per_chunk, len(self))
            if start < stop:
                yield (start, stop)

def tile_index(g: Grout, backend: Literal['pandas', 'polars', 'list'] = 'pandas'):
    """Materialize tile index to a DataFrame or list.
    
    Parameters
    ----------
    g : Grout
        Grid tile index
    backend : {'pandas', 'polars', 'list'}, default 'pandas'
        Output format
        
    Returns
    -------
    pandas.DataFrame, polars.DataFrame, or list of TileSpec
    
    Examples
    --------
    >>> g = Grout(dim=(1000, 1000), extent=(0, 100, 0, 100), blocksize=(256, 256))
    >>> df = tile_index(g)
    >>> df.head()
    """
    tiles = list(g)
    
    if backend == 'list':
        return tiles
    elif backend == 'pandas':
        import pandas as pd
        return pd.DataFrame(tiles)
    elif backend == 'polars':
        import polars as pl
        return pl.DataFrame(tiles)
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'pandas', 'polars', or 'list'.")


__all__ = ['Grout', 'TileSpec', 'tile_index', '__version__']
