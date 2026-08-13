import { useState } from 'react';
import useStudents from '../useStudents';
import { chartUrl } from '../api';

export default function ChartTab({ dbPath, refreshKey }) {
  const students = useStudents(dbPath, refreshKey);
  const [selected, setSelected] = useState(null);
  const [imgSrc, setImgSrc] = useState(null);
  const [error, setError] = useState(null);

  const showChart = () => {
    if (!selected) {
      setError('Please select a student from the list first.');
      return;
    }
    setError(null);
    setImgSrc(chartUrl(selected, dbPath));
  };

  return (
    <div className="split">
      <div className="card side-panel">
        <h3>Students</h3>
        <ul className="student-list">
          {students.map((s) => (
            <li
              key={s.student_index}
              className={selected === s.student_index ? 'selected' : ''}
              onClick={() => setSelected(s.student_index)}
            >
              {s.student_index} - {s.name}
            </li>
          ))}
        </ul>
        <button className="btn" onClick={showChart}>Show attendance chart</button>
      </div>

      <div className="card chart-panel">
        {error && <p className="error-text">{error}</p>}
        {imgSrc ? (
          <img src={imgSrc} alt="Attendance chart" onError={() => setError('Could not render chart.')} />
        ) : (
          <p>Select a student and click &quot;Show attendance chart&quot;.</p>
        )}
      </div>
    </div>
  );
}
