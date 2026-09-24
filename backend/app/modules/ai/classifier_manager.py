import logging
import json
from pathlib import Path
from PIL import Image
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("stylesync.ai.classifier")

# The occasion labels are the ones that read as a "category" to a user, so a
# caller asking for one string gets an occasion first and only falls back to the
# other axes when no occasion fired. Season and tradition are real answers too,
# just not to the question "what kind of garment is this".
SINGLE_LABEL_PRIORITY = ["occasion", "tradition", "season"]


class ClassifierManager:
    """
    Singleton manager for the custom classification model (MobileNetV2).

    The checkpoint has six sigmoid outputs grouped into three independent axes --
    occasion, season, tradition -- rather than one softmax over seven classes.
    A garment is not required to pick between Ethnic, Summer and Casual when all
    three are true, which is what the old head forced it to do.

    Each output has its own decision threshold, measured on val and carried in
    metadata.json. They are nowhere near 0.5 for the rare labels (party 0.94,
    formal 0.88, winter 0.78) because the training loss weighted those positives
    to buy recall; reading them at a flat 0.5 costs about 0.06 macro F1.
    """

    def __init__(self) -> None:
        self.model: Any = None
        self.transform: Any = None
        self.labels: List[str] = []
        self.axes: Dict[str, Dict[str, Any]] = {}
        self.thresholds: Dict[str, float] = {}
        self._is_loaded: bool = False
        self.model_version: str = "v1"

    def load_model(self) -> None:
        """Load the multi-head checkpoint, its labels and its thresholds."""
        if self._is_loaded:
            return

        logger.info("Initializing Custom Classifier manager...")
        try:
            import torch
            import torchvision.transforms as transforms

            checkpoint_dir = Path("app/modules/ai/checkpoints")
            model_path = checkpoint_dir / "mobilenetv2_multihead.pth"
            metadata_path = checkpoint_dir / "metadata.json"

            if not model_path.exists():
                logger.warning(
                    "Model checkpoint not found at %s. Custom classification will be disabled.",
                    model_path,
                )
                self._is_loaded = False
                return

            if not metadata_path.exists():
                # Guessing what the outputs mean would silently mislabel every
                # prediction, so refuse to load rather than serve wrong answers.
                logger.error(
                    "Model metadata not found at %s. Classification is DISABLED. "
                    "Run model/export_serving_metadata.py to regenerate it.",
                    metadata_path,
                )
                self._is_loaded = False
                return

            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            self.labels = metadata.get("labels", [])
            self.axes = metadata.get("axes", {})
            self.thresholds = metadata.get("thresholds", {})
            self.model_version = metadata.get("version", "")

            if not self.labels or not self.axes or not self.model_version:
                logger.error(
                    "Model metadata at %s is missing labels, axes or version. "
                    "Classification is DISABLED.",
                    metadata_path,
                )
                self._is_loaded = False
                return

            # A missing threshold is not something to paper over with 0.5. That
            # default is wrong by a wide margin for exactly the labels most
            # likely to be missing, and the failure would be invisible.
            missing = [name for name in self.labels if name not in self.thresholds]
            if missing:
                logger.error(
                    "Metadata at %s has no threshold for %s. Classification is DISABLED. "
                    "Run model/calibrate_thresholds.py then model/export_serving_metadata.py.",
                    metadata_path,
                    ", ".join(missing),
                )
                self._is_loaded = False
                return

            from torchvision.models import mobilenet_v2
            import torch.nn as nn

            self.model = mobilenet_v2(pretrained=False)
            self.model.classifier[1] = nn.Linear(self.model.last_channel, len(self.labels))

            device = "cuda" if settings.ai_device == "cuda" and torch.cuda.is_available() else "cpu"

            checkpoint = torch.load(model_path, map_location=device, weights_only=False)
            # Training saves a dict around the weights; a bare state_dict is
            # still accepted so an older checkpoint does not become unloadable.
            state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
            saved_labels = checkpoint.get("labels") if isinstance(checkpoint, dict) else None
            if saved_labels and saved_labels != self.labels:
                logger.error(
                    "Checkpoint at %s was trained on %s but metadata.json describes %s. "
                    "Classification is DISABLED rather than served against mismatched labels.",
                    model_path, saved_labels, self.labels,
                )
                self._is_loaded = False
                return

            self.model.load_state_dict(state_dict)
            self.model = self.model.to(device)
            self.model.eval()

            # Matches model/preprocess.py's evaluation transform exactly. If these
            # drift apart the thresholds stop meaning anything, because they were
            # measured against images preprocessed this way.
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

            self._is_loaded = True
            logger.info(
                "Custom classifier loaded successfully (%s, %d labels) on device: %s",
                self.model_version, len(self.labels), device,
            )

        except Exception as exc:
            logger.warning(f"Could not load custom classifier model. Fallback active: {exc}")
            self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def _probabilities(self, pil_image: Image.Image) -> Optional[Dict[str, float]]:
        """Sigmoid score per label, or None if the model is unavailable."""
        if not self.is_loaded or self.model is None or self.transform is None:
            return None

        import torch

        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        input_tensor = self.transform(pil_image).unsqueeze(0)
        device = next(self.model.parameters()).device
        input_tensor = input_tensor.to(device)

        with torch.no_grad():
            # Sigmoid, not softmax: the outputs are independent questions and do
            # not compete for a shared probability mass.
            scores = torch.sigmoid(self.model(input_tensor)[0])

        return {name: float(scores[index]) for index, name in enumerate(self.labels)}

    def predict_axes(self, pil_image: Image.Image) -> Optional[Dict[str, Any]]:
        """Full three-axis reading of one image.

        Returns each axis's fired labels alongside every raw probability, so a
        caller can apply its own cut without a second forward pass.
        """
        try:
            probabilities = self._probabilities(pil_image)
        except Exception as exc:
            logger.error(f"Error during prediction: {exc}")
            return None
        if probabilities is None:
            return None

        result: Dict[str, Any] = {
            "probabilities": probabilities,
            "thresholds": dict(self.thresholds),
            "model_version": self.model_version,
        }
        for axis, definition in self.axes.items():
            axis_labels = definition.get("labels", [])
            fired = [name for name in axis_labels
                     if probabilities.get(name, 0.0) >= self.thresholds[name]]
            if definition.get("multi_label", True):
                result[axis] = fired
            else:
                # A single-output axis is a binary question, so the absence of
                # the positive label is itself an answer, not a blank.
                positive = axis_labels[0] if axis_labels else None
                result[axis] = positive if fired else definition.get("negative_label")
        return result

    def single_label(self, probabilities: Dict[str, float]) -> Tuple[Optional[str], Optional[float]]:
        """Collapse a set of scores to one label, for callers that want one.

        Takes probabilities rather than an image so a caller that already has
        them -- anything that called predict_axes -- does not pay for a second
        forward pass to also get this.
        """
        for axis in SINGLE_LABEL_PRIORITY:
            axis_labels = self.axes.get(axis, {}).get("labels", [])
            fired = [name for name in axis_labels
                     if probabilities.get(name, 0.0) >= self.thresholds[name]]
            if not fired:
                continue
            # Rank by how far past its own cut each label sits, not by raw
            # probability: at thresholds of 0.94 and 0.54 the raw numbers are
            # not on a comparable scale.
            best = max(fired, key=lambda name: probabilities[name] - self.thresholds[name])
            return best.capitalize(), probabilities[best]

        # Nothing cleared its threshold. Saying so beats inventing a label, but
        # the strongest score is still worth reporting as the near miss it is.
        if not probabilities:
            return None, None
        best = max(probabilities, key=lambda name: probabilities[name] - self.thresholds[name])
        return None, probabilities[best]

    def predict(self, pil_image: Image.Image) -> Tuple[Optional[str], Optional[float]]:
        """
        Predict the category of the given image.
        Returns: (predicted_category_string, confidence_score)

        Kept for callers that want one label. Six independent answers cannot be
        collapsed into one without losing something, so this reports the
        strongest label that cleared its own threshold -- see predict_axes for
        the reading that throws nothing away.
        """
        try:
            probabilities = self._probabilities(pil_image)
        except Exception as exc:
            logger.error(f"Error during prediction: {exc}")
            return None, None
        if probabilities is None:
            return None, None
        return self.single_label(probabilities)


# Singleton instance
classifier_manager = ClassifierManager()
