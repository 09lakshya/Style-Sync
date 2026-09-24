"""Map the Myntra 44k catalogue onto StyleSync's three label axes.

The seven-class folder taxonomy (Casual/Party/Formal/Ethnic/Western/Summer/
Winter) flattens three independent questions into one label, so a cotton kurta
has to choose between Ethnic, Summer and Casual when all three are true. This
script keeps them apart, the way backend/app/modules/ai/service.py and
frontend/src/types/wardrobe.ts already do:

    occasion   casual | formal | party     (multi-label)
    season     summer | winter             (multi-label)
    tradition  ethnic | western            (binary)

Myntra labels `usage` and `season` per item independently, which is exactly
this supervision, already annotated.

Not every row answers every axis, and nothing here fills a gap by guessing. A
`usage` of Ethnic says what tradition a garment belongs to but not what
occasion it suits; a `season` of Fall or Spring has no home in a summer/winter
split. Those axes are left unlabelled and carry a mask of 0, so the loss
ignores them instead of training on an invented answer. Every row that is
dropped, and every axis left blank, is counted in the report.

Output is a manifest, not a copied tree: at 23GB the catalogue is not worth
duplicating, and a multi-label set cannot be expressed as one-folder-per-class
for ImageFolder anyway. Pass --stage to copy the selected images as well.

    python dataset/scripts/00_ingest_myntra.py --dry-run
    python dataset/scripts/00_ingest_myntra.py
"""

import argparse
import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = BASE_DIR / "raw" / "myntra"
DEFAULT_STAGED = BASE_DIR / "myntra"
PROCESSED_DIR = BASE_DIR / "processed"
MANIFEST = PROCESSED_DIR / "00_myntra_manifest.csv"

# Kept in step with 00_ingest_custom.py's floor and the trained input size.
MIN_WIDTH = 224
MIN_HEIGHT = 224
PHASH_MAX_DISTANCE = 4

OCCASIONS = ["casual", "formal", "party"]
SEASONS = ["summer", "winter"]

# Myntra `usage` -> occasion labels. A value absent here contributes no occasion.
# "Smart Casual" is deliberately casual only: it is a dress-code register, not a
# claim that the garment is also boardroom-formal.
USAGE_TO_OCCASION = {
    "casual": ["casual"],
    "smart casual": ["casual"],
    "formal": ["formal"],
    "party": ["party"],
    "ethnic": [],           # tradition, not occasion -- left unlabelled
    "travel": [],
    "home": [],
}
# Rows whose usage puts them outside the wardrobe StyleSync models at all.
USAGE_EXCLUDED = {"sports"}

# Myntra `season` -> season labels. Fall and Spring have no honest mapping onto
# a two-way summer/winter split, so they are left unlabelled rather than forced.
SEASON_TO_SEASON = {
    "summer": ["summer"],
    "winter": ["winter"],
    "fall": [],
    "spring": [],
}

# articleType values that place a garment on the Ethnic side regardless of what
# `usage` says. Lowercased for comparison.
ETHNIC_ARTICLE_TYPES = {
    "kurtas", "kurtis", "kurta sets", "churidar", "salwar", "salwar and dupatta",
    "patiala", "dupatta", "sarees", "lehenga choli", "sherwani", "nehru jackets",
    "dhotis", "angrakha", "jodhpuri", "mojaris", "blouse", "petticoats",
}

# masterCategory values worth keeping: garments, not watches or fragrances.
KEEP_MASTER = {"apparel"}


