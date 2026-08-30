"""Extract the 2022 Seoul flood-event rainfall window from the official ZIP."""

import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path


RAW_ZIP = Path("data/raw/rainfall/seoul_rainfall_2022.zip")
OUTPUT = Path("data/processed/seoul_rainfall_2022_event.csv")
START = datetime.fromisoformat("2022-08-08 00:00")
END = datetime.fromisoformat("2022-08-17 23:59")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    max_rainfall = 0.0

    with zipfile.ZipFile(RAW_ZIP) as archive:
        august_file = next(name for name in archive.namelist() if "2022" in name and "08" in name)
        source = io.StringIO(archive.read(august_file).decode("cp949"))
        reader = csv.DictReader(source)

        with OUTPUT.open("w", encoding="utf-8-sig", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "station_code",
                    "station_name",
                    "district_code",
                    "district_name",
                    "rainfall_10min_mm",
                    "observed_at",
                ],
            )
            writer.writeheader()

            for row in reader:
                observed_at = datetime.fromisoformat(row["자료수집 시각"])
                if not START <= observed_at <= END:
                    continue
                rainfall = float(row["10분우량"] or 0)
                writer.writerow(
                    {
                        "station_code": row["강우량계 코드"],
                        "station_name": row["강우량계명"],
                        "district_code": row["구청 코드"],
                        "district_name": row["구청명"],
                        "rainfall_10min_mm": rainfall,
                        "observed_at": observed_at.isoformat(sep=" "),
                    }
                )
                rows_written += 1
                max_rainfall = max(max_rainfall, rainfall)

    print(f"output={OUTPUT} rows={rows_written} max_10min_mm={max_rainfall}")


if __name__ == "__main__":
    main()
