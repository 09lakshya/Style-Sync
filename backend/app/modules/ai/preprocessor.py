import logging
import cv2
import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger("stylesync.ai.preprocessor")


class ImagePreprocessor:
    """
    OpenCV and Pillow image preprocessing engine for computer vision and multimodal feature extraction.
    """

    @staticmethod
    def decode_image_bytes(file_bytes: bytes) -> np.ndarray:
        """Decode raw image bytes into an OpenCV BGR numpy array."""
        if not file_bytes:
            raise ValueError("Empty image byte array provided for preprocessing.")

        np_arr = np.frombuffer(file_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("OpenCV could not decode the provided image bytes.")

        return bgr

    @staticmethod
    def enhance_contrast_and_lighting(bgr_image: np.ndarray) -> np.ndarray:
        """
        Enhance image exposure and contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        applied strictly to the L (Luminance) channel in LAB color space to preserve chromaticity.
        """
        if not settings.enable_clahe_preprocessing:
            return bgr_image

        try:
            lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)

            # Apply CLAHE to L-channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_l = clahe.apply(l_channel)

            merged_lab = cv2.merge((enhanced_l, a_channel, b_channel))
            enhanced_bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
            return enhanced_bgr
        except Exception as exc:
            logger.warning("CLAHE enhancement failed, using original BGR image: %s", exc)
            return bgr_image

    @classmethod
    def preprocess_for_clip(cls, file_bytes: bytes, target_size: tuple[int, int] = (224, 224)) -> Image.Image:
        """
        Process raw image bytes through OpenCV decoding, contrast enhancement, and convert to PIL RGB.
        """
        bgr = cls.decode_image_bytes(file_bytes)
        enhanced_bgr = cls.enhance_contrast_and_lighting(bgr)

        # Convert OpenCV BGR to RGB
        rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image
        pil_image = Image.fromarray(rgb)

        # Resize if specified while maintaining aspect ratio and centering
        if target_size:
            pil_image = pil_image.resize(target_size, Image.Resampling.BICUBIC)

        return pil_image


preprocessor = ImagePreprocessor()
