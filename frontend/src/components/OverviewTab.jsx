import { useEffect, useState, useCallback } from 'react';
import { getOverview } from '../api';

export default function OverviewTab({ dbPath, refreshKey }) {
    const [sheetIds, setSheetIds] = useState([]);
    const [students, setStudents] = useState([]);
    const [error, setError] = useState(null);

    const refresh = useCallback(async () => {
        try {
            const data = await getOverview(dbPath);
            setSheetIds(data.sheet_ids);
            setStudents(data.students);
            setError(null);
        } catch (e) {
            setError(e.message);
        }
    }, [dbPath]);

    useEffect(() => {
        refresh();
    }, [refresh, refreshKey]);

    return (
        <div>
            <div className="tab-header">
                <h2>All processed sheets, all students</h2>
                <button className="btn" onClick={refresh}>Refresh</button>
            </div>
            {error && <p className="error-text">{error}</p>}
            <div className="card">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Student</th>
                            {sheetIds.map((sid) => (
                                <th key={sid}>Sheet {sid}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {students.map((s) => (
                            <tr key={s.student_index}>
                                <td>{s.name}</td>
                                {sheetIds.map((sid) => {
                                    const present = s.status_by_sheet[sid];
                                    const label = present === undefined ? '-' : present ? 'Present' : 'Absent';
                                    const cls = present === true ? 'present' : present === false ? 'absent' : '';
                                    return (
                                        <td key={sid} className={cls} style={{ textAlign: 'center' }}>
                                            {label}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
