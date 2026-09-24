"""Train the three-axis wardrobe model: occasion, season, tradition.

Replaces the single softmax over seven mutually-exclusive folders. Those seven
classes were three questions flattened into one -- a cotton kurta is Ethnic and
Summer and Casual, and cross-entropy forced it to pick one and be marked wrong
on the other two. That ceiling, not a shortage of images, is what held test
accuracy at 0.726.

Here each axis gets its own sigmoid outputs and its own masked BCE term, so a
sample teaches only the axes its source actually labelled. The backbone and the
two-phase transfer-learning schedule are unchanged from train.py.

model/train.py is left in place: keep it until this path has been evaluated and
you are satisfied the new numbers are better, not just different.

    python model/train_multihead.py
"""

import argparse
import os
import sys
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models

from multilabel_dataset import AXES, AXIS_ORDER, LABELS, build_dataset, describe
from preprocess import get_transforms

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(BASE_DIR, "dataset", "processed", "00_myntra_manifest.csv")
CURATED = os.path.join(BASE_DIR, "dataset", "curated")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "backend", "app", "modules", "ai", "checkpoints")
ARTIFACT_DIR = os.path.join(BASE_DIR, "model", "artifacts")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "mobilenetv2_multihead.pth")
# Training overwrites its checkpoint in place, and the backend now serves that
# same file with thresholds calibrated against those exact weights. Writing new
# weights there mid-run would leave the API reading them through stale cuts, so
# a run can be pointed at a candidate file and promoted only once recalibrated.
OUTPUT_PATH = os.path.join(CHECKPOINT_DIR,
                           os.environ.get("STYLESYNC_CHECKPOINT_OUT",
                                          "mobilenetv2_multihead.pth"))
LOG_PATH = os.path.join(ARTIFACT_DIR, "multihead_train.log")


POS_WEIGHT_CAP = 50.0


class Tee:
    """Send every print to the terminal and to a log file at once.

    The first run reported its per-label F1 to stdout and nowhere else, so when
    the terminal was closed the only record of how the checkpoint scored went
    with it. A run that costs hours on CPU should not be able to lose its own
    numbers that way.
    """

    def __init__(self, stream, handle):
        self.stream = stream
        self.handle = handle

    def write(self, text):
        self.stream.write(text)
        self.handle.write(text)
        self.handle.flush()

    def flush(self):
        self.stream.flush()
        self.handle.flush()


def positive_weights(dataset):
    """neg/pos ratio per label, over the samples that actually label that axis.

    The Myntra catalogue is wildly unbalanced -- 15,621 casual against 22 party,
    11,924 summer against 823 winter. Plain BCE on that predicts "not party" for
    everything and scores well doing it. Weighting the positive term keeps the
    rare labels worth learning. The cap stops the thinnest label from producing a
    gradient so large it destabilises the shared backbone.
    """
    positives = torch.zeros(len(LABELS))
    labelled = torch.zeros(len(LABELS))
    for _, labels, masks in dataset.samples:
        for position, axis in enumerate(AXIS_ORDER):
            if not masks[position]:
                continue
            for index in range(*AXES[axis].indices(len(LABELS))):
                labelled[index] += 1
                positives[index] += labels[index]
    weights = (labelled - positives) / positives.clamp(min=1.0)
    return weights.clamp(min=1.0, max=POS_WEIGHT_CAP), positives, labelled


def masked_bce(logits, targets, masks, pos_weight):
    """BCE summed over axes, skipping axes a sample does not answer.

    Each axis is averaged over its own labelled samples before the axes are
    summed, so an axis with fewer labels still pulls its weight instead of being
    drowned out by whichever axis the catalogue happened to annotate most.
    """
    per_element = nn.functional.binary_cross_entropy_with_logits(
        logits, targets, reduction="none", pos_weight=pos_weight)
    total = logits.new_zeros(())
    for position, axis in enumerate(AXIS_ORDER):
        axis_mask = masks[:, position]
        if axis_mask.sum() == 0:
            continue
        axis_loss = per_element[:, AXES[axis]].mean(dim=1)
        total = total + (axis_loss * axis_mask).sum() / axis_mask.sum()
    return total


@torch.no_grad()
def evaluate(model, loader, device):
    """Per-label F1 at a 0.5 threshold, counting only labelled samples.

    Accuracy is not reported: with six sigmoids over a partially-labelled set it
    would be dominated by the majority-negative outputs and would look good for
    the wrong reason.
    """
    model.eval()
    tp = torch.zeros(len(LABELS))
    fp = torch.zeros(len(LABELS))
    fn = torch.zeros(len(LABELS))

    for inputs, targets, masks in loader:
        inputs = inputs.to(device)
        probabilities = torch.sigmoid(model(inputs)).cpu()
        predictions = (probabilities >= 0.5).float()
        for position, axis in enumerate(AXIS_ORDER):
            columns = AXES[axis]
            active = masks[:, position].unsqueeze(1)
            predicted = predictions[:, columns] * active
            actual = targets[:, columns] * active
            tp[columns] += (predicted * actual).sum(dim=0)
            fp[columns] += (predicted * (1 - actual)).sum(dim=0)
            fn[columns] += ((1 - predicted) * actual).sum(dim=0)

    precision = tp / (tp + fp).clamp(min=1e-9)
    recall = tp / (tp + fn).clamp(min=1e-9)
    f1 = 2 * precision * recall / (precision + recall).clamp(min=1e-9)
    return f1, precision, recall


