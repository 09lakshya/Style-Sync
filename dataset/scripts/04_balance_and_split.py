import os
import csv
import yaml
import shutil
import random
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "dataset_config.yaml"
IN_CSV = BASE_DIR / "processed" / "03_colors_extracted.csv"

OUT_DIR_TRAIN = BASE_DIR / "images" / "train"
OUT_DIR_VAL = BASE_DIR / "images" / "validation"
OUT_DIR_TEST = BASE_DIR / "images" / "test"

CSV_TRAIN = BASE_DIR / "annotations" / "train.csv"
CSV_VAL = BASE_DIR / "annotations" / "validation.csv"
CSV_TEST = BASE_DIR / "annotations" / "test.csv"
TEMPLATE_CSV = BASE_DIR / "annotations" / "annotation_template.csv"

# Load config
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

MAX_PER_CLASS = config["filtering_rules"].get("max_images_per_class", 100)
SPLIT_RATIOS = config["split_ratios"]
SEED = config.get("random_seed", 42)

def main():
    random.seed(SEED)
    
    if not IN_CSV.exists():
        print(f"Input {IN_CSV} not found.")
        return

    # Read data
    data_by_category = defaultdict(list)
    with open(IN_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data_by_category[row["category"]].append(row)

    train_data = []
    val_data = []
    test_data = []

    print("Balancing and Splitting Data...")
    
    for category, items in data_by_category.items():
        # Shuffle explicitly to ensure randomness but reproduceable via SEED
        random.shuffle(items)
        
        # Cap per category
        if len(items) > MAX_PER_CLASS:
            items = items[:MAX_PER_CLASS]
            
        n_total = len(items)
        n_train = int(n_total * SPLIT_RATIOS["train"])
        n_val = int(n_total * SPLIT_RATIOS["validation"])
        
        train_items = items[:n_train]
        val_items = items[n_train:n_train+n_val]
        test_items = items[n_train+n_val:]
        
        train_data.extend(train_items)
        val_data.extend(val_items)
        test_data.extend(test_items)
        
    print(f"Total balanced dataset size: {len(train_data) + len(val_data) + len(test_data)}")
    print(f"Train: {len(train_data)}, Validation: {len(val_data)}, Test: {len(test_data)}")
    
    # Save CSVs
    def save_split(data, csv_path, img_dir):
        img_dir.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not data:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["image_id", "source_image_path", "category", "primary_color", "pattern", "sleeve_type", "season", "occasion", "verified"])
            return
            
        fieldnames = ["image_id", "source_image_path", "category", "primary_color", "pattern", "sleeve_type", "season", "occasion", "verified"]
        
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in data:
                # Add default template fields
                row["pattern"] = row.get("pattern", "NOT_AVAILABLE")
                row["sleeve_type"] = row.get("sleeve_type", "NOT_AVAILABLE")
                row["season"] = "NOT_AVAILABLE"
                row["occasion"] = "NOT_AVAILABLE"
                row["verified"] = "False"
                writer.writerow(row)
                
                # Copy image if it exists
                src = row["source_image_path"]
                if os.path.exists(src):
                    filename = f"{row['image_id']}.jpg"
                    dst = img_dir / filename
                    shutil.copy2(src, dst)

    save_split(train_data, CSV_TRAIN, OUT_DIR_TRAIN)
    save_split(val_data, CSV_VAL, OUT_DIR_VAL)
    save_split(test_data, CSV_TEST, OUT_DIR_TEST)
    
    # Generate unified annotation template for students
    all_data = train_data + val_data + test_data
    save_split(all_data, TEMPLATE_CSV, BASE_DIR / "images" / "tmp") # Images already copied, just reuse logic for CSV
    
    # Clean up tmp (dirty hack above just to write the unified CSV)
    if (BASE_DIR / "images" / "tmp").exists():
        shutil.rmtree(BASE_DIR / "images" / "tmp")
        
    print(f"Saved splits to {BASE_DIR}/annotations/")
    print(f"Created manual annotation template: {TEMPLATE_CSV}")

if __name__ == "__main__":
    main()
