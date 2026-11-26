| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.75 | 0.0 | 0 | 0.238 | 5.497 |
| all-cloud | 0.7571 | 0.8571 | 0.0 | 0.487 | 7.919 |
| rule | 0.8286 | 0.5714 | 0.0 | 0.272 | 7.155 |
| second-only | 0.75 | 1.0 | 0.0 | 0.532 | 7.919 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.775 | 0.7 | 0.65 | 1.0 |
| all-cloud | 0.925 | 0.45 | 0.775 | 1.0 |
| rule | 0.925 | 0.7 | 0.775 | 1.0 |
| second-only | 0.925 | 0.45 | 0.775 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.007 [-0.071, +0.093]
- rule - all-local: +0.079 [+0.021, +0.136]
- second-only - all-local: +0.000 [-0.079, +0.086]
- rule - all-cloud: +0.071 [+0.014, +0.129]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- second-only - rule: -0.079 [-0.136, -0.021]
