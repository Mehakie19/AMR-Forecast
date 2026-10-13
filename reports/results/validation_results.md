# Validation results

> **Surveillance and research tool only.** Not for treatment decisions. High-risk and rising thresholds are project-defined.

## Configuration: `glass`

### Target: `high_risk_next`

| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |
|---|---|---|---|---|---|---|---|
| **Baseline** | 0.9179 [0.8666, 0.9577] | 0.9291 | 0.937 | 0.931 | 0.073 | 0.0707 | ref |
| LR | 0.9850 [0.9658, 0.9957] | 0.9820 | 0.948 | 0.972 | 0.103 | 0.0526 | +0.0671 [+0.0375, +0.1034] |
| RF | 0.9806 [0.9451, 0.9970] | 0.9806 | 0.948 | 0.959 | 0.085 | 0.0466 | +0.0627 [+0.0348, +0.0994] |
| XGB | 0.9866 [0.9688, 0.9969] | 0.9837 | 0.953 | 0.972 | 0.091 | 0.0459 | +0.0686 [+0.0389, +0.1074] |
| VOTING | 0.9867 [0.9661, 0.9971] | 0.9841 | 0.950 | 0.954 | 0.073 | 0.0458 | +0.0687 [+0.0390, +0.1062] |
| STACKING | 0.9868 [0.9660, 0.9971] | 0.9842 | 0.950 | 0.954 | 0.073 | 0.0474 | +0.0688 [+0.0390, +0.1065] |

- Stacking meta-training excluded **352** training rows lacking full out-of-fold history.
- Stacking meta-learner weights (LR, RF, XGB): `[np.float64(2.612), np.float64(2.846), np.float64(2.525)]`

### Target: `rising_next`

| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |
|---|---|---|---|---|---|---|---|
| **Baseline** | 0.1331 [0.0831, 0.1994] | 0.4383 | 0.097 | 0.130 | 0.253 | 0.3403 | ref |
| LR | 0.5476 [0.2511, 0.7447] | 0.8108 | 0.496 | 0.537 | 0.104 | 0.1960 | +0.4145 [+0.1556, +0.5723] |
| RF | 0.4747 [0.2420, 0.6781] | 0.8424 | 0.514 | 0.500 | 0.073 | 0.2087 | +0.3416 [+0.1461, +0.5062] |
| XGB | 0.4036 [0.2026, 0.6222] | 0.8312 | 0.490 | 0.463 | 0.070 | 0.1898 | +0.2705 [+0.1078, +0.4550] |
| VOTING | 0.5638 [0.2412, 0.7684] | 0.8474 | 0.552 | 0.593 | 0.091 | 0.1909 | +0.4306 [+0.1453, +0.5917] |
| STACKING | 0.5481 [0.2302, 0.7559] | 0.8482 | 0.545 | 0.611 | 0.104 | 0.1030 | +0.4149 [+0.1384, +0.5772] |

- Stacking meta-training excluded **352** training rows lacking full out-of-fold history.
- Stacking meta-learner weights (LR, RF, XGB): `[np.float64(1.027), np.float64(1.186), np.float64(1.654)]`

### Companion Regression (`y_reg`)

| Model | MAE (pp) | RMSE (pp) | Beat Persistence Share |
|---|---|---|---|
| persistence | 6.331 | 10.962 | 0.0% |
| roll_mean_2 | 5.425 | 8.952 | 53.9% |
| ridge | 6.319 | 9.480 | 42.1% |
| xgb_reg | 6.397 | 10.125 | 41.6% |

## Configuration: `ecdc`

### Target: `high_risk_next`

| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |
|---|---|---|---|---|---|---|---|
| **Baseline** | 0.9364 [0.9035, 0.9581] | 0.9708 | 0.961 | 0.961 | 0.019 | 0.0258 | ref |
| LR | 0.9954 [0.9908, 0.9977] | 0.9976 | 0.966 | 0.956 | 0.012 | 0.0546 | +0.0590 [+0.0391, +0.0885] |
| RF | 0.9939 [0.9883, 0.9975] | 0.9968 | 0.971 | 0.976 | 0.017 | 0.0260 | +0.0576 [+0.0377, +0.0860] |
| XGB | 0.9958 [0.9915, 0.9981] | 0.9978 | 0.976 | 0.980 | 0.014 | 0.0290 | +0.0594 [+0.0393, +0.0890] |
| VOTING | 0.9957 [0.9918, 0.9979] | 0.9978 | 0.971 | 0.980 | 0.019 | 0.0302 | +0.0593 [+0.0391, +0.0892] |
| STACKING | 0.9958 [0.9918, 0.9980] | 0.9978 | 0.971 | 0.980 | 0.019 | 0.0193 | +0.0594 [+0.0391, +0.0893] |

- Stacking meta-training excluded **1129** training rows lacking full out-of-fold history.
- Stacking meta-learner weights (LR, RF, XGB): `[np.float64(4.01), np.float64(3.643), np.float64(2.9)]`

### Target: `rising_next`

| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |
|---|---|---|---|---|---|---|---|
| **Baseline** | 0.0442 [0.0259, 0.0664] | 0.4842 | 0.044 | 0.071 | 0.103 | 0.1403 | ref |
| LR | 0.1891 [0.0901, 0.3629] | 0.7105 | 0.250 | 0.214 | 0.024 | 0.2177 | +0.1449 [+0.0456, +0.3258] |
| RF | 0.0883 [0.0541, 0.1694] | 0.7445 | 0.146 | 0.321 | 0.145 | 0.1770 | +0.0441 [+0.0180, +0.1228] |
| XGB | 0.1095 [0.0634, 0.2287] | 0.7581 | 0.177 | 0.464 | 0.179 | 0.1842 | +0.0653 [+0.0239, +0.1850] |
| VOTING | 0.1582 [0.0810, 0.3153] | 0.7482 | 0.245 | 0.214 | 0.025 | 0.1882 | +0.1140 [+0.0363, +0.2663] |
| STACKING | 0.1556 [0.0777, 0.2991] | 0.7513 | 0.215 | 0.250 | 0.051 | 0.0416 | +0.1114 [+0.0353, +0.2595] |

- Stacking meta-training excluded **1129** training rows lacking full out-of-fold history.
- Stacking meta-learner weights (LR, RF, XGB): `[np.float64(1.165), np.float64(1.176), np.float64(1.817)]`

### Companion Regression (`y_reg`)

| Model | MAE (pp) | RMSE (pp) | Beat Persistence Share |
|---|---|---|---|
| persistence | 2.560 | 4.209 | 0.0% |
| roll_mean_2 | 2.586 | 4.234 | 49.0% |
| ridge | 2.701 | 4.250 | 44.4% |
| xgb_reg | 2.793 | 4.496 | 41.6% |

## Configuration: `pooled`

### Target: `high_risk_next`

| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |
|---|---|---|---|---|---|---|---|
| **Baseline** | 0.9233 [0.8908, 0.9490] | 0.9555 | 0.949 | 0.945 | 0.034 | 0.0429 | ref |
| LR | 0.9889 [0.9795, 0.9955] | 0.9926 | 0.956 | 0.955 | 0.031 | 0.0382 | +0.0656 [+0.0446, +0.0907] |
| RF | 0.9853 [0.9655, 0.9960] | 0.9916 | 0.955 | 0.964 | 0.040 | 0.0343 | +0.0620 [+0.0415, +0.0875] |
| XGB | 0.9895 [0.9785, 0.9964] | 0.9930 | 0.958 | 0.964 | 0.036 | 0.0357 | +0.0662 [+0.0451, +0.0922] |
| VOTING | 0.9897 [0.9780, 0.9962] | 0.9932 | 0.958 | 0.962 | 0.034 | 0.0347 | +0.0664 [+0.0451, +0.0920] |
| STACKING | 0.9897 [0.9781, 0.9962] | 0.9932 | 0.958 | 0.962 | 0.034 | 0.0314 | +0.0664 [+0.0451, +0.0920] |

- Stacking meta-training excluded **2458** training rows lacking full out-of-fold history.
- Stacking meta-learner weights (LR, RF, XGB): `[np.float64(2.934), np.float64(2.899), np.float64(2.766)]`

### Target: `rising_next`

| Model | PR-AUC (95% CI) | ROC-AUC | F1 | Recall | FAR | Brier | Diff vs Baseline (95% CI) |
|---|---|---|---|---|---|---|---|
| **Baseline** | 0.0793 [0.0550, 0.1109] | 0.4766 | 0.077 | 0.110 | 0.157 | 0.2166 | ref |
| LR | 0.4308 [0.2001, 0.6272] | 0.7837 | 0.435 | 0.451 | 0.055 | 0.2088 | +0.3515 [+0.1317, +0.5331] |
| RF | 0.3460 [0.1751, 0.5409] | 0.8214 | 0.397 | 0.329 | 0.029 | 0.2166 | +0.2667 [+0.1051, +0.4394] |
| XGB | 0.4200 [0.2082, 0.6281] | 0.8332 | 0.432 | 0.427 | 0.049 | 0.2106 | +0.3407 [+0.1428, +0.5326] |
| VOTING | 0.4725 [0.2301, 0.6648] | 0.8234 | 0.471 | 0.451 | 0.041 | 0.2052 | +0.3932 [+0.1654, +0.5642] |
| STACKING | 0.4727 [0.2304, 0.6641] | 0.8221 | 0.454 | 0.451 | 0.048 | 0.0636 | +0.3934 [+0.1640, +0.5644] |

- Stacking meta-training excluded **2458** training rows lacking full out-of-fold history.
- Stacking meta-learner weights (LR, RF, XGB): `[np.float64(2.075), np.float64(1.572), np.float64(2.118)]`

### Companion Regression (`y_reg`)

| Model | MAE (pp) | RMSE (pp) | Beat Persistence Share |
|---|---|---|---|
| persistence | 3.997 | 7.535 | 0.0% |
| roll_mean_2 | 3.668 | 6.453 | 50.9% |
| ridge | 3.924 | 6.711 | 46.6% |
| xgb_reg | 4.053 | 6.904 | 43.2% |
