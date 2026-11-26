| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.8071 | 0.0 | 0 | 0.23 | 3.975 |
| all-cloud | 0.9 | 0.8571 | 0.0 | 0.387 | 7.155 |
| rule | 0.8857 | 0.5714 | 0.0 | 0.264 | 7.155 |
| second-only | 0.8929 | 1.0 | 0.0 | 0.422 | 7.155 |
| third-only | 0.9 | 0.0 | 0 | 0.363 | 4.096 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.775 | 0.9 | 0.65 | 1.0 |
| all-cloud | 0.925 | 0.95 | 0.775 | 1.0 |
| rule | 0.925 | 0.9 | 0.775 | 1.0 |
| second-only | 0.925 | 0.95 | 0.775 | 0.95 |
| third-only | 0.9 | 0.975 | 0.8 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.093 [+0.036, +0.157]
- rule - all-local: +0.079 [+0.021, +0.136]
- second-only - all-local: +0.086 [+0.021, +0.150]
- third-only - all-local: +0.093 [+0.036, +0.150]
- rule - all-cloud: -0.014 [-0.043, +0.007]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- third-only - all-cloud: +0.000 [-0.050, +0.050]
- second-only - rule: +0.007 [-0.021, +0.043]
- third-only - rule: +0.014 [-0.036, +0.064]
- third-only - second-only: +0.007 [-0.043, +0.064]
