"""Manifest (hashes of everything that produced the data) and progress/cost status."""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from .config import expand, protocol_hashes, scrub, sha256_file
from .stages import read_jsonl

# USD per million tokens (input, output), list prices; used only for the status estimate
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.1, 0.5)}
# list prices; the Batch API bills half (PROTOCOL.md 5.4)


def _q(*args) -> str:
    import subprocess
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return (r.stdout or r.stderr).strip()
    except Exception as e:  # noqa: BLE001 - informational only
        return f"unavailable: {e}"


def machine_info() -> dict:
    """The computer and its network state, for the record (nothing here reaches a model)."""
    return {"hw_model": _q("sysctl", "-n", "hw.model"), "chip": _q("sysctl", "-n", "machdep.cpu.brand_string"),
            "memory_bytes": _q("sysctl", "-n", "hw.memsize"), "macos": _q("sw_vers", "-productVersion"),
            "build": _q("sw_vers", "-buildVersion"), **network_state()}


def network_state() -> dict:
    """Wi-Fi power and the Ethernet link status (the registered run has both off; PROTOCOL.md 5.5)."""
    return {"wifi": _q("networksetup", "-getairportpower", "en1"),
            "ethernet_en0": _q("sh", "-c", "ifconfig en0 | grep status")}


def stage_times(outdir: Path) -> dict:
    """First and last attempt time of every call log, UTC, and the number of attempts."""
    out = {}
    for f in sorted(outdir.glob("calls_*.jsonl")):
        ts = sorted(r["time_utc"] for r in read_jsonl(f) if r.get("time_utc"))
        if ts:
            out[f.name] = {"first_utc": ts[0], "last_utc": ts[-1], "attempts": len(ts)}
    return out


def write_manifest(cfg, arm: str, outdir: Path, code: dict, mock: bool = False) -> str:
    import anthropic, numpy, openai, scipy
    m = {"written_utc": datetime.now(timezone.utc).isoformat(), "arm": arm,
         "protocol_sha256": protocol_hashes(), "code_sha256": code,
         "data_sha256": {p.name: sha256_file(p) for p in sorted(outdir.glob("*")) if p.is_file() and p.name != "manifest.json"},
         "versions": {"python": platform.python_version(), "anthropic": anthropic.__version__, "openai": openai.__version__,
                      "numpy": numpy.__version__, "scipy": scipy.__version__, "platform": platform.platform()},
         "machine": machine_info(), "stage_times": stage_times(outdir), "config": cfg}
    from .preflight import line_models, lmstudio_info, weights_hash
    if not mock:
        m["weights_sha256"] = {name: weights_hash(spec["weights_dir"]) for name, spec in line_models(cfg, arm).items()
                               if spec["backend"] == "openai_compatible" and expand(spec["weights_dir"]).exists()}
        m["lmstudio"] = lmstudio_info()
    models = {}
    for f in outdir.glob("calls_*.jsonl"):
        for r in read_jsonl(f):
            models.setdefault(f.name, set()).add(r.get("model_returned"))
    m["models_returned"] = {k: sorted(x for x in v if x) for k, v in models.items()}
    path = outdir / "manifest.json"
    path.write_text(scrub(json.dumps(m, indent=2, ensure_ascii=False)))
    return f"wrote {path}"


