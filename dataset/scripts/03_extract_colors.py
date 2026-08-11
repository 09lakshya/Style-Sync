import os
import csv
import cv2
import numpy as np
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "dataset_config.yaml"
IN_CSV = BASE_DIR / "processed" / "02_deduplicated.csv"
OUT_CSV = BASE_DIR / "processed" / "03_colors_extracted.csv"

# Load Config for Color Families
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

COLOR_FAMILIES = config["color_families"]

# A simplistic hardcoded mapping for demonstration
# In a real scenario, we'd use Lab color space distance to true centroids
COLOR_CENTROIDS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "grey": (128, 128, 128),
    "red": (0, 0, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0),
    "yellow": (0, 255, 255),
    "pink": (203, 192, 255),
    "brown": (42, 42, 165),
    "navy": (128, 0, 0),
    "beige": (220, 245, 245),
    "purple": (128, 0, 128),
    "orange": (0, 165, 255)
}

def extract_dominant_color(img_path: str) -> str:
    """Uses K-Means clustering to find the dominant color and maps it to a standard family."""
    if not os.path.exists(img_path):
        return "NOT_AVAILABLE"
        
    img = cv2.imread(img_path)
    if img is None:
        return "NOT_AVAILABLE"
        
    # Crop central region assuming clothing is centered
    h, w, _ = img.shape
    crop = img[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
    
    # Reshape
    pixels = np.float32(crop.reshape(-1, 3))
    
    # K-Means
    n_colors = 3
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Find most common cluster
    _, counts = np.unique(labels, return_counts=True)
    dominant = palette[np.argmax(counts)]
    
    # Map to closest color family using Euclidean distance
    min_dist = float("inf")
    closest_color = "NOT_AVAILABLE"
    
    for color_name, bgr in COLOR_CENTROIDS.items():
        dist = np.linalg.norm(dominant - np.array(bgr))
        if dist < min_dist:
            min_dist = dist
            closest_color = color_name
            
    return closest_color

def main():
    if not IN_CSV.exists():
        print(f"Input {IN_CSV} not found.")
        return

    print("Extracting dominant colors via OpenCV K-Means...")
    
    rows = []
    with open(IN_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            color = extract_dominant_color(row["source_image_path"])
            row["primary_color"] = color
            rows.append(row)
            
    if not rows:
        print("No rows to process.")
    
    with open(OUT_CSV, "w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerow(["image_id", "source_image_path", "category", "width", "height", "primary_color"])
            
    print(f"Color extraction complete. Saved to {OUT_CSV}")

if __name__ == "__main__":
    main()
