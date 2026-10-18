"""The registered analysis on synthetic data with known truth (Dean's three categories; H1, H2a, H2b, each at .05)."""
import math

import numpy as np
import pytest

from np_registered import analysis as A


def synth(n=84, shift=0.0, p_approve=(0.85, 0.85, 0.75, 0.45), seed=0, both_passes=True, quality_shift=0.0):
    """n orgs per structure, 12 proposals each. Hierarchy novelty sub-scales shifted by `shift` (on the latent scale)
    and its workability and relevance by `quality_shift` - planted generation effects. Votes depend on quality,
    not on origin. Scores centered so that the categories at threshold 6 are all populated."""
    rng = np.random.default_rng(seed)
    orgs, props, votes, ratings = [], [], [], []
    for s in ("hierarchy", "polyarchy"):
        for i in range(n):
            oid = f"{s[0]}{i:03d}"
            orgs.append({"org_id": oid, "structure": s})
            for j in range(12):
                pid = f"{oid}-{j}"
                props.append({"proposal_id": pid, "org_id": oid, "structure": s, "role": "r"})
                nov = rng.normal(0, 1) + (shift if s == "hierarchy" else 0)
                q = quality_shift if s == "hierarchy" else 0
                rel, wrk = rng.normal(0, 1) + q, rng.normal(0, 1) + q
                for pas in ((1, 2) if both_passes else (1,)):
                    def sc(lat, lo, hi):
                        return int(np.clip(np.round(3.0 + lat + rng.normal(0, .6)), lo, hi))
                    r = {"proposal_id": pid, "pass": pas,
                         "originality": sc(nov, 1, 4), "paradigm_relatedness": sc(nov, 1, 4),
                         "acceptability": sc(wrk, 1, 4), "implementability": sc(wrk, 1, 4),
                         "applicability": sc(rel, 1, 4), "effectiveness": sc(rel, 1, 4)}
                    ratings.append(r)
                qq = 0.6 * rel + 0.4 * wrk
                for role, base in zip("abcd", p_approve):
                    pr = 1 / (1 + math.exp(-(math.log(base / (1 - base)) + 0.8 * qq)))
                    votes.append({"proposal_id": pid, "role": role,
                                  "decision": "approve" if rng.random() < pr else "reject"})
    return orgs, props, votes, ratings


def test_categories_are_dean_exclusive_exhaustive_with_equality_passing():
    nov = np.array([6.0, 6.0, 5.75, 8.0, 2.0])
    wrk = np.array([6.0, 5.75, 7.0, 6.0, 8.0])
    rel = np.array([6.0, 7.0, 6.0, 5.999999999, 8.0])
    c = A.categories(nov, wrk, rel)
    assert c["quality"].tolist() == [True, False, True, True, True]     # 5.999999999 is within the tolerance of 6
    assert c["creative"].tolist() == [True, False, False, True, False]
    assert c["below"].tolist() == [False, True, False, False, False]
    assert c["novel"].tolist() == [True, True, False, True, False]
    assert np.all(c["creative"] <= c["quality"]) and np.all(c["below"] == ~c["quality"])
    # exclusive and exhaustive: creative + (quality and not creative) + below = 1 for every proposal
    assert np.all(c["creative"].astype(int) + (c["quality"] & ~c["creative"]).astype(int) + c["below"].astype(int) == 1)


def test_dim_scores_sum_subscales_and_skip_missing_subscales():
    rows = [{"proposal_id": "p", "pass": 1, "originality": 3, "paradigm_relatedness": 4, "acceptability": 2, "implementability": 2,
             "applicability": 4, "effectiveness": 4},
            {"proposal_id": "p", "pass": 2, "originality": 2, "paradigm_relatedness": 3, "acceptability": None, "implementability": 2,
             "applicability": 3, "effectiveness": 4}]
    sc = A.dim_scores(rows)["p"]
    assert sc["novelty"] == 6.0 and sc["workability"] == 4.0 and sc["relevance"] == 7.5 and "specificity" not in sc
    assert sc["n_passes"] == 2
    d = A.Data([{"org_id": "o", "structure": "hierarchy"}], [{"proposal_id": "p", "org_id": "o", "role": "r"},
                                                              {"proposal_id": "q", "org_id": "o", "role": "r"}],
               [], rows + [{"proposal_id": "q", "pass": 1, "originality": 3, "paradigm_relatedness": 3, "acceptability": None,
                            "implementability": None, "applicability": 3, "effectiveness": 3}])
    assert d.pids == ["p"] and d.n_unclassified == 1        # q has no workability rating: unclassified


