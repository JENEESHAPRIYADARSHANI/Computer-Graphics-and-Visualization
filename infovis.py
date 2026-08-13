#!/usr/bin/env python3
"""
infovis.py -- show a summary of attendance for a given student.

Usage:
    python infovis.py <student_index> [--db attendance.db] [--out output/]
"""

import argparse
from data.repository import AttendanceRepository
from viz.visualizer import AttendanceVisualizer


def main():
    parser = argparse.ArgumentParser(description="Visualize attendance for a student.")
    parser.add_argument("student_index", help="Student index, e.g. 10009301")
    parser.add_argument("--db", default="attendance.db", help="SQLite DB path")
    parser.add_argument("--out", default=None, help="Output PNG path")
    args = parser.parse_args()

    repo = AttendanceRepository(args.db)
    viz = AttendanceVisualizer(repo)
    path = viz.render(args.student_index, output_path=args.out)
    print(f"[infovis] Saved chart to {path}")


if __name__ == "__main__":
    main()
