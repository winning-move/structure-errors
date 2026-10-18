"""Command line: uv run python -m np_registered <command> --arm <arm> [options]

Commands (run in this order; each is resumable and idempotent):
  allocate    write allocation.csv for the arm (deterministic from the seed)
  preflight   check credentials, model ids, weights hash (local arm), and one tiny call per model
  generate    run the generation stage until the registered sample is complete
  evaluate    four role evaluators screen every proposal with the arm's registered `evaluator` model (another
              arm's model); --evaluator X screens the same batches with arm X's model instead (cross-evaluation,
              written to votes_<X>.jsonl; not registered, PROTOCOL.md 5.2)
  judge       the registered primary judge (config judging.primary; --judge for the second judge): the floor of four
              readings, or the number readings-check decided (readings_<judge>.json); one call per proposal and reading,
              all six subscales in a seeded random order; resumable, adds only missing readings
  readings-check after a judge's floor readings of every proposal: sets that judge's number of readings once by the
              registered reliability rule (PROTOCOL.md 4.4; pooled over all proposals); writes readings_<judge>.json;
              then run judge again for the same judge (it adds the remaining readings)
  register-models  before registration only: SHA-256 of every file LM Studio serves -> config/model_files.json
  extend-check after the primary judge: the internal pilot's one recalculation at the pooled quantities (PROTOCOL.md
              6.4); writes extension.json (the smallest size on 84, 86, ..., 168 at which H2a and H2b reach .80, or
              168 with a hypothesis below .80 labeled underpowered); generate, evaluate, and judge then add only the
              new organizations
  manifest    write manifest.json (hashes of protocol, code, data, model weights, versions)
  analyze     run the registered analysis (analysis.py) and write results/; refuses before both judges have rated the
              final sample (PROTOCOL.md 4.5)
  status      progress and cost so far

--smoke N   a test run of N organizations per structure, written outside the study folder (never data).
--mock      uses the deterministic mock backend (no model calls); for testing the pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from . import stages
from .backends import make_backend
from .config import arm_dir, load_config, load_dotenv, load_prompts, scrub, sha256_file, ROOT


def _arm_backend(cfg, arm, mock):
    return make_backend(cfg["arms"][arm], mock=mock)


def _judge_backend(cfg, judge, mock):
    return make_backend(cfg["judges"][judge], mock=mock)


def _alloc(cfg, outdir, n):
    path = outdir / "allocation.csv"
    rows = stages.allocate(cfg, n)
    if path.exists():
        import csv
        with open(path, encoding="utf-8") as f:
            old = list(csv.DictReader(f))
        if [r["org_id"] + r["structure"] for r in old] != [r["org_id"] + r["structure"] for r in rows]:
            sys.exit(f"allocation.csv in {outdir} differs from the seeded allocation; refusing to continue")
    else:
        stages.write_allocation(rows, path)
    return rows


def _read_readings(outdir, judge):
    p = outdir / f"readings_{judge}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _read_extension(outdir):
    p = outdir / "extension.json"
    return json.loads(p.read_text()) if p.exists() else None


def _complete_rows(rows, ids, field, values):
    """Every proposal has exactly one terminal outcome per role or reading, including exhausted outcomes."""
    from collections import Counter
    seen = Counter((r.get("proposal_id"), r.get(field)) for r in rows)
    return all(seen[(pid, value)] == 1 for pid in ids for value in values)


def code_hash() -> dict:
    files = sorted((ROOT / "src" / "np_registered").glob("*.py"))
    return {f"src/np_registered/{p.name}": sha256_file(p) for p in files}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="np_registered", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["allocate", "preflight", "generate", "evaluate", "judge",
                                        "extend-check", "readings-check", "manifest", "analyze", "status", "register-models"])
    ap.add_argument("--arm", default="qwen38", help="an arm of config/study.yaml (an experiment, named after its writer)")
    ap.add_argument("--only", default=None,
                    help="preflight: check only this LM Studio identifier (the model loaded for the next step)")
    ap.add_argument("--evaluator", default=None,
                    help="evaluate/analyze: the arm whose model screens (default: the arm's registered evaluator)")
    ap.add_argument("--judge", default=None, help="a judge of config/study.yaml (default: judging.primary)")
    ap.add_argument("--smoke", type=int, default=0, help="organizations per structure for a test run (outside the study folder)")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--concurrency", type=int, default=0)
    a = ap.parse_args(argv)

    load_dotenv()
    cfg, prompts = load_config(), load_prompts()
    for opt, key in ((a.arm, "arms"), (a.evaluator, "arms"), (a.judge, "judges")):
        if opt is not None and opt not in cfg[key]:
            sys.exit(f"unknown {key[:-1]} '{opt}'; configured: {', '.join(cfg[key])}")
    reg_ev = cfg["arms"][a.arm].get("evaluator", a.arm)        # the registered evaluator of this arm
    ev = a.evaluator or reg_ev
    votes_file = f"votes{stages.eval_suffix(a.arm, reg_ev)}.jsonl"
    if a.judge is None:
        a.judge = cfg["judging"]["primary"]
    smoke = a.smoke > 0 or a.mock
    n = a.smoke if a.smoke else cfg["design"]["orgs_per_structure"]
    outdir = arm_dir(a.arm + ("-mock" if a.mock else ""), smoke=smoke)
    conc = a.concurrency or cfg["arms"].get(a.arm, {}).get("concurrency", 4)
    ext_cfg = cfg["design"].get("extension") if not smoke else None
    n_alloc = max(n, ext_cfg["max_per_structure"]) if ext_cfg else n     # the extension's organizations are pre-drawn
    ext = _read_extension(outdir)
    n_target = max(n, ext["target_per_structure"]) if ext else n          # after extend-check, the registered target
    waves = [set(ext["core_proposal_ids"])] if ext else None               # the first wave keeps its own batches

    if a.command == "register-models" and a.mock:
        sys.exit("register-models has no mock mode (it writes config/model_files.json, part of the fingerprint)")
    if a.command == "register-models":
        # before registration only: the SHA-256 of every file in each served folder of the line-up
        from .preflight import line_models, weights_hash
        out = {}
        for arm in [k for k, v in cfg["arms"].items() if v.get("evaluator") not in (None, k)]:
            for name, spec in line_models(cfg, arm).items():
                if spec["backend"] != "openai_compatible":
                    continue
                role = name.split(":")[0]                  # a local model writes in one experiment and evaluates in the other
                if spec["model"] in out:
                    roles = sorted(set(out[spec["model"]]["role"].split(", ")) | {role})
                    out[spec["model"]]["role"] = ", ".join(roles)
                    continue
                out[spec["model"]] = {"role": role, "weights_dir": spec["weights_dir"],
                                      "files": weights_hash(spec["weights_dir"])}
                print(f"{spec['model']}: {len(out[spec['model']]['files'])} files hashed in {spec['weights_dir']}")
        (ROOT / "config" / "model_files.json").write_text(json.dumps(out, indent=2) + "\n")
        print("wrote config/model_files.json (preflight checks the loaded models against it)")
        return
    if a.command == "allocate":
        rows = _alloc(cfg, outdir, n_alloc)
        print(f"{outdir}/allocation.csv: {sum(1 for r in rows if not r['reserve'])} organizations + reserves "
              f"(first wave {n} per structure; pre-drawn up to {n_alloc})")
        return
    if a.command == "preflight":
        from .preflight import preflight
        detail: dict = {}
        ok = preflight(cfg, prompts, a.arm, mock=a.mock, only=a.only, detail=detail, smoke=smoke)
        sys.exit(0 if ok else (3 if detail.get("needs_person") else 1))     # 3: no reload can fix it (run_all stops)
    if a.command == "generate":
        alloc = _alloc(cfg, outdir, n_alloc)
        be = _arm_backend(cfg, a.arm, a.mock)
        print(f"generation: arm={a.arm} model={be.describe()['model']} n={n_target}/structure -> {outdir}")
        orgs = stages.run_generation(cfg, prompts, be, outdir, a.arm, alloc, conc, n_target)
        print(f"registered sample: {len(orgs)} organizations")
        return
    if a.command in ("evaluate", "judge", "extend-check", "readings-check", "analyze", "manifest", "status"):
        alloc = _alloc(cfg, outdir, n_alloc)
        orgs = stages.registered_orgs(cfg, outdir, alloc, n_target)
        props = stages.proposals_of(orgs)
        complete = all(sum(1 for o in orgs if o["structure"] == s) == n_target for s in cfg["design"]["structures"])
        if a.command in ("evaluate", "judge", "extend-check", "readings-check") and not complete:
            sys.exit("generation is not complete for the registered sample; run `generate` first")
        if not smoke and a.command in ("judge", "readings-check") and a.judge == cfg["judging"]["second"]:
            primary = cfg["judging"]["primary"]
            rd = _read_readings(outdir, primary)
            ids = {p["proposal_id"] for p in props}
            if not ext or not rd or not _complete_rows(stages.read_jsonl(outdir / votes_file), ids, "role", prompts.roles["order"]) \
                    or not _complete_rows(stages.read_jsonl(outdir / f"ratings_{primary}.jsonl"), ids, "pass",
                                          range(1, rd["readings"] + 1)):
                sys.exit("the second judge requires the extension decision and complete registered evaluation and primary "
                         "readings of the final sample")
        if a.command == "evaluate":
            be = _arm_backend(cfg, ev, a.mock)
            ec = a.concurrency or cfg["arms"][ev].get("concurrency", 4)
            print(f"evaluation: arm={a.arm} evaluator={ev} model={be.describe()['model']}"
                  f"{'' if ev == reg_ev else ' (cross-screening; not the registered evaluator)'} -> {outdir}")
            votes = stages.run_evaluation(cfg, prompts, be, outdir, a.arm, props, ec, waves=waves, evaluator=ev)
            print(f"votes: {len(votes)} ({sum(v['decision'] is None for v in votes)} missing)")
        elif a.command == "readings-check":
            from .analysis import readings_check
            rd = _read_readings(outdir, a.judge)
            if rd:
                print(f"readings_{a.judge}.json exists: {rd['decision']} (decided {rd['decided_at']}); nothing to do")
                return
            floor = cfg["judging"]["readings"]["floor"]
            ratings = stages.read_jsonl(outdir / f"ratings_{a.judge}.jsonl")
            ids = {p["proposal_id"] for p in props}
            seen = {}
            for r in ratings:
                seen.setdefault(r["proposal_id"], set()).add(r["pass"])
            short = [pid for pid in ids if not {k for k in range(1, floor + 1)} <= seen.get(pid, set())]
            if short:
                sys.exit(f"the floor of {floor} readings by {a.judge} is not complete for {len(short)} of {len(ids)} proposals; "
                         f"run judge --judge {a.judge} first")
            chk = readings_check(cfg, [r for r in ratings if r["proposal_id"] in ids and r["pass"] <= floor], a.judge)
            rec = {"decided_at": datetime.now(timezone.utc).isoformat(), "n_per_structure_at_decision": n_target,
                   "proposal_ids": sorted(ids), **chk}
            (outdir / f"readings_{a.judge}.json").write_text(scrub(json.dumps(rec, indent=2)))
            print(json.dumps({k: chk[k] for k in ("icc1_1", "readings_needed", "reliability_of_mean_at_readings")}, indent=2))
            print(f"DECISION: {chk['decision']} -> {outdir}/readings_{a.judge}.json")
            if chk["readings"] > floor:
                print(f"next: judge --judge {a.judge} again (it adds readings {floor + 1} to {chk['readings']})")
        elif a.command == "extend-check":
            if a.judge != cfg["judging"]["primary"]:
                sys.exit(f"extend-check uses the registered primary judge only ({cfg['judging']['primary']})")
            if ext:
                print(f"extension.json exists: {ext['decision']} (decided {ext['decided_at']}); nothing to do")
                return
            if not ext_cfg:
                sys.exit("no extension is configured for smoke tests")
            from .analysis import Data, extension_check
            votes = stages.read_jsonl(outdir / votes_file)
            ratings = stages.read_jsonl(outdir / f"ratings_{a.judge}.jsonl")
            if not votes or not ratings:
                sys.exit(f"{votes_file} and the primary judge's ratings are required; run evaluate and judge first")
            rd = _read_readings(outdir, a.judge)
            if not rd:
                sys.exit(f"readings_{a.judge}.json is missing: the readings rule decides before the size rule (run readings-check)")
            ids = {p["proposal_id"] for p in props}
            if not _complete_rows(votes, ids, "role", prompts.roles["order"]):
                sys.exit(f"{votes_file} is incomplete for the registered evaluator; run evaluate first")
            if not _complete_rows(ratings, ids, "pass", range(1, rd["readings"] + 1)):
                sys.exit(f"the decided {rd['readings']} readings by {a.judge} are incomplete; run judge again first")
            chk = extension_check(cfg, Data(orgs, props, votes, ratings), n)
            rec = {"decided_at": datetime.now(timezone.utc).isoformat(), "judge": a.judge, "n_core": n,
                   "core_org_ids": [o["org_id"] for o in orgs], "core_proposal_ids": [p["proposal_id"] for p in props],
                   "target_per_structure": chk["target_per_structure"], "decision": chk["decision"], "check": chk}
            (outdir / "extension.json").write_text(scrub(json.dumps(rec, indent=2)))
            print(json.dumps({"pooled": chk["pooled"], "power": chk["power"]}, indent=2))
            print(f"DECISION: {chk['decision']} -> {outdir}/extension.json")
            if chk["target_per_structure"] > n:
                print("next: generate, evaluate, judge (same commands; only the new organizations are run), "
                      "then complete the second judge before analyze")
        elif a.command == "judge":
            be = _judge_backend(cfg, a.judge, a.mock)
            jc = a.concurrency or cfg["judges"][a.judge].get("concurrency", 8)
            rd = _read_readings(outdir, a.judge)
            k = rd["readings"] if rd else cfg["judging"]["readings"]["floor"]
            print(f"judge {a.judge}: {k} readings ({'decided by the readings rule' if rd else 'the floor; readings-check after it'})")
            rows = stages.run_judge(cfg, prompts, be, outdir, a.arm, a.judge, props, jc, waves=waves, passes=k)
            print(f"ratings: {len(rows)} ({sum(1 for r in rows if r.get('missing'))} missing)")
        elif a.command == "manifest":
            from .manifest import write_manifest
            print(write_manifest(cfg, a.arm, outdir, code_hash(), mock=a.mock))
        elif a.command == "status":
            from .manifest import status
            print(status(cfg, outdir, n_target) + (f"\n  extension: {ext['decision']}" if ext else
                                                   "\n  extension: not yet checked (run extend-check after the first wave is judged)"))
        elif a.command == "analyze":
            from .analysis import analyze
            if not complete:
                sys.exit("generation is not complete for the registered sample")
            if not smoke:
                # the registered order (PROTOCOL.md 4.5): no analysis before the extension decision, and none before every
                # stage it needs is complete for the final sample
                if not ext:
                    sys.exit("extension.json is missing: run extend-check (and any extension) before analyze")
                # no test before every stage is complete, the second judge included (PROTOCOL.md 4.5): the analysis with
                # either judge's categories needs both judges' ratings of the final sample and both readings decisions
                judges_needed = list(dict.fromkeys([cfg["judging"]["primary"], cfg["judging"]["second"], a.judge]))
                vote_files = list(dict.fromkeys([votes_file, f"votes{stages.eval_suffix(a.arm, ev)}.jsonl"]))
                need = vote_files + [f"ratings_{j}.jsonl" for j in judges_needed]
                missing = [f for f in need if not (outdir / f).exists()]
                missing += [f"readings_{j}.json (run readings-check)" for j in judges_needed
                            if not (outdir / f"readings_{j}.json").exists()]
                ids = {p["proposal_id"] for p in props}
                for f in vote_files:
                    if f not in missing and not _complete_rows(stages.read_jsonl(outdir / f), ids, "role", prompts.roles["order"]):
                        missing.append(f + " (incomplete for the final sample)")
                for j in judges_needed:
                    f = f"ratings_{j}.jsonl"
                    rd = _read_readings(outdir, j)
                    if f not in missing and rd and not _complete_rows(stages.read_jsonl(outdir / f), ids, "pass",
                                                                     range(1, rd["readings"] + 1)):
                        missing.append(f + " (incomplete for the decided readings of the final sample)")
                if missing:
                    sys.exit(f"not every stage is complete: {missing}")
            vf = f"votes{stages.eval_suffix(a.arm, ev)}.jsonl"
            tag = "" if ev == reg_ev else f"_eval-{ev}"      # cross-screening: a pre-specified secondary analysis
            analyze(cfg, outdir, orgs, props, smoke=smoke, judge=a.judge, votes_file=vf, evaluator=ev, tag=tag)
            from .report import write_report
            try:
                print(f"wrote {write_report(outdir, a.judge, tag)}")
            except Exception as e:  # noqa: BLE001 - the report is presentation only; the JSON is the result
                print(f"note: the readable report could not be written ({type(e).__name__}: {e}); "
                      "the analysis JSON is complete")
        return


def run():
    from .runner import Abort
    from .stages import ReserveExhausted
    try:
        main()
    except Abort as e:
        print(f"\nSTOPPED: {e}\nNo outcome (organization failure, vote, or rating) was recorded for the interrupted "
              "calls; their failed attempts are in the call log. Fix the cause (network, key, credit, rate limit) and "
              "run the same command again; completed calls are not repeated.", file=sys.stderr)
        sys.exit(2)
    except ReserveExhausted as e:
        print(f"\nSTOPPED: {e}\nThis is a registered stop (PROTOCOL.md 8.3): do not resume; report it to the "
              "researchers before doing anything else.", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    run()
