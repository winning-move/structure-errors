"""Model backends. Each takes one user-message prompt and a JSON schema and returns a Reply.

- AnthropicBackend / AnthropicBatchBackend: the Claude API (Messages; Message Batches), structured output via
  output_config.format. No system prompt and no server-side model fallback (a fallback would replace the registered
  model); refusals are content failures under the registered retry rule.
- OpenAIChatBackend: an OpenAI-compatible local server (LM Studio), structured output via response_format json_schema.
- MockBackend: a deterministic fake for the tests and the dry run; never used for data.

Every backend returns the full request body and the full raw response so that the
call log is the complete record.
"""
from __future__ import annotations

import hashlib
import re
import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import scrub


@dataclass
class Reply:
    ok: bool                       # transport succeeded and a final message exists
    text: str | None               # the JSON text of the answer (None if absent)
    stop_reason: str | None
    model_returned: str | None
    usage: dict
    request: dict
    raw: dict
    latency_s: float
    error: str | None = None
    retryable: bool = False        # transport error worth retrying with the same request
    extra: dict = field(default_factory=dict)


def _strip_for_anthropic(schema):
    """Remove keywords the API structured outputs do not support (kept client-side in schemas.py). The local
    server (LM Studio) receives the schema as built, item counts included (schemas.with_count)."""
    if isinstance(schema, dict):
        return {k: _strip_for_anthropic(v) for k, v in schema.items()
                if k not in ("minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength")}
    if isinstance(schema, list):
        return [_strip_for_anthropic(x) for x in schema]
    return schema


def call_seed(*parts) -> int:
    """Deterministic 31-bit seed from the call's identity (arm, stage, unit, attempt)."""
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) & 0x7FFFFFFF


class AnthropicBackend:
    def __init__(self, model: str, effort: str, max_tokens: int, thinking_display: str = "summarized"):
        import anthropic  # imported lazily so tests run without the SDK configured
        if not os.environ.get("ANTHROPIC_API_KEY"):
            from .runner import Abort
            raise Abort("ANTHROPIC_API_KEY is not set (registered/.env or the environment); nothing was sent")
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(max_retries=0, timeout=600.0)
        self.model, self.effort, self.max_tokens, self.display = model, effort, max_tokens, thinking_display

    def describe(self) -> dict:
        return {"backend": "anthropic", "model": self.model, "effort": self.effort,
                "max_tokens": self.max_tokens,
                "thinking": {"type": "adaptive", "display": self.display} if self.display else {"type": "adaptive"},
                "sdk_version": self._anthropic.__version__}

    def request(self, prompt: str, schema: dict) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "thinking": {"type": "adaptive", "display": self.display} if self.display else {"type": "adaptive"},
            "output_config": {"effort": self.effort,
                              "format": {"type": "json_schema", "schema": _strip_for_anthropic(schema)}},
            "messages": [{"role": "user", "content": prompt}],
        }

    @staticmethod
    def reply_from(msg, req: dict, latency: float) -> "Reply":
        raw = msg.model_dump(mode="json")
        text = "".join(b.text for b in msg.content if b.type == "text") or None
        thinking = [getattr(b, "thinking", "") for b in msg.content if b.type == "thinking"]
        return Reply(True, text, msg.stop_reason, msg.model, raw.get("usage", {}), req, raw,
                     latency, extra={"thinking_summary": "\n".join(t for t in thinking if t)})

    def complete(self, prompt: str, schema: dict, name: str, seed: int | None = None) -> Reply:
        req = self.request(prompt, schema)
        t0 = time.time()
        try:
            with self.client.messages.stream(**req) as stream:
                msg = stream.get_final_message()
        except (self._anthropic.RateLimitError, self._anthropic.InternalServerError,
                self._anthropic.APIConnectionError, self._anthropic.APITimeoutError) as e:
            return Reply(False, None, None, None, {}, req, {}, time.time() - t0, scrub(f"{type(e).__name__}: {e}"), True)
        except self._anthropic.APIStatusError as e:
            retry = getattr(e, "status_code", 0) in (408, 409, 429, 500, 502, 503, 504, 529)
            return Reply(False, None, None, None, {}, req, {}, time.time() - t0,
                         scrub(f"{type(e).__name__} {getattr(e, 'status_code', '')}: {e}"), retry)
        except Exception as e:  # noqa: BLE001 - e.g. a connection dropped mid-stream: treat as transport
            return Reply(False, None, None, None, {}, req, {}, time.time() - t0, scrub(f"{type(e).__name__}: {e}"), True)
        return self.reply_from(msg, req, time.time() - t0)


