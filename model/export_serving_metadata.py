r"""Write the serving contract the backend reads, from the calibration results.

metadata.json is what classifier_manager loads to find out what the checkpoint's
outputs mean. It still describes the old seven-class softmax, so the backend
would read six sigmoid outputs as seven mutually-exclusive classes if it were
pointed at the new checkpoint. This regenerates it.

The thresholds belong here rather than in the backend source. They were measured
on val and verified on test; a number that came from a measurement should travel
with the checkpoint that produced it, not be typed into a service by hand where
it can drift from the weights it was calibrated against.

No forward pass -- this reads model/artifacts/multihead_thresholds.json and the
checkpoint, so it is cheap to re-run after any recalibration.

    python model/export_serving_metadata.py
"""

import json
import os
from datetime import datetime, timezone

import torch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_DIR = os.path.join(BASE_DIR, "backend", "app", "modules", "ai", "checkpoints")
ARTIFACT_DIR = os.path.join(BASE_DIR, "model", "artifacts")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "mobilenetv2_multihead.pth")
THRESHOLD_PATH = os.path.join(ARTIFACT_DIR, "multihead_thresholds.json")
METADATA_PATH = os.path.join(CHECKPOINT_DIR, "metadata.json")

# Bump this whenever the weights change, not just when the format does. Wardrobe
# items store the model_version that labelled them, so leaving it fixed across a
# promotion would make two different models indistinguishable in the data and
# there would be no way to tell which predictions to re-check.
MODEL_VERSION = "mobilenetv2-multihead-1.2"


def main():
    if not os.path.isfile(THRESHOLD_PATH):
        raise SystemExit(
            "ERROR: no calibration at\n  {}\n"
            "Run model/calibrate_thresholds.py first; serving at a flat 0.5 costs "
            "about 0.06 macro F1.".format(THRESHOLD_PATH))
    if not os.path.isfile(CHECKPOINT_PATH):
        raise SystemExit("ERROR: no checkpoint at\n  {}".format(CHECKPOINT_PATH))

    with open(THRESHOLD_PATH, encoding="utf-8") as handle:
        calibration = json.load(handle)

    saved = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    labels = saved.get("labels")
    if labels != calibration["labels"]:
        raise SystemExit(
            "ERROR: the checkpoint's labels {}\ndo not match the calibration's {}.\n"
            "Recalibrate before exporting; stale thresholds are worse than none, "
            "because they look authoritative.".format(labels, calibration["labels"]))

    metadata = {
        "version": MODEL_VERSION,
        "architecture": "mobilenet_v2",
        "head": "multilabel",
        "checkpoint": os.path.basename(CHECKPOINT_PATH),
        "input_size": 224,
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        # Six sigmoid outputs in this order, grouped into three independent
        # questions. `tradition` is a single output: 1 means ethnic, 0 western.
        "labels": labels,
        "axes": {
            "occasion": {"labels": ["casual", "formal", "party"], "multi_label": True},
            "season": {"labels": ["summer", "winter"], "multi_label": True},
            "tradition": {"labels": ["ethnic"], "multi_label": False,
                          "negative_label": "western"},
        },
        # Measured, not assumed. pos_weight pushed the rare labels' logits up to
        # buy recall, so a flat 0.5 reads them as positives far too often:
        # party sat at 0.46 precision against 0.97 recall until this was applied.
        "thresholds": calibration["thresholds"],
        "metrics": {
            "split": "test",
            "num_samples": sum(row["support"] for row in calibration["test_tuned"].values()),
            "macro_f1": calibration["macro_f1"]["test_tuned"],
            "macro_f1_at_0.5": calibration["macro_f1"]["test_at_0.5"],
            "per_label_f1": {name: row["f1"] for name, row in calibration["test_tuned"].items()},
            "note": "Thresholds were chosen on val and applied unchanged to test. "
                    "Not comparable to the 0.726 accuracy of the seven-class model: "
                    "that was one softmax over three conflated questions.",
        },
        "calibrated_at": calibration["generated_at"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    print("Wrote {}".format(METADATA_PATH))
    print("  version   {}".format(MODEL_VERSION))
    print("  labels    {}".format(", ".join(labels)))
    print("  test macro F1 {:.4f} (was {:.4f} at a flat 0.5)".format(
        metadata["metrics"]["macro_f1"], metadata["metrics"]["macro_f1_at_0.5"]))


if __name__ == "__main__":
    main()