def test_null_false_positive_rates():
    """No effect of structure on what is written: H1 and the secondary creative share reject at most at about alpha."""
    reps, hits = 300, {"H1": 0, "creative": 0}
    for s in range(reps):
        d = A.Data(*synth(n=40, shift=0.0, seed=1000 + s))
        res = A.run(d, seed=s, B=0, power_check=False)
        hits["H1"] += res["H1"]["p"] < .05
        hits["creative"] += res["secondary"]["creative_share"]["p"] < .05
    rates = {k: v / reps for k, v in hits.items()}
    # binomial SE at .05 with 300 reps is .0126: allow 3 SE
    assert rates["H1"] < .09 and rates["creative"] < .09, rates


def test_planted_effect_recovered():
    """Hierarchies writing more workable and relevant proposals (fewer below the threshold): H1 supported; a planted
    novelty shift shows in the secondary creative share."""
    d = A.Data(*synth(n=84, quality_shift=0.6, seed=3))
    res = A.run(d, seed=1, B=0, power_check=False)
    assert res["H1"]["verdict"] == "supported" and res["H1"]["diff"] < 0 and "p_adjusted" not in res["H1"]
    assert res["multiplicity"] == {"hypotheses": ["H1", "H2a_quality", "H2b_below"], "correction": "none", "alpha": 0.05}
    orgs, props, votes, ratings = synth(n=84, shift=-0.6, seed=3)
    d = A.Data(orgs, props, votes, ratings)
    res = A.run(d, seed=1, B=300)
    assert res["secondary"]["creative_share"]["diff"] < 0 and res["secondary"]["creative_share"]["p"] < .05
    h2 = res["H2"]["H2a_quality"]
    # identity: the H2 difference = generation part + rule part (equal n), and it equals the Welch estimate
    assert abs(h2["h2_difference"] - (h2["generation_part"] + h2["rule_part"])) < 1e-9
    assert abs(h2["h2_difference"] - h2["diff"]) < 1e-9
    lo, hi = h2["bootstrap_ci95"]["h2_difference"]
    assert lo < h2["h2_difference"] < hi
    # the rule comparison is reported with an interval and no p-value, and has the mechanical sign
    rc = res["rule_comparison"]
    for side in ("rule_comparison_quality", "rule_comparison_below"):
        assert rc[side]["mean"] <= 0 and "p" not in rc[side] and len(rc[side]["ci95"]) == 2 and len(rc[side]["bootstrap_ci95"]) == 2
    assert rc["rates"]["quality_approved_rule4"] <= rc["rates"]["quality_approved_rule1"]
    t = d.org_table()[0]
    for side, c in (("rule_comparison_quality", "quality"), ("rule_comparison_below", "below")):
        keep = t[f"{c}_voted"] > 0
        expect = ((t[f"{c}_acc4"][keep] - t[f"{c}_acc1"][keep]) / t[f"{c}_voted"][keep]).mean()
        x = rc[side]
        assert abs(x["mean"] - expect) < 1e-9 and x["n_organizations"] == int(keep.sum()) <= 2 * 84 and x["df"] == x["n_organizations"] - 1
    cr = res["category_rates"]
    assert abs(cr["creative"] + cr["quality_not_creative"] + cr["below"] - 1) < 1e-9 and cr["creative"] <= cr["quality"]


def test_quality_shift_moves_h1_and_h2():
    """Hierarchies writing less workable and relevant proposals: more below-threshold proposals (H1 reversal) and,
    under the stricter rule, fewer quality approvals per proposal (H2a supported)."""
    d = A.Data(*synth(n=84, quality_shift=-0.7, seed=5))
    res = A.run(d, seed=1, B=0, power_check=False)
    assert res["H1"]["diff"] > 0 and res["H1"]["verdict"] == "reversal"
    assert res["H2"]["H2a_quality"]["diff"] < 0 and res["H2"]["H2a_quality"]["verdict"] == "supported"


