"""Cheap elevation hint: SRTM 30 m (opentopodata public API) at the underpass coordinate and the gauge,
compared with gauge datum (gdt, EL.m) + planned flood level / clean max level.

hint_pfh_minus_ground_m > 0  -> the river at planned flood level would stand above the ground at the
underpass coordinate (river-influence plausible). SRTM vertical error is several metres, the OSM
coordinate is not the sag point, and river slope between gauge and underpass is ignored: hint only.

Usage: python -X utf8 elevation_hint.py   (after facility_table.py)
Output: facility_gauge_exceedance_elev.csv
"""
import json
import os
import time
import urllib.request

import pandas as pd

REPO = r"C:\Users\11243\Documents\GitHub\Flood-Disaster-Digital-Twin"
OUT = os.path.dirname(os.path.abspath(__file__))
F = pd.read_csv(os.path.join(OUT, "facility_gauge_exceedance.csv"), dtype={"station_code": str, "nearest_code": str})
st = json.load(open(os.path.join(REPO, "data/manifests/hrfco-stations.json"), encoding="utf-8"))
meta = {s["code"]: s for s in st["kinds"]["waterlevel"]["stations"]}

pts = {}
for _, r in F.iterrows():
    pts[("fac", r.facility_id)] = (r.facility_lat, r.facility_lon)
for c in F.station_code.unique():
    pts[("gauge", c)] = (meta[c]["lat"], meta[c]["lon"])
keys = list(pts)
elev = {}
for i in range(0, len(keys), 90):
    chunk = keys[i:i + 90]
    loc = "|".join(f"{pts[k][0]:.6f},{pts[k][1]:.6f}" for k in chunk)
    url = "https://api.opentopodata.org/v1/srtm30m?locations=" + loc
    d = json.load(urllib.request.urlopen(url, timeout=120))
    for k, res in zip(chunk, d["results"]):
        elev[k] = res["elevation"]
    time.sleep(1.5)

F["ground_srtm_m"] = [elev[("fac", f)] for f in F.facility_id]
F["gauge_ground_srtm_m"] = [elev[("gauge", c)] for c in F.station_code]
F["pfh_elev_m"] = F.gdt_m + F.pfh
F["max_clean_elev_m"] = F.gdt_m + F.max_clean_m
F["hint_pfh_minus_ground_m"] = (F.pfh_elev_m - F.ground_srtm_m).round(1)
F["hint_maxclean_minus_ground_m"] = (F.max_clean_elev_m - F.ground_srtm_m).round(1)
F["gauge_check_ground_minus_gdt_m"] = (F.gauge_ground_srtm_m - F.gdt_m).round(1)
F.to_csv(os.path.join(OUT, "facility_gauge_exceedance_elev.csv"), index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250)
print(F[["facility_name", "sgg", "station_name", "distance_km", "gdt_m", "pfh", "ground_srtm_m", "gauge_ground_srtm_m",
         "gauge_check_ground_minus_gdt_m", "hint_pfh_minus_ground_m", "hint_maxclean_minus_ground_m"]].to_string())
