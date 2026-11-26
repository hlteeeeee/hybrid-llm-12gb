"""E2 task set: Japanese tasks with answers that can be checked exactly, split into dev and test halves.

Sources: JGLUE v1.3 JSQuAD and JCommonsenseQA validation sets (yahoojapan/JGLUE, CC BY-SA 4.0); MGSM Japanese
test set, read from the Hugging Face mirror juletxara/mgsm (its card says CC BY-SA 4.0; Google's original
google-research/url-nlp/mgsm/LICENSE is CC BY 4.0). The combined task file is shared under CC BY-SA 4.0.
Plus synthetic documents that contain personal data (fictional
people, made-up numbers) where the task is to extract one field: these must never leave the machine.

  python e2_tasks.py            -> data/e2_tasks.jsonl
Each line: {id, kind, split, prompt, gold, has_pii}. dev is for tuning the router, test is run once at the end.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
N_PER_KIND = 80
SEED = 20261126

INSTR = {
    "jsquad": "次の文章を読み、質問の答えを文章中からそのまま抜き出して、答えだけを出力してください。",
    "jcqa": "次の質問に最も適切な選択肢を一つ選び、その番号（0〜4）だけを出力してください。",
    "mgsm": "次の問題を解き、最後の行に「答え: 数値」の形で答えを書いてください。",
    "pii": "次の文書から指定された項目をそのまま抜き出して、その値だけを出力してください。",
}


def jsquad(rng):
    raw = json.loads((DATA / "jglue" / "jsquad-v1.3_valid.json").read_text(encoding="utf-8"))
    items = []
    for art in raw["data"]:
        for para in art["paragraphs"]:
            for qa in para["qas"]:
                if qa.get("is_impossible") or not qa["answers"]:
                    continue
                items.append({"context": para["context"], "question": qa["question"], "gold": sorted({a["text"] for a in qa["answers"]}), "qid": qa["id"]})
    rng.shuffle(items)
    out = []
    for it in items[:N_PER_KIND]:
        out.append({"id": f"jsquad-{it['qid']}", "kind": "jsquad", "has_pii": False, "gold": it["gold"],
                    "prompt": f"{INSTR['jsquad']}\n\n文章：{it['context']}\n\n質問：{it['question']}"})
    return out


def jcqa(rng):
    lines = (DATA / "jglue" / "jcommonsenseqa-v1.3_valid.json").read_text(encoding="utf-8").splitlines()
    items = [json.loads(l) for l in lines if l.strip()]
    rng.shuffle(items)
    out = []
    for it in items[:N_PER_KIND]:
        choices = "\n".join(f"{i}: {it[f'choice{i}']}" for i in range(5))
        out.append({"id": f"jcqa-{it['q_id']}", "kind": "jcqa", "has_pii": False, "gold": [str(it["label"])],
                    "prompt": f"{INSTR['jcqa']}\n\n質問：{it['question']}\n{choices}"})
    return out


def mgsm(rng):
    rows = []
    for f in sorted((DATA / "mgsm").glob("ja_test_*.json")):
        rows += [r["row"] for r in json.loads(f.read_text(encoding="utf-8"))["rows"]]
    rng.shuffle(rows)
    out = []
    for i, r in enumerate(rows[:N_PER_KIND]):
        out.append({"id": f"mgsm-{i}", "kind": "mgsm", "has_pii": False, "gold": [str(r["answer_number"])],
                    "prompt": f"{INSTR['mgsm']}\n\n{r['question']}"})
    return out


SURNAMES = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤", "吉田", "山田"]
GIVEN = ["陽菜", "蓮", "結衣", "湊", "葵", "大翔", "凛", "悠真", "美咲", "颯太"]
CITIES = ["札幌市北区", "仙台市青葉区", "横浜市港北区", "名古屋市中区", "大阪市北区", "福岡市中央区"]
FIELDS = [("電話番号", "phone"), ("メールアドレス", "email"), ("氏名", "name"), ("住所", "address")]


def pii(rng):
    """Fictional people and made-up numbers (phone numbers in the 090-0000-xxxx style, example.jp addresses)."""
    out = []
    for i in range(N_PER_KIND // 2):
        name = rng.choice(SURNAMES) + " " + rng.choice(GIVEN)
        phone = f"090-0000-{rng.randrange(1000, 9999)}"
        email = f"user{rng.randrange(100, 999)}@example.jp"
        address = f"{rng.choice(CITIES)}{rng.randrange(1, 9)}丁目{rng.randrange(1, 30)}番{rng.randrange(1, 20)}号"
        doc = (f"お客様対応記録\n対応日：2026年11月{rng.randrange(1, 28)}日\nお客様：{name} 様\n連絡先：{phone}／{email}\n"
               f"ご住所：{address}\n内容：注文した商品が届いていないとのお問い合わせ。配送状況を確認し、翌日に折り返し連絡することで合意。")
        label, key = rng.choice(FIELDS)
        gold = {"phone": phone, "email": email, "name": name, "address": address}[key]
        out.append({"id": f"pii-{i}", "kind": "pii", "has_pii": True, "gold": [gold, gold.replace(" ", "")],
                    "prompt": f"{INSTR['pii']}\n\n項目：{label}\n\n文書：\n{doc}"})
    return out


def main():
    rng = random.Random(SEED)
    tasks = jsquad(rng) + jcqa(rng) + mgsm(rng) + pii(rng)
    # dev/test split stratified by kind
    by_kind = {}
    for t in tasks:
        by_kind.setdefault(t["kind"], []).append(t)
    for items in by_kind.values():
        rng.shuffle(items)
        for j, t in enumerate(items):
            t["split"] = "dev" if j < len(items) // 2 else "test"
    path = DATA / "e2_tasks.jsonl"
    path.write_text("\n".join(json.dumps(t, ensure_ascii=False) for t in tasks) + "\n", encoding="utf-8")
    counts = {k: {s: sum(1 for t in v if t["split"] == s) for s in ("dev", "test")} for k, v in by_kind.items()}
    print(json.dumps({"tasks": len(tasks), "by_kind": counts, "file": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
