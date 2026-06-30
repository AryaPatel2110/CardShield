"""Fail-fast readiness check for a CardShield live demonstration."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = {
        "trained Spark model": ROOT / "models/fraud_pipeline",
        "categorical encoders": ROOT / "models/encoders/categories-v1.json",
        "replay dataset": ROOT / "data/clean_test.csv",
    }
    failures = 0
    print("CardShield demo preflight")
    for label, path in required.items():
        ready = path.exists()
        failures += int(not ready)
        print(f"  {'READY' if ready else 'MISSING':7} {label}: {path.relative_to(ROOT)}")

    metadata_path = ROOT / "models/fraud_pipeline-metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metrics = metadata.get("metrics", {})
        print(
            "  METRICS "
            f"recall={metrics.get('fraud_recall', 0):.3f} "
            f"precision={metrics.get('fraud_precision', 0):.3f} "
            f"PR-AUC={metrics.get('area_under_pr', 0):.3f}"
        )
        if metrics.get("fraud_recall", 0) < 0.5:
            print("  WARNING fraud recall is below the 0.50 demo gate")
        if metrics.get("fraud_precision", 0) < 0.2:
            print("  WARNING fraud precision is below the 0.20 demo gate")
    else:
        failures += 1
        print("  MISSING release model evaluation metadata")

    for command in ("docker",):
        ready = shutil.which(command) is not None
        failures += int(not ready)
        print(f"  {'READY' if ready else 'MISSING':7} command: {command}")

    if failures:
        print(f"\nPreflight failed with {failures} blocking item(s).")
        return 1
    print("\nPreflight passed. Start with: docker compose --profile demo up --build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
