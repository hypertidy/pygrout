"""Tests for grout package."""

import math
from grout import Grout, TileSpec, tile_index


def test_grout_basic():
    """Test basic Grout creation and properties."""
    g = Grout(
        dim=(1000, 500),
        extent=(0, 100, 0, 50),
        blocksize=(256, 256)
    )
    
    assert g.ncol == 1000
    assert g.nrow == 500
    assert g.block_width == 256
    assert g.block_height == 256
    assert g.tile_cols == 4  # ceil(1000/256)
    assert g.tile_rows == 2  # ceil(500/256)
    assert len(g) == 8


def test_grout_iteration():
    """Test tile iteration."""
    g = Grout(
        dim=(512, 512),
        extent=(0, 1, 0, 1),
        blocksize=(256, 256)
    )
    
    tiles = list(g)
    assert len(tiles) == 4
    
    # First tile
    t0 = tiles[0]
    assert t0.col == 0
    assert t0.row == 0
    assert t0.offset_x == 0
    assert t0.offset_y == 0
    assert t0.ncol == 256
    assert t0.nrow == 256
    assert t0.xmin == 0.0
    assert t0.ymax == 1.0


def test_grout_edge_tiles():
    """Test that edge tiles have correct reduced dimensions."""
    g = Grout(
        dim=(300, 200),
        extent=(0, 300, 0, 200),
        blocksize=(256, 256)
    )
    
    tiles = list(g)
    assert len(tiles) == 2  # 2 cols, 1 row
    
    # First tile: full size
    assert tiles[0].ncol == 256
    assert tiles[0].nrow == 200  # full height (200 < 256)
    
    # Second tile: edge
    assert tiles[1].ncol == 44   # 300 - 256
    assert tiles[1].nrow == 200


def test_grout_transform():
    """Test creation from GDAL-style geotransform."""
    # Geotransform: (xmin, xres, 0, ymax, 0, -yres)
    transform = (0.0, 0.1, 0.0, 50.0, 0.0, -0.1)
    
    g = Grout(
        dim=(1000, 500),
        transform=transform,
        blocksize=(100, 100)
    )
    
    assert g.xmin == 0.0
    assert g.ymax == 50.0
    assert g.xres == 0.1
    assert g.yres == 0.1


def test_tile_index_list():
    """Test tile_index with list backend."""
    g = Grout(dim=(100, 100), extent=(0, 1, 0, 1), blocksize=(50, 50))
    tiles = tile_index(g, backend='list')
    
    assert isinstance(tiles, list)
    assert len(tiles) == 4
    assert isinstance(tiles[0], TileSpec)


def test_tile_index_pandas():
    """Test tile_index with pandas backend."""
    pytest = __import__('pytest')
    pd = pytest.importorskip('pandas')
    
    g = Grout(dim=(100, 100), extent=(0, 1, 0, 1), blocksize=(50, 50))
    df = tile_index(g, backend='pandas')
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert list(df.columns) == ['col', 'row', 'offset_x', 'offset_y', 'ncol', 'nrow', 'xmin', 'xmax', 'ymin', 'ymax']


def test_tile_index_polars():
    """Test tile_index with polars backend."""
    pytest = __import__('pytest')
    pl = pytest.importorskip('polars')
    
    g = Grout(dim=(100, 100), extent=(0, 1, 0, 1), blocksize=(50, 50))
    df = tile_index(g, backend='polars')
    
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 4


def test_grout_repr():
    """Test string representation."""
    g = Grout(dim=(1000, 500), extent=(0, 100, 0, 50), blocksize=(256, 256))
    r = repr(g)
    
    assert 'Grout' in r
    assert '1000' in r
    assert '500' in r
    assert '256' in r


def test_coordinate_coverage():
    """Test that tiles cover the full extent without gaps or overlaps."""
    g = Grout(
        dim=(100, 100),
        extent=(0, 10, 0, 10),
        blocksize=(30, 30)
    )
    
    tiles = list(g)
    
    # Check x coverage
    x_ranges = [(t.xmin, t.xmax) for t in tiles if t.row == 0]
    x_ranges.sort()
    assert x_ranges[0][0] == 0.0  # starts at xmin
    for i in range(len(x_ranges) - 1):
        assert abs(x_ranges[i][1] - x_ranges[i+1][0]) < 1e-10  # no gaps
    assert abs(x_ranges[-1][1] - 10.0) < 1e-10  # ends at xmax


def test_gebco_scale():
    """Test with GEBCO-like dimensions."""
    g = Grout(
        dim=(86400, 43200),
        extent=(-180, 180, -90, 90),
        blocksize=(512, 512)
    )
    
    assert g.tile_cols == 169  # ceil(86400/512)
    assert g.tile_rows == 85   # ceil(43200/512)
    assert len(g) == 169 * 85
    
    # Check first tile
    first = next(iter(g))
    assert first.xmin == -180.0
    assert first.ymax == 90.0
