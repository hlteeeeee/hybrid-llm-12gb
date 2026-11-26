| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.7929 | 0.0 | 0 | 0.238 | 5.497 |
| all-cloud | 0.9071 | 0.8571 | 0.0 | 0.331 | 4.096 |
| rule | 0.7929 | 0.0 | 0 | 0.238 | 5.497 |
| second-only | 0.9 | 1.0 | 0.0 | 0.356 | 4.096 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.775 | 0.85 | 0.65 | 1.0 |
| all-cloud | 0.9 | 0.975 | 0.8 | 1.0 |
| rule | 0.775 | 0.85 | 0.65 | 1.0 |
| second-only | 0.9 | 0.975 | 0.8 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.114 [+0.064, +0.179]
- rule - all-local: +0.000 [+0.000, +0.000]
- second-only - all-local: +0.107 [+0.050, +0.171]
- rule - all-cloud: -0.114 [-0.179, -0.064]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- second-only - rule: +0.107 [+0.050, +0.171]
