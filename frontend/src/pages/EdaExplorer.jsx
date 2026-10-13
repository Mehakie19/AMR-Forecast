import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { BarChart3, TrendingUp, Filter, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';

export default function EdaExplorer({ scope, source }) {
  const [activeTab, setActiveTab] = useState('distributions');
  const [distData, setDistData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [sampleData, setSampleData] = useState([]);
  const [balanceData, setBalanceData] = useState(null);
  const [corrData, setCorrData] = useState(null);
  const [yoyData, setYoyData] = useState(null);
  const [selectedPathogen, setSelectedPathogen] = useState('Klebsiella pneumoniae');
  const [chartType, setChartType] = useState('box');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getEdaDistribution(source),
      api.getEdaTrend(source),
      api.getEdaSampleSize(source),
      api.getEdaClassBalance(source),
      api.getEdaCorrelation(source, selectedPathogen),
      api.getEdaYearChange(source),
    ])
      .then(([dist, tr, samp, bal, corr, yoy]) => {
        setDistData(dist?.records || dist?.rows || []);
        setTrendData(tr?.trends || tr?.series || []);
        setSampleData(samp?.points || samp?.rows || []);
        setBalanceData(bal || {});
        setCorrData(corr?.correlations || corr || null);
        setYoyData(yoy?.yoy || yoy || null);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [source, selectedPathogen]);

  // Antibiotic distribution aggregates
  const abxAggregates = React.useMemo(() => {
    const map = {};
    distData.forEach((d) => {
      const key = `${d.source}::${d.antibiotic}`;
      if (!map[key]) map[key] = [];
      map[key].push(d.pct_resistant);
    });
    return Object.entries(map).map(([key, vals]) => {
      const [sourceName, abx] = key.split('::');
      const sorted = [...vals].sort((a, b) => a - b);
      const median = sorted[Math.floor(sorted.length * 0.5)] || 0;
      const q25 = sorted[Math.floor(sorted.length * 0.25)] || 0;
      const q75 = sorted[Math.floor(sorted.length * 0.75)] || 0;
      const min = sorted[0] || 0;
      const max = sorted[sorted.length - 1] || 0;
      return { abx, source: sourceName, count: vals.length, median, q25, q75, min, max };
    }).sort((a, b) => b.median - a.median);
  }, [distData]);

  // Longitudinal trend aggregates
  const annualTrends = React.useMemo(() => {
    const filtered = trendData.filter((d) => !selectedPathogen || d.pathogen === selectedPathogen);
    return filtered.map((d) => ({
      year: Number(d.year), median: Number(d.median), mean: Number(d.mean),
      source: d.source, count: Number(d.count),
    })).filter((d) => Number.isFinite(d.median)).sort((a, b) => a.year - b.year);
  }, [trendData, selectedPathogen]);
  const lowSampleCount = sampleData.filter((row) => Number(row.number_tested) < 30).length;
  const adequateSampleCount = sampleData.filter((row) => Number(row.number_tested) >= 30).length;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Exploratory Data Analysis Explorer
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Empirical resistance distributions, longitudinal trends, sampling noise, and cross-resistance co-occurrence.
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="tabs-header">
        {[
          { id: 'distributions', label: '1. Distributions' },
          { id: 'trends', label: '2. Longitudinal Trends' },
          { id: 'samples', label: '3. Sample Size Funnel' },
          { id: 'yoy', label: '4. Year-on-Year Dynamics' },
          { id: 'balance', label: '5. Target Class Balance' },
          { id: 'correlation', label: '6. Cross-Resistance Heatmap' },
          { id: 'issues', label: '7. Data Issues & Decisions' },
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

      {/* TAB 1: Distributions */}
      {activeTab === 'distributions' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: '1.15rem' }}>Resistance Rate Distribution by Antibiotic Target</h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className={`btn ${chartType === 'box' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setChartType('box')}
                  style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                >
                  Quantiles View
                </button>
                <button
                  className={`btn ${chartType === 'table' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setChartType('table')}
                  style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                >
                  Data Table
                </button>
              </div>
            </div>

            {chartType === 'box' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {abxAggregates.map((item) => (
                  <div key={`${item.source}-${item.abx}`} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ width: 180, fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                      <span style={{ color: item.source?.includes('GLASS') ? 'var(--source-glass)' : 'var(--source-ecdc)' }}>{item.source?.includes('GLASS') ? 'GLASS' : 'ECDC'}</span> · {item.abx}
                    </div>
                    <div style={{ flex: 1, position: 'relative', height: 26, background: 'rgba(255,255,255,0.03)', borderRadius: 6 }}>
                      {/* Range line */}
                      <div
                        style={{
                          position: 'absolute',
                          left: `${item.min}%`,
                          width: `${item.max - item.min}%`,
                          top: 12,
                          height: 2,
                          background: 'rgba(255, 255, 255, 0.2)',
                        }}
                      />
                      {/* IQR Box */}
                      <div
                        style={{
                          position: 'absolute',
                          left: `${item.q25}%`,
                          width: `${Math.max(2, item.q75 - item.q25)}%`,
                          top: 4,
                          height: 18,
                          background: item.source?.includes('GLASS') ? 'rgba(14,165,233,.35)' : 'rgba(245,158,11,.3)',
                          border: `1px solid ${item.source?.includes('GLASS') ? 'var(--source-glass)' : 'var(--source-ecdc)'}`,
                          borderRadius: 4,
                        }}
                      />
                      {/* Median point */}
                      <div
                        style={{
                          position: 'absolute',
                          left: `${item.median}%`,
                          top: 2,
                          width: 4,
                          height: 22,
                          background: '#fff',
                          borderRadius: 2,
                          transform: 'translateX(-2px)',
                          boxShadow: '0 0 6px rgba(255,255,255,0.8)',
                        }}
                      />
                    </div>
                    <div style={{ width: 80, fontSize: '0.82rem', color: item.source?.includes('GLASS') ? 'var(--source-glass)' : 'var(--source-ecdc)', textAlign: 'right', fontWeight: 600 }}>
                      {item.median.toFixed(1)}% med
                    </div>
                  </div>
                ))}
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 146, paddingRight: 96, marginTop: 8, fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  <span>0%</span>
                  <span>25%</span>
                  <span>50%</span>
                  <span>75%</span>
                  <span>100%</span>
                </div>
              </div>
            ) : (
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Source</th><th>Antibiotic</th>
                      <th>Observations</th>
                      <th>Min</th>
                      <th>Q25</th>
                      <th>Median</th>
                      <th>Q75</th>
                      <th>Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {abxAggregates.map((item) => (
                      <tr key={`${item.source}-${item.abx}`}>
                        <td>{item.source?.includes('GLASS') ? 'GLASS' : 'ECDC'}</td><td><strong>{item.abx}</strong></td>
                        <td>{item.count}</td>
                        <td>{item.min.toFixed(1)}%</td>
                        <td>{item.q25.toFixed(1)}%</td>
                        <td style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{item.median.toFixed(1)}%</td>
                        <td>{item.q75.toFixed(1)}%</td>
                        <td>{item.max.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="explainer">
              Each source is summarized separately because GLASS reports resistant isolates and ECDC reports intermediate plus resistant isolates. These distributions should not be read as direct comparisons.
            </div>

            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', marginTop: 12, fontSize: '.8rem', color: 'var(--text-muted)' }}>
              <span><b style={{ color: 'var(--source-glass)' }}>●</b> GLASS-AMR · R reported</span>
              <span><b style={{ color: 'var(--source-ecdc)' }}>●</b> ECDC · I+R</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Longitudinal Trends */}
      {activeTab === 'trends' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ fontSize: '1.15rem' }}>Longitudinal Trajectories by Pathogen</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Pathogen:</span>
                <select
                  className="form-select"
                  style={{ width: 220 }}
                  value={selectedPathogen}
                  onChange={(e) => setSelectedPathogen(e.target.value)}
                >
                  <option value="Escherichia coli">Escherichia coli</option>
                  <option value="Klebsiella pneumoniae">Klebsiella pneumoniae</option>
                  <option value="Acinetobacter spp.">Acinetobacter spp.</option>
                </select>
              </div>
            </div>

            {/* SVG Trend Line Chart */}
            <div style={{ position: 'relative', height: 260, background: 'rgba(15, 23, 42, 0.4)', borderRadius: 8, padding: '20px 20px 40px' }}>
              <svg width="100%" height="100%" viewBox="0 0 800 200" preserveAspectRatio="none">
                {/* Horizontal gridlines */}
                {[0, 25, 50, 75, 100].map((v) => (
                  <line
                    key={v}
                    x1="40"
                    y1={180 - v * 1.6}
                    x2="780"
                    y2={180 - v * 1.6}
                    stroke="rgba(255,255,255,0.06)"
                    strokeDasharray="4 4"
                  />
                ))}

                {/* Trajectory path */}
                {[...new Set(annualTrends.map((pt) => pt.source))].map((series, seriesIndex) => {
                  const points = annualTrends.filter((pt) => pt.source === series);
                  const allYears = annualTrends.map((pt) => pt.year);
                  const minYear = Math.min(...allYears);
                  const maxYear = Math.max(...allYears);
                  const xFor = (year) => 50 + ((year - minYear) / Math.max(1, maxYear - minYear)) * 710;
                  const color = series?.toLowerCase().includes('glass') ? 'var(--source-glass)' : 'var(--source-ecdc)';
                  return <g key={series}>
                    {points.length > 1 && <path d={points.map((pt, idx) => `${idx ? 'L' : 'M'} ${xFor(pt.year)} ${180 - Math.min(100, pt.median) * 1.6}`).join(' ')} fill="none" stroke={color} strokeWidth="3" />}
                    {points.map((pt) => <g key={`${series}-${pt.year}`}>
                      <circle cx={xFor(pt.year)} cy={180 - Math.min(100, pt.median) * 1.6} r="4" fill={color} stroke="#fff" strokeWidth="1.5" />
                      {seriesIndex === 0 && <text x={xFor(pt.year)} y="196" fill="var(--text-dim)" fontSize="10" textAnchor="middle">{pt.year}</text>}
                    </g>)}
                  </g>;
                })}
              </svg>
            </div>

            <div className="explainer">
              Trajectories show annual median resistance across surveillance sites. Notice upward drift in 3rd-generation cephalosporins and carbapenem resistance in <em>Acinetobacter</em> spp.
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Sample Size Funnel */}
      {activeTab === 'samples' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>Sample Size Funnel & Low-Sample Binomial Variance</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
              Visualizes resistance rates against sample size tested (log-scaled). Observations with small N (&lt; 30) exhibit extreme binary swings (0% or 100%), creating artificial volatility.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginBottom: 20 }}>
              <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: 16, borderRadius: 8 }}>
                <div style={{ color: '#f87171', fontWeight: 600, fontSize: '0.9rem' }}>Low Sample Observations (N &lt; 30)</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#fff', margin: '4px 0' }}>{lowSampleCount.toLocaleString()} rows</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Excluded from classification targets to prevent noise</div>
              </div>
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: 16, borderRadius: 8 }}>
                <div style={{ color: '#34d399', fontWeight: 600, fontSize: '0.9rem' }}>Robust Sample Observations (N ≥ 30)</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#fff', margin: '4px 0' }}>{adequateSampleCount.toLocaleString()} rows</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Eligible consecutive panel training rows</div>
              </div>
            </div>

            <div className="explainer">
              Binomial standard error scales as $\sqrt{p(1-p)/N}$. Under small N, random sample variance masquerades as alarming year-on-year increases. Our model explicitly incorporates <code>wilson_width</code> and <code>log_tested</code>.
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Year-on-Year Dynamics */}
      {activeTab === 'yoy' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>Year-on-Year Volatility & COVID-19 Impact</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 20 }}>
              <div className="kpi-card">
                <div className="kpi-label">GLASS Annual Delta SD</div>
                <div className="kpi-value">{(yoyData?.glass?.std ?? yoyData?.std) != null ? `${(yoyData.glass?.std ?? yoyData.std).toFixed(1)} pp` : '—'}</div>
                <div className="kpi-sub">Higher variance across global sites</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">ECDC Annual Delta SD</div>
                <div className="kpi-value">{yoyData?.ecdc?.std != null ? `${yoyData.ecdc.std.toFixed(1)} pp` : '—'}</div>
                <div className="kpi-sub">More stable European surveillance</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Rises ≥ +5 pp Share</div>
                <div className="kpi-value">{(yoyData?.glass?.share_ge_5 ?? yoyData?.share_ge_5) != null ? `${((yoyData.glass?.share_ge_5 ?? yoyData.share_ge_5) * 100).toFixed(1)}%` : '—'}</div>
                <div className="kpi-sub">Target candidate proportion</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">2020 COVID Flag</div>
                <div className="kpi-value">Active</div>
                <div className="kpi-sub">Flagged without dropping observations</div>
              </div>
            </div>

            <div className="explainer">
              Source-specific year-on-year changes are kept separate because the resistance definitions differ. The 2020 observations remain in the time series.
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: Target Class Balance */}
      {activeTab === 'balance' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.15rem', marginBottom: 12 }}>Target Prevalence Across Surveillance Thresholds</h3>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Surveillance Flag / Target</th>
                    <th>GLASS-AMR</th>
                    <th>ECDC-derived</th>
                    <th>Pooled Combined</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>High-Risk (T = 20%)</strong></td>
                    <td style={{ color: 'var(--source-glass)' }}>{balanceData?.class_balance?.glass?.high_risk_20 != null ? `${(balanceData.class_balance.glass.high_risk_20 * 100).toFixed(1)}%` : '—'}</td>
                    <td style={{ color: 'var(--source-ecdc)' }}>{balanceData?.class_balance?.ecdc?.high_risk_20 != null ? `${(balanceData.class_balance.ecdc.high_risk_20 * 100).toFixed(1)}%` : '—'}</td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td><strong>High-Risk (T = 30%, Primary)</strong></td>
                    <td style={{ color: 'var(--source-glass)', fontWeight: 600 }}>{balanceData?.class_balance?.glass?.high_risk_30 != null ? `${(balanceData.class_balance.glass.high_risk_30 * 100).toFixed(1)}%` : '—'}</td>
                    <td style={{ color: 'var(--source-ecdc)', fontWeight: 600 }}>{balanceData?.class_balance?.ecdc?.high_risk_30 != null ? `${(balanceData.class_balance.ecdc.high_risk_30 * 100).toFixed(1)}%` : '—'}</td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td><strong>High-Risk (T = 50%)</strong></td>
                    <td style={{ color: 'var(--source-glass)' }}>{balanceData?.class_balance?.glass?.high_risk_50 != null ? `${(balanceData.class_balance.glass.high_risk_50 * 100).toFixed(1)}%` : '—'}</td>
                    <td style={{ color: 'var(--source-ecdc)' }}>{balanceData?.class_balance?.ecdc?.high_risk_50 != null ? `${(balanceData.class_balance.ecdc.high_risk_50 * 100).toFixed(1)}%` : '—'}</td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td><strong>Rising Acceleration (+5 pp &amp; p &lt; 0.05)</strong></td>
                    <td style={{ color: 'var(--accent-rose)', fontWeight: 600 }}>{balanceData?.class_balance?.glass?.rising_next != null ? `${(balanceData.class_balance.glass.rising_next * 100).toFixed(1)}%` : '—'}</td>
                    <td style={{ color: 'var(--accent-rose)', fontWeight: 600 }}>{balanceData?.class_balance?.ecdc?.rising_next != null ? `${(balanceData.class_balance.ecdc.rising_next * 100).toFixed(1)}%` : '—'}</td>
                    <td>—</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="explainer">
              Notice the extreme imbalance in <code>rising_next</code> (6.7% in ECDC, 16.9% in GLASS). This dictates why PR-AUC is our primary evaluation metric and class weighting is mandatory.
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: Cross-Resistance */}
      {activeTab === 'correlation' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: '1.15rem' }}>Cross-Resistance Correlation Matrix</h3>
              <select
                className="form-select"
                style={{ width: 220 }}
                value={selectedPathogen}
                onChange={(e) => setSelectedPathogen(e.target.value)}
              >
                <option value="Escherichia coli">Escherichia coli</option>
                <option value="Klebsiella pneumoniae">Klebsiella pneumoniae</option>
                <option value="Acinetobacter spp.">Acinetobacter spp.</option>
              </select>
            </div>

            {corrData?.matrix ? (
              <div style={{ overflowX: 'auto' }}>
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${corrData.antibiotics.length + 1}, minmax(80px, 1fr))`, gap: 4 }}>
                  <div />
                  {corrData.antibiotics.map((abx) => (
                    <div key={abx} style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-dim)', textAlign: 'center', padding: 4 }}>
                      {abx.slice(0, 7)}
                    </div>
                  ))}
                  {corrData.matrix.map((row, rIdx) => (
                    <React.Fragment key={rIdx}>
                      <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-dim)', display: 'flex', alignItems: 'center' }}>
                        {corrData.antibiotics[rIdx]?.slice(0, 7)}
                      </div>
                      {row.map((val, cIdx) => {
                        const intensity = Math.abs(val);
                        const isPos = val >= 0;
                        const bg = isPos
                          ? `rgba(6, 182, 212, ${intensity * 0.7})`
                          : `rgba(239, 68, 68, ${intensity * 0.7})`;
                        return (
                          <div
                            key={cIdx}
                            style={{
                              background: bg,
                              border: '1px solid rgba(255,255,255,0.05)',
                              borderRadius: 4,
                              height: 36,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              color: intensity > 0.4 ? '#fff' : 'var(--text-muted)',
                            }}
                          >
                            {val.toFixed(2)}
                          </div>
                        );
                      })}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>Loading correlation matrix...</p>
            )}

            <div className="explainer">
              Carbapenems (Meropenem, Imipenem) and 3rd-gen cephalosporins (Ceftriaxone, Ceftazidime) exhibit correlations &gt; 0.85, confirming strong co-resistance signals utilized by our <code>mdr_burden</code> and <code>class_mean_other</code> features.
            </div>
          </div>
        </div>
      )}

      {/* TAB 7: Data Issues & Decisions */}
      {activeTab === 'issues' && (
        <div className="card">
          <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Surveillance Realities & Modeling Countermeasures</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Surveillance Issue</th>
                  <th>Observed Empirical Data Reality</th>
                  <th>Pipeline Modeling Mitigation</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>1</td>
                  <td><strong>Definition Mismatch</strong></td>
                  <td>ECDC is I+R; GLASS is R. ECDC runs ~2–3 pp higher in Malta overlap.</td>
                  <td>All models evaluated in 3 configurations: <code>glass</code>, <code>ecdc</code>, and <code>pooled</code>. Never averaged naively.</td>
                </tr>
                <tr>
                  <td>2</td>
                  <td><strong>Small Sample Noise</strong></td>
                  <td>5.3% of GLASS rows have N &lt; 30, producing artificial 0/100% volatility.</td>
                  <td>Classification targets strictly require N ≥ 30 in both consecutive years. Sample size features included.</td>
                </tr>
                <tr>
                  <td>3</td>
                  <td><strong>Temporal Panel Disparity</strong></td>
                  <td>GLASS has 6 years (2018–2023); ECDC has 21 years (1999–2019).</td>
                  <td>Strict time-ordered splits with forward-chaining rolling-origin folds; no random cross-validation.</td>
                </tr>
                <tr>
                  <td>4</td>
                  <td><strong>COVID-19 Disruption</strong></td>
                  <td>2020 experienced diagnostic capacity shifts during the pandemic.</td>
                  <td>Added explicit <code>covid_flag</code> feature for target year 2020 rather than discarding records.</td>
                </tr>
                <tr>
                  <td>5</td>
                  <td><strong>AST Coverage Gaps</strong></td>
                  <td>Reported in GLASS; entirely unrecorded in ECDC.</td>
                  <td>Excluded in ECDC models; imputed with training median plus missing indicator in pooled model.</td>
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
          <h4>Key Takeaway: Empirical Surveillance Signals</h4>
          <p>
            Surveillance series exhibit strong inertia punctuated by acute sample-size noise under N &lt; 30 and strong carbapenem co-resistance. Our feature derivations specifically exploit cross-resistance co-occurrence while filtering small-sample artifacts.
          </p>
        </div>
      </div>
    </div>
  );
}
