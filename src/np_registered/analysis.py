"""The registered analysis (PROTOCOL.md section 7). Written and frozen before any data exist.

Unit of analysis: the organization (n per structure). X = 1 for hierarchy, 0 for polyarchy.
All tests two-sided at alpha = .05; each hypothesis is tested and reported separately.

Categories (Dean, Hender, Rodgers, and Santanen, 2006, pp. 648-649, 675-677): dimension scores from the primary
judge on Dean's summed scale (each subscale 1-4, averaged over the judge's readings; dimension = sum of its two
subscales, 2-8; Table 11, p. 667), absolute thresholds at 6 with equality passing (noncompensatory, p. 676).
    quality  = workability >= 6 AND relevance >= 6         (Dean's quality idea)
    creative = quality AND novelty >= 6                     (Dean's creative idea: a quality idea that is also novel)
    below    = NOT quality (workability < 6 OR relevance < 6)   ("below the quality threshold")
    novel    = novelty >= 6, whatever the quality            (Dean's third count; secondary)
The three categories quality-but-not-creative, creative, below are exclusive and exhaustive among classified
proposals; a proposal with no rating on a subscale that a dimension needs is unclassified and left out of every test.
Evaluation: every proposal of the experiment is evaluated once, blind to its origin, by four evaluators (one per
role); both rules read the same four votes. Approved under the polyarchy rule (one of four) if at least one
evaluator approves; under the hierarchy rule (four of four) if all four approve. A proposal with a vote still
missing after the registered attempts is reported and left out of the approval counts (H2) only.
Omission error = a quality proposal not approved; commission error = a below-threshold proposal approved.

H1  below-threshold proportion generated (of the organization's classified proposals), hierarchy vs polyarchy: Welch
    t-test, predicted negative. Because every classified proposal is either a quality proposal or below the threshold,
    the quality share is 1 minus the below share: H1 is also the prediction that hierarchies generate a larger
    proportion of quality proposals (one test, not two). The creative proportion is a secondary analysis.
    Secondary, only if H1 is not supported: equivalence test (TOST) at +-0.5 pooled SD.
H2a/b (each structure's own proposals under its own rule): quality (below-threshold) proposals approved under the
    organization's own rule (four of four for a hierarchy, one of four for a polyarchy), divided by the number of
    its proposals with complete votes (twelve unless a vote is missing); Welch t-test, hierarchy minus polyarchy,
    predicted negative.
Multiplicity (config analysis.correction): "none": each hypothesis is tested and reported on its own at .05 (Rubin,
    2021).
Reported, not tested (the rule comparison; the two rules on the same votes): per organization, the proportion of its
    quality (below-threshold) proposals with complete votes approved under the hierarchy rule minus the proportion
    approved under the polyarchy rule; the mean over organizations with a 95% interval. Because four-of-four approvals
    are a subset of one-of-four approvals the difference is never positive; it is a benchmark, not a hypothesis.
Reported with H2 (not a test): the decomposition of the H2 difference into a generation part (the difference in
    approvals per proposal, averaged over the two rules) and a rule part (the mean over all organizations of the
    four-of-four minus one-of-four approvals per proposal), which add up exactly with equal numbers of organizations.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

from .power import paired_orgs
from .stages import read_jsonl

DIMS = {"novelty": ("originality", "paradigm_relatedness", 2, 8),
        "workability": ("acceptability", "implementability", 2, 8),
        "relevance": ("applicability", "effectiveness", 2, 8)}      # specificity is not rated
ALPHA = 0.05
THRESHOLD = 6.0                     # Dean et al. (2006) pp. 676-677: the recommended threshold on the 2-8 dimension
SENSITIVITY_THRESHOLDS = (5.0, 7.0)  # registered secondary (PROTOCOL.md 7.4)
LABEL_DIMS = ("novelty", "workability", "relevance")
_EPS = 1e-9                         # a mean of integers compared with an integer threshold; equality passes


# ----------------------------------------------------------------------------- measurement
def dim_scores(ratings: list[dict]) -> dict:
    """{proposal_id: {dim: mean over passes of (subscale A + subscale B) on Dean's 2-8 scale,
    'n_passes': k}} from judge rows. A row marked missing is skipped; a row in which a subscale is missing (None, a
    one-subscale call that failed) contributes nothing to that dimension; a dimension with no pass is absent."""
    acc: dict = {}
    for r in ratings:
        if r.get("missing"):
            continue
        d = acc.setdefault(r["proposal_id"], {k: [] for k in DIMS})
        for dim, (s1, s2, lo, hi) in DIMS.items():
            a, b = r.get(s1), r.get(s2)
            if a is not None and b is not None:
                d[dim].append(a + b)
    out = {}
    for pid, d in acc.items():
        sc = {k: float(np.mean(v)) for k, v in d.items() if v}
        sc["n_passes"] = max((len(v) for v in d.values()), default=0)
        out[pid] = sc
    return out


def categories(nov, wrk, rel, thr: float = THRESHOLD) -> dict:
    """Dean's categories on the summed scale (equality passes): quality, creative (a subset of quality), below (the
    complement of quality), novel (novelty at or above the threshold, whatever the quality)."""
    nov, wrk, rel = (np.asarray(x, float) for x in (nov, wrk, rel))
    quality = (wrk >= thr - _EPS) & (rel >= thr - _EPS)
    novel = nov >= thr - _EPS
    return {"quality": quality, "creative": quality & novel, "below": ~quality, "novel": novel}


HYPOTHESIS_KEYS = {"H1": "H1", "H2a": "H2a_quality", "H2b": "H2b_below"}   # config name -> key in the results


def multiplicity(cfg: dict | None) -> tuple[list[str], str]:
    """The registered hypotheses of an experiment (result keys) and the correction over them ("none"), from config
    analysis.hypotheses and analysis.correction."""
    a = (cfg or {}).get("analysis") or {}
    names = a.get("hypotheses", ["H1", "H2a", "H2b"])
    corr = a.get("correction", "none")
    if corr != "none":
        raise ValueError(f"analysis.correction must be 'none', not {corr!r}")
    return [HYPOTHESIS_KEYS[h] for h in names], corr


def alpha_per_test(cfg: dict | None) -> float:
    """The level every test is held to: alpha, with no correction (PROTOCOL.md 7.2)."""
    multiplicity(cfg)
    return ALPHA


# ----------------------------------------------------------------------------- data assembly
class Data:
    """Proposal-level arrays plus the organization index, so labels can be recomputed in resamples."""

    def __init__(self, orgs, props, votes, ratings, roles: list[str] | None = None):
        """roles: the evaluator roles, in the order of seniority (default: the role order of the organization records,
        which is the order of seniority; else every role found in the votes). A proposal's votes are complete only
        when every role has a decision (a vote that is None after the registered attempts, or a role with no vote
        record at all, makes them incomplete). Duplicate vote records of one proposal and role are counted once if
        they agree and stop the analysis if they disagree."""
        self.org_ids = [o["org_id"] for o in orgs]
        if roles is None:
            roles = [r["role"] for r in orgs[0]["roles"]] if orgs and orgs[0].get("roles") else \
                sorted({v["role"] for v in votes})
        self.roles = list(roles)
        self.X = np.array([1 if o["structure"] == "hierarchy" else 0 for o in orgs])
        oi = {o: i for i, o in enumerate(self.org_ids)}
        sc = dim_scores(ratings)
        # classified = every dimension the categories use has at least one reading (8.4); the rest are unclassified
        ok = {pid for pid, s in sc.items() if all(k in s for k in LABEL_DIMS)}
        self.n_unscored = sum(1 for p in props if p["proposal_id"] not in sc)
        self.n_unclassified = sum(1 for p in props if p["proposal_id"] not in ok)
        props = [p for p in props if p["proposal_id"] in ok]
        self.pids = [p["proposal_id"] for p in props]
        self.text = [p.get("text", "") for p in props]
        self.p_org = np.array([oi[p["org_id"]] for p in props], dtype=int)
        self.role = np.array([p["role"] for p in props])
        for k in DIMS:
            setattr(self, k, np.array([sc[p].get(k, np.nan) for p in self.pids], dtype=float))
        self.n_passes = np.array([sc[p]["n_passes"] for p in self.pids])
        dec: dict = {}
        self.n_duplicate_votes = 0
        for v in votes:
            key = (v["proposal_id"], v["role"])
            if key in dec:
                if dec[key] != v["decision"]:
                    raise ValueError(f"conflicting votes for proposal {key[0]} by {key[1]}: {dec[key]!r} and {v['decision']!r}")
                self.n_duplicate_votes += 1
                continue
            dec[key] = v["decision"]
        unknown = sorted({r for _, r in dec} - set(self.roles))
        if unknown:
            raise ValueError(f"votes by roles that are not evaluators of this study: {unknown}")
        self.n_approve = np.array([sum(dec.get((p, r)) == "approve" for r in self.roles) for p in self.pids])
        self.n_missing_votes = np.array([sum(dec.get((p, r)) is None for r in self.roles) for p in self.pids])
        self.voted = self.n_missing_votes == 0                               # complete votes (PROTOCOL.md 8.4)
        self.acc1 = (self.n_approve >= 1) & self.voted
        self.acc4 = (self.n_approve == len(self.roles)) & self.voted
        self.slots = np.bincount(self.p_org, minlength=len(self.org_ids))   # scored proposals per org (12 if complete)

    def org_table(self, prop_idx=None, org_idx=None, thr: float = THRESHOLD, n_org: int | None = None):
        """Organization-level outcomes for a (possibly resampled) set of organizations.
        prop_idx/org_idx: arrays mapping resampled proposals to new organization positions.
        Returns (t, thr, cats): per organization, for each category c in quality, creative, below, novel, the count
        `c`, the approvals under one of four `c_acc1` and four of four `c_acc4`, the count with complete votes
        `c_voted`, and the share `c_share` of the organization's classified proposals."""
        if prop_idx is None:
            prop_idx, new_org, n_org = np.arange(len(self.pids)), self.p_org, len(self.org_ids)
        else:
            prop_idx, new_org = prop_idx, org_idx
            if n_org is None:
                n_org = int(org_idx.max()) + 1 if len(org_idx) else 0
        cats = categories(self.novelty[prop_idx], self.workability[prop_idx], self.relevance[prop_idx], thr)
        a1, a4, v = self.acc1[prop_idx], self.acc4[prop_idx], self.voted[prop_idx]
        cnt = lambda m: np.bincount(new_org, weights=m.astype(float), minlength=n_org)
        t = {"slots": cnt(np.ones(len(prop_idx), bool)), "voted": cnt(v)}
        for c, lab in cats.items():
            t[c], t[f"{c}_acc1"], t[f"{c}_acc4"], t[f"{c}_voted"] = cnt(lab), cnt(lab & a1), cnt(lab & a4), cnt(lab & v)
            with np.errstate(invalid="ignore", divide="ignore"):
                t[f"{c}_share"] = t[c] / t["slots"]
        return t, thr, cats


