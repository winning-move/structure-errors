"""Planning simulation of H2 (PROTOCOL.md 6.3, 6.4): the power of H2a (quality proposals, drawn in H1's direction: more
in hierarchies) and H2b (proposals below the quality threshold: fewer in hierarchies) at d = .5 on the share written,
alpha .05, by the registered design simulation (np_registered.power.design_power), over category rates, approval rates
under one of four (p1) and four of four (p4), and the dependence of approvals within organizations (rho). The last
pair of approval rates has the four evaluators almost always agreeing, where the two rules decide alike.
Run from registered/: uv run python power/run_h2_power.py -> power/h2_power.json (about a minute)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from np_registered.power import design_power  # noqa: E402

out = {}
for side, direction in (("H2a quality", +1), ("H2b below", -1)):
    for pi in (0.2, 0.5, 0.8):
        for p1, p4 in ((0.90, 0.20), (0.70, 0.30), (0.55, 0.45)):
            for rho in (0.0, 0.1):
                for n in (84, 168):
                    r = design_power(n, pi, 1.0, p4, reps=1000, seed=7, rho_pass=rho, p1=p1, direction=direction)
                    out[f"{side}: rate {pi}, p1 {p1}, p4 {p4}, rho {rho}, n {n}"] = round(r["power_h2"], 3)
Path(__file__).with_name("h2_power.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
