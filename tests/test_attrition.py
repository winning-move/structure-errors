"""The derived operational numbers and the attrition reporting (PROTOCOL.md 8.1, 8.3)."""
import json
import math

import numpy as np

from np_registered import analysis as A
from np_registered.config import load_config
from np_registered.manifest import attempts_report, status

CFG = load_config()


def test_reserve_is_one_replacement_per_planned_organization():
    """One replacement per planned organization of the same structure (8.3): as many reserve ids as the largest
    sample the internal pilot can reach (168 = 2 x 84)."""
    d = CFG["design"]
    assert d["reserve_orgs_per_structure"] == d["extension"]["max_per_structure"] == 2 * d["orgs_per_structure"] == 168


def test_attempt_limit_and_tolerated_rate():
    """3 attempts (a convention, 8.1); one proposal per judge call, so a rating is missing only when all 3
    attempts of its call fail (no one-at-a-time fallback is left). Up to a per-attempt failure rate of about .020, fewer
    than one judge rating of the whole run is expected to be missing (stated in 8.1)."""
    d, j = CFG["design"], CFG["judging"]
    assert j["batch_size"] == 1
    proposals = d["extension"]["max_per_structure"] * 2 * d["roles_per_org"] * d["proposals_per_role"]   # per arm
    judge_calls = 2 * 2 * proposals * j["readings"]["ceiling"]   # two arms, two judges, at the ceiling: one call per proposal and reading
    assert judge_calls == 129024
    A_ = CFG["retries"]["content_attempts"]
    assert A_ == 3
    expected_missing = lambda p: judge_calls * p ** A_
    p_max = (1 / judge_calls) ** (1 / A_)
    assert abs(p_max - 0.0198) < 5e-4 and "pause_attempt_failure_rate" not in CFG["retries"]
    assert expected_missing(p_max - 1e-3) < 1 < expected_missing(p_max + 1e-3)


def test_haldane_estimator():
    r = A.haldane_failure_rate(completed=168, failed=12)
    assert r["run"] == 180 and abs(r["naive"] - 12 / 180) < 1e-12
    assert abs(r["haldane"] - (1 - 167 / 179)) < 1e-12
    assert math.isnan(A.haldane_failure_rate(1, 0)["haldane"])


def test_lee_bounds_bracket_the_difference_and_trim_the_right_group():
    rng = np.random.default_rng(3)
    y1, y0 = rng.normal(0.5, 1, 200), rng.normal(0.0, 1, 200)
    same = A.lee_bounds(y1, y0, 0.9, 0.9)
    assert same["lower"] == same["upper"] == float(y1.mean() - y0.mean()) and same["trimmed_group"] is None
    b = A.lee_bounds(y1, y0, 0.95, 0.80)                     # hierarchy completed more often: it is trimmed
    assert b["trimmed_group"] == "hierarchy" and abs(b["trim_share"] - (0.95 - 0.80) / 0.95) < 1e-12
    assert b["n_trimmed"] == round(b["trim_share"] * 200)
    assert b["lower"] < b["difference_in_means"] < b["upper"]
    c = A.lee_bounds(y1, y0, 0.80, 0.95)                     # polyarchy completed more often: it is trimmed
    assert c["trimmed_group"] == "polyarchy" and c["lower"] < c["difference_in_means"] < c["upper"]
    # trimming the top of the trimmed group lowers that group's mean: with hierarchy trimmed the lower bound is
    # the top-trimmed contrast; with polyarchy trimmed the upper bound is
    assert b["upper"] - b["lower"] > 0 and c["upper"] - c["lower"] > 0


