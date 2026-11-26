"""E1: the 12 GB capacity table. Benchmarks each Foundry Local CUDA variant in its own process (bench_local.py).
With HYBRID_PARK_DIR set, each downloaded model is then moved out of fl-data to that folder so the next one fits on a
nearly full disk (the author's setup); without it nothing is moved. A model that would not fit on the disk is skipped
and recorded as such. A failed attempt's log is kept as capacity_<model>.failed-<n>.log before a rerun overwrites it.

  python run_capacity.py                # default list below
  python run_capacity.py qwen3-8b-cuda-gpu:2 ...
  python run_capacity.py --table        (rebuild capacity_table.md from capacity_table.json)
Writes out/capacity_table.json and out/capacity_table.md; per-model raw results stay in out/bench_*.json.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
MODELS = HERE / "fl-data" / "models"
# Optional: set HYBRID_PARK_DIR to move each model out of fl-data after use (and back when needed), for a nearly full
# disk. Unset (the default), models stay in fl-data and nothing is moved.
PARK = Path(os.environ["HYBRID_PARK_DIR"]) if os.environ.get("HYBRID_PARK_DIR") else None
PY = Path(sys.executable)  # the interpreter running this script, wherever its environment lives
# (variant id, catalog file size in MB) -- sizes from out/setup_eps_cuda_override.log
DEFAULT = [
    ("qwen2.5-1.5b-instruct-cuda-gpu:4", 1280),
    ("qwen3-4b-cuda-gpu:2", 2692),
    ("Phi-4-mini-instruct-cuda-gpu:5", 3686),
    ("qwen2.5-7b-instruct-cuda-gpu:4", 4843),
    ("qwen3-8b-cuda-gpu:2", 5674),
    ("Phi-4-cuda-gpu:2", 8570),
    ("qwen3-14b-cuda-gpu:2", 9302),
]
SIZES = dict(DEFAULT)


def free_mb(path: Path) -> int:
    return shutil.disk_usage(path).free // (1024 * 1024)


def model_dirs() -> set:
    return {p for p in MODELS.rglob("*") if p.is_dir() and any(f.suffix == ".onnx" for f in p.iterdir() if f.is_file())}


def unpark(vid: str) -> None:
    """Bring back a model parked by an earlier run instead of downloading it again."""
    if PARK is None:
        return
    for p in PARK.glob(f"*/{vid.replace(':', '-')}/*"):
        dest = MODELS / p.relative_to(PARK)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))


def park(dirs) -> list:
    out = []
    if PARK is None:
        return out
    for d in dirs:
        target = PARK / d.relative_to(MODELS)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(target))
        out.append(str(target))
    return out


def main(variants):
    OUT.mkdir(exist_ok=True)
    table = OUT / "capacity_table.json"
    # a rerun of some variants replaces their rows and keeps the others
    by_variant = {r["variant"]: r for r in json.loads(table.read_text(encoding="utf-8"))} if table.exists() else {}
    order = [v for v, _ in DEFAULT]
    for vid in variants:
        size = SIZES.get(vid, 0)
        room = free_mb(HERE)
        row = {"variant": vid, "catalog_mb": size, "f_free_mb_before": room}
        if size and room < size + 1500:
            row["status"] = f"skipped: needs about {size + 1500} MB free on the drive of {HERE}, has {room} MB"
            by_variant[vid] = row
            print(row["status"], flush=True)
            continue
        before = model_dirs()
        unpark(vid)
        t = time.time()
        log = OUT / f"capacity_{vid.replace(':', '_')}.log"
        if log.exists() and by_variant.get(vid, {}).get("status", "").startswith("failed"):
            n = len(list(OUT.glob(f"{log.stem}.failed-*.log"))) + 1
            log.rename(log.with_name(f"{log.stem}.failed-{n}.log"))
        with log.open("w", encoding="utf-8") as fh:
            rc = subprocess.run([str(PY), str(HERE / "bench_local.py"), "foundry", vid], cwd=HERE, stdout=fh, stderr=subprocess.STDOUT).returncode
        row["wall_s"] = round(time.time() - t)
        row["exit_code"] = rc
        result = OUT / f"bench_foundry-local-cuda_{vid.replace(':', '_')}.json"
        if rc == 0 and result.exists():
            r = json.loads(result.read_text(encoding="utf-8"))
            row.update({k: r.get(k) for k in ("load_s", "vram_idle_mb", "vram_after_load_mb", "vram_peak_mb", "model_vram_mb", "model_file_size_mb")})
            row["short"] = r["summary_median"].get("short")
            row["long"] = r["summary_median"].get("long")
            row["status"] = "ok"
        else:
            row["status"] = f"failed (exit {rc}); see {log.name}"
        # Park the downloaded model outside the workspace so the next one fits.
        row["parked"] = park(model_dirs() - before)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        by_variant[vid] = row
        table.write_text(json.dumps(list(by_variant.values()), ensure_ascii=False, indent=2), encoding="utf-8")

    rows = sorted(by_variant.values(), key=lambda r: order.index(r["variant"]) if r["variant"] in order else len(order))
    table.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_table(rows)


def long_prompt_tokens(vid: str):
    """The same long text is a different number of tokens for each tokenizer (Phi-4: 2080, Qwen: about 1400)."""
    f = OUT / f"bench_foundry-local-cuda_{vid.replace(':', '_')}.json"
    if not f.exists():
        return ""
    runs = json.loads(f.read_text(encoding="utf-8")).get("runs_raw", {}).get("long") or [{}]
    return runs[0].get("prompt_tokens") or ""


def write_table(rows) -> None:
    # The short prompt's generation speed is left out: 7-11 generated tokens are too few for a rate.
    lines = ["| model | file MB | load s | VRAM idle MB | VRAM peak MB | VRAM rise MB | long prompt tokens | TTFT long s | gen tok/s long | status |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        l = r.get("long") or {}
        lines.append(f"| {r['variant']} | {r.get('model_file_size_mb') or r['catalog_mb']} | {r.get('load_s', '')} | {r.get('vram_idle_mb', '')} | "
                     f"{r.get('vram_peak_mb', '')} | {r.get('model_vram_mb', '')} | {long_prompt_tokens(r['variant'])} | {l.get('ttft_s', '')} | "
                     f"{l.get('gen_tokens_per_s', '')} | {r['status']} |")
    (OUT / "capacity_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1:] == ["--table"]:  # rebuild capacity_table.md from capacity_table.json without running anything
        write_table(json.loads((OUT / "capacity_table.json").read_text(encoding="utf-8")))
    else:
        main(sys.argv[1:] or [v for v, _ in DEFAULT])
