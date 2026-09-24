r"""Pick a decision threshold per label instead of assuming 0.5 for all six.

Training scored the multi-head checkpoint at macro F1 0.7809, and every weak
label failed the same way: formal 0.94 recall against 0.53 precision, party
0.94/0.43, winter 0.79/0.48. That shape is not an undertrained backbone. It is
`pos_weight` doing exactly what it was capped to do -- buying recall on the rare
labels by pushing their logits up -- and then a 0.5 cut reading those inflated
scores as positives. The model ranks these garments fine; only the cut is wrong.

So: one forward pass over val, cache the probabilities, and sweep the cut per
label offline. Each label's F1 depends only on its own threshold, so six
independent 1-D sweeps are exact here, not a greedy approximation of a joint
search.

Thresholds are chosen on val and then applied unchanged to test, which is the
only way the test number means anything. Choosing and reporting on the same
split would just measure how well 99 candidates can fit 2,780 images.

    python model/calibrate_thresholds.py
"""

import json
import os
from datetime import datetime, timezone

import torch
import torch.nn as nn
from torchvision import models

from multilabel_dataset import AXES, AXIS_ORDER, LABELS, build_dataset
from preprocess import get_transforms

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(BASE_DIR, "dataset", "processed", "00_myntra_manifest.csv")
CURATED = os.path.join(BASE_DIR, "dataset", "curated")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "backend", "app", "modules", "ai", "checkpoints")
ARTIFACT_DIR = os.path.join(BASE_DIR, "model", "artifacts")
# Set STYLESYNC_CHECKPOINT_IN to calibrate a candidate produced by a training
# run before deciding whether it is worth promoting over the served weights.
CHECKPOINT_NAME = os.environ.get("STYLESYNC_CHECKPOINT_IN", "mobilenetv2_multihead.pth")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, CHECKPOINT_NAME)
THRESHOLD_SUFFIX = "" if CHECKPOINT_NAME == "mobilenetv2_multihead.pth" else ".candidate"
THRESHOLD_PATH = os.path.join(
    ARTIFACT_DIR, "multihead_thresholds{}.json".format(THRESHOLD_SUFFIX))

# 0.01 steps. Finer buys nothing: with 66 party positives in val, one image
# moving across the cut shifts F1 far more than a 0.005 change in threshold.
CANDIDATES = [index / 100.0 for index in range(1, 100)]

# Which axis mask governs each label, so a sample that never answered an axis is
# excluded from that label's counts rather than scored as a negative.
LABEL_AXIS = [AXIS_ORDER[0 if index < 3 else (1 if index < 5 else 2)]
              for index in range(len(LABELS))]


def axis_position(label_index):
    return AXIS_ORDER.index(LABEL_AXIS[label_index])


def load_model(device):
    if not os.path.isfile(CHECKPOINT_PATH):
        raise SystemExit(
            "ERROR: no checkpoint at\n  {}\nTrain the model before calibrating; "
            "thresholds over random weights mean nothing.".format(CHECKPOINT_PATH))
    saved = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    if saved.get("labels") != LABELS:
        raise SystemExit(
            "ERROR: that checkpoint was trained on {}\nbut this run expects {}.".format(
                saved.get("labels"), LABELS))

    try:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    except Exception:
        model = models.mobilenet_v2(pretrained=True)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(LABELS))
    model.load_state_dict(saved["state_dict"])
    return model.to(device).eval(), saved


@torch.no_grad()
def collect(model, split, device, workers):
    """One forward pass over a split, keeping probabilities rather than verdicts.

    The whole point is to try many cuts, so the pass has to hand back scores. At
    ~2,800 images by six floats this is a few hundred kilobytes -- the expensive
    thing is decoding the catalogue JPEGs, and that is paid once here instead of
    once per candidate threshold.
    """
    dataset = build_dataset(split, get_transforms(is_training=False),
                            manifest_path=MANIFEST, curated_dir=CURATED)
    loader_kwargs = {"batch_size": 32, "num_workers": workers}
    if workers:
        loader_kwargs["prefetch_factor"] = 4
    loader = torch.utils.data.DataLoader(dataset, shuffle=False, **loader_kwargs)

    probabilities, targets, masks = [], [], []
    for inputs, batch_targets, batch_masks in loader:
        scores = torch.sigmoid(model(inputs.to(device))).cpu()
        probabilities.append(scores)
        targets.append(batch_targets)
        masks.append(batch_masks)
    print("{:<5} {:>6} images".format(split, len(dataset)))
    return torch.cat(probabilities), torch.cat(targets), torch.cat(masks)


