"""
core/preprocessing.py

ImagePreprocessor: turns a raw phone photo into a clean binary image,
saving a snapshot after each stage so the report can show the
step-by-step process the coursework asks for.
"""

import os
import cv2
import numpy as np


class ImagePreprocessor:
    """Handles greyscale conversion and binarization for a single sheet image."""

    def __init__(self, snapshot_dir: str = None):
        """
        snapshot_dir: if given, each stage's output image is written here
                      as <stage_name>.jpg for report screenshots.
        """
        self.snapshot_dir = snapshot_dir
        if self.snapshot_dir:
            os.makedirs(self.snapshot_dir, exist_ok=True)

    def _save(self, name: str, image: np.ndarray) -> None:
        if self.snapshot_dir:
            cv2.imwrite(os.path.join(self.snapshot_dir, f"{name}.jpg"), image)

    def load(self, path: str) -> np.ndarray:
        image = cv2.imread(path)
        if image is None:
            raise FileNotFoundError(f"Could not read image: {path}")
        self._save("01_original", image)
        return image

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self._save("02_grayscale", gray)
        return gray

    def blur(self, gray: np.ndarray, ksize: int = 3) -> np.ndarray:
        """
        Light Gaussian blur before thresholding, to suppress paper-texture
        and JPEG-compression noise so binarization doesn't pick up speckle
        that would otherwise inflate ink-ratio measurements later.
        """
        blurred = cv2.GaussianBlur(gray, (ksize, ksize), 0)
        self._save("025_blurred", blurred)
        return blurred

    def binarize(self, gray: np.ndarray, block_size: int = 25, c: int = 15) -> np.ndarray:
        """
        Adaptive thresholding (not a single global threshold) because phone
        photos have uneven lighting across the page. Output: ink = white (255),
        background = black (0) -- this polarity makes ink-ratio counting in
        PresenceDetector a simple mean() call.
        """
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, block_size, c
        )
        self._save("03_binarized", binary)
        return binary

    def denoise(self, binary: np.ndarray) -> np.ndarray:
        """Remove small speckle noise (dust, scan artifacts) with a light open."""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        self._save("04_denoised", cleaned)
        return cleaned

    def run(self, path: str) -> dict:
        """Runs the full preprocessing chain: Gray -> Blur -> Threshold -> Denoise."""
        original = self.load(path)
        gray = self.to_grayscale(original)
        blurred = self.blur(gray)
        binary = self.binarize(blurred)
        cleaned = self.denoise(binary)
        return {
            "original": original,
            "gray": gray,
            "blurred": blurred,
            "binary": binary,
            "cleaned": cleaned,
        }
