"""List what Foundry Local offers on this machine: execution providers and catalog variants. Downloads nothing."""
import json
import sys

from fl_common import manager

sys.stdout.reconfigure(encoding="utf-8")

with manager() as m:
    print("== execution providers")
    for ep in m.discover_eps():
        print("  ", {k: getattr(ep, k) for k in dir(ep) if not k.startswith("_") and not callable(getattr(ep, k))})

    print("== catalog (chat models with a GPU variant)")
    rows = []
    for model in m.get_catalog().list_models():
        for v in model.variants:
            info = v.info
            d = {k: getattr(info, k) for k in dir(info) if not k.startswith("_") and not callable(getattr(info, k))}
            rows.append({"alias": model.alias, "id": v.id, **d})
    if rows:
        print("  fields:", sorted(rows[0].keys()))
    wanted = sys.argv[1:] or ["phi-4-mini", "qwen3-4b", "qwen3-8b", "phi-4", "qwen3-14b", "gpt-oss-20b", "qwen2.5-7b"]
    for r in rows:
        if r["alias"] in wanted:
            keep = {k: r[k] for k in r if k in ("alias", "id", "file_size_mb", "runtime", "task", "context_length", "supports_tool_calling", "cached")}
            rest = {k: v for k, v in r.items() if k not in keep and isinstance(v, (str, int, float, bool)) and len(str(v)) < 60}
            print("  ", json.dumps({**keep, **rest}, ensure_ascii=False, default=str))
    print("total variants:", len(rows), "| aliases:", len({r['alias'] for r in rows}))
