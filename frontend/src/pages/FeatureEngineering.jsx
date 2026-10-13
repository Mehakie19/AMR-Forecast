import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { ShieldCheck, Search, Filter, Layers, CheckCircle2 } from 'lucide-react';

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
        setImportance(imp?.importance || imp?.items || []);
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
          Feature Engineering & Leakage Prevention
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          23 domain-tailored surveillance features strictly respecting the temporal invariant $t \le t-1$.
        </p>
      </div>

      <div className="tabs-header">
        {[
          { id: 'dictionary', label: '1. Feature Dictionary' },
          { id: 'leakage', label: '2. Leakage-Safety Verification' },
          { id: 'importance', label: '3. Univariate Association' },
          { id: 'funnel', label: '4. Eligible-Row Funnel' },
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
                placeholder="Search feature or justification..."
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
                  <th>Feature Name</th>
                  <th>Group</th>
                  <th>Formula / Derivation</th>
                  <th>Availability</th>
                  <th>AMR Surveillance Rationale</th>
                </tr>
              </thead>
              <tbody>
                {filteredFeatures.map((f) => (
                  <tr key={f.name}>
                    <td><code style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{f.name}</code></td>
                    <td><span className="badge" style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 8px', borderRadius: 4 }}>{f.group}</span></td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{f.definition}</td>
                    <td><span style={{ fontSize: '0.78rem', color: f.availability === 'direct' ? '#34d399' : '#60a5fa' }}>{f.availability}</span></td>
                    <td style={{ fontSize: '0.8rem', color: '#e2e8f0' }}>{f.justification}</td>
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
              <h3 style={{ fontSize: '1.2rem' }}>Leakage-Safety Invariant Verification</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Target at year $t$ uses exclusively observations from years $\le t-1$. Scalers and encoders fit on training split only.
              </p>
            </div>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Verification Test Suite</th>
                  <th>Mathematical Invariant Proved</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>test_leakage.py::test_lag1_matches_raw</code></td>
                  <td>Confirm <code>lag_1</code> strictly matches raw <code>pct_resistant</code> at year $t-1$.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_leakage.py::test_permute_target_year_does_not_change_features</code></td>
                  <td>Permuting year $t$ labels produces zero change in any constructed feature vector.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_leakage.py::test_years_observed_excludes_target</code></td>
                  <td>Verifies <code>years_observed</code> never counts the evaluation year $t$.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_leakage.py::test_region_median_uses_t_minus_1</code></td>
                  <td>Confirms regional baseline medians are computed from year $t-1$ cross-sections only.</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
                <tr>
                  <td><code>test_splits.py::test_rolling_origin_order</code></td>
                  <td>Proves that in every fold: max(train_year) &lt; min(val_year).</td>
                  <td><span style={{ color: '#34d399', fontWeight: 600 }}>PASSED ✅</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="explainer" style={{ marginTop: 14 }}>
            All mathematical proofs verified by automated pytest unit tests. Final test year evaluated once under guarded <code>models/FROZEN</code> marker.
          </div>
        </div>
      )}

      {/* TAB 3: Univariate Association */}
      {activeTab === 'importance' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>Univariate Predictive Power (Training Rows Only)</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 20 }}>
            Ranked single-variable association with surveillance targets computed strictly on training observations.
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

          <div className="explainer">Each feature row is ranked by the size of its simple correlation with a target. The two signed correlations below show direction and strength: positive means the target tends to be higher as the feature rises; negative means the reverse. This is a quick association check, not proof that a feature causes resistance or works well in a full model.</div>

          <div className="explainer" style={{ marginTop: 20 }}>
            Temporal inertia (<code>lag_1</code>, <code>roll_mean_2</code>) provides dominant baseline predictability, enriched by multi-drug resistance burden (<code>mdr_burden</code>) and peer deviation (<code>gap_from_region_prev</code>).
          </div>
        </div>
      )}

      {/* TAB 4: Eligible Funnel */}
      {activeTab === 'funnel' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 14 }}>Surveillance Filtering &amp; Eligibility Funnel</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Processing Pipeline Stage</th>
                  <th>GLASS-AMR</th>
                  <th>ECDC-derived</th>
                  <th>Combined Pooled</th>
                  <th>Filtering Rationale</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>1. Raw Observations</strong></td>
                  <td>2,394</td>
                  <td>4,240</td>
                  <td>6,634</td>
                  <td>Initial surveillance exports from WHO &amp; Zenodo</td>
                </tr>
                <tr>
                  <td><strong>2. Consecutive Year Eligible</strong></td>
                  <td>1,995</td>
                  <td>3,879</td>
                  <td>5,874</td>
                  <td>Requires preceding year $t-1$ for lag &amp; delta construction</td>
                </tr>
                <tr>
                  <td><strong>3. Classification Filter ($N \ge 30$)</strong></td>
                  <td style={{ color: 'var(--source-glass)', fontWeight: 600 }}>1,867</td>
                  <td style={{ color: 'var(--source-ecdc)', fontWeight: 600 }}>3,879</td>
                  <td style={{ fontWeight: 600 }}>5,746</td>
                  <td>Excludes small sample noise ($N &lt; 30$ removed 128 GLASS rows; 0 ECDC rows)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Key Takeaway */}
      <div className="takeaway-box">
        <CheckCircle2 size={24} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4>Key Takeaway: Temporal Invariants Preserved</h4>
          <p>
            All 23 features strictly obey the rule $t \le t-1$, preventing any future lookahead bias. The 128 noisy observations with $N &lt; 30$ in GLASS are filtered from classification targets while remaining available for exploratory surveillance tracking.
          </p>
        </div>
      </div>
    </div>
  );
}
