#!/usr/bin/env python3
"""
investigate.py -- compare a student's signatures across all processed
sheets and report any that don't match well (coursework requirement IV).

Usage:
    python investigate.py <student_index> [--db attendance.db]
"""

import argparse
from data.repository import AttendanceRepository
from core.verifier import SignatureVerifier


def main():
    parser = argparse.ArgumentParser(description="Verify signature consistency for a student.")
    parser.add_argument("student_index", help="Student index, e.g. 10009301")
    parser.add_argument("--db", default="attendance.db", help="SQLite DB path")
    args = parser.parse_args()

    repo = AttendanceRepository(args.db)
    name = repo.get_student_name(args.student_index)
    if name is None:
        print(f"[investigate] No student found with index {args.student_index}")
        return

    crops = repo.get_signature_crops_for_student(args.student_index)
    print(f"[investigate] {name} ({args.student_index}): {len(crops)} signed sheet(s) found")

    if len(crops) < 2:
        print("[investigate] Need at least 2 signed sheets to compare. Nothing to do.")
        return

    verifier = SignatureVerifier()
    result = verifier.verify_student(crops)

    print("\nPairwise comparisons:")
    for c in result["comparisons"]:
        print(f"  sheet {c['sheet_a']} vs sheet {c['sheet_b']}: "
              f"similarity={c['similarity']:.3f}  good_matches={c.get('good_matches', 0)}")

    if result["flagged"]:
        print(f"\n[investigate] {len(result['flagged'])} pair(s) flagged as possible mismatch:")
        for f in result["flagged"]:
            print(f"  -> sheet {f['sheet_a']} vs sheet {f['sheet_b']} (similarity={f['similarity']:.3f})")
    else:
        print("\n[investigate] No mismatches flagged -- signatures appear consistent.")


if __name__ == "__main__":
    main()
