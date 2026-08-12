#!/usr/bin/env python3
"""
api.py -- HTTP API for the Student Attendance Management System web frontend.

Wraps the exact same classes used by sams.py / infovis.py / investigate.py
(SamsPipeline, AttendanceRepository, AttendanceVisualizer,
SignatureVerifier) so the web app and the CLI tools stay in sync -- no
processing/storage logic is duplicated here, only an HTTP boundary in front
of it (the browser can't call Python classes in-process, so request
handlers make the same calls a desktop app would).

Run with: python -m uvicorn api:app --reload --port 8010
"""

import os
import shutil
import threading
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.roster import Roster
from data.repository import AttendanceRepository
from sams import SamsPipeline
from viz.visualizer import AttendanceVisualizer
from core.verifier import SignatureVerifier

UPLOAD_DIR = "uploads"
DEFAULT_XML = os.path.join("sample_images", "info.xml")
FRONTEND_DIST = os.path.join("frontend", "dist")

app = FastAPI(title="SAMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory job store for the "process sheet" background pipeline run;
# the frontend polls this instead of a desktop app's worker-thread queue.
_jobs = {}
_jobs_lock = threading.Lock()


def _safe_id(value: str, label: str) -> str:
    """Rejects path-traversal-shaped ids before they're used to build a
    filesystem path (sheet_id / job_id both end up in rmtree() calls)."""
    if not value or value in (".", "..") or "/" in value or "\\" in value:
        raise HTTPException(400, f"Invalid {label}: {value!r}")
    return value


def _run_pipeline_job(job_id: str, image_path: str, xml_path: str, db_path: str):
    job = _jobs[job_id]
    try:
        roster = Roster.from_xml(xml_path)
        pipeline = SamsPipeline(db_path=db_path, output_dir="output")

        original_log = pipeline._log

        def job_log(msg):
            original_log(msg)
            with _jobs_lock:
                job["log"].append(msg)

        pipeline._log = job_log
        records = pipeline.process_sheet(image_path, roster)
        with _jobs_lock:
            job["status"] = "done"
            job["records"] = [
                {
                    "student_index": r.student_index,
                    "student_name": r.student_name,
                    "sheet_id": r.sheet_id,
                    "present": r.present,
                    "ink_ratio": r.ink_ratio,
                }
                for r in records
            ]
    except Exception as e:
        with _jobs_lock:
            job["status"] = "error"
            job["error"] = str(e)


@app.post("/api/process")
async def process_sheet(
    image: UploadFile = File(...),
    xml: UploadFile | None = File(None),
    db_path: str = Form("attendance.db"),
):
    job_id = uuid.uuid4().hex
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    image_path = os.path.join(job_dir, os.path.basename(image.filename))
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    if xml is not None and xml.filename:
        xml_path = os.path.join(job_dir, os.path.basename(xml.filename))
        with open(xml_path, "wb") as f:
            shutil.copyfileobj(xml.file, f)
    else:
        if not os.path.exists(DEFAULT_XML):
            raise HTTPException(400, "No info.xml uploaded and no default roster found.")
        xml_path = DEFAULT_XML

    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "log": [], "records": [], "error": None}

    thread = threading.Thread(
        target=_run_pipeline_job, args=(job_id, image_path, xml_path, db_path), daemon=True
    )
    thread.start()
    return {"job_id": job_id}


@app.get("/api/process/{job_id}")
async def process_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Unknown job id")
        return dict(job)


@app.delete("/api/sheet/{sheet_id}")
async def delete_sheet(sheet_id: str, db: str = "attendance.db", job_id: str | None = None):
    """
    Undoes processing a sheet: removes its attendance/reference-signature
    rows from the DB, its processing snapshots + signature crops
    (output/<sheet_id>/), and -- if the job that produced it is known --
    the originally uploaded image/xml (uploads/<job_id>/).
    """
    sheet_id = _safe_id(sheet_id, "sheet_id")

    repo = AttendanceRepository(db)
    repo.delete_sheet(sheet_id)
    repo.close()

    snap_dir = os.path.join("output", sheet_id)
    if os.path.isdir(snap_dir):
        shutil.rmtree(snap_dir, ignore_errors=True)

    if job_id:
        job_id = _safe_id(job_id, "job_id")
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        if os.path.isdir(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)
        with _jobs_lock:
            _jobs.pop(job_id, None)

    return {"status": "deleted", "sheet_id": sheet_id}