def _calls_file(path, n_calls, fail_first, exhausted=0):
    rows = []
    for i in range(n_calls):
        cid = f"judge:x:1:{i:04d}"
        if i < fail_first:
            rows.append({"call_id": cid, "stage": "judge", "content_attempt": 1, "valid": False, "error": "invalid: ids returned []",
                         "response_raw": {"choices": [{"message": {"reasoning_content": "I would rate 70"}}]}, "text": "{}",
                         "usage": {"completion_tokens": 100}})
            rows.append({"call_id": cid, "stage": "judge", "content_attempt": 2, "valid": True, "error": None, "parsed": {"ratings": []},
                         "usage": {"completion_tokens": 300}})
        else:
            rows.append({"call_id": cid, "stage": "judge", "content_attempt": 1, "valid": True, "error": None, "parsed": {"ratings": []},
                         "usage": {"completion_tokens": 300}})
    for i in range(exhausted):
        cid = f"judge:x:1:{9000 + i}"
        for a in (1, 2, 3):
            rows.append({"call_id": cid, "stage": "judge", "content_attempt": a, "valid": False, "error": "invalid: x", "usage": {}})
        rows.append({"call_id": cid, "stage": "judge", "exhausted": True, "valid": False, "error": "no valid answer after 3 attempts"})
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_attempts_report_counts_and_writes_the_audit(tmp_path):
    _calls_file(tmp_path / "calls_judge_glimmer.jsonl", 40, fail_first=4)
    rep = attempts_report(tmp_path, write_audit=True)["calls_judge_glimmer.jsonl"]
    assert rep["attempts_completed"] == 44 and rep["content_failures"] == 4 and rep["first_attempt_failures"] == 4
    assert rep["outcomes_from_a_retry"] == 4 and rep["exhausted_logical_calls"] == 0
    assert abs(rep["content_failure_rate"] - 4 / 44) < 1e-12
    rows = [json.loads(l) for l in open(tmp_path / rep["audit_file"])]
    assert len(rows) == 4 and rows[0]["reasoning_text"] == "I would rate 70" and rows[0]["later_valid_attempt"] == 2


def test_status_counts_failures_and_never_asks_for_a_pause(tmp_path):
    (tmp_path / "orgs.jsonl").write_text(""); (tmp_path / "org_failures.jsonl").write_text("")
    _calls_file(tmp_path / "calls_judge_glimmer.jsonl", 400, fail_first=4)              # 4 of 404 attempts
    s = status(CFG, tmp_path, 84)
    assert "4 content failures" in s and "PAUSE" not in s
    _calls_file(tmp_path / "calls_judge_glimmer.jsonl", 40, fail_first=20)            # 20 of 60 attempts = 33%
    s = status(CFG, tmp_path, 84)
    assert "20 content failures = 33.3%" in s and "PAUSE" not in s
    _calls_file(tmp_path / "calls_judge_glimmer.jsonl", 40, fail_first=0, exhausted=2)   # 2 of 42 logical calls exhausted
    s = status(CFG, tmp_path, 84)
    assert "2 exhausted = 4.8%" in s and "PAUSE" not in s


def test_fallback_counts_read_the_recorded_metadata(tmp_path):
    orgs = [{'structure': 'hierarchy'}, {'structure': 'polyarchy'}]
    props = [{'proposal_id': 'p', 'structure': 'hierarchy'}]
    vote = {'proposal_id': 'p', 'blind_id': 'P1', 'decision': 'approve'}
    (tmp_path / 'votes_gemma.jsonl').write_text(json.dumps(vote) + '\n')
    (tmp_path / 'ratings_glimmer.jsonl').write_text(json.dumps(vote) + '\n')
    for stage in ('evaluation_gemma', 'judge_glimmer'):
        row = {'call_id': 'batch:single:P1', 'content_attempt': 1, 'valid': True,
               'fallback_single': True, 'blind_ids': ['P1']}
        (tmp_path / f'calls_{stage}.jsonl').write_text(json.dumps(row) + '\n')
    result = A.attrition_and_fallbacks(tmp_path, orgs, props, 'votes_gemma.jsonl', 'glimmer')
    assert result['single_mode_proposals_evaluation']['hierarchy'] == 1
    assert result['single_mode_proposals_judge']['hierarchy'] == 1


def test_failed_attempt_audit_retains_streamed_reasoning(tmp_path):
    row = {'call_id': 'judge:batch', 'content_attempt': 1, 'valid': False, 'error': 'invalid: no ratings',
           'response_raw': {'content': [{'type': 'thinking', 'thinking': 'reasoning before refusal'}]}}
    (tmp_path / 'calls_judge_claude.jsonl').write_text(json.dumps(row) + '\n')
    result = attempts_report(tmp_path, write_audit=True)['calls_judge_claude.jsonl']
    audit = [json.loads(line) for line in (tmp_path / result['audit_file']).read_text().splitlines()]
    assert audit[0]['reasoning_text'] == 'reasoning before refusal'