def phash(image):
    """64-bit DCT perceptual hash -- identical to 00_ingest_custom.py's."""
    pixels = np.asarray(image.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    k = np.arange(32)
    basis = np.cos(np.pi * (2 * k[:, None] + 1) * k[None, :] / 64)
    basis[:, 0] *= 1 / np.sqrt(2)
    coefficients = basis.T @ pixels @ basis
    low = coefficients[:8, :8]
    bits = low > np.median(low.flatten()[1:])
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


POPCOUNT8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def hamming_all(candidate, known):
    """Distance from candidate to every hash in known, vectorised.

    The linear scan in 00_ingest_custom.py is fine for a few hundred images but
    would be 100M+ Python-level comparisons against a catalogue this size.
    """
    if known.size == 0:
        return np.empty(0, dtype=np.uint8)
    xor = np.bitwise_xor(known, np.uint64(candidate))
    return POPCOUNT8[xor.view(np.uint8).reshape(-1, 8)].sum(axis=1)


def find_styles_csv(source):
    # The Kaggle zip unpacks with a duplicated nested copy of the whole tree, so
    # the shallowest match is taken rather than whichever rglob yields first.
    matches = sorted(source.rglob("styles.csv"), key=lambda p: len(p.parts))
    if not matches:
        sys.exit(
            "ERROR: styles.csv not found under:\n  {}\n\n"
            "Download it first:\n"
            "  kaggle datasets download -d paramaggarwal/fashion-product-images-dataset "
            "-p {} --unzip".format(source, source)
        )
    return matches[0]


def find_images_dir(styles_csv):
    candidate = styles_csv.parent / "images"
    if candidate.is_dir():
        return candidate
    matches = [p for p in sorted(styles_csv.parent.rglob("images")) if p.is_dir()]
    if not matches:
        sys.exit("ERROR: no images/ directory beside {}".format(styles_csv))
    return matches[0]


def read_rows(styles_csv):
    """styles.csv carries unquoted commas in productDisplayName, so the trailing
    field is collected into restkey and ignored rather than tripping the reader.
    """
    with open(styles_csv, newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle, restkey="_overflow")
        required = {"id", "masterCategory", "articleType", "season", "usage"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            sys.exit(
                "ERROR: {} is missing expected column(s): {}\nFound: {}".format(
                    styles_csv, ", ".join(sorted(missing)), ", ".join(reader.fieldnames or [])
                )
            )
        for row in reader:
            yield row


def classify(row):
    """Return ((labels, masks), None) for one catalogue row, or (None, reason)."""
    master = (row.get("masterCategory") or "").strip().lower()
    if master not in KEEP_MASTER:
        return None, "not apparel"

    usage = (row.get("usage") or "").strip().lower()
    if usage in USAGE_EXCLUDED:
        return None, "usage={}".format(usage or "blank")

    article = (row.get("articleType") or "").strip().lower()
    season_raw = (row.get("season") or "").strip().lower()

    occasion = USAGE_TO_OCCASION.get(usage, [])
    season = SEASON_TO_SEASON.get(season_raw, [])
    tradition = "ethnic" if (usage == "ethnic" or article in ETHNIC_ARTICLE_TYPES) else "western"

    # An occasion mask of 0 means "this row does not say", not "none of these".
    labels = {"occasion": occasion, "season": season, "tradition": [tradition]}
    masks = {
        "occasion": 1 if occasion else 0,
        "season": 1 if season else 0,
        "tradition": 1,
    }
    return (labels, masks), None


def encode(labels, masks):
    out = {}
    for name in OCCASIONS:
        out["occasion_{}".format(name)] = int(name in labels["occasion"])
    for name in SEASONS:
        out["season_{}".format(name)] = int(name in labels["season"])
    out["tradition_ethnic"] = int("ethnic" in labels["tradition"])
    out["mask_occasion"] = masks["occasion"]
    out["mask_season"] = masks["season"]
    out["mask_tradition"] = masks["tradition"]
    return out


def existing_hashes(*folders):
    hashes = []
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            try:
                with Image.open(path) as img:
                    hashes.append(phash(img))
            except Exception:
                continue
    return np.array(hashes, dtype=np.uint64)


def ingest(source, staged, curated, dry_run, stage, limit):
    styles_csv = find_styles_csv(source)
    images_dir = find_images_dir(styles_csv)
    print("Catalogue: {}".format(styles_csv))
    print("Images:    {}\n".format(images_dir))

    selected, dropped = [], Counter()
    seen_usage, seen_season, seen_article = Counter(), Counter(), Counter()

    for row in read_rows(styles_csv):
        seen_usage[(row.get("usage") or "blank").strip().lower()] += 1
        seen_season[(row.get("season") or "blank").strip().lower()] += 1
        result, reason = classify(row)
        if result is None:
            dropped[reason] += 1
            continue
        labels, masks = result
        image_path = images_dir / "{}.jpg".format(row["id"].strip())
        if not image_path.is_file():
            dropped["image file missing"] += 1
            continue
        if labels["tradition"] == ["ethnic"]:
            seen_article[(row.get("articleType") or "").strip().lower()] += 1
        selected.append(dict(
            {"id": row["id"].strip(), "path": image_path,
             "articleType": (row.get("articleType") or "").strip()},
            **encode(labels, masks)))
        if limit and len(selected) >= limit:
            break

    print("{} rows selected from the catalogue.\n".format(len(selected)))
    print("usage values seen:")
    for value, count in seen_usage.most_common():
        print("  {:<15} {:>7}".format(value, count))
    print("\nseason values seen:")
    for value, count in seen_season.most_common():
        print("  {:<15} {:>7}".format(value, count))
    print("\nethnic articleTypes matched:")
    for value, count in seen_article.most_common(20):
        print("  {:<22} {:>7}".format(value, count))
    print("\ndropped:")
    for reason, count in dropped.most_common():
        print("  {:<22} {:>7}".format(reason, count))

    if dry_run:
        report(selected, staged, dry_run=True, staged_files=False)
        return 0

    print("\nHashing the existing dataset to guard against duplicates...")
    known = existing_hashes(curated, BASE_DIR / "raw" / "ethnic_wear")
    print("  {} images already in the dataset".format(known.size))

    print("Validating {} images...".format(len(selected)))
    accepted, rejected = [], Counter()
    # Preallocated so the growing hash pool is a view, not a fresh concatenate
    # on every one of ~20k iterations.
    pool = np.zeros(known.size + len(selected), dtype=np.uint64)
    pool[:known.size] = known
    pool_size = known.size
    for index, entry in enumerate(selected, 1):
        if index % 2000 == 0:
            print("  {}/{}  ({} accepted)".format(index, len(selected), len(accepted)))
        try:
            with Image.open(entry["path"]) as img:
                img.verify()
            with Image.open(entry["path"]) as img:
                width, height = img.size
                fingerprint = phash(img)
        except Exception as exc:
            rejected["unreadable ({})".format(exc.__class__.__name__)] += 1
            continue
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            rejected["below {}x{}".format(MIN_WIDTH, MIN_HEIGHT)] += 1
            continue
        if pool_size and hamming_all(fingerprint, pool[:pool_size]).min() <= PHASH_MAX_DISTANCE:
            rejected["duplicate of an existing image"] += 1
            continue
        pool[pool_size] = np.uint64(fingerprint)
        pool_size += 1
        entry["width"], entry["height"] = width, height
        entry["phash"] = "{:016x}".format(fingerprint)
        accepted.append(entry)

    print()
    for reason, count in rejected.most_common():
        print("  SKIP  {:<34} {:>7}".format(reason, count))

    if stage:
        print("\nStaging {} images under {}...".format(len(accepted), staged))
        staged.mkdir(parents=True, exist_ok=True)
        for entry in accepted:
            target = staged / "myntra_{}.jpg".format(entry["id"])
            shutil.copy2(entry["path"], target)
            entry["staged_path"] = str(target)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fields = (["image_id", "source_path", "staged_path", "articleType", "width", "height", "phash"]
              + ["occasion_{}".format(n) for n in OCCASIONS]
              + ["season_{}".format(n) for n in SEASONS]
              + ["tradition_ethnic", "mask_occasion", "mask_season", "mask_tradition"])
    with open(MANIFEST, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for entry in accepted:
            writer.writerow(dict(entry,
                                 image_id="myntra_{}".format(entry["id"]),
                                 source_path=str(entry["path"]),
                                 staged_path=entry.get("staged_path", "")))

    report(accepted, staged, dry_run=False, staged_files=stage)
    return 0 if accepted else 1


def report(rows, staged, dry_run, staged_files):
    print("\n{:<12} {:<10} {:>9} {:>9}".format("Axis", "Label", "Positive", "Labelled"))
    labelled_occasion = sum(r["mask_occasion"] for r in rows)
    for name in OCCASIONS:
        positive = sum(r["occasion_{}".format(name)] for r in rows)
        print("{:<12} {:<10} {:>9} {:>9}".format("occasion", name, positive, labelled_occasion))
    labelled_season = sum(r["mask_season"] for r in rows)
    for name in SEASONS:
        positive = sum(r["season_{}".format(name)] for r in rows)
        print("{:<12} {:<10} {:>9} {:>9}".format("season", name, positive, labelled_season))
    labelled_tradition = sum(r["mask_tradition"] for r in rows)
    ethnic = sum(r["tradition_ethnic"] for r in rows)
    print("{:<12} {:<10} {:>9} {:>9}".format("tradition", "ethnic", ethnic, labelled_tradition))
    print("{:<12} {:<10} {:>9} {:>9}".format("tradition", "western", len(rows) - ethnic, labelled_tradition))
    print("\nTOTAL {} images".format(len(rows)))

    if dry_run:
        print("\nDry run: no images were read, staged or written to a manifest.")
        return
    print("\nManifest: {}".format(MANIFEST))
    if not staged_files:
        print("Images were left in place; the manifest holds absolute source paths.")
    else:
        print("Staged under {}".format(staged))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Unzipped Myntra download holding styles.csv and images/")
    parser.add_argument("--staged", type=Path, default=DEFAULT_STAGED,
                        help="Where images are copied when --stage is given")
    parser.add_argument("--curated", type=Path, default=BASE_DIR / "curated",
                        help="Existing curated tree, checked for duplicates")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report the label mapping without reading any image")
    parser.add_argument("--stage", action="store_true",
                        help="Also copy accepted images into --staged (23GB source; off by default)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after N catalogue rows, for a quick check")
    args = parser.parse_args()

    sys.exit(ingest(args.source, args.staged, args.curated, args.dry_run, args.stage, args.limit))
