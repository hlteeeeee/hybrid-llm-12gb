timeout 3.0s, breaker opens after 2 consecutive failures for 5.0s, one request every 0.5s, phases [('up', 10), ('hang', 20), ('down', 10), ('up', 20)]

- breaker, outage 2 (hang): 3 of 22 requests waited for the cloud; first one served without waiting at +7.0 s
- breaker, outage 3 (down): 2 of 12 requests waited for the cloud; first one served without waiting at +2.5 s
- breaker, cloud back (phase 4): first cloud answer at +5.0 s
- no-breaker, outage 2 (hang): 6 of 6 requests waited for the cloud; first one served without waiting at +never s
- no-breaker, outage 3 (down): 4 of 4 requests waited for the cloud; first one served without waiting at +never s
- no-breaker, cloud back (phase 4): first cloud answer at +1.0 s

| config | phase | n | answered | correct | p50 s | p95 s | max s | waited for cloud | where |
|---|---|---|---|---|---|---|---|---|---|
| breaker | 1:up | 18 | 18 | 13 | 0.243 | 0.357 | 1.113 | 0 | {"cloud": 18} |
| breaker | 2:hang | 22 | 22 | 16 | 0.199 | 3.218 | 3.265 | 3 | {"local:fallback": 3, "local:breaker-open": 19} |
| breaker | 3:down | 12 | 12 | 11 | 0.154 | 2.194 | 2.202 | 2 | {"local:fallback": 2, "local:breaker-open": 10} |
| breaker | 4:up | 39 | 39 | 27 | 0.182 | 0.279 | 0.55 | 0 | {"local:breaker-open": 10, "cloud": 29} |
| no-breaker | 1:up | 19 | 19 | 13 | 0.238 | 0.365 | 0.527 | 0 | {"cloud": 19} |
| no-breaker | 2:hang | 6 | 6 | 5 | 3.22 | 3.291 | 3.291 | 6 | {"local:fallback": 6} |
| no-breaker | 3:down | 4 | 4 | 4 | 2.239 | 2.279 | 2.279 | 4 | {"local:fallback": 4} |
| no-breaker | 4:up | 38 | 38 | 27 | 0.182 | 0.245 | 0.484 | 0 | {"cloud": 38} |
