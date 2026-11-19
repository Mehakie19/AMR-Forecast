import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  BarChart2,
  FileCode,
  FlaskConical,
  LineChart,
  Radio,
  Globe2,
} from 'lucide-react';

import { api } from './api';
import DatasetOverview from './pages/DatasetOverview';
import EdaExplorer from './pages/EdaExplorer';
import FeatureEngineering from './pages/FeatureEngineering';
import ModelLab from './pages/ModelLab';
import ForecastExplorer from './pages/ForecastExplorer';
import IntelligenceOverview from './pages/IntelligenceOverview';

export default function App() {
  const [activePage, setActivePage] = useState('overview');
  const [scope, setScope] = useState('Combined');
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);

  // Map scope string to API query source
  const sourceParam = scope === 'GLASS-AMR' ? 'glass' : scope === 'ECDC-derived' ? 'ecdc' : 'combined';

  useEffect(() => {
    api.getHealth()
      .then((h) => setHealth(h))
      .catch((err) => {
        console.error('API health check error:', err);
        setHealth({ status: 'offline' });
      });

    api.getDatasetsSummary(sourceParam)
      .then((s) => setSummary(s))
      .catch(console.error);
  }, [sourceParam]);

  const navItems = [
    { id: 'intelligence', label: '1. Visual overview', icon: Globe2 },
    { id: 'overview', label: '2. Dataset Overview', icon: LayoutDashboard },
    { id: 'eda', label: '3. Explore data', icon: BarChart2 },
    { id: 'features', label: '4. Model inputs', icon: FileCode },
    { id: 'models', label: '5. Model results', icon: FlaskConical },
    { id: 'forecast', label: '6. Five-year forecast', icon: LineChart },
  ];

  return (
    <div>
      <div className="app-container">
        {/* 2. Left Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <div className="brand-title">
              AMR-Sense
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: 4 }}>
              Antibiotic resistance surveillance
            </div>
          </div>

          {/* Scope Selector */}
          <div className="sidebar-scope">
            <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: 6 }}>
              DATA SOURCE
            </label>
            <select
              className="form-select"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              <option value="Combined">Combined (GLASS + ECDC)</option>
              <option value="GLASS-AMR">GLASS-AMR (WHO)</option>
              <option value="ECDC-derived">ECDC-derived (EARS-Net)</option>
            </select>

          </div>

          {/* Navigation Links */}
          <nav className="sidebar-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  className={`nav-link ${isActive ? 'active' : ''}`}
                  onClick={() => setActivePage(item.id)}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Sidebar Footer Info */}
          <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            <div>API: <code>{import.meta.env.VITE_API_BASE_URL || '/api'}</code></div>
            <div>Seed: <code>42</code> | Strict Temporal Order</div>
          </div>
        </aside>

        {/* 3. Main Content Area */}
        <main className="main-content">
          {/* Status Strip */}
          <div className="status-strip">
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <span className={`status-badge ${health?.status === 'ok' ? 'online' : 'offline'}`}>
                <Radio size={12} />
                {health?.status === 'ok' ? 'FastAPI Online' : 'API Offline (Check port 8001)'}
              </span>
              <span>Data Version: <code>{health?.data_version || 'SHA256:49fb1...'}</code></span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <span>Reported observations: <strong>{summary?.rows?.toLocaleString() ?? '—'}</strong></span>
              <span className="status-badge" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                {health?.frozen ? 'Models Frozen (Test Unlocked)' : 'Models Frozen'}
              </span>
            </div>
          </div>

          {/* Active View */}
          {activePage === 'intelligence' && <IntelligenceOverview key={sourceParam} source={sourceParam} />}
          {activePage === 'overview' && <DatasetOverview scope={scope} source={sourceParam} />}
          {activePage === 'eda' && <EdaExplorer scope={scope} source={sourceParam} />}
          {activePage === 'features' && <FeatureEngineering scope={scope} source={sourceParam} />}
          {activePage === 'models' && <ModelLab scope={scope} />}
          {activePage === 'forecast' && <ForecastExplorer scope={scope} source={sourceParam} />}
        </main>
      </div>
    </div>
  );
}