class AnthropicBatchBackend(AnthropicBackend):
    """The second judge through the Anthropic Message Batches API (PROTOCOL.md 5.4): the same requests as AnthropicBackend
    (same model, settings, and prompts), sent together and answered when the batch ends (usually within an hour, at most
    24 hours), at half the price. run_batch submits, polls until the batch has ended, and returns every answer by call id;
    errored, expired, and canceled requests come back as transport failures (an invalid request is not retryable)."""

    batch = True

    def __init__(self, model: str, effort: str, max_tokens: int, thinking_display: str = "summarized",
                 poll_seconds: int = 60):
        super().__init__(model, effort, max_tokens, thinking_display)
        self.poll_seconds = poll_seconds

    def describe(self) -> dict:
        return {**super().describe(), "backend": "anthropic_batch"}

    @staticmethod
    def custom_id(call_id: str) -> str:
        return "c" + hashlib.sha256(call_id.encode()).hexdigest()[:40]      # the API allows [A-Za-z0-9_-]{1,64}

    POLL_MAX_S = 26 * 3600            # a batch ends within 24 hours (every unfinished request expires then); then give up

    def run_batch(self, calls: list[tuple], resume_file: "Path | None" = None) -> tuple[dict, str]:
        """calls: [(call_id, prompt, schema, name)]. Returns ({call_id: Reply}, batch_id).
        resume_file: where the batch id and its custom ids are written as soon as the batch is created, so that a run
        stopped while the batch is pending (Ctrl-C, a crash) polls the same batch again instead of submitting the
        requests twice; removed once the results are collected. Polling retries on its own after a network error
        (the batch keeps running at the API), with waits of up to 5 minutes, for at most 26 hours."""
        reqs, back = {}, {}
        for call_id, prompt, schema, _name in calls:
            cid = self.custom_id(call_id)
            reqs[call_id], back[cid] = self.request(prompt, schema), call_id
        t0 = time.time()
        batch_id = None
        if resume_file is not None and resume_file.exists():          # a batch submitted by an earlier session
            try:
                saved = json.loads(resume_file.read_text())
                if set(saved.get("custom_ids", [])) == set(back):
                    batch_id = saved["batch_id"]
            except (OSError, ValueError, KeyError):
                batch_id = None
        if batch_id is None:
            try:
                batch = self.client.messages.batches.create(
                    requests=[{"custom_id": self.custom_id(c), "params": r} for c, r in reqs.items()])
            except Exception as e:  # noqa: BLE001 - the batch was not created: every call is a transport failure
                err = scrub(f"{type(e).__name__}: {e}")
                bad = getattr(e, "status_code", 500) in (400, 401, 403, 404)
                return {c: Reply(False, None, None, None, {}, r, {}, time.time() - t0, err, not bad) for c, r in reqs.items()}, "none"
            batch_id = batch.id
            if resume_file is not None:
                resume_file.write_text(json.dumps({"batch_id": batch_id, "custom_ids": sorted(back),
                                                   "created_utc": datetime.now(timezone.utc).isoformat()}))
        results, wait, started = None, self.poll_seconds, time.time()
        while results is None:
            try:
                batch = self.client.messages.batches.retrieve(batch_id)
                if batch.processing_status == "ended":
                    results = list(self.client.messages.batches.results(batch_id))
                    break
                wait = self.poll_seconds
            except Exception as e:  # noqa: BLE001 - a network or server error while polling: the batch keeps running
                print(f"  batch {batch_id}: {type(e).__name__} while polling; retrying in {wait}s", flush=True)
                wait = min(300, wait * 2)
            if time.time() - started > self.POLL_MAX_S:
                err = f"batch {batch_id} not collected after {self.POLL_MAX_S // 3600} hours"
                return {c: Reply(False, None, None, None, {}, r, {}, time.time() - t0, err, True) for c, r in reqs.items()}, batch_id
            time.sleep(wait)
        if resume_file is not None:
            try:
                resume_file.unlink()
            except OSError:
                pass
        out = {}
        for res in results:
            call_id = back.get(res.custom_id)
            if call_id is None:
                continue
            kind = res.result.type
            if kind == "succeeded":
                rep = self.reply_from(res.result.message, reqs[call_id], time.time() - t0)
                rep.extra["custom_id"] = res.custom_id
                out[call_id] = rep
            else:
                detail = res.result.model_dump(mode="json") if hasattr(res.result, "model_dump") else {}
                etype = str(json.dumps(detail))
                retry = not (kind == "errored" and "invalid_request" in etype)   # a request the API rejects as malformed never clears
                out[call_id] = Reply(False, None, None, None, {}, reqs[call_id], detail, time.time() - t0,
                                     scrub(f"batch result {kind}: {etype[:300]}"), retry)
        for call_id, r in reqs.items():                       # a request missing from the results: treat as expired
            out.setdefault(call_id, Reply(False, None, None, None, {}, r, {}, time.time() - t0,
                                          "batch result missing", True))
        return out, batch_id

    def complete(self, prompt: str, schema: dict, name: str, seed: int | None = None) -> Reply:
        """One request as a batch of one (the preflight's tiny batch)."""
        replies, _ = self.run_batch([("preflight", prompt, schema, name)])   # no resume file: a tiny request
        return replies["preflight"]


