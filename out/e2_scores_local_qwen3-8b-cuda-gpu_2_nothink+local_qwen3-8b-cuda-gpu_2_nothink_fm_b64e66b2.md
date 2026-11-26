| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.7929 | 0.0 | 0 | 0.23 | 3.975 |
| all-cloud | 0.8214 | 0.8571 | 0.0 | 0.387 | 7.155 |
| rule | 0.8714 | 0.5714 | 0.0 | 0.264 | 7.155 |
| second-only | 0.8143 | 1.0 | 0.0 | 0.422 | 7.155 |
| third-only | 0.8429 | 0.0 | 0 | 0.363 | 4.096 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.775 | 0.85 | 0.65 | 1.0 |
| all-cloud | 0.925 | 0.675 | 0.775 | 1.0 |
| rule | 0.925 | 0.85 | 0.775 | 1.0 |
| second-only | 0.925 | 0.675 | 0.775 | 0.95 |
| third-only | 0.9 | 0.775 | 0.8 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.029 [-0.043, +0.107]
- rule - all-local: +0.079 [+0.021, +0.136]
- second-only - all-local: +0.021 [-0.050, +0.100]
- third-only - all-local: +0.050 [-0.014, +0.114]
- rule - all-cloud: +0.050 [+0.007, +0.093]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- third-only - all-cloud: +0.021 [-0.050, +0.086]
- second-only - rule: -0.057 [-0.100, -0.014]
- third-only - rule: -0.029 [-0.093, +0.029]
- third-only - second-only: +0.029 [-0.043, +0.093]
