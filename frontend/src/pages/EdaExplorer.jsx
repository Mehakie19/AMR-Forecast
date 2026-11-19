import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { BarChart3, TrendingUp, Filter, AlertCircle, Sparkles } from 'lucide-react';

function quantile(sortedValues, probability) {
  if (!sortedValues.length) return 0;
  const position = (sortedValues.length - 1) * probability;
  const lower = Math.floor(position);
  const fraction = position - lower;
  return sortedValues[lower] + (sortedValues[Math.min(lower + 1, sortedValues.length - 1)] - sortedValues[lower]) * fraction;
}

export default function EdaExplorer({ scope, source }) {
  const [activeTab, setActiveTab] = useState('distributions');
  const [distData, setDistData] = useState([]);
  const [trendData, setTrendData] = useState([]);
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
      api.getEdaCorrelation(source, selectedPathogen),
      api.getEdaYearChange('glass'),
      api.getEdaYearChange('ecdc'),
    ])
      .then(([dist, tr, corr, glassYoy, ecdcYoy]) => {
        setDistData(dist?.records || dist?.rows || []);
        setTrendData(tr?.trends || tr?.series || tr?.rows || []);
        setCorrData(corr?.correlations || corr || null);
        setYoyData({
          glass: glassYoy?.data?.glass || glassYoy?.data,
          ecdc: ecdcYoy?.data?.ecdc || ecdcYoy?.data,
        });
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
      const median = quantile(sorted, 0.5);
      const q25 = quantile(sorted, 0.25);
      const q75 = quantile(sorted, 0.75);
      const min = sorted[0] || 0;
      const max = sorted[sorted.length - 1] || 0;
      return { abx, source: sourceName, count: vals.length, median, q25, q75, min, max };
    }).sort((a, b) => b.median - a.median);
  }, [distData]);

  // Longitudinal trend aggregates
  const annualTrends = React.useMemo(() => {
    const filtered = trendData.filter((d) => !selectedPathogen || d.pathogen === selectedPathogen);
    const groups = new Map();
    filtered.forEach((row) => {
      const year = Number(row.year);
      const median = Number(row.median);
      if (!Number.isFinite(year) || !Number.isFinite(median)) return;
      const key = `${row.source}::${year}`;
      const group = groups.get(key) || { year, source: row.source, medians: [], count: 0 };
      group.medians.push(median);
      group.count += Number(row.count) || 0;
      groups.set(key, group);
    });
    return [...groups.values()].map(({ medians, ...group }) => {
      const sorted = medians.sort((a, b) => a - b);
      return { ...group, median: quantile(sorted, 0.5) };
    }).sort((a, b) => a.year - b.year);
  }, [trendData, selectedPathogen]);
  const trendYears = [...new Set(annualTrends.map((point) => point.year))].sort((a, b) => a - b);
  const trendMinYear = trendYears[0] ?? 0;
  const trendMaxYear = trendYears[trendYears.length - 1] ?? trendMinYear;
  const trendTickYears = trendYears.length > 5
    ? [...new Set([0, 0.25, 0.5, 0.75, 1].map((fraction) => trendYears[Math.round((trendYears.length - 1) * fraction)]))]
    : trendYears;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Explore the surveillance data
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Compare resistance distributions and trends, review year-to-year changes, and see which antibiotic rates move together.
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="tabs-header">
        {[
          { id: 'distributions', label: '1. Distributions' },
          { id: 'trends', label: '2. Longitudinal Trends' },
          { id: 'yoy', label: '3. Changes over time' },
          { id: 'correlation', label: '4. Antibiotic patterns' },
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
              <h3 style={{ fontSize: '1.15rem' }}>Resistance levels by antibiotic</h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className={`btn ${chartType === 'box' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setChartType('box')}
                  style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                >
                  Box view
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
              <h3 style={{ fontSize: '1.15rem' }}>Line chart: Yearly resistance trends by pathogen</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }} title="A bacterium being monitored">Pathogen:</span>
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
            <p style={{ fontSize: '.82rem', color: 'var(--text-muted)', margin: '0 0 10px' }}>
              Each point is the median of antibiotic-specific median resistance rates for the selected pathogen and reporting year.
            </p>
            <div style={{ position: 'relative', height: 290, background: 'rgba(15, 23, 42, 0.4)', borderRadius: 8, padding: '16px 20px 36px' }}>
              <svg width="100%" height="100%" viewBox="0 0 800 230" preserveAspectRatio="none" role="img" aria-label="Line chart of yearly median resistance percentage by source">
                <text x="18" y="100" fill="var(--text-muted)" fontSize="11" textAnchor="middle" transform="rotate(-90 18 100)">Median resistance (%)</text>
                {/* Horizontal gridlines */}
                {[0, 25, 50, 75, 100].map((v) => (
                  <g key={v}>
                    <line
                      x1="70"
                      y1={180 - v * 1.6}
                      x2="780"
                      y2={180 - v * 1.6}
                      stroke="rgba(255,255,255,0.06)"
                      strokeDasharray="4 4"
                    />
                    <text x="64" y={180 - v * 1.6 + 3} fill="var(--text-dim)" fontSize="10" textAnchor="end">{v}%</text>
                  </g>
                ))}

                {/* Trajectory path */}
                {trendTickYears.map((year) => {
                  const x = 80 + ((year - trendMinYear) / Math.max(1, trendMaxYear - trendMinYear)) * 690;
                  return <g key={`tick-${year}`}>
                    <line x1={x} y1="20" x2={x} y2="180" stroke="rgba(255,255,255,0.03)" />
                    <text x={x} y="196" fill="var(--text-dim)" fontSize="10" textAnchor="middle">{year}</text>
                  </g>;
                })}
                {[...new Set(annualTrends.map((pt) => pt.source))].map((series) => {
                  const points = annualTrends.filter((pt) => pt.source === series);
                  const xFor = (year) => 80 + ((year - trendMinYear) / Math.max(1, trendMaxYear - trendMinYear)) * 690;
                  const color = series?.toLowerCase().includes('glass') ? 'var(--source-glass)' : 'var(--source-ecdc)';
                  return <g key={series}>
                    {points.length > 1 && <path d={points.map((pt, idx) => `${idx ? 'L' : 'M'} ${xFor(pt.year)} ${180 - Math.min(100, pt.median) * 1.6}`).join(' ')} fill="none" stroke={color} strokeWidth="3" />}
                    {points.map((pt) => <g key={`${series}-${pt.year}`}>
                      <circle cx={xFor(pt.year)} cy={180 - Math.min(100, pt.median) * 1.6} r="4" fill={color} stroke="#fff" strokeWidth="1.5">
                        <title>{`${series} ${pt.year}: median resistance ${pt.median.toFixed(2)}%; ${pt.count} observations across antibiotic groups`}</title>
                      </circle>
                    </g>)}
                  </g>;
                })}
                <text x="425" y="220" fill="var(--text-muted)" fontSize="11" textAnchor="middle">Reporting year</text>
              </svg>
            </div>
            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', marginTop: 10, fontSize: '.8rem', color: 'var(--text-muted)' }}>
              {annualTrends.some((point) => point.source?.toLowerCase().includes('glass')) && <span><b style={{ color: 'var(--source-glass)' }}>●</b> GLASS-AMR (R)</span>}
              {annualTrends.some((point) => !point.source?.toLowerCase().includes('glass')) && <span><b style={{ color: 'var(--source-ecdc)' }}>●</b> ECDC (I+R)</span>}
            </div>

          </div>
        </div>
      )}

      {/* TAB 3: Year-on-Year Changes */}
      {activeTab === 'yoy' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>Line chart: Average year-to-year resistance change</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
              For each country–pathogen–antibiotic series, the reported percentage in one year is compared with the previous year. The chart shows the average of those changes for each year, in percentage points.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 20 }}>
              <div className="kpi-card">
                <div className="kpi-label">GLASS average change</div>
                <div className="kpi-value">{yoyData?.glass?.mean != null ? `${yoyData.glass.mean.toFixed(2)} pp` : '—'}</div>
                <div className="kpi-sub">Average year-to-year change across series</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">GLASS change variation</div>
                <div className="kpi-value">{yoyData?.glass?.std != null ? `${yoyData.glass.std.toFixed(2)} pp` : '—'}</div>
                <div className="kpi-sub">How much individual series changes vary</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">GLASS changes rising 5+ points</div>
                <div className="kpi-value">{yoyData?.glass?.share_ge_5 != null ? `${(yoyData.glass.share_ge_5 * 100).toFixed(1)}%` : '—'}</div>
                <div className="kpi-sub">Share of year-to-year changes meeting this size</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">ECDC average change</div>
                <div className="kpi-value">{yoyData?.ecdc?.mean != null ? `${yoyData.ecdc.mean.toFixed(2)} pp` : '—'}</div>
                <div className="kpi-sub">Average year-to-year change across series</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">ECDC change variation</div>
                <div className="kpi-value">{yoyData?.ecdc?.std != null ? `${yoyData.ecdc.std.toFixed(2)} pp` : '—'}</div>
                <div className="kpi-sub">How much individual series changes vary</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">ECDC changes rising 5+ points</div>
                <div className="kpi-value">{yoyData?.ecdc?.share_ge_5 != null ? `${(yoyData.ecdc.share_ge_5 * 100).toFixed(1)}%` : '—'}</div>
                <div className="kpi-sub">Share of year-to-year changes meeting this size</div>
              </div>
            </div>

            {(() => {
              const rows = ['glass', 'ecdc'].flatMap((key) => Object.entries(yoyData?.[key]?.by_year || {}).map(([year, change]) => ({
                source: key,
                year: Number(year),
                change: Number(change),
              })));
              const years = [...new Set(rows.map((row) => row.year))].sort((a, b) => a - b);
              const maxAbs = Math.max(1, ...rows.map((row) => Math.abs(row.change)));
              const limit = Math.ceil(maxAbs / 2) * 2;
              const yFor = (value) => 120 - ((value / limit) * 90);
              const xFor = (year) => 70 + ((year - (years[0] ?? 0)) / Math.max(1, (years[years.length - 1] ?? 0) - (years[0] ?? 0))) * 685;
              return (
                <>
                  <div style={{ overflowX: 'auto', marginBottom: 16 }}>
                    <svg viewBox="0 0 780 275" role="img" aria-label="Line chart of average year-to-year resistance change by reporting year and source" style={{ width: '100%', minWidth: 580, height: 275 }}>
                      <text x="14" y="120" fill="var(--text-muted)" fontSize="10" textAnchor="middle" transform="rotate(-90 14 120)">Mean change (percentage points)</text>
                      {[-limit, 0, limit].map((value) => (
                        <g key={value}>
                          <line x1="70" x2="755" y1={yFor(value)} y2={yFor(value)} stroke="rgba(255,255,255,.12)" strokeDasharray={value === 0 ? undefined : '4 4'} />
                          <text x="64" y={yFor(value) - 5} fill="var(--text-dim)" fontSize="10" textAnchor="end">{value} pp</text>
                        </g>
                      ))}
                      {years.map((year, index) => (index === 0 || index === years.length - 1 || index % Math.ceil(years.length / 6) === 0) && (
                        <text key={year} x={xFor(year)} y="235" fill="var(--text-dim)" fontSize="10" textAnchor="middle">{year}</text>
                      ))}
                      {['glass', 'ecdc'].map((key) => {
                        const points = rows.filter((row) => row.source === key).sort((a, b) => a.year - b.year);
                        const color = key === 'glass' ? 'var(--source-glass)' : 'var(--source-ecdc)';
                        return (
                          <g key={key}>
                            {points.length > 1 && <path d={points.map((point, index) => `${index ? 'L' : 'M'} ${xFor(point.year)} ${yFor(point.change)}`).join(' ')} fill="none" stroke={color} strokeWidth="2" />}
                            {points.map((point) => (
                              <circle key={`${key}-${point.year}`} cx={xFor(point.year)} cy={yFor(point.change)} r="3.5" fill={color}>
                                <title>{`${key.toUpperCase()} ${point.year}: ${point.change.toFixed(2)} percentage points average change`}</title>
                              </circle>
                            ))}
                          </g>
                        );
                      })}
                      <text x="400" y="264" fill="var(--text-muted)" fontSize="11" textAnchor="middle">Reporting year</text>
                    </svg>
                  </div>
                  <div style={{ display: 'flex', gap: 18, fontSize: '.8rem', color: 'var(--text-muted)', marginBottom: 20 }}>
                    <span><b style={{ color: 'var(--source-glass)' }}>●</b> GLASS (R)</span>
                    <span><b style={{ color: 'var(--source-ecdc)' }}>●</b> ECDC (I+R)</span>
                  </div>
                  <h4 style={{ marginBottom: 10 }}>Average change for each year</h4>
                  <div className="data-table-container">
                    <table className="data-table">
                      <thead><tr><th>Reporting year</th><th>GLASS average change</th><th>ECDC average change</th></tr></thead>
                      <tbody>{years.map((year) => {
                        const glass = rows.find((row) => row.source === 'glass' && row.year === year);
                        const ecdc = rows.find((row) => row.source === 'ecdc' && row.year === year);
                        return <tr key={year}><td>{year}</td><td>{glass ? `${glass.change.toFixed(2)} pp` : '—'}</td><td>{ecdc ? `${ecdc.change.toFixed(2)} pp` : '—'}</td></tr>;
                      })}</tbody>
                    </table>
                  </div>
                </>
              );
            })()}
            <p className="explainer" style={{ marginTop: 16 }}>
              Positive values mean an increase; negative values mean a decrease. For example, 20% to 25% is a rise of 5 percentage points. The yearly chart shows average changes across available country–pathogen–antibiotic series, not the change for every series. The “5+ points” cards count changes of that size only; they do not apply the statistical test and sample-size rules used for the project’s rising-alert target. GLASS and ECDC use different resistance definitions, so read their lines separately.
            </p>
          </div>
        </div>
      )}

      {/* TAB 4: Antibiotic Patterns */}
      {activeTab === 'correlation' && (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: '1.15rem' }}>Do antibiotic resistance rates move together?</h3>
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
              <p style={{ color: 'var(--text-muted)' }}>Loading antibiotic pattern results...</p>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
