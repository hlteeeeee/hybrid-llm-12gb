"""The hybrid router used in the article: personal data never leaves the machine, the caller's routing choice picks local
or cloud for the rest, and a cloud failure falls back to the local model behind a circuit breaker.

Both sides are OpenAI-compatible clients; only base_url and model differ. The cloud call streams and is bounded by four
limits: connect_s to connect, silence_s with no bytes at all, first_token_s until the first generated token (answer or
reasoning), total_s for the whole answer. A slow but healthy cloud that keeps streaming a long answer is not mistaken
for an outage; a cloud that sends only keep-alives, or never finishes, is. A stream that ends without a finish_reason
(cut off mid-way) counts as a failure, not as an answer.
  python hybrid.py      self-check: breaker logic on a fake clock, and how the personal-data rule scores on the E2 tasks
"""
import json
import re
import threading
import time
from pathlib import Path

import openai

# ponytail: regexes for the formats in this article's data (Japanese phone numbers, e-mail, addresses written with
# Arabic numerals such as 「3丁目」). A production system needs a real PII detector (names, card numbers, free-form
# addresses, 「三丁目」); see the self-check numbers.
PERSONAL_RE = re.compile(r"0\d{1,4}-\d{1,4}-\d{3,4}|[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\d+丁目|〒\s?\d{3}-?\d{4}")


def looks_personal(text: str) -> bool:
    return bool(PERSONAL_RE.search(text))


class Breaker:
    """Closed until `threshold` consecutive cloud failures; then open for `cooldown_s` (requests go straight to local).
    After the cooldown it is half-open: exactly one request (the probe) tries the cloud while the others keep going local.
    allow() hands out a ticket: None (stay local), "closed" (a normal attempt) or "probe". Only the probe's result moves
    the breaker out of half-open; a late failure of an older "closed" attempt never releases a second probe. Thread-safe."""

    def __init__(self, threshold: int = 2, cooldown_s: float = 30.0, clock=time.monotonic):
        self.threshold, self.cooldown_s, self.clock = threshold, cooldown_s, clock
        self.fails, self.open_until, self.probing = 0, 0.0, False
        self.lock = threading.Lock()

    def allow(self):
        with self.lock:
            if self.fails < self.threshold:
                return "closed"
            if self.probing or self.clock() < self.open_until:
                return None
            self.probing = True
            return "probe"

    def ok(self, ticket="closed") -> None:
        with self.lock:
            self.fails = 0
            if ticket == "probe":
                self.probing = False

    def fail(self, ticket="closed") -> None:
        with self.lock:
            if ticket == "probe":
                self.probing = False
                self.fails = max(self.fails + 1, self.threshold)
                self.open_until = self.clock() + self.cooldown_s
                return
            self.fails += 1
            if self.fails >= self.threshold and not self.probing:
                self.open_until = max(self.open_until, self.clock() + self.cooldown_s)


class CloudIncomplete(Exception):
    """The stream ended without a finish_reason: cut off, or closed by the first-token / total deadline."""


def _usage(u) -> dict:
    return {"prompt_tokens": u.prompt_tokens if u else None, "completion_tokens": u.completion_tokens if u else None}


def _ask(client: openai.OpenAI, model: str, prompt: str, max_tokens: int, timeout=None) -> dict:
    t0 = time.perf_counter()
    r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens,
                                       temperature=0, timeout=timeout)
    return {"text": r.choices[0].message.content or "", "total_s": round(time.perf_counter() - t0, 3), **_usage(r.usage)}


def _ask_stream(client: openai.OpenAI, model: str, prompt: str, max_tokens: int, timeout, first_token_s: float, total_s: float) -> dict:
    t0 = time.perf_counter()
    parts, usage, finished, started = [], None, False, threading.Event()
    stream = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens,
                                            temperature=0, stream=True, stream_options={"include_usage": True}, timeout=timeout)
    # Keep-alive comments are swallowed by the SDK, so the loop below cannot see time passing: timers close the stream.
    left = lambda limit: max(0.0, limit - (time.perf_counter() - t0))
    timers = [threading.Timer(left(first_token_s), lambda: None if started.is_set() else stream.close()),
              threading.Timer(left(total_s), stream.close)]
    for t in timers:
        t.daemon = True
        t.start()
    try:
        for ch in stream:
            usage = ch.usage or usage
            if not ch.choices:
                continue
            c = ch.choices[0]
            if c.delta.content or (c.delta.model_extra or {}).get("reasoning_content"):
                started.set()
            if c.delta.content:
                parts.append(c.delta.content)
            if c.finish_reason:
                finished = True
    except Exception as e:  # the stream was closed by a timer or broke mid-way
        raise CloudIncomplete(f"stream broken after {time.perf_counter() - t0:.1f} s: {type(e).__name__}") from e
    finally:
        for t in timers:
            t.cancel()
    if not finished:
        raise CloudIncomplete(f"stream ended without finish_reason after {time.perf_counter() - t0:.1f} s")
    return {"text": "".join(parts), "total_s": round(time.perf_counter() - t0, 3), **_usage(usage)}