class MockBatchBackend:
    """Tests only: the batch interface over the deterministic MockBackend (fail_first answers are unusable)."""

    batch = True

    def __init__(self, fail_first: int = 0, expire_first: int = 0):
        self.inner, self.expire_first, self.batches = MockBackend(fail_first=fail_first), expire_first, 0

    def describe(self) -> dict:
        return {"backend": "mock_batch", "model": self.inner.model}

    def run_batch(self, calls: list[tuple], resume_file=None) -> tuple[dict, str]:
        self.batches += 1
        out = {}
        for call_id, prompt, schema, name in calls:
            if self.expire_first > 0:
                self.expire_first -= 1
                out[call_id] = Reply(False, None, None, None, {}, {"prompt_sha256": "x"}, {}, 0.0, "batch result expired", True)
            else:
                out[call_id] = self.inner.complete(prompt, schema, name)
        return out, f"mockbatch_{self.batches}"


class OpenAIChatBackend:
    """An OpenAI-compatible local server (LM Studio). Each request has a 30-minute limit."""

    def __init__(self, model: str, max_tokens: int, base_url: str, sampling: dict | None = None,
                 seed_per_call: bool = False):
        import openai
        self._openai = openai
        self.client = openai.OpenAI(base_url=base_url, api_key="lm-studio", max_retries=0, timeout=1800.0)
        self.model, self.max_tokens, self.base_url = model, max_tokens, base_url
        self.sampling, self.seed_per_call = sampling or {}, seed_per_call

    def describe(self) -> dict:
        return {"backend": "openai_compatible", "model": self.model, "base_url": self.base_url,
                "max_tokens": self.max_tokens, "sampling": self.sampling, "seed_per_call": self.seed_per_call,
                "sdk_version": self._openai.__version__}

    def complete(self, prompt: str, schema: dict, name: str, seed: int | None = None) -> Reply:
        req = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
            "max_tokens": self.max_tokens,
        }
        for k in ("temperature", "top_p"):
            if k in self.sampling:
                req[k] = self.sampling[k]
        extra_body = {"top_k": self.sampling["top_k"]} if "top_k" in self.sampling else {}
        if self.seed_per_call and seed is not None:
            req["seed"] = seed
        t0 = time.time()
        try:
            resp = self.client.chat.completions.create(**req, extra_body=extra_body or None)
        except (self._openai.RateLimitError, self._openai.InternalServerError,
                self._openai.APIConnectionError, self._openai.APITimeoutError) as e:
            return Reply(False, None, None, None, {}, req, {}, time.time() - t0, scrub(f"{type(e).__name__}: {e}"), True)
        except self._openai.APIStatusError as e:
            retry = retryable_status(getattr(e, "status_code", 0), str(e))
            return Reply(False, None, None, None, {}, req, {}, time.time() - t0,
                         scrub(f"{type(e).__name__} {getattr(e, 'status_code', '')}: {e}"), retry)
        except Exception as e:  # noqa: BLE001 - e.g. a dropped connection: treat as transport
            return Reply(False, None, None, None, {}, req, {}, time.time() - t0, scrub(f"{type(e).__name__}: {e}"), True)
        raw = resp.model_dump(mode="json")
        if extra_body:
            req = {**req, "extra_body": extra_body}
        ch = resp.choices[0] if resp.choices else None
        text = strip_reasoning(ch.message.content) if ch else None
        refusal = getattr(ch.message, "refusal", None) if ch else None
        stop = "refusal" if refusal else (ch.finish_reason if ch else None)
        return Reply(True, text, stop, resp.model, raw.get("usage") or {}, req, raw, time.time() - t0)


