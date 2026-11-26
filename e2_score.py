"""E2 scoring: compare routing strategies offline from one local run and one cloud run of the same tasks.

  python e2_score.py out/e2_local_<...>.jsonl out/e2_cloud_<...>.jsonl --in 0.25 --out 2.00 [--router out/e2_router_<...>.jsonl]
  python e2_score.py out/e2_local_<a>.jsonl out/e2_local_<b>.jsonl --local-pair [--lenient] [--third out/e2_local_<c>.jsonl]

Prices are USD per million tokens for the cloud model (input, output); local tokens cost nothing here
(electricity is estimated separately in E1). Every strategy keeps tasks with personal data on the local model.
--lenient scores JSQuAD by containment instead of exact match (see e2_run.score). The task kind used by the rule
is the dataset's label: in an application it would come from which feature sent the request.

Strategies ("cloud" means the second file, "local" the first)
  all-local      every task answered locally
  all-cloud      every task answered by the cloud (personal-data tasks still local: they may not leave the machine)
  second-only    only with --local-pair: every task, personal data included, answered by the second model
  third-only     only with --third: every task answered by a third model (e.g. one bigger model instead of routing two)
  rule           personal data -> local; task kinds that are local-safe on the dev split -> local; the rest -> cloud
  classifier     only with --router: a JSONL of {id, difficulty in 0..1}; difficulty at or above a threshold -> cloud;
                 the threshold is chosen on the dev split only and reported on test (no router script yet: build it
                 only if the rule router leaves a gap worth closing)
Writes out/e2_scores_<first>_vs_<second>.json and .md (the second file may be another local model, priced at 0).
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def load(path, lenient=False):
    """Per-task results; `correct` is recomputed from the saved answer text with the current scorer.
    "A.jsonl+B.jsonl": B's answers replace A's for the tasks B has (e.g. a re-run of one task kind with another prompt)."""
    from e2_run import TASKS, score
    tasks = {t["id"]: t for t in (json.loads(l) for l in TASKS.read_text(encoding="utf-8").splitlines() if l.strip())}
    rows = {}
    for part in str(path).split("+"):
        rows.update({r["id"]: r for r in (json.loads(l) for l in Path(part).read_text(encoding="utf-8").splitlines() if l.strip())})
    for i, r in rows.items():
        if "text" in r and i in tasks:
            r["correct"] = score(tasks[i], r["text"], lenient=lenient)
    return rows


def cost_usd(r, price_in, price_out):
    return ((r.get("prompt_tokens") or 0) * price_in + (r.get("completion_tokens") or 0) * price_out) / 1e6


def pick(c, i, local, cloud, third=None):
    return cloud[i] if c == "cloud" else third[i] if c == "third" else local[i]


def evaluate(choice, local, cloud, ids, price_in, price_out, third=None):
    picked = [pick(choice(i), i, local, cloud, third) for i in ids]
    latencies = [r["total_s"] for r in picked if r.get("total_s") is not None]
    return {
        "accuracy": round(sum(r["correct"] for r in picked) / len(picked), 4) if picked else None,
        "cloud_share": round(sum(1 for i in ids if choice(i) == "cloud") / len(ids), 4) if ids else None,
        "cost_usd": round(sum(cost_usd(cloud[i], price_in, price_out) for i in ids if choice(i) == "cloud"), 6),
        "latency_p50_s": round(statistics.median(latencies), 3) if latencies else None,
        "latency_p95_s": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3) if latencies else None,
        "n": len(ids),
    }


def paired_ci(strategies, local, cloud, ids, n=2000, seed=0, third=None):
    """Accuracy difference of each strategy against each other one, resampling the same tasks for both (paired)."""
    import random
    hit = {s: [pick(f(i), i, local, cloud, third)["correct"] for i in ids] for s, f in strategies.items()}
    names = list(strategies)
    out = {}
    for a_i, a in enumerate(names):
        for b in names[a_i + 1:]:
            rng = random.Random(seed)  # same resamples for every pair, whatever the order of strategies
            d = [x - y for x, y in zip(hit[b], hit[a])]
            boots = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
            out[f"{b} - {a}"] = {"diff": round(sum(d) / len(d), 4), "lo": round(boots[int(0.025 * n)], 4), "hi": round(boots[int(0.975 * n) - 1], 4)}
    return out


def main(argv):
    lenient = "--lenient" in argv
    local, cloud = load(argv[0], lenient), load(argv[1], lenient)
    price_in = float(argv[argv.index("--in") + 1]) if "--in" in argv else 0.0
    price_out = float(argv[argv.index("--out") + 1]) if "--out" in argv else 0.0
    router = load(argv[argv.index("--router") + 1]) if "--router" in argv else None
    ids = [i for i in local if i in cloud]
    dev = [i for i in ids if local[i]["split"] == "dev"]
    test = [i for i in ids if local[i]["split"] == "test"]
    pii = lambda i: local[i]["has_pii"]

    # rule: a kind goes local when, on the dev split, the local model is at most 5 points below the cloud
    # (integer arithmetic: (cloud - local) / n <= 0.05, so that exactly 5 points is never lost to float rounding)
    kinds = sorted({local[i]["kind"] for i in ids})
    local_kinds = set()
    for k in kinds:
        kd = [i for i in dev if local[i]["kind"] == k]
        if kd and (sum(cloud[i]["correct"] for i in kd) - sum(local[i]["correct"] for i in kd)) * 20 <= len(kd):
            local_kinds.add(k)

    strategies = {
        "all-local": lambda i: "local",
        "all-cloud": lambda i: "local" if pii(i) else "cloud",
        "rule": lambda i: "local" if pii(i) or local[i]["kind"] in local_kinds else "cloud",
    }
    if "--local-pair" in argv:
        strategies["second-only"] = lambda i: "cloud"
    third = load(argv[argv.index("--third") + 1], lenient) if "--third" in argv else None
    if third:
        # a third model answering everything on its own, compared on the same tasks (e.g. routing two models vs one bigger)
        ids = [i for i in ids if i in third]
        dev = [i for i in dev if i in third]
        test = [i for i in test if i in third]
        strategies["third-only"] = lambda i: "third"
    threshold = None
    if router:
        # choose the threshold that maximises dev accuracy per dollar spent, never below all-local accuracy
        best = None
        for th in [x / 20 for x in range(0, 21)]:
            choose = lambda i, th=th: "local" if pii(i) or router.get(i, {}).get("difficulty", 1.0) < th else "cloud"
            r = evaluate(choose, local, cloud, dev, price_in, price_out)
            key = (r["accuracy"], -r["cost_usd"])
            if best is None or key > best[0]:
                best = (key, th)
        threshold = best[1]
        strategies["classifier"] = lambda i: "local" if pii(i) or router.get(i, {}).get("difficulty", 1.0) < threshold else "cloud"

    result = {"prices_usd_per_mtok": {"input": price_in, "output": price_out}, "rule_local_kinds": sorted(local_kinds), "classifier_threshold": threshold,
              "dev": {n: evaluate(f, local, cloud, dev, price_in, price_out, third) for n, f in strategies.items()},
              "test": {n: evaluate(f, local, cloud, test, price_in, price_out, third) for n, f in strategies.items()},
              "test_by_kind": {n: {k: evaluate(f, local, cloud, [i for i in test if local[i]["kind"] == k], price_in, price_out, third)["accuracy"] for k in kinds} for n, f in strategies.items()}}
    result["test_diff_ci95"] = paired_ci(strategies, local, cloud, test, third=third)
    OUT.mkdir(exist_ok=True)
    third_path = argv[argv.index("--third") + 1] if third else None
    label = lambda p: "+".join(Path(x).stem.removeprefix("e2_") for x in p.split("+"))
    name = ("e2_scores_" + "_vs_".join(label(p) for p in argv[:2])
            + (f"_and_{label(third_path)}" if third else "") + ("_lenient" if lenient else ""))
    if len(name) > 120:  # Windows path limits: keep it short and unique; the full inputs are listed in the JSON
        import hashlib
        name = f"{name[:80]}_{hashlib.sha1(name.encode()).hexdigest()[:8]}" + ("_lenient" if lenient else "")
    result["inputs"] = argv[:2] + ([third_path] if third else [])
    result["jsquad_scoring"] = "containment" if lenient else "exact"
    (OUT / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["| strategy (test split) | accuracy | cloud share | cloud cost USD | p50 s | p95 s |", "|---|---|---|---|---|---|"]
    for n, r in result["test"].items():
        lines.append(f"| {n} | {r['accuracy']} | {r['cloud_share']} | {r['cost_usd']} | {r['latency_p50_s']} | {r['latency_p95_s']} |")
    lines += ["", "| strategy | " + " | ".join(kinds) + " |", "|---|" + "---|" * len(kinds)]
    lines += [f"| {n} | " + " | ".join(str(v[k]) for k in kinds) + " |" for n, v in result["test_by_kind"].items()]
    lines += ["", "accuracy difference on test, paired bootstrap 95% interval (2000 resamples):"]
    lines += [f"- {pair}: {d['diff']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]" for pair, d in result["test_diff_ci95"].items()]
    (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(json.dumps({"rule_local_kinds": result["rule_local_kinds"], "classifier_threshold": threshold}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1:])