class Hybrid:
    def __init__(self, local: openai.OpenAI, local_model: str, cloud: openai.OpenAI, cloud_model: str,
                 connect_s: float = 1.0, silence_s: float = 5.0, first_token_s: float = 15.0, total_s: float = 120.0,
                 breaker: Breaker | None = None, max_tokens: int = 512, stream: bool = True):
        # the openai client retries connection errors, timeouts, 408/409/429 and 5xx twice by default; here the
        # fallback to the local model is the retry
        self.local, self.local_model, self.cloud, self.cloud_model = local, local_model, cloud.with_options(max_retries=0), cloud_model
        self.breaker, self.max_tokens, self.stream = breaker or Breaker(), max_tokens, stream
        self.first_token_s, self.total_s = first_token_s, total_s
        # stream=False is kept only to show the failure mode in E3: without streaming, the read timeout has to cover
        # the whole generation (nothing arrives until the answer is complete)
        self.timeout = openai.Timeout(silence_s, connect=connect_s) if stream else silence_s

    def _local(self, prompt: str, where: str) -> dict:
        return {**_ask(self.local, self.local_model, prompt, self.max_tokens), "where": where}

    def ask(self, prompt: str, prefer: str = "cloud") -> dict:
        """prefer is the caller's choice for this kind of request (e.g. by which feature sent it); personal data overrides it."""
        if looks_personal(prompt):
            return self._local(prompt, "local:personal")
        if prefer == "local":
            return self._local(prompt, "local:rule")
        ticket = self.breaker.allow()
        if ticket is None:
            return self._local(prompt, "local:breaker-open")
        t0 = time.perf_counter()
        try:
            if self.stream:
                out = _ask_stream(self.cloud, self.cloud_model, prompt, self.max_tokens, self.timeout, self.first_token_s, self.total_s)
            else:
                out = _ask(self.cloud, self.cloud_model, prompt, self.max_tokens, self.timeout)
        except openai.APIStatusError as e:  # the cloud answered with an HTTP error
            if e.status_code in (401, 403, 404):
                # wrong key, no access or wrong model name: a configuration error must be loud, not a silent fallback.
                # The cloud did answer, so the ticket is released as a success (a probe must not stay out forever).
                self.breaker.ok(ticket)
                raise
            outage = e.status_code >= 500 or e.status_code in (408, 409, 429)
            return self._fallback(prompt, t0, e, ticket, outage)  # e.g. 400: this request's problem; the cloud is up
        except Exception as e:  # connect/read timeout, refused connection, broken or unfinished stream
            return self._fallback(prompt, t0, e, ticket, True)
        self.breaker.ok(ticket)
        return {**out, "where": "cloud"}

    def _fallback(self, prompt, t0, err, ticket, outage: bool) -> dict:
        (self.breaker.fail if outage else self.breaker.ok)(ticket)
        waited = round(time.perf_counter() - t0, 3)
        out = self._local(prompt, "local:fallback")
        out["cloud_wait_s"] = waited
        out["total_s"] = round(time.perf_counter() - t0, 3)  # includes the time lost waiting for the cloud
        out["cloud_error"] = type(err).__name__
        out["counted_as_outage"] = outage
        return out


def _self_check() -> None:
    now = [0.0]
    b = Breaker(threshold=2, cooldown_s=10, clock=lambda: now[0])
    assert b.allow() == "closed"
    b.fail()
    assert b.allow() == "closed"          # one failure: still closed
    b.fail()
    assert b.allow() is None              # second consecutive failure opens it
    now[0] = 10.0
    assert b.allow() == "probe"           # cooldown over: this caller is the probe
    assert b.allow() is None              # while the probe is out, everyone else stays local
    b.fail("probe")
    assert b.allow() is None              # the probe failed: open again at once
    now[0] = 20.0
    assert b.allow() == "probe"
    b.ok("probe")                         # the next probe succeeded: closed
    assert b.allow() == "closed" and b.allow() == "closed"
    b.fail()
    assert b.allow() == "closed"          # a success reset the count

    # a late failure of an old attempt while a probe is out must not release a second probe
    now[0], c = 0.0, Breaker(threshold=2, cooldown_s=5, clock=lambda: now[0])
    c.fail(); c.fail()
    now[0] = 5.0
    assert c.allow() == "probe"
    now[0] = 6.0
    c.fail("closed")                      # stale failure from before the breaker opened
    now[0] = 11.0
    assert c.allow() is None              # still one probe at a time
    c.ok("probe")
    assert c.allow() == "closed"

    tasks = [json.loads(l) for l in (Path(__file__).resolve().parent / "data" / "e2_tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    tp = sum(1 for t in tasks if t["has_pii"] and looks_personal(t["prompt"]))
    fn = [t["id"] for t in tasks if t["has_pii"] and not looks_personal(t["prompt"])]
    fp = [t["id"] for t in tasks if not t["has_pii"] and looks_personal(t["prompt"])]
    print(json.dumps({"personal_tasks_detected": f"{tp}/{tp + len(fn)}", "missed": fn,
                      "other_tasks_flagged": f"{len(fp)}/{sum(1 for t in tasks if not t['has_pii'])}", "flagged_ids": fp}, ensure_ascii=False))
    assert not fn, "a personal-data task would leave the machine"
    assert not looks_personal("東京都港区三丁目")  # the documented limit: kanji numerals are not caught
    print("self-check ok")


if __name__ == "__main__":
    _self_check()