# ----------------------------------------------------------------------------- tests
def welch(y1, y0) -> dict:
    """Hierarchy (y1) minus polyarchy (y0). An organization whose outcome is undefined (nan: no classified proposal,
    or no proposal with complete votes) contributes no observation; the n reported are the organizations used."""
    y1, y0 = np.asarray(y1, float), np.asarray(y0, float)
    y1, y0 = y1[~np.isnan(y1)], y0[~np.isnan(y0)]
    if len(y1) < 2 or len(y0) < 2:
        nan = float("nan")
        return {"mean_hierarchy": float(y1.mean()) if len(y1) else nan, "mean_polyarchy": float(y0.mean()) if len(y0) else nan,
                "diff": nan, "se": nan, "t": nan, "df": nan, "p": nan, "ci95": [nan, nan], "d": nan, "sd_pooled": nan,
                "n_hierarchy": len(y1), "n_polyarchy": len(y0)}
    n1, n0 = len(y1), len(y0)
    v1, v0 = y1.var(ddof=1), y0.var(ddof=1)
    diff = y1.mean() - y0.mean()
    se = math.sqrt(v1 / n1 + v0 / n0)
    df = (v1 / n1 + v0 / n0) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v0 / n0) ** 2 / (n0 - 1)) if se > 0 else float("nan")
    t = diff / se if se > 0 else float("nan")
    p = 2 * stats.t.sf(abs(t), df) if se > 0 else float("nan")
    q = stats.t.ppf(1 - ALPHA / 2, df) if se > 0 else float("nan")
    sp = math.sqrt(((n1 - 1) * v1 + (n0 - 1) * v0) / (n1 + n0 - 2))
    return {"mean_hierarchy": y1.mean(), "mean_polyarchy": y0.mean(), "diff": diff, "se": se, "t": t, "df": df,
            "p": p, "ci95": [diff - q * se, diff + q * se], "d": diff / sp if sp > 0 else float("nan"),
            "sd_pooled": sp, "n_hierarchy": n1, "n_polyarchy": n0}


def tost(y1, y0, bound_d=0.5) -> dict:
    """Equivalence at +-bound_d pooled SDs (Welch form): both one-sided tests at alpha."""
    w = welch(y1, y0)
    b = bound_d * w["sd_pooled"]
    if not w["se"] > 0:
        return {"bound": b, "p_lower": float("nan"), "p_upper": float("nan"), "p": float("nan"), "equivalent": False}
    p_lo = stats.t.sf((w["diff"] + b) / w["se"], w["df"])
    p_hi = stats.t.cdf((w["diff"] - b) / w["se"], w["df"])
    return {"bound": b, "bound_d": bound_d, "p_lower": p_lo, "p_upper": p_hi, "p": max(p_lo, p_hi),
            "equivalent": bool(max(p_lo, p_hi) < ALPHA)}


def ols_hc2(Xmat, y):
    """OLS with HC2 standard errors. A rank-deficient design (e.g., a count that is zero in every
    organization of one structure) is not estimable: every quantity is returned as nan, and the
    corresponding test is reported as not significant instead of stopping the analysis."""
    k = Xmat.shape[1]
    if np.linalg.matrix_rank(Xmat) < k:
        nan = np.full(k, np.nan)
        return nan, nan, nan, nan, len(y) - k, np.full(len(y), np.nan)
    XtX_inv = np.linalg.inv(Xmat.T @ Xmat)
    beta = XtX_inv @ Xmat.T @ y
    e = y - Xmat @ beta
    h = np.einsum("ij,jk,ik->i", Xmat, XtX_inv, Xmat)
    with np.errstate(invalid="ignore", divide="ignore"):
        meat = (Xmat * (e ** 2 / (1 - h))[:, None]).T @ Xmat
    V = XtX_inv @ meat @ XtX_inv
    with np.errstate(invalid="ignore", divide="ignore"):
        se = np.sqrt(np.diag(V))
        t = beta / se
    df = len(y) - Xmat.shape[1]
    p = 2 * stats.t.sf(np.abs(t), df)
    return beta, se, t, p, df, e


def verdict(est, p, predicted_sign=-1):
    if not p < ALPHA:
        return "not supported"
    return "supported" if np.sign(est) == predicted_sign else "reversal"


def one_sample(y) -> dict:
    """Mean of y against 0: two-sided one-sample t-test with a 95% interval."""
    y = np.asarray(y, float)
    n = len(y)
    m, sd = y.mean(), y.std(ddof=1) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    if not se > 0:
        return {"mean": m, "se": se, "t": float("nan"), "df": n - 1, "p": float("nan"), "ci95": [m, m], "n": n}
    t = m / se
    q = stats.t.ppf(1 - ALPHA / 2, n - 1)
    return {"mean": m, "se": se, "t": t, "df": n - 1, "p": 2 * stats.t.sf(abs(t), n - 1),
            "ci95": [m - q * se, m + q * se], "n": n}


def _org_diff_mean(k4, k1, m) -> float:
    """The rule comparison: the mean over organizations with at least one labeled proposal with complete votes of the
    proportion approved under four of four minus the proportion approved under one of four."""
    k4, k1, m = (np.asarray(x, float) for x in (k4, k1, m))
    keep = m > 0
    return float(((k4[keep] - k1[keep]) / m[keep]).mean()) if keep.any() else float("nan")


