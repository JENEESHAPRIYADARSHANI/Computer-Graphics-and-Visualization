import { useEffect, useRef, useState } from 'react';
import { startProcessSheet, getProcessStatus, resetAll } from '../api';

export default function ProcessSheetTab({ dbPath, onProcessed }) {
  const [imageFile, setImageFile] = useState(null);
  const [xmlFile, setXmlFile] = useState(null);
  const [log, setLog] = useState([]);
  const [records, setRecords] = useState([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [clearing, setClearing] = useState(false);
  const [inputResetKey, setInputResetKey] = useState(0);
  const pollRef = useRef(null);
  const logBoxRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  useEffect(() => {
    if (logBoxRef.current) {
      logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
    }
  }, [log]);

  const handleProcess = async () => {
    if (!imageFile) {
      setError('Please choose a signing sheet image.');
      return;
    }
    setError(null);
    setLog([]);
    setRecords([]);
    setRunning(true);

    try {
      const { job_id } = await startProcessSheet({ imageFile, xmlFile, dbPath });
      pollRef.current = setInterval(async () => {
        try {
          const status = await getProcessStatus(job_id);
          setLog(status.log);
          if (status.status === 'done') {
            clearInterval(pollRef.current);
            setLog((l) => [...l, 'Processing complete.']);
            setRecords(status.records);
            setRunning(false);
            onProcessed?.();
          } else if (status.status === 'error') {
            clearInterval(pollRef.current);
            setError(status.error);
            setLog((l) => [...l, `ERROR: ${status.error}`]);
            setRunning(false);
          }
        } catch (e) {
          clearInterval(pollRef.current);
          setError(e.message);
          setRunning(false);
        }
      }, 400);
    } catch (e) {
      setError(e.message);
      setRunning(false);
    }
  };

  const resetLocalState = () => {
    setImageFile(null);
    setXmlFile(null);
    setLog([]);
    setRecords([]);
    setError(null);
    setInputResetKey((k) => k + 1);
  };

  // Full reset, not just "undo the last upload": every file under uploads/,
  // every processing snapshot/chart/match-image under output/, and every
  // row in the db at dbPath -- all sheets, all students, everything.
  const handleClear = async () => {
    const ok = window.confirm(
      `Delete ALL uploaded files and ALL attendance data (every sheet, every student) ` +
        `in database "${dbPath}"? This cannot be undone.`
    );
    if (!ok) return;

    setClearing(true);
    setError(null);
    try {
      await resetAll(dbPath);
      resetLocalState();
      onProcessed?.();
    } catch (e) {
      setError(`Could not clear data: ${e.message}`);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div>
      <div className="card form-card">
        <div className="file-row" key={`image-${inputResetKey}`}>
          <label>Signing sheet image:</label>
          <input
            type="file"
            accept="image/png,image/jpeg"
            onChange={(e) => setImageFile(e.target.files[0] || null)}
          />
        </div>
        <div className="file-row" key={`xml-${inputResetKey}`}>
          <label>info.xml roster (optional):</label>
          <input
            type="file"
            accept=".xml"
            onChange={(e) => setXmlFile(e.target.files[0] || null)}
          />
          <span className="hint">defaults to sample_images/info.xml on the server</span>
        </div>
        <div className="button-row">
          <button className="btn accent" onClick={handleProcess} disabled={running}>
            {running ? 'Processing…' : 'Process sheet'}
          </button>
          <button className="btn" onClick={handleClear} disabled={running || clearing}>
            {clearing ? 'Clearing…' : 'Clear all data'}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </div>

      <div className="two-col">
        <div className="card">
          <h3>Processing log</h3>
          <div className="log-box" ref={logBoxRef}>
            {log.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Result for this sheet</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Index</th>
                <th>Status</th>
                <th>Ink ratio</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.student_index}>
                  <td>{r.student_name}</td>
                  <td>{r.student_index}</td>
                  <td className={r.present ? 'present' : 'absent'}>
                    {r.present ? 'Present' : 'Absent'}
                  </td>
                  <td>{r.ink_ratio.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