def test_paired_orgs_is_the_one_sample_t_of_organization_differences():
    """The rule comparison: the paired t over organizations equals the one-sample t of the per-organization
    differences; organizations without such a proposal are left out; the difference is never positive."""
    from np_registered.power import paired_orgs
    rng = np.random.default_rng(7)
    m = rng.integers(0, 6, 50)
    k1 = rng.binomial(m, 0.9)
    k4 = rng.binomial(k1, 0.4)
    r = paired_orgs(k4, k1, m)
    keep = m > 0
    o = A.one_sample((k4[keep] - k1[keep]) / m[keep])
    assert abs(r["mean"] - o["mean"]) < 1e-12 and abs(r["se"] - o["se"]) < 1e-12 and abs(r["p"] - o["p"]) < 1e-12
    assert r["df"] == int(keep.sum()) - 1 and r["n_organizations"] == int(keep.sum()) and r["n_proposals"] == int(m.sum())
    assert r["mean"] <= 0 and r["ci95"][0] <= r["mean"] <= r["ci95"][1]


def test_welch_matches_scipy():
    from scipy import stats
    rng = np.random.default_rng(2)
    a, b = rng.normal(0, 1, 30), rng.normal(.5, 2, 45)
    w = A.welch(a, b)
    s = stats.ttest_ind(a, b, equal_var=False)
    assert abs(w["t"] - s.statistic) < 1e-9 and abs(w["p"] - s.pvalue) < 1e-9


def test_degenerate_data_does_not_crash():
    """Tiny or degenerate samples (rank-deficient regressions) must still produce a full result file."""
    for n, shift in ((2, 0.0), (3, -5.0)):     # shift -5: hierarchies write (almost) no creative proposals
        d = A.Data(*synth(n=n, shift=shift, seed=9))
        res = A.run(d, seed=1, B=50, power_check=False)
        assert "rule_comparison" in res and "secondary" in res and "multiplicity" in res
        assert res["H1"]["verdict"] in ("supported", "reversal", "not supported")


def test_report_on_degenerate_result(tmp_path):
    """The readable report handles not-estimable quantities (None) without failing."""
    import json
    from np_registered.report import write_report
    d = A.Data(*synth(n=2, shift=-5.0, seed=9))
    res = A._clean({"arm_dir": "x", "judge": "glimmer", "smoke_test_not_data": True, **A.run(d, seed=1, B=50)})
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "analysis_glimmer.json").write_text(json.dumps(res))
    assert write_report(tmp_path, "glimmer").exists()


@pytest.mark.parametrize("seed", range(12))
def test_analysis_never_fails_on_random_designs(seed):
    """Fuzz: random sizes, effects, and evaluator strictness (including extreme ones) always give a result."""
    rng = np.random.default_rng(seed)
    n = int(rng.integers(2, 30))
    shift = float(rng.choice([-6.0, -1.0, 0.0, 1.0, 6.0]))
    strict = tuple(float(x) for x in rng.choice([0.02, 0.3, 0.7, 0.98], size=4))
    d = A.Data(*synth(n=n, shift=shift, p_approve=strict, seed=seed, both_passes=bool(seed % 2)))
    res = A.run(d, seed=seed, B=30, power_check=False)
    assert res["H1"]["verdict"] in ("supported", "reversal", "not supported")
    for side in ("H2a_quality", "H2b_below"):
        assert res["H2"][side]["verdict"] in ("supported", "reversal", "not supported")


