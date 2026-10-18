"""The blinded sample extension (PROTOCOL.md 6.4): generation limited to the target, waves that keep
their own blind ids and batches on resume, and the decision rule on pooled quantities only."""
import copy
import json
from collections import Counter

from np_registered import stages
from np_registered.analysis import Data, extension_candidates, extension_check
from np_registered.backends import MockBackend
from np_registered.config import load_config, load_prompts

REGISTERED, PR = load_config(), load_prompts()
QUIET = lambda *_: None
# The registered first wave is 84 per structure (test at the end of this file); the machinery (waves, the grid, the
# decision) is tested on small mock samples with the judge reading six proposals per call.
CFG = copy.deepcopy(REGISTERED)
CFG["judging"]["batch_size"] = 6


def test_generation_runs_only_the_target_then_extends(tmp_path):
    alloc = stages.allocate(CFG, 6)                      # pre-drawn: 6 per structure
    orgs = stages.run_generation(CFG, PR, MockBackend(), tmp_path, "t", alloc, 4, 4, progress=QUIET)
    assert Counter(o["structure"] for o in orgs) == {"hierarchy": 4, "polyarchy": 4}
    assert len(stages.read_jsonl(tmp_path / "orgs.jsonl")) == 8      # positions beyond the target were not run
    orgs2 = stages.run_generation(CFG, PR, MockBackend(), tmp_path, "t", alloc, 4, 6, progress=QUIET)
    assert Counter(o["structure"] for o in orgs2) == {"hierarchy": 6, "polyarchy": 6}
    assert [o["org_id"] for o in orgs] == [o["org_id"] for o in orgs2 if o["org_id"] in {x["org_id"] for x in orgs}]


