"""Build a Docker build context (tar.gz) for a server that runs the national watch board.

    python deploy/build_context.py [out.tar.gz]

`Dockerfile.aws` predates the watch board and leaves out what `#watch` reads: the HRFCO hourly series, the gauge
catalogue, facility links, the river-type research table (under docs/, which .dockerignore drops), official
forecast history, the validation scorecard and the KMA AWS station list. The hourly series is 847 MB locally and
mostly untracked, so this context keeps it trimmed:

- full series for the gauges tracked in git (미호강 3 water-level + 4 rain gauges: the operational facility and
  its backtest use every year),
- every other gauge only inside REPLAY_WINDOWS (the validation cases and the default replay), which is all the
  board and `case_validation` read.

Code and tracked data come from `git archive HEAD`, so uncommitted work in the tree never ships.
"""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOURLY = ROOT / "data" / "processed" / "hrfco"
DEFAULT_OUT = ROOT.parent / "floodops-deploy-context.tar.gz"
REPLAY_WINDOWS = [("2020-07-25", "2020-08-03"), ("2023-07-10", "2023-07-18"), ("2024-07-05", "2024-07-13")]
ARCHIVE_PATHS = [
    "Dockerfile.deploy", "package.json", "package-lock.json", "index.html", "tsconfig.json", "tsconfig.app.json", "vite.config.ts",
    "src", "public", "backend/requirements.txt", "backend/app",
    "data/processed/osong", "data/processed/seoul_2022", "data/processed/pohang_2022", "data/processed/andong_uiseong_2026",
    "data/models", "data/facilities", "data/manifests", "data/processed/facilities", "data/processed/flood_forecast",
    "data/processed/validation", "data/processed/kma", "data/processed/platform",
    "docs/research/underpass_river_influence/facility_river_influence_ranked.csv",
]
DOCKERIGNORE = b"node_modules\n.git\n.env\n.env.*\n"


def _in_windows(line: str) -> bool:
    day = line[:10]
    return any(start <= day <= end for start, end in REPLAY_WINDOWS)


def _trimmed(path: Path) -> bytes:
    with path.open(encoding="utf-8") as handle:
        header = handle.readline()
        rows = [line for line in handle if _in_windows(line)]
    return (header + "".join(rows)).encode("utf-8")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    tracked = set(subprocess.run(["git", "ls-files", "data/processed/hrfco"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split())
    existing = [p for p in ARCHIVE_PATHS if subprocess.run(["git", "cat-file", "-e", f"HEAD:{p}"], cwd=ROOT, capture_output=True).returncode == 0]
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD", *existing, *sorted(tracked)], cwd=ROOT, capture_output=True, check=True).stdout
    total_full = total_trim = 0
    with tarfile.open(out, "w:gz") as bundle:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source.getmembers():
                bundle.addfile(member, source.extractfile(member) if member.isfile() else None)
        for path in sorted(HOURLY.glob("*.csv")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in tracked:
                continue
            data = path.read_bytes() if path.name.endswith("_10M.csv") else _trimmed(path)
            total_full += path.stat().st_size
            total_trim += len(data)
            info = tarfile.TarInfo(rel)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
        info = tarfile.TarInfo(".dockerignore")
        info.size = len(DOCKERIGNORE)
        bundle.addfile(info, io.BytesIO(DOCKERIGNORE))
    print(f"{out} · {out.stat().st_size / 1e6:.1f} MB · untracked HRFCO {total_full / 1e6:.0f} MB → {total_trim / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
