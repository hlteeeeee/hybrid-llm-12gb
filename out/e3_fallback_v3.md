connect 1.0s, silence 3.0s, breaker opens after 2 consecutive failures for 5.0s, one request every 0.5s, phases [('up', 10), ('hang', 20), ('up', 15), ('down', 15), ('up', 15)]

- breaker, phase 1 (cloud healthy): 0 false alarms
- breaker, outage 2 (hang, 20 s): 9 requests sent, 3 waited for the cloud (total 9.0 s, each [3.001, 3.008, 3.003]); first request served without waiting at +7.0 s
- breaker, phase 3 (cloud healthy): 0 false alarms
- breaker, cloud back at 30 s: first request answered by the cloud was sent at +0.0 s
- breaker, outage 4 (down, 15 s): 9 requests sent, 3 waited for the cloud (total 3.0 s, each [1.013, 1.002, 1.01]); first request served without waiting at +3.5 s
- breaker, phase 5 (cloud healthy): 0 false alarms
- breaker, cloud back at 60 s: first request answered by the cloud was sent at +1.5 s
- no-breaker, phase 1 (cloud healthy): 0 false alarms
- no-breaker, outage 2 (hang, 20 s): 5 requests sent, 5 waited for the cloud (total 13.1 s, each [3.023, 3.011, 3.002, 3.027, 1.012]); first request served without waiting at never
- no-breaker, phase 3 (cloud healthy): 0 false alarms
- no-breaker, cloud back at 30 s: first request answered by the cloud was sent at +0.5 s
- no-breaker, outage 4 (down, 15 s): 6 requests sent, 6 waited for the cloud (total 6.0 s, each [1.004, 1.005, 1.002, 1.013, 1.007, 1.008]); first request served without waiting at never
- no-breaker, phase 5 (cloud healthy): 0 false alarms
- no-breaker, cloud back at 60 s: first request answered by the cloud was sent at +3.02 s
- breaker-total-3s, phase 1 (cloud healthy): 1 false alarms ([('mgsm', 'APITimeoutError', 333)])
- breaker-total-3s, outage 2 (hang, 20 s): 9 requests sent, 2 waited for the cloud (total 6.0 s, each [3.009, 3.012]); first request served without waiting at +6.0 s
- breaker-total-3s, phase 3 (cloud healthy): 1 false alarms ([('mgsm', 'APITimeoutError', 512)])
- breaker-total-3s, cloud back at 30 s: first request answered by the cloud was sent at +1.0 s
- breaker-total-3s, outage 4 (down, 15 s): 6 requests sent, 2 waited for the cloud (total 6.6 s, each [2.052, 4.562]); first request served without waiting at +8.5 s
- breaker-total-3s, phase 5 (cloud healthy): 0 false alarms
- breaker-total-3s, cloud back at 60 s: first request answered by the cloud was sent at +10.0 s

| config | phase | requests | waited for cloud | total wait s | max wait s | where |
|---|---|---|---|---|---|---|
| breaker | 1:up | 6 | 0 | 0 |  | {"cloud": 6} |
| breaker | 2:hang | 9 | 3 | 9.01 | 3.008 | {"local:fallback": 3, "local:breaker-open": 6} |
| breaker | 3:up | 12 | 0 | 0 |  | {"cloud": 12} |
| breaker | 4:down | 9 | 3 | 3.02 | 1.013 | {"local:fallback": 3, "local:breaker-open": 5, "cloud": 1} |
| breaker | 5:up | 12 | 0 | 0 |  | {"cloud": 12} |
| no-breaker | 1:up | 8 | 0 | 0 |  | {"cloud": 8} |
| no-breaker | 2:hang | 5 | 5 | 13.07 | 3.027 | {"local:fallback": 5} |
| no-breaker | 3:up | 11 | 0 | 0 |  | {"cloud": 11} |
| no-breaker | 4:down | 6 | 6 | 6.04 | 1.013 | {"local:fallback": 6} |
| no-breaker | 5:up | 9 | 0 | 0 |  | {"cloud": 9} |
| breaker-total-3s | 1:up | 6 | 1 | 3.01 | 3.014 | {"cloud": 5, "local:fallback": 1} |
| breaker-total-3s | 2:hang | 9 | 2 | 6.02 | 3.012 | {"local:fallback": 2, "local:breaker-open": 7} |
| breaker-total-3s | 3:up | 12 | 1 | 3.02 | 3.022 | {"cloud": 11, "local:fallback": 1} |
| breaker-total-3s | 4:down | 6 | 2 | 6.61 | 4.562 | {"local:fallback": 2, "local:breaker-open": 4} |
| breaker-total-3s | 5:up | 6 | 0 | 0 |  | {"cloud": 6} |