def own_rule(X, k4, k1, voted) -> np.ndarray:
    """Approved under the organization's own rule per proposal with complete votes (H2)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(X == 1, k4, k1) / np.where(voted > 0, voted, np.nan)


def gaps(X, k4, k1, voted) -> dict:
    """The H2 difference (hierarchy minus polyarchy, per proposal) and its decomposition: generation part (the
    difference averaged over the two rules) plus rule part (four of four minus one of four, mean over all
    organizations); exact with equal numbers of organizations."""
    H, P = X == 1, X == 0
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.where(voted > 0, voted, np.nan)
        a4, a1 = k4 / v, k1 / v
    own = np.where(H, a4, a1)
    total = np.nanmean(own[H]) - np.nanmean(own[P])
    gen = np.nanmean(((a4 + a1) / 2)[H]) - np.nanmean(((a4 + a1) / 2)[P])
    rule = np.nanmean(a4 - a1)
    return {"h2_difference": total, "generation_part": gen, "rule_part": rule}


H2_SIDES = {"H2a_quality": "quality", "H2b_below": "below"}      # the own-rule tests and their categories
H1_DIRECTION = {"quality": +1, "below": -1}   # the sign of hierarchy minus polyarchy in what is written, as H1 predicts it
RULE_SIDES = {"quality": "rule_comparison_quality", "below": "rule_comparison_below"}


def bootstrap(data: Data, B: int, seed: int) -> dict:
    """Percentile cluster bootstrap: resample organizations within structure (the categories use absolute thresholds,
    so nothing is recut). Intervals for the H2 decomposition and for the reported rule comparison."""
    rng = np.random.default_rng(seed)
    by_org = [np.where(data.p_org == i)[0] for i in range(len(data.org_ids))]
    idx_h, idx_p = np.where(data.X == 1)[0], np.where(data.X == 0)[0]
    keys = list(RULE_SIDES.values()) + [f"{s}_{q}" for s in H2_SIDES for q in ("h2_difference", "generation_part", "rule_part")]
    out = {k: [] for k in keys}
    for _ in range(B):
        orgs = np.r_[rng.choice(idx_h, len(idx_h)), rng.choice(idx_p, len(idx_p))]
        Xb = data.X[orgs]
        prop_idx = np.concatenate([by_org[o] for o in orgs])
        new_org = np.concatenate([np.full(len(by_org[o]), j) for j, o in enumerate(orgs)])
        t, _, _ = data.org_table(prop_idx, new_org, n_org=len(orgs))
        for c, name in RULE_SIDES.items():
            out[name].append(_org_diff_mean(t[f"{c}_acc4"], t[f"{c}_acc1"], t[f"{c}_voted"]))
        for side, c in H2_SIDES.items():
            for q, v in gaps(Xb, t[f"{c}_acc4"], t[f"{c}_acc1"], t["voted"]).items():
                out[f"{side}_{q}"].append(v)
    return {k: {"ci95": np.nanpercentile(v, [2.5, 97.5]).tolist(), "B": B} for k, v in out.items()}


# words that would let an evaluator or judge infer that a proposal came from a hierarchy chain
# (a junior quoting a senior). Fixed before data exist; case-insensitive, whole words.
LEAK_PATTERN = (r"\b(colleague|colleagues|stance|senior colleague|senior colleagues|"
                r"as the (compliance officer|lab director|director|researcher) "
                r"(noted|notes|argued|argues|said|says|suggested|suggests|proposed|proposes|emphasized|emphasizes|"
                r"stressed|stresses|recommended|recommends|pointed out|points out))\b")


def lpm_cluster(y, x, groups):
    """Proposal-level linear probability model y ~ 1 + x with organization-clustered (CR1) standard
    errors, t with G - 1 df."""
    X = np.c_[np.ones(len(y)), x]
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    G = len(np.unique(groups))
    meat = np.zeros((2, 2))
    for g in np.unique(groups):
        sg = X[groups == g].T @ e[groups == g]
        meat += np.outer(sg, sg)
    n, k = X.shape
    c = G / (G - 1) * (n - 1) / (n - k)
    V = c * XtX_inv @ meat @ XtX_inv
    se = math.sqrt(V[1, 1])
    t = beta[1] / se
    return {"diff": beta[1], "se": se, "t": t, "df": G - 1, "p": 2 * stats.t.sf(abs(t), G - 1)}


def secondary(data: "Data", t: dict, cats: dict, orgs: list[dict] | None, cfg: dict | None = None) -> dict:
    """Pre-specified secondary analyses (PROTOCOL.md 7.4). None of them is a registered test."""
    import re
    X, H, Pm = data.X, data.X == 1, data.X == 0
    creative, below = cats["creative"], cats["below"]
    out = {}
    xp = X[data.p_org]
    # randomization inference for H1: structure labels permuted within allocation blocks, which
    # does not assume that organizations are independent of one another through shared batches
    if orgs and all("block" in o for o in orgs):
        # a replacement carries the block of the organization it replaced (stages.needed_reserves); a record
        # without one (block 0, older data) falls into one of two pseudo-blocks
        blk = np.array([o["block"] if o.get("block") else -1 - (i % 2) for i, o in enumerate(orgs)])
        out["permutation_within_blocks"] = permutation_within_blocks(X, blk, {"H1_below_share": t["below_share"],
                                                                             "creative_share": t["creative_share"]})
    # the creative proportion generated (secondary)
    out["creative_share"] = welch(t["creative_share"][H], t["creative_share"][Pm])
    # proposal-level LPM for H1 and for the creative proportion
    out["lpm_cluster_H1"] = _safe(lpm_cluster, below.astype(float), xp, data.p_org)
    out["lpm_cluster_creative"] = _safe(lpm_cluster, creative.astype(float), xp, data.p_org)
    # Dean's third count and the four cells of quality by novelty (PROTOCOL.md 7.4)
    out["novel_and_cells"] = _safe(novel_and_cells, data, t, cats)
    # the creative yield: creative proposals approved under the own rule per proposal with complete votes
    own = own_rule(X, t["creative_acc4"], t["creative_acc1"], t["voted"])
    ok = ~np.isnan(own)
    out["creative_yield_own_rule"] = welch(own[H & ok], own[Pm & ok])
    # placebo: the first role in the order of seniority has no seniors, so its prompt is identical in both structures
    first = data.roles[0]
    comp = data.role == first
    cm = np.bincount(data.p_org[comp], weights=creative[comp].astype(float), minlength=len(X))
    cw = np.bincount(data.p_org[comp], weights=below[comp].astype(float), minlength=len(X))
    cs = np.bincount(data.p_org[comp], minlength=len(X)).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["placebo_first_role"] = {"role": first, "below_share": welch((cw / cs)[H], (cw / cs)[Pm]),
                                     "creative_share": welch((cm / cs)[H], (cm / cs)[Pm])}
    # leakage of structure cues into proposal texts
    leak = np.array([bool(re.search(LEAK_PATTERN, txt, re.I)) for txt in data.text], dtype=bool)
    junior = data.role != first
    out["leakage"] = {"pattern": LEAK_PATTERN, "n_flagged": int(leak.sum()),
                      "share_juniors_hierarchy": float(leak[(xp == 1) & junior].mean()) if ((xp == 1) & junior).any() else None,
                      "share_juniors_polyarchy": float(leak[(xp == 0) & junior].mean()) if ((xp == 0) & junior).any() else None,
                      # the first role never sees anyone: its rate is the false-positive baseline
                      "share_first_role": float(leak[~junior].mean()) if (~junior).any() else None}
    keep = ~leak
    if keep.any():
        km = np.bincount(data.p_org[keep], weights=creative[keep].astype(float), minlength=len(X))
        kw = np.bincount(data.p_org[keep], weights=below[keep].astype(float), minlength=len(X))
        ks = np.bincount(data.p_org[keep], minlength=len(X)).astype(float)
        ok = ks > 0
        with np.errstate(invalid="ignore", divide="ignore"):
            out["H1_without_flagged"] = welch((kw / ks)[H & ok], (kw / ks)[Pm & ok])
            out["creative_share_without_flagged"] = welch((km / ks)[H & ok], (km / ks)[Pm & ok])
    # overdispersion of the count approved given the count written (noise of evaluation in the power model)
    for side in ("quality", "below"):
        w, k = t[f"{side}_voted"], t[f"{side}_acc4"]
        p = k.sum() / w.sum() if w.sum() else float("nan")
        den = (w * p * (1 - p)).sum()
        out[f"dispersion_kept_given_written_{side}_rule4"] = float(((k - p * w) ** 2).sum() / den) if den > 0 else float("nan")
    # stance manipulation check: a junior's stance and the mean of its seniors' stances (hierarchy),
    # against the same quantity computed on the same-position roles of polyarchies (baseline)
    if orgs:
        rows = {"hierarchy": ([], []), "polyarchy": ([], [])}
        sd = {"hierarchy": [], "polyarchy": []}
        for o in orgs:
            st = [r["stance"] for r in o["roles"]]
            sd[o["structure"]].append(float(np.std(st, ddof=1)))
            for k in range(1, len(st)):
                rows[o["structure"]][0].append(st[k])
                rows[o["structure"]][1].append(float(np.mean(st[:k])))
        out["stance_check"] = {s: {"corr_junior_with_mean_senior": float(np.corrcoef(*rows[s])[0, 1]) if len(rows[s][0]) > 2 else None,
                                   "mean_within_org_sd": float(np.mean(sd[s])) if sd[s] else None}
                               for s in rows}
        if sd["hierarchy"] and sd["polyarchy"]:
            out["stance_within_org_sd_welch"] = welch(np.array(sd["hierarchy"]), np.array(sd["polyarchy"]))
        rl = {s: [len(r["reasoning"].split()) for o in orgs if o["structure"] == s for r in o["roles"]] for s in rows}
        out["reasoning_words_mean"] = {s: float(np.mean(v)) if v else None for s, v in rl.items()}
        out["manipulation_check"] = _safe(manipulation_check, orgs)
    out["proposal_length"] = _safe(proposal_length, data, t)
    out["classification_sensitivity"] = _safe(classification_sensitivity, data, cfg)
    out["mediation_imai"] = _safe(mediation_imai, data, t)
    return out


def proposal_length(data: "Data", t: dict) -> dict:
    """Registered secondary analysis (5) (PROTOCOL.md 7.4): the length of the proposals. Per proposal, the number of
    words of its text; per organization, the mean over its scored proposals. Reported: mean length by structure with a
    Welch t-test (hierarchy minus polyarchy); the Pearson correlation of proposal length with each judge dimension over
    proposals; and H1 (and the creative share) as OLS of the organization share on structure and mean length (HC2),
    because LLM judges are known to favor longer answers and the structures may write at different lengths."""
    words = np.array([len(txt.split()) for txt in data.text], dtype=float)
    n_org = len(data.org_ids)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_len = np.bincount(data.p_org, weights=words, minlength=n_org) / np.bincount(data.p_org, minlength=n_org)
    H, Pm = data.X == 1, data.X == 0
    out = {"words_per_proposal_mean": {"hierarchy": float(np.nanmean(mean_len[H])) if H.any() else None,
                                      "polyarchy": float(np.nanmean(mean_len[Pm])) if Pm.any() else None},
           "welch_mean_length": welch(mean_len[H & ~np.isnan(mean_len)], mean_len[Pm & ~np.isnan(mean_len)]),
           "corr_length_with_dimension": {}}
    for k in DIMS:
        y = getattr(data, k).astype(float)
        ok = ~np.isnan(y) & ~np.isnan(words)
        out["corr_length_with_dimension"][k] = float(np.corrcoef(words[ok], y[ok])[0, 1]) if ok.sum() > 2 and words[ok].std() > 0 and y[ok].std() > 0 else None
    for name, share in (("H1_below_share", t["below_share"]), ("creative_share", t["creative_share"])):
        share = np.asarray(share, dtype=float)
        ok = ~np.isnan(mean_len) & ~np.isnan(share)
        Xmat = np.c_[np.ones(ok.sum()), data.X[ok].astype(float), mean_len[ok]]
        beta, se, tval, pval, df, _ = ols_hc2(Xmat, share[ok])
        out[f"{name}_with_length_covariate"] = {"structure_coef": float(beta[1]), "se_hc2": float(se[1]),
                                                "t": float(tval[1]), "p": float(pval[1]), "length_coef": float(beta[2]), "df": int(df)}
    # the distribution of proposal length by structure (the 60-110 word request is logged, not enforced; G2)
    qs = [5, 25, 50, 75, 95]
    out["words_by_structure"] = {s: ({"n": int(m.sum()), "mean": float(words[m].mean()),
                                      "percentiles": dict(zip(map(str, qs), np.percentile(words[m], qs).tolist())),
                                      "share_in_60_to_110": float(((words[m] >= 60) & (words[m] <= 110)).mean())}
                                     if m.any() else None)
                                 for s, m in (("hierarchy", data.X[data.p_org] == 1), ("polyarchy", data.X[data.p_org] == 0))}
    return out


def novel_and_cells(data: "Data", t: dict, cats: dict) -> dict:
    """Dean's third count (Table 19, p. 675), reported as a secondary generation outcome: novel proposals (novelty at or
    above the threshold, whatever the quality), their proportion generated (Welch) and approvals under the own rule per
    proposal (Welch); and the four cells of quality by novelty, as shares of classified proposals by structure."""
    X, H, Pm = data.X, data.X == 1, data.X == 0
    own = own_rule(X, t["novel_acc4"], t["novel_acc1"], t["voted"])
    ok = ~np.isnan(own)
    q, nv = cats["quality"], cats["novel"]
    xp = X[data.p_org]
    cells = {}
    for s, m in (("hierarchy", xp == 1), ("polyarchy", xp == 0)):
        n = int(m.sum())
        cells[s] = {"creative (quality and novel)": float((q & nv & m).sum() / n) if n else None,
                    "quality, not novel": float((q & ~nv & m).sum() / n) if n else None,
                    "novel, below the quality threshold": float((~q & nv & m).sum() / n) if n else None,
                    "neither": float((~q & ~nv & m).sum() / n) if n else None, "n_proposals": n}
    return {"novel_share": welch(t["novel_share"][H], t["novel_share"][Pm]),
            "novel_approved_own_rule_per_proposal": welch(own[H & ok], own[Pm & ok]),
            "cells_quality_by_novelty": cells}


def manipulation_check(orgs: list[dict]) -> dict:
    """Registered manipulation check (PROTOCOL.md 7.4): per organization, the mean absolute distance between each
    junior's stance and the mean stance of the roles before it in the order of seniority; Welch t-test, hierarchy
    minus polyarchy, predicted negative (in hierarchies juniors read their seniors' stances; in polyarchies the same
    positions are filled independently)."""
    d = {"hierarchy": [], "polyarchy": []}
    for o in orgs:
        st = [r.get("stance") for r in o["roles"]]
        if any(x is None for x in st) or len(st) < 2:
            continue
        d[o["structure"]].append(float(np.mean([abs(st[k] - np.mean(st[:k])) for k in range(1, len(st))])))
    w = welch(np.array(d["hierarchy"]), np.array(d["polyarchy"]))
    w["verdict"] = verdict(w["diff"], w["p"], -1)
    return w


def _tests_for_categories(data: "Data", thr: float, cfg: dict | None = None) -> dict:
    """The registered tests (estimates and p-values, no bootstrap), the creative proportion, and the rule comparison
    for the categories at another threshold."""
    t, _, _ = data.org_table(thr=thr)
    X, H, P = data.X, data.X == 1, data.X == 0
    out = {"H1": welch(t["below_share"][H], t["below_share"][P]),
           "creative_share": welch(t["creative_share"][H], t["creative_share"][P])}
    for side, c in H2_SIDES.items():
        own = own_rule(X, t[f"{c}_acc4"], t[f"{c}_acc1"], t["voted"])
        out[side] = welch(own[H], own[P])
    for c, name in RULE_SIDES.items():
        out[name] = paired_orgs(t[f"{c}_acc4"], t[f"{c}_acc1"], t[f"{c}_voted"])
    out["category_rates"] = {c: float(np.asarray(v, float).mean()) for c, v in
                             categories(data.novelty, data.workability, data.relevance, thr).items()}
    return out


def classification_sensitivity(data: "Data", cfg: dict | None = None) -> dict:
    """Registered secondary analysis (PROTOCOL.md 7.4): every test with the thresholds moved to 5 and to 7 in place
    of 6, and with the continuous scores in place of the categories: the quality score of a proposal is
    min(workability, relevance) on the 2-8 scale and its novelty score is novelty itself; H1 on organization means of
    8 - min(workability, relevance) (the shortfall), the creative proportion on organization means of novelty, H2 on the
    score-weighted approvals under the own rule per proposal with complete votes (quality score for H2a, shortfall for
    H2b)."""
    out = {"thresholds": {str(thr): _tests_for_categories(data, thr, cfg) for thr in SENSITIVITY_THRESHOLDS}}
    X, H, P = data.X, data.X == 1, data.X == 0
    n = len(data.org_ids)
    cnt = lambda w: np.bincount(data.p_org, weights=np.asarray(w, float), minlength=n)
    slots, voted = cnt(np.ones(len(data.pids))), cnt(data.voted.astype(float))
    qscore = np.minimum(data.workability, data.relevance)
    cont = {}
    for tag, sc in (("H1_shortfall_score", 8.0 - qscore), ("creative_novelty_score", data.novelty)):
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_sc = cnt(sc) / slots
        cont[tag] = welch(mean_sc[H], mean_sc[P])
    for tag, sc in (("H2a_quality_score", qscore), ("H2b_shortfall_score", 8.0 - qscore)):
        k1, k4 = cnt(sc * data.acc1), cnt(sc * data.acc4)
        own = own_rule(X, k4, k1, voted)
        cont[tag] = welch(own[H], own[P])
    cont["rule_comparison_quality_score"] = one_sample(cnt(qscore * data.acc4) - cnt(qscore * data.acc1))
    out["continuous"] = cont
    return out


def mediation_imai(data: "Data", t: dict, sims: int = 2000, seed: int = 26100516) -> dict:
    """Registered secondary analysis (PROTOCOL.md 7.4): causal mediation in the framework of Imai, Keele, and Tingley
    (2010), with linear models at the organization level. Treatment T = hierarchy (1) or polyarchy (0); for H2a the
    mediator M is the proportion of quality proposals generated and the outcome Y the H2a outcome (quality proposals
    approved under the own rule per proposal with complete votes); for H2b, the proportion of proposals below the quality
    threshold generated and the H2b outcome. (The two mediators are one generated share used with opposite signs: the
    quality share is 1 minus the below share.) Models: M = a2 + b2 T + e2; Y = a3 + b3 T + g0 M + g1 T M + e3, with the
    treatment by mediator interaction (Imai, Keele, and Tingley, 2010, section on interactions): the rule set by the
    structure changes how many labeled proposals pass, so the slope of Y on M differs by arm by construction.
    ACME under hierarchy = b2 (g0 + g1), under polyarchy = b2 g0; ADE under hierarchy = b3 + g1 (a2 + b2), under
    polyarchy = b3 + g1 a2; total = b2 (g0 + g1) + b3 + g1 a2 (the same from either decomposition); 95% intervals
    from a nonparametric bootstrap of organizations within structure. The no-interaction ACME (b2 g with a common
    slope) is also reported, because the sensitivity analysis below is defined for that model. Sensitivity (Imai, Keele, and Yamamoto, 2010, Theorem 4): with rho the
    correlation between e2 and e3, ACME(rho) = b2 (s1 / s2) [rt - rho sqrt((1 - rt^2) / (1 - rho^2))], where s1 and s2
    are the residual SDs of Y = a1 + b1 T + e1 and of the mediator model and rt = corr(e1, e2); the ACME is zero at
    rho = rt, reported with ACME at rho = -.4, -.2, 0, .2, .4. Because the structure also sets the rule, the direct
    effect here includes the effect of the rule."""
    X = data.X.astype(float)
    rng = np.random.default_rng(seed)
    H, P = np.where(data.X == 1)[0], np.where(data.X == 0)[0]
    out = {}
    for tag, mkey, k4, k1 in (("H2a_quality", "quality_share", t["quality_acc4"], t["quality_acc1"]),
                              ("H2b_below", "below_share", t["below_acc4"], t["below_acc1"])):
        M, Y = t[mkey], own_rule(data.X, k4, k1, t["voted"])
        ok = ~np.isnan(Y) & ~np.isnan(M)

        def fit(idx):
            T_, M_, Y_ = X[idx], M[idx], Y[idx]
            A4 = np.c_[np.ones(len(idx)), T_, M_, T_ * M_]
            if len(idx) < 5 or np.linalg.matrix_rank(A4) < 4:       # a structure without variation in M: not identified
                nan = np.full(4, np.nan)
                return nan[:2], nan[:3], nan, nan[:2], np.full(len(idx), np.nan), np.full(len(idx), np.nan)
            A2 = np.c_[np.ones(len(idx)), T_]
            b_m = np.linalg.lstsq(A2, M_, rcond=None)[0]
            A3 = np.c_[np.ones(len(idx)), T_, M_]
            b_y = np.linalg.lstsq(A3, Y_, rcond=None)[0]
            b_i = np.linalg.lstsq(A4, Y_, rcond=None)[0]
            b_t = np.linalg.lstsq(A2, Y_, rcond=None)[0]
            return b_m, b_y, b_i, b_t, M_ - A2 @ b_m, Y_ - A2 @ b_t

        def effects(b_m, b_i):
            a2, b2 = b_m
            b3, g0, g1 = b_i[1], b_i[2], b_i[3]
            return {"acme_hierarchy": b2 * (g0 + g1), "acme_polyarchy": b2 * g0,
                    "ade_hierarchy": b3 + g1 * (a2 + b2), "ade_polyarchy": b3 + g1 * a2,
                    "total": b2 * (g0 + g1) + b3 + g1 * a2}
        idx = np.where(ok)[0]
        b_m, b_y, b_i, b_t, e2, e1 = fit(idx)
        est = effects(b_m, b_i)
        acme, ade = b_m[1] * b_y[2], b_y[1]           # the no-interaction model (sensitivity below)
        boot, boot_i = [], []
        for _ in range(sims):
            ii = np.r_[rng.choice(np.intersect1d(H, idx), len(np.intersect1d(H, idx))),
                       rng.choice(np.intersect1d(P, idx), len(np.intersect1d(P, idx)))]
            bm, by, bi, _, _, _ = fit(ii)
            boot.append((bm[1] * by[2], by[1]))
            boot_i.append(effects(bm, bi))
        boot = np.array(boot)
        s1, s2 = float(np.std(e1)), float(np.std(e2))
        rt = float(np.corrcoef(e1, e2)[0, 1]) if s1 > 0 and s2 > 0 else float("nan")
        acme_at = lambda r: float(b_m[1] * s1 / s2 * (rt - r * np.sqrt((1 - rt ** 2) / (1 - r ** 2)))) if s2 > 0 else float("nan")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # all-NaN bootstraps when not identified -> null
            ci_i = {k + "_ci95": np.nanpercentile([b[k] for b in boot_i], [2.5, 97.5]).tolist() for k in est}
            ci_a = np.nanpercentile(boot[:, 0], [2.5, 97.5]).tolist()
            ci_d = np.nanpercentile(boot[:, 1], [2.5, 97.5]).tolist()
        out[tag] = {**{k: float(v) for k, v in est.items()}, **ci_i,
                    "interaction_slope_difference": float(b_i[3]),
                    "no_interaction": {"acme": float(acme), "ade": float(ade), "total": float(acme + ade),
                                       "acme_ci95": ci_a, "ade_ci95": ci_d},
                    "sensitivity_rho_at_zero_acme": rt,
                    "acme_at_rho": {str(r): acme_at(r) for r in (-0.4, -0.2, 0.0, 0.2, 0.4)}}
    return out


def permutation_within_blocks(X, blocks, outcomes: dict, B: int = 10000, seed: int = 26100507) -> dict:
    """Two-sided permutation p-values of the difference in means (hierarchy minus polyarchy), structure labels
    shuffled within allocation blocks (reserves form their own pseudo-blocks). Registered secondary (7.4)."""
    rng = np.random.default_rng(seed)
    X = np.asarray(X)
    idx = [np.where(blocks == b)[0] for b in np.unique(blocks)]
    out = {}
    for name, y in outcomes.items():
        y = np.asarray(y, float)
        if np.isnan(y).any():                    # an organization without an outcome is left out, with its block
            keep = ~np.isnan(y)
            out[name] = permutation_within_blocks(X[keep], np.asarray(blocks)[keep], {name: y[keep]}, B, seed)[name]
            out[name]["n_excluded"] = int((~keep).sum())
            continue
        if not (X == 1).any() or not (X == 0).any():
            out[name] = {"diff": float("nan"), "p_permutation": float("nan"), "B": 0}
            continue
        obs = y[X == 1].mean() - y[X == 0].mean()
        hits = 0
        for _ in range(B):
            Xp = X.copy()
            for ix in idx:
                Xp[ix] = rng.permutation(X[ix])
            hits += abs(y[Xp == 1].mean() - y[Xp == 0].mean()) >= abs(obs) - 1e-12
        out[name] = {"diff": float(obs), "p_permutation": (hits + 1) / (B + 1), "B": B}
    return out


# What Works Clearinghouse Standards Handbook, Version 4.1, Table II.1: the highest differential attrition (percentage
# points) at which a sample keeps low attrition, by overall attrition (percent), under the cautious assumptions
# (expected bias at most 0.05 SD). Overall attrition above 57% has no low-attrition region.
WWC_CAUTIOUS = [5.7, 5.8, 5.9, 5.9, 6.0, 6.1, 6.2, 6.3, 6.3, 6.3, 6.3, 6.2, 6.2, 6.1, 6.0, 5.9, 5.9, 5.8, 5.7, 5.5,
                5.4, 5.3, 5.2, 5.1, 4.9, 4.8, 4.7, 4.5, 4.4, 4.3, 4.1, 4.0, 3.8, 3.6, 3.5, 3.3, 3.2, 3.1, 2.9, 2.8,
                2.6, 2.5, 2.3, 2.1, 2.0, 1.8, 1.6, 1.5, 1.3, 1.2, 1.0, 0.9, 0.7, 0.6, 0.4, 0.3, 0.2, 0.0]


def wwc_attrition(failed: dict, completed: dict) -> dict:
    """Overall and differential attrition of the randomized organizations (a failed organization is attrition; its
    replacement is not counted as randomized), classified against the WWC cautious boundary (PROTOCOL.md 8.3)."""
    rate = {s: failed[s] / max(1, failed[s] + completed[s]) for s in completed}
    tot_f, tot_n = sum(failed.values()), sum(failed.values()) + sum(completed.values())
    overall = 100 * tot_f / max(1, tot_n)
    differential = 100 * abs(rate["hierarchy"] - rate["polyarchy"])
    k = int(overall)
    bound = WWC_CAUTIOUS[k] if k < len(WWC_CAUTIOUS) else None
    return {"overall_pct": overall, "differential_pct_points": differential,
            "rate_by_structure_pct": {s: 100 * r for s, r in rate.items()},
            "wwc_cautious_bound_pct_points": bound,
            "low_attrition": bool(bound is not None and differential <= bound)}


def haldane_failure_rate(completed: int, failed: int) -> dict:
    """The failure rate when the run continues until a fixed number of completed organizations (inverse
    sampling): the naive failed / run is biased; Haldane (1945, Biometrika 33, 222-225) shows that
    (m - 1) / (n - 1) is unbiased for the success rate when counting stops at the m-th success among n."""
    n = completed + failed
    naive = failed / n if n else float("nan")
    unbiased = 1 - (completed - 1) / (n - 1) if n > 1 and completed >= 1 else float("nan")
    return {"completed": completed, "failed": failed, "run": n, "naive": naive, "haldane": unbiased}


def lee_bounds(y1, y0, s1: float, s0: float) -> dict:
    """Trimming bounds on E[Y1] - E[Y0] when outcomes are observed only for completed organizations and the
    completion rates s1 (hierarchy) and s0 (polyarchy) differ (Lee, 2009, Review of Economic Studies 76,
    1071-1102). The group with the higher completion rate is trimmed by p = (s_hi - s_lo) / s_hi from the top
    and from the bottom of its outcome distribution; the two trimmed means give the bounds. With equal rates
    both bounds equal the difference in means. Assumes monotone selection (a structure can only add completions)."""
    y1, y0 = np.sort(np.asarray(y1, float)), np.sort(np.asarray(y0, float))
    y1, y0 = y1[~np.isnan(y1)], y0[~np.isnan(y0)]
    if not len(y1) or not len(y0) or not (s1 > 0 and s0 > 0):
        return {"lower": float("nan"), "upper": float("nan"), "trim_share": float("nan"), "trimmed_group": None}
    diff = float(y1.mean() - y0.mean())
    if abs(s1 - s0) < 1e-12:
        return {"lower": diff, "upper": diff, "trim_share": 0.0, "trimmed_group": None, "n_trimmed": 0}
    hi, lo = ("hierarchy", "polyarchy") if s1 > s0 else ("polyarchy", "hierarchy")
    p = (max(s1, s0) - min(s1, s0)) / max(s1, s0)
    y_hi = y1 if hi == "hierarchy" else y0
    k = int(round(p * len(y_hi)))
    k = min(k, len(y_hi) - 1)
    top_trimmed = y_hi[: len(y_hi) - k].mean()      # the largest k removed: the smallest mean the group can have
    bottom_trimmed = y_hi[k:].mean()                  # the smallest k removed: the largest mean
    if hi == "hierarchy":
        lower, upper = top_trimmed - y0.mean(), bottom_trimmed - y0.mean()
    else:
        lower, upper = y1.mean() - bottom_trimmed, y1.mean() - top_trimmed
    return {"lower": float(lower), "upper": float(upper), "trim_share": float(p), "trimmed_group": hi,
            "n_trimmed": int(k), "difference_in_means": diff}


def attrition_bounds(data: "Data", t: dict, failed: dict) -> dict:
    """Lee bounds for the registered contrasts by structure (H1, H2a, H2b), from the completion rates by structure;
    reported with every analysis (PROTOCOL.md 8.3). The rule comparison compares rules within organizations and has
    no structure contrast to bound."""
    X = data.X
    H, Pm = X == 1, X == 0
    comp = {"hierarchy": int(H.sum()), "polyarchy": int(Pm.sum())}
    s = {k: comp[k] / (comp[k] + failed.get(k, 0)) if comp[k] + failed.get(k, 0) else float("nan") for k in comp}
    out = {"completion_rate": s, "failure_rate": {k: haldane_failure_rate(comp[k], failed.get(k, 0)) for k in comp}}
    out["H1"] = lee_bounds(t["below_share"][H], t["below_share"][Pm], s["hierarchy"], s["polyarchy"])
    for h, c in (("H2a", "quality"), ("H2b", "below")):
        own = own_rule(X, t[f"{c}_acc4"], t[f"{c}_acc1"], t["voted"])
        out[h] = lee_bounds(own[H], own[Pm], s["hierarchy"], s["polyarchy"])
    return out


def attrition_and_fallbacks(outdir: Path, orgs, props, votes_file: str, judge: str) -> dict:
    """Reported with every analysis (PROTOCOL.md 8.3, 8.4): organizations that failed and were replaced, by structure,
    with Fisher's exact test; proposals measured in the one-at-a-time fallback mode, by structure."""
    out = {}
    fails = read_jsonl(outdir / "org_failures.jsonl")
    n = {s: sum(1 for o in orgs if o["structure"] == s) for s in ("hierarchy", "polyarchy")}
    f = {s: sum(1 for x in fails if x.get("structure") == s) for s in n}
    out["failed_organizations"] = f
    if sum(f.values()):
        out["fisher_failures_p"] = float(stats.fisher_exact([[f["hierarchy"], n["hierarchy"]], [f["polyarchy"], n["polyarchy"]]])[1])
    out["attrition"] = wwc_attrition(f, n)
    out["failure_rate_haldane"] = {s: haldane_failure_rate(n[s], f[s]) for s in n}
    from .manifest import attempts_report
    out["attempts"] = _safe(attempts_report, outdir, write_audit=True)
    st = {p["proposal_id"]: p["structure"] for p in props}
    for stage, log in (("evaluation", votes_file.replace("votes", "calls_evaluation")), ("judge", f"calls_judge_{judge}.jsonl")):
        recs = read_jsonl(outdir / log)
        single = set()
        for r in recs:
            m = r.get("meta") or r
            if m.get("fallback_single") and r.get("valid"):
                single.update(m.get("blind_ids") or [])
        votes = read_jsonl(outdir / votes_file) if stage == "evaluation" else read_jsonl(outdir / f"ratings_{judge}.jsonl")
        bid2pid = {v["blind_id"]: v["proposal_id"] for v in votes if "blind_id" in v}
        cnt = {"hierarchy": 0, "polyarchy": 0}
        for b in single:
            s_ = st.get(bid2pid.get(b))
            if s_:
                cnt[s_] += 1
        out[f"single_mode_proposals_{stage}"] = cnt
    return out


