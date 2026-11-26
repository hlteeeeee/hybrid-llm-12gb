"""E3: what happens to users when the cloud goes away. A local proxy stands in for the cloud and is switched between
  up    forwards to the local Foundry endpoint, streaming included (answers stay correct; only availability is measured)
  hang  accepts the request and never answers (a server or path that went silent: the client waits for its timeout)
  down  nothing listens on the port (connection refused)
A timer thread switches the proxy on schedule, independently of the requests, OFFSET_S after the request tick so a
send and a switch never coincide. Each outage starts from a healthy cloud (up, hang, up, down, up), so the breaker meets
each failure closed. One user sends a request every INTERVAL seconds (a request that takes longer delays the next one).
Tasks cycle through short (JCommonsenseQA, JSQuAD) and long (MGSM, several seconds) non-personal test tasks, so a slow
but healthy cloud is part of the test. A request belongs to the phase in effect when it was sent.

Configurations:
  breaker            streaming cloud call: connect 1 s, silence 3 s (no bytes), first token 10 s, total 60 s;
                     breaker opens after 2 failures for 5 s
  no-breaker         same limits, never opens
  breaker-nonstream-3s  non-streaming cloud call with a 3 s timeout: nothing arrives until the answer is complete,
                     so the 3 s has to cover the whole generation (the naive version)

  python e3_fallback.py qwen3-8b-cuda-gpu:2
  python e3_fallback.py --summarise      (rebuild the report from the saved jsonl)
Writes out/e3_fallback.jsonl (per request, written as it goes) and out/e3_fallback.md (per phase + summary).
"""
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import openai

from e2_run import score
from hybrid import Breaker, Hybrid

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SCHEDULE = [("up", 10), ("hang", 20), ("up", 15), ("down", 15), ("up", 15)]  # (cloud state, seconds)
INTERVAL, OFFSET_S = 0.5, 0.25
CONNECT_S, SILENCE_S, FIRST_TOKEN_S, TOTAL_S, COOLDOWN_S = 1.0, 3.0, 10.0, 60.0, 5.0
CONFIGS = [("breaker", 2, True), ("no-breaker", 10**9, True), ("breaker-nonstream-3s", 2, False)]  # (name, threshold, stream)


def switch_times():
    """When each phase begins (the first at 0, the others OFFSET_S after the nominal second)."""
    return [0.0] + [sum(s for _, s in SCHEDULE[:j]) + OFFSET_S for j in range(1, len(SCHEDULE))]


class FakeCloud:
    def __init__(self, upstream: str):
        self.upstream, self.mode = upstream, "up"
        self.server = self._start(0)
        self.port = self.server.server_address[1]

    def _start(self, port: int) -> ThreadingHTTPServer:
        cloud = self

        class Handler(BaseHTTPRequestHandler):  # HTTP/1.0: the body ends when the connection closes, so streaming needs no framing
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if cloud.mode == "hang":
                    deadline = time.monotonic() + 120
                    while cloud.mode == "hang" and time.monotonic() < deadline:
                        time.sleep(0.05)
                    return  # the client gave up long ago; close without answering
                headers = {"Content-Type": "application/json"}
                if self.headers.get("Authorization"):  # so a real cloud can stand behind the proxy too
                    headers["Authorization"] = self.headers["Authorization"]
                req = urllib.request.Request(cloud.upstream + "/chat/completions", data=body, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=300) as r:
                        self.send_response(200)
                        self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
                        self.end_headers()
                        while chunk := r.read1(8192):
                            self.wfile.write(chunk)
                            self.wfile.flush()
                except Exception:
                    # the client hung up (the non-streaming configuration), or the upstream broke mid-way: closing the
                    # connection now ends the body without a finish_reason, which the client treats as a failure
                    return

        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server

    def set_mode(self, mode: str) -> None:
        if mode == "down" and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        elif mode != "down" and self.server is None:
            self.server = self._start(self.port)
        self.mode = mode


def run_config(name, threshold, stream, local, base, variant, tasks, starts, total, fh):
    cloud = FakeCloud(base)
    client = openai.OpenAI(base_url=f"http://127.0.0.1:{cloud.port}/v1", api_key="fake")
    h = Hybrid(local, variant, client, variant, connect_s=CONNECT_S, silence_s=SILENCE_S, first_token_s=FIRST_TOKEN_S,
               total_s=TOTAL_S, breaker=Breaker(threshold, COOLDOWN_S), stream=stream)
    t0 = time.monotonic()

    def switcher():  # the cloud changes state on time, whatever requests are in flight
        for j, (mode, _) in enumerate(SCHEDULE):
            time.sleep(max(0.0, t0 + starts[j] - time.monotonic()))
            cloud.set_mode(mode)

    sw = threading.Thread(target=switcher, daemon=True)
    sw.start()
    rows, i = [], 0
    while (el := time.monotonic() - t0) < total:
        j = phase_at(el, starts)  # sends are on the 0.5 s grid, switches 0.25 s off it: no ties
        t = tasks[i % len(tasks)]
        i += 1
        try:
            r = h.ask(t["prompt"] + " /no_think", prefer="cloud")
            r["correct"] = score(t, r["text"])
        except Exception as e:  # the local side failed too: recorded as unanswered
            r = {"where": "error", "error": str(e)[:200], "correct": False}
        row = {"config": name, "phase": f"{j + 1}:{SCHEDULE[j][0]}", "sent_at_s": round(el, 3), "done_at_s": round(time.monotonic() - t0, 3),
               "id": t["id"], "kind": t["kind"], **{k: v for k, v in r.items() if k != "text"}}
        rows.append(row)
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        print(name, row["phase"], row["sent_at_s"], row["where"], row.get("total_s"), flush=True)
        nxt = INTERVAL * (int((time.monotonic() - t0) / INTERVAL) + 1)
        time.sleep(max(0.0, t0 + nxt - time.monotonic()))
    sw.join()
    cloud.set_mode("down")
    return rows


