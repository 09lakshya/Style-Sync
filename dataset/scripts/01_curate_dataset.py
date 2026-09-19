"""Curate a 7-class clothing dataset from DeepFashion raw images.

By default this script REFUSES to invent data: if the raw image directory is
missing, or a category cannot be filled from real images, it stops with a clear
error instead of silently generating placeholder images. Pass --allow-synthetic
to opt into placeholder generation, which is only ever appropriate for smoke
testing the pipeline -- never for training a model you intend to report on.

Set the raw image location with --raw-dir or the STYLESYNC_RAW_DIR environment
variable.
"""

import argparse
import os
import shutil
import random
import glob
import sys

# Paths
DEFAULT_RAW_DIR = r"C:\Users\Lakshya\OneDrive\Desktop\StyleSync\dataset\raw\deepfashion\datasets"
RAW_DIR = os.environ.get("STYLESYNC_RAW_DIR", DEFAULT_RAW_DIR)
OUT_DIR = r"C:\Users\Lakshya\Desktop\StyleSync\dataset\curated"

# Ensure output directories exist
splits = ['train', 'val', 'test']
categories = ['Casual', 'Party', 'Formal', 'Ethnic', 'Western', 'Summer', 'Winter']

IMAGES_PER_CATEGORY = 100


def map_filename_to_category(filename):
    """Map a DeepFashion filename to one of the seven categories, or None.

    Returning None is correct and expected for filenames the heuristic cannot
    classify -- they are skipped rather than assigned a guessed label.
    """
    name = filename.lower()
    # Party
    if 'dresses' in name and 'additional' not in name:
        return 'Party'
    if 'rompers_jumpsuits' in name or 'skirts' in name:
        return 'Party'
    
    # Formal
    if 'suiting' in name or 'shirts_polos' in name or 'blouses_shirts' in name:
        return 'Formal'
        
    # Western
    if 'jackets_vests' in name or 'jackets_coats' in name:
        return 'Western'
        
    # Summer
    if 'shorts' in name or 'leggings' in name:
        return 'Summer'
        
    # Winter
    if 'sweaters' in name or 'cardigans' in name:
        return 'Winter'
        
    # Casual
    if 'tees_tanks' in name or 'graphic_tees' in name or 'sweatshirts_hoodies' in name or 'denim' in name:
        return 'Casual'
        
    return None

def generate_synthetic_image(cat, dest_path):
    from PIL import Image, ImageDraw
    import random
    
    # Generate some random colored background based on category
    color_map = {
        'Casual': (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)),
        'Party': (random.randint(200, 255), 0, random.randint(100, 255)),
        'Formal': (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)),
        'Ethnic': (random.randint(200, 255), random.randint(150, 200), 0),
        'Western': (0, random.randint(100, 200), random.randint(150, 255)),
        'Summer': (random.randint(200, 255), random.randint(200, 255), 0),
        'Winter': (random.randint(0, 100), random.randint(0, 100), random.randint(150, 255)),
    }
    
    img = Image.new('RGB', (224, 224), color=color_map.get(cat, (255, 255, 255)))
    d = ImageDraw.Draw(img)
    # add some noise/shapes to make it learnable
    for _ in range(5):
        shape_type = random.choice(['rect', 'ellipse'])
        x0 = random.randint(0, 100)
        y0 = random.randint(0, 100)
        x1 = random.randint(124, 224)
        y1 = random.randint(124, 224)
        col = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        if shape_type == 'rect':
            d.rectangle([x0, y0, x1, y1], fill=col)
        else:
            d.ellipse([x0, y0, x1, y1], fill=col)
            
    img.save(dest_path)

def collect_extra_sources(extra_sources):
    """Load categories supplied from directories outside the DeepFashion tree.

    DeepFashion is a Western fashion catalogue and contains no ethnic wear, so
    'Ethnic' has to come from a separately labelled source. Each entry is
    CATEGORY=PATH; every image in PATH is taken as labelled with CATEGORY.
    """
    collected = {}
    for entry in extra_sources:
        if "=" not in entry:
            sys.exit(f"ERROR: --extra-source expects CATEGORY=PATH, got: {entry}")
        cat, path = entry.split("=", 1)
        if cat not in categories:
            sys.exit(f"ERROR: unknown category '{cat}'. Expected one of: {', '.join(categories)}")
        if not os.path.isdir(path):
            sys.exit(f"ERROR: --extra-source directory not found for {cat}:\n  {path}")

        found = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            found.extend(glob.glob(os.path.join(path, ext)))
        if not found:
            sys.exit(f"ERROR: no images found for {cat} in:\n  {path}")

        print(f"Extra source: {cat} <- {len(found)} images from {path}")
        collected.setdefault(cat, []).extend(found)
    return collected


