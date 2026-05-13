"""
DocuMind AI — Image Preprocessing Pipeline
===========================================
WHY WE DO THIS:
    Raw scanned images are often slightly rotated (skewed), have uneven lighting,
    or contain noise/grain. If you feed these directly into PaddleOCR or Tesseract,
    accuracy plummets by 20-40%. 
    
    Preprocessing standardizes the image: perfectly horizontal, stark black and white,
    with no noise. This dramatically boosts OCR engine confidence.

ENGINEERING BEST PRACTICES:
    - We use OpenCV (cv2) because it is the industry standard and extremely fast (C++).
    - We keep these functions pure (Image -> Image) so they are highly testable.
    - We avoid hardcoding kernel sizes; we use parameters with sensible defaults.

PIPELINE: Grayscale -> Denoise -> Deskew -> Adaptive Thresholding -> OCR
"""

import cv2
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Tuple

class ImagePreprocessor:
    """Core logic for image enhancement prior to OCR."""

    @staticmethod
    def read_image(image_path: Path | str) -> np.ndarray:
        """Reads image from disk safely."""
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Failed to load image from {image_path}")
        return img

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Convert to grayscale. Color data is useless and distracting for OCR."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """
        Removes background noise/grain.
        Uses Gaussian Blur. Bilateral filter is better but much slower.
        For document OCR, a simple 3x3 or 5x5 Gaussian blur is usually optimal.
        """
        # We apply a slight blur to smooth out the noise before thresholding
        return cv2.GaussianBlur(image, (5, 5), 0)

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """
        Detects text orientation and rotates the image to be perfectly horizontal.
        
        HOW IT WORKS:
            1. Invert image (white text, black background).
            2. Find all non-zero pixels (text coordinates).
            3. Calculate a bounding box (minAreaRect) containing all text.
            4. Extract the angle of that bounding box.
            5. Rotate the entire image by that angle.
        """
        # Ensure grayscale
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Threshold to create binary image (inverted)
        # Text becomes white, background becomes black
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # Get all white pixel coordinates
        coords = np.column_stack(np.where(thresh > 0))
        
        # If image is totally blank, return as is
        if len(coords) == 0:
            return image

        # Calculate bounding box angle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        
        # OpenCV 4.5+ returns angle in [0, 90]
        # Older versions return angle in [-90, 0)
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = angle - 90
        else:
            angle = -angle

        # If the skew is very minor (e.g. < 0.5 degrees), don't rotate (saves compute & avoids blur)
        if abs(angle) < 0.5:
            return image

        logger.debug(f"Deskewing image by {angle:.2f} degrees")
        
        # Execute the rotation
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Fill empty space after rotation with white (255, 255, 255)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC, 
            borderMode=cv2.BORDER_CONSTANT, 
            borderValue=(255, 255, 255)
        )
        return rotated

    @staticmethod
    def adaptive_threshold(image: np.ndarray) -> np.ndarray:
        """
        Binarization (Black & White).
        
        WHY ADAPTIVE?
            Standard thresholding uses one value globally. If a page has a shadow
            on one side, standard thresholding will turn the shadow pitch black, hiding text.
            Adaptive Thresholding calculates the threshold for small regions locally,
            completely eliminating shadows and uneven lighting.
        """
        # Ensure grayscale
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Adaptive Gaussian Thresholding
        # blockSize=21 (size of pixel neighborhood)
        # C=10 (constant subtracted from mean)
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 10
        )
        return binary

    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """
        Enhances image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        This brings out faded text on poor quality scans.
        """
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @staticmethod
    def sharpen(image: np.ndarray) -> np.ndarray:
        """
        Applies a sharpening filter to make blurry text edges crisp.
        """
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)

    @staticmethod
    def process_for_ocr(image: Path | np.ndarray, output_path: Path | None = None) -> np.ndarray:
        """
        The Master Preprocessing Pipeline.
        Executes the exact sequence required for optimal OCR extraction.
        Accepts either a file path or a NumPy array directly.
        """
        try:
            # 1. Read or use array directly
            if isinstance(image, (Path, str)):
                img = ImagePreprocessor.read_image(Path(image))
            else:
                img = image
            
            # 2. Deskew (done on raw image to avoid warping artifacts on binary pixels)
            deskewed = ImagePreprocessor.deskew(img)
            
            # 3. Grayscale
            gray = ImagePreprocessor.to_grayscale(deskewed)
            
            # 4. Enhance Contrast
            contrasted = ImagePreprocessor.enhance_contrast(gray)
            
            # 5. Denoise
            denoised = ImagePreprocessor.denoise(contrasted)
            
            # 6. Sharpen
            sharpened = ImagePreprocessor.sharpen(denoised)
            
            # 7. Adaptive Threshold (Binarization)
            final_binary = ImagePreprocessor.adaptive_threshold(sharpened)
            
            # Save if requested (useful for debugging/logging)
            if output_path:
                cv2.imwrite(str(output_path), final_binary)
                
            return final_binary
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise RuntimeError(f"Preprocessing pipeline failed: {e}")
