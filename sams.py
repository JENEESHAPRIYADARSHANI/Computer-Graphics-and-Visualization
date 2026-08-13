#!/usr/bin/env python3
"""
sams.py -- Student Attendance Management System

Usage:
    python sams.py <sheet_image> <info.xml> [--db attendance.db] [--out output/]

Runs the full pipeline: deskew -> locate table -> split rows -> extract
signature cells -> detect presence -> match to roster -> store in DB.
Prints progress at each stage (coursework requirement II).
"""

import argparse
import os
import sys
import cv2

from core.preprocessing import ImagePreprocessor
from core.table_detection import TableDetector
from core.extraction import SignatureCellExtractor
from core.detection import PresenceDetector
from core.roster import Roster
from data.repository import AttendanceRepository
from data.models import AttendanceRecord


class SamsPipeline:
    def __init__(self, db_path: str = "attendance.db", output_dir: str = "output"):
        self.output_dir = output_dir
        self.repo = AttendanceRepository(db_path)
        self.presence_detector = PresenceDetector()

    def _log(self, msg: str):
        print(f"[sams] {msg}")

    def process_sheet(self, image_path: str, roster: Roster) -> list:
        sheet_id = os.path.splitext(os.path.basename(image_path))[0]
        snap_dir = os.path.join(self.output_dir, sheet_id)
        self.repo.upsert_sheet(sheet_id, image_path)

        self._log(f"Processing sheet '{sheet_id}' ({image_path})")

        self._log("Stage 1/7: loading image + greyscale + blur + binarization...")
        pre = ImagePreprocessor(snapshot_dir=snap_dir)
        pre.run(image_path)

        self._log("Stage 2/7: perspective correction (4-corner homography)...")
        det = TableDetector(snapshot_dir=snap_dir)
        raw_image = cv2.imread(image_path)

        self._log("Stage 3/7: table line detection (projection histogram + Hough)...")
        result = det.run(raw_image, expect_rows=len(roster))
        self._log(f"  -> {len(result['row_lines'])} row lines found, "
                   f"{result['hough_line_count']} Hough line segments detected")

        self._log("Stage 4/7: removing table lines from detected grid...")
        # (line_mask already built inside det.run(); used below during extraction)

        self._log("Stage 5/7: extracting signature cells...")
        ext = SignatureCellExtractor(snapshot_dir=snap_dir)
        cells = ext.extract_cells(result["deskewed_image"], result["row_lines"],
                                   result["signature_col"], line_mask=result["line_mask"])
        self._log(f"  -> extracted {len(cells)} cell(s)")

        self._log("Stage 6/7: detecting ink presence per cell...")
        row_results = []
        for i, (cell, cell_mask) in enumerate(cells):
            outcome = self.presence_detector.is_present(cell, cell_mask)
            row_results.append(outcome)
            status = "PRESENT" if outcome["present"] else "absent "
            self._log(f"  row {i+1}: {status}  (ink_ratio={outcome['ink_ratio']:.4f})")

        self._log("Stage 7/7: reading info.xml, matching rows to roster, storing in DB...")
        merged = roster.match_to_rows(row_results)
        records = []
        for i, m in enumerate(merged):
            crop_path = os.path.join(snap_dir, f"row{i+1}_signature_cell.jpg")
            record = AttendanceRecord(
                student_index=m["index"],
                student_name=m["name"],
                sheet_id=sheet_id,
                present=m["present"],
                ink_ratio=m["ink_ratio"],
                signature_crop_path=crop_path if os.path.exists(crop_path) else None,
            )
            self.repo.save_record(record)
            if record.present and record.signature_crop_path:
                self.repo.save_reference_signature(record.student_index, record.signature_crop_path, sheet_id)
            records.append(record)

        present_count = sum(1 for r in records if r.present)
        self._log(f"Done. {present_count}/{len(records)} present on sheet '{sheet_id}'.")
        return records


def main():
    parser = argparse.ArgumentParser(description="Process a signing sheet and update attendance DB.")
    parser.add_argument("image", help="Path to the signing sheet image (.png/.jpg)")
    parser.add_argument("info_xml", help="Path to info.xml roster file")
    parser.add_argument("--db", default="attendance.db", help="SQLite DB path")
    parser.add_argument("--out", default="output", help="Directory for processing snapshots")
    args = parser.parse_args()

    roster = Roster.from_xml(args.info_xml)
    pipeline = SamsPipeline(db_path=args.db, output_dir=args.out)
    pipeline.process_sheet(args.image, roster)


if __name__ == "__main__":
    main()
