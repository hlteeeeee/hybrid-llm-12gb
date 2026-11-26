| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.8286 | 0.0 | 0 | 0.356 | 4.096 |
| all-cloud | 0.75 | 0.8571 | 0.0 | 0.527 | 7.919 |
| rule | 0.8286 | 0.5714 | 0.0 | 0.39 | 7.155 |
| second-only | 0.75 | 1.0 | 0.0 | 0.532 | 7.919 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.9 | 0.725 | 0.8 | 0.95 |
| all-cloud | 0.925 | 0.45 | 0.775 | 0.95 |
| rule | 0.925 | 0.725 | 0.775 | 0.95 |
| second-only | 0.925 | 0.45 | 0.775 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: -0.079 [-0.143, -0.014]
- rule - all-local: +0.000 [-0.043, +0.043]
- second-only - all-local: -0.079 [-0.143, -0.007]
- rule - all-cloud: +0.079 [+0.036, +0.129]
- second-only - all-cloud: +0.000 [-0.021, +0.021]
- second-only - rule: -0.079 [-0.136, -0.029]
