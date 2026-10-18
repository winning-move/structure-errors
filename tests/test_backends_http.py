"""The real SDK clients against a fake local HTTP server: checks the exact request bodies the
registered backends send, and that responses are parsed. No network, no keys, no cost."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from np_registered.backends import AnthropicBackend, OpenAIChatBackend
from np_registered.schemas import GENERATION_SCHEMA

ANSWER = {"reasoning": "r " * 20, "stance": 40,
          "proposals": [{"title": "t", "what": "w", "how": "h", "why": "y"}] * 3}
SEEN = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append((self.path, body, dict(self.headers)))
        if self.path.endswith("/v1/messages"):
            text = json.dumps(ANSWER)
            msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5",
                   "content": [], "stop_reason": None, "stop_sequence": None,
                   "usage": {"input_tokens": 100, "output_tokens": 1}}
            events = [("message_start", {"type": "message_start", "message": msg}),
                      ("content_block_start", {"type": "content_block_start", "index": 0,
                                               "content_block": {"type": "thinking", "thinking": "", "signature": ""}}),
                      ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                               "delta": {"type": "thinking_delta", "thinking": "summary of thought"}}),
                      ("content_block_stop", {"type": "content_block_stop", "index": 0}),
                      ("content_block_start", {"type": "content_block_start", "index": 1,
                                               "content_block": {"type": "text", "text": ""}}),
                      ("content_block_delta", {"type": "content_block_delta", "index": 1,
                                               "delta": {"type": "text_delta", "text": text}}),
                      ("content_block_stop", {"type": "content_block_stop", "index": 1}),
                      ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                         "usage": {"output_tokens": 50}}),
                      ("message_stop", {"type": "message_stop"})]
            payload = "".join(f"event: {e}\ndata: {json.dumps(d)}\n\n" for e, d in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            resp = {"id": "c1", "object": "chat.completion", "created": 0, "model": "gemma4",
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": json.dumps(ANSWER), "refusal": None}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
            payload = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_anthropic_request_shape(server, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", server)
    SEEN.clear()
    be = AnthropicBackend("claude-sonnet-5-5", "medium", 16000, "summarized")
    r = be.complete("PROMPT TEXT", GENERATION_SCHEMA, "generation")
    assert r.ok and json.loads(r.text) == ANSWER and r.stop_reason == "end_turn"
    assert r.model_returned == "claude-sonnet-5-5"
    assert r.extra["thinking_summary"] == "summary of thought"
    path, body, headers = SEEN[-1]
    assert path.endswith("/v1/messages") and body["stream"] is True
    assert body["model"] == "claude-sonnet-5-5" and body["max_tokens"] == 16000
    assert body["messages"] == [{"role": "user", "content": "PROMPT TEXT"}]
    assert "system" not in body and "temperature" not in body and "top_p" not in body
    assert "fallbacks" not in body and "tools" not in body
    assert body["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert body["output_config"]["effort"] == "medium"
    fmt = body["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert "minimum" not in json.dumps(fmt) and "minItems" not in json.dumps(fmt)


def test_local_gemma_request_shape(server):
    SEEN.clear()
    be = OpenAIChatBackend("gemma4", 8000, base_url=server + "/v1",
                           sampling={"temperature": 1.0, "top_p": 0.95, "top_k": 64}, seed_per_call=True)
    r = be.complete("GEN PROMPT", GENERATION_SCHEMA, "generation", seed=12345)
    assert r.ok
    _, body, _ = SEEN[-1]
    assert body["temperature"] == 1.0 and body["top_p"] == 0.95 and body["top_k"] == 64
    assert body["seed"] == 12345 and body["max_tokens"] == 8000
    assert body["temperature"] != 0
    # the local server receives the item counts (LM Studio's grammar enforces them; the API backends strip them)
    from np_registered.schemas import JUDGE_SCHEMA, with_count
    SEEN.clear()
    be.complete("JUDGE PROMPT", with_count(JUDGE_SCHEMA, "ratings", 6), "judge", seed=1)
    _, body, _ = SEEN[-1]
    arr = body["response_format"]["json_schema"]["schema"]["properties"]["ratings"]
    assert arr["minItems"] == arr["maxItems"] == 6


def test_strip_reasoning_keeps_only_the_answer():
    from np_registered.backends import strip_reasoning
    assert strip_reasoning('<|channel>thought\nlet me think<channel|>{"a": 1}') == '{"a": 1}'
    assert strip_reasoning('<think>hmm</think>\n{"a": 1}') == '{"a": 1}'
    assert strip_reasoning('{"a": 1}') == '{"a": 1}'
    assert strip_reasoning(None) is None


class _FakeBatches:
    """A fake of client.messages.batches: create, retrieve (ends on the second poll), results."""

    def __init__(self, outcomes: dict, fail_retrieve_first: int = 0):
        self.outcomes, self.created, self.polls, self.fail_retrieve_first = outcomes, [], 0, fail_retrieve_first

    def create(self, requests):
        self.created.append(requests)
        from types import SimpleNamespace
        return SimpleNamespace(id=f"msgbatch_{len(self.created)}", processing_status="in_progress")

    def retrieve(self, batch_id):
        from types import SimpleNamespace
        self.polls += 1
        if self.fail_retrieve_first > 0:
            self.fail_retrieve_first -= 1
            raise ConnectionError("network down")
        return SimpleNamespace(id=batch_id, processing_status="ended" if self.polls >= 2 else "in_progress")

    def results(self, batch_id):
        from types import SimpleNamespace
        out = []
        for req in self.created[-1]:
            kind = self.outcomes.get(req["custom_id"], "succeeded")
            if kind == "succeeded":
                msg = SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking="t"),
                                              SimpleNamespace(type="text", text=json.dumps(ANSWER))],
                                      stop_reason="end_turn", model=req["params"]["model"],
                                      model_dump=lambda mode=None, m=req["params"]["model"]: {"model": m, "usage": {"input_tokens": 5, "output_tokens": 7}})
                out.append(SimpleNamespace(custom_id=req["custom_id"], result=SimpleNamespace(type="succeeded", message=msg)))
            elif kind == "invalid":
                err = {"type": "errored", "error": {"type": "error", "error": {"type": "invalid_request_error", "message": "bad"}}}
                out.append(SimpleNamespace(custom_id=req["custom_id"], result=SimpleNamespace(type="errored", model_dump=lambda mode=None, e=err: e)))
            else:
                out.append(SimpleNamespace(custom_id=req["custom_id"], result=SimpleNamespace(type=kind, model_dump=lambda mode=None, k=kind: {"type": k})))
        return out


def test_anthropic_batch_backend_submits_polls_and_parses(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from np_registered.backends import AnthropicBatchBackend
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    be = AnthropicBatchBackend("claude-sonnet-5-5", "medium", 8000, "summarized", poll_seconds=0)
    ids = {c: AnthropicBatchBackend.custom_id(c) for c in ("judge:claude:1:0001", "judge:claude:1:0002", "judge:claude:1:0003")}
    fake = _FakeBatches({ids["judge:claude:1:0002"]: "expired", ids["judge:claude:1:0003"]: "invalid"}, fail_retrieve_first=1)
    be.client = SimpleNamespace(messages=SimpleNamespace(batches=fake))
    monkeypatch.setattr("np_registered.backends.time.sleep", lambda s: None)
    resume = tmp_path / "calls_judge_claude.batch.json"
    replies, batch_id = be.run_batch([(c, "p", GENERATION_SCHEMA, "generation") for c in ids], resume_file=resume)
    assert batch_id == "msgbatch_1" and len(fake.created) == 1 and not resume.exists()
    req = fake.created[0][0]["params"]
    assert req["model"] == "claude-sonnet-5-5" and req["output_config"]["effort"] == "medium" and "thinking" in req
    assert "minItems" not in json.dumps(req["output_config"]["format"]["schema"])
    ok = replies["judge:claude:1:0001"]
    assert ok.ok and json.loads(ok.text) == ANSWER and ok.model_returned == "claude-sonnet-5-5" and ok.extra["thinking_summary"] == "t"
    assert ok.usage == {"input_tokens": 5, "output_tokens": 7} and ok.extra["custom_id"] == ids["judge:claude:1:0001"]
    exp = replies["judge:claude:1:0002"]
    assert not exp.ok and exp.retryable and "expired" in exp.error
    bad = replies["judge:claude:1:0003"]
    assert not bad.ok and not bad.retryable and "invalid_request" in bad.error


def test_anthropic_batch_backend_resumes_a_pending_batch(monkeypatch, tmp_path):
    """A batch id saved by an earlier session is polled again; nothing is submitted twice."""
    from types import SimpleNamespace
    from np_registered.backends import AnthropicBatchBackend
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    be = AnthropicBatchBackend("claude-sonnet-5-5", "medium", 8000, "summarized", poll_seconds=0)
    calls = [(c, "p", GENERATION_SCHEMA, "generation") for c in ("a", "b")]
    fake = _FakeBatches({})
    fake.created.append([{"custom_id": AnthropicBatchBackend.custom_id(c), "params": {"model": "claude-sonnet-5-5"}} for c, *_ in calls])
    be.client = SimpleNamespace(messages=SimpleNamespace(batches=fake))
    monkeypatch.setattr("np_registered.backends.time.sleep", lambda s: None)
    resume = tmp_path / "x.batch.json"
    resume.write_text(json.dumps({"batch_id": "msgbatch_1", "custom_ids": sorted(AnthropicBatchBackend.custom_id(c) for c, *_ in calls)}))
    replies, batch_id = be.run_batch(calls, resume_file=resume)
    assert batch_id == "msgbatch_1" and len(fake.created) == 1 and all(r.ok for r in replies.values()) and not resume.exists()
