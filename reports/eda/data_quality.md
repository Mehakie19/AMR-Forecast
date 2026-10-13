# Data quality report

Single source of truth: `data/raw/combined_amr_dataset.csv`.

## Provenance

Original `ML_DATASET.csv` and `summary_AMR_filtered.csv` were **not** present in this workspace; row-level reproduction against those files was skipped.

## Expected-value assertions

- All expected-value checks matched.

## Row counts per source

| Source | Rows |
|--------|------|
| GLASS-AMR | 2394 |
| ECDC-EARSNet(Zenodo) | 4240 |
| **Total** | 6634 |

## Missing values (column counts)

- `ast_coverage`: 4240 (63.91%)

## Duplicates on `source, iso3, year, pathogen, antibiotic`

Duplicate row count (including pairs): **0**

## Count consistency

Rows with `number_resistant > number_tested`: **0**
Rows where recomputed `pct_resistant` differs from stored by >0.01 pp: **0**

## Sample size (`number_tested < 30`)

- **GLASS-AMR**: 5.30% of rows (127 rows)
- **ECDC-EARSNet(Zenodo)**: 0.00% of rows (0 rows)

## Series length distribution

### GLASS-AMR
- Series count: 399
- Min / median / max years per series: 6 / 6 / 6

### ECDC-EARSNet(Zenodo)
- Series count: 322
- Min / median / max years per series: 6 / 14 / 21


## Countries per source and year

### GLASS-AMR
- Countries per year: min 31, max 31, median 31
- Unique countries (overall): 31

### ECDC-EARSNet(Zenodo)
- Countries per year: min 2, max 27, median 25
- Unique countries (overall): 27


## Malta overlap (`key_overlap=True`)

| source               | iso3   | country   |   year | pathogen         | antibiotic    |   pct_resistant |   number_tested |
|:---------------------|:-------|:----------|-------:|:-----------------|:--------------|----------------:|----------------:|
| ECDC-EARSNet(Zenodo) | MLT    | Malta     |   2018 | Escherichia coli | Ceftazidime   |         12.8    |             125 |
| GLASS-AMR            | MLT    | Malta     |   2018 | Escherichia coli | Ceftazidime   |         10.2273 |             352 |
| ECDC-EARSNet(Zenodo) | MLT    | Malta     |   2018 | Escherichia coli | Ciprofloxacin |         45.6    |             125 |
| GLASS-AMR            | MLT    | Malta     |   2018 | Escherichia coli | Ciprofloxacin |         43.1818 |             352 |
| ECDC-EARSNet(Zenodo) | MLT    | Malta     |   2019 | Escherichia coli | Ceftazidime   |         20      |             150 |
| GLASS-AMR            | MLT    | Malta     |   2019 | Escherichia coli | Ceftazidime   |         17.0391 |             358 |
| ECDC-EARSNet(Zenodo) | MLT    | Malta     |   2019 | Escherichia coli | Ciprofloxacin |         44      |             150 |
| GLASS-AMR            | MLT    | Malta     |   2019 | Escherichia coli | Ciprofloxacin |         41.3408 |             358 |