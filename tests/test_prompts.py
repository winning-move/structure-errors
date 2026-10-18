"""Prompt assembly: what each model reads, in what order, and that nothing else reaches it."""
import json

import pytest

from np_registered import prompts as P
from np_registered.config import load_config, load_prompts


def test_judge_prompt_is_dean_verbatim():
    """The judge reads the same Article 12 text as the evaluators, the stated problem with the decision frame, Dean's
    definitions of the three dimensions rated, and the anchors of the six subscales verbatim from Dean et al. (2006,
    Appendices A and B); no persona claim, no comparison instruction, and no specificity."""
    pr = load_prompts()
    plan = P.judge_plan(load_config(), "P1001", 1)
    built = P.judge_prompt_all(pr, [{"id": "P1001", "text": "x"}], plan)
    assert pr.policy in built and pr.judge_problem in built and "committing scarce implementation resources" in built
    assert "without regard for workability" in built                     # Dean Table 25, p. 690
    assert "common strategies that violate no norms" in built            # Dean Table 22, p. 687
    assert "totally unacceptable business practice" in built             # Dean Table 22, level 1
    assert "ingenious, imaginative, or surprising; may be humorous" in built   # Dean Table 21, level 4
    assert "Novelty: the degree to which an idea is original" in built  # Table 8 definitions
    assert "never compare" not in built and "taught a course" not in built
    assert "Specificity" not in built and "completeness" not in built and "NOT therefore less acceptable" not in built
    assert set(pr.judge_anchors) == {"originality", "paradigm_relatedness", "acceptability", "implementability",
                                     "applicability", "effectiveness"}
    assert "Executive-level" not in json.dumps(pr.roles) and "Pioneer" not in json.dumps(pr.roles)


def test_judge_check_per_subscale():
    from np_registered.schemas import Invalid, JUDGE_DIMENSIONS, check_subscales, judge_schema_for
    pair = JUDGE_DIMENSIONS["workability"]
    sch = judge_schema_for(pair)["properties"]["ratings"]["items"]
    assert sch["required"] == ["id", "acceptability_evidence", "acceptability", "implementability_evidence", "implementability"]
    ok = {"id": "P1", "acceptability_evidence": "e.", "acceptability": 4, "implementability_evidence": "e.", "implementability": 1}
    check_subscales(ok, pair)
    for bad in (dict(ok, acceptability=5), dict(ok, implementability_evidence=" "), {k: v for k, v in ok.items() if k != "acceptability"}):
        with pytest.raises(Invalid):
            check_subscales(bad, pair)
    assert list(JUDGE_DIMENSIONS) == ["novelty", "workability", "relevance"]


def test_generation_assembly_order():
    pr = load_prompts()
    poly = P.generation_prompt(pr, "director", None)
    assert poly == "\n\n".join([pr.roles["card"]["director"], pr.policy, pr.stance_task, pr.generation_task])
    seniors = [{"role": "compliance", "stance": 40, "reasoning": "Reason A."},
               {"role": "director", "stance": 55, "reasoning": "Reason B."}]
    hier = P.generation_prompt(pr, "researcher", seniors)
    assert "Compliance Officer (stance 40/100): Reason A.\n\nLab Director (stance 55/100): Reason B." in hier
    assert hier.index(pr.policy) < hier.index(pr.hierarchy_peer_intro) < hier.index(pr.stance_task)
    assert "Internal consultation reference" not in hier


def test_items_inlined_and_parseable():
    pr = load_prompts()
    items = [{"id": "P0003", "text": "A. b c d."}, {"id": "P0001", "text": 'He said "x".'}]
    one = items[1:]                                    # evaluators and the judge read one proposal per call
    built = P.evaluation_prompt(pr, "engineer", one)
    js = built[built.index("[\n"): built.rindex("]") + 1]
    assert json.loads(js) == one
    assert "The proposal to screen is listed below" in built and "{n}" not in built and "JSON file at" not in built
    built = P.judge_prompt_all(pr, one, P.judge_plan(load_config(), one[0]["id"], 1))
    js = built[built.index("[\n"): built.rindex("]") + 1]
    assert json.loads(js) == one
    assert "The proposal to rate is listed below" in built and "{n}" not in built and "JSON file at" not in built
