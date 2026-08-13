import { useState } from 'react';
import './App.css';
import ProcessSheetTab from './components/ProcessSheetTab';
import OverviewTab from './components/OverviewTab';
import ChartTab from './components/ChartTab';
import InvestigateTab from './components/InvestigateTab';

const TABS = [
  { id: 'process', label: 'Process sheet' },
  { id: 'overview', label: 'Attendance overview' },
  { id: 'chart', label: 'Student chart' },
  { id: 'investigate', label: 'Signature check' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('process');
  const [dbPath, setDbPath] = useState('attendance.db');
  const [refreshKey, setRefreshKey] = useState(0);

  const bumpRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Student Attendance Management System</h1>
        <p className="subtitle">CS402.3 - image processing + attendance visualization</p>
        <div className="db-row">
          <label htmlFor="db-path">Database file:</label>
          <input
            id="db-path"
            type="text"
            value={dbPath}
            onChange={(e) => setDbPath(e.target.value)}
          />
        </div>
      </header>

      <nav className="tab-bar">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* All 4 tabs stay mounted (hidden via CSS, not unmounted) so each
          keeps its own state -- e.g. Process sheet remembers which sheet it
          just processed -- when you switch away and back. */}
      <main className="tab-content">
        <div hidden={activeTab !== 'process'}>
          <ProcessSheetTab dbPath={dbPath} onProcessed={bumpRefresh} />
        </div>
        <div hidden={activeTab !== 'overview'}>
          <OverviewTab dbPath={dbPath} refreshKey={refreshKey} />
        </div>
        <div hidden={activeTab !== 'chart'}>
          <ChartTab dbPath={dbPath} refreshKey={refreshKey} />
        </div>
        <div hidden={activeTab !== 'investigate'}>
          <InvestigateTab dbPath={dbPath} refreshKey={refreshKey} />
        </div>
      </main>
    </div>
  );
}
