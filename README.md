# SAMS — Student Attendance Management System

> **CS402.3 — Computer Graphics and Visualization Coursework**

<p align="center">
  <strong>Computer Vision-Based Attendance Detection from Handwritten Signing Sheets</strong>
</p>

<p align="center">
  <em>Detect • Process • Verify • Visualize • Store</em>
</p>

---

## 📌 Overview

**SAMS (Student Attendance Management System)** is a computer-vision-based attendance system that automatically identifies student attendance from photographs of handwritten paper signing sheets.

The system takes a **phone-captured attendance sheet** together with an `info.xml` student roster, detects which students have signed, stores the results in a local SQLite database, and provides a web interface for viewing attendance records and investigating signature consistency.

Unlike systems that depend on fixed pixel coordinates, SAMS dynamically detects the table structure from every image. This allows the system to handle variations in **position, rotation, scale, and perspective** caused by handheld photographs.

---

## ✨ Key Features

| Feature                          | Description                                              |
| -------------------------------- | -------------------------------------------------------- |
| 📷 **Sheet Processing**          | Process photographed paper attendance sheets             |
| 🔍 **Automatic Table Detection** | Detect table geometry without hardcoded coordinates      |
| 📐 **Perspective Correction**    | Correct rotation and camera perspective using homography |
| ✍️ **Signature Detection**       | Detect signed/unsigned cells using ink-density analysis  |
| 🧹 **Grid-Line Removal**         | Remove table-line artifacts before signature analysis    |
| 👨‍🎓 **Roster Matching**           | Match attendance rows with students from `info.xml`      |
| 💾 **SQLite Storage**            | Persist attendance records locally                       |
| 📊 **Attendance Visualization**  | Generate student attendance charts                       |
| 🔎 **Signature Verification**    | Compare signatures using ORB features                    |
| 🖼️ **Visual Match Inspection**   | View actual ORB keypoint matches                         |
| 🌐 **Web Interface**             | React + FastAPI browser-based application                |
| 🧪 **Pipeline Testing**          | Validate processing against sample sheets                |

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │  Attendance Sheet    │
                    │   Phone Photograph   │
                    └──────────┬───────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │   Perspective Correction  │
                 │   4-Corner Homography     │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │     Image Preprocessing   │
                 │ Gray → Blur → Threshold   │
                 │          → Denoise        │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │     Table Detection       │
                 │ Projection + Hough Lines  │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │   Signature Cell Cropping │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │   Local Grid-Line Removal │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │    Presence Detection     │
                 │      Ink-Ratio Analysis   │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │      info.xml Matching    │
                 │     Student ID + Name     │
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │       SQLite Database     │
                 └─────────────┬─────────────┘
                               │
                  ┌────────────┼────────────┐
                  ▼            ▼            ▼
             ┌────────┐  ┌──────────┐  ┌───────────┐
             │Overview│  │  Charts  │  │ Signature │
             │        │  │          │  │  Check    │
             └────────┘  └──────────┘  └───────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ React Web UI│
                        └─────────────┘
```

---

# 🧠 Core Design Decision

## Dynamic Table Detection

The `info.xml` roster provides **student identity**, not image coordinates.

For example:

```xml
<Student>
    <Index>10009301</Index>
    <Name>Student Name</Name>
</Student>
```

It does **not** specify where the student's signature appears in the image.

Although the printed sheet has a fixed layout, photographs taken using a phone can have different:

- Positions
- Rotations
- Scales
- Camera angles
- Perspective distortion

Therefore, SAMS detects the table geometry **from every input image** instead of using hardcoded coordinates.

This was validated against all **five provided sample sheets** through:

```text
tests/test_pipeline.py
```

---

# 📐 Why Perspective Correction?

A simple deskew operation can correct rotation, but it cannot fully correct perspective distortion.

For example, a phone photograph may produce a table where one side appears wider than the other.

SAMS therefore uses a four-corner homography:

```python
cv2.getPerspectiveTransform()
cv2.warpPerspective()
```

This corrects:

- Rotation
- Translation
- Scaling
- Perspective distortion

Perspective correction therefore provides a normalized representation of the attendance sheet before grid and signature detection.

---

# ✍️ Signature Detection

After the individual signature cells are extracted, SAMS determines whether a student has signed by measuring the amount of dark handwritten content inside each cell.

The basic process is:

```text
Signature Cell
      │
      ▼
Remove Grid-Line Remnants
      │
      ▼
Calculate Dark-Pixel Ratio
      │
      ▼
Compare Against Threshold
      │
      ├── Below threshold → ABSENT
      │
      └── Above threshold → PRESENT
