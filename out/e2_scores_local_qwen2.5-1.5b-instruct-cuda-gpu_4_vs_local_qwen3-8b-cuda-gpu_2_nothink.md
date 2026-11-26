| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.5571 | 0.0 | 0 | 0.051 | 1.073 |
| all-cloud | 0.7429 | 0.8571 | 0.0 | 0.213 | 5.497 |
| rule | 0.7429 | 0.8571 | 0.0 | 0.213 | 5.497 |
| second-only | 0.75 | 1.0 | 0.0 | 0.238 | 5.497 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.525 | 0.725 | 0.225 | 0.95 |
| all-cloud | 0.775 | 0.7 | 0.65 | 0.95 |
| rule | 0.775 | 0.7 | 0.65 | 0.95 |
| second-only | 0.775 | 0.7 | 0.65 | 1.0 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.186 [+0.093, +0.279]
- rule - all-local: +0.186 [+0.093, +0.279]
- second-only - all-local: +0.193 [+0.100, +0.286]
- rule - all-cloud: +0.000 [+0.000, +0.000]
- second-only - all-cloud: +0.007 [+0.000, +0.021]
- second-only - rule: +0.007 [+0.000, +0.021]
