"""Pipeline on the mock backend: allocation, information flow, retries, failures, resume."""
import json
from collections import Counter

import pytest

from np_registered import stages
from np_registered.backends import MockBackend, Reply
from np_registered.config import load_config, load_prompts
from np_registered.runner import CallLog, Failed, run_call
from np_registered.schemas import GENERATION_SCHEMA, Invalid, validate_generation

CFG, PR = load_config(), load_prompts()


def test_allocation_balanced_deterministic():
    a, b = stages.allocate(CFG), stages.allocate(CFG)
    assert a == b
    main = [r for r in a if not r["reserve"]]
    N = CFG["design"]["orgs_per_structure"]
    assert Counter(r["structure"] for r in main) == {"hierarchy": N, "polyarchy": N}
    for blk in {r["block"] for r in main}:
        assert Counter(r["structure"] for r in main if r["block"] == blk) == {"hierarchy": 2, "polyarchy": 2}
    assert [r["org_id"] for r in main] == [f"org{i:03d}" for i in range(1, 2 * N + 1)]
    assert sum(1 for r in a if r["reserve"]) == 2 * CFG["design"]["reserve_orgs_per_structure"]


class Recorder(MockBackend):
    def __init__(self):
        super().__init__()
        self.prompts = []

    def complete(self, prompt, schema, name, seed=None):
        self.prompts.append(prompt)
        return super().complete(prompt, schema, name, seed)


def test_information_flow(tmp_path):
    be = Recorder()
    log = CallLog(tmp_path / "c.jsonl")
    h = stages.run_org({"org_id": "orgH", "structure": "hierarchy", "block": 1, "reserve": 0}, be, log, PR, CFG, "t")
    p = stages.run_org({"org_id": "orgP", "structure": "polyarchy", "block": 1, "reserve": 0}, be, log, PR, CFG, "t")
    hp, pp = be.prompts[:4], be.prompts[4:]
    # hierarchy: junior k sees exactly k seniors' reasoning, in order, and no proposal text
    for k, prompt in enumerate(hp):
        assert prompt.count("/100): ") == k
        for s in h["roles"][:k]:
            assert s["reasoning"] in prompt
            for prop in s["proposals"]:
                assert prop["what"] not in prompt
    assert [r["n_seniors_seen"] for r in h["roles"]] == [0, 1, 2, 3]
    # polyarchy: nobody sees anybody
    for prompt in pp:
        assert PR.hierarchy_peer_intro not in prompt
    assert all(len(r["proposals"]) == 3 for r in h["roles"] + p["roles"])


def test_content_retry_then_success(tmp_path):
    be = MockBackend(fail_first=2)
    log = CallLog(tmp_path / "c.jsonl")
    obj = run_call(be, log, "gen:x:compliance", {"stage": "generation"}, "prompt", GENERATION_SCHEMA, "generation",
                   lambda o: validate_generation(o, CFG["validation"]), CFG["retries"], seed_parts=("t",))
    recs = [json.loads(l) for l in open(tmp_path / "c.jsonl")]
    assert [r["valid"] for r in recs] == [False, False, True]
    assert all(r["error"].startswith("invalid") for r in recs[:2])
    assert recs[0]["seed"] != recs[1]["seed"]          # local models get a new seed per content attempt
    # resume: a second call returns the logged answer without calling the model
    n = be.calls
    assert run_call(be, log, "gen:x:compliance", {}, "prompt", GENERATION_SCHEMA, "generation",
                    lambda o: o, CFG["retries"]) == obj
    assert be.calls == n


def test_content_failure_exhausts(tmp_path):
    be = MockBackend(fail_first=99)
    with pytest.raises(Failed):
        run_call(be, CallLog(tmp_path / "c.jsonl"), "id", {}, "p", GENERATION_SCHEMA, "generation",
                 lambda o: validate_generation(o, CFG["validation"]), CFG["retries"])
    assert be.calls == CFG["retries"]["content_attempts"]


class Flaky(MockBackend):
    def complete(self, prompt, schema, name, seed=None):
        self.calls += 1
        if self.calls == 1:
            return Reply(False, None, None, None, {}, {}, {}, 0.0, "RateLimitError", True)
        return super().complete(prompt, schema, name, seed)