def train(resume=False):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    manifest = MANIFEST if os.path.isfile(MANIFEST) else None
    if manifest is None:
        print("No Myntra manifest yet; training on the curated tree alone.")
        print("Run dataset/scripts/00_ingest_myntra.py to add the catalogue.\n")

    datasets = {
        split: build_dataset(split, get_transforms(is_training=(split == "train")),
                             manifest_path=manifest, curated_dir=CURATED)
        for split in ("train", "val")
    }
    for split, dataset in datasets.items():
        print("{} split: {} images".format(split, len(dataset)))
        print(describe(dataset))
    print()

    # Decoding full-resolution catalogue JPEGs costs about as much as the forward
    # and backward pass combined, and this box has no CUDA. Workers overlap the
    # two so an epoch costs roughly compute alone instead of compute plus decode.
    workers = int(os.environ.get("STYLESYNC_WORKERS", 6))
    loader_kwargs = {"batch_size": 32, "num_workers": workers}
    if workers:
        loader_kwargs["persistent_workers"] = True
        loader_kwargs["prefetch_factor"] = 4
    loaders = {
        "train": torch.utils.data.DataLoader(datasets["train"], shuffle=True, **loader_kwargs),
        "val": torch.utils.data.DataLoader(datasets["val"], shuffle=False, **loader_kwargs),
    }

    pos_weight, positives, labelled = positive_weights(datasets["train"])
    print("{:<10} {:>10} {:>10} {:>12}".format("label", "positive", "labelled", "pos_weight"))
    for position, name in enumerate(LABELS):
        print("{:<10} {:>10.0f} {:>10.0f} {:>12.2f}".format(
            name, positives[position], labelled[position], pos_weight[position]))
    print()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    try:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    except Exception:
        model = models.mobilenet_v2(pretrained=True)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(LABELS))

    resumed_optimizer_state = None
    if resume:
        if not os.path.isfile(CHECKPOINT_PATH):
            raise SystemExit(
                "ERROR: --resume was asked for but there is no checkpoint at\n  {}\n"
                "Run without --resume to train from ImageNet weights.".format(CHECKPOINT_PATH))
        saved = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        if saved.get("labels") != LABELS:
            raise SystemExit(
                "ERROR: that checkpoint was trained on {}\nbut this run expects {}. "
                "Refusing to load mismatched heads.".format(saved.get("labels"), LABELS))
        model.load_state_dict(saved["state_dict"])
        # Adam's moments are part of where a run had got to, not a detail. Left
        # out, the first epochs go into rebuilding momentum the previous run had
        # already paid for, which is what made epochs 0 to 2 of the last resume
        # look like a converged model drifting sideways.
        resumed_optimizer_state = saved.get("optimizer")
        print("Resuming from {}".format(CHECKPOINT_PATH))
        if "epoch" in saved:
            print("  saved at epoch {}, macro F1 {:.4f}".format(
                saved["epoch"], saved.get("macro_f1", float("nan"))))
        if resumed_optimizer_state is None:
            print("  this checkpoint stores weights only -- it predates optimiser state,")
            print("  so fine-tuning restarts with a fresh Adam and its moments unset.")
        else:
            print("  optimiser state travels with it, so this continues the previous")
            print("  run rather than restarting momentum from zero.")
        print()

    model = model.to(device)
    pos_weight = pos_weight.to(device)

    # A resumed run has already paid for phase 1: its head is trained and its
    # backbone has been unfrozen once. Setting head_epochs to 0 makes the
    # existing `epoch == head_epochs` branch fire on the first epoch, which
    # unfreezes and drops to lr=1e-4 -- the same phase 2 the run was in when it
    # stopped, instead of re-flattening the head at lr=1e-3 first.
    head_epochs = 0 if resume else int(os.environ.get("STYLESYNC_HEAD_EPOCHS", 5))
    finetune_epochs = int(os.environ.get("STYLESYNC_EPOCHS", 25))
    patience = int(os.environ.get("STYLESYNC_PATIENCE", 8))
    num_epochs = head_epochs + finetune_epochs

    for parameter in model.features.parameters():
        parameter.requires_grad = False
    optimizer = optim.Adam(model.classifier.parameters(), lr=1e-3)
    scheduler = None

    checkpoint_path = OUTPUT_PATH
    if OUTPUT_PATH != CHECKPOINT_PATH:
        print("Writing improvements to {}".format(os.path.basename(OUTPUT_PATH)))
        print("The served checkpoint is left alone until this one is calibrated.\n")
    best_f1, best_epoch, epochs_since_best = 0.0, -1, 0

    if resume:
        # Score the loaded weights before training a single batch. Without this
        # baseline the first epoch to finish counts as "best so far" and
        # overwrites a checkpoint that may well have been better. It also
        # recovers the val numbers of the run that stopped, which were printed
        # to a closed terminal and lost.
        baseline, baseline_precision, baseline_recall = evaluate(model, loaders["val"], device)
        best_f1 = float(baseline.mean())
        print("Resumed checkpoint, scored on val before training:")
        print("{:<10} {:>7} {:>7} {:>7}".format("label", "P", "R", "F1"))
        for position, name in enumerate(LABELS):
            print("{:<10} {:>7.4f} {:>7.4f} {:>7.4f}".format(
                name, baseline_precision[position], baseline_recall[position], baseline[position]))
        print("macro F1: {:.4f}".format(best_f1))
        print("Only an epoch above that will overwrite it.")
    else:
        print("Phase 1: training head for {} epochs ({} outputs)".format(head_epochs, len(LABELS)))

    for epoch in range(num_epochs):
        if epoch == head_epochs:
            for parameter in model.features.parameters():
                parameter.requires_grad = True
            optimizer = optim.Adam(model.parameters(), lr=1e-4)
            if resumed_optimizer_state is not None:
                # Only valid here: the saved state came from this same phase-2
                # optimiser, Adam over every parameter. A mismatch means the
                # checkpoint was written by a different schedule, and carrying
                # on with a fresh optimiser beats loading moments that belong to
                # a different set of tensors.
                try:
                    optimizer.load_state_dict(resumed_optimizer_state)
                    print("\nRestored optimiser state from the checkpoint.")
                except ValueError as exc:
                    print("\nCould not restore optimiser state ({}); "
                          "continuing with a fresh Adam.".format(exc))
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)
            print("\nPhase 2: fine-tuning all layers at lr=1e-4 for {} epochs".format(finetune_epochs))

        print("\nEpoch {}/{}".format(epoch, num_epochs - 1))
        print("-" * 10)

        model.train()
        running_loss, seen = 0.0, 0
        for inputs, targets, masks in loaders["train"]:
            inputs, targets, masks = inputs.to(device), targets.to(device), masks.to(device)
            optimizer.zero_grad()
            loss = masked_bce(model(inputs), targets, masks, pos_weight)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * inputs.size(0)
            seen += inputs.size(0)
        print("train loss: {:.4f}".format(running_loss / max(seen, 1)))

        f1, precision, recall = evaluate(model, loaders["val"], device)
        print("{:<10} {:>7} {:>7} {:>7}".format("label", "P", "R", "F1"))
        for position, name in enumerate(LABELS):
            print("{:<10} {:>7.4f} {:>7.4f} {:>7.4f}".format(
                name, precision[position], recall[position], f1[position]))
        macro_f1 = float(f1.mean())
        print("macro F1: {:.4f}".format(macro_f1))

        if scheduler is not None:
            scheduler.step(macro_f1)

        if macro_f1 > best_f1:
            best_f1, best_epoch, epochs_since_best = macro_f1, epoch, 0
            torch.save({
                "state_dict": model.state_dict(),
                "labels": LABELS,
                "axes": AXIS_ORDER,
                "epoch": epoch,
                "macro_f1": macro_f1,
                "per_label_f1": {name: float(f1[index]) for index, name in enumerate(LABELS)},
                "optimizer": optimizer.state_dict(),
            }, checkpoint_path)
            print("  -> new best macro F1 {:.4f}, checkpoint saved".format(best_f1))
        else:
            epochs_since_best += 1

        if epochs_since_best >= patience:
            print("\nNo improvement for {} epochs; stopping early at epoch {}.".format(patience, epoch))
            break

    if best_epoch < 0:
        if resume:
            # Not a failure. The checkpoint on disk is still the best one seen
            # and was left untouched; the run simply found no improvement.
            print("\nNo epoch beat the resumed macro F1 of {:.4f}; the checkpoint "
                  "is unchanged on disk.".format(best_f1))
            print("Treat this as converged and evaluate it on test rather than "
                  "training it further.")
            return
        raise SystemExit("ERROR: no epoch improved on validation F1; nothing was saved.")
    print("\nBest checkpoint: epoch {}, macro F1 {:.4f} -> {}".format(best_epoch, best_f1, checkpoint_path))
    print("These numbers are not comparable to the 0.726 accuracy of the seven-class model;")
    print("they answer three separate questions rather than one impossible one.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train the three-axis wardrobe model.")
    parser.add_argument(
        "--resume", action="store_true",
        help="continue fine-tuning the saved checkpoint instead of starting from ImageNet weights")
    arguments = parser.parse_args()

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write("\n=== run started {} (resume={}) ===\n".format(
            datetime.now().isoformat(timespec="seconds"), arguments.resume))
        sys.stdout = Tee(sys.__stdout__, log)
        sys.stderr = Tee(sys.__stderr__, log)
        try:
            train(resume=arguments.resume)
        finally:
            sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
