| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |
|---|---|---|---|---|---|
| all-local | 0.8143 | 0.0 | 0 | 0.236 | 3.866 |
| all-cloud | 0.8786 | 0.8571 | 0.0 | 0.487 | 7.919 |
| rule | 0.8786 | 0.5714 | 0.0 | 0.265 | 7.155 |
| second-only | 0.8714 | 1.0 | 0.0 | 0.532 | 7.919 |

| strategy | jcqa | jsquad | mgsm | pii |
|---|---|---|---|---|
| all-local | 0.75 | 0.875 | 0.725 | 1.0 |
| all-cloud | 0.925 | 0.875 | 0.775 | 1.0 |
| rule | 0.925 | 0.875 | 0.775 | 1.0 |
| second-only | 0.925 | 0.875 | 0.775 | 0.95 |

accuracy difference on test, paired bootstrap 95% interval (2000 resamples):
- all-cloud - all-local: +0.064 [+0.000, +0.136]
- rule - all-local: +0.064 [+0.007, +0.121]
- second-only - all-local: +0.057 [-0.007, +0.129]
- rule - all-cloud: +0.000 [-0.036, +0.036]
- second-only - all-cloud: -0.007 [-0.021, +0.000]
- second-only - rule: -0.007 [-0.050, +0.036]
