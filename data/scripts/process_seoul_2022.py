"""Convert the acquired Seoul 2022 flood footprints to WGS84 GeoJSON."""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import geopandas as gpd


ROOT = Path(__file__).resolve().parents[2]
RAW_ZIP = ROOT / "data" / "raw" / "seoul_flood_footprints_2022.zip"
OUTPUT = ROOT / "data" / "processed" / "seoul_flood_footprints_2022.geojson"


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        with ZipFile(RAW_ZIP) as archive:
            archive.extractall(temp_dir)
        source = next(Path(temp_dir).rglob("*.shp"))
        frame = gpd.read_file(source, encoding="cp949")
        frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty].copy()
        frame["geometry"] = frame.geometry.make_valid()
        frame = frame.to_crs("EPSG:4326")

        frame = frame.rename(
            columns={
                "F_SHIM": "flood_depth_m",
                "F_AREA": "flood_area_m2",
                "F_DISA_NM": "event_name",
                "F_SAT_YMD": "start_date",
                "F_END_YMD": "end_date",
                "F_RSN_DTL": "cause_detail",
                "F_ZONE_NM": "flood_zone",
                "GU_NAM": "district",
                "ADM_CD": "admin_code",
                "TYPE": "damage_type",
            }
        )
        keep = [
            "flood_depth_m",
            "flood_area_m2",
            "event_name",
            "start_date",
            "end_date",
            "cause_detail",
            "flood_zone",
            "district",
            "admin_code",
            "damage_type",
            "geometry",
        ]
        frame = frame[[column for column in keep if column in frame.columns]]
        frame["origin"] = "OBSERVED"
        frame["source"] = "Seoul Open Data Plaza"
        frame.to_file(OUTPUT, driver="GeoJSON", encoding="utf-8")
        print(f"wrote {len(frame)} features to {OUTPUT}")


if __name__ == "__main__":
    main()
