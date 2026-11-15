import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Globe2, MapPin, TrendingUp } from 'lucide-react';
import { api } from '../api';
import './IntelligenceOverview.css';

const MAP_URL = `${import.meta.env.BASE_URL}data/ne_110m_admin_0_countries.geojson`;

function project([longitude, latitude]) {
  return [
    20 + ((longitude + 180) / 360) * 960,
    18 + ((85 - Math.max(-85, Math.min(85, latitude))) / 170) * 464,
  ];
}

function ringPath(ring) {
  return ring.map((point, index) => {
    const [x, y] = project(point);
    return `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ') + ' Z';
}

function geometryPath(geometry) {
  if (!geometry) return '';
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  return polygons.map((polygon) => ringPath(polygon[0])).join(' ');
}

function resistanceColor(value) {
  if (!Number.isFinite(value)) return '#243247';
  if (value < 20) return '#2b7484';
  if (value < 40) return '#b18a3d';
  if (value < 60) return '#c5653d';
  return '#bd454d';
}

export default function IntelligenceOverview({ source }) {
  const [selectedSource, setSelectedSource] = useState(source === 'ecdc' ? 'ecdc' : 'glass');
  const [pathogen, setPathogen] = useState('');
  const [antibiotic, setAntibiotic] = useState('');
  const [data, setData] = useState(null);
  const [geometry, setGeometry] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mapError, setMapError] = useState('');

  useEffect(() => {
    let active = true;
    fetch(MAP_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`Country map could not be loaded (${response.status}).`);
        return response.json();
      })
      .then((geojson) => {
        if (active) setGeometry(geojson.features || []);
      })
      .catch((err) => {
        if (active) setMapError(err.message);
      });
    return () => { active = false; };
  }, []);

  async function loadOverview(nextSource, nextPathogen = '', nextAntibiotic = '') {
    try {
      const result = await api.getIntelligenceOverview(nextSource, nextPathogen, nextAntibiotic);
      setData(result);
      setPathogen(result.pathogen);
      setAntibiotic(result.antibiotic);
      setSelectedCountry('');
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    api.getIntelligenceOverview(selectedSource)
      .then((result) => {
        if (!active) return;
        setData(result);
        setPathogen(result.pathogen);
        setAntibiotic(result.antibiotic);
        setSelectedCountry('');
      })
      .catch((err) => {
        if (!active) return;
        setError(err.message);
        setData(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [selectedSource]);

  const countryValues = useMemo(
    () => new Map((data?.countries || []).map((country) => [country.iso3, country])),
    [data],
  );
  const countryDetails = countryValues.get(selectedCountry);
  const sourceLabel = selectedSource === 'glass' ? 'WHO GLASS-AMR' : 'ECDC EARS-Net';

  function choosePathogen(nextPathogen) {
    const nextAntibiotic = data?.pathogen === nextPathogen
      ? antibiotic
      : '';
    setLoading(true);
    setError('');
    loadOverview(selectedSource, nextPathogen, nextAntibiotic);
  }

  function chooseAntibiotic(nextAntibiotic) {
    setLoading(true);
    setError('');
    loadOverview(selectedSource, pathogen, nextAntibiotic);
  }

  function handleMapKeyDown(event, iso3) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setSelectedCountry(iso3);
    }
  }

  return (
    <div className="intelligence-page">
      <header className="intelligence-heading">
        <div>
          <div className="intelligence-eyebrow"><Globe2 size={15} /> AMR-SENSE · SURVEILLANCE SNAPSHOT</div>
          <h1>Resistance at a glance</h1>
          <p>See where resistance is highest, which reports are rising, and what the surveillance data covers.</p>
        </div>
        <div className="intelligence-source">
          <label htmlFor="intelligence-source">Reporting source</label>
          <select
            id="intelligence-source"
            className="form-select"
            value={selectedSource}
            onChange={(event) => {
              setLoading(true);
              setError('');
              setSelectedSource(event.target.value);
            }}
          >
            <option value="glass">WHO GLASS-AMR</option>
            <option value="ecdc">ECDC EARS-Net</option>
          </select>
        </div>
      </header>

      <div className="intelligence-note">
        <AlertTriangle size={17} />
        <span>
          Sources are shown separately because GLASS reports resistant bacteria (R), while ECDC reports
          intermediate plus resistant bacteria (I+R). Map values are each country’s latest report, not necessarily
          from the same year.
        </span>
      </div>

      <section className="card intelligence-map-card">
        <div className="intelligence-map-header">
          <div>
            <h2>Latest reported resistance</h2>
            <p>Choose a bacterium and antibiotic. Click a country for its latest value and report year.</p>
          </div>
          <div className="intelligence-filters">
            <label>
              <span>Bacterium</span>
              <select
                className="form-select"
                value={pathogen}
                disabled={!data?.pathogens?.length || loading}
                onChange={(event) => choosePathogen(event.target.value)}
              >
                {(data?.pathogens || []).map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <label>
              <span>Antibiotic</span>
              <select
                className="form-select"
                value={antibiotic}
                disabled={!data?.antibiotics?.length || loading}
                onChange={(event) => chooseAntibiotic(event.target.value)}
              >
                {(data?.antibiotics || []).map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          </div>
        </div>

        {error && <div className="intelligence-error" role="alert">{error}</div>}
        {mapError && <div className="intelligence-error" role="alert">{mapError}</div>}

        <div className="intelligence-map-layout">
          <div className="intelligence-map-wrap">
            {loading && <div className="intelligence-map-loading">Loading country reports…</div>}
            <svg
              className="intelligence-map"
              viewBox="0 0 1000 500"
              role="img"
              aria-label={`World map of latest ${data?.pathogen || ''} resistance to ${data?.antibiotic || ''}`}
            >
              {geometry.map((feature) => {
                const { iso3, name } = feature.properties;
                const value = countryValues.get(iso3);
                const isSelected = selectedCountry === iso3;
                return (
                  <path
                    key={iso3 || name}
                    d={geometryPath(feature.geometry)}
                    fill={value ? resistanceColor(value.pct_resistant) : '#1a293b'}
                    className={`intelligence-country${isSelected ? ' selected' : ''}`}
                    role="button"
                    tabIndex={0}
                    aria-label={`${name}${value ? `, ${value.pct_resistant.toFixed(1)} percent, ${value.year}` : ', no matching report'}`}
                    onClick={() => value && setSelectedCountry(iso3)}
                    onKeyDown={(event) => value && handleMapKeyDown(event, iso3)}
                  >
                    <title>
                      {name}{value
                        ? ` · ${value.pct_resistant.toFixed(1)}% · ${value.year} · n=${Math.round(value.number_tested)}`
                        : ' · No matching report'}
                    </title>
                  </path>
                );
              })}
            </svg>
            <div className="intelligence-map-legend" aria-label="Resistance percentage legend">
              <span><i style={{ background: '#2b7484' }} />0–19%</span>
              <span><i style={{ background: '#b18a3d' }} />20–39%</span>
              <span><i style={{ background: '#c5653d' }} />40–59%</span>
              <span><i style={{ background: '#bd454d' }} />60–100%</span>
              <span><i className="no-report" />No report</span>
            </div>
            <div className="intelligence-map-attribution">Country boundaries: Natural Earth, public domain.</div>
          </div>

          <aside className="intelligence-country-panel">
            {countryDetails ? (
              <>
                <div className="intelligence-country-icon"><MapPin size={18} /></div>
                <span className="intelligence-panel-label">SELECTED COUNTRY</span>
                <h3>{countryDetails.country}</h3>
                <div className="intelligence-country-value" style={{ color: resistanceColor(countryDetails.pct_resistant) }}>
                  {countryDetails.pct_resistant.toFixed(1)}%
                </div>
                <p>Reported resistance in {countryDetails.year}</p>
                <div className="intelligence-country-meta">
                  <span>Bacterium</span><strong>{countryDetails.pathogen}</strong>
                  <span>Antibiotic</span><strong>{countryDetails.antibiotic}</strong>
                  <span>Tests reported</span><strong>{Math.round(countryDetails.number_tested).toLocaleString()}</strong>
                  <span>Source</span><strong>{sourceLabel}</strong>
                </div>
              </>
            ) : (
              <div className="intelligence-country-empty">
                <MapPin size={22} />
                <strong>Select a colored country</strong>
                <span>The map shows the latest available report for this bacterium and antibiotic.</span>
              </div>
            )}
          </aside>
        </div>
      </section>

      <div className="intelligence-summary-grid">
        <section className="card intelligence-summary-card">
          <div className="intelligence-card-title">
            <span className="intelligence-icon-hotspot">!</span>
            <div><h2>Highest reported levels</h2><p>Latest report by country · at least {data?.minimum_tests_for_rankings ?? 30} tests</p></div>
          </div>
          {data?.hotspots?.length ? (
            <ol className="intelligence-ranking">
              {data.hotspots.map((row) => (
                <li key={row.iso3}>
                  <button type="button" onClick={() => setSelectedCountry(row.iso3)}>
                    <span className="intelligence-rank-country"><b>{row.country}</b><small>{row.iso3} · {row.year}</small></span>
                    <strong style={{ color: resistanceColor(row.pct_resistant) }}>{row.pct_resistant.toFixed(1)}%</strong>
                  </button>
                </li>
              ))}
            </ol>
          ) : <p className="intelligence-empty">No country reports meet the minimum test count for this selection.</p>}
        </section>

        <section className="card intelligence-summary-card">
          <div className="intelligence-card-title">
            <span className="intelligence-icon-rise"><TrendingUp size={17} /></span>
            <div><h2>Largest recent increases</h2><p>Change between the latest two consecutive years, with 30+ tests in both</p></div>
          </div>
          {data?.fastest_rising?.length ? (
            <ol className="intelligence-ranking">
              {data.fastest_rising.map((row) => (
                <li key={`${row.iso3}-${row.pathogen}-${row.antibiotic}`}>
                  <button type="button" onClick={() => setSelectedCountry(row.iso3)}>
                    <span className="intelligence-rank-country"><b>{row.country}</b><small>{row.from_year} → {row.to_year} · {row.previous_pct.toFixed(1)}% to {row.latest_pct.toFixed(1)}%</small></span>
                    <strong className="intelligence-rise-value">+{row.change_pp.toFixed(1)} pp</strong>
                  </button>
                </li>
              ))}
            </ol>
          ) : <p className="intelligence-empty">No consecutive-year increases with enough tests were found for this selection.</p>}
          <p className="intelligence-footnote">These are observed changes, not predictions or statistical significance tests.</p>
        </section>
      </div>

      <section className="card intelligence-pathogens">
        <div className="intelligence-card-title">
          <div><h2>Most commonly reported bacteria</h2><p>Ranked by country coverage in this source; this is not a ranking of danger.</p></div>
        </div>
        <div className="intelligence-pathogen-list">
          {(data?.important_pathogens || []).map((item, index) => (
            <div className="intelligence-pathogen" key={item.name}>
              <span className="intelligence-pathogen-number">{String(index + 1).padStart(2, '0')}</span>
              <strong>{item.name}</strong>
              <span>{item.countries_reporting} countries</span>
              <small>latest report: {item.latest_year}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="intelligence-findings">
        <div className="intelligence-findings-heading">
          <span>KEY FINDINGS</span>
          <strong>{pathogen} · {antibiotic}</strong>
        </div>
        <ul>
          {(data?.key_findings || []).map((finding) => <li key={finding}>{finding}</li>)}
        </ul>
      </section>

      <p className="intelligence-disclaimer">{data?.disclaimer || 'Surveillance summary only; do not use for treatment decisions.'}</p>
    </div>
  );
}