def attempts_report(outdir: Path, write_audit: bool = False) -> dict:
    """Per call log: attempts that completed, content failures among them, first-attempt failures, outcomes
    obtained on a retry, exhausted logical calls, and the failure reasons (PROTOCOL.md 7.3, 8.1). With write_audit,
    every content-failed attempt is written to results/failed_attempts_<log>.jsonl next to the answer that the
    same logical call later gave (the reasoning text of the failed attempt included), for the audit of whether
    failures depend on the answer the model was about to give."""
    out = {}
    for f in sorted(outdir.glob("calls_*.jsonl")):
        recs = read_jsonl(f)
        attempts = [r for r in recs if "exhausted" not in r and (r.get("valid") or str(r.get("error") or "").startswith("invalid"))]
        failures = [r for r in attempts if not r.get("valid")]
        first = [r for r in attempts if r.get("content_attempt") == 1]
        valid = [r for r in attempts if r.get("valid")]
        reasons = {}
        for r in failures:
            key = str(r.get("error") or "")[:60]
            reasons[key] = reasons.get(key, 0) + 1
        by_structure = {}
        for r in attempts:
            s = r.get("structure")
            if s:
                d = by_structure.setdefault(s, {"attempts": 0, "content_failures": 0})
                d["attempts"] += 1
                d["content_failures"] += int(not r.get("valid"))
        out[f.name] = {"attempts_completed": len(attempts), "content_failures": len(failures),
                       "content_failure_rate": len(failures) / len(attempts) if attempts else None,
                       "first_attempts": len(first), "first_attempt_failures": sum(1 for r in first if not r.get("valid")),
                       "valid_outcomes": len(valid), "outcomes_from_a_retry": sum(1 for r in valid if (r.get("content_attempt") or 1) > 1),
                       "exhausted_logical_calls": sum(1 for r in recs if r.get("exhausted")),
                       "failure_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])[:12]),
                       "by_structure": by_structure or None}
        if write_audit and failures:
            later = {}
            for r in valid:
                later[r["call_id"]] = r
            rows = []
            for r in failures:
                msg = ((r.get("response_raw") or {}).get("choices") or [{}])[0].get("message") or {}
                ok = later.get(r["call_id"])
                rows.append({"call_id": r["call_id"], "stage": r.get("stage"), "content_attempt": r.get("content_attempt"),
                             "error": r.get("error"), "stop_reason": r.get("stop_reason"),
                             "completion_tokens": (r.get("usage") or {}).get("completion_tokens"),
                             "reasoning_text": msg.get("reasoning_content") or msg.get("reasoning")
                             or (r.get("extra") or {}).get("thinking_summary")
                             or "\n".join(b.get("thinking", "") for b in (r.get("response_raw") or {}).get("content", [])
                                          if b.get("type") == "thinking") or None,
                             "text": r.get("text"),
                             "later_valid_attempt": ok.get("content_attempt") if ok else None,
                             "later_parsed": ok.get("parsed") if ok else None})
            (outdir / "results").mkdir(exist_ok=True)
            path = outdir / "results" / f"failed_attempts_{f.stem}.jsonl"
            with open(path, "w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(scrub(json.dumps(row, ensure_ascii=False)) + "\n")
            out[f.name]["audit_file"] = str(path.relative_to(outdir))
    return out


def status(cfg, outdir: Path, n: int) -> str:
    lines = [f"data: {outdir}"]
    orgs = read_jsonl(outdir / "orgs.jsonl")
    fails = read_jsonl(outdir / "org_failures.jsonl")
    for s in cfg["design"]["structures"]:
        lines.append(f"  {s}: {sum(o['structure'] == s for o in orgs)} complete / {n} registered; "
                     f"{sum(f['structure'] == s for f in fails)} failed")
    cost = 0.0
    for f in sorted(outdir.glob("calls_*.jsonl")):
        recs = read_jsonl(f)
        tin = sum((r.get("usage") or {}).get("input_tokens", 0) or (r.get("usage") or {}).get("prompt_tokens", 0) for r in recs)
        tout = sum((r.get("usage") or {}).get("output_tokens", 0) or (r.get("usage") or {}).get("completion_tokens", 0) for r in recs)
        models = sorted({r.get("model_returned") for r in recs if r.get("model_returned")})
        model = models[0] if models else None
        pin, pout = next((v for k, v in PRICES.items() if model and model.startswith(k)), (0.0, 0.0))
        c = tin / 1e6 * pin + tout / 1e6 * pout
        cost += c
        ids = {r["call_id"] for r in recs if "call_id" in r}
        done = {r["call_id"] for r in recs if r.get("valid")}
        exhausted = {r["call_id"] for r in recs if r.get("exhausted")}
        share = 100 * len(exhausted) / max(1, len(ids))
        attempts = [r for r in recs if "exhausted" not in r and (r.get("valid") or str(r.get("error") or "").startswith("invalid"))]
        n_fail = sum(1 for r in attempts if not r.get("valid"))
        rate = n_fail / len(attempts) if attempts else 0.0
        lines.append(f"  {f.name}: {len(ids)} logical calls ({len(done)} done, {len(exhausted)} exhausted = {share:.1f}%); "
                     f"{len(attempts)} attempts completed, {n_fail} content failures = {100 * rate:.1f}%"
                     f"; tokens in {tin:,} out {tout:,}; ~${c:,.2f}; models returned {models}")
    lines.append(f"  estimated cost so far: ${cost:,.2f}")
    return "\n".join(lines)
