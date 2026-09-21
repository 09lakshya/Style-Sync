"""Validate and stage custom (self-labelled) images for the 7-class dataset.

DeepFashion supplies the public half of the dataset; this script handles the
half you photograph or collect yourself. Drop images into per-class folders:

    dataset/raw/custom/Casual/...
    dataset/raw/custom/Ethnic/...
    ...one folder per category, the folder name IS the label.

Then run:

    python dataset/scripts/00_ingest_custom.py

Accepted images are copied to dataset/custom/<Category>/ and recorded in
dataset/processed/00_custom_manifest.csv. The staged folder is what
01_curate_dataset.py consumes via --extra-source (the command is printed at
the end).

Nothing here invents data. An image is rejected -- never repaired, resized up
or relabelled -- when it cannot be decoded, is below the 224x224 floor the
pipeline requires, or duplicates an image already in the dataset. Rejections
are listed with a reason so the shortfall is visible rather than papered over.
"""

import argparse
import csv
import hashlib
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = BASE_DIR / "raw" / "custom"
DEFAULT_STAGED = BASE_DIR / "custom"
PROCESSED_DIR = BASE_DIR / "processed"
MANIFEST = PROCESSED_DIR / "00_custom_manifest.csv"

# Kept in step with 01_curate_dataset.py and the trained class map.
CATEGORIES = ["Casual", "Party", "Formal", "Ethnic", "Western", "Summer", "Winter"]
MIN_WIDTH = 224
MIN_HEIGHT = 224
EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# The project target for self-labelled images, spread across the seven classes.
TARGET_TOTAL_MIN = 500
TARGET_TOTAL_MAX = 1000

# Distance at which two perceptual hashes count as the same picture. 0 is an
# exact visual match; a small allowance catches re-compressed and lightly
# cropped copies, which are the usual way a duplicate sneaks in.
PHASH_MAX_DISTANCE = 4


