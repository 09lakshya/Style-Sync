r"""Partially-labelled multi-label dataset over the three StyleSync axes.

Six sigmoid outputs, grouped into three independent axes:

    index  0        1        2       3        4        5
           casual   formal   party   summer   winter   ethnic
           \____ occasion ____/      \_ season _/      tradition

`tradition` is one output where 1 means ethnic and 0 means western, because the
two are complementary; occasion and season are genuinely multi-label (a garment
can be both casual and party, or carry no season at all).

Every sample also carries a 3-wide mask, one flag per axis. A 0 means the source
never answered that question, and the loss skips it. This is what lets two very
differently-labelled sources train one model:

  * The Myntra manifest labels occasion and season independently, and tradition
    is derived from usage/articleType -- often all three axes at once.
  * The existing curated/ tree is single-label, so each image answers exactly
    one axis: Casual names an occasion and says nothing about season, Winter
    names a season and says nothing about occasion. Folding it in this way costs
    nothing and invents nothing.

Splits are assigned by a deterministic hash of the image id (seed 42, matching
dataset_config.yaml), so an image lands in the same split on every run and never
leaks between train and val.
"""

import csv
import hashlib
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

LABELS = ["casual", "formal", "party", "summer", "winter", "ethnic"]
AXES = {"occasion": slice(0, 3), "season": slice(3, 5), "tradition": slice(5, 6)}
AXIS_ORDER = ["occasion", "season", "tradition"]

MANIFEST_COLUMNS = [
    "occasion_casual", "occasion_formal", "occasion_party",
    "season_summer", "season_winter", "tradition_ethnic",
]
MASK_COLUMNS = ["mask_occasion", "mask_season", "mask_tradition"]

# How a single-label curated/ folder name answers one axis and leaves the rest
# unlabelled: (label index or None, axis name, positive?)
CURATED_FOLDER_TO_AXIS = {
    "Casual":  (0, "occasion", 1),
    "Formal":  (1, "occasion", 1),
    "Party":   (2, "occasion", 1),
    "Summer":  (3, "season", 1),
    "Winter":  (4, "season", 1),
    "Ethnic":  (5, "tradition", 1),
    "Western": (5, "tradition", 0),
}

SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED = 42


def assign_split(image_id):
    """Stable 70/15/15 split from the image id alone."""
    digest = hashlib.sha1("{}:{}".format(SEED, image_id).encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    if bucket < SPLIT_RATIOS["train"]:
        return "train"
    if bucket < SPLIT_RATIOS["train"] + SPLIT_RATIOS["val"]:
        return "val"
    return "test"


def load_manifest(manifest_path, split):
    """Rows from the Myntra manifest belonging to one split."""
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise SystemExit(
            "ERROR: manifest not found:\n  {}\n\n"
            "Run dataset/scripts/00_ingest_myntra.py first.".format(manifest_path)
        )
    samples = []
    with open(manifest_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            image_id = row["image_id"]
            if assign_split(image_id) != split:
                continue
            path = row.get("staged_path") or row["source_path"]
            labels = [float(row[column]) for column in MANIFEST_COLUMNS]
            masks = [float(row[column]) for column in MASK_COLUMNS]
            samples.append((path, labels, masks))
    return samples


def load_curated(curated_dir, split):
    """The existing single-label tree, read as one-axis-labelled samples.

    The curated tree has its own train/val/test folders; those are respected
    rather than re-split, so images keep the split they were evaluated under.
    """
    curated_dir = Path(curated_dir)
    split_dir = curated_dir / split
    if not split_dir.is_dir():
        return []
    samples = []
    for folder_name, (index, axis, positive) in CURATED_FOLDER_TO_AXIS.items():
        folder = split_dir / folder_name
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            labels = [0.0] * len(LABELS)
            masks = [0.0] * len(AXIS_ORDER)
            labels[index] = float(positive)
            masks[AXIS_ORDER.index(axis)] = 1.0
            samples.append((str(path), labels, masks))
    return samples


class MultiLabelWardrobe(Dataset):
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, labels, masks = self.samples[index]
        with Image.open(path) as img:
            image = self.transform(img.convert("RGB"))
        return image, torch.tensor(labels, dtype=torch.float32), torch.tensor(masks, dtype=torch.float32)


def build_dataset(split, transform, manifest_path=None, curated_dir=None):
    samples = []
    if manifest_path is not None:
        samples.extend(load_manifest(manifest_path, split))
    if curated_dir is not None:
        samples.extend(load_curated(curated_dir, split))
    if not samples:
        raise SystemExit(
            "ERROR: the {} split is empty. Training on nothing produces a model "
            "whose metrics mean nothing.".format(split)
        )
    return MultiLabelWardrobe(samples, transform)


def describe(dataset):
    """Per-axis counts, so a thin axis is visible before training rather than after."""
    lines = []
    labelled = {axis: 0 for axis in AXIS_ORDER}
    positive = {name: 0 for name in LABELS}
    for _, labels, masks in dataset.samples:
        for position, axis in enumerate(AXIS_ORDER):
            if masks[position]:
                labelled[axis] += 1
        for position, name in enumerate(LABELS):
            axis = AXIS_ORDER[0 if position < 3 else (1 if position < 5 else 2)]
            if masks[AXIS_ORDER.index(axis)] and labels[position]:
                positive[name] += 1
    for axis in AXIS_ORDER:
        names = LABELS[AXES[axis]]
        counts = ", ".join("{} {}".format(name, positive[name]) for name in names)
        lines.append("  {:<10} {:>6} labelled   ({})".format(axis, labelled[axis], counts))
    return "\n".join(lines)
