"""E2: answer every task once with one model and record correctness, tokens and latency per task.
Routing strategies are then compared offline (e2_score.py) by choosing, per task, the local or the cloud answer,
so no strategy needs its own model run.

  python e2_run.py foundry qwen3-8b-cuda-gpu:2 [--no-think] [--tag run2] [--kinds jsquad] [--extra "text appended to prompts"]
  python e2_run.py openai https://api.deepseek.com deepseek-chat DEEPSEEK_API_KEY
  python e2_run.py check        (scorer self-check)
Writes out/e2_<label>.jsonl (one line per task) and prints dev accuracy per kind (test is scored only by e2_score.py).
The API key is read from the named environment variable and never written anywhere.
"""
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
TASKS = HERE / "data" / "e2_tasks.jsonl"
OUT = HERE / "out"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s)).strip().lower()
    return re.sub(r"[\s「」『』（）()。、，,．.・:：\"'“”]", "", s)


def clean_output(text: str) -> str:
    """Runtime artifacts seen with Foundry Local's qwen3-14b and /no_think (56 of its 280 answers, none for the other models):
    a dangling '...</think>' before the answer and a leading 'TokenName' line. Removed for every model before scoring."""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = text.strip()
    return text[len("TokenName"):].strip() if text.startswith("TokenName") else text


def score(task: dict, text: str, lenient: bool = False) -> bool:
    """Exact scoring by default. lenient=True changes only JSQuAD: the gold span anywhere in the first line counts
    (a model that answers in a sentence, e.g. 「印刷に使用される。」 for 「印刷」, is credited)."""
    out = clean_output(text)
    kind = task["kind"]
    if kind == "jcqa":
        m = re.search(r"[0-4]", unicodedata.normalize("NFKC", out))
        return bool(m) and m.group(0) == task["gold"][0]
    if kind == "mgsm":
        # The prompt asks for a final 「答え: 数値」 line. The answer is the last number on the rest of the line after the
        # last 「答え:」/「答え：」/「答えは」 (「答え: 3 × 5 = 15」 -> 15, 「答え: 数値：240」 -> 240). A chain of reasoning cut off
        # before such a statement scores 0 (「答えを出すには、3 つの…」 is not one).
        found = list(ANSWER_RE.finditer(unicodedata.normalize("NFKC", out).replace(",", "")))
        nums = re.findall(r"-?\d+(?:\.\d+)?", found[-1].group(1)) if found else []
        return bool(nums) and float(nums[-1]) == float(task["gold"][0])
    # jsquad and pii: the first line equals a gold answer after normalisation. Applied to every model alike:
    # punctuation, quotes and spaces are ignored, and so are a leading field label from the task's own wording
    # (「ご住所：…」, 「メールアドレス: …」) and a trailing honorific (「… 様」).
    first = out.splitlines()[0] if out else ""
    cands = {first, LABEL_RE.sub("", first)}
    cands |= {HONORIFIC_RE.sub("", c) for c in cands}
    if lenient and kind == "jsquad":
        # one-character golds (「本」, 「白」) are left to exact matching: they would be found inside unrelated words
        return any(norm(c) == norm(g) or (len(norm(g)) > 1 and norm(g) in norm(c)) for c in cands for g in task["gold"])
    return any(norm(c) == norm(g) for c in cands for g in task["gold"])


ANSWER_RE = re.compile(r"答え\s*(?:は|[:：])([^\n]*)")
# only labels the tasks themselves use, so that 「東京：大阪」 is not read as label + answer
LABEL_RE = re.compile(r"^\s*(?:氏名|お名前|お客様|ご住所|住所|電話番号|電話|連絡先|メールアドレス|メール|答え|回答)\s*[:：]\s*")
HONORIFIC_RE = re.compile(r"\s*(?:様|さん|殿)$")


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def answer(client: OpenAI, model: str, prompt: str, max_tokens: int) -> dict:
    t0 = time.perf_counter()
    first, parts, usage = None, [], None
    stream = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens,
                                            temperature=0, stream=True, stream_options={"include_usage": True})
    for ch in stream:
        if ch.usage:
            usage = ch.usage
        if ch.choices:
            d = ch.choices[0].delta
            thought = getattr(d, "reasoning_content", None) or (d.model_extra or {}).get("reasoning_content")
            if d.content or thought:
                first = first or time.perf_counter()
            if d.content:
                parts.append(d.content)
    t1 = time.perf_counter()
    return {"text": strip_thinking("".join(parts)), "ttft_s": round(first - t0, 3) if first else None, "total_s": round(t1 - t0, 3),
            "prompt_tokens": usage.prompt_tokens if usage else None, "completion_tokens": usage.completion_tokens if usage else None}


