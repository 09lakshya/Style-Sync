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
