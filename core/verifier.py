"""
core/verifier.py

SignatureVerifier: compares a student's signature crops across multiple
sheets to flag likely mismatches (coursework requirement IV -- stretch
goal for higher marks). Uses ORB (Oriented FAST and Rotated BRIEF) feature
matching, which is scale/rotation tolerant and doesn't require training
data, unlike a learned model -- appropriate given we only have a handful
of samples per student.
"""

import os

import cv2
import numpy as np


class SignatureVerifier:
    def __init__(self, min_match_ratio: float = 0.04):
        """
        Calibrated against the 5 sample sheets: same-student signature pairs
        averaged similarity 0.111, different-student pairs averaged 0.083.
        The gap is real but narrow -- small, thin-stroke signature crops
        give ORB few stable keypoints to work with. Treat flagged pairs as
        "worth a human look", not a definitive forgery verdict; this is an
        honest limitation to state in the report rather than a bug to hide.
        """
        self.orb = cv2.ORB_create(nfeatures=500)
        self.min_match_ratio = min_match_ratio

    def _prep(self, image_path: str) -> np.ndarray:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(image_path)
        return img

    def compare_pair(self, path_a: str, path_b: str) -> dict:
        img_a, img_b = self._prep(path_a), self._prep(path_b)
        kp_a, des_a = self.orb.detectAndCompute(img_a, None)
        kp_b, des_b = self.orb.detectAndCompute(img_b, None)

        if des_a is None or des_b is None or len(kp_a) < 4 or len(kp_b) < 4:
            return {"similarity": 0.0, "good_matches": 0, "note": "insufficient features detected"}

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des_a, des_b)
        matches = sorted(matches, key=lambda m: m.distance)
        good = [m for m in matches if m.distance < 60]

        denom = min(len(kp_a), len(kp_b))
        similarity = len(good) / denom if denom else 0.0
        return {
            "similarity": round(similarity, 4),
            "good_matches": len(good),
            "total_keypoints": denom,
        }

    def render_match_image(self, path_a: str, path_b: str, output_path: str,
                            max_matches: int = 30) -> str:
        """
        Draws the ORB keypoint matches between two signature crops
        side-by-side (cv2.drawMatches) and saves it to output_path. Lets a
        human see *why* a pair was flagged/OK instead of just the bare
        similarity number compare_pair() returns -- same detect/match logic,
        just visualized rather than reduced to a ratio.
        """
        img_a, img_b = self._prep(path_a), self._prep(path_b)
        kp_a, des_a = self.orb.detectAndCompute(img_a, None)
        kp_b, des_b = self.orb.detectAndCompute(img_b, None)

        good = []
        if des_a is not None and des_b is not None:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = sorted(bf.match(des_a, des_b), key=lambda m: m.distance)
            good = [m for m in matches if m.distance < 60][:max_matches]

        match_img = cv2.drawMatches(
            img_a, kp_a, img_b, kp_b, good, None,
            flags=cv2.DRAW_MATCHES_FLAGS_NOT_DRAW_SINGLE_POINTS,
        )

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        cv2.imwrite(output_path, match_img)
        return output_path

    def verify_student(self, crop_paths: list) -> dict:
        """
        Compares every pair of a student's signature crops. Returns pairwise
        similarity scores and flags any pair below min_match_ratio as a
        possible mismatch worth manual review.
        """
        results = []
        flagged = []
        for i in range(len(crop_paths)):
            for j in range(i + 1, len(crop_paths)):
                cmp = self.compare_pair(crop_paths[i]["signature_crop_path"],
                                         crop_paths[j]["signature_crop_path"])
                pair_result = {
                    "sheet_a": crop_paths[i]["sheet_id"],
                    "sheet_b": crop_paths[j]["sheet_id"],
                    **cmp,
                }
                results.append(pair_result)
                if cmp["similarity"] < self.min_match_ratio:
                    flagged.append(pair_result)
        return {"comparisons": results, "flagged": flagged}