def test_org_counts_dispersion_and_power_check():
    """The count generator hits the requested mean and dispersion above and below binomial, and the
    observed-quantity power check returns a power in [0, 1] that rises with the pass rate."""
    from np_registered.power import design_power, min_phi, org_counts
    rng = np.random.default_rng(3)
    for pi, phi in ((0.16, 1.0), (0.16, 0.85), (0.70, 0.70), (0.55, 1.5), (0.16, 1.3)):
        m = org_counts(rng, 200000, pi, phi)
        assert abs(m.mean() / 12 - pi) < 0.004
        assert abs(m.var() / (12 * pi * (1 - pi)) - phi) < 0.03, (pi, phi, m.var() / (12 * pi * (1 - pi)))
    assert 0 < min_phi(0.16) < 1
    with pytest.raises(ValueError):
        org_counts(rng, 10, 0.16, min_phi(0.16) - 0.05)
    lo = design_power(40, 0.16, 1.0, 0.03, reps=300, p1=0.10)
    hi = design_power(40, 0.16, 1.0, 0.30, reps=300, p1=0.95)
    assert 0 <= lo["power"] <= hi["power"] <= 1
    assert design_power(40, 0.16, 0.2, 0.3, reps=100, p1=0.9)["phi_used"] >= min_phi(0.16)
    # a stricter alpha lowers the simulated power
    assert design_power(84, 0.2, 1.0, 0.2, reps=400, p1=0.9, alpha=0.0125)["power_h2"] <= design_power(84, 0.2, 1.0, 0.2, reps=400, p1=0.9)["power_h2"] + 0.02


def test_h2_power_at_planning_values():
    """At 84 per structure, d = .5, approval rates .9 and .2: H1 near .90 at alpha .05; H2 well powered because the
    two rules differ."""
    from np_registered.power import power_two_sample, simulate_h2
    r = simulate_h2(84, 0.20, 0.5, 0.9, 0.2, phi=0.85, reps=800, seed=4)
    assert 0.80 < r["H1"] < 0.97 and r["H2"] > 0.95
    assert 0.74 < power_two_sample(84, 0.5, 0.05 / 4) < 0.80 and power_two_sample(92, 0.5, 0.05 / 4) >= 0.80 > power_two_sample(90, 0.5, 0.05 / 4)


def test_reliability_statistics():
    """ICC(1,1)/ICC(1,k), ICC(C,1)/ICC(A,1), Cohen's and Fleiss' kappa on known cases; split-half kappa runs."""
    rng = np.random.default_rng(11)
    true = rng.normal(0, 1, 400)
    Y = true[:, None] + rng.normal(0, 1, (400, 4))           # reliability of one reading = .5
    r = A.icc1(Y)
    assert abs(r["icc1_1"] - 0.5) < 0.07 and abs(r["icc1_k"] - 0.8) < 0.05
    shifted = np.c_[true, true + 1.0]                         # a constant offset: consistency 1, agreement < 1
    t = A.icc_two_way(shifted)
    assert abs(t["icc_c1"] - 1) < 1e-9 and t["icc_a1"] < 0.9
    assert A.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert abs(A.fleiss_kappa([[4, 0], [0, 4], [4, 0], [0, 4]]) - 1.0) < 1e-12
    orgs, props, votes, ratings = synth(n=20, seed=4)
    ratings4 = ratings + [dict(r, **{"pass": r["pass"] + 2}) for r in ratings]
    rel = A.pass_reliability(ratings4)
    assert rel["passes"] == 4 and rel["split_half_kappa_three_way"] is not None and "split_half_kappa_creative" in rel
    ja = A.judge_agreement(A.dim_scores(ratings), A.dim_scores(ratings4))
    assert ja["kappa_three_way"] == 1.0 and ja["agreement_three_way"] == 1.0
    ev = A.evaluator_agreement(votes, votes)
    assert ev["agreement_four_of_four"] == 1.0 and all(v == 1.0 for v in ev["kappa_by_role"].values() if v is not None)