def phase_at(t, starts):
    return max(j for j, s in enumerate(starts) if t >= s)


def summarise(rows, starts):
    """Uses the phase stored with each request (the phase in effect when it was sent). A fallback in a healthy phase
    counts as a false alarm only if the whole wait for the cloud lay inside that phase. Recovery: the first request
    answered by the cloud that finished after the cloud came back, including one sent just before (a probe in flight)."""
    ends = starts[1:] + [sum(s for _, s in SCHEDULE)]
    out = []
    for name, _, _ in CONFIGS:
        mine = sorted((r for r in rows if r["config"] == name), key=lambda r: r["sent_at_s"])
        for j, (mode, _) in enumerate(SCHEDULE):
            ph = [r for r in mine if r["phase"] == f"{j + 1}:{mode}"]
            if mode != "up":
                waits = [r["cloud_wait_s"] for r in ph if "cloud_wait_s" in r]
                fast = next((r for r in ph if r["where"].startswith("local") and "cloud_wait_s" not in r), None)
                when = f"+{round(fast['sent_at_s'] - starts[j], 2)} s" if fast else "never"
                out.append(f"{name}, outage {j + 1} ({mode}, {round(ends[j] - starts[j], 2)} s): {len(ph)} requests sent, {len(waits)} waited for the cloud "
                           f"(total {round(sum(waits), 1)} s, each {waits}); first request served locally without waiting sent at {when}")
            else:
                false_fb = [r for r in ph if "cloud_wait_s" in r and r["sent_at_s"] + r["cloud_wait_s"] <= ends[j]]
                out.append(f"{name}, phase {j + 1} (cloud healthy): {len(false_fb)} false alarms"
                           + (f" ({[(r['kind'], r['cloud_error'], r.get('completion_tokens')) for r in false_fb]})" if false_fb else ""))
                if j > 0:
                    back = next((r for r in mine if r["where"] == "cloud" and r["done_at_s"] >= starts[j]), None)
                    when = (f"sent at {round(back['sent_at_s'] - starts[j], 2):+} s, finished at +{round(back['done_at_s'] - starts[j], 2)} s"
                            if back else "never")
                    out.append(f"{name}, cloud back at {round(starts[j], 2)} s: first cloud answer {when} (relative to the cloud coming back)")
    return out


def write_report(rows, starts):
    summary = summarise(rows, starts)
    lines = [f"connect {CONNECT_S}s, silence {SILENCE_S}s, first token {FIRST_TOKEN_S}s, total {TOTAL_S}s; breaker opens after "
             f"2 consecutive failures for {COOLDOWN_S}s; one request every {INTERVAL}s; phases {SCHEDULE}, switched at {starts}",
             "", *[f"- {s}" for s in summary], "",
             "| config | phase | requests | waited for cloud | total wait s | max wait s | where |", "|---|---|---|---|---|---|---|"]
    for name, _, _ in CONFIGS:
        for phase in dict.fromkeys(r["phase"] for r in rows):
            rs = [r for r in rows if r["config"] == name and r["phase"] == phase]
            waits = [r["cloud_wait_s"] for r in rs if "cloud_wait_s" in r]
            where = {}
            for r in rs:
                where[r["where"]] = where.get(r["where"], 0) + 1
            lines.append(f"| {name} | {phase} | {len(rs)} | {len(waits)} | {round(sum(waits), 2)} | {max(waits) if waits else ''} | {json.dumps(where, ensure_ascii=False)} |")
    (OUT / "e3_fallback.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main(argv):
    starts = switch_times()
    total = sum(s for _, s in SCHEDULE)
    if argv[0] == "--summarise":  # rebuild the report from out/e3_fallback.jsonl without running anything
        write_report([json.loads(l) for l in (OUT / "e3_fallback.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()], starts)
        return
    variant = argv[0]
    tasks = [json.loads(l) for l in (HERE / "data" / "e2_tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by_kind = {k: [t for t in tasks if t["split"] == "test" and t["kind"] == k] for k in ("jcqa", "jsquad", "mgsm")}
    tasks = [t for trio in zip(*by_kind.values()) for t in trio]  # jcqa, jsquad, mgsm, jcqa, ...

    from fl_common import serve
    from run_capacity import model_dirs, park, unpark
    OUT.mkdir(exist_ok=True)
    before = model_dirs()
    unpark(variant)
    rows = []
    try:
        with serve(variant) as base, (OUT / "e3_fallback.jsonl").open("w", encoding="utf-8") as fh:
            local = openai.OpenAI(base_url=base, api_key="not-needed-locally")
            for name, threshold, stream in CONFIGS:
                rows += run_config(name, threshold, stream, local, base, variant, tasks, starts, total, fh)
        write_report(rows, starts)
    finally:
        print("parked", park(model_dirs() - before))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
