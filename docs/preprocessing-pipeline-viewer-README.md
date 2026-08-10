# Part 1 — Preprocessing + Pipeline Stage Viewer

## Goal

Show the step-by-step image-processing pipeline (original → grayscale →
binarized → denoised) for the last processed sheet in a new **Pipeline**
tab in the web UI.

## Current state (read before you start)

`core/preprocessing.py` (`ImagePreprocessor`) already implements the full
chain and already saves the snapshots you need, into `output/<sheet_id>/`:

- `01_original.jpg` — `load()`
- `02_grayscale.jpg` — `to_grayscale()`
- `025_blurred.jpg` — `blur()` (extra stage, not in the requested sequence — leave it, it's harmless, just don't rely on the viewer needing it)
- `03_binarized.jpg` — `binarize()`
- `04_denoised.jpg` — `denoise()`

So **the CV side of this part is essentially done**. Your real work is:

1. Sanity-check `core/preprocessing.py` — confirm the 4 stages match the
   spec, tidy naming/comments if needed, add a unit test if you want extra
   coverage (coordinate with Part 7, who owns `tests/test_pipeline.py`).
2. Add the new `GET /api/pipeline/{sheet_id}` route to `api.py`.
3. Build the `Pipeline` tab in the frontend: `frontend/src/components/PipelineTab.jsx`.

## Files in this folder

- `core/preprocessing.py` — current version, reference/starting point.
- `api.py` — current version. **Add your route near the bottom**, before
  the `if os.path.isdir(FRONTEND_DIST):` block at the end. Suggested
  shape:

  ```python
  @app.get("/api/pipeline/{sheet_id}")
  async def pipeline_stages(sheet_id: str):
      sheet_id = _safe_id(sheet_id, "sheet_id")
      snap_dir = os.path.join("output", sheet_id)
      if not os.path.isdir(snap_dir):
          raise HTTPException(404, f"No snapshots found for sheet {sheet_id!r}")
      # list the stage files that actually exist for this sheet (Part 2's
      # 11_grid_mask.jpg..14_table_lines_mask.jpg live in the same folder),
      # in stage order, and return filenames the frontend can build image
      # URLs from.
      ...

  @app.get("/api/pipeline/{sheet_id}/{filename}")
  async def pipeline_stage_image(sheet_id: str, filename: str):
      sheet_id = _safe_id(sheet_id, "sheet_id")
      path = os.path.join("output", sheet_id, filename)
      if not os.path.isfile(path):
          raise HTTPException(404, "Stage image not found")
      return FileResponse(path, media_type="image/jpeg")
  ```

  Validate `filename` too (no path separators / `..`) before joining it
  into a filesystem path — reuse `_safe_id` or write a similarly strict
  check, the same way `delete_sheet`/`reset_all` already guard `sheet_id`.

- `frontend/src/api.js` — current version. Add a small helper (e.g.
  `pipelineStageUrl(sheetId, filename)`) following the existing pattern
  (`chartUrl`, `matchImageUrl`).
- `frontend/src/App.jsx` — current version, **read-only reference**. Add
  one entry to `TABS` (e.g. `{ id: 'pipeline', label: 'Pipeline' }`) and
  one `<div hidden={...}><PipelineTab .../></div>` block, without touching
  the other tabs' entries — Part 7 is adding a `Trends` tab the same way.
- `frontend/src/components/PipelineTab.jsx` — a skeleton starting point,
  already wired for the full 8-stage sequence (your 4 preprocessing stages
  + Part 2's 4 geometry stages) so you don't have to coordinate the array
  shape with Part 2 later. Fill in the `TODO`s.
- `frontend/src/App.css` — current version. The stub already references
  two classes that don't exist yet (`pipeline-strip`, `pipeline-stage`) —
  add them here (a flex/grid strip of cards is enough, following the
  existing `.card`/`.data-table` conventions already in this file).

## Coordination

- Part 2 extends the same `PipelineTab.jsx` with the geometry stages
  (`11_grid_mask.jpg` → `14_table_lines_mask.jpg`). The stub already lists
  both groups in one `PIPELINE_STAGES` array — build the viewer to render
  whatever stages exist for a sheet (some sheets may not have Part 2's
  stages yet), not to assume all 8 are always present.
- Part 7 also edits `App.jsx` (adding the `Trends` tab) and `api.js`
  (adding trend/export helpers) — only touch your own lines in both files.