def test_secondary_registered_analyses():
    """Thresholds 5 and 7 and continuous versions of every test, the novel count and four cells, the creative yield,
    the manipulation check, and the Imai mediation analysis run; at rho = 0 the sensitivity formula reproduces the
    ACME (Imai, Keele, and Yamamoto, 2010)."""
    d = A.Data(*synth(n=30, shift=-0.6, seed=5))
    t, thr, cats = d.org_table()
    cs = A.classification_sensitivity(d)
    assert set(cs["thresholds"]) == {"5.0", "7.0"}
    for thr_ in cs["thresholds"].values():
        assert set(thr_) >= {"H1", "creative_share", "H2a_quality", "H2b_below", "rule_comparison_quality", "category_rates"}
        assert thr_["rule_comparison_quality"]["mean"] <= 0 and "p" in thr_["H1"]
    assert cs["thresholds"]["5.0"]["category_rates"]["quality"] >= cs["thresholds"]["7.0"]["category_rates"]["quality"]
    assert cs["continuous"]["rule_comparison_quality_score"]["mean"] <= 0
    nc = A.novel_and_cells(d, t, cats)
    for s in ("hierarchy", "polyarchy"):
        cells = nc["cells_quality_by_novelty"][s]
        assert abs(sum(v for k, v in cells.items() if k != "n_proposals") - 1) < 1e-9
    assert nc["novel_share"]["diff"] < 0                      # the planted novelty shift shows in Dean's third count
    med = A.mediation_imai(d, t, sims=200)
    for side in ("H2a_quality", "H2b_below"):
        m = med[side]
        ni = m["no_interaction"]
        assert abs(ni["acme"] + ni["ade"] - ni["total"]) < 1e-9
        assert abs(m["acme_at_rho"]["0.0"] - ni["acme"]) < 1e-9
        assert abs(m["acme_hierarchy"] + m["ade_polyarchy"] - m["total"]) < 1e-9
        assert abs(m["acme_polyarchy"] + m["ade_hierarchy"] - m["total"]) < 1e-9
        assert len(m["acme_hierarchy_ci95"]) == 2
    sec = A.secondary(d, t, cats, None)
    assert "p" in sec["creative_yield_own_rule"] and "novel_and_cells" in sec
    ev = A.evaluator_role_agreement(synth(n=30, shift=-0.6, seed=5)[2])
    assert ev["n"] > 0 and 0 <= ev["share_disagree"] <= 1 and len(ev["kappa_by_pair"]) == 6


def test_proposal_length_secondary():
    d = A.Data(*synth(n=20, shift=-0.6, seed=5))
    t, thr, cats = d.org_table()
    pl = A.proposal_length(d, t)
    assert set(pl["corr_length_with_dimension"]) == set(A.DIMS)
    assert pl["words_per_proposal_mean"]["hierarchy"] is not None and "p" in pl["welch_mean_length"]   # synth texts are empty
    assert set(pl) >= {"H1_below_share_with_length_covariate", "creative_share_with_length_covariate", "words_by_structure"}
    r = pl["H1_below_share_with_length_covariate"]
    assert (r["p"] != r["p"]) or 0 <= r["p"] <= 1          # nan when the design is rank-deficient, else a p-value


def test_mediation_interaction_recovers_arm_specific_slopes():
    """With Y = M x p(T) + noise, the rule-specific slope differs by arm by construction; the interaction model
    recovers ACME = b2 x slope under each structure, which a common slope cannot (Imai, Keele, and Tingley, 2010)."""
    rng = np.random.default_rng(7)
    n = 400
    T = np.r_[np.ones(n), np.zeros(n)]
    M = 0.30 - 0.10 * T + rng.normal(0, 0.05, 2 * n)          # b2 = -0.10
    Y = M * np.where(T == 1, 0.2, 1.0) + rng.normal(0, 0.01, 2 * n)   # slope .2 (four of four) vs 1.0 (one of four)
    class D:
        X = T.astype(int)
    t = {"quality_share": M, "below_share": M, "quality_acc4": None, "quality_acc1": None, "below_acc4": None,
         "below_acc1": None, "voted": None}
    import np_registered.analysis as AA
    saved = AA.own_rule
    AA.own_rule = lambda X, k4, k1, voted: Y
    try:
        m = AA.mediation_imai(D(), t, sims=100)["H2a_quality"]
    finally:
        AA.own_rule = saved
    assert abs(m["acme_hierarchy"] - (-0.10 * 0.2)) < 0.01
    assert abs(m["acme_polyarchy"] - (-0.10 * 1.0)) < 0.02
    assert abs(m["interaction_slope_difference"] - (-0.8)) < 0.05


