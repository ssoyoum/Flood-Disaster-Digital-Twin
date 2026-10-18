"""Per-gauge threshold exceedance stats (2019-2026 hourly), read-only on the repo.

Usage: python -X utf8 gauge_exceedance.py
Outputs (scratchpad): gauge_stats.csv, gauge_events.csv
"""
import json
import os
import sys

import pandas as pd

REPO = r"C:\Users\11243\Documents\GitHub\Flood-Disaster-Digital-Twin"
OUT = os.path.dirname(os.path.abspath(__file__))
GAP_H = 24  # same as repo `events` (hrfco-events.json gap_hours)

links = pd.read_csv(os.path.join(REPO, "data/processed/facilities/facility_gauge_links.csv"), dtype={"station_code": str})
st = json.load(open(os.path.join(REPO, "data/manifests/hrfco-stations.json"), encoding="utf-8"))
meta = {s["code"]: s for s in st["kinds"]["waterlevel"]["stations"]}

wl = links[(links.kind == "waterlevel") & (links.within_max_km)]
codes = sorted(wl.station_code.unique())

LEVELS = [("attention", "attwl"), ("advisory", "wrnwl"), ("warning", "almwl"), ("planned", "pfh")]

stats, events = [], []
for code in codes:
    m = meta.get(code, {})
    qpath = os.path.join(REPO, f"data/processed/hrfco-quality/waterlevel_{code}_1H_quality.csv")
    rpath = os.path.join(REPO, f"data/processed/hrfco/waterlevel_{code}_1H.csv")
    row = {"station_code": code, "station_name": m.get("name"), "gdt_m": m.get("gdt"),
           "attwl": m.get("attwl"), "wrnwl": m.get("wrnwl"), "almwl": m.get("almwl"), "pfh": m.get("pfh"),
           "flood_forecast_station": m.get("flood_forecast_station"), "address": f"{m.get('address','')} {m.get('address_detail','')}".strip()}
    if not os.path.exists(rpath):
        row["series"] = "none"
        stats.append(row)
        continue
    if os.path.exists(qpath):
        q = pd.read_csv(qpath, usecols=["timestamp_kst", "wl", "reading_usable", "reading_reasons", "jump_review_required"])
        q["t"] = pd.to_datetime(q.timestamp_kst)
        row["series"] = "quality_mask"
    else:
        q = pd.read_csv(rpath)
        q["t"] = pd.to_datetime(q.timestamp_kst)
        q["reading_usable"] = q.wl.notna()
        q["jump_review_required"] = q.wl.diff().abs() >= 3.0
        row["series"] = "raw_no_mask"
    q = q.sort_values("t").reset_index(drop=True)
    total = len(q)
    use = q[q.reading_usable == True].copy()
    row.update(rows=total, usable=len(use), usable_pct=round(100 * len(use) / max(total, 1), 1),
               first=str(use.t.min()), last=str(use.t.max()),
               jump_flags=int(q.jump_review_required.sum()))
    if use.empty:
        stats.append(row)
        continue
    # clean max: drop readings inside +-3h of any jump flag (spike/step suspects)
    jt = q.loc[q.jump_review_required == True, "t"]
    bad = pd.Series(False, index=use.index)
    for t in jt:
        bad |= (use.t >= t - pd.Timedelta(hours=3)) & (use.t <= t + pd.Timedelta(hours=6))
    cu = use[~bad]
    row["max_clean_m"] = float(cu.wl.max()) if not cu.empty else None
    row["max_clean_time"] = str(cu.loc[cu.wl.idxmax(), "t"]) if not cu.empty else None
    if m.get("pfh") and row["max_clean_m"] is not None:
        row["max_clean_over_pfh"] = round(row["max_clean_m"] / m["pfh"], 3)
    imax = use.wl.idxmax()
    row["max_wl_m"] = float(use.wl.max())
    row["max_time"] = str(use.loc[imax, "t"])
    # jump flags near the peak -> suspicious maximum
    near = q[(q.t >= use.loc[imax, "t"] - pd.Timedelta(hours=3)) & (q.t <= use.loc[imax, "t"] + pd.Timedelta(hours=3))]
    row["max_near_jump_flag"] = bool(near.jump_review_required.any())
    if m.get("pfh"):
        row["max_over_pfh"] = round(row["max_wl_m"] / m["pfh"], 3)
    jump_times = set(q.loc[q.jump_review_required == True, "t"])
    for lname, key in LEVELS:
        thr = m.get(key)
        if thr is None:
            row[f"ev_{lname}"] = None
            continue
        ex = use[use.wl >= thr]
        if ex.empty:
            row[f"ev_{lname}"] = 0; row[f"yrs_{lname}"] = 0; row[f"hrs_{lname}"] = 0; row[f"ev_{lname}_clean"] = 0
            continue
        grp = (ex.t.diff() > pd.Timedelta(hours=GAP_H)).cumsum()
        n_clean = 0
        yrs = set()
        for _, g in ex.groupby(grp):
            s, e = g.t.min(), g.t.max()
            pk = g.loc[g.wl.idxmax()]
            win = [t for t in jump_times if s - pd.Timedelta(hours=2) <= t <= e + pd.Timedelta(hours=2)]
            suspicious = bool(win)
            if not suspicious:
                n_clean += 1
                yrs.add(s.year)
            events.append({"station_code": code, "station_name": m.get("name"), "level": lname, "threshold_m": thr,
                           "start": str(s), "end": str(e), "hours": len(g), "peak_m": float(pk.wl), "peak_time": str(pk.t),
                           "jump_flag_in_window": suspicious})
        row[f"ev_{lname}"] = int(grp.nunique())
        row[f"ev_{lname}_clean"] = n_clean
        row[f"yrs_{lname}"] = len(yrs)
        row[f"years_{lname}"] = ";".join(str(y) for y in sorted(yrs))
        row[f"hrs_{lname}"] = len(ex)
    stats.append(row)

S = pd.DataFrame(stats)
S.to_csv(os.path.join(OUT, "gauge_stats.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(events).to_csv(os.path.join(OUT, "gauge_events.csv"), index=False, encoding="utf-8-sig")
print(S.series.value_counts())
print(S[S.series != "none"][["station_code", "station_name", "usable_pct", "max_wl_m", "pfh", "ev_advisory_clean", "ev_warning_clean", "ev_planned_clean", "max_near_jump_flag"]].to_string())
