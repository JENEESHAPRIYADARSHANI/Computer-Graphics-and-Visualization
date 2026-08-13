"""
core/table_detection.py

TableDetector: finds the signing-sheet table inside a raw phone photo and
straightens it, following this pipeline (matches the approved architecture
diagram):

"""

import os
import cv2
import numpy as np


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype="float32")


class TableDetector:
    def __init__(self, snapshot_dir: str = None, work_width: int = 1000):
        self.snapshot_dir = snapshot_dir
        self.work_width = work_width
        if self.snapshot_dir:
            os.makedirs(self.snapshot_dir, exist_ok=True)

    def _save(self, name, image):
        if self.snapshot_dir:
            cv2.imwrite(os.path.join(self.snapshot_dir, f"{name}.jpg"), image)

    # ---------- grid line masks (shared by corner-finding and line detection) ----------

    def _grid_masks(self, gray: np.ndarray):
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                        cv2.THRESH_BINARY_INV, 25, 15)
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1))
        horiz = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horiz_kernel, iterations=1)
        horiz = cv2.dilate(horiz, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3)), iterations=2)

        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 35))
        vert = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vert_kernel, iterations=1)
        vert = cv2.dilate(vert, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15)), iterations=2)
        return horiz, vert

    def _find_table_contour(self, gray: np.ndarray):
        horiz, vert = self._grid_masks(gray)
        grid = cv2.add(horiz, vert)
        contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise RuntimeError("No table grid detected in image.")
        return max(contours, key=cv2.contourArea), grid

    def _find_quad_corners(self, contour) -> np.ndarray:
        """
        Reduces the table's outer contour to 4 corner points. Tries
        approxPolyDP at increasing tolerance first (handles a genuinely
        skewed/perspective quadrilateral); falls back to extreme-point
        picking on the convex hull if the contour is too noisy to settle
        on exactly 4 points.
        """
        hull = cv2.convexHull(contour)
        peri = cv2.arcLength(hull, True)
        for frac in (0.02, 0.03, 0.05, 0.08, 0.12):
            approx = cv2.approxPolyDP(hull, frac * peri, True)
            if len(approx) == 4:
                return order_corners(approx)

        pts = hull.reshape(-1, 2)
        s = pts.sum(axis=1)
        diff = pts[:, 0] - pts[:, 1]
        tl = pts[np.argmin(s)]
        br = pts[np.argmax(s)]
        tr = pts[np.argmax(diff)]
        bl = pts[np.argmin(diff)]
        return order_corners(np.array([tl, tr, br, bl]))

    # ---------- Stage A: perspective correction ----------

    def perspective_correct(self, image: np.ndarray) -> np.ndarray:
        """
        Finds the table's 4 corners and warps them to a flat rectangle with
        a full perspective transform (cv2.getPerspectiveTransform +
        warpPerspective). This corrects both in-plane rotation and
        keystone/perspective distortion in one step -- a plain rotation fix
        only handles the first of those.
        """
        scale = self.work_width / image.shape[1]
        small = cv2.resize(image, (self.work_width, int(image.shape[0] * scale)))
        gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        contour, grid_mask = self._find_table_contour(gray_small)
        self._save("11_grid_mask", grid_mask)
        corners_small = self._find_quad_corners(contour)

        debug = small.copy()
        cv2.polylines(debug, [corners_small.astype(int)], True, (0, 0, 255), 2)
        for p in corners_small:
            cv2.circle(debug, tuple(p.astype(int)), 5, (0, 255, 0), -1)
        self._save("12_corners_detected", debug)

        corners_full = corners_small / scale
        (tl, tr, br, bl) = corners_full

        width_top = np.linalg.norm(tr - tl)
        width_bottom = np.linalg.norm(br - bl)
        height_left = np.linalg.norm(bl - tl)
        height_right = np.linalg.norm(br - tr)
        dst_w = int(max(width_top, width_bottom))
        dst_h = int(max(height_left, height_right))

        dst_pts = np.array([[0, 0], [dst_w - 1, 0], [dst_w - 1, dst_h - 1], [0, dst_h - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(corners_full, dst_pts)
        warped = cv2.warpPerspective(image, M, (dst_w, dst_h), borderValue=(255, 255, 255))
        self._save("13_perspective_corrected", warped)
        return warped

    # ---------- Stage B: table line detection (projection histogram + Hough) ----------

    def _line_positions(self, profile: np.ndarray, min_gap: int) -> list:
        threshold = profile.max() * 0.5
        candidates = np.where(profile > threshold)[0]
        if len(candidates) == 0:
            return []
        lines = []
        group = [candidates[0]]
        for c in candidates[1:]:
            if c - group[-1] <= min_gap:
                group.append(c)
            else:
                lines.append(int(np.mean(group)))
                group = [c]
        lines.append(int(np.mean(group)))
        return lines

    def _thin_line_masks(self, gray: np.ndarray, vert_len_frac: float = 0.5):
        """
        Undilated version of the line masks, used where line THICKNESS
        matters (removal, and precise peak positions) rather than just
        connectivity for contour-finding. _grid_masks() above is
        deliberately fattened so the whole table forms one connected
        blob for corner detection; reusing that fattened mask to subtract
        lines out of a signature cell would eat real ink along with the
        border, so this keeps a separate, tight version.

        vert_len_frac matters a lot here: on the warped (table-only)
        image, a printed column border spans the table's FULL height,
        while a single signature's vertical stroke is confined to one
        ~90px-tall row. A short vertical open kernel (e.g. 35px, fine on
        the downscaled whole-photo image used for corner-finding) is
        nowhere near long enough to tell those apart on this image scale
        -- cursive flourishes were being misdetected as column borders
        until this was tied to the image's actual height.
        """
        h, w = gray.shape
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                        cv2.THRESH_BINARY_INV, 25, 15)

        # close small gaps (faded ink, lighting, JPEG artifacts) BEFORE the
        # length-based open -- otherwise a real printed line with even a
        # few broken pixels gets erased entirely by the long open kernel,
        # since erosion (open's first step) can't tell "genuinely short"
        # from "long but interrupted".
        thresh_h = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1)))
        thresh_v = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 9)))

        horiz = cv2.morphologyEx(thresh_h, cv2.MORPH_OPEN,
                                  cv2.getStructuringElement(cv2.MORPH_RECT, (max(35, int(w * 0.3)), 1)), iterations=1)
        vert = cv2.morphologyEx(thresh_v, cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(35, int(h * vert_len_frac)))), iterations=1)
        return horiz, vert

    def detect_grid_lines(self, warped_image: np.ndarray, expect_rows: int = 6) -> dict:
        """
        Row lines: found first, from the dilated/connected masks
        (_grid_masks) across the full warped image -- position-finding
        needs broken line segments merged into one continuous peak.

        Column lines: the header sub-table (Date/Lecturer's Name/Signatue)
        sits above the main student table with a DIFFERENT column layout,
        so no single vertical line spans the whole warped image -- a
        length-based filter has to be scoped to the main table's own
        height, not the full image. Column detection is therefore done
        only within the main table's y-range (found from the row lines
        just above), and requires a run length long enough that no single
        student's signature flourish (confined to one ~90px row) can be
        mistaken for a printed border spanning the whole table.

        Cross-checked with a Hough transform pass (the architecture
        diagram's alternative technique) purely as a sanity signal on how
        many straight edges the image contains.
        """
        gray = cv2.cvtColor(warped_image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        horiz_thick, _ = self._grid_masks(gray)
        row_profile = horiz_thick.sum(axis=1)
        row_lines_all = self._line_positions(row_profile, min_gap=int(0.02 * h))
        needed = expect_rows + 2
        row_lines = row_lines_all[-needed:] if len(row_lines_all) >= needed else row_lines_all

        table_top, table_bottom = row_lines[0], row_lines[-1]
        header_top, header_bottom = row_lines[0], row_lines[1]
        # Column borders are found ONLY within the header row band (No |
        # Student No | Title | Student Name | Signature). That band is
        # guaranteed free of student ink -- no signature can appear there
        # -- so any vertical run spanning it is unambiguously a printed
        # border, with none of the "does this line span the whole table"
        # continuity problems that come from the header sub-table having a
        # different column layout, or a real column border having a few
        # broken/faded pixels somewhere across a much longer span.
        gray_header = gray[header_top:header_bottom, :]
        _, thin_vert = self._thin_line_masks(gray_header, vert_len_frac=0.6)
        col_profile = thin_vert.sum(axis=0)
        col_lines = self._line_positions(col_profile, min_gap=int(0.03 * w))

        edges = cv2.Canny(gray, 50, 150)
        hough_lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=100,
                                       minLineLength=int(0.3 * w), maxLineGap=10)
        hough_line_count = 0 if hough_lines is None else len(hough_lines)

        return {
            "row_lines": row_lines,
            "col_lines": col_lines,
            "hough_line_count": hough_line_count,
        }

    def build_line_removal_mask(self, warped_shape: tuple, row_lines: list, col_lines: list, thickness: int = 5) -> np.ndarray:
        """
        Stage: 'remove table lines'. Draws a mask directly at the same
        row_lines/col_lines coordinates already used for cropping cells,
        rather than re-detecting lines independently -- an independent
        second detection pass (tried first) doesn't pixel-align with the
        coordinates extraction actually crops at, since different
        morphological kernels shift a detected line's effective center by
        a few pixels. Drawing from the same coordinates guarantees the
        removal mask lines up with what gets cropped.
        """
        h, w = warped_shape[0], warped_shape[1]
        mask = np.zeros((h, w), dtype=np.uint8)
        half = thickness // 2
        for y in row_lines:
            cv2.line(mask, (0, y), (w, y), 255, thickness)
        if col_lines:
            top, bottom = row_lines[0], row_lines[-1]
            for x in col_lines:
                cv2.line(mask, (x, top), (x, bottom), 255, thickness)
        self._save("14_table_lines_mask", mask)
        return mask

    # ---------- orchestration ----------

    def run(self, image: np.ndarray, expect_rows: int = 6) -> dict:
        warped = self.perspective_correct(image)
        grid = self.detect_grid_lines(warped, expect_rows=expect_rows)

        row_lines = grid["row_lines"]
        col_lines = grid["col_lines"]
        if len(col_lines) < 2:
            raise RuntimeError("Could not detect enough column lines.")
        signature_col = (col_lines[-2], col_lines[-1])

        line_mask = self.build_line_removal_mask(warped.shape, row_lines, col_lines)

        return {
            "deskewed_image": warped,
            "row_lines": row_lines,
            "signature_col": signature_col,
            "line_mask": line_mask,
            "hough_line_count": grid["hough_line_count"],
        }