def score_label(probabilities, targets, masks, label_index, threshold):
    """Precision, recall and F1 for one label at one cut."""
    active = masks[:, axis_position(label_index)] > 0
    if active.sum() == 0:
        return 0.0, 0.0, 0.0, 0
    predicted = (probabilities[active, label_index] >= threshold).float()
    actual = targets[active, label_index]
    true_positive = float((predicted * actual).sum())
    false_positive = float((predicted * (1 - actual)).sum())
    false_negative = float(((1 - predicted) * actual).sum())
    precision = true_positive / max(true_positive + false_positive, 1e-9)
    recall = true_positive / max(true_positive + false_negative, 1e-9)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return precision, recall, f1, int(actual.sum())


def sweep(probabilities, targets, masks):
    """Best threshold per label, by F1 on this split."""
    chosen = {}
    for label_index, name in enumerate(LABELS):
        best = max(CANDIDATES,
                   key=lambda cut: score_label(probabilities, targets, masks, label_index, cut)[2])
        chosen[name] = best
    return chosen


def report(title, probabilities, targets, masks, thresholds):
    print("\n{}".format(title))
    print("{:<10} {:>6} {:>8} {:>8} {:>8} {:>8}".format(
        "label", "cut", "support", "P", "R", "F1"))
    f1_values = []
    rows = {}
    for label_index, name in enumerate(LABELS):
        cut = thresholds[name]
        precision, recall, f1, support = score_label(
            probabilities, targets, masks, label_index, cut)
        f1_values.append(f1)
        rows[name] = {"threshold": cut, "support": support,
                      "precision": precision, "recall": recall, "f1": f1}
        print("{:<10} {:>6.2f} {:>8} {:>8.4f} {:>8.4f} {:>8.4f}".format(
            name, cut, support, precision, recall, f1))
    macro = sum(f1_values) / len(f1_values)
    print("{:<10} {:>6} {:>8} {:>8} {:>8} {:>8.4f}".format("macro", "", "", "", "", macro))
    return macro, rows


def main():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    workers = int(os.environ.get("STYLESYNC_WORKERS", 6))
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model, saved = load_model(device)
    print("Loaded {}".format(CHECKPOINT_PATH))
    if "macro_f1" in saved:
        print("  checkpoint reports epoch {} at macro F1 {:.4f}".format(
            saved["epoch"], saved["macro_f1"]))
    print()

    val = collect(model, "val", device, workers)
    test = collect(model, "test", device, workers)

    default = {name: 0.5 for name in LABELS}
    val_default, _ = report("val @ 0.5 (what training reported)", *val, default)
    tuned = sweep(*val)
    val_tuned, val_rows = report("val @ tuned (thresholds chosen here)", *val, tuned)

    test_default, test_default_rows = report("test @ 0.5", *test, default)
    test_tuned, test_tuned_rows = report(
        "test @ tuned (val thresholds, untouched)", *test, tuned)

    print("\nmacro F1")
    print("  val   0.5 -> tuned : {:.4f} -> {:.4f}  ({:+.4f})".format(
        val_default, val_tuned, val_tuned - val_default))
    print("  test  0.5 -> tuned : {:.4f} -> {:.4f}  ({:+.4f})".format(
        test_default, test_tuned, test_tuned - test_default))
    print("\nThe test line is the honest one: those thresholds never saw this split.")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": os.path.basename(CHECKPOINT_PATH),
        "labels": LABELS,
        "axes": {axis: [AXES[axis].start, AXES[axis].stop] for axis in AXIS_ORDER},
        "thresholds": tuned,
        "macro_f1": {
            "val_at_0.5": val_default, "val_tuned": val_tuned,
            "test_at_0.5": test_default, "test_tuned": test_tuned,
        },
        "val": val_rows,
        "test_at_0.5": test_default_rows,
        "test_tuned": test_tuned_rows,
    }
    with open(THRESHOLD_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print("\nWrote {}".format(THRESHOLD_PATH))


if __name__ == "__main__":
    main()
