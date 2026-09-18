import json
import os
from datetime import datetime, timezone

import torch
import torch.nn as nn
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from torchvision import datasets, models

from preprocess import get_transforms

ROOT = r"C:\Users\Lakshya\Desktop\StyleSync"
DATA_DIR = os.path.join(ROOT, "dataset", "curated")
CHECKPOINT_DIR = os.path.join(ROOT, "backend", "app", "modules", "ai", "checkpoints")
ARTIFACT_DIR = os.path.join(ROOT, "model", "artifacts")

ARCHITECTURE = "mobilenet_v2"
MODEL_VERSION = "mobilenetv2-1.0"


def evaluate_model():
    test_dir = os.path.join(DATA_DIR, "test")
    checkpoint_path = os.path.join(CHECKPOINT_DIR, "mobilenetv2_fashion.pth")

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(checkpoint_path):
        raise SystemExit(
            f"Checkpoint not found at {checkpoint_path}. Train the model before evaluating; "
            "evaluating random weights would produce meaningless metrics."
        )

    if not os.path.exists(test_dir) or sum(len(files) for _, _, files in os.walk(test_dir)) == 0:
        raise SystemExit(f"Test dataset not found or empty at {test_dir}.")

    test_dataset = datasets.ImageFolder(test_dir, get_transforms(is_training=False))
    test_loader = torch.utils.data.DataLoader(
        test_dataset, batch_size=16, shuffle=False, num_workers=0
    )
    class_names = test_dataset.classes

    try:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    except Exception:
        model = models.mobilenet_v2(pretrained=True)

    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, len(class_names))
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    print(f"Loaded checkpoint from {checkpoint_path}")

    model = model.to(device)
    model.eval()

    all_labels: list[int] = []
    all_preds: list[int] = []

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            all_labels.extend(labels.cpu().tolist())
            all_preds.extend(preds.cpu().tolist())

    total = len(all_labels)
    correct = sum(int(a == b) for a, b in zip(all_labels, all_preds))
    accuracy = correct / total if total else 0.0

    labels_idx = list(range(len(class_names)))
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, labels=labels_idx, average="macro", zero_division=0
    )
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, labels=labels_idx, average="weighted", zero_division=0
    )
    per_p, per_r, per_f1, per_support = precision_recall_fscore_support(
        all_labels, all_preds, labels=labels_idx, average=None, zero_division=0
    )
    cm = confusion_matrix(all_labels, all_preds, labels=labels_idx)

    print(f"\nTest samples: {total}")
    print(f"Test Accuracy: {accuracy:.4f}")
    print(f"Macro    P/R/F1: {macro_p:.4f} / {macro_r:.4f} / {macro_f1:.4f}")
    print(f"Weighted P/R/F1: {weighted_p:.4f} / {weighted_r:.4f} / {weighted_f1:.4f}")
    print("\n" + classification_report(
        all_labels, all_preds, labels=labels_idx, target_names=class_names, zero_division=0
    ))
    print("Confusion matrix (rows = true, cols = predicted):")
    print("            " + "".join(f"{name[:8]:>10}" for name in class_names))
    for name, row in zip(class_names, cm):
        print(f"{name[:10]:>12}" + "".join(f"{int(v):>10}" for v in row))

    per_class = {
        name: {
            "precision": round(float(per_p[i]), 4),
            "recall": round(float(per_r[i]), 4),
            "f1": round(float(per_f1[i]), 4),
            "support": int(per_support[i]),
        }
        for i, name in enumerate(class_names)
    }

    metrics = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "split": "test",
        "num_samples": total,
        "num_classes": len(class_names),
        "accuracy": round(accuracy, 4),
        "macro": {
            "precision": round(float(macro_p), 4),
            "recall": round(float(macro_r), 4),
            "f1": round(float(macro_f1), 4),
        },
        "weighted": {
            "precision": round(float(weighted_p), 4),
            "recall": round(float(weighted_r), 4),
            "f1": round(float(weighted_f1), 4),
        },
        "per_class": per_class,
        "confusion_matrix": {
            "labels": class_names,
            "matrix": cm.astype(int).tolist(),
        },
    }

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    metrics_path = os.path.join(ARTIFACT_DIR, "evaluation_metrics.json")
    with open(metrics_path, "w") as handle:
        json.dump(metrics, handle, indent=2)
    print(f"\nMetrics written to {metrics_path}")

    # Metadata consumed by backend ClassifierManager at startup.
    metadata = {
        "version": MODEL_VERSION,
        "architecture": ARCHITECTURE,
        "input_size": 224,
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        "class_mapping": {str(i): name for i, name in enumerate(class_names)},
        "metrics": {
            "split": "test",
            "num_samples": total,
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro"]["f1"],
            "weighted_f1": metrics["weighted"]["f1"],
        },
        "generated_at": metrics["evaluated_at"],
    }

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    metadata_path = os.path.join(CHECKPOINT_DIR, "metadata.json")
    with open(metadata_path, "w") as handle:
        json.dump(metadata, handle, indent=2)
    print(f"Model metadata written to {metadata_path}")

    return metrics


if __name__ == "__main__":
    evaluate_model()