def _clear_dir_contents(path: str):
    """Removes everything inside a directory but keeps the directory itself
    (SamsPipeline/uploads code assumes it exists)."""
    if not os.path.isdir(path):
        return
    for entry in os.listdir(path):
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
        else:
            os.remove(full)


@app.delete("/api/reset")
async def reset_all(db: str = "attendance.db"):
    """
    Full reset for the "Clear" button: wipes every table in the db back to
    empty (AttendanceRepository.delete_all), deletes every uploaded file
    (uploads/), and every processing snapshot / chart / match-image the
    pipeline has ever generated (output/) -- not just the most recently
    processed sheet. All of it is regenerable by reprocessing the source
    images, so this is safe to treat as disposable cache + a DB reset.
    """
    repo = AttendanceRepository(db)
    repo.delete_all()
    repo.close()

    _clear_dir_contents(UPLOAD_DIR)
    _clear_dir_contents("output")

    with _jobs_lock:
        _jobs.clear()

    return {"status": "reset"}


@app.get("/api/students")
async def list_students(db: str = "attendance.db"):
    repo = AttendanceRepository(db)
    rows = repo.conn.execute(
        "SELECT student_index, name FROM students ORDER BY student_index"
    ).fetchall()
    repo.close()
    return [{"student_index": r["student_index"], "name": r["name"]} for r in rows]


@app.get("/api/overview")
async def overview(db: str = "attendance.db"):
    repo = AttendanceRepository(db)
    sheet_rows = repo.conn.execute(
        "SELECT DISTINCT sheet_id FROM sheets ORDER BY processed_at"
    ).fetchall()
    sheet_ids = [r["sheet_id"] for r in sheet_rows]

    students = repo.conn.execute(
        "SELECT student_index, name FROM students ORDER BY student_index"
    ).fetchall()

    result = []
    for s in students:
        records = repo.conn.execute(
            "SELECT sheet_id, present FROM attendance_records WHERE student_index = ?",
            (s["student_index"],),
        ).fetchall()
        status_by_sheet = {r["sheet_id"]: bool(r["present"]) for r in records}
        result.append({
            "student_index": s["student_index"],
            "name": s["name"],
            "status_by_sheet": {sid: status_by_sheet.get(sid) for sid in sheet_ids if sid in status_by_sheet},
        })
    repo.close()
    return {"sheet_ids": sheet_ids, "students": result}


@app.get("/api/chart/{student_index}")
async def chart(student_index: str, db: str = "attendance.db"):
    try:
        repo = AttendanceRepository(db)
        viz = AttendanceVisualizer(repo)
        out_path = os.path.join("output", f"infovis_{student_index}.png")
        viz.render(student_index, output_path=out_path)
        repo.close()
        return FileResponse(out_path, media_type="image/png")
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/investigate/{student_index}")
async def investigate(student_index: str, db: str = "attendance.db"):
    repo = AttendanceRepository(db)
    name = repo.get_student_name(student_index)
    if name is None:
        repo.close()
        raise HTTPException(404, f"No student found with index {student_index}")

    crops = repo.get_signature_crops_for_student(student_index)
    if len(crops) < 2:
        repo.close()
        return {"comparisons": [], "flagged": [], "note": "need_more_sheets", "signed_sheet_count": len(crops)}

    verifier = SignatureVerifier()
    result = verifier.verify_student(crops)
    repo.close()
    return {
        "comparisons": result["comparisons"],
        "flagged": result["flagged"],
        "note": None,
        "signed_sheet_count": len(crops),
    }


@app.get("/api/investigate/{student_index}/match-image")
async def investigate_match_image(student_index: str, sheet_a: str, sheet_b: str, db: str = "attendance.db"):
    repo = AttendanceRepository(db)
    crops = repo.get_signature_crops_for_student(student_index)
    repo.close()

    path_a = next((c["signature_crop_path"] for c in crops if c["sheet_id"] == sheet_a), None)
    path_b = next((c["signature_crop_path"] for c in crops if c["sheet_id"] == sheet_b), None)
    if path_a is None or path_b is None:
        raise HTTPException(404, f"No signed crop found for sheet {sheet_a!r} or {sheet_b!r}")

    out_path = os.path.join("output", f"match_{student_index}_{sheet_a}_vs_{sheet_b}.png")
    verifier = SignatureVerifier()
    verifier.render_match_image(path_a, path_b, out_path)
    return FileResponse(out_path, media_type="image/png")


# Serve the built React app (frontend/dist) if present, so the whole thing
# can run as a single `uvicorn api:app` process in addition to the Vite dev
# server used during frontend development.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
