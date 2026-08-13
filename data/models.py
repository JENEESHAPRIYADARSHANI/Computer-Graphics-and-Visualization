"""data/models.py -- plain data classes for what gets stored in the DB."""

from dataclasses import dataclass


@dataclass
class AttendanceRecord:
    student_index: str
    student_name: str
    sheet_id: str
    present: bool
    ink_ratio: float
    signature_crop_path: str = None
