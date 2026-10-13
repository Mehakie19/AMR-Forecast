import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { TrendingUp, AlertTriangle, ShieldAlert, Sparkles, CheckCircle2 } from 'lucide-react';

export default function ForecastExplorer({ scope, source }) {
  const [selectedSource, setSelectedSource] = useState('glass');
  const [iso3, setIso3] = useState('ARE');
  const [pathogen, setPathogen] = useState('Escherichia coli');
  const [antibiotic, setAntibiotic] = useState('Ciprofloxacin');
  const [modelConfig, setModelConfig] = useState('glass');

  const [history, setHistory] = useState([]);
  const [seriesOptions, setSeriesOptions] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  const availCountries = [...new Set(seriesOptions.map((item) => item.iso3))];
  const availablePathogens = [...new Set(seriesOptions.filter((item) => item.iso3 === iso3).map((item) => item.pathogen))];
  const availableAntibiotics = [...new Set(seriesOptions.filter((item) => item.iso3 === iso3 && item.pathogen === pathogen).map((item) => item.antibiotic))];

  useEffect(() => {
    if (scope === 'GLASS-AMR') setSelectedSource('glass');
    else if (scope === 'ECDC-derived') setSelectedSource('ecdc');
  }, [scope]);

  useEffect(() => {
    setModelConfig(selectedSource);
    api.getSeriesOptions(selectedSource).then((data) => setSeriesOptions(data?.items || [])).catch((err) => console.error(err));
  }, [selectedSource]);

  useEffect(() => {
    if (availCountries.length && !availCountries.includes(iso3)) setIso3(availCountries[0]);
  }, [availCountries.join('|')]);
  useEffect(() => {
    if (availablePathogens.length && !availablePathogens.includes(pathogen)) setPathogen(availablePathogens[0]);
  }, [availablePathogens.join('|')]);
  useEffect(() => {
    if (availableAntibiotics.length && !availableAntibiotics.includes(antibiotic)) setAntibiotic(availableAntibiotics[0]);
  }, [availableAntibiotics.join('|')]);

  useEffect(() => {
    setLoading(true);
    api.getSeriesHistory(selectedSource, iso3, pathogen, antibiotic)
      .then((data) => setHistory(data?.history || data?.records || []))
      .catch((err) => console.error(err));

    api.predictSeries({
      source: selectedSource,
      iso3,
      pathogen,
      antibiotic,
      model_config: modelConfig,
    })
      .then((pred) => setPrediction(pred))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [selectedSource, iso3, pathogen, antibiotic, modelConfig]);

  const lastObs = history[history.length - 1];
  const lastYear = lastObs?.year || 2023;
  const targetYear = lastYear + 1;
  const forecastVal = prediction?.forecast_pct ?? lastObs?.pct_resistant ?? 0;
  const persVal = lastObs?.pct_resistant ?? 0;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Interactive Surveillance Forecast Explorer
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Real-time next-year predictive inference synthesising temporal inertia, sample volatility, and cross-resistance context.
        </p>
      </div>

      {/* Selectors Bar */}
      <div
        className="card"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 14,
          padding: '16px 20px',
          marginBottom: 24,
        }}
      >
        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>SOURCE SYSTEM</label>
          <select
            className="form-select"
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
          >
            <option value="glass">WHO GLASS-AMR</option>
            <option value="ecdc">ECDC EARS-Net</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>COUNTRY (ISO3)</label>
          <select
            className="form-select"
            value={iso3}
            onChange={(e) => setIso3(e.target.value)}
          >
            {availCountries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>PATHOGEN</label>
          <select
            className="form-select"
            value={pathogen}
            onChange={(e) => setPathogen(e.target.value)}
          >
            {availablePathogens.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>ANTIBIOTIC TARGET</label>
          <select
            className="form-select"
            value={antibiotic}
            onChange={(e) => setAntibiotic(e.target.value)}
          >
            {availableAntibiotics.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>MODEL SUITE</label>
          <select
            className="form-select"
            value={modelConfig}
            onChange={(e) => setModelConfig(e.target.value)}
          >
            <option value={selectedSource}>{selectedSource.toUpperCase()} Dedicated</option>
            <option value="pooled">Pooled Ensemble</option>
          </select>
        </div>
      </div>

      {/* Main Trajectory Visualizer */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>
              Surveillance Trajectory: <span style={{ color: 'var(--accent-cyan)' }}>{iso3}</span> — {pathogen} / {antibiotic}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Historical annual observations + Machine Learning forecast for year {targetYear}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: '0.78rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6' }} />
              Observed (N ≥ 30)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', border: '2px solid #ef4444' }} />
              Low sample (N &lt; 30)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 2, background: '#10b981' }} />
              ML Forecast
            </span>
          </div>
        </div>

        {/* SVG Interactive Trajectory Chart */}
        <div style={{ position: 'relative', height: 260, background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '20px 20px 30px' }}>
          <svg width="100%" height="100%" viewBox="0 0 760 200">
            {/* Gridlines */}
            {[0, 25, 50, 75, 100].map((v) => (
              <line
                key={v}
                x1="40"
                y1={170 - v * 1.5}
                x2="740"
                y2={170 - v * 1.5}
                stroke="rgba(255,255,255,0.06)"
                strokeDasharray="4 4"
              />
            ))}

            {/* Connecting historical line */}
            {history.length > 1 && (
              <path
                d={history.reduce((acc, pt, idx) => {
                  const x = 50 + (idx / history.length) * 580;
                  const y = 170 - Math.min(100, pt.pct_resistant) * 1.5;
                  return `${acc} ${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
                }, '')}
                fill="none"
                stroke="#3b82f6"
                strokeWidth="2.5"
              />
            )}

            {/* Forecast dashed projection line */}
            {history.length > 0 && (
              <line
                x1={50 + ((history.length - 1) / history.length) * 580}
                y1={170 - Math.min(100, persVal) * 1.5}
                x2={690}
                y2={170 - Math.min(100, forecastVal) * 1.5}
                stroke="#10b981"
                strokeWidth="3"
                strokeDasharray="6 4"
              />
            )}

            {/* Historical Points */}
            {history.map((pt, idx) => {
              const x = 50 + (idx / history.length) * 580;
              const y = 170 - Math.min(100, pt.pct_resistant) * 1.5;
              const isNoisy = pt.number_tested < 30;
              const r = Math.min(9, Math.max(4, Math.sqrt(pt.number_tested || 30) / 2));
              return (
                <g key={pt.year}>
                  {isNoisy ? (
                    <circle cx={x} cy={y} r={r} fill="transparent" stroke="#ef4444" strokeWidth="2.5" />
                  ) : (
                    <circle cx={x} cy={y} r={r} fill="#3b82f6" stroke="#fff" strokeWidth="1.5" />
                  )}
                  <text x={x} y="190" fill="var(--text-dim)" fontSize="11" textAnchor="middle">
                    {pt.year}
                  </text>
                  <text x={x} y={y - 12} fill="#fff" fontSize="10" fontWeight="600" textAnchor="middle">
                    {pt.pct_resistant.toFixed(1)}%
                  </text>
                </g>
              );
            })}

            {/* Forecast Star Marker */}
            {prediction && (
              <g>
                <circle cx="690" cy={170 - Math.min(100, forecastVal) * 1.5} r="7" fill="#10b981" stroke="#fff" strokeWidth="2" />
                <text x="690" y="190" fill="#34d399" fontSize="11" fontWeight="700" textAnchor="middle">
                  {targetYear} (FC)
                </text>
                <text x="690" y={170 - Math.min(100, forecastVal) * 1.5 - 12} fill="#34d399" fontSize="11" fontWeight="700" textAnchor="middle">
                  {forecastVal.toFixed(1)}%
                </text>
              </g>
            )}
          </svg>
        </div>

        <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: 12, textAlign: 'center' }}>
          ⚠️ Surveillance and research forecast only. Not for clinical treatment or antibiotic dose selection.
        </div>
      </div>

      {/* Surveillance Alert Probability Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
        {/* High Risk Alarm */}
        <div
          className="card"
          style={{
            borderLeft: `4px solid ${prediction?.high_risk_probability >= 0.4 ? '#f43f5e' : '#10b981'}`,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>HIGH-RISK ALARM PROBABILITY</div>
              <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#fff', margin: '6px 0' }}>
                {prediction ? `${(prediction.high_risk_probability * 100).toFixed(1)}%` : '--'}
              </div>
            </div>
            <span
              className="badge"
              style={{
                background: prediction?.high_risk_probability >= 0.4 ? 'rgba(244, 63, 94, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: prediction?.high_risk_probability >= 0.4 ? '#f87171' : '#34d399',
              }}
            >
              Cutoff: 30%
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: prediction?.high_risk_probability >= 0.4 ? '#fca5a5' : '#a7f3d0' }}>
            {prediction?.high_risk_probability >= 0.4
              ? '⚠️ Above review threshold — candidate for audit'
              : '✅ Below surveillance review threshold'}
          </div>
        </div>

        {/* Rising Acceleration Alarm */}
        <div
          className="card"
          style={{
            borderLeft: `4px solid ${prediction?.rising_probability >= 0.2 ? '#f59e0b' : '#10b981'}`,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>RISING ACCELERATION PROBABILITY</div>
              <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#fff', margin: '6px 0' }}>
                {prediction ? `${(prediction.rising_probability * 100).toFixed(1)}%` : '--'}
              </div>
            </div>
            <span
              className="badge"
              style={{
                background: prediction?.rising_probability >= 0.2 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: prediction?.rising_probability >= 0.2 ? '#fbbf24' : '#34d399',
              }}
            >
              +5 pp &amp; p &lt; 0.05
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: prediction?.rising_probability >= 0.2 ? '#fde68a' : '#a7f3d0' }}>
            {prediction?.rising_probability >= 0.2
              ? '⚡ Acceleration signal detected — potential outbreak cluster'
              : '✅ Stable trajectory (no significant acceleration)'}
          </div>
        </div>

        {/* Companion Point Forecast */}
        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>NEXT-YEAR POINT FORECAST</div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--accent-cyan)', margin: '6px 0' }}>
            {forecastVal.toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Persistence: {persVal.toFixed(1)}% ({forecastVal >= persVal ? `+${(forecastVal - persVal).toFixed(1)}` : (forecastVal - persVal).toFixed(1)} pp)
          </div>
        </div>
      </div>

      {/* Feature Context & Cross-Resistance Profile */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
        {/* Features Inspector */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14 }}>Feature Vector Values (Year {lastYear})</h3>
          <div className="data-table-container">
            <table className="data-table" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {prediction?.features && Object.keys(prediction.features).length ? (
                  Object.entries(prediction.features).map(([k, v]) => (
                    <tr key={k}>
                      <td><code>{k}</code></td>
                      <td style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                        {typeof v === 'number' ? v.toFixed(3) : String(v)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={2}>No features available</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Cross-Resistance Profile Bar Chart */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14 }}>
            Co-Resistance Profile: {pathogen} in {iso3}
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Resistance across related antibiotic classes for this pathogen in the latest observed surveillance year.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {prediction?.cross_resistance_context?.length ? (
              prediction.cross_resistance_context.map(({ antibiotic: abx, pct_resistant: val, number_tested: n }) => (
                <div key={abx} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 110, fontSize: '0.78rem', color: '#fff' }}>{abx}</div>
                  <div style={{ flex: 1, height: 16, background: 'rgba(255,255,255,0.04)', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, val)}%`,
                        background: val >= 30 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #06b6d4, #3b82f6)',
                        borderRadius: 4,
                      }}
                    />
                  </div>
                  <div style={{ width: 66, fontSize: '0.78rem', textAlign: 'right', fontWeight: 600, color: val >= 30 ? '#f87171' : 'var(--accent-cyan)' }}>
                    {val.toFixed(1)}% <small style={{ color: 'var(--text-dim)' }}>n={n}</small>
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No co-resistance data available</p>
            )}
          </div>
        </div>
      </div>

      {/* Key Takeaway */}
      <div className="takeaway-box">
        <CheckCircle2 size={24} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4>Key Takeaway: Calibrated Surveillance Alerting</h4>
          <p>
            Predicted probabilities quantify surveillance triage priority based on historical lag, multi-drug resistance burden, and peer regional deviations. The predicted alerts represent early public health triggers rather than clinical prescribing decisions.
          </p>
        </div>
      </div>
    </div>
  );
}
