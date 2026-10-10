"""Retrain the 6-hour maximum water-level rise model on real HRFCO stations.

The input contract follows ``water-level-rise/baseline.py`` (FEATURES, make_features): the water level at
the reference hour and 1/3/6/12/24 h before it, surface rainfall totals over 1/6/24 h, and the derived
changes, accelerations and 24 h range. Target = max(WL(t+1h..t+6h)) - WL(t) in metres, negatives valid.
IMERG, radar and basin columns of the research contract do not exist here and are left out; station
statistics (median level, rise std and q99) are computed from training rows only, as in the research code.

Data: data/processed/hrfco/waterlevel_{code}_1H.csv (+ rainfall_{code}_1H.csv of the nearest rain gauge from
data/manifests/hrfco-forecast-rain-pairs.json). Real station codes, real KST timestamps.

    python data/scripts/train_rise_model.py                      # all stations on disk
    python data/scripts/train_rise_model.py --stations 3011665   # one station
    python data/scripts/train_rise_model.py --holdout 2023-07    # month kept out of training (default)

Outputs: data/models/rise_lgbm_1h.txt (LightGBM booster text), data/models/rise_station_stats.json,
data/models/rise_model_card.json and data/manifests/rise-model.json (metrics, cross-validation, Osong 2023-07-15 check).
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

REPO_ROOT = Path(__file__).resolve().parents[2]
HRFCO = REPO_ROOT / "data" / "processed" / "hrfco"
PAIRS = REPO_ROOT / "data" / "manifests" / "hrfco-forecast-rain-pairs.json"
STATIONS = REPO_ROOT / "data" / "manifests" / "hrfco-stations.json"
MODEL_DIR = REPO_ROOT / "data" / "models"
MODEL_FILE = MODEL_DIR / "rise_lgbm_1h.txt"
STATS_FILE = MODEL_DIR / "rise_station_stats.json"
METRICS_FILE = REPO_ROOT / "data" / "manifests" / "rise-model.json"
CARD_FILE = MODEL_DIR / "rise_model_card.json"  # same content; shipped with the model because data/manifests is not in the image

LAGS = (1, 3, 6, 12, 24)
HORIZON = 6
WATER_FEATURES = ["wl_t"] + [f"wl_t_minus_{h}h" for h in LAGS]
RAIN_FEATURES = ["sfc_rain_1h", "sfc_rain_6h", "sfc_rain_24h"]
JUMP_M = 3.0  # same threshold as `collect_hrfco_history.py qc`: a 1 h change above this is a sensor/datum fault
PARAMS = {"objective": "regression", "learning_rate": 0.03, "num_leaves": 31, "min_data_in_leaf": 200, "feature_fraction": 0.8,
          "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 1.0, "verbose": -1, "num_threads": 6}

# Osong reference: 궁평2지하차도 / 미호강교 3011665, 2023-07-15 (levels in backend/app/twin.py).
OSONG = {"station": "3011665", "start": "2023-07-14 12:00", "end": "2023-07-15 10:00", "planned_flood_m": 9.38, "warning_m": 8.0}


# ---- dataset --------------------------------------------------------------------------------------
def rain_pairs() -> dict[str, str]:
    """Water-level station -> first of its three nearest rain gauges whose hourly CSV actually holds data."""
    if not PAIRS.exists():
        return {}
    data = json.loads(PAIRS.read_text(encoding="utf-8"))
    out = {}
    for wl, v in data["pairs"].items():
        for cand in (v or {}).get("candidates", []):
            path = HRFCO / f"rainfall_{cand['rain']}_1H.csv"
            if path.exists() and pd.read_csv(path, usecols=["rf"])["rf"].notna().sum() >= 1000:
                out[wl] = cand["rain"]
                break
    return out


def hourly(path: Path, column: str) -> pd.Series:
    frame = pd.read_csv(path, usecols=["timestamp_kst", column])
    frame["t"] = pd.to_datetime(frame["timestamp_kst"])
    series = pd.to_numeric(frame[column], errors="coerce")
    series.index = frame["t"]
    series = series[~series.index.duplicated(keep="last")].sort_index()
    full = pd.date_range(series.index.min(), series.index.max(), freq="h")
    return series.reindex(full)


def station_frame(code: str, rain_code: str | None) -> pd.DataFrame:
    wl = hourly(HRFCO / f"waterlevel_{code}_1H.csv", "wl")
    # Drop readings on either side of a > JUMP_M step (sensor/datum fault, see docs/HRFCO_HISTORY.md).
    jump = wl.diff().abs() > JUMP_M
    wl[jump | jump.shift(-1, fill_value=False)] = np.nan
    frame = pd.DataFrame({"wl_t": wl})
    for h in LAGS:
        frame[f"wl_t_minus_{h}h"] = wl.shift(h)
    future = pd.concat([wl.shift(-k) for k in range(1, HORIZON + 1)], axis=1)
    frame["target_maxrise_6h"] = future.max(axis=1).where(future.notna().all(axis=1)) - wl
    rain_path = HRFCO / f"rainfall_{rain_code}_1H.csv" if rain_code else None
    if rain_path and rain_path.exists():
        rf = hourly(rain_path, "rf").reindex(frame.index)
        frame["sfc_rain_1h"] = rf
        frame["sfc_rain_6h"] = rf.rolling(6, min_periods=6).sum()
        frame["sfc_rain_24h"] = rf.rolling(24, min_periods=24).sum()
        frame["rain_station"] = rain_code
    else:
        for name in RAIN_FEATURES:
            frame[name] = np.nan
        frame["rain_station"] = ""
    frame["station_id"] = code
    frame = frame.dropna(subset=WATER_FEATURES + ["target_maxrise_6h"])
    frame.index.name = "timestamp_kst"
    return frame.reset_index()


def select_rows(frame: pd.DataFrame, calm_keep: float, seed: int) -> pd.DataFrame:
    """Keep every 'active' hour (level moved or it rained) and a random share of calm hours."""
    levels = frame[WATER_FEATURES]
    active = ((levels.max(axis=1) - levels.min(axis=1)) >= 0.2) | (frame["target_maxrise_6h"].abs() >= 0.2) | (frame["sfc_rain_24h"].fillna(0) >= 10)
    rng = np.random.default_rng(seed)
    keep = active.to_numpy() | (rng.random(len(frame)) < calm_keep)
    out = frame[keep].copy()
    out["active"] = active[keep].to_numpy()
    return out


def build_dataset(codes: list[str], calm_keep: float, seed: int) -> pd.DataFrame:
    pairs = rain_pairs()
    parts = []
    for code in codes:
        frame = station_frame(code, pairs.get(code))
        if len(frame):
            parts.append(select_rows(frame, calm_keep, seed))
    data = pd.concat(parts, ignore_index=True)
    data["month"] = data["timestamp_kst"].dt.strftime("%Y-%m")
    return data


# ---- features (research contract) ----------------------------------------------------------------
def station_stats(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    g = frame.groupby("station_id")
    return {
        "wl_median": g["wl_t"].median().to_dict(),
        "rise_std": g["target_maxrise_6h"].std().to_dict(),
        "rise_q99": g["target_maxrise_6h"].quantile(0.99).to_dict(),
        "wl_fallback": float(frame["wl_t"].median()),
    }


def make_features(frame: pd.DataFrame, stats: dict) -> pd.DataFrame:
    x = frame[WATER_FEATURES + RAIN_FEATURES].astype(float).copy()
    for h in LAGS:
        x[f"wl_change_{h}h"] = x["wl_t"] - x[f"wl_t_minus_{h}h"]
    x["wl_acceleration_3h"] = x["wl_change_1h"] - x["wl_change_3h"] / 3
    x["wl_acceleration_6h"] = x["wl_change_3h"] / 3 - x["wl_change_6h"] / 6
    x["wl_observed_range_24h"] = x[WATER_FEATURES].max(axis=1) - x[WATER_FEATURES].min(axis=1)
    x["sfc_rain_previous_1_to_6h"] = x["sfc_rain_6h"] - x["sfc_rain_1h"]
    x["sfc_rain_previous_6_to_24h"] = x["sfc_rain_24h"] - x["sfc_rain_6h"]
    x["sfc_rain_recent_share"] = x["sfc_rain_1h"] / (x["sfc_rain_6h"].abs() + 1.0)
    station = frame["station_id"]
    x["wl_above_station_median"] = x["wl_t"] - station.map(stats["wl_median"]).fillna(stats["wl_fallback"]).to_numpy(dtype=float)
    x["station_rise_std"] = station.map(stats["rise_std"]).to_numpy(dtype=float)
    x["station_rise_q99"] = station.map(stats["rise_q99"]).to_numpy(dtype=float)
    return x


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) if len(a) else float("nan")


def fit(x: pd.DataFrame, y: np.ndarray, rounds: int, seed: int) -> lgb.Booster:
    return lgb.train({**PARAMS, "seed": seed}, lgb.Dataset(x, y), rounds)


def official_levels() -> dict[str, dict[str, float]]:
    cat = json.loads(STATIONS.read_text(encoding="utf-8"))
    out = {}
    for st in cat["kinds"]["waterlevel"]["stations"]:
        levels = {k: float(st[k]) for k in ("attwl", "wrnwl", "almwl", "pfh") if st.get(k) not in (None, "", 0, "0")}
        if levels:
            out[st["code"]] = levels
    return out


def threshold_skill(frame: pd.DataFrame, preds: dict[str, np.ndarray]) -> dict:
    """Does 'WL(t) + forecast rise >= level' predict 'max WL in the next 6 h >= level'? Only hours below the level count."""
    levels = official_levels()
    out = {}
    for key in ("attwl", "wrnwl", "almwl", "pfh"):
        level = frame["station_id"].map(lambda c: levels.get(c, {}).get(key, np.nan)).to_numpy(dtype=float)
        below = (frame["wl_t"].to_numpy() < level) & np.isfinite(level)
        if not below.any():
            continue
        actual = (frame["wl_t"].to_numpy() + frame["target_maxrise_6h"].to_numpy()) >= level
        entry = {"hours_below_level": int(below.sum()), "hours_reaching_within_6h": int((actual & below).sum())}
        for name, p in preds.items():
            fc = (frame["wl_t"].to_numpy() + p) >= level
            hit, miss, false = int((fc & actual & below).sum()), int((~fc & actual & below).sum()), int((fc & ~actual & below).sum())
            entry[name] = {"hit": hit, "miss": miss, "false_alarm": false, "pod": round(hit / (hit + miss), 3) if hit + miss else None, "far": round(false / (hit + false), 3) if hit + false else None}
        out[key] = entry
    return out


# ---- Osong check ---------------------------------------------------------------------------------
def osong_check(model: lgb.Booster, stats: dict, frame_all: pd.DataFrame) -> dict:
    """Lead time of 'forecast level reaches the threshold' for the model vs. no-change and linear extrapolation."""
    w = frame_all[(frame_all["station_id"] == OSONG["station"]) & (frame_all["timestamp_kst"] >= OSONG["start"]) & (frame_all["timestamp_kst"] <= OSONG["end"])].copy()
    if w.empty:
        return {"available": False}
    x = make_features(w, stats)
    w["pred_model"] = model.predict(x)
    w["pred_linear"] = (w["wl_t"] - w["wl_t_minus_1h"]).clip(lower=0) * HORIZON
    w["pred_persist"] = 0.0
    actual = w["target_maxrise_6h"].to_numpy()
    rows = []
    for _, r in w.iterrows():
        rows.append({"t": r["timestamp_kst"].strftime("%m-%d %H:%M"), "wl": round(r["wl_t"], 2), "actual_rise": round(r["target_maxrise_6h"], 2),
                     "model": round(float(r["pred_model"]), 2), "linear": round(float(r["pred_linear"]), 2), "rain_6h": None if pd.isna(r["sfc_rain_6h"]) else round(float(r["sfc_rain_6h"]), 1)})
    out = {"available": True, "window": [OSONG["start"], OSONG["end"]], "rows": rows,
           "rmse_m": {k: round(rmse(actual, w[f"pred_{k}"]), 3) for k in ("model", "linear", "persist")}}
    for name, level in (("planned_flood", OSONG["planned_flood_m"]), ("warning", OSONG["warning_m"])):
        reached = w[w["wl_t"] >= level]
        first_actual = reached["timestamp_kst"].min() if len(reached) else None
        entry = {"level_m": level, "first_observed": first_actual.strftime("%Y-%m-%d %H:%M") if first_actual is not None else None}
        for k in ("model", "linear", "persist"):
            hit = w[(w["wl_t"] + w[f"pred_{k}"]) >= level]
            first = hit["timestamp_kst"].min() if len(hit) else None
            entry[f"first_forecast_{k}"] = first.strftime("%Y-%m-%d %H:%M") if first is not None else None
            entry[f"lead_min_{k}"] = int((first_actual - first).total_seconds() // 60) if (first is not None and first_actual is not None) else None
        out[name] = entry
    return out


# ---- main ----------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stations", nargs="*", default=None, help="station codes (default: every waterlevel_*_1H.csv on disk)")
    parser.add_argument("--holdout", default="2023-07", help="YYYY-MM kept out of training for the Osong check")
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=800)
    parser.add_argument("--calm-keep", type=float, default=0.05, help="share of calm hours kept beside every active hour")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--skip-cv", action="store_true")
    args = parser.parse_args()

    codes = args.stations or sorted(p.stem.split("_")[1] for p in HRFCO.glob("waterlevel_*_1H.csv"))
    data = build_dataset(codes, args.calm_keep, args.seed)
    y_all = data["target_maxrise_6h"].to_numpy(dtype=float)
    train_mask = (data["month"] != args.holdout).to_numpy()
    train, hold = data[train_mask].reset_index(drop=True), data[~train_mask].reset_index(drop=True)
    y, groups = y_all[train_mask], train["month"].to_numpy()
    with_rain = int(train["sfc_rain_6h"].notna().sum())
    print(f"stations {len(codes)}  rows {len(data):,} (train {len(train):,}, holdout {args.holdout} {len(hold):,})  rows with rain {with_rain:,}  active {int(data['active'].sum()):,}", flush=True)

    metrics: dict = {"trained_at": datetime.now().isoformat(timespec="seconds"), "stations": len(codes), "station_codes": codes, "rows": int(len(data)), "train_rows": int(len(train)),
                     "holdout_month": args.holdout, "holdout_rows": int(len(hold)), "rows_with_rain": with_rain, "calm_keep": args.calm_keep, "params": {**PARAMS, "rounds": args.rounds},
                     "contract": "water-level-rise/baseline.py FEATURES (water lags + sfc rain) without imerg/radar/basin; target max(WL(t+1..t+6)) - WL(t)",
                     "qc": f"readings beside a 1 h step > {JUMP_M} m dropped; rows need all lags and all 6 future hours present"}
    if not args.skip_cv:
        oof = np.full(len(train), np.nan)
        folds = []
        for fold, (a, b) in enumerate(GroupKFold(args.folds).split(train, y, groups), 1):
            stats = station_stats(train.iloc[a])
            model = fit(make_features(train.iloc[a], stats), y[a], args.rounds, args.seed)
            oof[b] = model.predict(make_features(train.iloc[b], stats))
            folds.append({"fold": fold, "months": int(np.unique(groups[b]).size), "rows": int(len(b)), "rmse_m": round(rmse(y[b], oof[b]), 4)})
            print(json.dumps(folds[-1]), flush=True)
        big = y > 1
        persist = np.zeros_like(y)
        linear = (train["wl_t"] - train["wl_t_minus_1h"]).clip(lower=0).to_numpy() * HORIZON
        metrics["cv"] = {"folds": folds, "oof_rmse_m": round(rmse(y, oof), 4), "oof_rmse_target_gt_1m": round(rmse(y[big], oof[big]), 4), "rows_target_gt_1m": int(big.sum()),
                         "baseline_no_change_rmse_m": round(rmse(y, persist), 4), "baseline_linear_rmse_m": round(rmse(y, linear), 4),
                         "baseline_no_change_rmse_target_gt_1m": round(rmse(y[big], persist[big]), 4), "baseline_linear_rmse_target_gt_1m": round(rmse(y[big], linear[big]), 4)}
        print(json.dumps(metrics["cv"]), flush=True)

    stats = station_stats(train)
    model = fit(make_features(train, stats), y, args.rounds, args.seed)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    # LightGBM cannot open non-ASCII paths on Windows; write the model text ourselves (load with Booster(model_str=...)).
    MODEL_FILE.write_text(model.model_to_string(), encoding="utf-8")
    STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    importance = dict(sorted(zip(model.feature_name(), model.feature_importance("gain").round(1).tolist()), key=lambda kv: -kv[1]))
    metrics["features"] = model.feature_name()
    metrics["importance_gain"] = {k: v for k, v in list(importance.items())[:12]}
    if len(hold):
        yh = hold["target_maxrise_6h"].to_numpy(dtype=float)
        ph = model.predict(make_features(hold, stats))
        lh = (hold["wl_t"] - hold["wl_t_minus_1h"]).clip(lower=0).to_numpy() * HORIZON
        metrics["holdout"] = {"rows": int(len(hold)), "rmse_model_m": round(rmse(yh, ph), 4), "rmse_no_change_m": round(rmse(yh, np.zeros_like(yh)), 4), "rmse_linear_m": round(rmse(yh, lh), 4),
                              "threshold_skill": threshold_skill(hold, {"model": ph, "linear": lh, "persist": np.zeros_like(yh)})}
    # Osong window from the unsampled series so every hour is present.
    full = station_frame(OSONG["station"], rain_pairs().get(OSONG["station"])) if OSONG["station"] in codes else pd.DataFrame()
    metrics["osong_2023_07_15"] = osong_check(model, stats, full) if len(full) else {"available": False}
    metrics["model_file"] = str(MODEL_FILE.relative_to(REPO_ROOT)).replace("\\", "/")
    metrics["lightgbm"] = lgb.__version__
    METRICS_FILE.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    CARD_FILE.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("holdout", "osong_2023_07_15") if k in metrics}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
