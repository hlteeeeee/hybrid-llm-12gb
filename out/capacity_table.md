| model | file MB | load s | VRAM idle MB | VRAM peak MB | VRAM rise MB | long prompt tokens | TTFT long s | gen tok/s long | status |
|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-1.5b-instruct-cuda-gpu:4 | 1280 | 1.4 | 2512 | 5547 | 3035 | 1399 | 0.0938 | 270.5 | ok |
| qwen3-4b-cuda-gpu:2 | 2692 | 1.8 | 864 | 6140 | 5276 | 1378 | 0.2563 | 135.3 | ok |
| Phi-4-mini-instruct-cuda-gpu:5 | 3686 | 2.4 | 2512 | 9323 | 6811 | 1494 | 0.2687 | 120.4 | ok |
| qwen2.5-7b-instruct-cuda-gpu:4 | 4843 | 1.7 | 2512 | 9707 | 7195 | 1399 | 0.3903 | 100.4 | ok |
| qwen3-8b-cuda-gpu:2 | 5674 | 1.9 | 2512 | 10855 | 8343 | 1378 | 0.4479 | 89.5 | ok |
| Phi-4-cuda-gpu:2 | 8570 | 1.6 | 2512 | 11713 | 9201 | 2080 | 1.196 | 61.3 | ok |
| qwen3-14b-cuda-gpu:2 | 9302 | 2.3 | 865 | 11734 | 10869 | 1378 | 0.7718 | 54.3 | ok |
| gpt-oss-20b-cuda-gpu:1 | 0 |  |  |  |  |  |  |  | failed (exit 1); see capacity_gpt-oss-20b-cuda-gpu_1.log |
