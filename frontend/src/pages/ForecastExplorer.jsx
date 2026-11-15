import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { TrendingUp, AlertTriangle, ShieldAlert, Sparkles } from 'lucide-react';

export default function ForecastExplorer({ scope, source }) {
  const [selectedSource, setSelectedSource] = useState('glass');
  const [iso3, setIso3] = useState('ARE');
  const [pathogen, setPathogen] = useState('Escherichia coli');
  const [antibiotic, setAntibiotic] = useState('Ciprofloxacin');
  const [modelConfig, setModelConfig] = useState('glass');

  const [history, setHistory] = useState([]);
  const [seriesOptions, setSeriesOptions] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [predictionError, setPredictionError] = useState(null);
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
    setPrediction(null);
    setPredictionError(null);
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
      .catch((err) => {
        console.error(err);
        setPredictionError(err.message);
      })
      .finally(() => setLoading(false));
  }, [selectedSource, iso3, pathogen, antibiotic, modelConfig]);

  const lastObs = history[history.length - 1];
  const lastYear = lastObs?.year || 2023;
  const targetYear = lastYear + 1;
  const persVal = lastObs?.pct_resistant ?? 0;
  const hasForecast = Number.isFinite(prediction?.forecast_pct);
  const forecastVal = hasForecast ? prediction.forecast_pct : 0;
  const forecastRows = prediction?.forecast_horizons || [];
  const resistanceThreshold = prediction?.high_resistance_threshold_pct ?? 40;
  const allChartYears = [
    ...history.map((point) => point.year),
    ...forecastRows.filter((point) => Number.isFinite(point.forecast_pct)).map((point) => point.year),
  ];
  const chartMinYear = allChartYears.length ? Math.min(...allChartYears) : lastYear;
  const chartMaxYear = allChartYears.length ? Math.max(...allChartYears) : lastYear + 5;
  const chartX = (year) => 50 + ((year - chartMinYear) / Math.max(1, chartMaxYear - chartMinYear)) * 650;
  const chartY = (value) => 170 - Math.max(0, Math.min(100, value)) * 1.5;
  const historyPath = history.map((point) => `${chartX(point.year)},${chartY(point.pct_resistant)}`).join(' ');
  const forecastPoints = [
    ...(lastObs ? [{ year: lastYear, pct_resistant: persVal }] : []),
    ...forecastRows.filter((point) => Number.isFinite(point.forecast_pct))
      .map((point) => ({ year: point.year, pct_resistant: point.forecast_pct })),
  ];
  const forecastPath = forecastPoints.map((point) => `${chartX(point.year)},${chartY(point.pct_resistant)}`).join(' ');

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Explore a five-year forecast
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Choose a source and surveillance series to compare reported history with a separate direct model estimate for each of the next five years.
        </p>
      </div>
      {predictionError && (
        <div
          role="alert"
          style={{
            marginBottom: 20,
            padding: '12px 16px',
            border: '1px solid rgba(248, 113, 113, 0.4)',
            borderRadius: 8,
            background: 'rgba(127, 29, 29, 0.2)',
            color: '#fecaca',
          }}
        >
          <strong>Prediction unavailable:</strong> {predictionError}
        </div>
      )}

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
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>DATA SOURCE</label>
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
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }} title="ISO3 is the standard three-letter country code">COUNTRY</label>
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
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }} title="The bacterium being monitored">PATHOGEN</label>
          <select
            className="form-select"
            value={pathogen}
            onChange={(e) => setPathogen(e.target.value)}
          >
            {availablePathogens.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>ANTIBIOTIC</label>
          <select
            className="form-select"
            value={antibiotic}
            onChange={(e) => setAntibiotic(e.target.value)}
          >
            {availableAntibiotics.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }} title="A dedicated model uses one source; a pooled model uses data from both sources">MODEL</label>
          <select
            className="form-select"
            value={modelConfig}
            onChange={(e) => setModelConfig(e.target.value)}
          >
            <option value={selectedSource}>{selectedSource.toUpperCase()} Dedicated</option>
            <option value="pooled">Pooled model</option>
          </select>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>
              Reported history: <span style={{ color: 'var(--accent-cyan)' }}>{iso3}</span> — {pathogen} / {antibiotic}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Reported values through {lastYear}; separate estimates for {targetYear}–{lastYear + 5}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: '0.78rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6' }} />
              30+ tests
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', border: '2px solid #ef4444' }} />
              Fewer than 30 tests
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 2, background: '#10b981' }} />
              Direct model forecast
            </span>
          </div>
        </div>

        <div style={{ position: 'relative', height: 260, background: 'rgba(15, 23, 42, 0.5)', borderRadius: 8, padding: '20px 20px 30px' }}>
          <svg width="100%" height="100%" viewBox="0 0 760 200" role="img" aria-label="Reported resistance and five-year resistance forecast">
            {[0, 25, 50, 75, 100].map((value) => (
              <g key={value}>
                <line x1="40" y1={chartY(value)} x2="740" y2={chartY(value)} stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                <text x="34" y={chartY(value) + 4} fill="var(--text-dim)" fontSize="9" textAnchor="end">{value}%</text>
              </g>
            ))}

            {history.length > 1 && (
              <polyline points={historyPath} fill="none" stroke="#3b82f6" strokeWidth="2.5" />
            )}
            {forecastPoints.length > 1 && (
              <polyline points={forecastPath} fill="none" stroke="#10b981" strokeWidth="3" strokeDasharray="7 5" />
            )}

            {history.map((point) => {
              const x = chartX(point.year);
              const y = chartY(point.pct_resistant);
              const smallSample = point.number_tested < 30;
              const radius = Math.min(9, Math.max(4, Math.sqrt(point.number_tested || 30) / 2));
              return (
                <g key={point.year}>
                  <circle cx={x} cy={y} r={radius} fill={smallSample ? 'transparent' : '#3b82f6'} stroke={smallSample ? '#ef4444' : '#fff'} strokeWidth="1.7" />
                  <text x={x} y="190" fill="var(--text-dim)" fontSize="10" textAnchor="middle">{point.year}</text>
                  <text x={x} y={y - 10} fill="#fff" fontSize="9" fontWeight="600" textAnchor="middle">{point.pct_resistant.toFixed(1)}%</text>
                </g>
              );
            })}

            {forecastRows.filter((point) => Number.isFinite(point.forecast_pct)).map((point) => {
              const x = chartX(point.year);
              const y = chartY(point.forecast_pct);
              return (
                <g key={point.year}>
                  <circle cx={x} cy={y} r="5.5" fill="#10b981" stroke="#fff" strokeWidth="1.5" />
                  <text x={x} y="190" fill="#34d399" fontSize="10" fontWeight="700" textAnchor="middle">{point.year}</text>
                  <text x={x} y={y - 10} fill="#34d399" fontSize="9" fontWeight="700" textAnchor="middle">{point.forecast_pct.toFixed(1)}%</text>
                </g>
              );
            })}
          </svg>
        </div>

        <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: 12, textAlign: 'center' }}>
          Each year is predicted independently from historical surveillance data; estimates are not chained together. Research use only, not treatment advice.
        </div>

        <div className="data-table-container" style={{ marginTop: 18 }}>
          <table className="data-table">
            <thead>
              <tr><th>Year</th><th>Estimated resistance</th><th>Category ({resistanceThreshold}% cutoff)</th><th>Historical check</th></tr>
            </thead>
            <tbody>
              {forecastRows.map((point) => (
                <tr key={point.year}>
                  <td>{point.year}</td>
                  <td>{Number.isFinite(point.forecast_pct) ? `${point.forecast_pct.toFixed(1)}%` : 'Unavailable'}</td>
                  <td>
                    {point.category ? (
                      <span className="badge" style={{
                        background: point.category === 'High Resistance' ? 'rgba(244, 63, 94, .16)' : 'rgba(16, 185, 129, .16)',
                        color: point.category === 'High Resistance' ? '#fda4af' : '#6ee7b7',
                      }}>
                        {point.category}
                      </span>
                    ) : 'Not available'}
                  </td>
                  <td>
                    {point.evaluation ? (
                      <span title={`Compared with carrying forward the previous resistance value; ${point.evaluation.holdout_samples} held-out reports from ${point.evaluation.holdout_year}.`}>
                        MAE {point.evaluation.holdout_mae_pct.toFixed(1)} pp vs {point.evaluation.persistence_mae_pct.toFixed(1)} pp baseline
                        {point.evaluation.beats_persistence ? ' · better' : ' · not better'}
                      </span>
                    ) : 'No separate time holdout'}
                  </td>
                </tr>
              ))}
              {!forecastRows.length && <tr><td colSpan={4}>Forecasts are not available for this series.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="explainer" style={{ marginTop: 12 }}>
          Low Resistance means below {resistanceThreshold}% and High Resistance means {resistanceThreshold}% or above.
          The historical check uses the latest available year as a time-ordered holdout; a model can perform worse than
          carrying the last report forward. “No separate time holdout” means there are not enough distinct target years
          to test that horizon.
        </p>
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
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>ESTIMATED CHANCE OF THE HIGH-RISK CATEGORY</div>
              <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#fff', margin: '6px 0' }}>
                {prediction ? `${(prediction.high_risk_probability * 100).toFixed(1)}%` : '--'}
              </div>
            </div>
            <span
              className="badge"
              style={{
                background: !prediction ? 'rgba(255, 255, 255, 0.08)' : prediction.high_risk_probability >= 0.4 ? 'rgba(244, 63, 94, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: !prediction ? 'var(--text-dim)' : prediction.high_risk_probability >= 0.4 ? '#f87171' : '#34d399',
              }}
            >
              Model label: project-defined 30%+ category
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: !prediction ? 'var(--text-dim)' : prediction.high_risk_probability >= 0.4 ? '#fca5a5' : '#a7f3d0' }}>
            {!prediction
              ? 'Prediction unavailable'
              : prediction.high_risk_probability >= 0.4
                ? 'Above the 40% review score — check the underlying reports'
                : 'Below the 40% review score'}
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
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>ESTIMATED CHANCE OF A SIGNIFICANT RISE</div>
              <div style={{ fontSize: '1.85rem', fontWeight: 700, color: '#fff', margin: '6px 0' }}>
                {prediction ? `${(prediction.rising_probability * 100).toFixed(1)}%` : '--'}
              </div>
            </div>
            <span
              className="badge"
              style={{
                background: !prediction ? 'rgba(255, 255, 255, 0.08)' : prediction.rising_probability >= 0.2 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: !prediction ? 'var(--text-dim)' : prediction.rising_probability >= 0.2 ? '#fbbf24' : '#34d399',
              }}
            >
              +5 points, statistical test, 30+ tests
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: !prediction ? 'var(--text-dim)' : prediction.rising_probability >= 0.2 ? '#fde68a' : '#a7f3d0' }}>
            {!prediction
              ? 'Prediction unavailable'
              : prediction.rising_probability >= 0.2
                ? 'Above the 20% review score — check the underlying reports'
                : 'Below the 20% review score'}
          </div>
        </div>

        {/* Companion Point Forecast */}
        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>NEXT-YEAR DIRECT ESTIMATE</div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--accent-cyan)', margin: '6px 0' }}>
            {hasForecast ? `${forecastVal.toFixed(1)}%` : 'Unavailable'}
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {hasForecast
              ? `Last reported: ${persVal.toFixed(1)}% · change from last report: ${forecastVal >= persVal ? '+' : ''}${(forecastVal - persVal).toFixed(1)} percentage points`
              : `Last reported: ${persVal.toFixed(1)}%`}
          </div>
        </div>
      </div>

      {/* Feature Context & Cross-Resistance Profile */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
        {/* Features Inspector */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14 }}>Information available through {lastYear}</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>These input values summarize available history; they are not separate test results.</p>
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

        {/* Other antibiotic resistance values */}
        <div className="card">
          <h3 style={{ fontSize: '1.05rem', marginBottom: 14 }}>
          Other antibiotic resistance: {pathogen} in {iso3}
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Latest reported resistance percentages for this pathogen and other antibiotics in the selected source.
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

    </div>
  );
}
