import pandas as pd
import geopandas as gpd


def add_soccer_counts_to_grid(
    grid: gpd.GeoDataFrame,
    csv_path: str,
    lon_col: str = "lon",
    lat_col: str = "lat",
    filter_soccer: bool = True,
    dedupe: bool = True,
    tile_id_col: str = "tile_id",  # change if your grid uses a different id
) -> gpd.GeoDataFrame:
    if grid.crs is None:
        raise ValueError("Grid GeoDataFrame has no CRS. Set one (e.g., EPSG:4326).")

    # Load CSV -> points GeoDataFrame
    df = pd.read_csv(csv_path)

    # Optional filtering to soccer-only rows
    if filter_soccer and "sport" in df.columns:
        df = df[df["sport"].astype(str).str.contains("soccer", case=False, na=False)]

    # Optional dedupe by unique OSM feature
    if dedupe and {"osm_type", "osm_id"}.issubset(df.columns):
        df = df.drop_duplicates(subset=["osm_type", "osm_id"])

    # Build points
    if lon_col not in df.columns or lat_col not in df.columns:
        raise KeyError(f"CSV must contain '{lon_col}' and '{lat_col}' columns.")
    pts = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=4326,
    ).to_crs(grid.crs)

    # Ensure the grid has a stable ID
    grid = grid.copy()
    if tile_id_col not in grid.columns:
        grid = grid.reset_index(drop=True)
        grid[tile_id_col] = grid.index.astype(int)

    # Spatial join: count points per tile
    joined = gpd.sjoin(
        pts[["geometry"]],
        grid[[tile_id_col, "geometry"]],
        how="left",
        predicate="within",
    )
    counts = (
        joined.groupby(tile_id_col, as_index=False)
        .size()
        .rename(columns={"size": "soccer_count"})
    )

    # Merge counts onto grid
    out = grid.merge(counts, on=tile_id_col, how="left")
    return out
