"""The power simulation used by the internal pilot's recalculation (PROTOCOL.md 6.4) and by the planning numbers of
section 6: the exact power of the two-sample t-test (H1), and a simulation of the design for H2 (12 proposals per
organization in four roles, nested approvals under the two rules, dependence of approvals within organizations).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def paired_orgs(k4, k1, m, alpha: float = 0.05) -> dict:
    """The rule comparison (PROTOCOL.md 7.3): per organization, the proportion of its labeled proposals with complete
    votes (m) approved under four of four (k4) minus the proportion approved under one of four (k1); organizations with
    no such proposal contribute nothing. Mean, t interval over organizations (G - 1 degrees of freedom), and the
    one-sample t statistic against 0 (used in the simulation; not reported as a test)."""
    k4, k1, m = (np.asarray(x, float) for x in (k4, k1, m))
    keep = m > 0
    d = (k4[keep] - k1[keep]) / m[keep]
    G, N = len(d), int(m[keep].sum())
    if G == 0:
        return {"mean": float("nan"), "se": float("nan"), "t": float("nan"), "df": 0, "p": float("nan"),
                "ci95": [float("nan"), float("nan")], "n_proposals": 0, "n_organizations": 0}
    mean = float(d.mean())
    if G < 2:
        return {"mean": mean, "se": float("nan"), "t": float("nan"), "df": 0, "p": float("nan"), "ci95": [mean, mean],
                "n_proposals": N, "n_organizations": G}
    se = float(d.std(ddof=1)) / math.sqrt(G)
    if not se > 0:
        return {"mean": mean, "se": se, "t": float("nan"), "df": G - 1, "p": float("nan"), "ci95": [mean, mean],
                "n_proposals": N, "n_organizations": G}
    t = mean / se
    q = stats.t.ppf(1 - alpha / 2, G - 1)
    return {"mean": mean, "se": se, "t": t, "df": G - 1, "p": 2 * stats.t.sf(abs(t), G - 1),
            "ci95": [mean - q * se, mean + q * se], "n_proposals": N, "n_organizations": G}


def power_two_sample(n: int, d: float, alpha: float = 0.05) -> float:
    """Exact power of the two-sided two-sample t-test, n per group (noncentral t)."""
    df = 2 * n - 2
    nc = d * math.sqrt(n / 2)
    tc = stats.t.ppf(1 - alpha / 2, df)
    if nc > 8:  # power > 1 - 1e-9; scipy nct returns nan for large noncentrality
        return 1.0
    return float(stats.nct.sf(tc, df, nc) + stats.nct.cdf(-tc, df, nc))


def min_phi(pi: float, K: int = 12) -> float:
    """Smallest dispersion the role-split generator can produce at base rate pi (one role's rate at 0 or 1)."""
    lo = min(pi, 1 - pi)
    return 1.0 - 3 * lo * lo / (pi * (1 - pi))


def org_counts(rng, n: int, pi: float, phi: float, K: int = 12):
    """Counts of labeled proposals for n organizations with K slots, mean K*pi and variance phi*K*pi*(1-pi).

    phi = 1: binomial (every slot the same rate).
    phi > 1: beta-binomial (organizations' rates vary; intraclass correlation (phi - 1)/(K - 1)).
    phi < 1: under-dispersion, which arises when the four roles write at different rates (the 12
             slots are a stratified sample, 3 per role): one role at pi +/- 3*delta and three roles at
             pi -/+ delta, with delta = sqrt((1 - phi) * pi * (1 - pi) / 3); the variance of the count
             is then K*pi*(1-pi) - 36*delta^2 = phi*K*pi*(1-pi).
    """
    if phi > 1:
        rho = (phi - 1) / (K - 1)
        s = (1 - rho) / rho
        return rng.binomial(K, rng.beta(pi * s, (1 - pi) * s, n))
    if phi == 1 or K != 12:
        return rng.binomial(K, np.full(n, pi))
    if phi < min_phi(pi, K) - 1e-9:
        raise ValueError(f"phi={phi} is below the smallest feasible dispersion {min_phi(pi, K):.3f} at pi={pi}")
    delta = math.sqrt((1 - phi) * pi * (1 - pi) / 3)
    if pi < 0.5:
        rates = [pi + 3 * delta] + [pi - delta] * 3     # one role writes most of the labeled proposals
    else:
        rates = [pi - 3 * delta] + [pi + delta] * 3     # one role writes few of them
    rates = np.clip(rates, 0.0, 1.0)
    return sum(rng.binomial(3, np.full(n, r)) for r in rates)


def rho_pass_from_counts(written, kept) -> dict:
    """Dependence of the passes within an organization, from organization counts pooled over structures:
    psi = sum (kept - p m)^2 / sum m p (1 - p) with p the pooled pass rate (psi = 1 for independent passes), and the
    intraclass correlation it implies, rho = (psi - 1) sum m / sum m (m - 1), floored at 0 (negative dependence is
    not credited). A difference in pass rates between the structures can only raise psi (conservative)."""
    w, k = np.asarray(written, float), np.asarray(kept, float)
    if w.sum() <= 0:
        return {"psi": float("nan"), "rho_pass": 0.0}
    p = k.sum() / w.sum()
    den = (w * p * (1 - p)).sum()
    psi = float(((k - p * w) ** 2).sum() / den) if den > 0 else float("nan")
    pairs = (w * (w - 1)).sum()
    rho = (psi - 1) * w.sum() / pairs if pairs > 0 and psi == psi else 0.0
    return {"psi": psi, "rho_pass": float(min(max(rho, 0.0), 0.5))}


def _welch_pvalue(a, b):
    """The same Welch test from sufficient statistics, avoiding per-sample input processing in the simulation."""
    return stats.ttest_ind_from_stats(a.mean(), a.std(ddof=1), len(a), b.mean(), b.std(ddof=1), len(b),
                                      equal_var=False).pvalue


def simulate_h2(n: int, pi_p: float, d: float, p1: float, p4: float, phi: float = 1.0, K: int = 12,
                reps: int = 2000, alpha: float = 0.05, seed: int = 1, rho_pass: float = 0.0, direction: int = -1) -> dict:
    """Simulate the design on one category (quality or below the threshold) at n organizations per structure.
    Organizations write the category's proposals at rate pi_p (polyarchy) and at the rate d pooled SDs away in
    `direction` (hierarchy; -1 for proposals below the quality threshold, +1 for quality proposals, as H1 predicts);
    each such proposal is approved by at least one evaluator with probability p1 and by all four with probability p4
    (nested: P(all four | at least one) = p4 / p1). With rho_pass > 0 an organization's approval probabilities are drawn
    from beta distributions with intraclass correlation rho_pass. Returns the share of simulated studies in which
    H1 (Welch test of the share written), H2 (Welch test of approvals under the own rule per proposal), and the rule
    comparison (four of four minus one of four, per organization) are significant at alpha."""
    rng = np.random.default_rng(seed)
    pi_h = hierarchy_rate_signed(pi_p, d, direction, phi, K) if d > 0 else pi_p
    q = p4 / p1 if p1 > 0 else 0.0
    hits = {"H1": 0, "H2": 0, "rule": 0}

    def draw(p):
        if rho_pass <= 0 or p <= 0 or p >= 1:
            return np.full(2 * n, p)
        return rng.beta(p * (1 - rho_pass) / rho_pass, (1 - p) * (1 - rho_pass) / rho_pass, 2 * n)

    for _ in range(reps):
        m = np.r_[org_counts(rng, n, pi_h, phi, K), org_counts(rng, n, pi_p, phi, K)]
        k1 = rng.binomial(m, draw(p1))
        k4 = rng.binomial(k1, draw(q))
        hits["H1"] += _welch_pvalue(m[:n] / K, m[n:] / K) < alpha
        own = np.r_[k4[:n], k1[n:]] / K                 # H2: hierarchies under four of four, polyarchies under one of four
        if own[:n].std() > 0 or own[n:].std() > 0:
            hits["H2"] += _welch_pvalue(own[:n], own[n:]) < alpha
        rc = paired_orgs(k4, k1, m, alpha)              # the rule comparison, per organization
        hits["rule"] += bool(rc["p"] < alpha and rc["mean"] < 0)
    return {"H1": hits["H1"] / reps, "H2": hits["H2"] / reps, "rule": hits["rule"] / reps, "n_per_structure": n, "pi_polyarchy": pi_p,
            "pi_hierarchy": round(pi_h, 4), "d": d, "p1": p1, "p4": p4, "phi": phi, "rho_pass": rho_pass, "reps": reps,
            "direction": direction}


def centered_rates(pi: float, d: float, direction: int = -1, phi: float = 1.0, K: int = 12) -> tuple[float, float]:
    """(polyarchy rate, hierarchy rate) d pooled SDs apart in `direction` whose mean is pi: the observed category rate
    is pooled over both structures, so the two simulated structures are centered on it, not the polyarchy alone."""
    lo, hi = (pi, 1 - 1e-6) if direction < 0 else (1e-6, pi)
    for _ in range(80):
        mid = (lo + hi) / 2
        if (mid + hierarchy_rate_signed(mid, d, direction, phi, K)) / 2 < pi:
            lo = mid
        else:
            hi = mid
    pi_p = (lo + hi) / 2
    return pi_p, hierarchy_rate_signed(pi_p, d, direction, phi, K)


def design_power(n: int, pi: float, phi: float, p4: float, reps: int = 4000, seed: int = 61,
                 rho_pass: float = 0.0, p1: float | None = None, alpha: float = 0.05, direction: int = -1) -> dict:
    """The design simulation of H2 at quantities pooled over structures (PROTOCOL.md 6.4): category rate pi (the mean
    of the two structures' simulated rates, centered_rates), dispersion phi of the counts written, approval rates p1
    (one of four) and p4 (four of four) of the category's proposals, dependence rho_pass, at n per structure and d = .5
    on the share written, in the direction H1 predicts for the category (direction: -1 below the quality threshold,
    +1 quality; simulate_h2). phi below the generator's floor is raised to the floor and reported."""
    if p1 is None:
        p1 = 1.0
    phi_used = phi
    pi_p, pi_h = centered_rates(pi, 0.5, direction, phi_used)
    if phi < 1:  # the generator's floor depends on the rates of both structures
        for _ in range(50):
            pi_p, pi_h = centered_rates(pi, 0.5, direction, phi_used)
            floor = max(min_phi(pi_p), min_phi(pi_h)) + 1e-6
            if phi_used >= floor:
                break
            phi_used = min(1.0, floor)
        pi_p, pi_h = centered_rates(pi, 0.5, direction, phi_used)
    r = simulate_h2(n, pi_p, 0.5, p1, p4, phi=phi_used, reps=reps, seed=seed, rho_pass=rho_pass, alpha=alpha,
                    direction=direction)
    return {"n_per_structure": n, "pi": pi, "pi_polyarchy": pi_p, "pi_hierarchy": pi_h, "phi_observed": phi,
            "phi_used": phi_used, "p1": p1, "p4": p4, "direction": direction,
            "rho_pass": rho_pass, "reps": reps, "seed": seed, "alpha": alpha, "power": r["H2"], "power_h2": r["H2"],
            "power_rule_comparison": r["rule"], "power_h1": r["H1"],
            "adequately_powered": bool(r["H2"] >= 0.80)}


def hierarchy_rate(pi_p: float, d: float, phi: float = 1.0, K: int = 12) -> float:
    """The hierarchy's label rate such that the difference in shares is exactly d pooled SDs
    (the SD of a share out of K, sqrt(phi * pi * (1 - pi) / K), averaged over the two structures)."""
    lo, hi = 1e-6, pi_p
    for _ in range(80):
        mid = (lo + hi) / 2
        sd = math.sqrt(phi * (pi_p * (1 - pi_p) + mid * (1 - mid)) / (2 * K))
        if (pi_p - mid) / sd > d:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def hierarchy_rate_signed(pi_p: float, d: float, direction: int = -1, phi: float = 1.0, K: int = 12) -> float:
    """The hierarchy's category rate d pooled SDs below (direction -1) or above (+1) the polyarchy's rate pi_p. The SD
    of a share is symmetric in pi and 1 - pi, so the rate above is the mirror image of the rate below."""
    if direction not in (-1, 1):
        raise ValueError(f"direction must be -1 or +1, not {direction!r}")
    return hierarchy_rate(pi_p, d, phi, K) if direction < 0 else 1.0 - hierarchy_rate(1.0 - pi_p, d, phi, K)
