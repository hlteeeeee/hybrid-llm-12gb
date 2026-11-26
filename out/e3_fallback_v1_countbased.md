timeout 3.0s, breaker opens after 2 consecutive failures for 10.0s

| config | phase | n | answered | correct | p50 s | p95 s | max s | waited for cloud | where |
|---|---|---|---|---|---|---|---|---|---|
| breaker | 1:up | 10 | 10 | 7 | 0.255 | 1.083 | 1.083 | 0 | {"cloud": 10} |
| breaker | 2:hang | 20 | 20 | 16 | 0.202 | 3.223 | 3.237 | 2 | {"local:fallback": 2, "local:breaker-open": 18} |
| breaker | 3:down | 10 | 10 | 6 | 0.198 | 0.473 | 0.473 | 0 | {"local:breaker-open": 10} |
| breaker | 4:up | 15 | 15 | 11 | 0.15 | 0.153 | 0.153 | 0 | {"local:breaker-open": 15} |
| no-breaker | 1:up | 10 | 10 | 7 | 0.247 | 0.539 | 0.539 | 0 | {"cloud": 10} |
| no-breaker | 2:hang | 20 | 20 | 16 | 3.222 | 3.271 | 3.315 | 20 | {"local:fallback": 20} |
| no-breaker | 3:down | 10 | 10 | 6 | 2.25 | 2.513 | 2.513 | 10 | {"local:fallback": 10} |
| no-breaker | 4:up | 15 | 15 | 11 | 0.184 | 0.19 | 0.193 | 0 | {"cloud": 15} |
