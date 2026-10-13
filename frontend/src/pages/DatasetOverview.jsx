import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Database, Activity, MapPin, Calendar, AlertTriangle, Layers, CheckCircle2 } from 'lucide-react';

export default function DatasetOverview({ scope, source }) {
  const [summary, setSummary] = useState(null);
  const [glassSum, setGlassSum] = useState(null);
  const [ecdcSum, setEcdcSum] = useState(null);
  const [quality, setQuality] = useState(null);
  const [coverage, setCoverage] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getDatasetsSummary(source),
      api.getDatasetsSummary('glass'),
      api.getDatasetsSummary('ecdc'),
      api.getDatasetsQuality(),
      api.getDatasetsCoverage(source),
    ])
      .then(([curr, g, e, q, cov]) => {
        setSummary(curr);
        setGlassSum(g);
        setEcdcSum(e);
        setQuality(q);
        setCoverage(cov?.coverage || cov?.matrix || []);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [source]);

  // Aggregate coverage per country
  const countryCoverage = React.useMemo(() => {
    const map = {};
    coverage.forEach((c) => {
      if (!map[c.iso3]) {
        map[c.iso3] = { iso3: c.iso3, country: c.country, count: 0, years: new Set() };
      }
      map[c.iso3].count += c.series_count;
      map[c.iso3].years.add(c.year);
    });
    return Object.values(map)
      .map((item) => ({ ...item, yearCount: item.years.size }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15);
  }, [coverage]);
  const overlapPairs = React.useMemo(() => {
    const groups = new Map();
    (quality?.malta_overlap || []).forEach((row) => {
      const key = `${row.year}-${row.pathogen}-${row.antibiotic}`;
      const pair = groups.get(key) || {};
      pair[row.source === 'GLASS-AMR' ? 'glass' : 'ecdc'] = row.pct_resistant;
      Object.assign(pair, { year: row.year, pathogen: row.pathogen, antibiotic: row.antibiotic });
      groups.set(key, pair);
    });
    return [...groups.values()].filter((row) => row.glass != null && row.ecdc != null);
  }, [quality]);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 8 }}>
          Dataset Overview & Surveillance Coverage
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Single source of truth: <code>data/raw/combined_amr_dataset.csv</code> (6,634 records across 42 countries).
        </p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Total Surveillance Records</div>
          <div className="kpi-value">{summary?.rows?.toLocaleString() ?? '—'}</div>
          <div className="kpi-sub">Harmonized observations</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Unique Series</div>
          <div className="kpi-value">{summary?.series?.toLocaleString() ?? '—'}</div>
          <div className="kpi-sub">ISO3 × Pathogen × Antibiotic</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Jurisdictions / Countries</div>
          <div className="kpi-value">{summary?.countries ?? '—'}</div>
          <div className="kpi-sub">31 GLASS + 27 ECDC (Malta overlaps)</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Longitudinal Span</div>
          <div className="kpi-value">
            {summary?.years ? `${summary.years[0]}–${summary.years[1]}` : '1999–2023'}
          </div>
          <div className="kpi-sub">25 surveillance years</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Pathogen Families</div>
          <div className="kpi-value">{summary?.pathogens?.length ?? '—'}</div>
          <div className="kpi-sub">E. coli, K. pneumoniae, Acinetobacter</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Target Antibiotics</div>
          <div className="kpi-value">{summary?.antibiotics?.length ?? '—'}</div>
          <div className="kpi-sub">Carbapenems, Cephalosporins, etc.</div>
        </div>
      </div>

      {/* Per-Source Breakdown Banner */}
      {scope === 'Combined' && glassSum && ecdcSum && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 16,
            marginBottom: 28,
          }}
        >
          <div
            className="card"
            style={{
              borderLeft: '4px solid var(--source-glass)',
              background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.08), rgba(15, 23, 42, 0.6))',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: 'var(--source-glass)',
                }}
              />
              <strong style={{ color: '#fff', fontSize: '1rem' }}>WHO GLASS-AMR</strong>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <div>• Records: <strong>{glassSum.rows?.toLocaleString()}</strong> (399 series × 6 rounds)</div>
              <div>• Window: <strong>2018 – 2023</strong> (Balanced panel)</div>
              <div>• Definition: <strong>R (Resistant)</strong> as reported by GLASS</div>
              <div>• Setting: Bloodstream infection isolates</div>
            </div>
          </div>

          <div
            className="card"
            style={{
              borderLeft: '4px solid var(--source-ecdc)',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(15, 23, 42, 0.6))',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: 'var(--source-ecdc)',
                }}
              />
              <strong style={{ color: '#fff', fontSize: '1rem' }}>ECDC EARS-Net (Derived)</strong>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <div>• Records: <strong>{ecdcSum.rows?.toLocaleString()}</strong> (Unbalanced panel)</div>
              <div>• Window: <strong>1999 – 2019</strong> (21 rounds)</div>
              <div>• Definition: <strong>I+R (Intermediate + Resistant)</strong></div>
              <div>• Setting: Inpatient invasive blood & CSF isolates</div>
            </div>
          </div>
        </div>
      )}

      {/* Source Comparison Table */}
      <div className="card" style={{ marginBottom: 28 }}>
        <h3 style={{ fontSize: '1.15rem', marginBottom: 16 }}>Surveillance Source Provenance & Schema Specification</h3>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Attribute</th>
                <th style={{ color: 'var(--source-glass)' }}>WHO GLASS-AMR</th>
                <th style={{ color: 'var(--source-ecdc)' }}>ECDC EARS-Net (Derived)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Publisher / Repository</strong></td>
                <td>World Health Organization (GLASS Dashboard export)</td>
                <td>Zenodo record 14224680 (Emons, Blanquart, Lehtinen)</td>
              </tr>
              <tr>
                <td><strong>Temporal Horizon</strong></td>
                <td>2018 – 2023 (6 annual rounds)</td>
                <td>1999 – 2019 (21 annual rounds)</td>
              </tr>
              <tr>
                <td><strong>Geographic Scope</strong></td>
                <td>31 participating countries across 5 WHO regions</td>
                <td>27 European countries in this combined dataset</td>
              </tr>
              <tr>
                <td><strong>Resistance Metric</strong></td>
                <td><strong>R</strong> (Resistant as defined by GLASS)</td>
                <td><strong>I+R</strong> (Intermediate + Resistant combined)</td>
              </tr>
              <tr>
                <td><strong>Sample Size Policy</strong></td>
                <td>~5.3% of rows have N &lt; 30 (noisy surveillance)</td>
                <td>Pre-filtered to N ≥ 30 isolates per observation</td>
              </tr>
              <tr>
                <td><strong>Key Overlap Cases</strong></td>
                <td colSpan={2} style={{ textAlign: 'center', color: '#fde68a' }}>
                  8 records in Malta (2018–2019, 2 series pairs). ECDC rates run ~2–3 pp higher due to I+R inclusion.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Coverage & Quality Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 20 }}>
        {/* Top Reporting Countries */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', marginBottom: 14 }}>Top Reporting Surveillance Jurisdictions</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ISO3</th>
                  <th>Country</th>
                  <th>Series Records</th>
                  <th>Active Years</th>
                </tr>
              </thead>
              <tbody>
                {countryCoverage.map((c) => (
                  <tr key={c.iso3}>
                    <td><span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{c.iso3}</span></td>
                    <td>{c.country}</td>
                    <td>{c.count}</td>
                    <td>{c.yearCount} yrs</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quality Audit & Malta Table */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', marginBottom: 14 }}>Data Quality & Overlap Audit</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>PRIMARY KEY DUPLICATES</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#34d399' }}>{quality?.duplicates ?? '—'}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>100% uniquely identified</div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>GLASS N &lt; 30 SHARE</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f87171' }}>{quality?.n_lt_30_share?.glass != null ? `${(quality.n_lt_30_share.glass * 100).toFixed(1)}%` : '—'}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Excluded from classification</div>
            </div>
          </div>

          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 8 }}>
            Malta Overlap Audit (Identical Series in 2018–2019):
          </h4>
          <div className="data-table-container">
            <table className="data-table" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Pathogen</th>
                  <th>Antibiotic</th>
                  <th>GLASS (R)</th>
                  <th>ECDC (I+R)</th>
                </tr>
              </thead>
              <tbody>
                {overlapPairs.map((row) => <tr key={`${row.year}-${row.pathogen}-${row.antibiotic}`}>
                  <td>{row.year}</td><td>{row.pathogen}</td><td>{row.antibiotic}</td>
                  <td>{Number(row.glass).toFixed(1)}%</td><td>{Number(row.ecdc).toFixed(1)}%</td>
                </tr>)}
              </tbody>
            </table>
          </div>
          <div className="explainer" style={{ marginTop: 10 }}>
            ECDC values systematically run ~2–3 pp higher because ECDC includes Intermediate isolates, verifying why models must run in dedicated and source-flagged configurations.
          </div>
        </div>
      </div>

      {/* Key Takeaway */}
      <div className="takeaway-box">
        <CheckCircle2 size={24} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h4>Key Takeaway: Rigorous Single Source of Truth</h4>
          <p>
            The harmonized dataset provides 6,634 surveillance observations across 42 countries. GLASS supplies a balanced 6-year panel (2018–2023), while ECDC supplies 21 years of longitudinal depth (1999–2019). Because resistance definitions differ (R vs I+R), our modeling pipelines strictly isolate definitions rather than naively blending them.
          </p>
        </div>
      </div>
    </div>
  );
}
