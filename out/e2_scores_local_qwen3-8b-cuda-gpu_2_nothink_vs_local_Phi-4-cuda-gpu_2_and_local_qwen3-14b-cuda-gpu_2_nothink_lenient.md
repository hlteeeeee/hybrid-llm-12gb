| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.7929 | 0.0 | 0 | 0.238 | 5.497 |
| all-cloud | 0.8786 | 0.8571 | 0.0 | 0.487 | 7.919 |
| rule | 0.8714 | 0.5714 | 0.0 | 0.272 | 7.155 |
| second-only | 0.8714 | 1.0 | 0.0 | 0.532 | 7.919 |
| third-only | 0.9 | 0.0 | 0 | 0.356 | 4.096 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.775 | 0.85 | 0.65 | 1.0 |
| all-cloud | 0.925 | 0.875 | 0.775 | 1.0 |
| rule | 0.925 | 0.85 | 0.775 | 1.0 |
| second-only | 0.925 | 0.875 | 0.775 | 0.95 |
| third-only | 0.9 | 0.975 | 0.8 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.086 [+0.021, +0.157]
- rule - all-local: +0.079 [+0.021, +0.136]
- second-only - all-local: +0.079 [+0.014, +0.157]
- third-only - all-local: +0.107 [+0.050, +0.171]
- rule - all-cloud: -0.007 [-0.050, +0.036]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- third-only - all-cloud: +0.021 [-0.036, +0.079]
- second-only - rule: +0.000 [-0.043, +0.043]
- third-only - rule: +0.029 [-0.029, +0.086]
- third-only - second-only: +0.029 [-0.029, +0.086]
