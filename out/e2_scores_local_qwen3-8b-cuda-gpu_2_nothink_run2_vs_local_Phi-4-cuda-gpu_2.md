| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.7714 | 0.0 | 0 | 0.236 | 3.866 |
| all-cloud | 0.7571 | 0.8571 | 0.0 | 0.487 | 7.919 |
| rule | 0.8357 | 0.5714 | 0.0 | 0.265 | 7.155 |
| second-only | 0.75 | 1.0 | 0.0 | 0.532 | 7.919 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.75 | 0.725 | 0.725 | 1.0 |
| all-cloud | 0.925 | 0.45 | 0.775 | 1.0 |
| rule | 0.925 | 0.725 | 0.775 | 1.0 |
| second-only | 0.925 | 0.45 | 0.775 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: -0.014 [-0.093, +0.071]
- rule - all-local: +0.064 [+0.007, +0.121]
- second-only - all-local: -0.021 [-0.100, +0.064]
- rule - all-cloud: +0.079 [+0.021, +0.136]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- second-only - rule: -0.086 [-0.143, -0.029]
