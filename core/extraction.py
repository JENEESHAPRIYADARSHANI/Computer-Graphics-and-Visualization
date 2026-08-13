"""
core/extraction.py

SignatureCellExtractor: crops the individual signature cell for each of the
6 student rows out of the deskewed image, using the row lines and signature
column boundaries found by TableDetector.
"""

import os
import cv2
import numpy as np


class SignatureCellExtractor:
    def __init__(self, snapshot_dir: str = None, pad: int = 4):
        self.snapshot_dir = snapshot_dir
        self.pad = pad
        if self.snapshot_dir:
            os.makedirs(self.snapshot_dir, exist_ok=True)

    def extract_cells(self, deskewed_image: np.ndarray, row_lines: list, signature_col: tuple,
                       line_mask: np.ndarray = None) -> list:
        """
        row_lines: list of y-coordinates, length = num_rows + 1 (first is the
                   header row's top, so student row i is between
                   row_lines[i+1] and row_lines[i+2]).
        line_mask: optional table-line mask (same size as deskewed_image,
                   single channel) from TableDetector.build_line_removal_mask.
                   When given, each cell's matching mask region is cropped
                   alongside the image so PresenceDetector can subtract
                   leaked grid-line pixels before counting ink.
        Returns a list of (cell_image, cell_line_mask) tuples, one per
        student row, in order. cell_line_mask is None if no mask was given.
        """
        left, right = signature_col
        cells = []
        for i in range(1, len(row_lines) - 1):
            top = row_lines[i] + self.pad
            bottom = row_lines[i + 1] - self.pad
            cell = deskewed_image[top:bottom, left + self.pad:right - self.pad]
            mask_cell = None
            if line_mask is not None:
                mask_cell = line_mask[top:bottom, left + self.pad:right - self.pad]
            cells.append((cell, mask_cell))
            if self.snapshot_dir:
                cv2.imwrite(os.path.join(self.snapshot_dir, f"row{i}_signature_cell.jpg"), cell)
        return cells