def run(client: OpenAI, model: str, label: str, suffix: str = "", max_tokens: int = 512, kinds=None) -> None:
    tasks = [json.loads(l) for l in TASKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if kinds:
        tasks = [t for t in tasks if t["kind"] in kinds]
    OUT.mkdir(exist_ok=True)
    path = OUT / f"e2_{label}.jsonl"
    done = {}
    if path.exists():  # resume; a task that ended in an error is asked again (the later line wins when reading)
        for l in path.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                if "error" not in r:
                    done[r["id"]] = r
    with path.open("a", encoding="utf-8") as fh:
        for i, t in enumerate(tasks):
            if t["id"] in done:
                continue
            try:
                a = answer(client, model, t["prompt"] + suffix, max_tokens)
                rec = {"id": t["id"], "kind": t["kind"], "split": t["split"], "has_pii": t["has_pii"], "correct": score(t, a["text"]), **a}
            except Exception as e:  # recorded, not hidden: an error counts as a wrong answer in scoring
                rec = {"id": t["id"], "kind": t["kind"], "split": t["split"], "has_pii": t["has_pii"], "correct": False, "error": str(e)[:300]}
            done[t["id"]] = rec
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 20 == 0:
                print(f"{i + 1}/{len(tasks)}", flush=True)
    summary = {}
    for r in done.values():
        if r["split"] != "dev":  # test accuracy is only looked at through e2_score.py, after decisions are made on dev
            continue
        s = summary.setdefault(f"{r['kind']}/dev", [0, 0])
        s[0] += int(r["correct"])
        s[1] += 1
    print(json.dumps({k: f"{c}/{n}" for k, (c, n) in sorted(summary.items())}, ensure_ascii=False, indent=1))
    print("wrote", path)


def option(name: str):
    """Value of --name VALUE, or None; a missing value or one that looks like another option is an error."""
    if name not in sys.argv:
        return None
    i = sys.argv.index(name)
    if i + 1 >= len(sys.argv) or sys.argv[i + 1].startswith("--"):
        sys.exit(f"{name} needs a value")
    return sys.argv[i + 1]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    tag = f"_{option('--tag')}" if option("--tag") else ""          # e.g. --tag run2 for a repeat run
    extra = option("--extra") or ""                                    # text appended to every prompt (a prompt variant)
    kinds = option("--kinds").split(",") if option("--kinds") else None  # e.g. --kinds jsquad
    if mode == "foundry":
        variant = sys.argv[2]
        no_think = "--no-think" in sys.argv
        from fl_common import serve
        from run_capacity import model_dirs, park, unpark
        before = model_dirs()
        unpark(variant)  # only when HYBRID_PARK_DIR is set
        try:
            with serve(variant) as base:
                run(OpenAI(base_url=base, api_key="not-needed-locally"), variant,
                    f"local_{variant.replace(':', '_')}{'_nothink' if no_think else ''}{tag}", extra + (" /no_think" if no_think else ""), kinds=kinds)
        finally:
            print("parked", park(model_dirs() - before))
    elif mode == "openai":
        base, model, key_env = sys.argv[2], sys.argv[3], sys.argv[4]
        key = os.environ.get(key_env)
        if not key:
            sys.exit(f"environment variable {key_env} is not set")
        run(OpenAI(base_url=base, api_key=key), model, f"cloud_{model.replace('/', '_')}{tag}", extra, kinds=kinds)
    elif mode == "check":
        check_scorer()
    else:
        sys.exit(__doc__)


def check_scorer() -> None:
    """python e2_run.py check -- the scoring rules, including what they must reject."""
    pii = {"kind": "pii", "gold": ["鈴木 湊", "鈴木湊"]}
    assert score(pii, "鈴木 湊 様") and score(pii, "氏名：鈴木湊") and score(pii, "TokenName\n\n鈴木湊")
    assert not score(pii, "鈴木") and not score(pii, "鈴木 湊 様と山田 太郎 様")
    qa = {"kind": "jsquad", "gold": ["印刷", "本"]}
    assert score(qa, "「印刷」") and score(qa, ": \n\n</think>\n\n印刷") and not score(qa, "印刷に使用される。")
    assert score(qa, "印刷に使用される。", lenient=True) and not score(qa, "活字", lenient=True)
    math = {"kind": "mgsm", "gold": ["240"]}
    assert score(math, "…よって\n答え: 240") and score(math, "答え: 数値：240") and score(math, "答え:: 240")
    assert score(math, "答え: 1,200 ではなく\n答え: 240")             # the last 答え line wins
    assert score(math, "答え: 12 ではなく 240") and score(math, "答え: 3 × 80 = 240") and score(math, "したがって、答えは240人です。")
    assert score(math, "答え:カルメンはこれらのパズルに合計240分を費やすでしょう。")
    assert not score(math, "240本のキャンドルを作って、さらに")          # cut off before the answer line: no credit
    assert not score(math, "この問題の答えを出すには、240 個の箱を")       # 「答えを」 is not an answer statement
    assert not score(math, "答え: 2400") and not score(math, "答え: 240 ではなく 24")
    lab = {"kind": "jsquad", "gold": ["大阪"]}
    assert score(lab, "答え：大阪") and not score(lab, "東京：大阪")      # only the tasks' own labels are stripped
    one = {"kind": "jsquad", "gold": ["白"]}
    assert score(one, "白", lenient=True) and not score(one, "白黒の写真", lenient=True)
    mc = {"kind": "jcqa", "gold": ["1"]}
    assert score(mc, "1") and score(mc, "1: 木の実") and not score(mc, "0: 虫\n\n1: 木の実")
    print("scorer check ok")


if __name__ == "__main__":
    main()