def phash(image: Image.Image) -> int:
    """64-bit DCT perceptual hash, as an int whose XOR popcount is the distance.

    Equivalent to imagehash.phash, computed here with numpy so the pipeline needs
    no dependency beyond what the project already installs.
    """
    pixels = np.asarray(image.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    # DCT-II along both axes via the orthonormal basis matrix.
    k = np.arange(32)
    basis = np.cos(np.pi * (2 * k[:, None] + 1) * k[None, :] / 64)
    basis[:, 0] *= 1 / np.sqrt(2)
    coefficients = basis.T @ pixels @ basis
    low = coefficients[:8, :8]
    # The DC term encodes overall brightness, not structure, so the median that
    # sets the threshold is taken over the remaining coefficients.
    bits = low > np.median(low.flatten()[1:])
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


def hamming(left: int, right: int) -> int:
    return bin(left ^ right).count("1")


def iter_images(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            yield path


def existing_hashes(*folders: Path) -> dict:
    """Perceptual hashes of images already in the dataset, keyed by hash."""
    seen = {}
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in iter_images(folder):
            try:
                with Image.open(path) as img:
                    seen[phash(img)] = path
            except Exception:
                # An unreadable file already in the tree is not this script's
                # problem; it simply cannot serve as a duplicate reference.
                continue
    return seen


def is_duplicate(candidate: int, known: dict):
    """Return the matching path when candidate is within PHASH_MAX_DISTANCE."""
    for known_hash, path in known.items():
        if hamming(candidate, known_hash) <= PHASH_MAX_DISTANCE:
            return path
    return None


def ingest(source: Path, staged: Path, curated: Path, dry_run: bool) -> int:
    if not source.is_dir():
        sys.exit(
            f"ERROR: source directory not found:\n  {source}\n\n"
            "Create it and add one folder per category, e.g.\n"
            f"  {source / 'Casual'}\n"
            f"  {source / 'Ethnic'}"
        )

    class_folders = [source / category for category in CATEGORIES if (source / category).is_dir()]
    if not class_folders:
        sys.exit(
            f"ERROR: no category folders inside:\n  {source}\n\n"
            f"Expected one or more of: {', '.join(CATEGORIES)}"
        )

    unexpected = [p.name for p in source.iterdir() if p.is_dir() and p.name not in CATEGORIES]
    if unexpected:
        sys.exit(
            f"ERROR: unknown category folder(s): {', '.join(sorted(unexpected))}\n"
            f"Folder names are the labels and must be one of: {', '.join(CATEGORIES)}"
        )

    print(f"Reading existing images to guard against duplicates...")
    known = existing_hashes(curated, staged, BASE_DIR / "raw" / "ethnic_wear")
    print(f"  {len(known)} images already in the dataset\n")

    accepted, rejected = [], []
    counts = {category: 0 for category in CATEGORIES}

    for folder in class_folders:
        category = folder.name
        for path in iter_images(folder):
            try:
                with Image.open(path) as img:
                    img.verify()
                with Image.open(path) as img:
                    width, height = img.size
                    fingerprint = phash(img)
            except Exception as exc:
                rejected.append((path, category, f"unreadable ({exc.__class__.__name__})"))
                continue

            if width < MIN_WIDTH or height < MIN_HEIGHT:
                rejected.append((path, category, f"too small ({width}x{height}, need {MIN_WIDTH}x{MIN_HEIGHT})"))
                continue

            match = is_duplicate(fingerprint, known)
            if match is not None:
                rejected.append((path, category, f"duplicate of {match.name}"))
                continue

            known[fingerprint] = path
            digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
            accepted.append(
                {
                    "image_id": f"custom_{category.lower()}_{digest}",
                    "category": category,
                    "source_path": str(path),
                    "width": width,
                    "height": height,
                    "phash": f"{fingerprint:016x}",
                }
            )
            counts[category] += 1

    for row in rejected:
        print(f"  SKIP  {row[1]:<8} {row[0].name}: {row[2]}")
    if rejected:
        print()

    if not dry_run:
        for row in accepted:
            destination = staged / row["category"]
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / f"{row['image_id']}{Path(row['source_path']).suffix.lower()}"
            shutil.copy2(row["source_path"], target)
            row["staged_path"] = str(target)

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["image_id", "category", "source_path", "staged_path", "width", "height", "phash"],
            )
            writer.writeheader()
            for row in accepted:
                writer.writerow(row)

    report(counts, len(accepted), len(rejected), staged, dry_run)
    return 0 if accepted or dry_run else 1


def report(counts: dict, accepted: int, rejected: int, staged: Path, dry_run: bool) -> None:
    print(f"{'Category':<10} {'Accepted':>9}")
    for category in CATEGORIES:
        print(f"{category:<10} {counts[category]:>9}")
    print(f"{'TOTAL':<10} {accepted:>9}   ({rejected} rejected)")

    print()
    if accepted < TARGET_TOTAL_MIN:
        short = TARGET_TOTAL_MIN - accepted
        print(f"{short} short of the {TARGET_TOTAL_MIN}-image target.")
        thin = [c for c in CATEGORIES if counts[c] < TARGET_TOTAL_MIN // len(CATEGORIES)]
        if thin:
            print(f"Thinnest classes: {', '.join(thin)}")
    else:
        print(f"Target met: {accepted} images (target {TARGET_TOTAL_MIN}-{TARGET_TOTAL_MAX}).")

    if dry_run:
        print("\nDry run: nothing was copied and no manifest was written.")
        return

    print(f"\nStaged under {staged}")
    print(f"Manifest: {MANIFEST}")
    print("\nFeed them into curation with:\n")
    sources = " ".join(
        f'--extra-source {category}="{staged / category}"' for category in CATEGORIES if counts[category]
    )
    print(f"  python dataset/scripts/01_curate_dataset.py {sources}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Drop folder holding one subfolder per category")
    parser.add_argument("--staged", type=Path, default=DEFAULT_STAGED,
                        help="Where validated images are copied")
    parser.add_argument("--curated", type=Path, default=BASE_DIR / "curated",
                        help="Existing curated tree, checked for duplicates")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be accepted without copying anything")
    args = parser.parse_args()

    sys.exit(ingest(args.source, args.staged, args.curated, args.dry_run))
