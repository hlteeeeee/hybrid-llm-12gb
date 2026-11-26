"""Download the public datasets e2_tasks.py reads: JGLUE v1.3 (JSQuAD, JCommonsenseQA validation; CC BY-SA 4.0) and
the Japanese MGSM test set (via the Hugging Face datasets-server). Existing files are kept unless --force.

  python fetch_data.py [--dest data] [--force]
"""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
JGLUE = "https://raw.githubusercontent.com/yahoojapan/JGLUE/main"
MGSM = "https://datasets-server.huggingface.co/rows?dataset=juletxara%2Fmgsm&config=ja&split=test&offset={off}&length=100"


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fetch-data/1.0"}), timeout=60) as r:
        return r.read()


def main(argv):
    dest = Path(argv[argv.index("--dest") + 1]) if "--dest" in argv else HERE / "data"
    force = "--force" in argv
    files = {dest / "jglue" / "LICENSE": f"{JGLUE}/LICENSE"}
    for d in ("jsquad-v1.3", "jcommonsenseqa-v1.3"):
        files[dest / "jglue" / f"{d}_valid.json"] = f"{JGLUE}/datasets/{d}/valid-v1.3.json"
    for off in (0, 100, 200):  # 250 problems, 100 rows per request
        files[dest / "mgsm" / f"ja_test_{off}.json"] = MGSM.format(off=off)
    for path, url in files.items():
        if path.exists() and not force:
            print("keep", path)
            continue
        data = get(url)
        if path.suffix == ".json":  # fail loudly on an error page instead of saving it (JCommonsenseQA is one object per line)
            try:
                json.loads(data)
            except json.JSONDecodeError:
                [json.loads(l) for l in data.decode("utf-8").splitlines() if l.strip()]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print("wrote", path, len(data), "bytes")


if __name__ == "__main__":
    main(sys.argv[1:])
