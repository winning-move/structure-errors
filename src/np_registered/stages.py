"""Allocation, generation, evaluation, and judging stages.

All randomness comes from the seeds in config/study.yaml through random.Random(seed);
re-running any stage reproduces the same allocation, orders, batches, and blind ids.
"""
from __future__ import annotations

import csv
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import prompts as P
from .config import scrub
from .runner import Abort, CallLog, Failed, read_records, run_call, run_calls_batch, start_on_new_line  # noqa: F401  (Abort stops a stage)
from .schemas import (EVALUATION_SCHEMA, GENERATION_SCHEMA, JUDGE_SCALES, check_subscales, check_vote,  # noqa: F401
                      judge_schema_for, with_count, validate_generation, validate_items)


class ReserveExhausted(RuntimeError):
    """More organizations of one structure failed than there are replacements (PROTOCOL.md 8.3)."""


# ----------------------------------------------------------------------------- allocation
def allocate(cfg: dict, n_per_structure: int | None = None) -> list[dict]:
    """Interleaved blocks of 2 hierarchy + 2 polyarchy; order within each block from the seed.

    Organization ids are created first (org001, org002, ... in run order) and the structure is
    then drawn for each position, so an id carries no information about its structure.
    Reserve ids (rsv-hierarchy-01, ...; one per planned organization at the maximum sample) replace failed
    organizations of the same structure, in order; the cap in force during a run is the registered target (8.3).
    """
    d = cfg["design"]
    n = n_per_structure or d["orgs_per_structure"]
    bs = d["allocation_block_size"]
    assert bs % 2 == 0, "block size must be even"
    rng = random.Random(d["seeds"]["allocation"])
    rows, k = [], 0
    sizes = [bs] * (2 * n // bs) + ([2 * n % bs] if 2 * n % bs else [])   # a final smaller block only in smoke tests
    for b, size in enumerate(sizes):
        block = ["hierarchy"] * (size // 2) + ["polyarchy"] * (size // 2)
        rng.shuffle(block)
        for s in block:
            k += 1
            rows.append({"org_id": f"org{k:03d}", "structure": s, "block": b + 1, "position": k, "reserve": 0})
    for s in d["structures"]:
        for r in range(1, d["reserve_orgs_per_structure"] + 1):
            rows.append({"org_id": f"rsv-{s}-{r:02d}", "structure": s, "block": 0, "position": 0, "reserve": r})
    return rows


def write_allocation(rows: list[dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def read_jsonl(path: Path) -> list[dict]:
    return read_records(path)      # skips, with a warning, a line left incomplete by an interrupted write


def append_jsonl(path: Path, rec: dict):
    start_on_new_line(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(scrub(json.dumps(rec, ensure_ascii=False)) + "\n")


# ----------------------------------------------------------------------------- generation
def run_org(org: dict, backend, log: CallLog, prompts, cfg: dict, arm: str) -> dict:
    """One organization: four role calls. Hierarchy = seniority order, each junior reads every
    senior's stance and reasoning; polyarchy = the same calls with no peer information.
    A role whose call fails after the registered attempts ends the organization (no junior is
    ever shown an incomplete chain)."""
    order = prompts.roles["order"]
    seniors, roles_out = [], []
    vcfg, retries = cfg["validation"], cfg["retries"]
    n_prop = cfg["design"]["proposals_per_role"]
    for role in order:
        peer = list(seniors) if org["structure"] == "hierarchy" else None
        prompt = P.generation_prompt(prompts, role, peer)
        call_id = f"gen:{org['org_id']}:{role}"
        meta = {"stage": "generation", "arm": arm, "org_id": org["org_id"], "structure": org["structure"], "role": role}
        obj = run_call(backend, log, call_id, meta, prompt, with_count(GENERATION_SCHEMA, "proposals", n_prop), "generation",
                       lambda o: validate_generation(o, vcfg, n_prop), retries, seed_parts=(arm, call_id))
        if org["structure"] == "hierarchy":
            seniors.append({"role": role, "stance": obj["stance"], "reasoning": obj["reasoning"]})
        roles_out.append({"role": role, "call_id": call_id, "stance": obj["stance"], "reasoning": obj["reasoning"],
                          "proposals": obj["proposals"], "n_seniors_seen": len(peer or [])})
    return {"org_id": org["org_id"], "structure": org["structure"], "block": org["block"],
            "reserve": org["reserve"], "replaces": org.get("replaces"), "roles": roles_out}


def run_generation(cfg, prompts, backend, outdir: Path, arm: str, alloc: list[dict], concurrency: int,
                   n_target: int, progress=print):
    """Run organizations in allocation order until n_target complete per structure.
    Failed organizations are recorded and replaced by the next reserve of the same structure, which takes the
    failed organization's block (PROTOCOL.md 8.3)."""
    log = CallLog(outdir / "calls_generation.jsonl")
    orgs_path, fail_path = outdir / "orgs.jsonl", outdir / "org_failures.jsonl"
    done = {o["org_id"] for o in read_jsonl(orgs_path)}
    failed = {o["org_id"] for o in read_jsonl(fail_path)}
    main = []
    for s in cfg["design"]["structures"]:          # the first n_target of each structure, in allocation order
        main += [o for o in alloc if not o["reserve"] and o["structure"] == s][:n_target]
    main.sort(key=lambda o: o["position"])
    reserves = {s: [o for o in alloc if o["reserve"] and o["structure"] == s] for s in cfg["design"]["structures"]}

    def n_fail(s):
        return sum(1 for o in alloc if o["structure"] == s and o["org_id"] in failed)

    def check_cap():
        for s in reserves:
            cap = min(n_target, len(reserves[s]))      # one replacement per planned organization (PROTOCOL.md 8.3)
            if n_fail(s) > cap:
                raise ReserveExhausted(
                    f"{s}: {n_fail(s)} failed organizations exceed the {cap} replacements allowed (one per planned "
                    "organization); the run stops here and the problem is reported (PROTOCOL.md 8.3)")

    def needed_reserves(s):
        """The reserves in use, each carrying the block of the organization it replaces (in the order the
        failures were recorded, so a resumed run assigns the same blocks) and the id it replaces."""
        order = [f["org_id"] for f in read_jsonl(fail_path) if f.get("structure") == s]
        block_of = {o["org_id"]: o["block"] for o in alloc}
        out = []
        for r, fid in zip(reserves[s], order):
            block_of[r["org_id"]] = block_of.get(fid, 0)
            out.append({**r, "block": block_of[fid], "replaces": fid})
        return out

    check_cap()

    while True:
        queue = [o for o in main if o["org_id"] not in done and o["org_id"] not in failed]
        for s in reserves:
            queue += [o for o in needed_reserves(s) if o["org_id"] not in done and o["org_id"] not in failed]
        if not queue:
            break
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs = {ex.submit(run_org, o, backend, log, prompts, cfg, arm): o for o in queue}
            for fut in as_completed(futs):
                o = futs[fut]
                try:
                    rec = fut.result()
                    append_jsonl(orgs_path, rec)
                    done.add(o["org_id"])
                    progress(f"  org {o['org_id']} ({o['structure']}) complete [{len(done)} done]")
                except Failed as e:
                    append_jsonl(fail_path, {"org_id": o["org_id"], "structure": o["structure"], "error": str(e)})
                    failed.add(o["org_id"])
                    progress(f"  org {o['org_id']} FAILED: {e}")
                    try:
                        check_cap()
                    except ReserveExhausted:
                        ex.shutdown(wait=False, cancel_futures=True)
                        raise
                except Abort:
                    ex.shutdown(wait=False, cancel_futures=True)   # stop now; queued organizations are not started
                    raise
    return registered_orgs(cfg, outdir, alloc, n_target)


def registered_orgs(cfg, outdir: Path, alloc: list[dict], n_target: int) -> list[dict]:
    """The analysis sample: per structure, the completed main organizations in allocation order,
    then completed reserves in reserve order, up to n_target."""
    recs = {o["org_id"]: o for o in read_jsonl(outdir / "orgs.jsonl")}
    out = []
    for s in cfg["design"]["structures"]:
        ordered = [o for o in alloc if o["structure"] == s and not o["reserve"]] + \
                  [o for o in alloc if o["structure"] == s and o["reserve"]]
        ok = [recs[o["org_id"]] for o in ordered if o["org_id"] in recs]
        out += ok[:n_target]
    return out


def proposals_of(orgs: list[dict]) -> list[dict]:
    rows = []
    for o in orgs:
        for r in o["roles"]:
            for j, p in enumerate(r["proposals"], 1):
                rows.append({"proposal_id": f"{o['org_id']}-{r['role']}-{j}", "org_id": o["org_id"],
                             "structure": o["structure"], "role": r["role"], "slot": j,
                             "text": P.proposal_text(p), "n_words": len(P.proposal_text(p).split()), **p})
    return rows


def blind_ids(cfg, proposals: list[dict], wave: int = 1) -> dict:
    """Opaque ids (P1001...) from a seeded permutation of the sorted proposal ids. An extension wave
    (PROTOCOL.md 6.4) gets its own permutation and its own number range (P6001... for wave 2), so the
    ids of the first wave never change when organizations are added. Ids have no leading zeros, which a
    model may drop when it copies an id back."""
    ids = sorted(p["proposal_id"] for p in proposals)
    assert len(ids) < 5000, "a wave must have fewer than 5,000 proposals (id ranges of waves must not overlap)"
    rng = random.Random(cfg["design"]["seeds"]["judge_blind_ids"] + (wave - 1))
    rng.shuffle(ids)
    off = 1000 + 5000 * (wave - 1)
    return {pid: f"P{off + i + 1}" for i, pid in enumerate(ids)}


def waves_of(proposals: list[dict], waves: list[set] | None) -> list[list[dict]]:
    """Split the proposals into waves (lists of proposal ids). None = one wave with everything.
    Proposals not named in any wave form a final wave of their own."""
    if not waves:
        return [list(proposals)]
    out, seen = [], set()
    for w in waves:
        out.append([p for p in proposals if p["proposal_id"] in w])
        seen |= set(w)
    rest = [p for p in proposals if p["proposal_id"] not in seen]
    if rest:
        out.append(rest)
    return [w for w in out if w]


# ----------------------------------------------------------------------------- batched stages
def _batches(ids: list[str], seed: int, size: int) -> list[list[str]]:
    ids = sorted(ids)
    random.Random(seed).shuffle(ids)
    return [ids[i:i + size] for i in range(0, len(ids), size)]


def _run_batched(jobs, backend, log, concurrency, progress, label):
    """jobs: list of (key, fn). Returns {key: result or Exception}."""
    out = {}
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(fn): key for key, fn in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            key = futs[fut]
            try:
                out[key] = fut.result()
            except Failed as e:
                out[key] = e
            except Abort:
                ex.shutdown(wait=False, cancel_futures=True)   # stop now; queued calls are not started
                raise
            if i % 25 == 0 or i == len(futs):
                progress(f"  {label}: {i}/{len(futs)} calls")
    return out


def _with_singles(backend, log, call_id, meta, build_prompt, schema, name, item_check, key, ids, retries, seed_parts):
    """A batch call; if it fails after the registered attempts, each item is sent alone
    (registered fallback; a call that already holds one item has no fallback: its registered attempts are its last).
    Returns {blind_id: item or None}."""
    try:
        obj = run_call(backend, log, call_id, meta, build_prompt(ids), with_count(schema, key, len(ids)), name,
                       lambda o: validate_items(o, key, ids, item_check), retries, seed_parts=seed_parts + (call_id,))
        return {it["id"]: it for it in obj[key]}
    except Failed:
        if len(ids) == 1:
            return {ids[0]: None}
        res = {}
        for bid in ids:
            cid = f"{call_id}:single:{bid}"
            try:
                obj = run_call(backend, log, cid, {**meta, "fallback_single": True, "blind_ids": [bid]}, build_prompt([bid]),
                               with_count(schema, key, 1), name,
                               lambda o, b=bid: validate_items(o, key, [b], item_check), retries,
                               seed_parts=seed_parts + (cid,))
                res[bid] = obj[key][0]
            except Failed:
                res[bid] = None
        return res


def eval_suffix(arm: str, evaluator: str | None) -> str:
    """File-name suffix that says who screened: '' when an arm screens its own proposals (calls_evaluation.jsonl,
    votes.jsonl), '_<evaluator>' otherwise (calls_evaluation_gemma.jsonl, votes_gemma.jsonl). A screening by
    another model therefore never resumes from, or overwrites, another evaluator's log."""
    return "" if evaluator in (None, arm) else f"_{evaluator}"


def run_evaluation(cfg, prompts, backend, outdir: Path, arm: str, proposals: list[dict], concurrency: int, progress=print,
                   waves: list[set] | None = None, evaluator: str | None = None):
    """Every role screens every proposal: per role its own seeded order and batch partition.
    waves: proposal ids of the first wave (and later waves) when the sample was extended (6.4); each wave
    is batched on its own, so the calls of an earlier wave are never re-partitioned or repeated.
    evaluator: the arm whose model screens (default: the arm itself). Orders and batches do not depend on the
    evaluator, so every evaluator screens the same batches in the same order (cross-screening, PROTOCOL.md 7.4)."""
    sfx = eval_suffix(arm, evaluator)
    log = CallLog(outdir / f"calls_evaluation{sfx}.jsonl")
    size, retries = cfg["evaluation"]["batch_size"], cfg["retries"]
    jobs, back = [], {}
    for w, props_w in enumerate(waves_of(proposals, waves), 1):
        bmap = blind_ids(cfg, props_w, w)
        text = {bmap[p["proposal_id"]]: p["text"] for p in props_w}
        back.update({v: k for k, v in bmap.items()})
        tag = "" if w == 1 else f"w{w}:"
        for ri, role in enumerate(prompts.roles["order"]):
            seed = cfg["design"]["seeds"]["evaluation_order"] + ri + 1000 * (w - 1)
            for bi, ids in enumerate(_batches(list(text), seed, size), 1):
                call_id = f"eval:{tag}{role}:{bi:04d}"
                meta = {"stage": "evaluation", "arm": arm, "evaluator": evaluator or arm, "role": role, "batch": bi,
                        "wave": w, "blind_ids": ids}
                build = (lambda r, tx: (lambda idl: P.evaluation_prompt(prompts, r, [{"id": i, "text": tx[i]} for i in idl])))(role, text)
                jobs.append(((w, role, bi), (lambda c=call_id, m=meta, b=build, i=ids: _with_singles(
                    backend, log, c, m, b, EVALUATION_SCHEMA, "evaluation", check_vote, "screenings", i, retries,
                    (arm,) if not sfx else (arm, "screened-by", evaluator)))))
    random.Random(cfg["design"]["seeds"]["schedule"]).shuffle(jobs)      # roles and proposals interleaved in time (9)
    res = _run_batched(jobs, backend, log, concurrency, progress, f"evaluation by {evaluator or arm}")
    votes = []
    for (w, role, bi), r in sorted(res.items()):
        for bid, it in r.items():
            votes.append({"proposal_id": back[bid], "blind_id": bid, "role": role, "batch": bi, "wave": w,
                          "decision": it["decision"] if it else None, "promise": it["promise"] if it else None,
                          "rationale": it["rationale"] if it else None})
    _write_jsonl(outdir / f"votes{sfx}.jsonl", votes)
    return votes


def run_judge(cfg, prompts, backend, outdir: Path, arm: str, judge: str, proposals: list[dict], concurrency: int, progress=print,
              waves: list[set] | None = None, passes: int | None = None):
    """Readings (passes) 1..passes of every proposal by one judge; default the registered floor (judging.readings.floor).
    As registered (PROTOCOL.md 4.4): one proposal per call (judging.batch_size: 1), and one call rates all six
    subscales, the three dimensions in a random order, each followed by its two subscales in a random order
    (prompts.judge_plan: seeded by the proposal and the reading; recorded in the call and in the ratings row). In every
    reading the calls run in a seeded random order (judge_pass_k). A backend that answers in batches (the second judge,
    the Anthropic Batch API) receives every pending call of the stage in one batch, under the same attempt rules.
    Resumable: a later call with a larger `passes` (the number the readings rule decided) adds only the missing
    readings; completed calls are never repeated. One row per proposal and reading; a subscale whose call failed after
    the registered attempts is None in the row (missing_subscales lists it); a row with no subscale is marked missing."""
    passes = passes or cfg["judging"]["readings"]["floor"]
    log = CallLog(outdir / f"calls_judge_{judge}.jsonl")
    size, retries = cfg["judging"]["batch_size"], cfg["retries"]
    jobs, specs, back, plans = [], [], {}, {}
    for w, props_w in enumerate(waves_of(proposals, waves), 1):
        bmap = blind_ids(cfg, props_w, w)
        text = {bmap[p["proposal_id"]]: p["text"] for p in props_w}
        back.update({v: k for k, v in bmap.items()})
        tag = "" if w == 1 else f"w{w}:"
        for k in range(1, passes + 1):
            seed = cfg["design"]["seeds"][f"judge_pass_{k}"] + 1000 * (w - 1)
            for bi, ids in enumerate(_batches(list(text), seed, size), 1):
                call_id = f"judge:{judge}:{tag}{k}:{bi:04d}"
                plan = P.judge_plan(cfg, ids[0], k)
                order = tuple(x for _, pair in plan for x in pair)
                plans[(w, k, bi)] = (plan, ids)
                meta = {"stage": "judge", "arm": arm, "judge": judge, "pass": k, "batch": bi, "wave": w, "blind_ids": ids,
                        "dimension_order": [d for d, _ in plan], "subscale_order": list(order)}
                build = (lambda tx, pl: (lambda idl: P.judge_prompt_all(prompts, [{"id": i, "text": tx[i]} for i in idl], pl)))(text, plan)
                check = (lambda o: (lambda it: check_subscales(it, o)))(order)
                schema = judge_schema_for(order)
                if getattr(backend, "batch", False):
                    specs.append({"call_id": call_id, "meta": meta, "prompt": build(ids),
                                  "schema": with_count(schema, "ratings", len(ids)), "name": "judge",
                                  "validate": (lambda i, ck: (lambda o: validate_items(o, "ratings", i, ck)))(ids, check),
                                  "key": (w, k, bi), "ids": ids})
                else:
                    jobs.append(((w, k, bi), (lambda c=call_id, m=meta, b=build, i=ids, sc=schema, ck=check: _with_singles(
                        backend, log, c, m, b, sc, "judge", ck, "ratings", i, retries, (arm, judge)))))
    if specs:
        got = run_calls_batch(backend, log, specs, retries, progress)
        res = {sp["key"]: ({it["id"]: it for it in got[sp["call_id"]]["ratings"]} if got.get(sp["call_id"])
                           else {i: None for i in sp["ids"]}) for sp in specs}
    else:
        random.Random(cfg["design"]["seeds"]["schedule"] + 1).shuffle(jobs)   # readings and proposals interleaved in time (9)
        res = _run_batched(jobs, backend, log, concurrency, progress, f"judge {judge}")
    rows = []
    for (w, k, bi), r in sorted(res.items()):
        plan, ids = plans[(w, k, bi)]
        if isinstance(r, Exception):                  # an unexpected error in the call: its reading is missing, never silent
            r = {i: None for i in ids}
        for bid, it in r.items():
            row = {"proposal_id": back[bid], "blind_id": bid, "judge": judge, "pass": k, "wave": w, "call": bi,
                   "dimension_order": [d for d, _ in plan], "subscale_order": [x for _, pair in plan for x in pair]}
            for s_ in JUDGE_SCALES:
                row[s_] = it[s_] if it else None
                row[f"evidence_{s_}"] = it[f"{s_}_evidence"] if it else None
            missing = [s_ for s_ in JUDGE_SCALES if row.get(s_) is None]
            if len(missing) == len(JUDGE_SCALES):
                row["missing"] = True
            elif missing:
                row["missing_subscales"] = missing
            rows.append(row)
    rows.sort(key=lambda r: (r["wave"], r["pass"], r["blind_id"]))
    _write_jsonl(outdir / f"ratings_{judge}.jsonl", rows)
    return rows


def _write_jsonl(path: Path, rows: list[dict]):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(scrub(json.dumps(r, ensure_ascii=False)) + "\n")
