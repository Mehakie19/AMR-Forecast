import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Award, TrendingUp, Sliders, CheckCircle2, ChevronRight, BarChart2 } from 'lucide-react';

export default function ModelLab({ scope }) {
  const [config, setConfig] = useState('glass');
  const [target, setTarget] = useState('high_risk_next');
  const [split, setSplit] = useState('test');
  const [activeTab, setActiveTab] = useState('comparison');

  const [comparison, setComparison] = useState([]);
  const [curves, setCurves] = useState(null);
  const [selectedModel, setSelectedModel] = useState('xgb');
  const [regularization, setRegularization] = useState(null);
  const [tuning, setTuning] = useState(null);
  const [ensembles, setEnsembles] = useState(null);
  const [segments, setSegments] = useState(null);
  const [errors, setErrors] = useState(null);
  const [pooledVsSep, setPooledVsSep] = useState('');
  const [regressors, setRegressors] = useState([]);

  useEffect(() => {
    // Sync config if user changed scope
    if (scope === 'GLASS-AMR') setConfig('glass');
    else if (scope === 'ECDC-derived') setConfig('ecdc');
  }, [scope]);

  useEffect(() => {
    api.getResultsComparison(config, target, split)
      .then((data) => setComparison(data?.rows || []))
      .catch((err) => console.error(err));

    api.getResultsComparison(config, 'y_reg', split)
      .then((data) => setRegressors(data?.rows || []))
      .catch((err) => console.error(err));
  }, [config, target, split]);

  useEffect(() => {
    api.getResultsCurves(config, target, selectedModel)
      .then((data) => setCurves(data?.curves || null))
      .catch((err) => console.error(err));
  }, [config, target, selectedModel]);

  useEffect(() => {
    api.getResultsRegularization().then((d) => setRegularization(d)).catch(console.error);
    api.getResultsTuning(config).then((d) => setTuning(d)).catch(console.error);
    api.getResultsEnsembles(config).then((d) => setEnsembles(d)).catch(console.error);
    api.getResultsSegments(config, target).then((d) => setSegments(d)).catch(console.error);
    api.getResultsErrors(config).then((d) => setErrors(d)).catch(console.error);
    api.getResultsPooledVsSeparate().then((d) => setPooledVsSep(d?.markdown || '')).catch(console.error);
  }, [config, target]);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Model Lab — Rigorous Benchmarking &amp; Diagnostics
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Compare baselines, tuned tree ensembles, and time-safe stacking against paired country-cluster bootstrap CIs.
        </p>
      </div>

      {/* Top Filter Controls */}
      <div
        className="card"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 16,
          padding: '16px 20px',
          marginBottom: 24,
        }}
      >
        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>
            Model Configuration
          </label>
          <select
            className="form-select"
            value={config}
            onChange={(e) => setConfig(e.target.value)}
            style={{ marginTop: 4 }}
          >
            <option value="glass">GLASS-AMR (Dedicated)</option>
            <option value="ecdc">ECDC-derived (Dedicated)</option>
            <option value="pooled">Pooled (Combined with Source Flags)</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>
            Surveillance Target
          </label>
          <select
            className="form-select"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            style={{ marginTop: 4 }}
          >
            <option value="high_risk_next">High-Risk Next Year (T ≥ 30%)</option>
            <option value="rising_next">Rising Next Year (+5 pp &amp; p &lt; 0.05)</option>
            <option value="y_reg">Continuous Resistance % (Regression)</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>
            Evaluation Split
          </label>
          <select
            className="form-select"
            value={split}
            onChange={(e) => setSplit(e.target.value)}
            style={{ marginTop: 4 }}
          >
            <option value="test">Held-Out Test Set (Single-Shot FROZEN)</option>
            <option value="validation">Validation Split (Forward Rolling OOF)</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-header">
        {[
          { id: 'comparison', label: '1. Model Comparison' },
          { id: 'curves', label: '2. PR / ROC Curves' },
          { id: 'regularization', label: '3. Regularization Evidence' },
          { id: 'tuning', label: '4. Hyperparameter Tuning' },
          { id: 'ensembles', label: '5. Ensembles & Diversity' },
          { id: 'segments', label: '6. Segments' },
          { id: 'errors', label: '7. Error Analysis' },
          { id: 'pooling', label: '8. Thresholds & Pooling' },
          { id: 'regressors', label: '9. Companion Regressors' },
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

      {/* TAB 1: Comparison Table */}
      {activeTab === 'comparison' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: '1.15rem' }}>
                Benchmark Performance Table ({config.toUpperCase()} • {target} • {split.toUpperCase()})
              </h3>
              <span className="badge" style={{ background: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-cyan)' }}>
                Evaluation metrics
              </span>
            </div>

            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Model Family</th>
                    <th>PR-AUC (95% CI)</th>
                    <th>ROC-AUC</th>
                    <th>F1 Score</th>
                    <th>Sensitivity (Recall)</th>
                    <th>False-Alert Rate</th>
                    <th>Brier Score</th>
                    <th>Diff vs Baseline (95% CI)</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map((row) => {
                    const isBase = row.model?.toLowerCase().includes('baseline');
                    return (
                      <tr
                        key={row.model}
                        style={{
                          background: isBase ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
                          fontWeight: isBase ? 600 : 400,
                        }}
                      >
                        <td>
                          <span style={{ color: isBase ? '#94a3b8' : 'var(--accent-cyan)' }}>
                            {row.model}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600, color: '#fff' }}>
                          {row.pr_auc?.toFixed(4)}{' '}
                          {row.pr_auc_ci && (
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                              [{row.pr_auc_ci[1]?.toFixed(4)}, {row.pr_auc_ci[2]?.toFixed(4)}]
                            </span>
                          )}
                        </td>
                        <td>{row.roc_auc?.toFixed(4)}</td>
                        <td>{row.f1?.toFixed(3)}</td>
                        <td>{row.recall?.toFixed(3)}</td>
                        <td style={{ color: row.false_alert_rate > 0.15 ? '#f87171' : '#34d399' }}>
                          {row.false_alert_rate?.toFixed(3)}
                        </td>
                        <td>{row.brier?.toFixed(4)}</td>
                        <td style={{ color: isBase ? 'var(--text-dim)' : '#34d399', fontWeight: 600 }}>
                          {isBase
                            ? 'Reference'
                            : row.diff_ci
                            ? `${row.diff_ci[0] > 0 ? '+' : ''}${row.diff_ci[0]?.toFixed(4)} [${row.diff_ci[1]?.toFixed(4)}, ${row.diff_ci[2]?.toFixed(4)}]`
                            : 'Not available'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="explainer" style={{ marginTop: 16 }}>
              <strong>Glossary:</strong> PR-AUC = Area under Precision-Recall curve (primary for imbalanced surveillance alerts). False-Alert Rate = FP / (FP + TN). Bootstrap CIs resample countries with replacement to account for cross-sectional clustering.
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Curves */}
      {activeTab === 'curves' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: '1.15rem' }}>Precision-Recall &amp; Calibration Curves</h3>
            <select
              className="form-select"
              style={{ width: 180 }}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              <option value="xgb">XGBoost</option>
              <option value="rf">Random Forest</option>
              <option value="lr">Logistic Regression</option>
              <option value="voting">Soft Voting</option>
              <option value="stacking">Stacking Ensemble</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
            {/* PR Curve SVG */}
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: 16, borderRadius: 8 }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: 12, color: 'var(--accent-cyan)' }}>
                Precision-Recall Curve ({selectedModel})
              </h4>
              <div style={{ height: 200, position: 'relative' }}>
                <svg width="100%" height="100%" viewBox="0 0 300 180">
                  <line x1="30" y1="160" x2="280" y2="160" stroke="rgba(255,255,255,0.1)" />
                  <line x1="30" y1="20" x2="30" y2="160" stroke="rgba(255,255,255,0.1)" />
                  {curves?.pr_curve?.recall && (
                    <path
                      d={curves.pr_curve.recall.reduce((acc, r, i) => {
                        const p = curves.pr_curve.precision[i];
                        const x = 30 + r * 250;
                        const y = 160 - p * 140;
                        return `${acc} ${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                      }, '')}
                      fill="none"
                      stroke="var(--accent-cyan)"
                      strokeWidth="2.5"
                    />
                  )}
                  <text x="30" y="175" fill="var(--text-dim)" fontSize="10">0.0</text>
                  <text x="155" y="175" fill="var(--text-dim)" fontSize="10">Recall</text>
                  <text x="270" y="175" fill="var(--text-dim)" fontSize="10">1.0</text>
                  <text x="8" y="25" fill="var(--text-dim)" fontSize="10">1.0</text>
                  <text x="8" y="160" fill="var(--text-dim)" fontSize="10">0.0</text>
                </svg>
              </div>
            </div>

            {/* ROC Curve SVG */}
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: 16, borderRadius: 8 }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: 12, color: '#a855f7' }}>
                ROC Curve ({selectedModel})
              </h4>
              <div style={{ height: 200, position: 'relative' }}>
                <svg width="100%" height="100%" viewBox="0 0 300 180">
                  <line x1="30" y1="160" x2="280" y2="160" stroke="rgba(255,255,255,0.1)" />
                  <line x1="30" y1="20" x2="30" y2="160" stroke="rgba(255,255,255,0.1)" />
                  <line x1="30" y1="160" x2="280" y2="20" stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
                  {curves?.roc_curve?.fpr && (
                    <path
                      d={curves.roc_curve.fpr.reduce((acc, f, i) => {
                        const t = curves.roc_curve.tpr[i];
                        const x = 30 + f * 250;
                        const y = 160 - t * 140;
                        return `${acc} ${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                      }, '')}
                      fill="none"
                      stroke="#a855f7"
                      strokeWidth="2.5"
                    />
                  )}
                  <text x="30" y="175" fill="var(--text-dim)" fontSize="10">0.0</text>
                  <text x="155" y="175" fill="var(--text-dim)" fontSize="10">FPR</text>
                  <text x="270" y="175" fill="var(--text-dim)" fontSize="10">1.0</text>
                </svg>
              </div>
            </div>
          </div>
          <div className="result-grid" style={{ marginTop: 20 }}>
            <section className="result-panel">
              <h4>Calibration</h4>
              {curves?.calibration?.length ? <svg viewBox="0 0 300 230" role="img" aria-label="Calibration plot" style={{ width: '100%', height: 230 }}>
                <line x1="35" y1="190" x2="270" y2="190" stroke="rgba(255,255,255,.2)" />
                <line x1="35" y1="20" x2="35" y2="190" stroke="rgba(255,255,255,.2)" />
                <line x1="35" y1="190" x2="270" y2="20" stroke="rgba(255,255,255,.25)" strokeDasharray="5 4" />
                <path d={curves.calibration.map((point, index) => `${index ? 'L' : 'M'} ${35 + point.mean_pred * 235} ${190 - point.frac_pos * 170}`).join(' ')} fill="none" stroke="var(--accent-cyan)" strokeWidth="2.5" />
                {curves.calibration.map((point, index) => <circle key={index} cx={35 + point.mean_pred * 235} cy={190 - point.frac_pos * 170} r="4" fill="var(--accent-cyan)"><title>{`Predicted ${point.mean_pred.toFixed(2)}, observed ${point.frac_pos.toFixed(2)} (n=${point.count})`}</title></circle>)}
                <text x="125" y="218" fill="var(--text-muted)" fontSize="11">Mean predicted risk</text>
              </svg> : <p className="explainer">Calibration data is unavailable for this curve.</p>}
            </section>
            <section className="result-panel">
              <h4>Confusion matrix at selected threshold</h4>
              {curves?.confusion_matrix ? <div className="confusion-grid">
                <div><small>True negative</small><strong>{curves.confusion_matrix.tn}</strong></div>
                <div><small>False positive</small><strong>{curves.confusion_matrix.fp}</strong></div>
                <div><small>False negative</small><strong>{curves.confusion_matrix.fn}</strong></div>
                <div><small>True positive</small><strong>{curves.confusion_matrix.tp}</strong></div>
                <p>Threshold: {Number(curves.confusion_matrix.threshold).toFixed(2)}</p>
              </div> : <p className="explainer">Confusion matrix is unavailable for this curve.</p>}
            </section>
          </div>
        </div>
      )}

      {/* TAB 3: Regularization */}
      {activeTab === 'regularization' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>Regularization Evidence &amp; Overfitting Controls</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 20 }}>
            Evaluation of train vs. validation generalization gap across penalties (None, L1, L2, Elastic Net) and tree regularizers.
          </p>

          {regularization?.markdown ? <pre className="result-json">{regularization.markdown}</pre> : <p className="explainer">No regularization report is available in reports/results/regularization.md.</p>}
        </div>
      )}

      {activeTab === 'tuning' && <div className="card">
        <h3>Hyperparameter tuning</h3>
        <p className="explainer">Optuna artifacts are returned by the API when present. No study artifact is available for this configuration yet.</p>
        <pre className="result-json">{JSON.stringify(tuning?.study || {}, null, 2)}</pre>
      </div>}

      {activeTab === 'ensembles' && <div className="card">
        <h3>Ensemble methods</h3>
        <div className="result-grid">
          <section><h4>Soft voting</h4><p>{ensembles?.voting_description || 'Description unavailable.'}</p></section>
          <section><h4>Time safe stacking</h4><p>{ensembles?.stacking_description || 'Description unavailable.'}</p></section>
        </div>
      </div>}

      {activeTab === 'segments' && <div className="card">
        <h3>Performance by surveillance segment</h3>
        {segments?.segments && Object.entries(segments.segments).map(([group, rows]) => <section className="result-section" key={group}>
          <h4>{group}</h4><div className="data-table-container"><table className="data-table"><thead><tr><th>Segment</th><th>Rows</th><th>PR AUC</th><th>ROC AUC</th><th>Recall</th><th>False alert rate</th></tr></thead>
            <tbody>{rows.map((row) => <tr key={row.segment}><td>{row.segment}</td><td>{row.n_rows}</td><td>{row.pr_auc?.toFixed(3) ?? '—'}</td><td>{row.roc_auc?.toFixed(3) ?? '—'}</td><td>{row.recall?.toFixed(3) ?? '—'}</td><td>{row.false_alert_rate?.toFixed(3) ?? '—'}</td></tr>)}</tbody>
          </table></div>
        </section>)}
        {!segments?.segments && <p className="explainer">No segment results available for this selection.</p>}
      </div>}

      {activeTab === 'errors' && <div className="card">
        <h3>Forecast error review</h3>
        {errors?.errors?.largest_forecast_errors?.length ? <div className="data-table-container"><table className="data-table"><thead><tr><th>Source</th><th>Country</th><th>Year</th><th>Pathogen</th><th>Antibiotic</th><th>Observed</th><th>Forecast</th><th>Absolute error</th></tr></thead><tbody>
          {errors.errors.largest_forecast_errors.map((row, i) => <tr key={`${row.iso3}-${row.year}-${i}`}><td>{row.source}</td><td>{row.iso3}</td><td>{row.year}</td><td>{row.pathogen}</td><td>{row.antibiotic}</td><td>{row.y_reg?.toFixed(1)}%</td><td>{row.pred_reg?.toFixed(1)}%</td><td>{row.abs_error?.toFixed(1)} pp</td></tr>)}
        </tbody></table></div> : <p className="explainer">No error analysis is available for this configuration.</p>}
        {errors?.errors?.highest_confidence_false_alerts?.length > 0 && <section className="result-section">
          <h4>Highest confidence false alerts</h4>
          <div className="data-table-container"><table className="data-table"><thead><tr><th>Source</th><th>Country</th><th>Year</th><th>Pathogen</th><th>Antibiotic</th><th>Latest resistance</th><th>Next-year risk score</th></tr></thead><tbody>
            {errors.errors.highest_confidence_false_alerts.map((row, i) => <tr key={`${row.iso3}-${row.year}-${i}`}><td>{row.source}</td><td>{row.iso3}</td><td>{row.year}</td><td>{row.pathogen}</td><td>{row.antibiotic}</td><td>{row.lag_1?.toFixed(1)}%</td><td>{row.prob_high_risk_next != null ? `${(row.prob_high_risk_next * 100).toFixed(1)}%` : '—'}</td></tr>)}
          </tbody></table></div>
        </section>}
      </div>}

      {/* TAB 8: Thresholds & Pooling */}
      {activeTab === 'pooling' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Pooled vs. Dedicated Single-Source Evaluation</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Comparison on exact identical held-out test rows to answer: <em>Did combining GLASS and ECDC surveillance data help or hurt?</em>
          </p>
          <details className="explainer"><summary>Open current source-specific evaluation report</summary>
            <pre className="result-json">{pooledVsSep || 'No pooled comparison report is available.'}</pre>
          </details>

          <div className="data-table-container" style={{ marginBottom: 24 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Test Slice</th>
                  <th>Target</th>
                  <th>Dedicated Model PR-AUC (95% CI)</th>
                  <th>Pooled Model PR-AUC (95% CI)</th>
                  <th>Difference (Pooled - Ded) [95% CI]</th>
                  <th>Empirical Verdict</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>GLASS (2023)</strong></td>
                  <td>high_risk_next</td>
                  <td>0.9886 [0.9790, 0.9952]</td>
                  <td>0.9896 [0.9785, 0.9971]</td>
                  <td>+0.0010 [-0.0043, +0.0065]</td>
                  <td><span style={{ color: 'var(--text-muted)' }}>No significant difference</span></td>
                </tr>
                <tr>
                  <td><strong>ECDC (2018–2019)</strong></td>
                  <td>high_risk_next</td>
                  <td>0.9834 [0.9505, 0.9963]</td>
                  <td>0.9832 [0.9495, 0.9964]</td>
                  <td>-0.0003 [-0.0016, +0.0012]</td>
                  <td><span style={{ color: 'var(--text-muted)' }}>No significant difference</span></td>
                </tr>
                <tr>
                  <td><strong>GLASS (2023)</strong></td>
                  <td>rising_next</td>
                  <td>0.2561 [0.1418, 0.4538]</td>
                  <td>0.2522 [0.1439, 0.4231]</td>
                  <td>-0.0040 [-0.0621, +0.0398]</td>
                  <td><span style={{ color: 'var(--text-muted)' }}>No significant difference</span></td>
                </tr>
                <tr>
                  <td><strong>ECDC (2018–2019)</strong></td>
                  <td>rising_next</td>
                  <td>0.1172 [0.0826, 0.1896]</td>
                  <td>0.1694 [0.1243, 0.2508]</td>
                  <td style={{ color: '#34d399', fontWeight: 600 }}>+0.0522 [+0.0160, +0.0869]</td>
                  <td><span style={{ color: '#34d399', fontWeight: 700 }}>Pooling significantly helped ✅</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <h4 style={{ fontSize: '0.95rem', marginBottom: 10, color: 'var(--accent-cyan)' }}>
            Threshold Sensitivity Analysis (T = 20%, 30%, 50%)
          </h4>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Config</th>
                  <th>Threshold T</th>
                  <th>Test Prevalence</th>
                  <th>Persistence PR-AUC</th>
                  <th>LR PR-AUC</th>
                  <th>XGBoost PR-AUC</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>GLASS</td><td>T = 20%</td><td>68.4%</td><td>0.9674</td><td>0.9927</td><td>0.9920</td></tr>
                <tr><td>GLASS</td><td>T = 30%</td><td>58.5%</td><td>0.9527</td><td>0.9886</td><td>0.9890</td></tr>
                <tr><td>GLASS</td><td>T = 50%</td><td>40.2%</td><td>0.8698</td><td>0.9698</td><td>0.9616</td></tr>
                <tr><td>ECDC</td><td>T = 20%</td><td>41.4%</td><td>0.9039</td><td>0.9809</td><td>0.9785</td></tr>
                <tr><td>ECDC</td><td>T = 30%</td><td>33.4%</td><td>0.9298</td><td>0.9834</td><td>0.9829</td></tr>
                <tr><td>ECDC</td><td>T = 50%</td><td>20.9%</td><td>0.9172</td><td>0.9777</td><td>0.7810</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 9: Companion Regressors */}
      {activeTab === 'regressors' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>Companion Continuous Percentage Regressors</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>MAE (pp)</th>
                  <th>RMSE (pp)</th>
                  <th>Beat Persistence Share</th>
                </tr>
              </thead>
              <tbody>
                {regressors.map((r) => (
                  <tr key={r.model}>
                    <td><strong>{r.model}</strong></td>
                    <td style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{r.mae?.toFixed(3)} pp</td>
                    <td>{r.rmse?.toFixed(3)} pp</td>
                    <td>{r.beat_persistence_share ? `${(r.beat_persistence_share * 100).toFixed(1)}%` : '0.0%'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="explainer" style={{ marginTop: 14 }}>
            Persistence is an exceptionally tough regression baseline (MAE 3.06 pp in ECDC, 4.71 pp in GLASS). ML regressors outperform persistence on ~42–46% of volatile series.
          </div>
        </div>
      )}

      {/* Key Takeaway */}
      <div className="takeaway-box">
        <CheckCircle2 size={24} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4>Key Takeaway: ML Beats Baselines with Statistically Positive CIs</h4>
          <p>
            On held-out test data, tuned ML classifiers beat persistence baseline on PR-AUC with 95% confidence (GLASS High-Risk diff: +0.0381 [+0.0163, +0.0646]; GLASS Rising diff: +0.1486 [+0.0620, +0.2969]). On ECDC rising acceleration, pooling with source flags significantly improved detection precision (+0.0522 [+0.0160, +0.0869]).
          </p>
        </div>
      </div>
    </div>
  );
}
