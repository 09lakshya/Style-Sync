import os
import csv
from pathlib import Path
from PIL import Image

try:
    import imagehash
except ImportError:
    print("Please install imagehash: pip install imagehash")
    exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "processed"
IN_CSV = PROCESSED_DIR / "01_candidates.csv"
OUT_CSV = PROCESSED_DIR / "02_deduplicated.csv"

def compute_phash(image_path: str) -> str:
    try:
        img = Image.open(image_path)
        return str(imagehash.phash(img))
    except Exception as e:
        print(f"Error hashing {image_path}: {e}")
        return None

def main():
    if not IN_CSV.exists():
        print(f"Input {IN_CSV} not found. Run 01_parse_and_filter.py first.")
        return

    print("Starting deduplication via Perceptual Hashing...")
    unique_hashes = set()
    deduplicated_candidates = []
    duplicates_removed = 0

    with open(IN_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # If the file doesn't actually exist (e.g. running empty pipeline), we skip hash and just pass it through
            # to allow the pipeline to complete without crashing.
            if not os.path.exists(row["source_image_path"]):
                # Mock hash for empty pipeline testing
                phash = row["image_id"][:16] 
            else:
                phash = compute_phash(row["source_image_path"])
                
            if phash is None:
                continue
                
            if phash in unique_hashes:
                duplicates_removed += 1
            else:
                unique_hashes.add(phash)
                deduplicated_candidates.append(row)

    with open(OUT_CSV, "w", newline="") as f:
        if not deduplicated_candidates:
            # write header only if empty
            writer = csv.writer(f)
            writer.writerow(["image_id", "source_image_path", "category", "width", "height"])
        else:
            writer = csv.DictWriter(f, fieldnames=deduplicated_candidates[0].keys())
            writer.writeheader()
            writer.writerows(deduplicated_candidates)

    print(f"Deduplication complete.")
    print(f"Removed {duplicates_removed} near-duplicate images.")
    print(f"Kept {len(deduplicated_candidates)} unique images.")
    print(f"Saved to {OUT_CSV}")

if __name__ == "__main__":
    main()
