# Regularization evidence

> Compares training vs validation scores (the overfitting gap) across regularization controls.

## Configuration: `glass`

| Model & Regularization Setting | Train PR-AUC | Val PR-AUC | Overfitting Gap (Train - Val) |
|---|---|---|---|
| LR (none) | 0.9916 | 0.9835 | +0.0081 |
| LR (L2, C=1.0) | 0.9907 | 0.9846 | +0.0061 |
| LR (L1, C=0.1) | 0.9893 | 0.9858 | +0.0035 |
| LR (ElasticNet, C=0.5, l1=0.5) | 0.9903 | 0.9847 | +0.0056 |
| XGBoost (default reg, depth=6) | 0.9996 | 0.9830 | +0.0165 |
| XGBoost (tuned reg, depth=3) | 0.9969 | 0.9841 | +0.0128 |
| Random Forest (min_samples_leaf=1) | 1.0000 | 0.9675 | +0.0325 |
| Random Forest (min_samples_leaf=10) | 0.9951 | 0.9837 | +0.0114 |

- L1-regularized Logistic Regression retained **10** nonzero coefficients (sparsity evidence).

## Configuration: `ecdc`

| Model & Regularization Setting | Train PR-AUC | Val PR-AUC | Overfitting Gap (Train - Val) |
|---|---|---|---|
| LR (none) | 0.9792 | 0.9933 | -0.0141 |
| LR (L2, C=1.0) | 0.9790 | 0.9933 | -0.0143 |
| LR (L1, C=0.1) | 0.9773 | 0.9943 | -0.0170 |
| LR (ElasticNet, C=0.5, l1=0.5) | 0.9784 | 0.9936 | -0.0152 |
| XGBoost (default reg, depth=6) | 0.9983 | 0.9884 | +0.0099 |
| XGBoost (tuned reg, depth=3) | 0.9913 | 0.9923 | -0.0010 |
| Random Forest (min_samples_leaf=1) | 1.0000 | 0.9913 | +0.0087 |
| Random Forest (min_samples_leaf=10) | 0.9888 | 0.9930 | -0.0042 |

- L1-regularized Logistic Regression retained **10** nonzero coefficients (sparsity evidence).

## Configuration: `pooled`

| Model & Regularization Setting | Train PR-AUC | Val PR-AUC | Overfitting Gap (Train - Val) |
|---|---|---|---|
| LR (none) | 0.9834 | 0.9881 | -0.0048 |
| LR (L2, C=1.0) | 0.9832 | 0.9881 | -0.0049 |
| LR (L1, C=0.1) | 0.9824 | 0.9883 | -0.0060 |
| LR (ElasticNet, C=0.5, l1=0.5) | 0.9830 | 0.9881 | -0.0050 |
| XGBoost (default reg, depth=6) | 0.9989 | 0.9897 | +0.0093 |
| XGBoost (tuned reg, depth=3) | 0.9930 | 0.9893 | +0.0036 |
| Random Forest (min_samples_leaf=1) | 1.0000 | 0.9825 | +0.0175 |
| Random Forest (min_samples_leaf=10) | 0.9928 | 0.9899 | +0.0029 |

- L1-regularized Logistic Regression retained **17** nonzero coefficients (sparsity evidence).

## Ensemble mechanisms in AMR surveillance

- **Soft Voting (variance reduction):** Bagging and averaging smooths out sampling noise and variance from sparse isolates.
- **XGBoost (bias reduction):** Gradient boosting refines decision boundaries around complex multi-drug resistance phenotypes.
- **Stacking (error diversity):** Stacking leverages complementary error profiles between linear and tree-based representations.
