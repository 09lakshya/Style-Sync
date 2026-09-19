"""Locate the person in a photo so analysis sees the garment, not the room.

CLIP embeds the whole image. In a full-scene photo the subject can occupy a
small fraction of the frame -- a heritage-room portrait measured here put the
person at 5.8% -- so colour, pattern and sleeve judgements are dominated by
background. Cropping to the detected person restores the garment as the subject.

Uses a COCO-pretrained detector from torchvision (already a dependency). The
model is loaded once, lazily, on first use.
"""

import logging
from typing import Any

from PIL import Image

logger = logging.getLogger("stylesync.ai.subject")

PERSON_LABEL = 1  # COCO class id
MIN_SCORE = 0.5
# Padding around the box, as a fraction of its size, so hems and sleeves are not
# clipped by a tight detection.
BOX_PADDING = 0.08
# Only crop when the subject is genuinely lost in the frame. Measured on 80
# ground-truth images, cropping normally-framed garment photos REDUCES accuracy
# (0.575 -> 0.475 on sleeve detection), so this is deliberately conservative:
# ordinary wardrobe photos are left untouched and only full-scene shots, where
# the background demonstrably contaminates the result, are cropped.
MAX_COVERAGE_TO_CROP = 0.25


class SubjectDetector:
    def __init__(self) -> None:
        self.model: Any = None
        self._is_loaded = False
        self._load_failed = False

    def load_model(self) -> None:
        if self._is_loaded or self._load_failed:
            return
        try:
            from torchvision.models.detection import (
                FasterRCNN_MobileNet_V3_Large_320_FPN_Weights,
                fasterrcnn_mobilenet_v3_large_320_fpn,
            )

            weights = FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT
            self.model = fasterrcnn_mobilenet_v3_large_320_fpn(weights=weights)
            self.model.eval()
            self._is_loaded = True
            logger.info("Subject detector loaded")
        except Exception as exc:
            # Analysis must still work without it -- callers fall back to the
            # full frame.
            self._load_failed = True
            logger.warning("Subject detector unavailable, using full frame: %s", exc)

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def crop_to_subject(self, pil_image: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
        """Return (image, info). Falls back to the original image unchanged."""
        info: dict[str, Any] = {"cropped": False, "reason": "", "coverage": None, "score": None}

        self.load_model()
        if not self._is_loaded:
            info["reason"] = "detector unavailable"
            return pil_image, info

        try:
            import torch
            import torchvision.transforms.functional as TF

            rgb = pil_image.convert("RGB") if pil_image.mode != "RGB" else pil_image
            with torch.no_grad():
                out = self.model([TF.to_tensor(rgb)])[0]

            best_box, best_score = None, 0.0
            for box, label, score in zip(out["boxes"], out["labels"], out["scores"]):
                s = float(score)
                if int(label) == PERSON_LABEL and s >= MIN_SCORE and s > best_score:
                    best_box, best_score = box.tolist(), s

            if best_box is None:
                info["reason"] = "no person detected"
                return pil_image, info

            width, height = rgb.size
            x0, y0, x1, y1 = best_box
            coverage = ((x1 - x0) * (y1 - y0)) / float(width * height)
            info["coverage"] = round(coverage, 4)
            info["score"] = round(best_score, 4)

            if coverage >= MAX_COVERAGE_TO_CROP:
                info["reason"] = "subject already fills the frame"
                return pil_image, info

            pad_x = (x1 - x0) * BOX_PADDING
            pad_y = (y1 - y0) * BOX_PADDING
            box = (
                max(0, int(x0 - pad_x)),
                max(0, int(y0 - pad_y)),
                min(width, int(x1 + pad_x)),
                min(height, int(y1 + pad_y)),
            )
            if box[2] - box[0] < 32 or box[3] - box[1] < 32:
                info["reason"] = "detected region too small to crop"
                return pil_image, info

            info["cropped"] = True
            info["reason"] = "cropped to detected person"
            return rgb.crop(box), info

        except Exception as exc:
            logger.warning("Subject detection failed, using full frame: %s", exc)
            info["reason"] = f"detection error: {exc}"
            return pil_image, info


subject_detector = SubjectDetector()