def test_wwc_attrition_classification():
    from np_registered.analysis import wwc_attrition
    a = wwc_attrition({"hierarchy": 13, "polyarchy": 13}, {"hierarchy": 168, "polyarchy": 168})
    assert abs(a["overall_pct"] - 100 * 26 / 362) < 1e-9 and a["differential_pct_points"] == 0 and a["low_attrition"]
    b = wwc_attrition({"hierarchy": 20, "polyarchy": 0}, {"hierarchy": 168, "polyarchy": 168})
    assert b["differential_pct_points"] > 10.5 and not b["low_attrition"]
    c = wwc_attrition({"hierarchy": 0, "polyarchy": 0}, {"hierarchy": 84, "polyarchy": 84})
    assert c["overall_pct"] == 0 and c["low_attrition"] and c["wwc_cautious_bound_pct_points"] == 5.7


# ----------------------------------------------------------------------------- edge cases
def _one_org_unscored(orgs, props, ratings):
    """Remove every rating of the first hierarchy organization: it has no classified proposal."""
    gone = {p["proposal_id"] for p in props if p["org_id"] == orgs[0]["org_id"]}
    return [r for r in ratings if r["proposal_id"] not in gone]


def test_organization_without_classified_proposal_does_not_void_h1():
    """An organization whose proposals are all unclassified has no share; it is left out of H1 (and reported), and
    H1 is still computed on the other organizations."""
    orgs, props, votes, ratings = synth(n=20, seed=21)
    d = A.Data(orgs, props, votes, _one_org_unscored(orgs, props, ratings))
    res = A.run(d, seed=1, B=20, power_check=False)
    assert res["orgs_without_classified_proposal"] == 1
    assert res["H1"]["n_hierarchy"] == 19 and res["H1"]["n_polyarchy"] == 20 and res["H1"]["p"] == res["H1"]["p"]
    assert res["H1"]["verdict"] in ("supported", "reversal", "not supported")


def test_absent_vote_record_makes_votes_incomplete():
    """A role with no vote record at all for a proposal (not only a vote that is None) leaves the proposal's votes
    incomplete: it counts under neither rule and is left out of the H2 denominator."""
    orgs, props, votes, ratings = synth(n=10, seed=22)
    pid = props[0]["proposal_id"]
    dropped = [v for v in votes if not (v["proposal_id"] == pid and v["role"] == "a")]
    d = A.Data(orgs, props, dropped, ratings)
    i = d.pids.index(pid)
    assert not d.voted[i] and not d.acc1[i] and not d.acc4[i] and d.n_missing_votes[i] == 1
    full = A.Data(orgs, props, votes, ratings)
    assert full.voted.sum() == d.voted.sum() + 1


def test_duplicate_votes_counted_once_and_conflicts_stop():
    orgs, props, votes, ratings = synth(n=10, seed=23)
    d0 = A.Data(orgs, props, votes, ratings)
    d1 = A.Data(orgs, props, votes + votes[:5], ratings)
    assert d1.n_duplicate_votes == 5 and (d1.n_approve == d0.n_approve).all() and (d1.acc4 == d0.acc4).all()
    flip = dict(votes[0], decision="reject" if votes[0]["decision"] == "approve" else "approve")
    with pytest.raises(ValueError, match="conflicting votes"):
        A.Data(orgs, props, votes + [flip], ratings)


def test_placebo_uses_the_first_role_of_the_order():
    """The placebo and the leakage baseline take the first role in the order of seniority from the organization
    records, whatever its name."""
    orgs, props, votes, ratings = synth(n=12, seed=24)
    names = ["lead", "b2", "c3", "d4"]
    for o in orgs:
        o["roles"] = [{"role": r, "stance": 50, "reasoning": "x"} for r in names]
    for k, p in enumerate(props):
        p["role"] = names[k % 4]
    votes = [dict(v, role=names["abcd".index(v["role"])]) for v in votes]
    d = A.Data(orgs, props, votes, ratings)
    assert d.roles == names
    t, _, cats = d.org_table()
    sec = A.secondary(d, t, cats, None)
    assert sec["placebo_first_role"]["role"] == "lead" and sec["placebo_first_role"]["below_share"]["n_hierarchy"] == 12


