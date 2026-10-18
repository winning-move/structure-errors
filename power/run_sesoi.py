"""H1's sample size at each smallest effect size of interest (SESOI), PROTOCOL.md 6.1, 6.2, and 6.6.
Detection: exact two-sided two-sample t power (noncentral t). Equivalence: two one-sided tests with bounds of
+-SESOI x the pooled SD, at a true difference of 0 (exact, central t). Also the smallest effect detectable with power
.80 at the first wave (84) and at the cap (168). Run from registered/:
  uv run python power/run_sesoi.py -> power/sesoi_table.json"""
import json
import math
import sys
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from np_registered.power import power_two_sample  # noqa: E402


def tost_power(n, b, alpha=0.05):
    df = 2 * n - 2
    delta = b * math.sqrt(n / 2) - stats.t.ppf(1 - alpha, df)
    return max(0.0, 2 * stats.t.cdf(delta, df) - 1)


def nmin(f, target):
    n = 10
    while f(n) < target:
        n += 1
    return n


def mde(n, target=0.80):
    lo, hi = 0.05, 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if power_two_sample(n, mid) >= target else (mid, hi)
    return round(hi, 3)


out = {"sesoi": {}, "smallest_detectable_d_at_power_.80": {str(n): mde(n) for n in (84, 168)}}
for b in (0.5, 0.45, 0.4, 0.35, 0.3):
    out["sesoi"][str(b)] = {
        "n_detect_80": nmin(lambda n: power_two_sample(n, b), 0.80),
        "n_detect_90": nmin(lambda n: power_two_sample(n, b), 0.90),
        "n_equivalence_80": nmin(lambda n: tost_power(n, b), 0.80),
        "power_detect_at": {str(n): round(power_two_sample(n, b), 3) for n in (84, 168)},
        "power_equivalence_at": {str(n): round(tost_power(n, b), 3) for n in (84, 168)},
    }
Path(__file__).with_name("sesoi_table.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