def retryable_status(status: int, message: str) -> bool:
    """Which API errors are transport failures (re-sent with backoff, PROTOCOL.md 8.1): rate limits, server errors,
    timeouts, and LM Studio's context-pool overflow. With parallel slots sharing one context pool, a request that
    does not fit while the other slots are busy is refused with a 400 whose message says the context size was
    exceeded; it fits once the other answers have finished, so it is
    re-sent like a server error. A prompt that is itself larger than the pool fails the same way every time and
    ends in Abort after the registered attempts; the study's prompts are far below the pool."""
    msg = (message or "").lower()
    return status in (408, 409, 429, 500, 502, 503, 504) or "context size" in msg or "exceed_context_size" in msg


def strip_reasoning(text: str | None) -> str | None:
    """The answer without any reasoning that the serving software left inside it. With GGUF on LM Studio's llama.cpp
    engine the reasoning normally arrives in a separate field (kept in the raw record); some templates (Gemma 4 with
    thinking on) can leave it inside the content, between "<|channel>thought" and "<channel|>", and others between
    "<think>" and "</think>". Only the text after the last closing marker is the answer; the raw record keeps all."""
    if not text:
        return text
    for close in ("<channel|>", "</think>"):
        if close in text:
            text = text.rsplit(close, 1)[1]
    return text.strip()


class MockBackend:
    """Deterministic fake model for tests and dry runs. Produces schema-valid answers."""

    WORDS = ("audit trail logging pipeline provenance registry dashboard sandbox benchmark consortium "
             "toolkit certification protocol dataset monitoring telemetry ledger attestation workshop").split()

    def __init__(self, fail_first: int = 0, model: str = "mock-model"):
        self.fail_first, self.calls, self.model = fail_first, 0, model

    def describe(self) -> dict:
        return {"backend": "mock", "model": self.model}

    def _sent(self, rng, n):
        return " ".join(rng.choice(self.WORDS) for _ in range(n)).capitalize() + "."

    def complete(self, prompt: str, schema: dict, name: str, seed: int | None = None) -> Reply:
        self.calls += 1
        rng = random.Random(hashlib.sha256((prompt + str(seed) + str(self.calls)).encode()).hexdigest())
        req = {"model": self.model, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "name": name}
        if self.calls <= self.fail_first:
            return Reply(True, '{"broken": ', "end_turn", self.model, {}, req, {}, 0.0)
        if name == "generation":
            obj = {"reasoning": self._sent(rng, 40), "stance": rng.randint(0, 100),
                   "proposals": [{"title": self._sent(rng, 5), "what": self._sent(rng, 25),
                                  "how": self._sent(rng, 25), "why": self._sent(rng, 15)} for _ in range(3)]}
        else:
            ids = [it["id"] for it in json.loads(prompt[prompt.index("["): prompt.rindex("]") + 1])]
            if name == "evaluation":
                obj = {"screenings": [{"id": i, "rationale": self._sent(rng, 12),
                                       "decision": rng.choice(["approve", "reject"]),
                                       "promise": rng.randint(0, 100)} for i in ids]}
            else:
                from .schemas import JUDGE_SCALES
                order = re.search(r"SUBSCALES IN ORDER: ([\w, ]+)", prompt)
                subs = tuple(x.strip() for x in order.group(1).split(",")) if order else ()
                obj = {"ratings": [{"id": i, **{k: v for s in subs for k, v in
                                                ((f"{s}_evidence", self._sent(rng, 10)), (s, rng.randint(*JUDGE_SCALES[s])))}}
                                   for i in ids]}
        return Reply(True, json.dumps(obj), "end_turn", self.model, {"input_tokens": len(prompt) // 4}, req, {}, 0.0)


def make_backend(spec: dict, mock: bool = False):
    if mock:
        return MockBackend()
    kind = spec["backend"]
    if kind == "anthropic":
        return AnthropicBackend(spec["model"], spec["effort"], spec["max_tokens"], spec.get("thinking_display"))
    if kind == "anthropic_batch":
        return AnthropicBatchBackend(spec["model"], spec["effort"], spec["max_tokens"], spec.get("thinking_display"),
                                     spec.get("poll_seconds", 60))
    if kind == "openai_compatible":
        return OpenAIChatBackend(spec["model"], spec["max_tokens"], base_url=spec["base_url"],
                                 sampling=spec.get("sampling"), seed_per_call=spec.get("seed_per_call", False))
    raise ValueError(f"unknown backend {kind}")