def test_no_correction_option():
    d = A.Data(*synth(n=30, quality_shift=0.4, seed=25))
    cfg = {"analysis": {"hypotheses": ["H1", "H2a", "H2b"], "correction": "none"}}
    res = A.run(d, seed=1, B=0, power_check=False, cfg=cfg)
    assert res["multiplicity"]["correction"] == "none" and A.alpha_per_test(cfg) == 0.05
    for corr in ("holm", "bonferroni"):
        with pytest.raises(ValueError):
            A.multiplicity({"analysis": {"correction": corr}})


def test_power_simulator_draws_quality_in_h1s_direction():
    """For quality proposals H1 predicts a higher rate in hierarchies: the simulator raises the hierarchy's quality
    rate (direction +1) and lowers its below-threshold rate (direction -1), by the same d."""
    from np_registered.power import hierarchy_rate_signed, simulate_h2
    lo, hi = hierarchy_rate_signed(0.8, 0.5, -1), hierarchy_rate_signed(0.2, 0.5, +1)
    assert lo < 0.8 and hi > 0.2 and abs((0.8 - lo) - (hi - 0.2)) < 1e-9
    up = simulate_h2(84, 0.8, 0.5, 0.9, 0.9, reps=50, seed=3, direction=+1)
    assert up["pi_hierarchy"] > 0.8 and up["direction"] == 1
    with pytest.raises(ValueError):
        hierarchy_rate_signed(0.5, 0.5, 0)


def test_bootstrap_retains_empty_organizations():
    orgs, props, votes, ratings = synth(n=2)
    gone = {p['proposal_id'] for p in props if p['org_id'] == orgs[-1]['org_id']}
    data = A.Data(orgs, props, votes, [r for r in ratings if r['proposal_id'] not in gone])
    result = A.bootstrap(data, B=20, seed=1)
    assert len(result['H2a_quality_h2_difference']['ci95']) == 2


def test_bootstrap_all_unclassified():
    orgs, props, votes, _ = synth(n=2)
    data = A.Data(orgs, props, votes, [])
    result = A.bootstrap(data, B=2, seed=1)
    assert np.isnan(result['H2a_quality_h2_difference']['ci95']).all()


def test_incomplete_votes_do_not_count_as_rejections(monkeypatch):
    from np_registered.config import load_config
    orgs, props, votes, ratings = synth(n=2)
    for r in ratings:
        for keys in A.DIMS.values():
            for key in keys[:2]:
                r[key] = 3
    for v in votes:
        v['decision'] = 'reject' if v['proposal_id'] == props[1]['proposal_id'] else 'approve'
    votes = votes[1:]
    data = A.Data(orgs, props, votes, ratings)
    monkeypatch.setattr(A, 'secondary', lambda *a, **k: {})
    result = A.run(data, seed=1, B=0, power_check=False)
    expected = 46 / 47
    assert result['pass_rates']['quality_rule1'] == expected
    assert result['pass_rates']['quality_rule4'] == expected
    assert result['pass_rates']['all_rule1'] == expected
    monkeypatch.setattr('np_registered.power.design_power', lambda *a, **k: {'power_h2': .9})
    check = A.extension_check(load_config(), data, 2)
    assert check['pooled']['quality']['approval_rate_one_of_four'] == expected
    assert check['pooled']['quality']['approval_rate_four_of_four'] == expected


def test_equivalence_follows_a_null_result_only(monkeypatch):
    """PROTOCOL.md 7.2: the equivalence test asks whether a non-significant H1 shows that no effect of interest exists.
    After a reversal (a significant effect in the opposite direction) that question does not arise."""
    monkeypatch.setattr(A, 'secondary', lambda *a, **k: {})
    rev = A.run(A.Data(*synth(n=30, quality_shift=-2, seed=5)), seed=1, B=0, power_check=False)
    assert rev['H1']['verdict'] == 'reversal' and 'equivalence_secondary' not in rev['H1']
    null = A.run(A.Data(*synth(n=30, seed=6)), seed=1, B=0, power_check=False)
    assert null['H1']['verdict'] == 'not supported' and 'equivalence_secondary' in null['H1']


