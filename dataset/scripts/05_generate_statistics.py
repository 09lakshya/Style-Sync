import os
import csv
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_TRAIN = BASE_DIR / "annotations" / "train.csv"
CSV_VAL = BASE_DIR / "annotations" / "validation.csv"
CSV_TEST = BASE_DIR / "annotations" / "test.csv"
REPORT_MD = BASE_DIR / "dataset_statistics.md"

def analyze_split(csv_path):
    if not csv_path.exists():
        return [], 0
    
    data = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data, len(data)

def main():
    print("Generating Dataset Statistics Report...")
    
    train_data, train_count = analyze_split(CSV_TRAIN)
    val_data, val_count = analyze_split(CSV_VAL)
    test_data, test_count = analyze_split(CSV_TEST)
    
    all_data = train_data + val_data + test_data
    total_count = len(all_data)
    
    if total_count == 0:
        print("No data found to generate statistics.")
        return
        
    categories = Counter(row["category"] for row in all_data)
    colors = Counter(row["primary_color"] for row in all_data)
    patterns = Counter(row["pattern"] for row in all_data)
    
    missing_pattern = sum(1 for row in all_data if row["pattern"] == "NOT_AVAILABLE")
    missing_season = sum(1 for row in all_data if row["season"] == "NOT_AVAILABLE")
    
    report = [
        "# StyleSync Final Dataset Report\n",
        "This dataset was algorithmically curated from the DeepFashion Benchmark.\n",
        "## Overall Statistics\n",
        f"- **Total Images:** {total_count}",
        f"- **Training:** {train_count}",
        f"- **Validation:** {val_count}",
        f"- **Testing:** {test_count}\n",
        "## Category Distribution\n"
    ]
    
    for cat, count in categories.most_common():
        report.append(f"- **{cat.capitalize()}**: {count}")
        
    report.append("\n## Color Distribution (Top 5)\n")
    for col, count in colors.most_common(5):
        report.append(f"- **{col.capitalize()}**: {count}")
        
    report.append("\n## Missing Attributes (Requires Manual Annotation)\n")
    report.append(f"- **Pattern**: {missing_pattern} ({(missing_pattern/total_count)*100:.1f}%)")
    report.append(f"- **Season**: {missing_season} ({(missing_season/total_count)*100:.1f}%)")
    
    report_content = "\n".join(report)
    
    with open(REPORT_MD, "w") as f:
        f.write(report_content)
        
    print(report_content)
    print(f"\nSaved full report to {REPORT_MD}")

if __name__ == "__main__":
    main()
