r"""Score Gemini item detection against the hand-labelled real-world photos.

Gemini is what the add-item form uses whenever an API key is configured, so it
is the detector users actually see; evaluate_real_photos.py scores only the
local classifier and CLIP, which serve as the fallback. Same labels
(model/real_photos.csv), same photos (data/), comparable rules:

  * type / colour / pattern / tradition: the one answer is acceptable.
  * season: every expected season is present and its opposite is not.
  * occasion: at least one predicted occasion is acceptable. This is more
    lenient than the classifier's rule (everything that fired must be
    acceptable) because Gemini lists every occasion a garment suits.

Each photo is one Gemini request, so this spends API quota. On a quota error
it waits out the pause and retries; a photo that still gets no answer is
reported and left out of the totals.

    backend\.venv\Scripts\python.exe model\evaluate_gemini_photos.py
    backend\.venv\Scripts\python.exe model\evaluate_gemini_photos.py --json model\artifacts\gemini_photos_eval.json
"""

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCH_DIR = Path.cwd()
sys.path.insert(0, str(ROOT / "backend"))
# Settings read backend/.env relative to the working directory.
os.chdir(ROOT / "backend")

from app.modules.ai.gemini_service import gemini_service  # noqa: E402
from app.modules.wardrobe.normalise import (  # noqa: E402
    normalise_color,
    normalise_occasions,
    normalise_pattern,
    normalise_seasons,
    normalise_type,
)

LABELS_PATH = ROOT / "model" / "real_photos.csv"
PHOTO_DIR = ROOT / "data"
OPPOSITE_SEASON = {"summer": "winter", "winter": "summer"}


def accepted(cell: str) -> set[str]:
    return {value.strip().lower() for value in cell.split("|") if value.strip()}


def score(row: dict[str, str], pred: dict[str, object]) -> dict[str, bool]:
    ok: dict[str, bool] = {}
    if row["occasion"]:
        allowed = set(normalise_occasions(list(accepted(row["occasion"]))))
        ok["occasion"] = any(o in allowed for o in pred["occasion"])
    if row["season"]:
        seasons = set(pred["season"])
        ok["season"] = all(s in seasons and OPPOSITE_SEASON[s] not in seasons for s in accepted(row["season"]))
    for check, column in (("tradition", "tradition"), ("type", "type"), ("colour", "color"), ("pattern", "pattern")):
        if row[column]:
            ok[check] = pred[check] in accepted(row[column])
    return ok


async def detect_waiting_out_quota(image: bytes, mime: str, attempts: int = 3):
    """Detect one photo; on a quota pause, wait it out and try again.

    The app falls back to the local models during a pause, which is right for a
    user but would leave holes in an evaluation.
    """
    for _ in range(attempts):
        started = time.monotonic()
        res = await gemini_service.detect_clothing_item(image, mime)
        seconds = time.monotonic() - started
        if res or not gemini_service.is_paused:
            return res, seconds
        wait = gemini_service._paused_until - time.monotonic() + 1
        print(f"  quota pause - waiting {wait:.0f}s")
        await asyncio.sleep(max(wait, 1))
    return None, seconds


async def main(json_path: Path | None) -> None:
    if not gemini_service.is_configured:
        sys.exit("No Gemini API key configured (GEMINI_API_KEY in backend/.env).")

    rows = list(csv.DictReader(open(LABELS_PATH, encoding="utf-8")))
    totals: dict[str, list[int]] = {}
    results = []
    unanswered = 0
    for row in rows:
        path = PHOTO_DIR / row["file"]
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        res, seconds = await detect_waiting_out_quota(path.read_bytes(), mime)
        if not res:
            unanswered += 1
            print(f"{row['file']:16} no answer after {seconds:.1f}s")
            results.append({"file": row["file"], "answered": False})
            continue

        pred = {
            "occasion": normalise_occasions(res.get("occasion", [])),
            "season": normalise_seasons(res.get("season", [])),
            "tradition": "ethnic" if res.get("is_ethnic") else "western",
            "type": normalise_type(res.get("type")) or "",
            "colour": normalise_color(res.get("color")) or "",
            "pattern": normalise_pattern(res.get("pattern")) or "",
        }
        ok = score(row, pred)
        for check, passed in ok.items():
            tally = totals.setdefault(check, [0, 0])
            tally[0] += passed
            tally[1] += 1
        misses = "; ".join(f"{c}={pred[c]} (want {row[{'colour': 'color'}.get(c, c)]})" for c, p in ok.items() if not p)
        print(f"{row['file']:16} {sum(ok.values())}/{len(ok)}  {seconds:4.1f}s  {res.get('name')!r}  {misses}")
        results.append({
            "file": row["file"], "answered": True, "name": res.get("name"), "model": res.get("model_used"),
            "seconds": round(seconds, 1), "predictions": pred, "correct": ok,
        })

    print(f"\n{'check':16} correct")
    for check, (correct, scored) in totals.items():
        print(f"gemini {check:9} {correct:2}/{scored:<2} {100 * correct / scored:3.0f}%")
    if unanswered:
        print(f"\n{unanswered} photo(s) got no answer and are not in the totals.")

    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps({
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "totals": {k: {"correct": c, "scored": n} for k, (c, n) in totals.items()},
            "unanswered": unanswered,
            "results": results,
        }, indent=1), encoding="utf-8")
        print(f"Wrote {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="also write the results to this file")
    json_arg = parser.parse_args().json
    # Relative to where the script was launched, not backend/ (see os.chdir above).
    asyncio.run(main(LAUNCH_DIR / json_arg if json_arg else None))