def test_simulated_welch_matches_scipy_for_unequal_and_constant_samples():
    from scipy import stats
    from np_registered.power import _welch_pvalue, simulate_h2
    rng = np.random.default_rng(17)
    for a, b in ((rng.normal(size=9), rng.normal(.2, 2, 13)),
                 (np.ones(5), rng.normal(size=20)),
                 (np.ones(5), np.zeros(8)), (np.ones(5), np.ones(8))):
        expected = stats.ttest_ind(a, b, equal_var=False).pvalue
        assert _welch_pvalue(a, b) == pytest.approx(expected, nan_ok=True)
    # Retain the recorded fixed-seed simulation outcomes while avoiding repeated input processing.
    result = simulate_h2(84, .2, .5, .9, .2, reps=200, seed=7)
    assert (result['H1'], result['H2'], result['rule']) == (.89, 1., 1.)


def test_analysis_report_keeps_registered_limitations(monkeypatch, tmp_path):
    import json
    from np_registered.config import load_config
    from np_registered.report import write_report
    from np_registered.stages import _write_jsonl
    cfg = load_config()
    judge = cfg['judging']['primary']
    orgs, props, votes, ratings = synth(n=2)
    _write_jsonl(tmp_path / 'votes.jsonl', votes)
    _write_jsonl(tmp_path / f'ratings_{judge}.jsonl', ratings)
    _write_jsonl(tmp_path / 'org_failures.jsonl', [{'org_id': f'failed-{i}', 'structure': 'hierarchy'} for i in range(20)])
    decision = A.readings_check(cfg, ratings, judge)
    (tmp_path / f'readings_{judge}.json').write_text(json.dumps(decision))
    (tmp_path / 'extension.json').write_text(json.dumps({'check': {'underpowered_sides_at_target': ['H2b_below']}}))
    monkeypatch.setattr(A, 'secondary', lambda *a, **k: {})
    result = A.analyze(cfg, tmp_path, orgs, props, smoke=True, judge=judge, B=0, quiet=True)
    assert result['H2']['H2b_below']['underpowered']
    assert not result['H1']['underpowered']
    for test in [result['H1'], *result['H2'].values()]:
        assert test['high_attrition']
        assert set(test['below_reliability_target']) == {'workability', 'relevance'}
    report = write_report(tmp_path, judge).read_text()
    rows = [line for line in report.splitlines() if line.startswith(('| H1 below', '| H2a quality', '| H2b below'))]
    assert len(rows) == 3
    assert all('HIGH ATTRITION' in line and 'BELOW RELIABILITY TARGET' in line for line in rows)
    assert 'UNDERPOWERED' not in rows[0] and 'UNDERPOWERED' in rows[2]



@pytest.mark.parametrize('remove_all', [False, True])
def test_missing_classifications_do_not_discard_independent_secondary_results(remove_all):
    orgs, props, votes, ratings = synth(n=2)
    gone = {p['proposal_id'] for p in props if remove_all or p['structure'] == 'hierarchy'}
    data = A.Data(orgs, props, votes, [r for r in ratings if r['proposal_id'] not in gone])
    result = A.run(data, seed=1, B=0, power_check=False)
    assert 'creative_share' in result['secondary']
    assert 'classification_sensitivity' in result['secondary']
    assert 'leakage' in result['secondary']


def test_permutation_with_no_structure_contrast_is_not_significant():
    result = A.permutation_within_blocks(np.array([1, 1]), np.array([1, 1]), {'H1': [.2, .3]}, B=10)
    assert np.isnan(result['H1']['p_permutation'])


def test_power_simulation_is_centered_on_the_pooled_rate():
    """The observed category rate is pooled over both structures, so the simulated polyarchy and hierarchy rates average
    to it, d = .5 apart in H1's direction for the category."""
    from np_registered.power import centered_rates, design_power, hierarchy_rate_signed
    for pi, direction in ((0.2, -1), (0.8, +1), (0.5, -1)):
        pp, ph = centered_rates(pi, 0.5, direction)
        assert abs((pp + ph) / 2 - pi) < 1e-9 and abs(ph - hierarchy_rate_signed(pp, 0.5, direction)) < 1e-12
        assert (ph - pp) * direction > 0
    r = design_power(84, 0.2, 1.0, 0.2, reps=100, p1=0.9, direction=-1)
    assert abs((r["pi_polyarchy"] + r["pi_hierarchy"]) / 2 - 0.2) < 1e-9
