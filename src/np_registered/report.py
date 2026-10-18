"""Readable summary of results/analysis_<judge>.json in the order of PROTOCOL.md section 7.
Presentation only: every number comes from the analysis file; nothing is recomputed here."""
from __future__ import annotations

import json
from pathlib import Path


def _f(x, k=3):
    return "n/a" if not isinstance(x, (int, float)) else f"{x:.{k}f}"


def _ci(c):
    if not isinstance(c, (list, tuple)) or len(c) != 2 or not all(isinstance(v, (int, float)) for v in c):
        return "n/a"
    return f"[{c[0]:.3f}, {c[1]:.3f}]"


def _limitations(test):
    flags = []
    if test.get("underpowered"):
        flags.append("UNDERPOWERED")
    if test.get("high_attrition"):
        flags.append("HIGH ATTRITION")
    if test.get("below_reliability_target"):
        flags.append("BELOW RELIABILITY TARGET: " + ", ".join(test["below_reliability_target"]))
    return " [" + "; ".join(flags) + "]" if flags else ""


def write_report(outdir: Path, judge: str = "glimmer", tag: str = "") -> Path:
    r = json.loads((outdir / "results" / f"analysis_{judge}{tag}.json").read_text())
    L = []
    if r.get("smoke_test_not_data"):
        L.append("> SMOKE TEST: NOT DATA. Do not interpret.\n")
    L.append(f"# Results: arm {r['arm_dir']}, categories from judge {judge}\n")
    L.append("## Sample and integrity\n")
    L.append(f"- Organizations: hierarchy {r['n_orgs']['hierarchy']}, polyarchy {r['n_orgs']['polyarchy']}; "
             f"proposals classified {r['n_proposals_classified']}, unscored {r['n_proposals_unscored']}, unclassified "
             f"{r.get('n_proposals_unclassified')}; organizations with fewer than 12 classified slots {r['orgs_with_fewer_than_12_classified']}; "
             f"proposals with one judge pass {r['proposals_with_one_judge_pass']}; missing votes {r['missing_votes']}.")
    rd = r.get("readings")
    if rd:
        L.append(f"- Readings by judge {judge} (PROTOCOL 4.4): {rd['decision']} (floor {rd['floor']}, ceiling {rd['ceiling']}, "
                 f"target {rd['target']}); single-reading ICC(1,1) {json.dumps({k: (round(v, 3) if v is not None else None) for k, v in rd['icc1_1'].items()})}"
                 + (f"; BELOW THE RELIABILITY TARGET on {', '.join(rd['below_target'])}: every category using it is reported as such."
                    if rd.get("below_target") else "."))
    cr = r["category_rates"]
    L.append(f"- Category rates (threshold {r.get('threshold')} on the 2-8 scale): quality {_f(cr['quality'])} (of which creative "
             f"{_f(cr['creative'])}), below the quality threshold {_f(cr['below'])}; novel {_f(cr['novel'])} (novel but below "
             f"{_f(cr.get('novel_below'))}). Share of proposals at the threshold: {json.dumps(r.get('share_at_threshold'))}.")
    L.append(f"- Approval rates of categorized proposals: {json.dumps(r['pass_rates'])}.")
    for side in ("quality", "below"):
        c = (r.get("power_check") or {}).get(side) or {}
        if "power_h2" in c:
            L.append(f"- Internal pilot, {side} (PROTOCOL 6.4, at alpha {_f(c.get('alpha'), 4)}): category rate {_f(c['pi'], 3)}, approval rates "
                     f"{_f(c['p1'], 3)} (one of four) and {_f(c['p4'], 3)} (four of four), dispersion phi {_f(c['phi_observed'], 2)} "
                     f"(used {_f(c['phi_used'], 2)}); simulated power of H2 at n = {c['n_per_structure']}: {_f(c['power_h2'], 3)}.")
        else:
            L.append(f"- Internal pilot, {side}: {c.get('error', 'not available')}.")
    L.append(f"- Dispersion of counts written over binomial (phi): {json.dumps(r.get('dispersion_phi_observed_over_binomial'))}; "
             f"correlation of novelty with relevance: {_f(r.get('corr_novelty_relevance_proposals'))}, with workability: "
             f"{_f(r.get('corr_novelty_workability_proposals'))}.\n")
    L.append("## Registered tests (hierarchy minus polyarchy; each at alpha .05, no correction)\n")
    L.append("| | estimate | 95% CI | d | p | verdict |\n|---|---|---|---|---|---|")
    x = r["H1"]
    L.append(f"| H1 below-threshold proportion generated (= 1 - quality proportion){_limitations(x)} | {_f(x['diff'])} | {_ci(x['ci95'])} | "
             f"{_f(x['d'],2)} | {_f(x['p'],4)} | {x.get('verdict')} |")
    for side, lab in (("H2a_quality", "H2a quality proposals approved per proposal, own rule"),
                      ("H2b_below", "H2b below-threshold proposals approved per proposal, own rule")):
        x = r["H2"][side]
        L.append(f"| {lab}{_limitations(x)} | {_f(x['diff'])} | {_ci(x['ci95'])} | {_f(x['d'],2)} | {_f(x['p'],4)} | {x.get('verdict')} |")
    if "equivalence_secondary" in r["H1"]:
        e = r["H1"]["equivalence_secondary"]
        L.append(f"\nH1 secondary equivalence (bound {_f(e['bound'])}): p = {_f(e['p'],4)}, equivalent = {e['equivalent']}.")
    for side in ("H2a_quality", "H2b_below"):
        x = r["H2"][side]
        L.append(f"- {side}: decomposition (reported) H2 difference {_f(x['h2_difference'])} = generation part "
                 f"{_f(x['generation_part'])} + rule part {_f(x['rule_part'])}; bootstrap 95% {json.dumps(x.get('bootstrap_ci95'))}; "
                 f"cells {json.dumps(x['cells_per_organization'])}.")
    rc = r.get("rule_comparison") or {}
    L.append("\n## Reported, not tested: the two rules on the same votes\n")
    L.append("| per organization, proportion approved under four of four minus under one of four | mean | 95% CI | bootstrap 95% | organizations |\n|---|---|---|---|---|")
    for side, lab in (("rule_comparison_quality", "quality proposals"), ("rule_comparison_below", "below-threshold proposals")):
        x = rc.get(side) or {}
        L.append(f"| {lab} | {_f(x.get('mean'))} | {_ci(x.get('ci95'))} | {_ci(x.get('bootstrap_ci95'))} | {x.get('n_organizations')} |")
    L.append(f"\nApproval rates by rule: {json.dumps(rc.get('rates'))}. {rc.get('note', '')}\n")
    att = (r.get("secondary", {}).get("attrition_and_fallbacks") or {}).get("attrition")
    if att:
        L.append(f"\nAttrition (PROTOCOL 8.3): overall {att['overall_pct']:.1f}%, differential "
                 f"{att['differential_pct_points']:.1f} points (cautious WWC bound {att['wwc_cautious_bound_pct_points']}); "
                 f"{'low' if att['low_attrition'] else 'HIGH'} attrition.")
    ab = r.get("attrition_bounds") or {}
    if ab and "H1" in ab:
        fr = ab.get("failure_rate", {})
        L.append("Failure rate by structure (Haldane estimator for sampling to a fixed number of completions): "
                 + ", ".join(f"{s} {_f((fr.get(s) or {}).get('haldane'))} (naive {_f((fr.get(s) or {}).get('naive'))})" for s in ("hierarchy", "polyarchy")) + ".")
        L.append("\n| Lee bounds on the structure contrast (trimming the group with more completions) | lower | upper | trimmed | share |\n|---|---|---|---|---|")
        for h in ("H1", "H2a", "H2b"):
            b = ab.get(h) or {}
            L.append(f"| {h} | {_f(b.get('lower'))} | {_f(b.get('upper'))} | {b.get('trimmed_group') or 'none'} | {_f(b.get('trim_share'))} |")
    at = (r.get("secondary", {}).get("attrition_and_fallbacks") or {}).get("attempts") or {}
    if isinstance(at, dict) and at:
        L.append("\n| Call log | attempts | content failures | rate | first-attempt failures | outcomes from a retry | exhausted |\n|---|---|---|---|---|---|---|")
        for name, a in at.items():
            if isinstance(a, dict) and "attempts_completed" in a:
                L.append(f"| {name} | {a['attempts_completed']} | {a['content_failures']} | {_f(a.get('content_failure_rate'))} | "
                         f"{a['first_attempt_failures']} of {a['first_attempts']} | {a['outcomes_from_a_retry']} | {a['exhausted_logical_calls']} |")
    L.append("\n## Secondary (PROTOCOL 7.4)\n")
    L.append("```json\n" + json.dumps(r.get("secondary", {}), indent=1) + "\n```")
    path = outdir / "results" / f"REPORT_{judge}{tag}.md"
    path.write_text("\n".join(L) + "\n")
    return path
