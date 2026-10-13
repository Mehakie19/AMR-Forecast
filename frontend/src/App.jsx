import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  BarChart2,
  FileCode,
  FlaskConical,
  LineChart,
  ClipboardList,
  HelpCircle,
  AlertTriangle,
  Radio,
  CheckCircle,
  Database
} from 'lucide-react';

import { api } from './api';
import DatasetOverview from './pages/DatasetOverview';
import EdaExplorer from './pages/EdaExplorer';
import FeatureEngineering from './pages/FeatureEngineering';
import ModelLab from './pages/ModelLab';
import ForecastExplorer from './pages/ForecastExplorer';
import SurveillanceWatchlist from './pages/SurveillanceWatchlist';
import MethodsLimitations from './pages/MethodsLimitations';

const DISCLAIMER_TEXT =
  "Surveillance and research tool. Not for treatment decisions. Predicted resistance is not the probability of clinical cure. 'High risk' and 'rising' thresholds are project-defined.";

const COMBINED_NOTICE =
  "Sources use different resistance definitions (GLASS: R; ECDC: I+R). Do not compare levels directly.";

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
    { id: 'overview', label: '1. Dataset Overview', icon: LayoutDashboard },
    { id: 'eda', label: '2. EDA Explorer', icon: BarChart2 },
    { id: 'features', label: '3. Feature Engineering', icon: FileCode },
    { id: 'models', label: '4. Model Lab & Results', icon: FlaskConical },
    { id: 'forecast', label: '5. Forecast Explorer', icon: LineChart },
    { id: 'watchlist', label: '6. Surveillance Watchlist', icon: ClipboardList },
    { id: 'methods', label: '7. Methods & Roadmap', icon: HelpCircle },
  ];

  return (
    <div>
      {/* 1. Persistent Top Warning Banner */}
      <div className="disclaimer-banner">
        <AlertTriangle size={18} />
        <div>
          <strong>Disclaimer:</strong> {DISCLAIMER_TEXT}
        </div>
      </div>

      <div className="app-container">
        {/* 2. Left Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <div className="brand-title">
              AMR-Sense <span className="badge">Phase 1</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: 4 }}>
              Explainable AMR Surveillance &amp; Early Warning
            </div>
          </div>

          {/* Scope Selector */}
          <div className="sidebar-scope">
            <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: 6 }}>
              DATA SCOPE
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

            {scope === 'Combined' && (
              <div
                style={{
                  marginTop: 10,
                  padding: '8px 10px',
                  background: 'rgba(245, 158, 11, 0.1)',
                  border: '1px solid rgba(245, 158, 11, 0.25)',
                  borderRadius: 6,
                  fontSize: '0.74rem',
                  color: '#fde68a',
                  lineHeight: 1.4,
                }}
              >
                ⚠️ {COMBINED_NOTICE}
              </div>
            )}
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
              <span>Rows in Scope: <strong>{summary?.rows?.toLocaleString() ?? '—'}</strong></span>
              <span className="status-badge" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                {health?.frozen ? 'Models Frozen (Test Unlocked)' : 'Models Frozen'}
              </span>
            </div>
          </div>

          {/* Active View */}
          {activePage === 'overview' && <DatasetOverview scope={scope} source={sourceParam} />}
          {activePage === 'eda' && <EdaExplorer scope={scope} source={sourceParam} />}
          {activePage === 'features' && <FeatureEngineering scope={scope} source={sourceParam} />}
          {activePage === 'models' && <ModelLab scope={scope} />}
          {activePage === 'forecast' && <ForecastExplorer scope={scope} source={sourceParam} />}
          {activePage === 'watchlist' && <SurveillanceWatchlist scope={scope} source={sourceParam} />}
          {activePage === 'methods' && <MethodsLimitations />}
        </main>
      </div>
    </div>
  );
}
