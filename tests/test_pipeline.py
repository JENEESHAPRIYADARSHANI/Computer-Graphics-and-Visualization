"""
tests/test_pipeline.py

Basic sanity tests for roster parsing and table detection.
Run with: python -m pytest tests/ -v
(or plain: python tests/test_pipeline.py)
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import cv2

from core.table_detection import TableDetector
from core.roster import Roster


SAMPLE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "sample_images"
)


def test_roster_parses_all_students():
    roster = Roster.from_xml(
        os.path.join(SAMPLE_DIR, "info.xml")
    )

    assert len(roster) == 6
    assert roster[0].index == "10000409"


def test_table_detection_finds_six_rows():
    img = cv2.imread(
        os.path.join(SAMPLE_DIR, "1.jpeg")
    )

    det = TableDetector()
    result = det.run(img, expect_rows=6)

    # 6 data rows + header row needs 8 boundary lines
    assert len(result["row_lines"]) == 8


if __name__ == "__main__":
    test_roster_parses_all_students()
    print("test_roster_parses_all_students: PASS")

    test_table_detection_finds_six_rows()
    print("test_table_detection_finds_six_rows: PASS")

    print("\nPart 1 tests passed.")