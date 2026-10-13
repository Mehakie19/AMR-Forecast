import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { BookOpen, AlertOctagon, Terminal, CheckCircle2 } from 'lucide-react';

export default function MethodsLimitations() {
  const [activeTab, setActiveTab] = useState('definitions');
  const [methods, setMethods] = useState(null);

  useEffect(() => {
    api.getMethods().then((m) => setMethods(m)).catch(console.error);
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Methodological Framework, Technical Limitations &amp; Roadmap
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Formal target mathematics, temporal validation designs, surveillance caveats, and Phase 2 research modules.
        </p>
      </div>

      <div className="tabs-header">
        {[
          { id: 'definitions', label: '1. Targets & Hypothesis Math' },
          { id: 'splits', label: '2. Time-Ordered Split Design' },
          { id: 'limitations', label: '3. Surveillance Limitations' },
          { id: 'phase2', label: '4. Phase 2 Roadmap & Stubs' },
          { id: 'provenance', label: '5. System Provenance' },
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

      {/* TAB 1: Definitions */}
      {activeTab === 'definitions' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Operational Target Definitions &amp; Significance Rules</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: 18, borderRadius: 8 }}>
              <h4 style={{ color: 'var(--accent-cyan)', marginBottom: 8 }}>1. Continuous Resistance Forecast (<code>y_reg</code>)</h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Next-year continuous percentage resistance $p_t \in [0, 100]$ for series $(s, c, p, a)$. Evaluated on Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and the proportion of surveillance series where model absolute error beats naive persistence $|p_t - p_{t-1}|$.
              </p>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: 18, borderRadius: 8 }}>
              <h4 style={{ color: '#f87171', marginBottom: 8 }}>2. High-Risk Surveillance Alarm (<code>high_risk_next</code>)</h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Binary classification target $y_t = \mathbb{I}(p_t \ge T)$, evaluated at project-defined threshold $T = 30\%$ (with sensitivity checks at $T = 20\%$ and $T = 50\%$). Decision threshold is selected exclusively on validation years to maximize F1 subject to a false-alert rate cap ($\le 20\%$).
              </p>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: 18, borderRadius: 8 }}>
              <h4 style={{ color: '#fbbf24', marginBottom: 8 }}>3. Statistically Significant Acceleration (<code>rising_next</code>)</h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Composite surveillance flag indicating acute acceleration:
                <br />
                • Condition 1: Magnitude rise: p_t - p_(t-1) &ge; 5.0 percentage points.
                <br />
                • Condition 2: One-sided two-proportion z-test (<code>proportions_ztest</code>) on raw counts (n_r, n_t) at year t vs t-1 yields p &lt; 0.05.
                <br />
                • Condition 3: Sample reliability: N_t &ge; 30 and N_(t-1) &ge; 30 in both surveillance years.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Splits */}
      {activeTab === 'splits' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 14 }}>Time-Ordered Split Architecture &amp; Rolling-Origin Folds</h3>
          <div className="data-table-container" style={{ marginBottom: 20 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Configuration</th>
                  <th>Training Targets</th>
                  <th>Validation Folds</th>
                  <th>Guarded Final Test</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>GLASS-AMR</strong></td>
                  <td>2019 – 2021</td>
                  <td>2022</td>
                  <td>2023 (Single shot)</td>
                </tr>
                <tr>
                  <td><strong>ECDC-derived</strong></td>
                  <td>1999 – 2015</td>
                  <td>2016 – 2017</td>
                  <td>2018 – 2019 (Single shot)</td>
                </tr>
                <tr>
                  <td><strong>Pooled</strong></td>
                  <td>ECDC $\le 2015$ + GLASS 2019–2021</td>
                  <td>ECDC 2016–2017 + GLASS 2022</td>
                  <td>ECDC 2018–2019 + GLASS 2023</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="explainer">
            <strong>Rolling-Origin Folds:</strong> On training years, fold $k$ trains exclusively on years $&lt; Y_k$ and evaluates on $Y_k$. This expands the training window forward in time without cross-contamination.
          </div>
        </div>
      )}

      {/* TAB 3: Limitations */}
      {activeTab === 'limitations' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Surveillance Caveats &amp; Known Limitations</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Limitation Domain</th>
                  <th>Scientific / Surveillance Caveat</th>
                  <th>Impact on Interpretation</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Definition Mismatch (R vs I+R)</strong></td>
                  <td>ECDC reports Intermediate + Resistant isolates; GLASS reports Resistant.</td>
                  <td>Numeric resistance levels must never be compared directly across sources.</td>
                </tr>
                <tr>
                  <td><strong>Short GLASS Horizon</strong></td>
                  <td>GLASS provides 6 annual rounds (2018–2023). Requiring lags consumes 2 years.</td>
                  <td>Restricted historical training window for non-European surveillance sites.</td>
                </tr>
                <tr>
                  <td><strong>Reporting Filter Bias</strong></td>
                  <td>GLASS participating sites reflect better-resourced tertiary hospital labs.</td>
                  <td>May over-represent complex hospital-acquired resistance vs community infections.</td>
                </tr>
                <tr>
                  <td><strong>Project-Defined Cutoffs</strong></td>
                  <td>Thresholds (T = 30%, +5 pp rise) are chosen for surveillance triage.</td>
                  <td>Cutoffs reflect surveillance alerting priorities, not clinical treatment thresholds.</td>
                </tr>
                <tr>
                  <td><strong>Small Sample Variance</strong></td>
                  <td>5.3% of GLASS rows have N &lt; 30 isolates.</td>
                  <td>Binomial volatility necessitates sample-size filtering for classification benchmarks.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: Phase 2 Roadmap */}
      {activeTab === 'phase2' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Phase 2 Technical Roadmap &amp; Extension Stubs</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 20 }}>
            Phase 1 provides tested interfaces and precomputed representations for subsequent Phase 2 research modules:
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
              <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
                1. SHAP TreeExplainers
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Local feature attribution explanations per surveillance series forecast.
              </p>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
              <div style={{ color: '#a855f7', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
                2. Conformal Prediction
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Distribution-free finite-sample prediction coverage bands with guaranteed risk calibration.
              </p>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
              <div style={{ color: '#34d399', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
                3. Trajectory Clustering
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Dynamic time warping (DTW) and unsupervised clustering of regional resistance paths.
              </p>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
              <div style={{ color: '#fbbf24', fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
                4. Change-Point Outbreak Detection
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                CUSUM and Isolation Forests for automated detection of sudden hospital transmission spikes.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: Provenance */}
      {activeTab === 'provenance' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 14 }}>System &amp; Data Provenance</h3>
          <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: 16, borderRadius: 8, fontFamily: 'monospace', fontSize: '0.8rem', color: '#e2e8f0' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(methods || {}, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Key Takeaway */}
      <div className="takeaway-box">
        <CheckCircle2 size={24} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4>Key Takeaway: Methodological Integrity</h4>
          <p>
            AMR-Sense decouples clinical prescribing from epidemiological surveillance. All metrics rely on strict temporal rolling-origin cross-validation, country-clustered bootstrap confidence intervals, and frozen one-shot test evaluations.
          </p>
        </div>
      </div>
    </div>
  );
}
