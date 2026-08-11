import os
import yaml
import csv
import cv2
import uuid
import shutil
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "dataset_config.yaml"
RAW_DIR = BASE_DIR / "raw" / "deepfashion"
PROCESSED_DIR = BASE_DIR / "processed"

# Load Config
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

TARGET_CATEGORIES = set(config["categories"])
MIN_WIDTH = config["filtering_rules"]["min_resolution_width"]
MIN_HEIGHT = config["filtering_rules"]["min_resolution_height"]

def load_deepfashion_categories():
    """Simulates or reads DeepFashion's list_category_cloth.txt"""
    # Mapping DeepFashion categories to StyleSync target categories
    return {
        "Dress": "dress",
        "Tee": "t-shirt",
        "Blouse": "top",
        "Tank": "top",
        "Skirt": "skirt",
        "Jeans": "jeans",
        "Sweater": "top",
        "Jacket": "jacket",
        "Coat": "coat",
        "Shorts": "shorts"
    }

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = PROCESSED_DIR / "01_candidates.csv"
    
    print(f"Loading configuration from {CONFIG_PATH}")
    print(f"Target categories: {TARGET_CATEGORIES}")
    
    if not RAW_DIR.exists():
        print(f"WARNING: Raw dataset directory not found at {RAW_DIR}.")
        print("Please download and extract DeepFashion Category and Attribute Prediction Benchmark.")
        print("Creating an empty candidates CSV for pipeline continuation.")
        
        with open(out_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["image_id", "source_image_path", "category", "width", "height"])
        return

    category_mapping = load_deepfashion_categories()
    candidates = []
    
    # 1. Read list_category_img.txt
    anno_file = RAW_DIR / "Anno" / "list_category_img.txt"
    if anno_file.exists():
        with open(anno_file, "r") as f:
            lines = f.readlines()[2:] # Skip header
            for line in lines:
                parts = line.strip().split()
                img_path = parts[0]
                cat_idx = int(parts[1])
                
                # In full implementation, map cat_idx to string via list_category_cloth.txt
                # Then map to StyleSync category
                # For this pipeline skeleton, we assume we got a mapped_category
                mapped_category = "dress" # Placeholder for parsed mapping
                
                if mapped_category in TARGET_CATEGORIES:
                    full_path = RAW_DIR / img_path
                    if full_path.exists():
                        # 2. Check Resolution
                        img = cv2.imread(str(full_path))
                        if img is not None:
                            h, w, _ = img.shape
                            if w >= MIN_WIDTH and h >= MIN_HEIGHT:
                                candidates.append({
                                    "image_id": str(uuid.uuid4()),
                                    "source_image_path": str(full_path),
                                    "category": mapped_category,
                                    "width": w,
                                    "height": h
                                })
    
    # Write output
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image_id", "source_image_path", "category", "width", "height"])
        writer.writeheader()
        writer.writerows(candidates)
        
    print(f"Filtered {len(candidates)} valid candidate images.")
    print(f"Saved to {out_csv}")

if __name__ == "__main__":
    main()
