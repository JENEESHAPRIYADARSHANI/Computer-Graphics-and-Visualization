"""
data/repository.py

AttendanceRepository: the only module that touches SQLite directly. Every
other module works with plain Python objects (AttendanceRecord) and never
writes SQL -- keeps DB concerns in one place, easy to swap or unit-test.
"""

import sqlite3
from .models import AttendanceRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_index TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sheets (
    sheet_id TEXT PRIMARY KEY,
    source_image TEXT,
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_index TEXT NOT NULL,
    sheet_id TEXT NOT NULL,
    present INTEGER NOT NULL,
    ink_ratio REAL,
    signature_crop_path TEXT,
    FOREIGN KEY (student_index) REFERENCES students(student_index),
    FOREIGN KEY (sheet_id) REFERENCES sheets(sheet_id),
    UNIQUE(student_index, sheet_id)
);

CREATE TABLE IF NOT EXISTS reference_signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_index TEXT NOT NULL,
    crop_path TEXT NOT NULL,
    sheet_id TEXT NOT NULL
);
"""


class AttendanceRepository:
    def __init__(self, db_path: str = "attendance.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert_student(self, student_index: str, name: str):
        self.conn.execute(
            "INSERT INTO students (student_index, name) VALUES (?, ?) "
            "ON CONFLICT(student_index) DO UPDATE SET name=excluded.name",
            (student_index, name),
        )

    def upsert_sheet(self, sheet_id: str, source_image: str):
        self.conn.execute(
            "INSERT INTO sheets (sheet_id, source_image) VALUES (?, ?) "
            "ON CONFLICT(sheet_id) DO UPDATE SET source_image=excluded.source_image",
            (sheet_id, source_image),
        )

    def save_record(self, record: AttendanceRecord):
        self.upsert_student(record.student_index, record.student_name)
        self.conn.execute(
            "INSERT INTO attendance_records "
            "(student_index, sheet_id, present, ink_ratio, signature_crop_path) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(student_index, sheet_id) DO UPDATE SET "
            "present=excluded.present, ink_ratio=excluded.ink_ratio, "
            "signature_crop_path=excluded.signature_crop_path",
            (record.student_index, record.sheet_id, int(record.present),
             record.ink_ratio, record.signature_crop_path),
        )
        self.conn.commit()

    def save_reference_signature(self, student_index: str, crop_path: str, sheet_id: str):
        self.conn.execute(
            "INSERT INTO reference_signatures (student_index, crop_path, sheet_id) "
            "VALUES (?, ?, ?)",
            (student_index, crop_path, sheet_id),
        )
        self.conn.commit()

    def get_attendance_for_student(self, student_index: str) -> list:
        rows = self.conn.execute(
            "SELECT ar.*, s.sheet_id, s.source_image FROM attendance_records ar "
            "JOIN sheets s ON ar.sheet_id = s.sheet_id "
            "WHERE ar.student_index = ? ORDER BY s.processed_at",
            (student_index,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_student_name(self, student_index: str) -> str:
        row = self.conn.execute(
            "SELECT name FROM students WHERE student_index = ?", (student_index,)
        ).fetchone()
        return row["name"] if row else None

    def get_signature_crops_for_student(self, student_index: str) -> list:
        rows = self.conn.execute(
            "SELECT signature_crop_path, sheet_id FROM attendance_records "
            "WHERE student_index = ? AND present = 1 AND signature_crop_path IS NOT NULL",
            (student_index,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_sheet(self, sheet_id: str):
        """
        Removes a sheet and everything it produced: its attendance records,
        any reference signatures pulled from it, and the sheets row itself.
        Students aren't deleted -- they may still have records from other
        sheets.
        """
        self.conn.execute("DELETE FROM attendance_records WHERE sheet_id = ?", (sheet_id,))
        self.conn.execute("DELETE FROM reference_signatures WHERE sheet_id = ?", (sheet_id,))
        self.conn.execute("DELETE FROM sheets WHERE sheet_id = ?", (sheet_id,))
        self.conn.commit()

    def delete_all(self):
        """
        Full reset: wipes every table back to empty. Used by the web UI's
        "Clear" action, which undoes everything ever uploaded/processed
        into this db, not just the most recently processed sheet.
        """
        self.conn.execute("DELETE FROM attendance_records")
        self.conn.execute("DELETE FROM reference_signatures")
        self.conn.execute("DELETE FROM sheets")
        self.conn.execute("DELETE FROM students")
        self.conn.commit()

    def close(self):
        self.conn.close()
