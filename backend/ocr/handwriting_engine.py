"""
DocuMind AI — Handwriting OCR Engine (TrOCR)
==============================================
WHY TROCR?
    Traditional OCR engines like PaddleOCR use CNNs to detect visual shapes of letters.
    This fails spectacularly on cursive or messy handwriting where shapes blend together.
    Microsoft TrOCR uses a VisionEncoderDecoder model (Transformer), effectively
    treating OCR as an image-to-text translation problem. It uses language modeling
    to infer what messy words likely say based on context.
"""

from loguru import logger
import numpy as np
from PIL import Image
from backend.config.settings import settings

class HandwritingEngine:
    """Singleton wrapper for Microsoft TrOCR."""
    
    def __init__(self):
        logger.info("Initializing TrOCR (microsoft/trocr-base-handwritten)...")
        try:
            from huggingface_hub import try_to_load_from_cache
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            # Use cached files only so offline/local installs fail fast instead
            # of hanging on repeated network retries during document ingestion.
            model_name = "microsoft/trocr-base-handwritten"
            cached_config = try_to_load_from_cache(model_name, "config.json")
            if not isinstance(cached_config, str):
                raise FileNotFoundError(
                    f"Cached model '{model_name}' not found. Download it once to enable handwriting OCR."
                )
            self.processor = TrOCRProcessor.from_pretrained(
                model_name,
                local_files_only=True,
            )
            self.model = VisionEncoderDecoderModel.from_pretrained(
                model_name,
                local_files_only=True,
            )
            logger.info("TrOCR initialized successfully.")
        except Exception as e:
            logger.warning(f"TrOCR not available locally; disabling handwriting OCR fallback: {e}")
            # We don't raise here, we just let the instance be "broken"
            self.processor = None
            self.model = None
            
    def process_region(self, region_image_array: np.ndarray) -> str:
        """
        Takes a cropped NumPy array (a bounding box of handwriting) and translates it to text.
        """
        if self.model is None or self.processor is None:
            return ""
            
        if region_image_array is None or region_image_array.size == 0:
            return ""
            
        try:
            # TrOCR expects a PIL Image
            image = Image.fromarray(region_image_array).convert("RGB")
            
            # Preprocess the image for the transformer
            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values
            
            # Generate text
            generated_ids = self.model.generate(pixel_values)
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            return generated_text.strip()
            
        except Exception as e:
            logger.warning(f"TrOCR failed on region: {e}")
            return ""

# Global instance initialized lazily
handwriting_engine = None

def get_handwriting_engine() -> HandwritingEngine:
    if not settings.enable_handwriting_ocr:
        logger.debug("Handwriting OCR disabled by configuration.")
        return None

    global handwriting_engine
    if handwriting_engine is None:
        try:
            handwriting_engine = HandwritingEngine()
            if handwriting_engine.model is None:
                logger.warning("Handwriting engine failed to load models. Falling back to standard OCR.")
                return None
        except Exception as e:
            logger.error(f"Critical failure in handwriting engine setup: {e}")
            return None
    return handwriting_engine
