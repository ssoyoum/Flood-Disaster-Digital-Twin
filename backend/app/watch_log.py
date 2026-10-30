"""Record the live board every 10 minutes and score every facility from that record, without historical downloads.

Each line of data/local/watch-log/YYYY.jsonl is one board snapshot: the time, how many facilities were assessed,
and only the facilities at 관심 or above (level, whether an official flood forecast applied). A facility that is
calm costs nothing to store. The season board then reads the lines back and, per facility, joins consecutive
snapshots at 주의 or above into episodes and counts how long each level lasted.

Only live snapshots are written: replay and the synthetic rain test never enter the record.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERVAL_SECONDS = 600
GAP_MINUTES = 30  # a missing snapshot or two does not split an episode
LEVEL_KO = {1: "관심", 2: "주의", 3: "경계", 4: "심각"}
_LOCK = threading.Lock()
_started = False


def log_dir() -> Path:
    return Path(os.environ.get("FLOODOPS_WATCH_LOG_DIR", REPO_ROOT / "data" / "local" / "watch-log"))


def record_once() -> dict[str, Any] | None:
    from . import facility_risk

    risk = facility_risk.facility_risk(limit=10000)
    if risk.get("mode") != "live":
        return None
    line = {"at": risk["at"], "observed_at": risk.get("observed_at"), "rain_at": risk.get("rain_at"), "total": risk["counts"]["total"],
            "facilities": {row["facility_id"]: [row["level"], 1 if row.get("official") else 0]
                           for row in risk["facilities"] if row["level"] >= 1}}
    path = log_dir() / f"{risk['at'][:4]}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n")
    return line


def _loop() -> None:
    time.sleep(60)
    while True:
        try:
            record_once()
        except Exception as exc:  # noqa: BLE001 - one failed snapshot must not stop the recorder
            print(f"watch_log: snapshot failed: {exc}")
        time.sleep(INTERVAL_SECONDS)


def start_background() -> bool:
    """Start the recorder once per process when the board runs live. Set FLOODOPS_WATCH_LOG=off to disable."""
    global _started
    if _started or os.environ.get("FLOODOPS_WATCH_LOG", "").lower() == "off":
        return False
    from .twin import twin_mode

    if twin_mode()["mode"] != "live":
        return False
    _started = True
    threading.Thread(target=_loop, name="watch-log", daemon=True).start()
    return True


def _snapshots(year: int) -> list[dict[str, Any]]:
    path = log_dir() / f"{year}.jsonl"
    if not path.exists():
        return []
    with _LOCK, path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def season_board(year: int, limit: int = 300) -> dict[str, Any]:
    from . import facility_risk
    from .national_watch import facility_catalog

    snaps = _snapshots(year)
    catalog = {f["facility_id"]: f for f in facility_catalog()}
    drivers = {fid: facility_risk.driver_of(f)[0] for fid, f in catalog.items()}
    per: dict[str, dict[str, Any]] = {}
    previous: dict[str, datetime] = {}
    for snap in snaps:
        at = datetime.fromisoformat(snap["at"])
        for fid, (level, official) in snap["facilities"].items():
            row = per.setdefault(fid, {"minutes": {k: 0 for k in LEVEL_KO}, "peak": 0, "episodes": [], "first_at": snap["at"]})
            row["minutes"][level] += INTERVAL_SECONDS // 60
            row["peak"] = max(row["peak"], level)
            if level < 2:
                continue
            last = previous.get(fid)
            if last is None or at - last > timedelta(minutes=GAP_MINUTES):
                row["episodes"].append({"start": snap["at"], "end": snap["at"], "peak": level, "official": bool(official)})
            else:
                episode = row["episodes"][-1]
                episode.update(end=snap["at"], peak=max(episode["peak"], level), official=episode["official"] or bool(official))
            previous[fid] = at

    rows = []
    for fid, row in per.items():
        facility = catalog.get(fid, {})
        episodes = row["episodes"]
        rows.append({
            "facility_id": fid, "name": facility.get("name", fid), "kind_ko": facility.get("kind_ko"), "region": facility.get("region"),
            "driver": drivers.get(fid), "peak_level": row["peak"], "peak_label": LEVEL_KO.get(row["peak"]),
            "episodes": len(episodes), "episodes_with_official": sum(e["official"] for e in episodes),
            "episodes_alone": sum(not e["official"] for e in episodes),
            "minutes_by_level": {LEVEL_KO[k]: v for k, v in row["minutes"].items()},
            "first_alert_at": episodes[0]["start"] if episodes else None, "last_episode": episodes[-1] if episodes else None,
        })
    rows.sort(key=lambda r: (-r["peak_level"], -r["episodes"], -sum(r["minutes_by_level"].values()), r["name"]))
    coverage = {"snapshots": len(snaps), "from": snaps[0]["at"] if snaps else None, "to": snaps[-1]["at"] if snaps else None,
                "interval_min": INTERVAL_SECONDS // 60, "facilities_assessed": snaps[-1]["total"] if snaps else len(catalog)}
    return {
        "season": year, "coverage": coverage,
        "counts": {"facilities": coverage["facilities_assessed"],
                   "reached": {LEVEL_KO[k]: sum(1 for r in rows if r["peak_level"] >= k) for k in (2, 3, 4)},
                   "episodes": sum(r["episodes"] for r in rows),
                   "episodes_with_official": sum(r["episodes_with_official"] for r in rows),
                   "episodes_alone": sum(r["episodes_alone"] for r in rows)},
        "facilities": rows[:limit],
        "method": f"서버가 {INTERVAL_SECONDS // 60}분마다 실시간 보드를 기록하고, 주의 이상이 {GAP_MINUTES}분 넘게 끊기지 않고 이어진 구간을 한 번의 경보 구간으로 셉니다.",
        "limitations": [
            "기록을 시작한 시각 이전은 채점하지 않습니다. 과거 이력을 내려받아 채우지 않습니다.",
            "공식 특보가 함께였는지는 하천형 시설의 홍수특보만 봅니다. 혼자 울린 구간은 헛경보 후보이며 오경보로 확정하지 않습니다.",
            "서버가 멈춘 동안은 기록이 비고, 그 시간은 평상으로 세지 않고 빠진 것으로 둡니다.",
        ],
    }
