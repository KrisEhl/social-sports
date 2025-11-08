import numpy as np
from shapely.geometry import box
import geopandas as gpd


def pick_utm_epsg_from_wgs84_bounds(gdf_ll):
    """Pick a UTM zone based on centroid in lon/lat; returns EPSG (WGS84 UTM)."""
    c = gdf_ll.unary_union.centroid
    lon, lat = c.x, c.y
    zone = int(np.floor((lon + 180) / 6) + 1)
    return 32600 + zone if lat >= 0 else 32700 + zone


def make_fishnet(bounds, tile_size):
    minx, miny, maxx, maxy = bounds
    minx = np.floor(minx / tile_size) * tile_size
    miny = np.floor(miny / tile_size) * tile_size
    maxx = np.ceil(maxx / tile_size) * tile_size
    maxy = np.ceil(maxy / tile_size) * tile_size

    xs = np.arange(minx, maxx, tile_size)
    ys = np.arange(miny, maxy, tile_size)

    boxes = []
    ids = []
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            boxes.append(box(x, y, x + tile_size, y + tile_size))
            ids.append(f"t_{i}_{j}")
    return ids, boxes


def regrid_sum_2km(gdf, tile_size_m=2000, area_weighted=True, target_epsg=None):
    if gdf.crs is None:
        raise ValueError("gdf.crs is None. Set a CRS (e.g. EPSG:4326) before calling.")

    # Project to meters
    if gdf.crs.is_geographic:
        epsg = target_epsg or pick_utm_epsg_from_wgs84_bounds(gdf.to_crs(4326))
        gdfm = gdf.to_crs(epsg=epsg)
    else:
        gdfm = gdf
        epsg = gdfm.crs.to_epsg()

    # Build grid
    ids, boxes = make_fishnet(gdfm.total_bounds, tile_size_m)
    grid = gpd.GeoDataFrame({"tile_id": ids, "geometry": boxes}, crs=gdfm.crs)

    if area_weighted:
        # Pre-compute original polygon areas to get fractions
        gdfm = gdfm.copy()
        gdfm["poly_area"] = gdfm.geometry.area

        # Intersection
        inter = gpd.overlay(
            gdfm[["value", "poly_area", "geometry"]],
            grid[["tile_id", "geometry"]],
            how="intersection",
            keep_geom_type=False,
        )

        if inter.empty:
            # Return empty result with same grid CRS
            grid["sum_value"] = 0.0
            return grid

        inter["inter_area"] = inter.geometry.area
        # Avoid division by zero (degenerate geometries)
        inter = inter[inter["poly_area"] > 0]
        inter["weighted_value"] = inter["value"] * (
            inter["inter_area"] / inter["poly_area"]
        )

        # Sum by tile
        out = inter.groupby("tile_id", as_index=False)["weighted_value"].sum()
        out = out.rename(columns={"weighted_value": "sum_value"})
    else:
        # Simple overlap: count each polygon's full value if it touches a tile
        # Quicker route: spatial join then groupby
        joined = gpd.sjoin(
            gdfm[["value", "geometry"]],
            grid[["tile_id", "geometry"]],
            how="inner",
            predicate="intersects",
        )
        if joined.empty:
            grid["sum_value"] = 0.0
            return grid
        out = joined.groupby("tile_id", as_index=False)["value"].sum()
        out = out.rename(columns={"value": "sum_value"})

    # Attach sums back to grid GeoDataFrame
    grid = grid.merge(out, on="tile_id", how="left")
    grid["value"] = grid["sum_value"].fillna(0.0)

    # (Optional) return to original CRS
    try:
        return grid.to_crs(gdf.crs)
    except Exception:
        return grid
