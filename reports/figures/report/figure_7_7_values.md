| Maximum depth | Validation PR-AUC | Validation ROC-AUC |
|---:|---:|---:|
| 1 | 0.9156 | 0.9315 |
| 2 | 0.9489 | 0.9605 |
| 3 | 0.9455 | 0.9502 |
| 5 | 0.9512 | 0.9550 |
| 8 | 0.8936 | 0.9056 |
| 12 | 0.8746 | 0.8910 |
| unlimited | 0.8746 | 0.8910 |

Coefficient counts use absolute-value tolerance `1e-05`.
L1 is the Lasso penalty; L2 is Ridge-type regularization, not Lasso.
Tree depth is a supplementary single-tree diagnostic; the project also compares Random Forest models.
PR/ROC and probability-threshold plots use the held-out GLASS test split. The LR cutoff is selected from validation data.

| C | L1 non-zero coefficients | L2 non-zero coefficients |
|---:|---:|---:|
| 0.01 | 3 | 45 |
| 0.1 | 10 | 45 |
| 1 | 21 | 45 |
| 10 | 39 | 45 |
