# StyleSync Dataset Curation Pipeline

This directory contains the data curation pipeline for extracting a high-quality 800-image subset from the DeepFashion dataset for StyleSync's academic ML requirements.

## Licensing & Usage

The images processed by this pipeline originate from the **DeepFashion (Category and Attribute Prediction Benchmark)** (Ziwei Liu, Ping Luo, Shi Qiu, Xiaogang Wang, and Xiaoou Tang, "DeepFashion: Powering Robust Clothes Recognition and Retrieval", in Proceedings of IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2016).

**IMPORTANT:** The DeepFashion dataset is strictly available for **non-commercial research purposes only**. Do not redistribute the source images. This pipeline is designed to be reproducible locally so that the GitHub repository does not need to host the raw image files.

## Prerequisites

1. Install pipeline requirements:
   ```bash
   pip install opencv-python-headless pyyaml imagehash Pillow
   ```
2. Download the DeepFashion Category and Attribute Prediction Benchmark.
3. Extract the contents so that the `img/` folder and `Anno/` folder are located in `dataset/raw/deepfashion/`.

## Custom (self-labelled) images

The public half of the dataset comes from DeepFashion. The custom half is
images you collect and label yourself, and it is the only source for `Ethnic`,
which a Western catalogue does not cover.

Drop images into one folder per category — **the folder name is the label**:

```
dataset/raw/custom/Casual/...
dataset/raw/custom/Ethnic/...
dataset/raw/custom/Formal/...        (Party, Western, Summer, Winter likewise)
```

Then validate and stage them:

```bash
# 0. Validate, de-duplicate and stage custom images (add --dry-run to preview)
python scripts/00_ingest_custom.py
```

The script rejects, rather than repairs, anything unusable: images it cannot
decode, images below 224x224, and near-duplicates of images already in
`dataset/curated/`, `dataset/custom/` or `dataset/raw/ethnic_wear/` (64-bit DCT
perceptual hash, Hamming distance <= 4). Every rejection is printed with its
reason, and a per-class count shows progress toward the 500-1000 target. It is
safe to re-run: images already staged are recognised and skipped.

Accepted images land in `dataset/custom/<Category>/`, are recorded in
`dataset/processed/00_custom_manifest.csv`, and the script prints the exact
`01_curate_dataset.py --extra-source` command to fold them into curation.

**Current custom count: 400** (all `Ethnic`, in `dataset/raw/ethnic_wear/`),
plus 80 colour-labelled evaluation images in `dataset/raw/colour_eval/`. Around
100 more, spread across the other six classes, reaches the 500 minimum.

## Pipeline Execution

Run the scripts in sequential order to generate the curated dataset:

```bash
# 1. Filter raw annotations by category and minimum resolution (224x224)
python scripts/01_parse_and_filter.py

# 2. Remove near-identical images via perceptual hashing to prevent data leakage
python scripts/02_deduplicate.py

# 3. Extract and normalize dominant colors using OpenCV K-Means clustering
python scripts/03_extract_colors.py

# 4. Cap categories, balance the dataset, and perform a stratified 70/15/15 split
python scripts/04_balance_and_split.py

# 5. Generate the final academic dataset statistics report
python scripts/05_generate_statistics.py
```

## Manual Annotation Phase

Because datasets like DeepFashion do not explicitly contain subjective labels like `season` or `occasion`, the pipeline generates an `annotations/annotation_template.csv`.

Students should open this template, review the generated labels, and manually fill in the missing `NOT_AVAILABLE` fields for the final 800 images to complete the academic manual annotation requirement.
