"""The readings rule (PROTOCOL.md 4.4): floor, one decision from the single-reading reliability pooled over all
proposals, ceiling with the below-target flag; and the item counts sent to the local server (schemas.with_count)."""
import json

import numpy as np

from np_registered import analysis as A
from np_registered.analysis import readings_check
from np_registered.config import load_config
from np_registered.schemas import GENERATION_SCHEMA, JUDGE_SCHEMA, with_count

CFG = load_config()
RC = CFG["judging"]["readings"]


def synth_ratings(n=400, k=4, rel=0.75, seed=0):
    """k readings of n proposals whose dimension sub-scales have a single-reading reliability of about `rel`
    (true score plus independent error, rounded to the 1-4 integer scales)."""
    rng = np.random.default_rng(seed)
    rows = []
    true = rng.normal(0, 1, (n, 8))
    sd_e = np.sqrt((1 - rel) / rel) if rel > 0 else 10.0
    keys = ["originality", "paradigm_relatedness", "acceptability", "implementability", "applicability", "effectiveness",
            "completeness", "implicational_explicitness"]
    for i in range(n):
        for p in range(1, k + 1):
            x = true[i] + rng.normal(0, sd_e, 8)
            vals = np.clip(np.round(2.5 + 1.2 * x), 1, 4).astype(int)
            vals[6:] = np.clip(vals[6:], 1, 3)
            rows.append({"proposal_id": f"org{i:03d}-r-1", "judge": "j", "pass": p, "batch": 1, "wave": 1,
                         "pros": "p", "cons": "c", **dict(zip(keys, map(int, vals)))})
    return rows


def test_rule_floor_ceiling_and_flag():
    hi = readings_check(CFG, synth_ratings(rel=0.85), "j")
    assert hi["readings"] == RC["floor"] and hi["below_target"] == [] and "the floor" in hi["decision"]
    mid = readings_check(CFG, synth_ratings(rel=0.45, seed=1), "j")
    assert RC["floor"] < mid["readings"] <= RC["ceiling"] and mid["below_target"] == []
    for d in RC["dimensions"]:
        r = mid["icc1_1"][d]
        assert abs(mid["reliability_of_mean_at_readings"][d] - mid["readings"] * r / (1 + (mid["readings"] - 1) * r)) < 1e-9
    lo = readings_check(CFG, synth_ratings(rel=0.15, seed=2), "j")
    assert lo["readings"] == RC["ceiling"] and set(lo["below_target"]) == set(RC["dimensions"])
    assert "below the reliability target" in lo["decision"]
    none = readings_check(CFG, synth_ratings(rel=0.0, seed=3), "j")
    assert none["readings"] == RC["ceiling"] and none["below_target"]


def test_rule_uses_only_the_floor_readings_and_nothing_by_structure():
    rows = synth_ratings(k=RC["floor"] + 2, rel=0.6)
    out = readings_check(CFG, rows, "j")
    out_floor = readings_check(CFG, [r for r in rows if r["pass"] <= RC["floor"]], "j")
    assert out["icc1_1"] == out_floor["icc1_1"] and out["readings"] == out_floor["readings"]
    assert out["n_proposals_rated_in_every_floor_reading"] == 400
    s = json.dumps(out)
    assert "hierarchy" not in s and "polyarchy" not in s and "org" not in s


def test_config_is_the_registered_rule():
    assert RC["floor"] == 4 and RC["ceiling"] == 8 == 2 * RC["floor"] and RC["target"] == 0.80
    assert RC["dimensions"] == ["novelty", "workability", "relevance"]
    assert all(f"judge_pass_{k}" in CFG["design"]["seeds"] for k in range(1, RC["ceiling"] + 1))
    assert CFG["design"]["extension"]["max_per_structure"] == 2 * CFG["design"]["orgs_per_structure"]   # internal pilot cap
    assert RC["step"] == 2                                                                         # 4, 6, or 8 readings


def test_with_count_fixes_the_list_length_and_changes_nothing_else():
    s = with_count(JUDGE_SCHEMA, "ratings", 6)
    assert s["properties"]["ratings"]["minItems"] == s["properties"]["ratings"]["maxItems"] == 6
    assert "minItems" not in JUDGE_SCHEMA["properties"]["ratings"]
    g = with_count(GENERATION_SCHEMA, "proposals", 3)
    assert g["properties"]["proposals"]["minItems"] == 3 and g["properties"]["stance"] == GENERATION_SCHEMA["properties"]["stance"]



def test_reliability_uses_each_dimensions_complete_readings():
    rows = synth_ratings(n=20, k=4, rel=.7)
    for r in rows:
        if r['pass'] == 1:
            r['originality'] = None
    result = A.pass_reliability(rows)
    assert result['passes'] == 4
    assert result['icc1_workability']['n'] == 20
    assert result.get('icc1_novelty') is None
    assert 'split_half_kappa_three_way' not in result


def test_readings_rule_uses_dimension_specific_complete_cases():
    rows = synth_ratings(n=20, k=4, rel=.7)
    expected = A.readings_check(load_config(), rows, 'j')
    for r in rows:
        if r['pass'] == 1:
            r['originality'] = None
    result = A.readings_check(load_config(), rows, 'j')
    assert result['icc1_1']['novelty'] is None
    assert result['icc1_1']['workability'] == expected['icc1_1']['workability']