def curate(raw_dir, allow_synthetic=False, extra_sources=()):
    TRAIN_IMAGES_DIR = os.path.join(raw_dir, "train_images")
    TEST_IMAGES_DIR = os.path.join(raw_dir, "test_images")

    if not os.path.isdir(raw_dir) and not allow_synthetic:
        sys.exit(
            f"ERROR: raw image directory not found:\n  {raw_dir}\n\n"
            "Point at the DeepFashion images with --raw-dir or STYLESYNC_RAW_DIR.\n"
            "Refusing to generate placeholder images. Re-run with --allow-synthetic\n"
            "only if you explicitly want a throwaway dataset for smoke testing."
        )

    for split in splits:
        for cat in categories:
            os.makedirs(os.path.join(OUT_DIR, split, cat), exist_ok=True)

    images = []
    if os.path.exists(TRAIN_IMAGES_DIR):
        images.extend(glob.glob(os.path.join(TRAIN_IMAGES_DIR, "*.png")))
        images.extend(glob.glob(os.path.join(TRAIN_IMAGES_DIR, "*.jpg")))
    if os.path.exists(TEST_IMAGES_DIR):
        images.extend(glob.glob(os.path.join(TEST_IMAGES_DIR, "*.png")))
        images.extend(glob.glob(os.path.join(TEST_IMAGES_DIR, "*.jpg")))
        
    print(f"Found {len(images)} images in raw directories.")
    
    # Group by mapped category
    categorized = {cat: [] for cat in categories}
    
    for img_path in images:
        filename = os.path.basename(img_path)
        cat = map_filename_to_category(filename)
        if cat and cat in categorized:
            categorized[cat].append(img_path)

    # Categories supplied from outside DeepFashion (notably Ethnic).
    for cat, paths in collect_extra_sources(extra_sources).items():
        categorized[cat].extend(paths)

    # Fail before writing anything if the real data cannot fill every category.
    shortfalls = {
        cat: IMAGES_PER_CATEGORY - len(categorized[cat])
        for cat in categories
        if len(categorized[cat]) < IMAGES_PER_CATEGORY
    }
    if shortfalls and not allow_synthetic:
        lines = "\n".join(
            f"  {cat}: {len(categorized[cat])} of {IMAGES_PER_CATEGORY} "
            f"(short by {missing})"
            for cat, missing in shortfalls.items()
        )
        sys.exit(
            "ERROR: the raw data cannot fill every category:\n"
            f"{lines}\n\n"
            "Categories with no filename heuristic (notably Ethnic) need real labelled\n"
            "images or an explicit mapping -- they will not be invented.\n"
            "Refusing to pad with placeholder images. Re-run with --allow-synthetic\n"
            "only if you explicitly want a throwaway dataset for smoke testing."
        )

    # Sample and split
    # Target: IMAGES_PER_CATEGORY per class (70 train, 15 val, 15 test)
    for cat in categories:
        available = categorized[cat]
        print(f"Category {cat}: {len(available)} available")

        random.shuffle(available)
        selected = available[:IMAGES_PER_CATEGORY]

        if len(selected) < IMAGES_PER_CATEGORY:
            # Only reachable with --allow-synthetic; loudly marked as not real data.
            missing = IMAGES_PER_CATEGORY - len(selected)
            print(f"  !! PLACEHOLDER: padding {cat} with {missing} generated images "
                  f"-- this dataset is NOT suitable for reported results")
            selected.extend([f"synthetic_{cat}_{i}.png" for i in range(missing)])

        n_total = len(selected)
        n_train = int(n_total * 0.7)
        n_val = int(n_total * 0.15)
        
        train_imgs = selected[:n_train]
        val_imgs = selected[n_train:n_train+n_val]
        test_imgs = selected[n_train+n_val:]
        
        splits_dict = {'train': train_imgs, 'val': val_imgs, 'test': test_imgs}
        
        for split_name, img_list in splits_dict.items():
            for i, img_p in enumerate(img_list):
                dest = os.path.join(OUT_DIR, split_name, cat, os.path.basename(img_p))
                if img_p.startswith("synthetic_"):
                    generate_synthetic_image(cat, dest)
                else:
                    try:
                        shutil.copy2(img_p, dest)
                    except Exception as e:
                        print(f"Failed to copy {img_p}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", default=RAW_DIR,
                        help="Directory holding DeepFashion train_images/ and test_images/")
    parser.add_argument("--allow-synthetic", action="store_true",
                        help="Permit generated placeholder images when real data is missing "
                             "(smoke testing only -- never for reported results)")
    parser.add_argument("--extra-source", action="append", default=[], metavar="CATEGORY=PATH",
                        help="Supply a category from a directory outside DeepFashion, e.g. "
                             "--extra-source Ethnic=C:\\data\\ethnic_wear. Repeatable.")
    args = parser.parse_args()

    if args.allow_synthetic:
        print("!! --allow-synthetic is set: output may contain generated placeholder "
              "images and must not be used for reported results.\n")

    curate(args.raw_dir, allow_synthetic=args.allow_synthetic, extra_sources=args.extra_source)
    print("Curation complete.")
