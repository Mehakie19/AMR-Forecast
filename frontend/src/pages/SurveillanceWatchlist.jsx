import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { AlertCircle, Download, Search, Filter, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function SurveillanceWatchlist({ scope, source }) {
  const [watchlist, setWatchlist] = useState([]);
  const [sortBy, setSortBy] = useState('high_risk_probability');
  const [filterPathogen, setFilterPathogen] = useState('');
  const [filterAbx, setFilterAbx] = useState('');
  const [minTested, setMinTested] = useState(30);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getWatchlist({
      source,
      pathogen: filterPathogen,
      antibiotic: filterAbx,
      min_tested: minTested,
      sort: sortBy,
    })
      .then((data) => setWatchlist(data?.items || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [source, filterPathogen, filterAbx, minTested, sortBy]);

  const highRiskCount = watchlist.filter((item) => (item.high_risk_probability || 0) >= 0.4).length;
  const risingCount = watchlist.filter((item) => (item.rising_probability || 0) >= 0.2).length;
  const noisyCount = watchlist.filter((item) => (item.number_tested || 0) < 30).length;

  // Export CSV
  const downloadCsv = () => {
    if (!watchlist.length) return;
    const headers = [
      'source', 'iso3', 'country', 'pathogen', 'antibiotic',
      'latest_year', 'latest_resistance_pct', 'number_tested', 'forecast_pct',
      'high_risk_probability', 'rising_probability', 'data_quality_flag'
    ];
    const rows = watchlist.map((w) =>
      headers.map((h) => `"${w[h] ?? ''}"`).join(',')
    );
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
      const encodedUri = `data:text/csv;charset=utf-8,${encodeURIComponent([headers.join(','), ...rows].join('\n'))}`;
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'amr_sense_candidates_for_expert_review.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Surveillance Watchlist: Candidates for Expert Review
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Prioritised surveillance series ranked by predicted next-year resistance risk and acute acceleration signals.
        </p>
      </div>

      {/* Summary Tiles */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">Active Series in Scope</div>
          <div className="kpi-value">{watchlist.length}</div>
          <div className="kpi-sub">Latest observed round</div>
        </div>
        <div className="kpi-card" style={{ borderLeft: '3px solid #f43f5e' }}>
          <div className="kpi-label">High-Risk Candidates</div>
          <div className="kpi-value" style={{ color: '#f87171' }}>{highRiskCount}</div>
          <div className="kpi-sub">P(Res ≥ 30%) ≥ 40%</div>
        </div>
        <div className="kpi-card" style={{ borderLeft: '3px solid #f59e0b' }}>
          <div className="kpi-label">Acceleration Signals</div>
          <div className="kpi-value" style={{ color: '#fbbf24' }}>{risingCount}</div>
          <div className="kpi-sub">P(Rise ≥ 5 pp) ≥ 20%</div>
        </div>
        <div className="kpi-card" style={{ borderLeft: '3px solid #64748b' }}>
          <div className="kpi-label">Small Sample Flags</div>
          <div className="kpi-value" style={{ color: '#94a3b8' }}>{noisyCount}</div>
          <div className="kpi-sub">N &lt; 30 (high variance)</div>
        </div>
      </div>

      {/* Table Controls */}
      <div
        className="card"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
          padding: '16px 20px',
          marginBottom: 20,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <select
            className="form-select"
            style={{ width: 180 }}
            value={filterPathogen}
            onChange={(e) => setFilterPathogen(e.target.value)}
          >
            <option value="">All Pathogens</option>
            <option value="Escherichia coli">Escherichia coli</option>
            <option value="Klebsiella pneumoniae">Klebsiella pneumoniae</option>
            <option value="Acinetobacter spp.">Acinetobacter spp.</option>
          </select>

          <select
            className="form-select"
            style={{ width: 170 }}
            value={filterAbx}
            onChange={(e) => setFilterAbx(e.target.value)}
          >
            <option value="">All Antibiotics</option>
            <option value="Ciprofloxacin">Ciprofloxacin</option>
            <option value="Ceftriaxone">Ceftriaxone</option>
            <option value="Meropenem">Meropenem</option>
            <option value="Gentamicin">Gentamicin</option>
            <option value="Colistin">Colistin</option>
            <option value="Amikacin">Amikacin</option>
          </select>

          <select
            className="form-select"
            style={{ width: 190 }}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="high_risk_probability">Sort: High Risk Prob</option>
            <option value="rising_probability">Sort: Rising Prob</option>
            <option value="forecast_pct">Sort: Forecast %</option>
            <option value="latest_resistance_pct">Sort: Latest Resistance</option>
            <option value="number_tested">Sort: Sample Size N</option>
          </select>
        </div>

        <button className="btn btn-primary" onClick={downloadCsv}>
          <Download size={16} />
          Export Candidates CSV
        </button>
      </div>

      {/* Ranked Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="data-table-container" style={{ border: 'none', maxHeight: 520, overflowY: 'auto' }}>
          <table className="data-table">
            <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
              <tr>
                <th>Source</th>
                <th>Country</th>
                <th>Pathogen</th>
                <th>Antibiotic</th>
                <th>Latest Yr</th>
                <th>Observed %</th>
                <th>Tested N</th>
                <th>Forecast %</th>
                <th>High Risk Prob</th>
                <th>Rising Prob</th>
                <th>Data Flag</th>
              </tr>
            </thead>
            <tbody>
              {watchlist.map((item, idx) => {
                const highRisk = (item.high_risk_probability || 0) >= 0.4;
                const isRising = (item.rising_probability || 0) >= 0.2;
                return (
                  <tr key={`${item.source}-${item.iso3}-${item.pathogen}-${item.antibiotic}-${idx}`}>
                    <td>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 6px',
                          borderRadius: 4,
                          background: item.source === 'GLASS-AMR' ? 'rgba(14, 165, 233, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                          color: item.source === 'GLASS-AMR' ? 'var(--source-glass)' : 'var(--source-ecdc)',
                        }}
                      >
                        {item.source === 'GLASS-AMR' ? 'GLASS' : 'ECDC'}
                      </span>
                    </td>
                    <td>
                      <strong>{item.iso3}</strong>{' '}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{item.country}</span>
                    </td>
                    <td><em style={{ fontSize: '0.8rem' }}>{item.pathogen}</em></td>
                    <td>{item.antibiotic}</td>
                    <td>{item.latest_year}</td>
                    <td style={{ fontWeight: 600 }}>{item.latest_resistance_pct?.toFixed(1)}%</td>
                    <td style={{ color: item.number_tested < 30 ? '#f87171' : 'var(--text-muted)' }}>
                      {item.number_tested}
                    </td>
                    <td style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                      {item.forecast_pct?.toFixed(1)}%
                    </td>
                    <td style={{ color: highRisk ? '#f87171' : 'var(--text-muted)', fontWeight: highRisk ? 700 : 400 }}>
                      {((item.high_risk_probability || 0) * 100).toFixed(1)}%
                    </td>
                    <td style={{ color: isRising ? '#fbbf24' : 'var(--text-muted)', fontWeight: isRising ? 700 : 400 }}>
                      {((item.rising_probability || 0) * 100).toFixed(1)}%
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          color: item.data_quality_flag?.includes('Robust') ? '#34d399' : '#fca5a5',
                        }}
                      >
                        {item.data_quality_flag || 'Standard'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ marginTop: 12, fontSize: '0.8rem', color: 'var(--text-dim)' }}>
        Note: Candidates for expert review. Prioritization indicates statistical triage for laboratory verification and public health audit, not automated treatment recommendations.
      </div>

      {/* Key Takeaway */}
      <div className="takeaway-box">
        <CheckCircle2 size={24} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4>Key Takeaway: Surveillance Triage Protocol</h4>
          <p>
            The surveillance watchlist integrates latest-round prevalence with calibrated ML risk projections. Public health teams can filter by pathogen and export the triage list for retrospective audit and antimicrobial stewardship monitoring.
          </p>
        </div>
      </div>
    </div>
  );
}
