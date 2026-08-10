import { useState } from 'react';
// TODO (Part 1): add a `getPipeline(sheetId)` (or similar) helper to
// frontend/src/api.js that hits GET /api/pipeline/{sheet_id} and returns
// the ordered list of stage image filenames, then import it here instead
// of building URLs by hand.

// Stage list is owned jointly by Part 1 (stages 01-04, preprocessing) and
// Part 2 (stages 11-14, geometry). Keep both groups in one ordered array
// so the viewer renders a single continuous pipeline strip.
const PIPELINE_STAGES = [
  // --- Part 1: core/preprocessing.py (ImagePreprocessor) ---
  { file: '01_original.jpg', label: 'Original' },
  { file: '02_grayscale.jpg', label: 'Grayscale' },
  { file: '03_binarized.jpg', label: 'Binarized' },
  { file: '04_denoised.jpg', label: 'Denoised' },
  // --- Part 2: core/table_detection.py (TableDetector) ---
  { file: '11_grid_mask.jpg', label: 'Grid mask' },
  { file: '12_corners_detected.jpg', label: 'Corners detected' },
  { file: '13_perspective_corrected.jpg', label: 'Perspective corrected' },
  { file: '14_table_lines_mask.jpg', label: 'Table lines mask' },
];

export default function PipelineTab({ dbPath, refreshKey }) {
  // dbPath/refreshKey aren't used by this stub yet -- kept as props since
  // App.jsx passes the same props to every tab; wire them in once the
  // sheet_id picker (see TODO below) needs either of them.
  const [sheetId, setSheetId] = useState('');
  const [error, setError] = useState(null);

  // TODO (Part 1): decide how the user picks/enters the last-processed
  // sheet_id (a text input is the simplest starting point -- sheet_id is
  // just the image filename without extension, e.g. "5" for 5.jpeg).
  // Consider deriving it automatically from ProcessSheetTab's last run
  // instead of typing it in, once the shared state story is worked out.

  const imgUrl = (stageFile) =>
    `/api/pipeline/${encodeURIComponent(sheetId)}/${stageFile}?t=${Date.now()}`;

  return (
    <div>
      <div className="tab-header">
        <h2>Pipeline stage viewer</h2>
      </div>
      <div className="card form-card">
        <label htmlFor="pipeline-sheet-id">Sheet id:</label>
        <input
          id="pipeline-sheet-id"
          type="text"
          value={sheetId}
          onChange={(e) => setSheetId(e.target.value)}
          placeholder="e.g. 5"
        />
      </div>
      {error && <p className="error-text">{error}</p>}
      {/* TODO: render PIPELINE_STAGES in sequence, each as a labelled
          thumbnail (card + <img>), falling back gracefully (hide or show
          a placeholder) for any stage image that 404s -- e.g. stages 11-14
          won't exist until Part 2's table_detection.py changes land. */}
      <div className="pipeline-strip">
        {sheetId
          ? PIPELINE_STAGES.map((stage) => (
              <div className="card pipeline-stage" key={stage.file}>
                <h4>{stage.label}</h4>
                <img
                  src={imgUrl(stage.file)}
                  alt={stage.label}
                  onError={() => setError(`Could not load ${stage.file} for sheet ${sheetId}`)}
                />
              </div>
            ))
          : <p>Enter a sheet id above to view its processing stages.</p>}
      </div>
    </div>
  );
}
