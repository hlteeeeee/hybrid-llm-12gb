"""How long does connecting to a closed local port take to fail on this machine? (Windows retries the SYN after the RST.)

  python diag_refused.py      -> out/diag/refused_connect.txt
Median of 5 tries each: raw socket to 127.0.0.1 and to 'localhost', the openai client with max_retries=0 and with its
default retries, and with a 1 s connect timeout (what hybrid.Hybrid uses); plus a server that accepts and never answers,
to see whether timeouts are retried as well.
"""
import platform
import socket
import statistics
import time
from pathlib import Path

import openai

OUT = Path(__file__).resolve().parent / "out" / "diag" / "refused_connect.txt"


def closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def median_s(fn, n=5):
    xs, err = [], None
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            fn()
        except Exception as e:  # the failure is what is being timed
            err = type(e).__name__
        xs.append(time.perf_counter() - t0)
    return round(statistics.median(xs), 3), err


def main():
    port = closed_port()
    url = f"http://127.0.0.1:{port}/v1"
    rows = [
        ("socket.create_connection 127.0.0.1", lambda: socket.create_connection(("127.0.0.1", port), timeout=10)),
        ("socket.create_connection localhost", lambda: socket.create_connection(("localhost", port), timeout=10)),
        ("openai, max_retries=0", lambda: openai.OpenAI(base_url=url, api_key="x", max_retries=0, timeout=10).models.list()),
        ("openai, default retries", lambda: openai.OpenAI(base_url=url, api_key="x", timeout=10).models.list()),
        ("openai, max_retries=0, connect timeout 1 s", lambda: openai.OpenAI(base_url=url, api_key="x", max_retries=0,
                                                                              timeout=openai.Timeout(10, connect=1.0)).models.list()),
    ]
    # a server that accepts and never answers: are timeouts retried too?
    hang = socket.socket()
    hang.bind(("127.0.0.1", 0))
    hang.listen(16)
    hurl = f"http://127.0.0.1:{hang.getsockname()[1]}/v1"
    rows += [
        ("silent server, openai timeout 0.5 s, max_retries=0", lambda: openai.OpenAI(base_url=hurl, api_key="x", max_retries=0, timeout=0.5).models.list()),
        ("silent server, openai timeout 0.5 s, default retries", lambda: openai.OpenAI(base_url=hurl, api_key="x", timeout=0.5).models.list()),
    ]
    lines = [f"{platform.platform()}  python {platform.python_version()}  openai {openai.__version__}  {time.strftime('%Y-%m-%d %H:%M:%S %z')}"]
    for name, fn in rows:
        s, err = median_s(fn)
        lines.append(f"{name}: median {s} s ({err})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