def test_waves_keep_first_wave_calls_and_ids(tmp_path):
    alloc = stages.allocate(CFG, 4)
    be = MockBackend()
    core = stages.run_generation(CFG, PR, be, tmp_path, "t", alloc, 4, 2, progress=QUIET)
    props1 = stages.proposals_of(core)
    votes1 = stages.run_evaluation(CFG, PR, be, tmp_path, "t", props1, 4, progress=QUIET)
    rows1 = stages.run_judge(CFG, PR, be, tmp_path, "t", "glimmer", props1, 4, progress=QUIET)
    calls_e1 = {json.loads(l)["call_id"] for l in open(tmp_path / "calls_evaluation.jsonl")}
    calls_j1 = {json.loads(l)["call_id"] for l in open(tmp_path / "calls_judge_glimmer.jsonl")}
    # extend: the first wave is named; the new organizations form wave 2
    allorgs = stages.run_generation(CFG, PR, be, tmp_path, "t", alloc, 4, 4, progress=QUIET)
    props = stages.proposals_of(allorgs)
    waves = [{p["proposal_id"] for p in props1}]
    n_before = be.calls
    votes = stages.run_evaluation(CFG, PR, be, tmp_path, "t", props, 4, progress=QUIET, waves=waves)
    rows = stages.run_judge(CFG, PR, be, tmp_path, "t", "glimmer", props, 4, progress=QUIET, waves=waves)
    calls_e = {json.loads(l)["call_id"] for l in open(tmp_path / "calls_evaluation.jsonl")}
    calls_j = {json.loads(l)["call_id"] for l in open(tmp_path / "calls_judge_glimmer.jsonl")}
    assert calls_e1 <= calls_e and calls_j1 <= calls_j                       # wave-1 calls untouched
    assert all(c.startswith("eval:w2:") for c in calls_e - calls_e1)
    assert all(c.startswith("judge:glimmer:w2:") for c in calls_j - calls_j1)
    n_new_props = len(props) - len(props1)
    expected_new = 4 * -(-n_new_props // CFG["evaluation"]["batch_size"]) + CFG["judging"]["readings"]["floor"] * -(-n_new_props // CFG["judging"]["batch_size"])
    assert be.calls - n_before == expected_new                                # only the new organizations were called
    # wave-1 votes and ratings are identical to the first run; blind ids of the two waves never collide
    v1 = {(v["proposal_id"], v["role"]): v["decision"] for v in votes1}
    assert all(v1[(v["proposal_id"], v["role"])] == v["decision"] for v in votes if (v["proposal_id"], v["role"]) in v1)
    r1 = {(r["proposal_id"], r["pass"]): r.get("originality") for r in rows1}
    assert all(r1[(r["proposal_id"], r["pass"])] == r.get("originality") for r in rows if (r["proposal_id"], r["pass"]) in r1)
    bl = {v["blind_id"]: v["proposal_id"] for v in votes}
    assert len(bl) == len(props) and len({v["proposal_id"] for v in votes}) == len(props)
    assert Counter(v["wave"] for v in votes) == {1: 4 * len(props1), 2: 4 * n_new_props}


def test_extension_decision_uses_pooled_quantities_only(tmp_path, monkeypatch):
    alloc = stages.allocate(CFG, 4)
    be = MockBackend()
    orgs = stages.run_generation(CFG, PR, be, tmp_path, "t", alloc, 4, 4, progress=QUIET)
    props = stages.proposals_of(orgs)
    votes = stages.run_evaluation(CFG, PR, be, tmp_path, "t", props, 4, progress=QUIET)
    rows = stages.run_judge(CFG, PR, be, tmp_path, "t", "glimmer", props, 4, progress=QUIET)
    import numpy as np
    from np_registered.schemas import JUDGE_SCALES
    rng = np.random.default_rng(2)
    for r in rows:                                    # mock levels that give both categories (the mock alone gives few quality)
        for s_ in JUDGE_SCALES:
            r[s_] = int(rng.integers(2, 5))
    data = Data(orgs, props, votes, rows)
    data.acc4 = np.random.default_rng(1).random(len(data.pids)) < 0.3     # a non-degenerate four-of-four pass rate
    seen = []

    def fake_power(n, pi, phi, p4, reps=4000, seed=61, rho_pass=0.0, p1=None, alpha=0.05, direction=-1):
        seen.append((n, pi, phi, p4, p1, alpha, direction))
        return {"power": 0.7 if n < 150 else 0.9, "power_h2": 0.7 if n < 150 else 0.9, "power_rule_comparison": 0.99}
    monkeypatch.setattr("np_registered.power.design_power", fake_power)
    chk = extension_check(CFG, data, 4)
    assert chk["target_per_structure"] == 150 and chk["adequately_powered_at_target"]
    assert chk["decision"].startswith("extend to 150")
    assert sorted({s[0] for s in seen}) == [4] + extension_candidates(CFG)
    assert all(s[5] == 0.05 for s in seen)                                 # alpha .05, no correction
    assert {s[6] for s in seen} == {-1, 1}                                  # quality simulated up, below down (H1's direction)
    assert extension_candidates(CFG) == list(range(86, 169, 2))          # steps of one allocation block (two per structure)
    assert "hierarchy" not in json.dumps(chk) and "polyarchy" not in json.dumps(chk)   # nothing by structure
    monkeypatch.setattr("np_registered.power.design_power", lambda *a, **k: {"power": 0.5, "power_h2": 0.5, "power_rule_comparison": 0.99})
    chk = extension_check(CFG, data, 4)
    assert chk["target_per_structure"] == 168 and not chk["adequately_powered_at_target"]
    assert "underpowered" in chk["decision"]
    # H1 (exact power of the two-sample t at d = .5) is part of the decision: with H2 always powered, the target is
    # the first candidate size at which H1 reaches .80
    from np_registered.power import power_two_sample
    monkeypatch.setattr("np_registered.power.design_power", lambda *a, **k: {"power": 0.95, "power_h2": 0.95, "power_rule_comparison": 0.95})
    n_h1 = next(n for n in [4] + extension_candidates(CFG) if power_two_sample(n, 0.5, 0.05) >= 0.80)
    assert extension_check(CFG, data, 4)["target_per_structure"] == n_h1 == 86
    assert extension_check(CFG, data, 100)["decision"] == "no extension"
    # one side of H2 short of .80 extends on its own
    monkeypatch.setattr("np_registered.power.design_power",
                        lambda n, *a, **k: {"power_h2": 0.5 if n < 120 else 0.9, "power_rule_comparison": 0.9})
    assert extension_check(CFG, data, 100)["target_per_structure"] == 120


def test_rho_pass_from_counts_and_correlated_passes_lower_power():
    from np_registered.power import design_power, rho_pass_from_counts
    import numpy as np
    rng = np.random.default_rng(3)
    w = rng.binomial(12, 0.3, 4000)
    indep = rho_pass_from_counts(w, rng.binomial(w, 0.25))
    assert abs(indep["psi"] - 1) < 0.08 and indep["rho_pass"] < 0.02
    p_org = rng.beta(0.25 * 4, 0.75 * 4, 4000)                       # intraclass correlation 1 / (1 + 4) = .2
    corr = rho_pass_from_counts(w, rng.binomial(w, p_org))
    assert 0.12 < corr["rho_pass"] < 0.28
    base = design_power(40, 0.2, 1.0, 0.4, reps=1500, seed=5, p1=0.5)["power_h2"]
    worse = design_power(40, 0.2, 1.0, 0.4, reps=1500, seed=5, p1=0.5, rho_pass=0.2)["power_h2"]
    assert worse < base


def test_extension_keeps_first_wave_replacements(tmp_path, monkeypatch):
    from np_registered.runner import Failed
    cfg, pr = load_config(), load_prompts()
    alloc = stages.allocate(cfg, 4)
    original = stages.run_org
    def run_org(org, *args, **kwargs):
        if org['org_id'] == 'org001':
            raise Failed('forced content failure')
        return original(org, *args, **kwargs)
    monkeypatch.setattr(stages, 'run_org', run_org)
    backend = MockBackend()
    core = stages.run_generation(cfg, pr, backend, tmp_path, 't', alloc, 2, 2, progress=lambda *_: None)
    core_ids = {o['org_id'] for o in core}
    (tmp_path / 'extension.json').write_text(json.dumps({'core_org_ids': sorted(core_ids), 'target_per_structure': 4}))
    extended = stages.run_generation(cfg, pr, backend, tmp_path, 't', alloc, 2, 4, progress=lambda *_: None)
    assert core_ids <= {o['org_id'] for o in extended}
    assert len(extended) == 8


def test_registered_internal_pilot_for_h2(tmp_path, monkeypatch):
    """One recalculation after the first 84 per structure, from pooled quantities, at alpha .05 (no
    correction): H1 has power .90 at 84 and never asks for more; the target is the smallest size on 84, 86, ..., 168
    (rounded up to a block) at which H2a and H2b reach .80; above 168 the sample is 168 and the short hypothesis is
    labeled underpowered, with its power, before any test."""
    assert extension_candidates(REGISTERED) == list(range(86, 169, 2))
    alloc = stages.allocate(REGISTERED, 4)
    be = MockBackend()
    orgs = stages.run_generation(REGISTERED, PR, be, tmp_path, "t", alloc, 4, 4, progress=QUIET)
    props = stages.proposals_of(orgs)
    votes = stages.run_evaluation(REGISTERED, PR, be, tmp_path, "t", props, 4, progress=QUIET)
    rows = stages.run_judge(REGISTERED, PR, be, tmp_path, "t", "glimmer", props, 4, progress=QUIET)
    import numpy as np
    from np_registered.schemas import JUDGE_SCALES
    rng = np.random.default_rng(2)
    for r in rows:
        for s_ in JUDGE_SCALES:
            r[s_] = int(rng.integers(2, 5))
    data = Data(orgs, props, votes, rows)
    data.acc4 = np.random.default_rng(1).random(len(data.pids)) < 0.3
    monkeypatch.setattr("np_registered.power.design_power", lambda *a, **k: {"power": 0.5, "power_h2": 0.5, "power_rule_comparison": 0.5})
    chk = extension_check(REGISTERED, data, 84)
    assert chk["alpha_per_test"] == 0.05 and abs(chk["power"]["84"]["H1"] - 0.90) < 0.01
    assert 0 < chk["pooled"]["quality"]["category_rate"] < 1
    assert chk["target_per_structure"] == 168 and not chk["adequately_powered_at_target"]
    assert "underpowered" in chk["decision"]
