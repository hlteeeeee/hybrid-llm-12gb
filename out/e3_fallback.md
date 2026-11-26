connect 1.0s, silence 3.0s, first token 10.0s, total 60.0s; breaker opens after 2 consecutive failures for 5.0s; one request every 0.5s; phases [('up', 10), ('hang', 20), ('up', 15), ('down', 15), ('up', 15)], switched at [0.0, 10.25, 30.25, 45.25, 60.25]

- breaker, phase 1 (cloud healthy): 0 false alarms
- breaker, outage 2 (hang, 20.0 s): 9 requests sent, 3 waited for the cloud (total 9.0 s, each [3.011, 3.024, 3.01]); first request served locally without waiting sent at +10.75 s
- breaker, phase 3 (cloud healthy): 0 false alarms
- breaker, cloud back at 30.25 s: first cloud answer sent at +2.75 s, finished at +2.92 s (relative to the cloud coming back)
- breaker, outage 4 (down, 15.0 s): 9 requests sent, 3 waited for the cloud (total 3.0 s, each [1.014, 1.009, 1.012]); first request served locally without waiting sent at +4.27 s
- breaker, phase 5 (cloud healthy): 0 false alarms
- breaker, cloud back at 60.25 s: first cloud answer sent at +0.27 s, finished at +0.41 s (relative to the cloud coming back)
- no-breaker, phase 1 (cloud healthy): 0 false alarms
- no-breaker, outage 2 (hang, 20.0 s): 5 requests sent, 5 waited for the cloud (total 12.8 s, each [3.004, 3.008, 3.017, 3.008, 0.758]); first request served locally without waiting sent at never
- no-breaker, phase 3 (cloud healthy): 0 false alarms
- no-breaker, cloud back at 30.25 s: first cloud answer sent at +0.25 s, finished at +0.53 s (relative to the cloud coming back)
- no-breaker, outage 4 (down, 15.0 s): 6 requests sent, 6 waited for the cloud (total 6.0 s, each [1.001, 1.007, 1.013, 1.004, 1.002, 1.001]); first request served locally without waiting sent at never
- no-breaker, phase 5 (cloud healthy): 0 false alarms
- no-breaker, cloud back at 60.25 s: first cloud answer sent at +3.75 s, finished at +3.92 s (relative to the cloud coming back)
- breaker-nonstream-3s, phase 1 (cloud healthy): 1 false alarms ([('mgsm', 'APITimeoutError', 333)])
- breaker-nonstream-3s, outage 2 (hang, 20.0 s): 10 requests sent, 3 waited for the cloud (total 6.8 s, each [3.009, 3.005, 0.769]); first request served locally without waiting sent at +5.75 s
- breaker-nonstream-3s, phase 3 (cloud healthy): 1 false alarms ([('mgsm', 'APITimeoutError', 512)])
- breaker-nonstream-3s, cloud back at 30.25 s: first cloud answer sent at +5.25 s, finished at +5.42 s (relative to the cloud coming back)
- breaker-nonstream-3s, outage 4 (down, 15.0 s): 6 requests sent, 2 waited for the cloud (total 4.1 s, each [2.043, 2.074]); first request served locally without waiting sent at +6.75 s
- breaker-nonstream-3s, phase 5 (cloud healthy): 0 false alarms
- breaker-nonstream-3s, cloud back at 60.25 s: first cloud answer sent at +4.25 s, finished at +5.66 s (relative to the cloud coming back)

| config | phase | requests | waited for cloud | total wait s | max wait s | where |
|---|---|---|---|---|---|---|
| breaker | 1:up | 7 | 0 | 0 |  | {"cloud": 7} |
| breaker | 2:hang | 9 | 3 | 9.04 | 3.024 | {"local:fallback": 3, "local:breaker-open": 6} |
| breaker | 3:up | 14 | 0 | 0 |  | {"local:breaker-open": 2, "cloud": 12} |
| breaker | 4:down | 9 | 3 | 3.04 | 1.014 | {"local:fallback": 3, "local:breaker-open": 6} |
| breaker | 5:up | 12 | 0 | 0 |  | {"cloud": 12} |
| no-breaker | 1:up | 8 | 0 | 0 |  | {"cloud": 8} |
| no-breaker | 2:hang | 5 | 5 | 12.79 | 3.017 | {"local:fallback": 5} |
| no-breaker | 3:up | 11 | 0 | 0 |  | {"cloud": 11} |
| no-breaker | 4:down | 6 | 6 | 6.03 | 1.013 | {"local:fallback": 6} |
| no-breaker | 5:up | 9 | 0 | 0 |  | {"cloud": 9} |
| breaker-nonstream-3s | 1:up | 6 | 1 | 3.01 | 3.008 | {"cloud": 5, "local:fallback": 1} |
| breaker-nonstream-3s | 2:hang | 10 | 3 | 6.78 | 3.009 | {"local:fallback": 3, "local:breaker-open": 7} |
| breaker-nonstream-3s | 3:up | 11 | 1 | 3.0 | 3.004 | {"local:breaker-open": 5, "cloud": 5, "local:fallback": 1} |
| breaker-nonstream-3s | 4:down | 6 | 2 | 4.12 | 2.074 | {"local:fallback": 2, "local:breaker-open": 4} |
| breaker-nonstream-3s | 5:up | 12 | 0 | 0 |  | {"local:breaker-open": 2, "cloud": 10} |
