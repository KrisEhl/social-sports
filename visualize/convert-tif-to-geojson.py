# pip install GDAL
from osgeo import gdal, ogr, osr
import os
import sys
import time


def tif_to_geojson(
    tif_path: str,
    out_geojson: str = "raster_polygons.geojson",
    band_index: int = 1,
    simplify_tolerance_deg: float | None = 0.00005,  # 5–6 m tolerance
):
    gdal.UseExceptions()

    start_time = time.time()
    print(f"\n[INFO] Starting polygonization of: {tif_path}")

    # --- 1) Open raster ---
    print("[INFO] Opening raster...")
    ds = gdal.Open(tif_path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"❌ Could not open {tif_path}")

    print("[INFO] Raster opened successfully.")
    print(f"      Size: {ds.RasterXSize} x {ds.RasterYSize} pixels")
    print(f"      Bands: {ds.RasterCount}")

    band = ds.GetRasterBand(band_index)
    print(f"[INFO] Using band {band_index}")

    nodata = band.GetNoDataValue()
    print(f"[INFO] Nodata value: {nodata}")

    mask_band = band.GetMaskBand()
    wkt = ds.GetProjection()
    src_srs = osr.SpatialReference()
    if wkt:
        src_srs.ImportFromWkt(wkt)
        print("[INFO] Source projection loaded.")
    else:
        print("[WARN] No projection found in source raster.")
        src_srs = None

    # --- 2) Create in-memory layer ---
    print("[INFO] Creating in-memory GeoPackage for intermediate output...")
    drv_gpkg = ogr.GetDriverByName("GPKG")
    mem_path = "/vsimem/polys.gpkg"
    try:
        drv_gpkg.DeleteDataSource(mem_path)
    except Exception:
        pass
    vg = drv_gpkg.CreateDataSource(mem_path)
    if vg is None:
        raise RuntimeError("❌ Could not create in-memory GPKG data source")

    layer = vg.CreateLayer("polys", srs=src_srs, geom_type=ogr.wkbPolygon)
    print("[INFO] Layer created in memory.")

    gdal_type = band.DataType
    fld_def = ogr.FieldDefn(
        "value", ogr.OFTInteger if gdal_type <= gdal.GDT_Int32 else ogr.OFTReal
    )
    layer.CreateField(fld_def)
    print("[INFO] Attribute field 'value' created.")

    # --- 3) Polygonize ---
    print("[INFO] Starting polygonization... (this may take several minutes)")
    t0 = time.time()
    gdal.Polygonize(
        srcBand=band, maskBand=mask_band, outLayer=layer, iPixValField=0, callback=None
    )
    t_poly = time.time() - t0
    print(f"[DONE] Polygonization complete in {t_poly:.2f} seconds.")

    layer = None
    vg = None
    print("[INFO] Intermediate polygons written to /vsimem memory store.")

    # --- 4) Reproject & (optionally) simplify, then write GeoJSON ---
    print("[INFO] Reprojecting to EPSG:4326 and writing GeoJSON...")

    # Build ogr2ogr-style flags
    opt_flags = []
    # Apply simplification in output CRS units (degrees after -t_srs EPSG:4326)
    if simplify_tolerance_deg is not None and simplify_tolerance_deg > 0:
        opt_flags += ["-simplify", str(simplify_tolerance_deg)]
        print(
            f"[INFO] Simplifying geometry with tolerance {simplify_tolerance_deg}° "
            f"(~{simplify_tolerance_deg*111000:.1f} m)"
        )

    # Reduce GeoJSON size a bit (optional)
    lco = ["COORDINATE_PRECISION=6"]

    vt_opts = gdal.VectorTranslateOptions(
        format="GeoJSON",
        dstSRS="EPSG:4326",  # same as -t_srs EPSG:4326
        layerName="polys",
        options=opt_flags,  # use ogr2ogr flags here
        layerCreationOptions=lco,  # GeoJSON driver LCOs
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_geojson)) or ".", exist_ok=True)

    t0 = time.time()
    out_ds = gdal.VectorTranslate(out_geojson, srcDS=mem_path, options=vt_opts)
    t_reproj = time.time() - t0
    if out_ds is None:
        raise RuntimeError("❌ VectorTranslate failed")
    out_ds = None

    print(f"[DONE] GeoJSON saved: {out_geojson}")
    print(f"       Reprojection/simplify time: {t_reproj:.2f} seconds")
    os.makedirs(os.path.dirname(os.path.abspath(out_geojson)) or ".", exist_ok=True)

    t0 = time.time()
    out_ds = gdal.VectorTranslate(
        destNameOrDestDS=out_geojson, srcDS=mem_path, options=vt_opts
    )
    t_reproj = time.time() - t0
    if out_ds is None:
        raise RuntimeError("❌ VectorTranslate failed")
    out_ds = None

    print(f"[DONE] GeoJSON saved: {out_geojson}")
    print(f"       Reprojection/simplify time: {t_reproj:.2f} seconds")

    drv_gpkg.DeleteDataSource(mem_path)
    total = time.time() - start_time
    print(f"[SUCCESS] Finished entire process in {total:.2f} seconds.\n")

    return out_geojson


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python tif_to_geojson.py <input.tif> <output.geojson> [band=1] [simplify_deg=0.00005 or none]"
        )
        sys.exit(1)
    tif = sys.argv[1]
    out = sys.argv[2]
    band = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    sim_arg = sys.argv[4].lower() if len(sys.argv) > 4 else "0.00005"
    simplify = None if sim_arg in ("none", "null", "0") else float(sim_arg)
    print(
        ">>>",
        tif_to_geojson(tif, out, band_index=band, simplify_tolerance_deg=simplify),
    )
