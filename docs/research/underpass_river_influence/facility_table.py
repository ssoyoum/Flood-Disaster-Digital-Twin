"""Facility-level join: each facility -> closest within-5km gauge that has a 2019-2026 series.

Usage: python -X utf8 facility_table.py   (after gauge_exceedance.py)
Output: facility_gauge_exceedance.csv
"""
import os

import pandas as pd

REPO = r"C:\Users\11243\Documents\GitHub\Flood-Disaster-Digital-Twin"
OUT = os.path.dirname(os.path.abspath(__file__))

L = pd.read_csv(os.path.join(REPO, "data/processed/facilities/facility_gauge_links.csv"), dtype={"station_code": str})
S = pd.read_csv(os.path.join(OUT, "gauge_stats.csv"), dtype={"station_code": str})
inv = pd.read_csv(os.path.join(REPO, "data/processed/facilities/underpass_coordinates.csv"))

w = L[(L.kind == "waterlevel") & (L.within_max_km)].copy()
nearest = w[w["rank"] == 1][["facility_id", "station_code", "station_name", "distance_km", "planned_flood_m"]].rename(
    columns={"station_code": "nearest_code", "station_name": "nearest_name", "distance_km": "nearest_km", "planned_flood_m": "nearest_pfh"})
withser = w.merge(S[S.series != "none"], on="station_code", how="inner", suffixes=("", "_s"))
withser = withser.sort_values(["facility_id", "distance_km"]).groupby("facility_id").head(1)
F = withser.merge(nearest, on="facility_id", how="left")
F["series_gauge_is_nearest"] = F.station_code == F.nearest_code
inv["facility_id"] = "underpass_coordinates:" + inv.molit_no.astype(str)
F = F.drop(columns=["sido", "sgg"]).merge(inv[["facility_id", "sido", "sgg", "structure", "management"]], on="facility_id", how="left")
cols = ["facility_id", "facility_name", "sido", "sgg", "facility_lon", "facility_lat", "station_code", "station_name", "distance_km",
        "series_gauge_is_nearest", "nearest_code", "nearest_name", "nearest_km", "gdt_m", "attwl", "wrnwl", "almwl", "pfh", "usable_pct",
        "max_wl_m", "max_time", "max_near_jump_flag", "max_over_pfh", "max_clean_m", "max_clean_time", "max_clean_over_pfh", "structure", "management",
        "ev_attention_clean", "ev_advisory_clean", "ev_warning_clean", "ev_planned_clean",
        "yrs_advisory", "yrs_warning", "yrs_planned", "years_advisory", "years_warning", "years_planned",
        "hrs_warning", "hrs_planned"]
F = F[cols]
F.to_csv(os.path.join(OUT, "facility_gauge_exceedance.csv"), index=False, encoding="utf-8-sig")
print(len(F), "facilities;", F.station_code.nunique(), "gauges;", F.series_gauge_is_nearest.sum(), "where series gauge is nearest")
for lv in ["advisory", "warning", "planned"]:
    print(lv, "facilities with >=1 clean event:", (F[f"ev_{lv}_clean"] >= 1).sum(),
          "gauges:", F[F[f"ev_{lv}_clean"] >= 1].station_code.nunique())
pd.set_option("display.width", 250)
print(F.sort_values(["ev_warning_clean", "ev_advisory_clean", "distance_km"], ascending=[False, False, True])[
    ["facility_name", "sido", "sgg", "station_name", "distance_km", "series_gauge_is_nearest", "nearest_name", "nearest_km", "max_clean_over_pfh",
     "ev_advisory_clean", "ev_warning_clean", "ev_planned_clean", "years_warning"]].to_string())
