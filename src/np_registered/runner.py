"""Run one logical call under the registered retry rules and log every attempt.

Two kinds of failure, handled differently (PROTOCOL.md section 8):
- transport failure (rate limit, server error, timeout, connection): the identical request
  is re-sent with exponential backoff, up to retries.transport_attempts;
- content failure (the call completed but the answer is unusable: invalid JSON, schema or
  registered validity rule violated, refusal, max_tokens): the identical prompt is re-issued,
  up to retries.content_attempts in all.

Every attempt, successful or not, is appended to calls.jsonl with the full request, the
full raw response (the model's reasoning text included), and the times it was sent and answered (UTC). The log is append-only; a resumed run skips logical calls that already
have a valid attempt. A line left incomplete by an interrupted write (a crash while appending)
is skipped with a warning, so the call it described is run again; no complete record is ever
skipped or changed.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import scrub
from .schemas import Invalid

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def read_records(path: Path) -> list[dict]:
    """Every complete record of an append-only JSONL file. A line that is not valid JSON can only be the remains of
    a write that was interrupted (a crash or power loss while appending); it is skipped with a warning, so the call
    or organization it described is simply done again when the stage resumes. A complete record is never skipped."""
    if not path.exists():
        return []
    rows, torn = [], 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                torn += 1
    if torn:
        print(f"WARNING: {path.name}: {torn} incomplete line(s) from an interrupted write skipped", file=sys.stderr)
    return rows


def start_on_new_line(path: Path):
    """Before appending: if the file ends in the middle of a line (an interrupted write), end that line first, so a
    new record never joins the remains of an old one. Nothing already in the file changes."""
    try:
        with open(path, "rb") as f:
            f.seek(-1, 2)
            ends_mid_line = f.read(1) != b"\n"
    except OSError:          # no file yet, or an empty one
        return
    if ends_mid_line:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")


class CallLog:
    def __init__(self, path: Path):
        self.path = path
        self.done: dict[str, dict] = {}
        self.exhausted: set[str] = set()
        self.n_invalid: dict[str, int] = {}   # completed but unusable answers already used, per call
        for rec in read_records(path):
            self._index(rec)

    def _index(self, rec: dict):
        if rec.get("valid"):
            self.done[rec["call_id"]] = rec
        elif rec.get("exhausted"):
            self.exhausted.add(rec["call_id"])
        elif str(rec.get("error") or "").startswith("invalid"):
            self.n_invalid[rec["call_id"]] = self.n_invalid.get(rec["call_id"], 0) + 1

    def append(self, rec: dict):
        line = scrub(json.dumps(rec, ensure_ascii=False))
        with _lock:
            start_on_new_line(self.path)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            self._index(rec)


class Failed(RuntimeError):
    """A logical call whose completed answers were unusable on every registered attempt
    (a content failure). Recorded as terminal: a resumed run does not try it again."""


class Abort(RuntimeError):
    """A transport or account failure that did not clear (outage, rate limit that persists,
    authentication, billing, invalid request). Never recorded as an outcome: the stage stops and
    is resumed later with the identical requests (PROTOCOL.md 8.1)."""


def run_call(backend, log: CallLog, call_id: str, meta: dict, prompt: str, schema: dict, name: str,
             validate, retries: dict, seed_parts: tuple = ()) -> dict:
    """Return the parsed, validated answer. Raises Failed when the attempts are exhausted."""
    if call_id in log.done:
        return log.done[call_id]["parsed"]
    if call_id in log.exhausted:
        raise Failed(f"{call_id}: attempts already exhausted in an earlier session")
    from .backends import call_seed
    # attempts already used in an earlier session count toward the limit (and keep their seeds)
    content_attempt = log.n_invalid.get(call_id, 0)
    while content_attempt < retries["content_attempts"]:
        content_attempt += 1
        seed = call_seed(*seed_parts, content_attempt) if seed_parts else None
        for transport_attempt in range(1, retries["transport_attempts"] + 1):
            sent = now()
            reply = backend.complete(prompt, schema, name, seed=seed)
            rec = {"call_id": call_id, **meta, "content_attempt": content_attempt,
                   "transport_attempt": transport_attempt, "time_sent_utc": sent, "time_utc": now(), "seed": seed,
                   "backend": backend.describe(), "request": reply.request, "response_raw": reply.raw,
                   "text": reply.text, "stop_reason": reply.stop_reason, "model_returned": reply.model_returned,
                   "usage": reply.usage, "latency_s": round(reply.latency_s, 3), "extra": reply.extra,
                   "valid": False, "error": reply.error, "parsed": None}
            if not reply.ok:
                log.append(rec)
                if reply.retryable and transport_attempt < retries["transport_attempts"]:
                    wait = min(120, 5 * 2 ** (transport_attempt - 1))
                    print(f"  retry {transport_attempt}/{retries['transport_attempts'] - 1} for {call_id} in {wait}s: "
                          f"{(reply.error or '')[:120]}", file=sys.stderr, flush=True)
                    time.sleep(wait)
                    continue
                if reply.retryable:
                    raise Abort(f"{call_id}: transport failed {transport_attempt} times: {reply.error}")
                raise Abort(f"{call_id}: non-retryable API error: {reply.error}")
            # completed: check content
            try:
                obj = check_content(reply, validate)
            except Invalid as e:
                rec["error"] = f"invalid: {e}"
                log.append(rec)
                break  # next content attempt, identical prompt
            rec["valid"], rec["parsed"] = True, obj
            log.append(rec)
            return obj
    log.append({"call_id": call_id, **meta, "exhausted": True, "valid": False, "time_utc": now(),
                "error": f"no valid answer after {retries['content_attempts']} attempts"})
    raise Failed(f"{call_id}: no valid answer after {retries['content_attempts']} attempts")


def check_content(reply, validate) -> dict:
    """The parsed answer of a completed reply, or Invalid (a content failure, PROTOCOL.md 8.1)."""
    if reply.stop_reason in ("refusal", "max_tokens", "length"):
        raise Invalid(f"stop_reason={reply.stop_reason}")
    if not reply.text:
        raise Invalid("no text in response")
    try:
        obj = json.loads(reply.text)
    except json.JSONDecodeError as e:
        raise Invalid(f"invalid JSON: {e}")
    validate(obj)
    return obj


BATCH_CHUNK = 10_000     # requests per batch (the API accepts 100,000; smaller batches end sooner and limit what one failure holds)


def _batch_chunks(log: CallLog, items: list[dict], backend) -> list[tuple[list[dict], Path]]:
    """The batches to run in this round, each with the file that records its batch id while it is pending
    (<log stem>.batch<n>.json next to the log). First the batches an earlier session submitted and did not collect
    (a stop while a batch was pending): a saved batch whose requests are all still pending is polled again through its
    file, never submitted twice, whichever chunk it was. A saved file whose requests are not all pending is stale (its
    answers were collected) and is removed. The remaining calls are cut into chunks of at most BATCH_CHUNK, each with a
    free file name."""
    custom = getattr(backend, "custom_id", None) or (lambda c: c)
    by_cid = {custom(sp["call_id"]): sp for sp in items}
    chunks, taken = [], set()
    for f in sorted(log.path.parent.glob(log.path.stem + ".batch*.json")):
        try:
            ids = set(json.loads(f.read_text()).get("custom_ids", []))
        except (OSError, ValueError):
            ids = set()
        if ids and ids <= set(by_cid) and not (ids & taken):
            chunks.append(([sp for sp in items if custom(sp["call_id"]) in ids], f))
            taken |= ids
        else:
            f.unlink(missing_ok=True)
    rest = [sp for sp in items if custom(sp["call_id"]) not in taken]
    n = 0
    for start in range(0, len(rest), BATCH_CHUNK):
        while (f := log.path.with_name(f"{log.path.stem}.batch{n}.json")).exists():
            n += 1
        chunks.append((rest[start:start + BATCH_CHUNK], f))
        n += 1
    return chunks


def run_calls_batch(backend, log: CallLog, specs: list[dict], retries: dict, progress=print) -> dict:
    """The same registered rules as run_call, for a backend that answers in batches (the Anthropic Batch API; PROTOCOL.md
    5.4, 8.1). specs: [{call_id, meta, prompt, schema, name, validate}]. Every pending call is submitted in one batch (in
    chunks of at most BATCH_CHUNK requests; a batch left pending by an earlier session is polled again, not re-sent,
    _batch_chunks); when the batch has ended, every answer is logged as an attempt exactly as run_call
    logs it (full request, full raw response, text, stop reason, usage, the batch id and the submit and end times). A
    request that errored, expired (unanswered after 24 hours), or was canceled is a transport failure: re-sent unchanged,
    up to retries.transport_attempts times, then Abort. A completed answer that fails validation is a content failure:
    re-sent with the identical prompt in the next batch, up to retries.content_attempts in all, then recorded as
    exhausted. Returns {call_id: parsed answer or None (exhausted)}."""
    out, pending, transport, rounds_failed = {}, {}, {}, 0
    for sp in specs:
        cid = sp["call_id"]
        if cid in log.done:
            out[cid] = log.done[cid]["parsed"]
        elif cid in log.exhausted:
            out[cid] = None
        else:
            pending[cid] = sp
    while pending:
        if rounds_failed:                                     # after a round with transport failures: the same backoff as run_call
            time.sleep(min(120, 5 * 2 ** (rounds_failed - 1)))
        items = list(pending.values())
        any_transport = False
        for chunk, resume_file in _batch_chunks(log, items, backend):
            sent = now()
            replies, batch_id = backend.run_batch([(sp["call_id"], sp["prompt"], sp["schema"], sp["name"]) for sp in chunk],
                                                  resume_file=resume_file)
            ended = now()
            progress(f"  batch {batch_id}: {len(chunk)} requests ended")
            for sp in chunk:
                cid = sp["call_id"]
                reply = replies[cid]
                attempt = log.n_invalid.get(cid, 0) + 1
                rec = {"call_id": cid, **sp["meta"], "content_attempt": attempt,
                       "transport_attempt": transport.get(cid, 0) + 1, "time_sent_utc": sent, "time_utc": ended,
                       "seed": None, "backend": backend.describe(), "request": reply.request, "response_raw": reply.raw,
                       "text": reply.text, "stop_reason": reply.stop_reason, "model_returned": reply.model_returned,
                       "usage": reply.usage, "latency_s": None, "extra": {**reply.extra, "batch_id": batch_id},
                       "valid": False, "error": reply.error, "parsed": None}
                if not reply.ok:
                    log.append(rec)
                    transport[cid] = transport.get(cid, 0) + 1
                    any_transport = True
                    if not reply.retryable or transport[cid] >= retries["transport_attempts"]:
                        raise Abort(f"{cid}: batch request failed {transport[cid]} times: {reply.error}")
                    continue
                try:
                    obj = check_content(reply, sp["validate"])
                except Invalid as e:
                    rec["error"] = f"invalid: {e}"
                    log.append(rec)
                    if log.n_invalid.get(cid, 0) >= retries["content_attempts"]:
                        log.append({"call_id": cid, **sp["meta"], "exhausted": True, "valid": False, "time_utc": now(),
                                    "error": f"no valid answer after {retries['content_attempts']} attempts"})
                        out[cid] = None
                        pending.pop(cid)
                    continue
                rec["valid"], rec["parsed"] = True, obj
                log.append(rec)
                out[cid] = obj
                pending.pop(cid)
        rounds_failed = rounds_failed + 1 if any_transport else 0
    return out
