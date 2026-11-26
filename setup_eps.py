"""Download and register the GPU execution providers, then list the GPU variants of the catalog.

Usage: python setup_eps.py [EpName ...]      (no names = all discoverable EPs)
"""
import sys
import time

from fl_common import DATA, manager

sys.stdout.reconfigure(encoding="utf-8")


def folder_mb(path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) // (1024 * 1024)


with manager() as m:
    last = {}

    def progress(name: str, pct: float) -> None:
        if int(pct) // 10 != last.get(name, -1):
            last[name] = int(pct) // 10
            print(f"  {name}: {pct:.0f}%", flush=True)

    t0 = time.time()
    res = m.download_and_register_eps(sys.argv[1:] or None, progress)
    print(f"download_and_register_eps: success={res.success} status={res.status!r} registered={res.registered_eps} failed={res.failed_eps} ({time.time() - t0:.0f}s)")
    print("eps now:", [(e.name, e.is_registered) for e in m.discover_eps()])
    print("fl-data size MB:", folder_mb(DATA))

    print("== GPU variants")
    for model in m.get_catalog().list_models():
        for v in model.variants:
            rt = v.info.runtime
            if "CPU" in str(getattr(rt, "device_type", "")):
                continue
            print(f"  {model.alias:28s} {v.id:55s} {getattr(rt, 'execution_provider', '?'):28s} {v.info.file_size_mb:>6} MB  ctx={v.info.context_length} tools={v.info.supports_tool_calling}")
