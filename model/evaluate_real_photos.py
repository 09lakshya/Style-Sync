r"""Score the served models against hand-labelled real-world photos.

The test split's macro F1 measures agreement with the training labels, and those
labels are noisy: Myntra's `season` is the catalogue season, so most jackets are
"summer" and a model that copies that scores well while calling a puffer jacket
a summer garment. This set is labelled by looking at the photo, so it measures
what a user would see.

Labels live in model/real_photos.csv, one row per photo in data/. Each column
holds every acceptable answer separated by `|`; a blank cell is not scored.

  * Classifier occasion/season: correct when something fired and everything that
    fired is acceptable. Firing nothing counts as a miss, not a pass.
  * Classifier tradition, CLIP type/colour/pattern: the one answer is acceptable.
  * CLIP season: the expected season is present and its opposite is not.

The classifier's season head is scored even though serving withholds it, so a
retrain can be compared against it.

    backend\.venv\Scripts\python.exe model\evaluate_real_photos.py
    backend\.venv\Scripts\python.exe model\evaluate_real_photos.py --json model\artifacts\real_photos_eval.json
"""

import argparse
import csv
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

LABELS_PATH = ROOT / "model" / "real_photos.csv"
PHOTO_DIR = ROOT / "data"

OPPOSITE_SEASON = {"summer": "winter", "winter": "summer"}


def accepted(cell: str) -> set[str]:
    return {value.strip().lower() for value in cell.split("|") if value.strip()}


def fired(probabilities, thresholds, labels) -> list[str]:
    return [name for name in labels if probabilities.get(name, 0.0) >= thresholds[name]]


def score_set(predicted: list[str], allowed: set[str]) -> bool:
    return bool(predicted) and set(predicted) <= allowed


def score_clip_season(predicted: list[str], expected: set[str]) -> bool:
    seasons = set(predicted)
    return all(s in seasons and OPPOSITE_SEASON[s] not in seasons for s in expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", type=Path, help="also write per-photo results here")
    args = parser.parse_args()
    json_path = args.json.resolve() if args.json else None

    logging.disable(logging.WARNING)
    # The backend resolves its checkpoint and .env relative to backend/.
    os.chdir(ROOT / "backend")
    from PIL import Image

    from app.modules.ai.classifier_manager import classifier_manager
    from app.modules.ai.service import ai_service

    ai_service.clip.load_model()
    classifier_manager.load_model()
    try:
        from app.modules.ai.subject_detector import subject_detector

        subject_detector.load_model()
    except Exception:
        pass
    if not (classifier_manager.is_loaded and ai_service.clip.is_loaded):
        raise SystemExit("Both the classifier and CLIP must load; scoring a fallback measures nothing.")

    axis_labels = {axis: d.get("labels", []) for axis, d in classifier_manager.axes.items()}
    thresholds = classifier_manager.thresholds

    with open(LABELS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    checks = ["clf occasion", "clf season", "clf tradition",
              "clip type", "clip colour", "clip pattern", "clip season", "clip tradition"]
    totals = {name: [0, 0] for name in checks}
    # A vague season ("all_season") and a wrong one (summer for a puffer) both
    # miss, but only the second misleads a user, so count it separately.
    contradicted = {"clf season": 0, "clip season": 0}
    results = []

    for row in rows:
        path = PHOTO_DIR / row["file"]
        if not path.exists():
            print(f"skip {row['file']}: not in {PHOTO_DIR}")
            continue
        data = path.read_bytes()

        probabilities = classifier_manager.predict_axes(Image.open(io.BytesIO(data)))["probabilities"]
        occasion = fired(probabilities, thresholds, axis_labels["occasion"])
        season = fired(probabilities, thresholds, axis_labels["season"])
        tradition = "ethnic" if fired(probabilities, thresholds, axis_labels["tradition"]) else "western"
        clip = ai_service.extract_clothing_metadata(file_bytes=data, filename=row["file"])
        clip_tradition = "ethnic" if clip.get("is_ethnic") else "western"

        predictions = {
            "clf occasion": occasion,
            "clf season": season,
            "clf tradition": tradition,
            "clip type": clip.get("type"),
            "clip colour": clip.get("primary_color"),
            "clip pattern": clip.get("pattern"),
            "clip season": clip.get("season", []),
            "clip tradition": clip_tradition,
        }
        expected = {
            "clf occasion": accepted(row["occasion"]),
            "clf season": accepted(row["season"]),
            "clf tradition": accepted(row["tradition"]),
            "clip type": accepted(row["type"]),
            "clip colour": accepted(row["color"]),
            "clip pattern": accepted(row["pattern"]),
            "clip season": accepted(row["season"]),
            "clip tradition": accepted(row["tradition"]),
        }

        outcome = {}
        for name in checks:
            if not expected[name]:
                continue
            if name in ("clf occasion", "clf season"):
                ok = score_set(predictions[name], expected[name])
            elif name == "clip season":
                ok = score_clip_season(predictions[name], expected[name])
            else:
                ok = str(predictions[name]).lower() in expected[name]
            outcome[name] = ok
            totals[name][0] += ok
            totals[name][1] += 1
            if name in contradicted and any(OPPOSITE_SEASON[s] in predictions[name] for s in expected[name]):
                contradicted[name] += 1

        misses = [f"{name}={predictions[name]} (want {'|'.join(sorted(expected[name]))})"
                  for name, ok in outcome.items() if not ok]
        print(f"{row['file']:16} {sum(outcome.values())}/{len(outcome)}  " + ("; ".join(misses) or "all correct"))
        results.append({
            "file": row["file"],
            "predictions": predictions,
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "correct": outcome,
        })

    print()
    print(f"{'check':16} correct")
    for name, (ok, n) in totals.items():
        if n:
            extra = f"  ({contradicted[name]} named the opposite season)" if name in contradicted else ""
            print(f"{name:16} {ok:2}/{n:<2}  {ok / n:.0%}{extra}")

    if json_path:
        json_path.write_text(json.dumps({
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "model_version": classifier_manager.model_version,
            "photos": len(results),
            "totals": {name: {"correct": ok, "scored": n} for name, (ok, n) in totals.items()},
            "opposite_season": contradicted,
            "results": results,
        }, indent=2))
        print(f"\nWrote {json_path}")


if __name__ == "__main__":
    main()
