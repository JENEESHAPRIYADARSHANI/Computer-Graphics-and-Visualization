"""
tests/test_pipeline.py

Basic sanity tests. Run with: python -m pytest tests/ -v
(or plain: python tests/test_pipeline.py)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
from core.table_detection import TableDetector
from core.extraction import SignatureCellExtractor
from core.detection import PresenceDetector
from core.roster import Roster

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_images")


def test_roster_parses_all_students():
    roster = Roster.from_xml(os.path.join(SAMPLE_DIR, "info.xml"))
    assert len(roster) == 6
    assert roster[0].index == "10000409"


def test_table_detection_finds_six_rows():
    img = cv2.imread(os.path.join(SAMPLE_DIR, "1.jpeg"))
    det = TableDetector()
    result = det.run(img, expect_rows=6)
    # 6 data rows + header row needs 8 boundary lines
    assert len(result["row_lines"]) == 8


def test_known_blank_cells_detected_as_absent():
    # sheet 3 in this project has confirmed-blank rows 2 and 3
    img = cv2.imread(os.path.join(SAMPLE_DIR, "3.jpeg"))
    det = TableDetector()
    ext = SignatureCellExtractor()
    pres = PresenceDetector()

    result = det.run(img, expect_rows=6)
    cells = ext.extract_cells(result["deskewed_image"], result["row_lines"],
                               result["signature_col"], line_mask=result["line_mask"])
    outcomes = [pres.is_present(c, m) for c, m in cells]

    assert outcomes[1]["present"] is False, "row 2 should be detected absent"
    assert outcomes[2]["present"] is False, "row 3 should be detected absent"
    assert outcomes[0]["present"] is True, "row 1 should be detected present"


def test_perspective_correction_produces_consistent_table_size():
    # all 5 sheets are photos of the same printed template, so after
    # perspective correction the warped table dimensions should be
    # consistent (within photo-quality tolerance), regardless of each
    # photo's original rotation/tilt/distance
    det = TableDetector()
    widths = []
    for fname in ("1.jpeg", "2.jpeg", "3.jpeg", "4.jpeg", "5.jpeg"):
        img = cv2.imread(os.path.join(SAMPLE_DIR, fname))
        warped = det.perspective_correct(img)
        widths.append(warped.shape[1])
    assert max(widths) - min(widths) < 300, f"warped widths vary too much: {widths}"


if __name__ == "__main__":
    test_roster_parses_all_students()
    print("test_roster_parses_all_students: PASS")
    test_table_detection_finds_six_rows()
    print("test_table_detection_finds_six_rows: PASS")
    test_known_blank_cells_detected_as_absent()
    print("test_known_blank_cells_detected_as_absent: PASS")
    test_perspective_correction_produces_consistent_table_size()
    print("test_perspective_correction_produces_consistent_table_size: PASS")
    print("\nAll tests passed.")
