# Feature dictionary

| Name | Group | Availability | Definition | Justification |
|------|-------|--------------|------------|---------------|
| lag_1 | temporal | derived | pct_resistant at t-1 (consecutive year only). | Persistence is a strong AMR baseline; last observed resistance anchors forecasts. |
| lag_2 | temporal | derived | pct_resistant at t-2 when consecutive. | Two-year history helps detect acceleration beyond single-year noise. |
| delta_1 | temporal | derived | lag_1 minus lag_2. | Recent momentum complements level for rising-resistance detection. |
| roll_mean_2 | temporal | derived | Mean of resistance in last two observed years before t. | Smooths single-year sampling noise in surveillance counts. |
| roll_std_2 | temporal | derived | Std dev of last two years before t. | Volatile series may need different alert thresholds in review. |
| hist_max | temporal | derived | Maximum pct_resistant in years < t. | Historical peaks indicate prior selection pressure in the population. |
| hist_min | temporal | derived | Minimum pct_resistant in years < t. | Floor resistance contextualizes how far a series has already risen. |
| years_observed | temporal | derived | Count of years with data strictly before t. | Maturity of surveillance series affects forecast reliability. |
| has_lag2 | temporal | derived | 1 if lag_2 is available. | Flags when two-year dynamics features are defined. |
| log_tested | sample quality | derived | log1p(number_tested at t-1). | Larger denominators stabilize proportion estimates in surveillance. |
| ast_coverage | sample quality | direct (GLASS) | GLASS AST coverage at t-1 row. | Incomplete testing can bias apparent resistance levels. |
| wilson_width | sample quality | derived | 95% Wilson interval width from t-1 counts. | Quantifies uncertainty in the lagged resistance estimate. |
| n_ge_30_prev | sample quality | derived | 1 if number_tested at t-1 >= 30. | WHO-style minimum denominators for reliable proportions. |
| class_mean_other | cross-resistance | derived | Mean resistance of other drugs same ATC class at t-1. | Class-level co-resistance is common in Gram-negative surveillance. |
| other_mean_all | cross-resistance | derived | Mean resistance of all other antibiotics at t-1. | Background multidrug resistance signals ecosystem pressure. |
| n_high_other | cross-resistance | derived | Count of other antibiotics with resistance >= T at t-1. | Counts co-resistant drugs relevant to multidrug phenotypes. |
| mdr_burden | cross-resistance | derived | n_high_other divided by number of other antibiotics observed. | Normalizes multidrug burden to comparable scale across pathogens. |
| pathogen | context | direct | Pathogen name. | Species drives intrinsic resistance mechanisms and trends. |
| antibiotic | context | direct | Antibiotic name. | Drug-specific epidemiology varies by mechanism and usage. |
| antibiotic_class | context | direct | ATC level-3 class. | Groups agents with related resistance pathways. |
| who_region | context | direct (GLASS) | WHO region (GLASS only). | Regional policies and circulation patterns differ globally. |
| region_median_prev | context | derived | Median resistance for pathogen x antibiotic across countries at t-1 within source. | Peer benchmark for whether a country is an outlier. |
| gap_from_region_prev | context | derived | lag_1 minus region_median_prev. | Relative elevation may persist or mean-revert differently. |
| covid_flag | flags | derived | 1 if target year is 2020. | Pandemic years disrupted sampling and hospital mix. |
| is_glass | flags | derived (pooled) | 1 if row is GLASS. | Lets pooled models respect source-specific measurement. |
| ecdc_definition_ipr | flags | derived (pooled) | 1 if row is ECDC (I+R definition). | Captures systematic definition difference in pooled training. |