def test_transport_retry(tmp_path, monkeypatch):
    monkeypatch.setattr("np_registered.runner.time.sleep", lambda s: None)
    be = Flaky()
    run_call(be, CallLog(tmp_path / "c.jsonl"), "id", {}, "p", GENERATION_SCHEMA, "generation",
             lambda o: validate_generation(o, CFG["validation"]), CFG["retries"])
    recs = [json.loads(l) for l in open(tmp_path / "c.jsonl")]
    assert [(r["transport_attempt"], r["valid"]) for r in recs] == [(1, False), (2, True)]


def test_validation_rules():
    v = CFG["validation"]
    good = {"reasoning": " ".join(f"w{i}" for i in range(20)), "stance": 50,
            "proposals": [{"title": f"T{k}", "what": " ".join(f"a{k}{i}" for i in range(10)),
                           "how": " ".join(f"b{k}{i}" for i in range(10)), "why": "c d e f"} for k in range(3)]}
    validate_generation(good, v)
    bad = [dict(good, stance=101), dict(good, stance="50"), dict(good, proposals=good["proposals"][:2]),
           dict(good, reasoning="test"), dict(good, proposals=[good["proposals"][0]] * 3)]
    for b in bad:
        with pytest.raises(Invalid):
            validate_generation(b, v)


class FailOrg(MockBackend):
    """Fails every call for one organization's director (content failure)."""
    def complete(self, prompt, schema, name, seed=None):
        if name == "generation" and "Lab Director" in prompt and "FAILME" in prompt:
            self.calls += 1
            return Reply(True, "not json", "end_turn", "m", {}, {}, {}, 0.0)
        return super().complete(prompt, schema, name, seed)


def test_failed_org_replaced_by_reserve(tmp_path, monkeypatch):
    cfg = json.loads(json.dumps(CFG))
    alloc = stages.allocate(cfg, 2)
    be = MockBackend()
    calls = {"n": 0}
    orig = stages.run_org

    def run_org(org, *a, **k):
        if org["org_id"] == "org001":
            raise Failed("forced")
        return orig(org, *a, **k)

    monkeypatch.setattr(stages, "run_org", run_org)
    orgs = stages.run_generation(cfg, PR, be, tmp_path, "t", alloc, 2, 2, progress=lambda *_: None)
    failed_struct = next(r["structure"] for r in alloc if r["org_id"] == "org001")
    ids = [o["org_id"] for o in orgs if o["structure"] == failed_struct]
    assert "org001" not in ids and ids[-1] == f"rsv-{failed_struct}-01"
    assert Counter(o["structure"] for o in orgs) == {"hierarchy": 2, "polyarchy": 2}
    # the replacement takes the block of the organization it replaced and names it (PROTOCOL.md 8.3)
    rep = next(o for o in orgs if o["org_id"] == f"rsv-{failed_struct}-01")
    assert rep["block"] == next(r["block"] for r in alloc if r["org_id"] == "org001") and rep["replaces"] == "org001"


def test_more_failures_than_planned_organizations_is_a_registered_stop(tmp_path, monkeypatch):
    """The cap in force is one replacement per planned organization (PROTOCOL.md 8.3): with 2 planned per structure,
    a third failure of the same structure stops the run."""
    cfg = json.loads(json.dumps(CFG))
    alloc = stages.allocate(cfg, 2)
    s = next(r["structure"] for r in alloc if r["org_id"] == "org001")
    victims = {r["org_id"] for r in alloc if r["structure"] == s and not r["reserve"]} | {f"rsv-{s}-01"}
    orig = stages.run_org

    def run_org(org, *a, **k):
        if org["org_id"] in victims:
            raise Failed("forced")
        return orig(org, *a, **k)

    monkeypatch.setattr(stages, "run_org", run_org)
    with pytest.raises(stages.ReserveExhausted):
        stages.run_generation(cfg, PR, MockBackend(), tmp_path, "t", alloc, 2, 2, progress=lambda *_: None)
    assert len([l for l in (tmp_path / "org_failures.jsonl").read_text().splitlines() if l]) == 3


