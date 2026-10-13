# EDA findings

## GLASS (GLASS-AMR)

- Rows: **2394**; countries: **31**; years **2018–2023**.
- Share rows with `number_tested < 30`: **5.30%**.
- Year-on-year change SD: **10.16 pp**; share rises ≥ 5 pp: **22.0%**.
- Persistence MAE (all consecutive pairs): **6.09 pp**.
- Classification-eligible rows: **1867**; high_risk_next (T=30) prevalence **56.4%**; rising_next **16.9%**.

## ECDC (ECDC-EARSNet(Zenodo))

- Rows: **4240**; countries: **27**; years **1999–2019**.
- Share rows with `number_tested < 30`: **0.00%**.
- Year-on-year change SD: **4.69 pp**; share rises ≥ 5 pp: **9.3%**.
- Persistence MAE (all consecutive pairs): **2.70 pp**.
- Classification-eligible rows: **3879**; high_risk_next (T=30) prevalence **23.1%**; rising_next **6.7%**.

## COVID-era check (combined)

Mean YoY change by calendar year (all sources):

- 1999: **nan pp**
- 2000: **1.19 pp**
- 2001: **0.18 pp**
- 2002: **0.89 pp**
- 2003: **0.89 pp**
- 2004: **1.17 pp**
- 2005: **0.63 pp**
- 2006: **0.85 pp**
- 2007: **1.61 pp**
- 2008: **1.56 pp**
- 2009: **1.02 pp**
- 2010: **0.46 pp**
- 2011: **1.28 pp**
- 2012: **0.15 pp**
- 2013: **0.06 pp**
- 2014: **-0.19 pp**
- 2015: **0.60 pp**
- 2016: **0.52 pp**
- 2017: **0.17 pp**
- 2018: **-0.55 pp**
- 2019: **1.28 pp**
- 2020: **2.18 pp**
- 2021: **0.41 pp**
- 2022: **0.03 pp**
- 2023: **0.16 pp**

2020 mean YoY change: **2.18 pp** (flagged via `covid_flag` in modeling; not dropped).

## Data issues that affect modeling

1. **Definition mismatch:** ECDC uses I+R; GLASS uses R as reported — do not compare levels across sources.
2. **Malta overlap:** 8 rows with `key_overlap=True`; excluded from pooled training per config.
3. **GLASS reporting filter:** participating countries may over-represent better reporters.
4. **Small sample sizes (GLASS):** ~5% of rows have n<30; increases YoY noise vs ECDC.
5. **Short GLASS panel:** only 2018–2023 limits temporal features for some series.
6. **COVID 2020:** potential surveillance disruption; modeled with `covid_flag`.
7. **Pooled temporal overlap:** GLASS train years 2019–2021 overlap calendar years with held-out ECDC 2018–2019.
