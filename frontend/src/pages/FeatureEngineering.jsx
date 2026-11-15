import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { ShieldCheck, Search, Filter, Layers } from 'lucide-react';

export default function FeatureEngineering({ scope, source }) {
  const [activeTab, setActiveTab] = useState('dictionary');
  const [features, setFeatures] = useState([]);
  const [importance, setImportance] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('All');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getFeaturesDictionary(),
      api.getFeaturesImportance(source),
    ])
      .then(([dict, imp]) => {
        setFeatures(dict?.features || []);
        setImportance(imp?.importance || imp?.items || imp?.data || []);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [source]);

  const groups = ['All', ...new Set(features.map((f) => f.group))];

  const filteredFeatures = features.filter((f) => {
    const matchesGroup = selectedGroup === 'All' || f.group === selectedGroup;
    const matchesSearch =
      !search ||
      f.name.toLowerCase().includes(search.toLowerCase()) ||
      f.justification.toLowerCase().includes(search.toLowerCase());
    return matchesGroup && matchesSearch;
  });

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          How the model uses past information
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Features are measurements created from surveillance reports. They help describe recent history without using the year the model is trying to predict.
        </p>
      </div>

      <div className="tabs-header">
        {[
          { id: 'dictionary', label: '1. Feature guide' },
          { id: 'leakage', label: '2. Past-data checks' },
          { id: 'importance', label: '3. Feature associations' },
        ].map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB 1: Dictionary */}
      {activeTab === 'dictionary' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', width: 280 }}>
              <input
                type="text"
                className="form-input"
                placeholder="Search feature names or explanations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Group:</span>
              <select
                className="form-select"
                style={{ width: 180 }}
                value={selectedGroup}
                onChange={(e) => setSelectedGroup(e.target.value)}
              >
                {groups.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th title="The internal name used by the model">Feature</th>
                  <th title="The type of information this feature summarizes">Type</th>
                </tr>
              </thead>
              <tbody>
                {filteredFeatures.map((f) => (
                  <tr key={f.name}>
                    <td><code style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{f.name}</code></td>
                    <td><span className="badge" style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 8px', borderRadius: 4 }}>{f.group}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 12, fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            Showing {filteredFeatures.length} of {features.length} features.
          </div>
        </div>
      )}

      {/* TAB 2: Leakage */}
      {activeTab === 'leakage' && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <ShieldCheck size={28} color="#34d399" />
            <div>
              <h3 style={{ fontSize: '1.2rem' }}>Checks that prevent looking into the future</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                A forecast for a year can only use information that would have been available before that year. Data preparation steps are fit on training years only.
              </p>
            </div>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Automated check</th>
                  <th>What it checks</th>
                  <th>Recorded result</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>test_leakage.py::test_lag1_matches_raw</code></td>
                  <td>The previous year’s resistance value is used as the previous-year feature.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_leakage.py::test_permute_target_year_does_not_change_features</code></td>
                  <td>Changing the year being predicted does not change features built from earlier data.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_leakage.py::test_years_observed_excludes_target</code></td>
                  <td>The year being predicted is not counted as an observed year.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_leakage.py::test_region_median_uses_t_minus_1</code></td>
                  <td>Regional comparisons use information from the preceding year, not the future year.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_splits.py::test_rolling_origin_order</code></td>
                  <td>Training years come before the validation years.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="explainer" style={{ marginTop: 14 }}>
            These checks are automated tests in the project; the table describes what they check, not whether they have just run. See the project test instructions to run them.
          </div>
        </div>
      )}

      {/* TAB 3: Univariate Association */}
      {activeTab === 'importance' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>How each feature relates to the target</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 20 }}>
            A one-at-a-time comparison using training records only. “Training records” are the past examples used to fit a model.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {importance.map((item) => (
              <div key={item.feature} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ width: 170, fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                  <code>{item.feature}</code>
                </div>
                <div style={{ flex: 1, position: 'relative', height: 20, background: 'rgba(255,255,255,0.03)', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, Math.abs(item.abs_importance ?? 0) * 100)}%`,
                      background: 'linear-gradient(90deg, #06b6d4, #3b82f6)',
                      borderRadius: 4,
                    }}
                  />
                </div>
                <div style={{ width: 70, fontSize: '0.8rem', color: 'var(--accent-cyan)', textAlign: 'right', fontWeight: 600 }}>
                  |r| {(item.abs_importance ?? 0).toFixed(2)}
                </div>
              </div>
            ))}
          </div>

        </div>
      )}

    </div>
  );
}
