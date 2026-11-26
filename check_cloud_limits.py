"""Offline check of hybrid.Hybrid's cloud limits and error handling against a fake OpenAI-compatible upstream
(no GPU, no Foundry Local, nothing leaves 127.0.0.1). The model name picks how the fake upstream behaves:
a slow but healthy stream (also against a 2 s total limit), keep-alives only, a stream cut after one token, HTTP 400,
HTTP 401 (also on a half-open probe); plus the
e3_fallback.FakeCloud proxy in its hang and down states.

  python check_cloud_limits.py      -> prints each case and "dry run ok"
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import openai
from e3_fallback import FakeCloud
from hybrid import Breaker, Hybrid

CHUNK = lambda text, finish=None: {"id": "x", "object": "chat.completion.chunk", "created": 0, "model": "m",
                                   "choices": [{"index": 0, "delta": {"content": text} if text else {}, "finish_reason": finish}]}


class Up(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def sse(self, obj):
        self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode()); self.wfile.flush()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        m = body.get("model")
        if m in ("e400", "e401"):
            code = int(m[1:])
            data = json.dumps({"error": {"message": m, "type": "x"}}).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data); return
        if not body.get("stream"):
            if m == "slow":
                time.sleep(5)
            data = json.dumps({"id": "x", "object": "chat.completion", "created": 0, "model": "m",
                               "choices": [{"index": 0, "message": {"role": "assistant", "content": "local answer"}, "finish_reason": "stop"}],
                               "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data); return
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        if m == "slow":                       # healthy but long: a token every 0.5 s for 5 s, then finish
            for k in range(10):
                self.sse(CHUNK(f"t{k} ")); time.sleep(0.5)
            self.sse(CHUNK(None, "stop")); self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        elif m == "keepalive":                # only keep-alive comments for 20 s
            for _ in range(20):
                self.wfile.write(b": keep-alive\n\n"); self.wfile.flush(); time.sleep(1)
        elif m == "cut":                      # one token, then the connection closes without finish_reason
            self.sse(CHUNK("HALF"))


up = ThreadingHTTPServer(("127.0.0.1", 0), Up); up.daemon_threads = True
threading.Thread(target=up.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{up.server_address[1]}/v1"
local = openai.OpenAI(base_url=base, api_key="x")
fc = FakeCloud(base)
via_proxy = openai.OpenAI(base_url=f"http://127.0.0.1:{fc.port}/v1", api_key="x")
direct = openai.OpenAI(base_url=base, api_key="x")


def ask(cloud, model, stream=True, mode="up", total_s=30.0):
    fc.set_mode(mode)
    b = Breaker(2, 5)
    h = Hybrid(local, "m", cloud, model, connect_s=1.0, silence_s=3.0, first_token_s=4.0, total_s=total_s, breaker=b, stream=stream)
    t = time.perf_counter()
    try:
        r = h.ask("q", prefer="cloud")
    except Exception as e:
        return ("raised", type(e).__name__, round(time.perf_counter() - t, 2), b.fails)
    return (r["where"], r.get("cloud_error"), round(time.perf_counter() - t, 2), b.fails, r["text"][:12])


res = {
    "slow-but-healthy, streaming": ask(via_proxy, "slow"),
    "slow-but-healthy, non-streaming 3 s": ask(via_proxy, "slow", stream=False),
    "keep-alive only (first-token limit 4 s)": ask(direct, "keepalive"),
    "stream cut mid-way, direct": ask(direct, "cut"),
    "stream cut mid-way, via FakeCloud": ask(via_proxy, "cut"),
    "hang": ask(via_proxy, "slow", mode="hang"),
    "down": ask(via_proxy, "slow", mode="down"),
    "HTTP 400": ask(direct, "e400"),
    "HTTP 401": ask(direct, "e401"),
    "total limit 2 s on a healthy 5 s stream": ask(via_proxy, "slow", total_s=2.0),
}

# a half-open probe that gets 401 must raise and still release the breaker (not leave it half-open forever)
now = [0.0]
pb = Breaker(2, 5, clock=lambda: now[0])
pb.fail(); pb.fail()
now[0] = 5.0
ph = Hybrid(local, "m", direct, "e401", connect_s=1.0, silence_s=3.0, first_token_s=4.0, total_s=30.0, breaker=pb)
try:
    ph.ask("q", prefer="cloud")
    probe_raised = False
except openai.AuthenticationError:
    probe_raised = True
res["half-open probe gets 401"] = (probe_raised, pb.probing, pb.allow())
for k, v in res.items():
    print(k, v)
assert res["slow-but-healthy, streaming"][:2] == ("cloud", None) and res["slow-but-healthy, streaming"][4].startswith("t0 t1")
assert res["slow-but-healthy, non-streaming 3 s"][0] == "local:fallback"
assert res["keep-alive only (first-token limit 4 s)"][0] == "local:fallback" and 3.8 < res["keep-alive only (first-token limit 4 s)"][2] < 6
assert res["stream cut mid-way, direct"][:2] == ("local:fallback", "CloudIncomplete") and res["stream cut mid-way, direct"][3] == 1
assert res["stream cut mid-way, via FakeCloud"][:2] == ("local:fallback", "CloudIncomplete")
assert res["hang"][0] == "local:fallback" and 2.8 < res["hang"][2] < 4
assert res["down"][0] == "local:fallback" and res["down"][2] < 1.6
assert res["HTTP 400"][0] == "local:fallback" and res["HTTP 400"][3] == 0       # fell back, not counted as an outage
assert res["HTTP 401"][:2] == ("raised", "AuthenticationError")                 # configuration error is loud
t2 = res["total limit 2 s on a healthy 5 s stream"]
assert t2[:2] == ("local:fallback", "CloudIncomplete") and 1.8 < t2[2] < 3        # the total limit closes the stream
assert res["half-open probe gets 401"] == (True, False, "closed")              # raised, ticket released
print("dry run ok")
