"""
core/roster.py

Roster: parses info.xml into an ordered list of Student records.

info.xml has no coordinate/geometry information -- it's purely a roster
(index + name), matching the figure in the coursework brief. Students are
matched to detected table rows by ORDER: the Nth <student> in info.xml is
assumed to correspond to the Nth row of the signing sheet. This mirrors how
the real sheets are laid out (No. 1-6 in a fixed printed order).
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Student:
    index: str
    name: str


class Roster:
    def __init__(self, students: list):
        self.students = students

    @classmethod
    def from_xml(cls, path: str) -> "Roster":
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            # The coursework brief's own info.xml example uses numeric tags
            # like <15> for a batch number, which is invalid XML (tag names
            # can't start with a digit). If the real file was authored the
            # same way, repair it by prefixing numeric-only tags before
            # parsing, rather than failing outright.
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            repaired = re.sub(r"<(/?)(\d[\w-]*)>", r"<\1batch_\2>", raw)
            root = ET.fromstring(repaired)
            tree = None
        if tree is not None:
            root = tree.getroot()
        students = []
        for student_el in root.iter("student"):
            index = student_el.findtext("index", default="").strip()
            name = student_el.findtext("name", default="").strip()
            students.append(Student(index=index, name=name))
        if not students:
            raise ValueError(f"No <student> entries found in {path}")
        return cls(students)

    def __len__(self):
        return len(self.students)

    def __getitem__(self, i):
        return self.students[i]

    def match_to_rows(self, row_results: list) -> list:
        """
        row_results: list of dicts (one per detected table row, in row order)
        e.g. [{"present": True, "ink_ratio": 0.15}, ...]
        Returns a list of merged dicts, one per student, combining roster
        identity with detection result. Raises if counts don't match, since
        a mismatch means a row was mis-detected and should be checked
        manually rather than silently misattributed.
        """
        if len(row_results) != len(self.students):
            raise ValueError(
                f"Row count ({len(row_results)}) does not match roster size "
                f"({len(self.students)}) -- check table detection before trusting results."
            )
        merged = []
        for student, result in zip(self.students, row_results):
            merged.append({
                "index": student.index,
                "name": student.name,
                **result,
            })
        return merged
