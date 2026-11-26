"""Measure local LLM speed through an OpenAI-compatible endpoint (the same client code the cloud side uses).

  python bench_local.py foundry qwen2.5-0.5b-instruct-cuda-gpu:4      # Foundry Local + CUDA EP (downloads if needed)
  python bench_local.py openai http://127.0.0.1:8080/v1 qwen2.5-0.5b   # any OpenAI-compatible server, e.g. llama-server

Per request: TTFT, prompt tokens / TTFT (includes HTTP + scheduling overhead, so a lower bound on prefill speed),
generation tokens/s after the first token. VRAM = nvidia-smi memory.used, whole GPU (WDDM gives no per-process
numbers), so "model_vram_mb" is the rise over the idle baseline and includes anything else that moved.
Writes out/bench_<runtime>_<model>.json.
"""
import json
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

from openai import OpenAI

OUT = Path(__file__).resolve().parent / "out"
PARAGRAPH = ("ハイブリッドLLMでは、機密データや軽いタスクはローカルGPUで処理し、難しい推論だけをクラウドに送る。"
             "これによりAPI費用と遅延を抑えつつ、品質が必要な場面ではクラウドの大型モデルを使える。")
PROMPTS = {"short": "日本の首都はどこですか？一文で答えてください。",
           "long": PARAGRAPH * 20 + "\n\n上の文章を三行で要約してください。"}
MAX_TOKENS, RUNS = 256, 3


def vram_used_mb() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, check=True).stdout
    return int(out.split()[0])


class PeakVram(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.peak, self.stop = 0, threading.Event()

    def run(self):
        while not self.stop.is_set():
            self.peak = max(self.peak, vram_used_mb())
            time.sleep(0.2)


def one_request(client: OpenAI, model: str, prompt: str) -> dict:
    t0 = time.perf_counter()
    first, chunks, usage, text, reasoning_chunks = None, 0, None, [], 0
    stream = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                            max_tokens=MAX_TOKENS, temperature=0, stream=True,
                                            stream_options={"include_usage": True})
    for ch in stream:
        if ch.usage:
            usage = ch.usage
        if not ch.choices:
            continue
        delta = ch.choices[0].delta
        # Reasoning models (qwen3, phi-4-mini-reasoning) stream their thinking in a separate field first;
        # it is generated tokens all the same, so it counts for time-to-first-token and speed.
        thought = getattr(delta, "reasoning_content", None) or (delta.model_extra or {}).get("reasoning_content") or (delta.model_extra or {}).get("reasoning")
        if delta.content or thought:
            first = first or time.perf_counter()
            chunks += 1
            if delta.content:
                text.append(delta.content)
            else:
                reasoning_chunks += 1
    t_end = time.perf_counter()
    if first is None:
        return {"ttft_s": None, "total_s": round(t_end - t0, 3), "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else 0, "token_count_source": "usage" if usage else "none",
                "prompt_tokens_per_s_from_ttft": None, "gen_tokens_per_s": None, "reasoning_chunks": 0, "text_head": "",
                "note": "no streamed tokens were observed"}
    gen = usage.completion_tokens if usage else chunks
    ttft = first - t0
    return {"ttft_s": round(ttft, 4), "total_s": round(t_end - t0, 3),
            "prompt_tokens": usage.prompt_tokens if usage else None, "completion_tokens": gen,
            "token_count_source": "usage" if usage else "stream_chunks",
            "prompt_tokens_per_s_from_ttft": round(usage.prompt_tokens / ttft, 1) if usage else None,
            "gen_tokens_per_s": round((gen - 1) / (t_end - first), 1) if gen > 1 else None,
            "reasoning_chunks": reasoning_chunks,
            "text_head": "".join(text)[:120]}


def bench(base_url: str, model: str, runtime: str, extra: dict) -> dict:
    client = OpenAI(base_url=base_url, api_key="not-needed-locally")
    peak = PeakVram()
    peak.start()
    one_request(client, model, PROMPTS["short"])  # warm-up
    results = {name: [one_request(client, model, p) for _ in range(RUNS)] for name, p in PROMPTS.items()}
    peak.stop.set()
    peak.join()
    summary = {name: {k: statistics.median(r[k] for r in rs) for k in ("ttft_s", "prompt_tokens_per_s_from_ttft", "gen_tokens_per_s")
                      if all(r[k] is not None for r in rs)} for name, rs in results.items()}
    report = {"runtime": runtime, "model": model, "base_url": base_url, "max_tokens": MAX_TOKENS, "runs": RUNS,
              **extra, "vram_peak_mb": peak.peak, "summary_median": summary, "runs_raw": results}
    if "vram_idle_mb" in report:
        report["model_vram_mb"] = peak.peak - report["vram_idle_mb"]
    OUT.mkdir(exist_ok=True)
    path = OUT / f"bench_{runtime}_{model.replace(':', '_').replace('/', '_')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "runs_raw"}, ensure_ascii=False, indent=2))
    print("wrote", path)
    return report


def run_foundry(variant_id: str) -> None:
    from fl_common import manager
    idle = vram_used_mb()
    with manager() as m:
        res = m.download_and_register_eps(["CUDAExecutionProvider"], None)
        print("EP registration:", res.status, res.registered_eps, res.failed_eps)
        model = m.get_catalog().get_model_variant(variant_id)
        if model is None:
            sys.exit(f"variant {variant_id} not in catalog (is the CUDA EP registered?)")
        if not model.is_cached:
            t = time.time()
            model.download(lambda p: print(f"\r  download {p:5.1f}%", end="", flush=True))
            print(f"\n  downloaded in {time.time() - t:.0f}s")
        t = time.time()
        model.load()
        load_s = round(time.time() - t, 1)
        m.start_web_service()
        base = m.urls[0].rstrip("/") + "/v1"
        bench(base, variant_id, "foundry-local-cuda",
              {"vram_idle_mb": idle, "vram_after_load_mb": vram_used_mb(), "load_s": load_s,
               "ep_registration": res.status, "model_file_size_mb": model.info.file_size_mb})
        model.unload()


if __name__ == "__main__":
    if sys.argv[1:2] == ["foundry"]:
        run_foundry(sys.argv[2])
    elif sys.argv[1:2] == ["openai"]:
        bench(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "openai-compatible",
              {"vram_idle_mb": int(sys.argv[5])} if len(sys.argv) > 5 else {})
    else:
        sys.exit(__doc__)
