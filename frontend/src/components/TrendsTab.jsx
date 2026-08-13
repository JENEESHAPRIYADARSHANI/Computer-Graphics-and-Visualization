import { useEffect, useState, useCallback } from 'react';
// TODO (Part 7): add `getTrends(dbPath)` and `exportTrendsCsvUrl(dbPath)`
// helpers to frontend/src/api.js (mirroring the getOverview/chartUrl
// pattern already there) that hit the new aggregation/export routes you
// add to api.py, then import them here instead of calling fetch() inline.

export default function TrendsTab({ dbPath, refreshKey }) {
  const [trend, setTrend] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      // TODO: replace with getTrends(dbPath) once the api.js helper exists.
      // Expected shape from the new GET /api/trends route: overall
      // class attendance rate per sheet, across all sheets in processed
      // order -- e.g. { sheet_ids: [...], attendance_rate: [0.83, 0.9, ...] }
      setTrend(null);
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
        <h2>Attendance trends</h2>
        <button className="btn" onClick={refresh}>Refresh</button>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="card">
        {/* TODO: render the overall class attendance rate across sheets
            over time (a line/bar chart is fine -- see ChartTab.jsx and
            viz/visualizer.py for the existing chart conventions used
            elsewhere in this app). */}
        {trend ? (
          <p>TODO: render trend chart from {JSON.stringify(trend)}</p>
        ) : (
          <p>No trend data yet.</p>
        )}
      </div>
      <div className="card">
        {/* TODO: CSV export -- a plain <a href={exportTrendsCsvUrl(dbPath)}
            download> pointing at the new export route is enough. */}
        <button className="btn" disabled>Export CSV (TODO)</button>
      </div>
    </div>
  );
}
