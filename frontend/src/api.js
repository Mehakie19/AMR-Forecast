/**
 * AMR-Sense API client for Vite Frontend.
 * Uses the Vite API proxy by default; configure VITE_API_BASE_URL for other hosts.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function fetchJson(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!res.ok) {
      let detail = `Request failed (${res.status})`;
      try { detail = (await res.json()).detail || detail; } catch { /* response may not be JSON */ }
      throw new Error(detail);
    }
    return await res.json();
  } catch (err) {
    if (err instanceof TypeError) throw new Error(`Cannot reach AMR-Sense API at ${API_BASE}. Start FastAPI and try again.`);
    throw err;
  }
}

export const api = {
  getHealth: () => fetchJson('/health'),
  getDatasetsSummary: (source = 'combined') => fetchJson(`/datasets/summary?source=${source}`),
  getDatasetsCoverage: (source = 'combined', pathogen = '', antibiotic = '') => {
    const q = new URLSearchParams({ source });
    if (pathogen) q.set('pathogen', pathogen);
    if (antibiotic) q.set('antibiotic', antibiotic);
    return fetchJson(`/datasets/coverage?${q}`);
  },
  getDatasetsQuality: () => fetchJson('/datasets/quality'),
  getEdaDistribution: (source = 'combined') => fetchJson(`/eda/distribution?source=${source}`),
  getEdaTrend: (source = 'combined') => fetchJson(`/eda/trend?source=${source}`),
  getEdaSampleSize: (source = 'combined') => fetchJson(`/eda/sample-size?source=${source}`),
  getEdaClassBalance: (source = 'combined') => fetchJson(`/eda/class-balance?source=${source}`),
  getEdaCorrelation: (source = 'combined', pathogen = 'Klebsiella pneumoniae') =>
    fetchJson(`/eda/correlation?source=${source === 'combined' ? 'glass' : source}&pathogen=${encodeURIComponent(pathogen)}`),
  getEdaYearChange: (source = 'combined') => fetchJson(`/eda/year-change?source=${source}`),
  getFeaturesDictionary: () => fetchJson('/features/dictionary'),
  getFeaturesImportance: (source = 'combined') => fetchJson(`/features/importance-preview?source=${source}`),
  getResultsComparison: (config = 'glass', target = 'high_risk_next', split = 'validation') =>
    fetchJson(`/results/comparison?config=${config}&target=${target}&split=${split}`),
  getResultsCurves: (config = 'glass', target = 'high_risk_next', model = 'xgb') =>
    fetchJson(`/results/curves?config=${config}&target=${target}&model=${model}`),
  getResultsRegularization: () => fetchJson('/results/regularization'),
  getResultsTuning: (config = 'glass') => fetchJson(`/results/tuning?config=${config}`),
  getResultsEnsembles: (config = 'glass') => fetchJson(`/results/ensembles?config=${config}`),
  getResultsSegments: (config = 'glass', target = 'high_risk_next') => fetchJson(`/results/segments?config=${config}&target=${target}`),
  getResultsErrors: (config = 'glass') => fetchJson(`/results/errors?config=${config}`),
  getResultsThresholdSensitivity: () => fetchJson('/results/threshold-sensitivity'),
  getResultsPooledVsSeparate: () => fetchJson('/results/pooled-vs-separate'),
  getSeriesHistory: (source, iso3, pathogen, antibiotic) => {
    const q = new URLSearchParams({ source, iso3, pathogen, antibiotic });
    return fetchJson(`/series?${q}`);
  },
  getSeriesOptions: (source) => fetchJson(`/series/options?source=${source}`),
  predictSeries: (payload) =>
    fetchJson('/predict', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getWatchlist: (params = {}) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') sp.append(k, v);
    });
    return fetchJson(`/watchlist?${sp.toString()}`);
  },
  getMethods: () => fetchJson('/methods'),
};