def _scores_by_pass(ratings: list[dict]) -> dict:
    per = {}
    for r in ratings:
        if not r.get("missing"):
            per.setdefault(r["proposal_id"], {})[r["pass"]] = r
    return per


def _dim(r, dim):
    """The dimension score of one reading on Dean's summed scale; nan when a subscale is missing."""
    s1, s2, lo, hi = DIMS[dim]
    a, b = r.get(s1), r.get(s2)
    return float("nan") if a is None or b is None else float(a + b)


def _complete(r) -> bool:
    return all(r.get(k) is not None for d in LABEL_DIMS for k in DIMS[d][:2])


def icc1(Y) -> dict:
    """One-way random-effects ICC (Shrout and Fleiss, 1979, case 1) from an n x k matrix whose columns are
    interchangeable repeated readings: ICC(1,1) for one reading and ICC(1,k) for the mean of k."""
    Y = np.asarray(Y, float)
    n, k = Y.shape
    msb = k * ((Y.mean(1) - Y.mean()) ** 2).sum() / (n - 1)
    msw = ((Y - Y.mean(1, keepdims=True)) ** 2).sum() / (n * (k - 1))
    d1 = msb + (k - 1) * msw
    return {"icc1_1": float((msb - msw) / d1) if d1 > 0 else None,
            "icc1_k": float((msb - msw) / msb) if msb > 0 else None, "n": n, "k": k}


