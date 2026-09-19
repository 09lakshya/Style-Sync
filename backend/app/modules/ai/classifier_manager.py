import logging
import json
from pathlib import Path
from PIL import Image
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("stylesync.ai.classifier")

class ClassifierManager:
    """
    Singleton manager for the custom classification model (MobileNetV2).
    Responsible for loading the custom trained model and predicting categories.
    """

    def __init__(self) -> None:
        self.model: Any = None
        self.transform: Any = None
        self.class_mapping: Dict[int, str] = {}
        self._is_loaded: bool = False
        self.model_version: str = "v1"

    def load_model(self) -> None:
        """Load the custom trained model and its class mappings."""
        if self._is_loaded:
            return

        logger.info("Initializing Custom Classifier manager...")
        try:
            import torch
            import torchvision.transforms as transforms
            
            # Load the trained MobileNetV2 model
            checkpoint_dir = Path("app/modules/ai/checkpoints")
            model_path = checkpoint_dir / "mobilenetv2_fashion.pth"
            metadata_path = checkpoint_dir / "metadata.json"
            
            if not model_path.exists():
                logger.warning(f"Model checkpoint not found at {model_path}. Custom classification will be disabled.")
                self._is_loaded = False
                return

            if not metadata_path.exists():
                # Guessing the class mapping would silently mislabel every prediction,
                # so refuse to load rather than serve wrong categories.
                logger.error(
                    "Model metadata not found at %s. Classification is DISABLED. "
                    "Run model/evaluate.py to regenerate it.",
                    metadata_path,
                )
                self._is_loaded = False
                return

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            self.class_mapping = {int(k): v for k, v in metadata.get("class_mapping", {}).items()}
            self.model_version = metadata.get("version", "")

            if not self.class_mapping or not self.model_version:
                logger.error(
                    "Model metadata at %s is missing class_mapping or version. "
                    "Classification is DISABLED.",
                    metadata_path,
                )
                self._is_loaded = False
                return

            # Load the architecture (e.g., MobileNetV2) and weights
            from torchvision.models import mobilenet_v2
            import torch.nn as nn

            num_classes = len(self.class_mapping)
            self.model = mobilenet_v2(pretrained=False)
            self.model.classifier[1] = nn.Linear(self.model.last_channel, num_classes)
            
            device = "cuda" if settings.ai_device == "cuda" and torch.cuda.is_available() else "cpu"
            
            self.model.load_state_dict(torch.load(model_path, map_location=device))
            self.model = self.model.to(device)
            self.model.eval()

            # Preprocessing transform
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

            self._is_loaded = True
            logger.info(f"Custom classifier loaded successfully (v{self.model_version}) on device: {device}")
            
        except Exception as exc:
            logger.warning(f"Could not load custom classifier model. Fallback active: {exc}")
            self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def predict(self, pil_image: Image.Image) -> Tuple[Optional[str], Optional[float]]:
        """
        Predict the category of the given image.
        Returns: (predicted_category_string, confidence_score)
        """
        if not self.is_loaded or self.model is None or self.transform is None:
            return None, None

        try:
            import torch
            
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
                
            input_tensor = self.transform(pil_image).unsqueeze(0)
            
            device = next(self.model.parameters()).device
            input_tensor = input_tensor.to(device)

            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                
                confidence, predicted_idx = torch.max(probabilities, 0)
                
                predicted_class = self.class_mapping.get(predicted_idx.item())
                return predicted_class, confidence.item()
                
        except Exception as exc:
            logger.error(f"Error during prediction: {exc}")
            return None, None

# Singleton instance
classifier_manager = ClassifierManager()
