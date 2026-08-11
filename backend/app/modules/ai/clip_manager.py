import hashlib
import logging
import math
import numpy as np
from PIL import Image
from typing import Any

from app.core.config import settings

logger = logging.getLogger("stylesync.ai.clip")


class CLIPManager:
    """
    Singleton manager for OpenAI CLIP (openai/clip-vit-base-patch32).
    Responsible for model lifecycle, float32 L2-normalized embedding extraction,
    and zero-shot attribute classification.
    """

    def __init__(self) -> None:
        self.model: Any = None
        self.processor: Any = None
        self._is_loaded: bool = False
        self.embedding_dim: int = 512

    def load_model(self) -> None:
        """Load pretrained CLIP model and processor into memory."""
        if self._is_loaded:
            return

        logger.info("Initializing CLIP model manager (%s)...", settings.clip_model_name)
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            self.model = CLIPModel.from_pretrained(settings.clip_model_name)
            self.processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
            self.model.eval()

            # Set model device
            device = settings.ai_device
            if device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to("cuda")
            else:
                self.model = self.model.to("cpu")

            self._is_loaded = True
            logger.info("CLIP model loaded successfully on device: %s", device)
        except Exception as exc:
            logger.warning("Could not load HuggingFace CLIP model (%s). Fallback inference active: %s", settings.clip_model_name, exc)
            self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def generate_image_embedding(self, pil_image: Image.Image) -> list[float]:
        """
        Generate a 512-dimensional float32 L2-normalized vector embedding for an image.
        """
        if self._is_loaded and self.model is not None and self.processor is not None:
            try:
                import torch

                inputs = self.processor(images=pil_image, return_tensors="pt")
                device = next(self.model.parameters()).device
                inputs = {k: v.to(device) for k, v in inputs.items()}

                with torch.no_grad():
                    output = self.model.get_image_features(**inputs)
                    image_features = getattr(output, "pooler_output", output)
                    if not isinstance(image_features, torch.Tensor):
                        image_features = output[0]
                    # L2-normalize
                    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                    embedding_vector = image_features[0].cpu().to(torch.float32).numpy().tolist()

                self.embedding_dim = len(embedding_vector)
                return embedding_vector
            except Exception as exc:
                logger.warning("CLIP live inference failed, using fallback embedding: %s", exc)

        # Fallback deterministic L2-normalized embedding generator
        return self._generate_fallback_image_embedding(pil_image)

    def generate_text_embedding(self, text: str) -> list[float]:
        """
        Generate a 512-dimensional float32 L2-normalized vector embedding for text.
        """
        if self._is_loaded and self.model is not None and self.processor is not None:
            try:
                import torch

                inputs = self.processor(text=[text], return_tensors="pt", padding=True)
                device = next(self.model.parameters()).device
                inputs = {k: v.to(device) for k, v in inputs.items()}

                with torch.no_grad():
                    output = self.model.get_text_features(**inputs)
                    text_features = getattr(output, "pooler_output", output)
                    if not isinstance(text_features, torch.Tensor):
                        text_features = output[0]
                    text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
                    return text_features[0].cpu().to(torch.float32).numpy().tolist()
            except Exception as exc:
                logger.warning("CLIP text inference failed, using fallback embedding: %s", exc)

        return self._generate_fallback_text_embedding(text)

    def zero_shot_classify(
        self,
        pil_image: Image.Image,
        candidate_labels: list[str],
        prompt_template: str = "a photo of a {} clothing item",
    ) -> list[tuple[str, float]]:
        """
        Perform zero-shot classification over candidate labels using prompt templates.
        Returns a list of (label, probability) tuples sorted descending by probability.
        """
        if not candidate_labels:
            return []

        if self._is_loaded and self.model is not None and self.processor is not None:
            try:
                import torch

                prompts = [prompt_template.format(label) for label in candidate_labels]
                inputs = self.processor(
                    text=prompts,
                    images=pil_image,
                    return_tensors="pt",
                    padding=True,
                )
                device = next(self.model.parameters()).device
                inputs = {k: v.to(device) for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits_per_image = outputs.logits_per_image  # [1, len(prompts)]
                    probs = logits_per_image.softmax(dim=1)[0].cpu().numpy().tolist()

                results = list(zip(candidate_labels, probs))
                results.sort(key=lambda x: x[1], reverse=True)
                return results
            except Exception as exc:
                logger.warning("Zero-shot CLIP classification failed, using fallback: %s", exc)

        # Fallback heuristic zero-shot matching
        return self._fallback_zero_shot(pil_image, candidate_labels)

    def _generate_fallback_image_embedding(self, pil_image: Image.Image) -> list[float]:
        """Generate deterministic 512-dim unit vector from image RGB histogram and hash."""
        # Use image RGB stats as seed
        rgb_img = pil_image.convert("RGB").resize((32, 32))
        raw_bytes = rgb_img.tobytes()
        digest = hashlib.sha256(raw_bytes).digest()

        # Build 512 dimensions
        vector = []
        for i in range(512):
            b1 = digest[i % len(digest)]
            b2 = digest[(i * 7 + 13) % len(digest)]
            val = ((b1 ^ b2) / 127.5) - 1.0
            vector.append(val)

        # L2-normalize
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [float(v / norm) for v in vector]

    def _generate_fallback_text_embedding(self, text: str) -> list[float]:
        """Generate deterministic 512-dim unit vector from text seed."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []
        for i in range(512):
            b = digest[(i * 13 + 5) % len(digest)]
            vector.append((b / 127.5) - 1.0)
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [float(v / norm) for v in vector]

    def _fallback_zero_shot(self, pil_image: Image.Image, candidate_labels: list[str]) -> list[tuple[str, float]]:
        """Fallback distribution across candidate labels."""
        n = len(candidate_labels)
        if n == 0:
            return []
        # Assign uniform or slightly stepped probabilities
        base_prob = 1.0 / n
        return [(label, round(base_prob, 4)) for label in candidate_labels]


clip_manager = CLIPManager()