def icc_two_way(Y) -> dict:
    """McGraw and Wong (1996), two-way model, single measures: ICC(C,1) consistency and ICC(A,1) absolute
    agreement, from an n x k matrix whose columns are fixed raters (here k = 2 judges)."""
    Y = np.asarray(Y, float)
    n, k = Y.shape
    gm = Y.mean()
    msr = k * ((Y.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((Y.mean(0) - gm) ** 2).sum() / (k - 1)
    mse = ((Y - Y.mean(1, keepdims=True) - Y.mean(0, keepdims=True) + gm) ** 2).sum() / ((n - 1) * (k - 1))
    dc = msr + (k - 1) * mse
    da = msr + (k - 1) * mse + k * (msc - mse) / n
    return {"icc_c1": float((msr - mse) / dc) if dc > 0 else None,
            "icc_a1": float((msr - mse) / da) if da > 0 else None, "n": n}


def cohen_kappa(a, b) -> float | None:
    a, b = np.asarray(a), np.asarray(b)
    if len(a) == 0:
        return None
    cats = np.union1d(a, b)
    po = float((a == b).mean())
    pe = float(sum((a == c).mean() * (b == c).mean() for c in cats))
    return (po - pe) / (1 - pe) if pe < 1 else None


def fleiss_kappa(M) -> float | None:
    """Fleiss' kappa from an n x c matrix of category counts per item (each row sums to the number of raters)."""
    M = np.asarray(M, float)
    n, m = M.shape[0], M[0].sum() if len(M) else 0
    if n == 0 or m < 2:
        return None
    pj = M.sum(0) / (n * m)
    Pi = ((M ** 2).sum(1) - m) / (m * (m - 1))
    Pe = (pj ** 2).sum()
    return float((Pi.mean() - Pe) / (1 - Pe)) if Pe < 1 else None


def _category_codes(scores: dict, pids: list[str]) -> dict:
    """Category arrays from pass-averaged scores: the three-way code (0 below, 1 quality not creative, 2 creative) and
    the two binary labels the tests use."""
    nov, wrk, rel = (np.array([scores[p][k] for p in pids]) for k in LABEL_DIMS)
    c = categories(nov, wrk, rel)
    return {"three_way": np.where(c["creative"], 2, np.where(c["quality"], 1, 0)), "creative": c["creative"], "below": c["below"]}


def pass_reliability(ratings: list[dict]) -> dict:
    """Agreement of a judge with itself (reported, not tested), per dimension, on proposals rated in every pass:
    ICC(1,1) and ICC(1,K), one-way random effects, readings as interchangeable repeats (Shrout and Fleiss, 1979,
    case 1); Pearson r between readings 1 and 2; and the split-half agreement of the categories: categories from
    the mean of readings 1-2 and, separately, of readings 3-4, Cohen's kappa between the two halves (three-way,
    creative, below)."""
    per = _scores_by_pass(ratings)
    k = max((r["pass"] for r in ratings), default=0)
    full = {p: v for p, v in per.items() if all(j in v and _complete(v[j]) for j in range(1, k + 1))}
    out = {"passes": k, "n_all_passes": len(full)}
    both = [v for v in per.values() if 1 in v and 2 in v]
    for dim in DIMS:
        a = np.array([_dim(v[1], dim) for v in both])
        b = np.array([_dim(v[2], dim) for v in both])
        okd = ~np.isnan(a) & ~np.isnan(b)
        a, b = a[okd], b[okd]
        out[f"r12_{dim}"] = float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 and a.std() > 0 and b.std() > 0 else None
        complete_dim = [v for v in per.values() if all(j in v for j in range(1, k + 1))]
        if k >= 2 and len(complete_dim) > 2:
            Y = np.array([[_dim(v[j], dim) for j in range(1, k + 1)] for v in complete_dim])
            Y = Y[~np.isnan(Y).any(1)]
            out[f"icc1_{dim}"] = icc1(Y) if len(Y) > 2 else None
    halves_full = {p: v for p, v in per.items() if all(j in v and _complete(v[j]) for j in range(1, 5))}
    if k >= 4 and len(halves_full) > 2:
        pids = sorted(halves_full)
        halves = []
        for js in ((1, 2), (3, 4)):
            sc = {p: {d: float(np.mean([_dim(halves_full[p][j], d) for j in js])) for d in LABEL_DIMS} for p in pids}
            halves.append(_category_codes(sc, pids))
        for key in ("three_way", "creative", "below"):
            out[f"split_half_kappa_{key}"] = cohen_kappa(halves[0][key], halves[1][key])
    return out


def judge_agreement(scores_a: dict, scores_b: dict, rel_a: dict | None = None, rel_b: dict | None = None) -> dict:
    """Agreement of two judges (reported, not tested), per dimension, on each judge's pass-averaged scores for
    proposals both scored: Pearson r, ICC(C,1) and ICC(A,1) (McGraw and Wong, 1996; two judges as fixed raters),
    and the disattenuated correlation r / sqrt(ICC_a(1,K) x ICC_b(1,K)) from each judge's own reliability;
    Cohen's kappa of the three-way category and of the creative and below labels, each judge's categories from its own
    scores."""
    common = sorted(set(scores_a) & set(scores_b))
    out = {"n": len(common)}
    if len(common) <= 2:
        return out
    for k in DIMS:
        pk = [p for p in common if k in scores_a[p] and k in scores_b[p]]
        if len(pk) <= 2:
            continue
        a = np.array([scores_a[p][k] for p in pk])
        b = np.array([scores_b[p][k] for p in pk])
        r = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else None
        out[f"r_{k}"] = r
        out[f"icc_{k}"] = icc_two_way(np.c_[a, b])
        ra = ((rel_a or {}).get(f"icc1_{k}") or {}).get("icc1_k")
        rb = ((rel_b or {}).get(f"icc1_{k}") or {}).get("icc1_k")
        out[f"r_disattenuated_{k}"] = r / math.sqrt(ra * rb) if r is not None and ra and rb and ra > 0 and rb > 0 else None
    common_c = [p for p in common if all(k in scores_a[p] and k in scores_b[p] for k in LABEL_DIMS)]
    if len(common_c) > 2:
        la, lb = _category_codes(scores_a, common_c), _category_codes(scores_b, common_c)
        for key in ("three_way", "creative", "below"):
            out[f"kappa_{key}"] = cohen_kappa(la[key], lb[key])
        out["agreement_three_way"] = float((la["three_way"] == lb["three_way"]).mean())
    return out


def evaluator_agreement(votes_a: list[dict], votes_b: list[dict]) -> dict:
    """Agreement of evaluation (reported, not tested): per role, Cohen's kappa between two evaluator models' votes on
    the same proposals (cross-evaluation); agreement of the two models' rule decisions (one of four, four of four);
    and, for each model, Fleiss' kappa among its four roles (not expected to be high: the roles are meant to differ)."""
    def table(votes):
        t = {}
        for v in votes:
            if v.get("decision") is None:      # a missing vote is not a reject
                continue
            t.setdefault(v["proposal_id"], {})[v["role"]] = 1 if v["decision"] == "approve" else 0
        return t
    ta, tb = table(votes_a), table(votes_b)
    common = sorted(set(ta) & set(tb))
    roles = sorted({r for p in common for r in ta[p]})
    out = {"n": len(common), "kappa_by_role": {}}
    for r in roles:
        ps = [p for p in common if r in ta[p] and r in tb[p]]
        out["kappa_by_role"][r] = cohen_kappa([ta[p][r] for p in ps], [tb[p][r] for p in ps])
    for name, need in (("one_of_four", 1), ("four_of_four", 4)):
        da = np.array([sum(ta[p].values()) >= need for p in common])
        db = np.array([sum(tb[p].values()) >= need for p in common])
        out[f"agreement_{name}"] = float((da == db).mean()) if len(common) else None
        out[f"kappa_{name}"] = cohen_kappa(da, db)
    for name, t in (("a", ta), ("b", tb)):
        M = [[sum(t[p].values()), len(t[p]) - sum(t[p].values())] for p in t if len(t[p]) == 4]
        out[f"fleiss_kappa_roles_{name}"] = fleiss_kappa(M)
    return out


def evaluator_role_agreement(votes: list[dict]) -> dict:
    """Agreement among the four evaluator roles on the registered votes (reported, not tested; PROTOCOL.md 7.3):
    Fleiss' kappa among the roles, Cohen's kappa for every pair of roles, and the share of proposals on which the
    roles disagree (the quantity that gives H2 its power). The roles are meant to differ, so high agreement is
    not expected."""
    t = {}
    for v in votes:
        if v.get("decision") is None:          # a vote still missing after the registered attempts (8.1): not a reject
            continue
        t.setdefault(v["proposal_id"], {})[v["role"]] = 1 if v["decision"] == "approve" else 0
    full = {p: r for p, r in t.items() if len(r) == 4}
    roles = sorted({r for p in full.values() for r in p})
    out = {"n": len(full), "fleiss_kappa_roles": fleiss_kappa([[sum(r.values()), 4 - sum(r.values())] for r in full.values()]),
           "share_disagree": float(np.mean([0 < sum(r.values()) < 4 for r in full.values()])) if full else None,
           "kappa_by_pair": {}}
    for i, a in enumerate(roles):
        for b in roles[i + 1:]:
            out["kappa_by_pair"][f"{a}-{b}"] = cohen_kappa([full[p][a] for p in full], [full[p][b] for p in full])
    return out


def _safe(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except Exception as e:  # noqa: BLE001 - reported, never fatal
        return {"error": f"{type(e).__name__}: {e}"}


def _rate(num, den):
    d = den.sum()
    return num.sum() / d if d else float("nan")


# ----------------------------------------------------------------------------- driver
def run(data: Data, seed: int, B: int = 10000, orgs: list[dict] | None = None, power_check: bool = True,
        failed: dict | None = None, cfg: dict | None = None) -> dict:
    """failed: failed organizations by structure (org_failures.jsonl); when given, Lee bounds and the Haldane
    failure rate are reported next to the confirmatory tests (PROTOCOL.md 8.3). cfg: the study configuration (the
    registered hypotheses and their correction, analysis.hypotheses and analysis.correction; default H1, H2a, H2b
    with no correction, as registered)."""
    fam, corr = multiplicity(cfg)
    t, thr, cats = data.org_table()
    X = data.X
    H, Pm = X == 1, X == 0
    quality, creative, below, novel = cats["quality"], cats["creative"], cats["below"], cats["novel"]
    res = {"n_orgs": {"hierarchy": int(H.sum()), "polyarchy": int(Pm.sum())},
           "n_proposals_classified": len(data.pids), "n_proposals_unscored": data.n_unscored,
           "n_proposals_unclassified": data.n_unclassified,
           "orgs_with_fewer_than_12_classified": int((data.slots < 12).sum()),
           "orgs_without_classified_proposal": int((data.slots == 0).sum()),
           "duplicate_vote_records": data.n_duplicate_votes,
           "proposals_with_one_judge_pass": int((data.n_passes < 2).sum()),
           "proposals_with_fewer_than_all_passes": int((data.n_passes < data.n_passes.max()).sum()) if len(data.n_passes) else 0,
           "missing_votes": int(data.n_missing_votes.sum()), "threshold": thr,
           "category_rates": {"quality": float(quality.mean()), "creative": float(creative.mean()),
                              "quality_not_creative": float((quality & ~creative).mean()), "below": float(below.mean()),
                              "novel": float(novel.mean()), "novel_below": float((novel & below).mean())},
           "pass_rates": {"quality_rule4": _rate(quality & data.acc4, quality & data.voted), "quality_rule1": _rate(quality & data.acc1, quality & data.voted),
                          "creative_rule4": _rate(creative & data.acc4, creative & data.voted), "creative_rule1": _rate(creative & data.acc1, creative & data.voted),
                          "below_rule4": _rate(below & data.acc4, below & data.voted), "below_rule1": _rate(below & data.acc1, below & data.voted),
                          "all_rule4": _rate(data.acc4, data.voted), "all_rule1": _rate(data.acc1, data.voted)}}
    # the share of classified proposals sitting exactly at the threshold and within half a point of it (ties; 7.1)
    res["share_at_threshold"] = {}
    for k in LABEL_DIMS:
        v = getattr(data, k)
        res["share_at_threshold"][k] = {"exactly": float((np.abs(v - thr) < _EPS).mean()),
                                        "within_half_point": float((np.abs(v - thr) <= 0.5 + _EPS).mean())}
    res["dimension_means"] = {k: {"hierarchy": float(np.nanmean(getattr(data, k)[X[data.p_org] == 1])) if H.any() else None,
                                  "polyarchy": float(np.nanmean(getattr(data, k)[X[data.p_org] == 0])) if Pm.any() else None}
                              for k in DIMS}
    # descriptives that check the planning assumptions of the sample size (PROTOCOL.md 6.3)
    disp = {}
    for side in ("quality", "creative", "below"):
        cnt = t[side]
        for s, m in (("hierarchy", H), ("polyarchy", Pm)):
            k = t["slots"][m].mean()
            pi = cnt[m].sum() / t["slots"][m].sum()
            vb = k * pi * (1 - pi)
            disp[f"{side}_{s}"] = float(cnt[m].var(ddof=1) / vb) if vb > 0 else float("nan")
    res["dispersion_phi_observed_over_binomial"] = disp
    res["corr_novelty_relevance_proposals"] = float(np.corrcoef(data.novelty, data.relevance)[0, 1])
    res["corr_novelty_workability_proposals"] = float(np.corrcoef(data.novelty, data.workability)[0, 1])
    # the power of H2 at the final size (PROTOCOL.md 6.4), reported: the design simulation of H2 at the observed pooled
    # category rate, dispersion of the counts written, approval rates under both rules, and dependence of approvals
    # within organizations, at the observed n per structure, in H1's direction for the category, at alpha .05
    from .power import design_power, rho_pass_from_counts
    n_obs = int(min(H.sum(), Pm.sum()))
    a_test = alpha_per_test(cfg)
    res["power_check"] = {}
    for side in ([] if not power_check else H2_SIDES.values()):
        phis = [disp[f"{side}_hierarchy"], disp[f"{side}_polyarchy"]]
        phi_obs = float(np.nanmean(phis)) if not all(np.isnan(phis)) else 1.0
        pi_obs = res["category_rates"][side]
        p1, p4 = res["pass_rates"][f"{side}_rule1"], res["pass_rates"][f"{side}_rule4"]
        w, k1, k4 = t[f"{side}_voted"], t[f"{side}_acc1"], t[f"{side}_acc4"]
        rho = max(rho_pass_from_counts(w, k1)["rho_pass"], rho_pass_from_counts(w, k4)["rho_pass"])
        if n_obs >= 4 and 0 < pi_obs < 1 and p1 == p1 and p4 == p4 and 0 < p1 <= 1 and 0 <= p4 < 1:
            res["power_check"][side] = _safe(design_power, n_obs, pi_obs, phi_obs, p4, rho_pass=rho, p1=p1, alpha=a_test,
                                             direction=H1_DIRECTION[side])
        else:
            res["power_check"][side] = {"error": "not computable (degenerate rates or too few organizations)"}
    # H1: the proportion of proposals below the quality threshold generated (= 1 - the quality proportion)
    res["H1"] = welch(t["below_share"][H], t["below_share"][Pm])
    # H2a, H2b: each structure's own proposals under its own rule, per proposal with complete votes
    res["H2"] = {}
    for side, c in H2_SIDES.items():
        k4, k1 = t[f"{c}_acc4"], t[f"{c}_acc1"]
        own = own_rule(X, k4, k1, t["voted"])
        w = welch(own[H], own[Pm])
        w.update(gaps(X, k4, k1, t["voted"]))
        w["cells_per_organization"] = {"hierarchy_rule4": k4[H].mean(), "hierarchy_rule1": k1[H].mean(),
                                       "polyarchy_rule4": k4[Pm].mean(), "polyarchy_rule1": k1[Pm].mean()}
        res["H2"][side] = w
    # each registered hypothesis on its own at alpha .05 (PROTOCOL.md 7.2)
    tests = {"H1": res["H1"], **res["H2"]}
    res["multiplicity"] = {"hypotheses": fam, "correction": corr, "alpha": ALPHA}
    for k in fam:
        tests[k]["verdict"] = verdict(tests[k]["diff"], tests[k]["p"], -1)
    if res["H1"].get("verdict") == "not supported":     # a null result only; a reversal is a significant effect (7.2)
        res["H1"]["equivalence_secondary"] = tost(t["below_share"][H], t["below_share"][Pm], 0.5)
    # Reported, not tested: the two rules on the same votes, per organization (PROTOCOL.md 7.3)
    res["rule_comparison"] = {}
    for c, name in RULE_SIDES.items():
        o = paired_orgs(t[f"{c}_acc4"], t[f"{c}_acc1"], t[f"{c}_voted"])
        o.pop("p", None); o.pop("t", None)          # a benchmark with an interval, not a test
        res["rule_comparison"][name] = o
    res["rule_comparison"]["rates"] = {f"{c}_approved_rule{r}": _rate(cats[c] & (data.acc4 if r == 4 else data.acc1), cats[c] & data.voted)
                                       for c in ("quality", "creative", "below") for r in (4, 1)}
    res["rule_comparison"]["note"] = ("per organization, the proportion of its quality (below-threshold) proposals with complete votes "
                                      "approved under four of four minus the proportion approved under one of four, mean over "
                                      "organizations with a 95% interval; both rules read the same four votes, so the difference "
                                      "is never positive: a benchmark, not a hypothesis")
    if failed is not None:
        res["attrition_bounds"] = _safe(attrition_bounds, data, t, failed)
    try:
        res["secondary"] = secondary(data, t, cats, orgs, cfg)
    except Exception as e:  # noqa: BLE001 - a secondary analysis must never block the registered tests
        res["secondary"] = {"error": f"{type(e).__name__}: {e}"}
    # bootstrap intervals
    if B:
        bs = bootstrap(data, B, seed)
        for c, name in RULE_SIDES.items():
            res["rule_comparison"][name]["bootstrap_ci95"] = bs[name]["ci95"]
        for side in H2_SIDES:
            res["H2"][side]["bootstrap_ci95"] = {q: bs[f"{side}_{q}"]["ci95"] for q in ("h2_difference", "generation_part", "rule_part")}
    return res


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if math.isnan(float(o)) else round(float(o), 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def analyze(cfg, outdir: Path, orgs, props, smoke=False, judge="glimmer", B=None, quiet=False,
            votes_file: str = "votes.jsonl", evaluator: str | None = None, tag: str = "") -> dict:
    """votes_file: the registered evaluator's votes (votes_<evaluator>.jsonl when another arm's model screens);
    tag: suffix of the result file for a pre-specified secondary analysis (cross-screening: '_eval-<evaluator>')."""
    votes = read_jsonl(outdir / votes_file)
    ratings = read_jsonl(outdir / f"ratings_{judge}.jsonl")
    if not votes or not ratings:
        raise SystemExit(f"{votes_file} and ratings_{judge}.jsonl are required; run evaluate and judge first")
    data = Data(orgs, props, votes, ratings)
    fails = read_jsonl(outdir / "org_failures.jsonl")
    failed = {s: sum(1 for x in fails if x.get("structure") == s) for s in ("hierarchy", "polyarchy")}
    res = run(data, cfg["design"]["seeds"]["bootstrap"], B=10000 if B is None else B, orgs=orgs, failed=failed, cfg=cfg)
    rel_primary = pass_reliability(ratings)
    res["secondary"]["judge_pass_reliability"] = rel_primary
    rp = outdir / f"readings_{judge}.json"
    res["readings"] = json.loads(rp.read_text()) if rp.exists() else None     # the readings decision of this judge (4.4)
    res["secondary"]["attrition_and_fallbacks"] = _safe(attrition_and_fallbacks, outdir, orgs, props, votes_file, judge)
    ep = outdir / "extension.json"
    res["extension"] = json.loads(ep.read_text()) if ep.exists() else None
    underpowered = ((res["extension"] or {}).get("check") or {}).get("underpowered_sides_at_target", [])
    attrition = (res["secondary"]["attrition_and_fallbacks"] or {}).get("attrition") or {}
    for name, test in {"H1": res["H1"], **res["H2"]}.items():
        test["underpowered"] = name in underpowered
        test["high_attrition"] = attrition.get("low_attrition") is False
        test["below_reliability_target"] = [d for d in (res["readings"] or {}).get("below_target", [])
                                             if d in ("workability", "relevance")]
    for other_file in sorted(outdir.glob("ratings_*.jsonl")):
        other = other_file.stem.replace("ratings_", "")
        if other == judge:
            continue
        other_ratings = read_jsonl(other_file)
        if other_ratings:
            rel_other = pass_reliability(other_ratings)
            res["secondary"][f"judge_pass_reliability_{other}"] = rel_other
            res["secondary"][f"judge_agreement_with_{other}"] = _safe(judge_agreement, dim_scores(ratings), dim_scores(other_ratings),
                                                                      rel_primary, rel_other)
    res["secondary"]["evaluator_agreement_among_roles"] = _safe(evaluator_role_agreement, votes)
    for other_votes in sorted(outdir.glob("votes*.jsonl")):
        if other_votes.name != votes_file:
            ov = read_jsonl(other_votes)
            if ov:
                res["secondary"][f"evaluator_agreement_with_{other_votes.stem}"] = _safe(evaluator_agreement, votes, ov)
    res = _clean({"arm_dir": str(outdir.name), "judge": judge, "evaluator": evaluator, "votes_file": votes_file,
                  "smoke_test_not_data": smoke, **res})
    rdir = outdir / "results"
    rdir.mkdir(exist_ok=True)
    path = rdir / f"analysis_{judge}{tag}.json"
    from .config import scrub
    path.write_text(scrub(json.dumps(res, indent=2)))
    if not quiet:
        print(("SMOKE TEST - NOT DATA. " if smoke else "") + f"wrote {path}")
    return res


# ----------------------------------------------------------------------------- internal pilot for H2 (PROTOCOL.md 6.4)
def extension_candidates(cfg) -> list[int]:
    """The sizes per structure an extension could choose: from the first wave upward in steps of one allocation block
    (design.extension.step_per_structure) to design.extension.max_per_structure: 86, 88, ..., 168 (PROTOCOL.md 6.4)."""
    d = cfg["design"]
    n0, step, top = d["orgs_per_structure"], d["extension"]["step_per_structure"], d["extension"]["max_per_structure"]
    return list(range(n0 + step, top + 1, step))


def readings_check(cfg, ratings: list[dict], judge: str) -> dict:
    """The number of readings of one judge (PROTOCOL.md 4.4), decided once after its floor readings of every proposal:
    the single-reading reliability ICC(1,1) of each dimension the labels use, estimated on all proposals together
    (nothing by structure enters), gives by Spearman-Brown the smallest number of readings at which the reliability of
    the mean reaches the target; the judge reads that many, between the floor and the ceiling. A dimension that would
    need more than the ceiling is reported as below the reliability target (the judge gets the ceiling)."""
    rc = cfg["judging"]["readings"]
    floor, ceiling, target, dims = int(rc["floor"]), int(rc["ceiling"]), float(rc["target"]), list(rc["dimensions"])
    per = _scores_by_pass(ratings)
    full = {p: v for p, v in per.items() if all(j in v and _complete(v[j]) for j in range(1, floor + 1))}
    out = {"judge": judge, "floor": floor, "ceiling": ceiling, "target": target, "dimensions": dims,
           "n_proposals_rated_in_every_floor_reading": len(full), "n_proposals_rated": len(per), "icc1_1": {}, "readings_needed": {}}
    for dim in dims:
        values = [[_dim(v[j], dim) for j in range(1, floor + 1)] for v in per.values()
                  if all(j in v for j in range(1, floor + 1))]
        values = [v for v in values if not np.isnan(v).any()]
        r = icc1(values)["icc1_1"] if len(values) > 2 else None
        out["icc1_1"][dim] = r
        out["readings_needed"][dim] = (math.ceil(target * (1 - r) / (r * (1 - target)) - 1e-9) if r and r > 0 else None)
    # a dimension whose reliability cannot be estimated or is not positive needs more than any ceiling
    k = max([v if v is not None else ceiling + 1 for v in out["readings_needed"].values()] + [floor])
    step = int(rc.get("step", 1))            # readings in steps of two (4, 6, 8): rounded up, never down
    k = floor + step * math.ceil((max(k, floor) - floor) / step)
    out["readings"] = min(k, ceiling)
    out["step"] = step
    out["below_target"] = [d for d, v in out["readings_needed"].items() if v is None or v > ceiling]
    out["reliability_of_mean_at_readings"] = {d: (out["readings"] * r / (1 + (out["readings"] - 1) * r) if r and r > 0 else None)
                                             for d, r in out["icc1_1"].items()}
    out["decision"] = (f"{out['readings']} readings" + (" (the floor)" if out["readings"] == floor else "")
                       + (f"; below the reliability target at the ceiling on {', '.join(out['below_target'])}"
                          if out["below_target"] else ""))
    return out


def extension_check(cfg, data: "Data", n_core: int, reps: int = 4000) -> dict:
    """The internal pilot's one recalculation after the primary judge (PROTOCOL.md 6.4; H1 never asks for more than 84,
    so the target is set by H2a and H2b, at most 168). Uses only quantities pooled over
    both structures (category rates, approval rates under both rules, the dispersion of the counts written over
    all organizations, and the dependence of approvals within organizations), never a comparison between the
    structures. Returns the exact power of H1 at d = .5 and the simulated power of H2a (quality) and H2b (below), each
    category simulated in the direction H1 predicts for it, all at alpha .05, at n_core and at each registered
    candidate size, and the target: the smallest size at which all reach .80, or the ceiling if none does."""
    from .power import design_power, power_two_sample, rho_pass_from_counts
    t, thr, cats = data.org_table()
    a_test = alpha_per_test(cfg)
    out = {"n_core": n_core, "threshold": thr, "alpha_per_test": a_test, "pooled": {}, "power": {},
           "candidates": extension_candidates(cfg)}
    sides = {"quality": cats["quality"], "below": cats["below"]}
    for side, lab in sides.items():
        pi = float(lab.mean())
        p1, p4 = _rate(lab & data.acc1, lab & data.voted), _rate(lab & data.acc4, lab & data.voted)
        k = float(t["slots"].mean())
        vb = k * pi * (1 - pi)
        phi_lumped = float(t[side].var(ddof=1) / vb) if vb > 0 else float("nan")
        # the variance over all organizations contains the (unknown) structure difference; under the planning value
        # d = .5 it is the within-structure variance times (1 + d^2 / 4), so the within-structure dispersion is
        # estimated by the adjusted lumped estimator (Kieser and Friede, 2003), without comparing the structures
        phi = phi_lumped / (1 + 0.5 ** 2 / 4)
        d1 = rho_pass_from_counts(t[f"{side}_voted"], t[f"{side}_acc1"])
        d4 = rho_pass_from_counts(t[f"{side}_voted"], t[f"{side}_acc4"])
        out["pooled"][side] = {"category_rate": pi, "approval_rate_one_of_four": p1, "approval_rate_four_of_four": p4,
                               "dispersion_phi_lumped": phi_lumped, "dispersion_phi_pooled": phi,
                               "psi_one_of_four": d1["psi"], "psi_four_of_four": d4["psi"],
                               "rho_pass": max(d1["rho_pass"], d4["rho_pass"]), "direction_simulated": H1_DIRECTION[side]}
    sizes = [n_core] + [c for c in out["candidates"] if c > n_core]
    h2_names = {"quality": "H2a_quality", "below": "H2b_below"}
    for n in sizes:
        out["power"][str(n)] = {"H1": float(power_two_sample(n, 0.5, a_test))}
        for side in sides:
            q = out["pooled"][side]
            p1, p4 = q["approval_rate_one_of_four"], q["approval_rate_four_of_four"]
            ok = 0 < q["category_rate"] < 1 and p1 == p1 and p4 == p4 and 0 < p1 <= 1 and 0 <= p4 < 1
            r = _safe(design_power, n, q["category_rate"], q["dispersion_phi_pooled"] if q["dispersion_phi_pooled"] == q["dispersion_phi_pooled"] else 1.0,
                      p4, reps, rho_pass=q["rho_pass"], p1=p1, alpha=a_test, direction=H1_DIRECTION[side]) if ok else {"error": "not computable"}
            # no category or no approvals leave H2 without signal: power 0 for the decision; a dispersion below what
            # the simulation can generate (raised to its floor) would overstate power: also 0 (extend)
            raised = isinstance(r, dict) and r.get("phi_used", 0) > (q["dispersion_phi_pooled"] or 0) + 1e-6
            good = isinstance(r, dict) and "power_h2" in r and not raised
            out["power"][str(n)][h2_names[side]] = float(r["power_h2"]) if good else 0.0
    all_sides = ["H1"] + list(h2_names.values())
    def both_ok(n):
        return all(out["power"][str(n)][s] >= 0.80 for s in all_sides)
    target = next((n for n in sizes if both_ok(n)), None)
    out["target_per_structure"] = target if target is not None else max(sizes)
    out["adequately_powered_at_target"] = target is not None
    out["underpowered_sides_at_target"] = [s for s in all_sides if out["power"][str(out["target_per_structure"])][s] < 0.80]
    out["decision"] = ("no extension" if out["target_per_structure"] == n_core else
                       f"extend to {out['target_per_structure']} per structure") + ("" if target is not None else
                       " (the maximum; the side below .80 is labeled underpowered before any test)")
    return out
