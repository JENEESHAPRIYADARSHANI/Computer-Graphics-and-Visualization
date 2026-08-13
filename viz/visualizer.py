"""
viz/visualizer.py

AttendanceVisualizer: queries the DB for a student's attendance history and
renders it as a chart (coursework requirement III).
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data.repository import AttendanceRepository


class AttendanceVisualizer:
    def __init__(self, repo: AttendanceRepository):
        self.repo = repo

    def render(self, student_index: str, output_path: str = None) -> str:
        name = self.repo.get_student_name(student_index)
        if name is None:
            raise ValueError(f"No student found with index {student_index}")

        records = self.repo.get_attendance_for_student(student_index)
        if not records:
            raise ValueError(f"No attendance records found for {student_index}")

        sheet_ids = [r["sheet_id"] for r in records]
        present = [r["present"] for r in records]
        ink_ratios = [r["ink_ratio"] for r in records]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

        # left: present/absent bar per sheet
        colors = ["#1D9E75" if p else "#E24B4A" for p in present]
        ax1.bar(sheet_ids, [1] * len(sheet_ids), color=colors)
        ax1.set_ylim(0, 1.2)
        ax1.set_yticks([])
        ax1.set_xlabel("Signing sheet")
        ax1.set_title(f"Attendance record: {name} ({student_index})")
        for i, p in enumerate(present):
            ax1.text(i, 1.05, "Present" if p else "Absent", ha="center", fontsize=9)

        # right: overall summary pie
        present_count = sum(present)
        absent_count = len(present) - present_count
        ax2.pie(
            [present_count, absent_count],
            labels=["Present", "Absent"],
            autopct="%1.0f%%",
            colors=["#1D9E75", "#E24B4A"],
        )
        ax2.set_title(f"Overall: {present_count}/{len(present)} sheets")

        plt.tight_layout()
        output_path = output_path or f"output/infovis_{student_index}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close(fig)
        return output_path
