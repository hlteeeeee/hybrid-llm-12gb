"""Are the local answers repeatable at temperature 0, and can one request's content leak into the next?

  python e2_repeat.py Phi-4-cuda-gpu:2 --pairs pii-9:pii-10 --ids jsquad-a4596p36q2 jsquad-a2164640p16q3
  python e2_repeat.py qwen3-8b-cuda-gpu:2 --no-think --ids jsquad-a29627p18q1 mgsm-54

For every --ids task: answered REPEAT times right after itself ("same prompt again") and REPEAT times right after an
unrelated filler prompt ("after another prompt"), with the same streaming call as E2. For every --pairs a:b: a then b,
REPEAT times; b's answer is checked for text that appears in a's prompt but not in b's (a leak from the previous request).
Writes out/diag/repeat_<model>.json.
"""
import json
import re
import sys
from pathlib import Path

from openai import OpenAI

from e2_run import TASKS, answer, score

HERE = Path(__file__).resolve().parent
REPEAT = 5
FILLER = "日本で一番高い山の名前を、名前だけ答えてください。"


def main(argv):
    variant = argv[0]
    suffix = " /no_think" if "--no-think" in argv else ""
    ids = []
    if "--ids" in argv:
        for i in argv[argv.index("--ids") + 1:]:
            if i.startswith("--"):
                break
            ids.append(i)
    pairs = []
    if "--pairs" in argv:
        for p in argv[argv.index("--pairs") + 1:]:
            if p.startswith("--"):
                break
            pairs.append(tuple(p.split(":")))
    tasks = {t["id"]: t for t in (json.loads(l) for l in TASKS.read_text(encoding="utf-8").splitlines() if l.strip())}

    from fl_common import serve
    from run_capacity import model_dirs, park, unpark
    before = model_dirs()
    unpark(variant)
    report = {"model": variant, "repeat": REPEAT, "ids": {}, "pairs": {}}
    try:
        with serve(variant) as base:
            c = OpenAI(base_url=base, api_key="not-needed-locally")
            ask = lambda prompt: answer(c, variant, prompt + suffix, 512)
            for i in ids:
                t = tasks[i]
                same = [ask(t["prompt"]) for _ in range(REPEAT)]
                after = []
                for _ in range(REPEAT):
                    ask(FILLER)
                    after.append(ask(t["prompt"]))
                runs = {"same prompt again": same, "after another prompt": after}
                report["ids"][i] = {k: {"distinct_texts": len({r["text"] for r in v}), "correct": [score(t, r["text"]) for r in v],
                                        "completion_tokens": [r["completion_tokens"] for r in v], "texts": [r["text"][:200] for r in v]}
                                    for k, v in runs.items()}
                print(i, {k: (v["distinct_texts"], v["completion_tokens"]) for k, v in report["ids"][i].items()}, flush=True)
            for a, b in pairs:
                ta, tb = tasks[a], tasks[b]
                outs = []
                for _ in range(REPEAT):
                    ask(ta["prompt"])
                    outs.append(ask(tb["prompt"])["text"])
                # values in a's prompt that are not in b's prompt (e-mail addresses, phone numbers)
                values = lambda s: set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\d{3}-\d{4}-\d{4}", s))
                foreign = sorted(values(ta["prompt"]) - values(tb["prompt"]))
                leaks = [o for o in outs if any(f in o for f in foreign)]
                report["pairs"][f"{a}->{b}"] = {"answers": outs, "gold": tb["gold"], "correct": [score(tb, o) for o in outs],
                                                 "foreign_values_checked": foreign, "answers_containing_previous_prompt_values": leaks}
                print(f"{a}->{b}", outs, "leaks:", len(leaks), flush=True)
    finally:
        print("parked", park(model_dirs() - before))
    out = HERE / "out" / "diag"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"repeat_{variant.replace(':', '_')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