def test_full_mock_run(tmp_path):
    alloc = stages.allocate(CFG, 2)
    be = MockBackend()
    orgs = stages.run_generation(CFG, PR, be, tmp_path, "t", alloc, 4, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    assert len(props) == 4 * 12
    votes = stages.run_evaluation(CFG, PR, be, tmp_path, "t", props, 4, progress=lambda *_: None)
    assert len(votes) == 4 * 48 and Counter(v["role"] for v in votes) == {r: 48 for r in PR.roles["order"]}
    rows = stages.run_judge(CFG, PR, be, tmp_path, "t", "glimmer", props, 4, progress=lambda *_: None)
    assert len(rows) == CFG["judging"]["readings"]["floor"] * 48
    # every proposal evaluated once by every role and judged once per pass
    assert Counter((v["proposal_id"], v["role"]) for v in votes).most_common(1)[0][1] == 1
    assert Counter((r["proposal_id"], r["pass"]) for r in rows).most_common(1)[0][1] == 1
    # blind ids carry no structure information and evaluators/judges never see org ids
    log = [json.loads(l) for l in open(tmp_path / "calls_evaluation.jsonl")]
    assert not any("org0" in json.dumps(r["request"]) for r in log)


class Outage(MockBackend):
    """Every call fails at the transport level (the API is down)."""
    def complete(self, prompt, schema, name, seed=None):
        self.calls += 1
        return Reply(False, None, None, None, {}, {}, {}, 0.0, "APIConnectionError: down", True)


def test_outage_stops_without_recording_failures(tmp_path, monkeypatch):
    """C1: an outage must never become an organization failure, a missing vote, or a rating."""
    from np_registered.runner import Abort
    monkeypatch.setattr("np_registered.runner.time.sleep", lambda s: None)
    alloc = stages.allocate(CFG, 2)
    with pytest.raises(Abort):
        stages.run_generation(CFG, PR, Outage(), tmp_path, "t", alloc, 2, 2, progress=lambda *_: None)
    assert not (tmp_path / "org_failures.jsonl").exists()
    assert not (tmp_path / "orgs.jsonl").exists()
    # evaluation during an outage: no votes file is written
    orgs = stages.run_generation(CFG, PR, MockBackend(), tmp_path, "t", alloc, 2, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    with pytest.raises(Abort):
        stages.run_evaluation(CFG, PR, Outage(), tmp_path, "t", props, 2, progress=lambda *_: None)
    assert not (tmp_path / "votes.jsonl").exists()


def test_reserve_cap_stops_run(tmp_path):
    """C2: more failures than reserves stops the run with an error."""
    alloc = stages.allocate(CFG, 2)
    with pytest.raises(stages.ReserveExhausted):
        stages.run_generation(CFG, PR, MockBackend(fail_first=10**6), tmp_path, "t", alloc, 2, 2,
                              progress=lambda *_: None)


def test_exhausted_call_not_retried_on_resume(tmp_path):
    """M8: a call that used up its attempts is not tried again after a restart."""
    be = MockBackend(fail_first=10**6)
    for _ in range(2):
        with pytest.raises(Failed):
            run_call(be, CallLog(tmp_path / "c.jsonl"), "id", {}, "p", GENERATION_SCHEMA, "generation",
                     lambda o: validate_generation(o, CFG["validation"]), CFG["retries"])
    assert be.calls == CFG["retries"]["content_attempts"]


class InvalidThenOutage(MockBackend):
    """First call: a completed but unusable answer; afterwards the API is down."""
    def complete(self, prompt, schema, name, seed=None):
        self.calls += 1
        self.seeds = getattr(self, "seeds", []) + [seed]
        if self.calls == 1:
            return Reply(True, "not json", "end_turn", "m", {}, {}, {}, 0.0)
        return Reply(False, None, None, None, {}, {}, {}, 0.0, "APIConnectionError: down", True)


def test_resume_keeps_attempt_count_and_new_seeds(tmp_path, monkeypatch):
    """R3: attempts used before an interruption count toward the limit after a resume, with new seeds."""
    from np_registered.runner import Abort
    monkeypatch.setattr("np_registered.runner.time.sleep", lambda s: None)
    path = tmp_path / "c.jsonl"
    v = lambda o: validate_generation(o, CFG["validation"])
    with pytest.raises(Abort):
        run_call(InvalidThenOutage(), CallLog(path), "id", {}, "p", GENERATION_SCHEMA, "generation", v,
                 CFG["retries"], seed_parts=("t",))
    be = MockBackend(fail_first=10**6)
    seeds = []
    orig = be.complete
    be.complete = lambda prompt, schema, name, seed=None: (seeds.append(seed), orig(prompt, schema, name, seed))[1]
    with pytest.raises(Failed):
        run_call(be, CallLog(path), "id", {}, "p", GENERATION_SCHEMA, "generation", v, CFG["retries"], seed_parts=("t",))
    recs = [json.loads(l) for l in open(path)]
    completed_invalid = [r for r in recs if str(r.get("error") or "").startswith("invalid")]
    assert len(completed_invalid) == CFG["retries"]["content_attempts"]
    assert len({r["seed"] for r in completed_invalid}) == len(completed_invalid)


def test_abort_stops_queue_promptly(tmp_path, monkeypatch):
    """R4: after an outage, queued organizations are not started."""
    from np_registered.runner import Abort
    monkeypatch.setattr("np_registered.runner.time.sleep", lambda s: None)
    be = Outage()
    alloc = stages.allocate(CFG, 20)
    with pytest.raises(Abort):
        stages.run_generation(CFG, PR, be, tmp_path, "t", alloc, 2, 20, progress=lambda *_: None)
    assert be.calls <= 4 * CFG["retries"]["transport_attempts"]   # at most the organizations in flight, not all 40


def test_resume_after_an_interrupted_write(tmp_path, capsys):
    """A crash while a record is being appended leaves an incomplete last line; the stage must still resume, redo
    only what that line described (here from the call log, with no new model call), and never merge two records."""
    alloc = stages.allocate(CFG, 2)
    orgs = stages.run_generation(CFG, PR, MockBackend(), tmp_path, "t", alloc, 4, 2, progress=lambda *_: None)
    op, cp = tmp_path / "orgs.jsonl", tmp_path / "calls_generation.jsonl"
    raw = op.read_bytes()
    cut_id = json.loads(raw.rstrip(b"\n").rsplit(b"\n", 1)[-1])["org_id"]
    op.write_bytes(raw[: raw.rstrip(b"\n").rfind(b"\n") + 1 + 40])          # the last organization cut after 40 bytes
    with open(cp, "ab") as f:
        f.write('{"call_id": "gen:unfinished", "text": "naïve'.encode()[:-1])   # cut inside a character
    be = MockBackend()
    stages.run_generation(CFG, PR, be, tmp_path, "t", alloc, 4, 2, progress=lambda *_: None)
    assert be.calls == 0                                    # every call of the cut organization was in the log
    again = stages.read_jsonl(op)
    assert sorted(o["org_id"] for o in again) == sorted(o["org_id"] for o in orgs)
    same = lambda o: [p["text"] for p in stages.proposals_of([o])]
    assert same(next(o for o in again if o["org_id"] == cut_id)) == same(next(o for o in orgs if o["org_id"] == cut_id))
    assert "incomplete line" in capsys.readouterr().err
    # the next record starts on its own line: the remains stay one skipped line, never part of a record
    log = CallLog(cp)
    log.append({"call_id": "gen:after", "valid": True, "parsed": {}})
    assert "gen:after" in CallLog(cp).done and "gen:unfinished" not in CallLog(cp).done
    assert len([l for l in cp.read_text(encoding="utf-8", errors="replace").splitlines() if "gen:unfinished" in l]) == 1


def test_fallback_resume_keeps_completed_items_and_single_item_metadata(tmp_path):
    from np_registered.runner import Abort
    from np_registered.schemas import EVALUATION_SCHEMA, check_vote
    from np_registered import prompts as P
    class InterruptedSingles(MockBackend):
        recovered = False
        completed = []
        def complete(self, prompt, schema, name, seed=None):
            ids = [row['id'] for row in json.loads(prompt[prompt.index('['):prompt.rindex(']') + 1])]
            if len(ids) > 1:
                self.calls += 1
                return Reply(True, 'not JSON', 'end_turn', 'mock-model', {}, {}, {}, 0.)
            if ids == ['P2'] and not self.recovered:
                self.calls += 1
                return Reply(False, None, None, None, {}, {}, {}, 0., 'transport interrupted', False)
            self.completed.append(ids[0])
            return super().complete(prompt, schema, name, seed)
    backend = InterruptedSingles()
    path = tmp_path / 'calls.jsonl'
    build = lambda ids: P.evaluation_prompt(PR, PR.roles['order'][0], [{'id': bid, 'text': 'proposal text'} for bid in ids])
    def run():
        return stages._with_singles(backend, CallLog(path), 'batch', {'blind_ids': ['P1', 'P2']}, build,
                                   EVALUATION_SCHEMA, 'evaluation', check_vote, 'screenings', ['P1', 'P2'],
                                   CFG['retries'], ('test',))
    with pytest.raises(Abort):
        run()
    backend.recovered = True
    result = run()
    assert set(result) == {'P1', 'P2'}
    assert backend.completed == ['P1', 'P2']
    before = backend.calls
    assert run() == result and backend.calls == before
    records = stages.read_jsonl(path)
    assert sum(r.get('error', '').startswith('invalid') for r in records if r.get('error')) == 3
    singles = [r for r in records if r.get('valid') and r.get('fallback_single')]
    assert all(r['blind_ids'] == [r['parsed']['screenings'][0]['id']] for r in singles)


def test_judge_reads_one_proposal_per_call_with_all_six_subscales_in_random_order(tmp_path):
    """One proposal per judge call rating all six subscales; the three dimensions in a random order, each
    followed by its two subscales in a random order, seeded by proposal and reading, recorded in the call and the row,
    shown in the prompt, and followed by the schema."""
    import json
    from collections import Counter
    from np_registered import stages
    from np_registered.backends import MockBackend
    from np_registered.config import load_prompts
    from np_registered.prompts import judge_plan, judge_prompt_all
    from np_registered.schemas import JUDGE_SUBSCALES, judge_schema_for
    pr = load_prompts()
    alloc = stages.allocate(CFG, 2)
    orgs = stages.run_generation(CFG, pr, MockBackend(), tmp_path, "t", alloc, 4, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    rows = stages.run_judge(CFG, pr, MockBackend(), tmp_path, "t", "glimmer", props, 4, progress=lambda *_: None, passes=2)
    calls = [json.loads(l) for l in open(tmp_path / "calls_judge_glimmer.jsonl")]
    assert len(calls) == 2 * len(props) and all(len(c["blind_ids"]) == 1 for c in calls)
    assert all(sorted(c["subscale_order"]) == sorted(JUDGE_SUBSCALES) for c in calls)
    assert len(rows) == 2 * len(props) and all(r[s] is not None for r in rows for s in JUDGE_SUBSCALES)
    firsts = Counter(c["dimension_order"][0] for c in calls)
    assert len(firsts) == 3                                    # every dimension comes first in some calls
    plan = judge_plan(CFG, "P1203", 1)
    assert plan == judge_plan(CFG, "P1203", 1) and [judge_plan(CFG, "P1203", k) for k in range(1, 9)] != [plan] * 8
    built = judge_prompt_all(pr, [{"id": "P1203", "text": "x"}], plan)
    order = [s for _, pair in plan for s in pair]
    assert ("SUBSCALES IN ORDER: " + ", ".join(order)) in built
    keys = list(judge_schema_for(tuple(order))["properties"]["ratings"]["items"]["properties"])
    assert keys == ["id"] + [k for s in order for k in (f"{s}_evidence", s)]


def test_batch_judge_follows_the_attempt_rules(tmp_path):
    """The second judge through a batch API: every pending call in one batch; expired requests re-sent (not an attempt);
    unusable answers re-sent with the identical prompt in the next batch (an attempt); records as in run_call."""
    import json
    from np_registered import stages
    from np_registered.backends import MockBackend, MockBatchBackend
    from np_registered.config import load_prompts
    pr = load_prompts()
    alloc = stages.allocate(CFG, 2)
    orgs = stages.run_generation(CFG, pr, MockBackend(), tmp_path, "t", alloc, 4, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    be = MockBatchBackend(fail_first=3, expire_first=2)
    rows = stages.run_judge(CFG, pr, be, tmp_path, "t", "claude", props, 4, progress=lambda *_: None, passes=1)
    recs = [json.loads(l) for l in open(tmp_path / "calls_judge_claude.jsonl")]
    assert len(rows) == len(props) and not any(r.get("missing") for r in rows)
    assert be.batches >= 2 and all(r.get("extra", {}).get("batch_id") for r in recs if "exhausted" not in r)
    assert sum(1 for r in recs if str(r.get("error") or "").startswith("invalid")) == 3
    assert sum(1 for r in recs if "expired" in str(r.get("error") or "")) == 2
    assert {r["call_id"] for r in recs if r.get("valid")} == {r["call_id"] for r in recs}   # every call ends valid
    n_batches = be.batches
    again = stages.run_judge(CFG, pr, be, tmp_path, "t", "claude", props, 4, progress=lambda *_: None, passes=1)
    assert len(again) == len(rows) and be.batches == n_batches                              # resume: nothing re-sent
    assert not list(tmp_path.glob("calls_judge_claude.batch*.json"))                      # no pending batch left


def test_batch_pending_from_an_earlier_session_is_polled_not_resent(tmp_path, monkeypatch):
    """A stop while a batch was pending (any chunk, not only the first): the next session polls that batch through its
    saved file and submits only the calls it did not hold; chunks respect the size limit; no file is left behind."""
    import json
    from np_registered import runner, stages
    from np_registered.backends import MockBackend
    from np_registered.config import load_prompts

    class _Fake:
        batch = True

        def __init__(self):
            self.inner, self.submitted, self.resumed = MockBackend(), [], []

        def describe(self):
            return {"backend": "fake_batch", "model": self.inner.model}

        @staticmethod
        def custom_id(call_id):
            return call_id

        def run_batch(self, calls, resume_file=None):
            ids = sorted(c for c, *_ in calls)
            if resume_file is not None and resume_file.exists():
                assert sorted(json.loads(resume_file.read_text())["custom_ids"]) == ids
                self.resumed.append(ids)
            else:
                self.submitted.append(ids)
            if resume_file is not None:
                resume_file.unlink(missing_ok=True)
            return {c: self.inner.complete(p, s, n) for c, p, s, n in calls}, f"b{len(self.submitted) + len(self.resumed)}"

    pr = load_prompts()
    alloc = stages.allocate(CFG, 2)
    orgs = stages.run_generation(CFG, pr, MockBackend(), tmp_path, "t", alloc, 4, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    monkeypatch.setattr(runner, "BATCH_CHUNK", 10)
    held = [f"judge:claude:1:{i:04d}" for i in (3, 14, 25, 36, 47)]           # a batch an earlier session left pending
    (tmp_path / "calls_judge_claude.batch7.json").write_text(json.dumps({"batch_id": "msgbatch_old", "custom_ids": held}))
    (tmp_path / "calls_judge_claude.batch2.json").write_text("not json")      # a torn file: removed, nothing else
    be = _Fake()
    rows = stages.run_judge(CFG, pr, be, tmp_path, "t", "claude", props, 4, progress=lambda *_: None, passes=1)
    assert len(rows) == len(props) and not any(r.get("missing") for r in rows)
    assert be.resumed == [sorted(held)]                                        # polled once through its file
    assert not any(set(held) & set(s) for s in be.submitted)                   # never submitted again
    assert all(len(s) <= 10 for s in be.submitted) and sum(map(len, be.submitted)) == len(props) - len(held)
    assert not list(tmp_path.glob("calls_judge_claude.batch*.json"))