```

### Current Threshold

```text
INK_RATIO_THRESHOLD = 0.01
```

The threshold was recalibrated after implementing local table-line removal.

---

# 🧹 Local Table-Line Removal

Removing table lines is important because grid borders can otherwise be interpreted as handwriting.

Two earlier approaches were tested but rejected:

### ❌ Contour-Based Global Mask

The contour mask was too thick and could remove genuine signature strokes.

### ❌ Separately Re-Detected Grid Mask

The re-detected mask did not always align with the extracted cell coordinates, causing table lines to remain in some cells.

### ✅ Current Approach

SAMS removes grid-line remnants **locally within each extracted cell**.

A row or column is treated as a grid-line remnant when it is dark across at least:

```text
85% of the cell width or height
```

This works because a table line typically spans almost the entire cell, while an actual signature stroke normally does not.

---

# 📊 Threshold Calibration

The threshold was calibrated using the five provided sample sheets after implementing local grid-line removal.

| Cell                      |  Ink Ratio |
| ------------------------- | ---------: |
| Confirmed blank           |   `0.0007` |
| Confirmed blank           |   `0.0026` |
| Lowest detected non-blank |   `0.0119` |
| **Current threshold**     | **`0.01`** |

The calibration showed a clear separation between confirmed blank cells and cells containing handwriting.

> **Note:** Recalibration should be performed if substantially different attendance-sheet samples are introduced.

---

# 🌐 Web Application

SAMS provides a browser-based application built with:

```text
Frontend        React + Vite
Backend         FastAPI
Image Processing OpenCV
Database        SQLite
Visualization   Matplotlib
```

The web application uses the **same core processing classes as the CLI tools**, avoiding duplicated processing and storage logic.

---

## 🖥️ Application Views

### 1. 📷 Process Sheet

Upload an attendance sheet and optionally provide an `info.xml` roster.

The interface provides:

- Image upload
- Optional roster upload
- Live processing status
- Pipeline log output
- Student attendance results
- Ink-ratio values
- Present/absent status

The backend runs the processing pipeline in a worker thread while the frontend polls the job-status endpoint.

---

### 2. 📋 Attendance Overview

Provides a complete:

```text
Student × Attendance Sheet
```

grid containing attendance results across all processed sheets.

This gives an overall view of attendance history.

---

### 3. 📈 Student Chart

Select a student to generate their attendance history chart.

The web application uses the same visualization functionality as:

```text
infovis.py
```

The resulting Matplotlib chart is served to the frontend as a PNG.

---

### 4. 🔎 Signature Check

The signature-check view uses the same ORB-based comparison implemented by:

```text
investigate.py
```

It provides:

- Pairwise similarity scores
- Potentially inconsistent signature pairs
- Flagged comparisons
- Visual match inspection

Each comparison includes a **View Match** option.

The system renders actual ORB keypoint matches using:

```python
cv2.drawMatches()
```

This allows a user to visually inspect the evidence instead of relying only on a numerical similarity score.

---

# 🗑️ Data Management

SAMS provides complete reset functionality.

### Reset Everything

```http
DELETE /api/reset
```

A full reset removes:

- Uploaded files
- Processing snapshots
- Generated charts
- Generated signature-match images
- Attendance records
- Processed sheets
- Stored student records

Because this operation is irreversible, the web interface requires confirmation.

### Delete a Single Sheet

```http
DELETE /api/sheet/{sheet_id}
```

The API also supports deletion of an individual sheet.

> The single-sheet deletion endpoint currently exists in the API but is not exposed in the web interface.

---

# 📁 Project Structure

```text
SAMS/
│
├── sams.py
│   └── Main pipeline orchestrator + CLI
│
├── api.py
│   └── FastAPI HTTP layer
│
├── infovis.py
│   └── Student attendance visualization CLI
│
├── investigate.py
│   └── Signature consistency analysis CLI
│
├── frontend/
│   ├── src/
│   │   └── components/
│   │       ├── ProcessSheetTab
│   │       ├── OverviewTab
│   │       ├── ChartTab
│   │       └── InvestigateTab
│   │
│   └── vite.config.js
│
├── core/
│   ├── preprocessing.py
│   │   └── Image enhancement
│   │
│   ├── table_detection.py
│   │   └── Perspective + grid detection
│   │
│   ├── extraction.py
│   │   └── Signature-cell extraction
│   │
│   ├── detection.py
│   │   └── Presence detection + line removal
│   │
│   ├── roster.py
│   │   └── info.xml parsing
│   │
│   └── verifier.py
│       └── ORB signature verification
│
├── data/
│   ├── models.py
│   │   └── Attendance data models
│   │
│   └── repository.py
│       └── SQLite database operations
│
├── viz/
│   └── visualizer.py
│       └── Attendance visualization
│
├── sample_images/
│   ├── 1.jpeg
│   ├── 2.jpeg
│   ├── 3.jpeg
│   ├── 4.jpeg
│   ├── 5.jpeg
│   └── info.xml
│
├── tests/
│   └── test_pipeline.py
│
├── output/
│   └── Generated processing results
│
├── uploads/
│   └── Uploaded attendance sheets
│
└── docs/
    └── gui_screenshots/
        └── Previous Tkinter GUI screenshots
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone <repository-url>
cd SAMS
```

## 2. Install Python Dependencies

If `requirements.txt` is available:

```bash
pip install -r requirements.txt
```

Otherwise, install the primary dependencies:

```bash
pip install fastapi uvicorn opencv-python numpy pandas matplotlib
```

## 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

# 🚀 Usage

## Option 1 — Web Application

### Start the Backend

Terminal 1:

```bash
python -m uvicorn api:app --reload --port 8010
```

### Start the Frontend

Terminal 2:

```bash
cd frontend
npm run dev
```

Open the URL displayed by Vite, normally:

```text
http://localhost:5173
```

---

## Option 2 — CLI

### Process a Sheet

```bash
python sams.py sample_images/1.jpeg sample_images/info.xml
```

### Generate a Student Attendance Chart

```bash
python infovis.py 10009301
```

### Investigate Signature Consistency

```bash
python investigate.py 10009301
```

### Run Pipeline Tests

```bash
python tests/test_pipeline.py
```

---

# 📦 Single-Process Deployment

The frontend can be built and served directly by FastAPI.

Build the frontend:

```bash
cd frontend
npm run build
```

This generates:

```text
frontend/dist/
```

Once the frontend has been built, `api.py` can serve the generated frontend.

Start the application with:

```bash
python -m uvicorn api:app
```

This allows the complete application to run as a single FastAPI process.

---

# 🧪 Testing

The pipeline has been validated against the five supplied attendance-sheet samples.

Run:

```bash
python tests/test_pipeline.py
```

The tests provide sanity checks for the real sample data and help verify that changes to image-processing logic do not break the established pipeline.

---

# ⚠️ Known Limitations

## 1. Ink Presence ≠ Signing Intent

The current detector determines attendance primarily from ink coverage.

It does not understand the semantic content of the handwriting.

For example, **Sheet 1, row 6** contains:

```text
ab
```

instead of a signature.

The system still detects it as present because its measured ink ratio is:

```text
0.058
```

This falls within the range of genuine signatures.

Therefore:

> The current system should be considered an **ink-presence detector**, not a handwriting or signature semantic recognizer.

---

## 2. Signature Verification Provides a Weak Signal

The ORB-based verification system produced the following average similarities on the sample data:

| Comparison    | Average Similarity |
| ------------- | -----------------: |
| Same student  |            `0.111` |
| Cross student |            `0.083` |

There is a measurable difference, but the signal is relatively weak because the extracted signature images are small and contain thin strokes.

Therefore, ORB flags should be interpreted as:

> **Potential inconsistencies requiring manual inspection, rather than definitive evidence of forged or inconsistent signatures.**

---

## 3. Expected Number of Rows

The current table detector expects:

```text
6 data rows
```

The value is configurable through `expect_rows`.

Attendance sheets with substantially different layouts may require this value to be adjusted.

---

# 🖥️ Previous Desktop Interface

Earlier versions of SAMS used a Tkinter desktop application.

The desktop GUI has since been replaced by the current React/FastAPI web application.

Screenshots of the previous interface are retained under:

```text
docs/gui_screenshots/
```

They are included for historical and development reference.

---

# 🛠️ Technology Stack

### Backend

- 🐍 Python
- ⚡ FastAPI
- 🚀 Uvicorn
- 👁️ OpenCV
- 🔢 NumPy
- 🐼 Pandas
- 📊 Matplotlib
- 🗄️ SQLite

### Frontend

- ⚛️ React
- ⚡ Vite
- JavaScript / TypeScript
- HTML / CSS

### Computer Vision

- Perspective transformation
- Homography
- Image thresholding
- Gaussian/image blurring
- Image denoising
- Projection histograms
- Hough transform
- Grid detection
- Cell extraction
- Ink-ratio analysis
- ORB feature detection
- ORB descriptor matching

---

# 🔄 Processing Summary

```text
📷 Photograph
     │
     ▼
📐 Perspective Correction
     │
     ▼
🖼️ Image Preprocessing
     │
     ▼
📏 Table & Grid Detection
     │
     ▼
✂️ Cell Extraction
     │
     ▼
🧹 Grid-Line Removal
     │
     ▼
✍️ Ink-Ratio Analysis
     │
     ▼
👨‍🎓 Student Matching
     │
     ▼
💾 SQLite Storage
     │
     ├───────────────┐
     ▼               ▼
📊 Attendance      🔎 Signature
   Charts            Analysis
     │               │
     └───────┬───────┘
             ▼
       🌐 Web Interface
```

---

# 🎯 Project Goal

The goal of SAMS is to demonstrate how **computer vision and image-processing techniques can be combined with database systems and web technologies to automate attendance extraction from physical signing sheets**.

The project focuses on making the detection pipeline robust to real-world photographic variations rather than relying on fixed image coordinates.

---

## 👥 Project

**Student Attendance Management System (SAMS)**

**Course:** CS402.3 — Computer Graphics and Visualization

**Application Type:** Computer Vision + Web Application

**Storage:** SQLite

**Backend:** FastAPI

**Frontend:** React + Vite
