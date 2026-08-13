import { useState } from 'react';
import useStudents from '../useStudents';
import { getInvestigate, matchImageUrl } from '../api';

export default function InvestigateTab({ dbPath, refreshKey }) {
  const students = useStudents(dbPath, refreshKey);
  const [selected, setSelected] = useState(null);
  const [resultStudent, setResultStudent] = useState(null);
  const [comparisons, setComparisons] = useState([]);
  const [flaggedKeys, setFlaggedKeys] = useState(new Set());
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);
  const [viewingPair, setViewingPair] = useState(null);

  const pairKey = (c) => `${c.sheet_a}|${c.sheet_b}`;

  const runCheck = async () => {
    if (!selected) {
      setError('Please select a student from the list first.');
      return;
    }
    setError(null);
    setViewingPair(null);
    try {
      const result = await getInvestigate(selected, dbPath);
      setResultStudent(selected);
      if (result.note === 'need_more_sheets') {
        setComparisons([]);
        setFlaggedKeys(new Set());
        setNote('Need at least 2 signed sheets for this student to compare.');
        return;
      }
      setComparisons(result.comparisons);
      setFlaggedKeys(new Set(result.flagged.map(pairKey)));
      setNote(
        `${result.flagged.length} of ${result.comparisons.length} pair(s) flagged. ` +
          'Similarity is a weak signal on small crops -- treat flags as worth a manual look, ' +
          'not definitive proof (see README).'
      );
    } catch (e) {
      setError(e.message);
    }
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
        <button className="btn" onClick={runCheck}>Check signature consistency</button>
      </div>

      <div className="card chart-panel">
        <h3>Pairwise signature similarity</h3>
        {error && <p className="error-text">{error}</p>}
        <table className="data-table">
          <thead>
            <tr>
              <th>Sheet A</th>
              <th>Sheet B</th>
              <th>Similarity</th>
              <th>Flag</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((c) => {
              const flagged = flaggedKeys.has(pairKey(c));
              return (
                <tr key={pairKey(c)} className={flagged ? 'absent' : ''}>
                  <td>{c.sheet_a}</td>
                  <td>{c.sheet_b}</td>
                  <td>{c.similarity.toFixed(3)}</td>
                  <td>{flagged ? 'Review suggested' : 'OK'}</td>
                  <td>
                    <button
                      className="btn small"
                      onClick={() => setViewingPair({ sheet_a: c.sheet_a, sheet_b: c.sheet_b })}
                    >
                      View match
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {note && <p className="note-text">{note}</p>}

        {viewingPair && (
          <div className="match-image-panel">
            <h4>
              Matched keypoints: sheet {viewingPair.sheet_a} vs sheet {viewingPair.sheet_b}
            </h4>
            <img
              src={matchImageUrl(resultStudent, viewingPair.sheet_a, viewingPair.sheet_b, dbPath)}
              alt={`ORB keypoint matches between sheet ${viewingPair.sheet_a} and sheet ${viewingPair.sheet_b}`}
              onError={() => setError('Could not render match image.')}
            />
          </div>
        )}
      </div>
    </div>
  );
}
