"""Transparent heuristic ranking of 'river-influence plausible' underpasses (NOT a proof of inflow path).

score = exceedance (warning-years*2 + planned-flood events*2 + min(advisory events,6)*0.5)
      + same-river proximity (OSM same-named waterway <=500 m: +3, <=1500 m: +1.5)
      + gauge distance <=2 km: +1
      + elevation hint (gdt+pfh - SRTM ground >= 0: +3, >= -3: +1.5)
Rows whose OSM-matched coordinate contradicts the MOLIT sido/sgg, and duplicate coordinates, are excluded.
Usage: python -X utf8 shortlist.py   (after river_names.py)
Output: facility_river_influence_ranked.csv
"""
import os

import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
F = pd.read_csv(os.path.join(OUT, "facility_shortlist_input.csv"), dtype={"station_code": str})

# manual coordinate sanity flags (MOLIT location vs OSM-matched coordinate / nearest gauge region)
COORD_BAD = {
    "underpass_coordinates:191": "MOLIT 용인시인데 좌표가 서울 마포 성산(동명이소)",
    "underpass_coordinates:245": "MOLIT 화성시인데 좌표가 서울 송파 장지(동명이소)",
}
for i, r in F.iterrows():
    if r.facility_name == "계룡지하차도(복)":
        COORD_BAD[r.facility_id] = "MOLIT 영동군(충북)인데 좌표가 대전 서구"
    if r.facility_name == "옥산지하차도" and r.sgg == "거제시":
        COORD_BAD[r.facility_id] = "MOLIT 거제시인데 좌표가 경산"
    if r.facility_name == "성산지하차도" and r.sgg == "영등포구":
        COORD_BAD[r.facility_id] = "MOLIT 영등포구인데 좌표가 마포 성산"
F["coord_flag"] = F.facility_id.map(COORD_BAD)
F["dup_of"] = None
F.loc[F.facility_name == "궁평지하차도", "dup_of"] = "궁평2지하차도와 같은 좌표(같은 시설로 추정)"
F.loc[F.duplicated(["facility_lat", "facility_lon", "facility_name"], keep="first"), "dup_of"] = "중복 좌표 행"

f = lambda x: 0 if pd.isna(x) else x
F["s_exceed"] = [2 * f(a) + 2 * f(b) + 0.5 * min(f(c), 6) for a, b, c in zip(F.yrs_warning, F.ev_planned_clean, F.ev_advisory_clean)]
F["s_river"] = [3 if (not pd.isna(d) and d <= 500) else 1.5 if (not pd.isna(d) and d <= 1500) else 0 for d in F.same_river_dist_m]
F["s_gauge"] = [1 if d <= 2 else 0 for d in F.distance_km]
F["s_elev"] = [3 if h >= 0 else 1.5 if h >= -3 else 0 for h in F.hint_pfh_minus_ground_m]
F["score"] = F.s_exceed + F.s_river + F.s_gauge + F.s_elev
F["eligible"] = F.coord_flag.isna() & F.dup_of.isna()
F = F.sort_values(["eligible", "score"], ascending=[False, False])
F.to_csv(os.path.join(OUT, "facility_river_influence_ranked.csv"), index=False, encoding="utf-8-sig")

E = F[F.eligible]
print("eligible", len(E), "of", len(F), "unique gauges", E.station_code.nunique())
# tiers
tA = E[(E.yrs_warning.fillna(0) >= 1) & (E.same_river_dist_m <= 1500) & (E.hint_pfh_minus_ground_m >= -3)]
tB = E[(E.ev_advisory_clean.fillna(0) >= 1) & (E.same_river_dist_m <= 1500) & (E.hint_pfh_minus_ground_m >= -3)]
tC = E[(E.same_river_dist_m.isna()) | (E.hint_pfh_minus_ground_m < -10)]
print("tier A (warning-yr>=1 & same river<=1.5km & elev>=-3):", len(tA), "gauges", tA.station_code.nunique())
print("tier B (advisory>=1 & same river<=1.5km & elev>=-3):", len(tB), "gauges", tB.station_code.nunique())
print("unlikely (no same-river within 1.5km or elev < -10 m):", len(tC))
print("same-river<=1.5km:", (E.same_river_dist_m <= 1500).sum(), " elev>=-3:", (E.hint_pfh_minus_ground_m >= -3).sum())
pd.set_option("display.width", 260)
print(E[["facility_name", "sido", "sgg", "station_name", "distance_km", "gauge_osm_river", "same_river_dist_m", "hint_pfh_minus_ground_m",
         "max_clean_over_pfh", "ev_advisory_clean", "ev_warning_clean", "ev_planned_clean", "years_warning", "score"]].head(30).to_string())
print(F[~F.eligible][["facility_name", "sgg", "coord_flag", "dup_of"]].to_string())
