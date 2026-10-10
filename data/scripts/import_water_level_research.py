"""Import a verified research contract, not anonymized observations or serialized models."""
import argparse
import ast
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    source = project / "baseline.py"
    features = None
    for node in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "FEATURES" for target in node.targets):
            features = list(ast.literal_eval(node.value))
    if not features or len(features) != 22:
        raise ValueError("Review the source input contract before importing a changed schema")
    metrics_path = project / "artifacts/blend_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    oof_path = project / "artifacts/blend_oof.csv"
    count = tail_count = 0
    sse = tail_sse = 0.0
    with oof_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            target, prediction = float(row["target"]), float(row["prediction"])
            if not math.isfinite(target) or not math.isfinite(prediction):
                raise ValueError("Non-finite OOF values")
            error = (target - prediction) ** 2
            sse += error
            count += 1
            if target > 1:
                tail_sse += error
                tail_count += 1
    rmse, tail_rmse = math.sqrt(sse / count), math.sqrt(tail_sse / tail_count)
    if not math.isclose(rmse, metrics["oof_global_rmse_m"], rel_tol=0, abs_tol=1e-10) or not math.isclose(tail_rmse, metrics["target_gt_1m_rmse_m"], rel_tol=0, abs_tol=1e-10):
        raise ValueError("OOF values disagree with the source metrics")
    with (project / "artifacts/blend_submission.csv").open(encoding="utf-8-sig", newline="") as handle:
        test_count = sum(1 for _ in csv.DictReader(handle))
    if test_count != metrics["test_rows"] or sum(fold["rows"] for fold in metrics["folds"]) != count:
        raise ValueError("Source row counts disagree")
    manifest = {
        "schema_version": "1.0", "project": "water-level-rise",
        "imported_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "status": "RESEARCH_ONLY", "target": "max(WL(t+1h),...,WL(t+6h))-WL(t)",
        "horizon_hours": 6, "target_unit": "m", "negative_target_valid": True,
        "station_identity": "anonymous", "timestamp_identity": "synthetic",
        "real_station_mapping_available": False, "facility_validation_complete": False,
        "required_features": features, "trained_features": metrics["features"],
        "models": metrics["models"], "seeds": metrics["seeds"],
        "evaluation": {"type": "source_project_train_oof", "rows": count, "test_prediction_rows": test_count,
                       "global_rmse_m": rmse, "target_gt_1m_rows": tail_count, "target_gt_1m_rmse_m": tail_rmse,
                       "folds": metrics["folds"], "recomputed_from_oof": True,
                       "floodops_facility_score": None},
        "provenance": [{"file": str(path.relative_to(project)).replace("\\", "/"),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                       for path in (source, project / "train_lgbm.py", metrics_path, oof_path)],
        "limits": ["익명 관측소·합성 시각을 실제 시설/시각과 연결하지 않는다.",
                   "대회 내부 OOF 오차는 FloodOps 실제 시설 예측 성능이 아니다.",
                   "6시간 최대 상승량은 임계 도달 시각·침수심·통제 명령이 아니다.",
                   "실제 관측의 단위·처리·유역 대표성을 확인하고 실측 사건으로 별도 학습·검증해야 한다."],
    }
    destination = ROOT / "data/manifests/water-level-research.json"
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"oof_rows": count, "global_rmse_m": rmse, "target_gt_1m_rmse_m": tail_rmse, "features": len(features)}))


if __name__ == "__main__":
    main()
