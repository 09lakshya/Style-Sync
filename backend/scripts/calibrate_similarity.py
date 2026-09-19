"""Calibrate the duplicate-detection thresholds against real garment photographs.

Measures the CLIP cosine distribution over the curated dataset in three buckets:

  identical    the same file compared with itself      -> the true-duplicate case
  same_class   two images from the same category       -> visually related, not duplicates
  diff_class   images from different categories        -> unrelated

A duplicate detector is only meaningful if `identical` separates from the other
two. VISUAL_DUPLICATE_GATE is recommended from the observed false-positive rate:
the gate must sit above almost all non-duplicate pairs, otherwise unrelated items
get reported as duplicates.

Run from the backend directory:
    python scripts/calibrate_similarity.py
"""

import glob
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.ai.clip_manager import clip_manager  # noqa: E402
from app.modules.ai.service import ai_service, cosine_similarity  # noqa: E402

CURATED = Path(__file__).resolve().parents[2] / "dataset" / "curated" / "test"
ARTIFACT = Path(__file__).resolve().parents[2] / "model" / "artifacts" / "similarity_calibration.json"
PER_CLASS = 8


def percentile(sorted_values, p):
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, int(round(p * (len(sorted_values) - 1))))
    return sorted_values[idx]


def summarize(name, values):
    values = sorted(values)
    if not values:
        return {"name": name, "n": 0}
    return {
        "name": name,
        "n": len(values),
        "min": round(values[0], 4),
        "p05": round(percentile(values, 0.05), 4),
        "median": round(statistics.median(values), 4),
        "p95": round(percentile(values, 0.95), 4),
        "p99": round(percentile(values, 0.99), 4),
        "max": round(values[-1], 4),
        "mean": round(statistics.mean(values), 4),
    }


def main():
    if not CURATED.is_dir():
        raise SystemExit(f"ERROR: curated test split not found at {CURATED}")

    clip_manager.load_model()

    classes = sorted(d.name for d in CURATED.iterdir() if d.is_dir())
    paths = {}
    for c in classes:
        found = []
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            found.extend(glob.glob(str(CURATED / c / ext)))
        paths[c] = sorted(found)[:PER_CLASS]

    print(f"Embedding {sum(len(v) for v in paths.values())} images across {len(classes)} classes...")
    emb = {}
    for c, files in paths.items():
        for f in files:
            emb[f] = ai_service.generate_image_embedding(Path(f).read_bytes())

    identical, same_class, diff_class = [], [], []

    for c, files in paths.items():
        for f in files:
            identical.append(cosine_similarity(emb[f], emb[f]))
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                same_class.append(cosine_similarity(emb[files[i]], emb[files[j]]))

    for a in classes:
        for b in classes:
            if a >= b:
                continue
            for fa in paths[a]:
                for fb in paths[b]:
                    diff_class.append(cosine_similarity(emb[fa], emb[fb]))

    buckets = [summarize("identical", identical),
               summarize("same_class", same_class),
               summarize("diff_class", diff_class)]

    print()
    for b in buckets:
        print(f"{b['name']:<12} n={b['n']:<5} min={b['min']:.4f} median={b['median']:.4f} "
              f"p95={b['p95']:.4f} p99={b['p99']:.4f} max={b['max']:.4f}")

    # A non-duplicate pair is anything that is not the same image.
    non_duplicate = sorted(same_class + diff_class)
    gate = percentile(non_duplicate, 0.99)
    headroom = min(identical) - gate if identical else 0.0

    print()
    print(f"non-duplicate pairs: {len(non_duplicate)}")
    print(f"  p99  = {gate:.4f}   <- recommended VISUAL_DUPLICATE_GATE")
    print(f"  max  = {non_duplicate[-1]:.4f}")
    print(f"identical min = {min(identical):.4f}")
    print(f"headroom between the gate and a true duplicate: {headroom:.4f}")

    if headroom <= 0.01:
        print("\n  WARNING: almost no separation. CLIP cannot distinguish duplicates from")
        print("  merely similar items on this data; the gate would be arbitrary.")
        verdict = "not_separable"
    elif headroom < 0.05:
        print("\n  Separation is thin. The gate will work for exact duplicates but has")
        print("  little margin for re-encoded or lightly edited images.")
        verdict = "thin"
    else:
        print("\n  Separation is clear; the gate is well founded.")
        verdict = "separable"

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps({
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "images_per_class": PER_CLASS,
        "classes": classes,
        "buckets": buckets,
        "recommended_visual_duplicate_gate": round(gate, 4),
        "identical_min": round(min(identical), 4) if identical else None,
        "headroom": round(headroom, 4),
        "verdict": verdict,
    }, indent=2))
    print(f"\nWritten to {ARTIFACT}")


if __name__ == "__main__":
    main()
