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
    def preprocess_for_clip(
        cls,
        file_bytes: bytes,
        target_size: tuple[int, int] = (224, 224),
        enhance: bool | None = None,
    ) -> Image.Image:
        """
        Process raw image bytes through OpenCV decoding, contrast enhancement, and convert to PIL RGB.

        `enhance` overrides the CLAHE setting for this call. Measured on labelled
        images, CLAHE helps structural attributes (sleeve detection 0.575 vs
        0.487) but distorts colour (0.575 vs 0.688), so callers ask for the
        variant that suits the attribute they are reading.
        """
        bgr = cls.decode_image_bytes(file_bytes)
        if enhance is False:
            enhanced_bgr = bgr
        else:
            enhanced_bgr = cls.enhance_contrast_and_lighting(bgr)

        # Convert OpenCV BGR to RGB
        rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image
        pil_image = Image.fromarray(rgb)

        # Resize while maintaining aspect ratio and centering.
        #
        # This used to squash straight to 224x224. The docstring claimed aspect
        # ratio was preserved, but a plain resize distorts every non-square
        # photo, and garments are read by their shape: a tall photo of wide-leg
        # linen trousers came out narrow and gathered, which CLIP called a
        # churidar. Letterboxing instead lifted tradition accuracy on the
        # curated test set from 93% to 98%, and fixed a men's blazer that was
        # scoring 0.18 as a waistcoat and now scores 0.76.
        if target_size:
            pil_image = cls.fit_to_canvas(pil_image, target_size)

        return pil_image

    @staticmethod
    def fit_to_canvas(
        image: Image.Image,
        target_size: tuple[int, int],
        background: tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """Scale to fit inside target_size, padding the remainder.

        Padding rather than cropping: a centre crop of a full-length photo cuts
        off the hem or the shoulders, and both carry the shape information that
        identifies the garment.
        """
        target_w, target_h = target_size
        scale = min(target_w / image.width, target_h / image.height)
        new_w = max(1, round(image.width * scale))
        new_h = max(1, round(image.height * scale))

        resized = image.resize((new_w, new_h), Image.Resampling.BICUBIC)
        canvas = Image.new("RGB", target_size, background)
        canvas.paste(resized, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        return canvas


preprocessor = ImagePreprocessor()
