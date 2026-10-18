"""Checks before any registered call: credentials, model identity, local weights, schema round-trip.

A preflight call is a minimal schema check ("Reply with ok") — it is not part of the study, never
uses the study's prompts, and is logged to data/<arm>/preflight.jsonl.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .backends import make_backend
from .config import arm_dir, expand, scrub, sha256_file

PING_SCHEMA = {"type": "object", "properties": {"ok": {"type": "string"}}, "required": ["ok"], "additionalProperties": False}


def _ping(name, spec, mock) -> tuple[bool, dict]:
    be = make_backend(spec, mock=mock)
    if mock:
        return True, {"model": "mock"}
    r = be.complete('Reply with the JSON object {"ok": "yes"}.', PING_SCHEMA, "ping")
    info = {"requested": spec["model"], "returned": r.model_returned, "stop_reason": r.stop_reason,
            "error": r.error, "text": r.text, "usage": r.usage, "describe": be.describe()}
    # a schema round-trip: a completed answer (not refused, not cut off) that parses to the schema's object with a
    # non-empty string; the wording of the string is not checked (a model that answers "Yes" is not a broken server)
    try:
        obj = json.loads(r.text or "")
        ok = (r.ok and r.stop_reason not in ("refusal", "max_tokens", "length") and isinstance(obj, dict)
              and set(obj) == {"ok"} and isinstance(obj["ok"], str) and bool(obj["ok"].strip()))
    except (json.JSONDecodeError, TypeError):
        ok = False
    if ok and spec["backend"] in ("anthropic", "anthropic_batch"):
        # the API must report the configured model id
        ok = (r.model_returned or "").startswith(spec["model"])
    return ok, info


def lmstudio_info() -> dict:
    """The local server's loaded-model settings and inference engines (LM Studio's own CLI)."""
    import subprocess
    lms = expand("~/.lmstudio/bin/lms")
    out = {}
    try:  # the application's own version (its engines are listed below); informational
        import plistlib
        with open("/Applications/LM Studio.app/Contents/Info.plist", "rb") as f:
            out["app_version"] = plistlib.load(f).get("CFBundleShortVersionString")
    except Exception as e:  # noqa: BLE001
        out["app_version"] = f"unavailable: {e}"
    for key, args in (("loaded_models", ["ps", "--json"]), ("runtimes", ["runtime", "ls"])):
        try:
            r = subprocess.run([str(lms), *args], capture_output=True, text=True, timeout=60)
            out[key] = json.loads(r.stdout) if key == "loaded_models" else r.stdout.strip().splitlines()
        except Exception as e:  # noqa: BLE001 - informational only
            out[key] = f"unavailable: {e}"
    return out


def weights_hash(weights_dir: str) -> dict:
    d = expand(weights_dir)
    return {p.name: sha256_file(p) for p in sorted(d.iterdir()) if p.is_file()}


def registered_files() -> dict:
    """{LM Studio identifier: {file name: SHA-256}} registered in config/model_files.json ({} if absent)."""
    from .config import ROOT
    f = ROOT / "config" / "model_files.json"
    return {k: v["files"] for k, v in json.loads(f.read_text()).items()} if f.exists() else {}


def loaded_identifiers() -> dict[str, str] | None:
    """{identifier: path relative to the models folder} of the models LM Studio has loaded now (None if it cannot be asked)."""
    info = lmstudio_info().get("loaded_models")
    if not isinstance(info, list):
        return None
    return {m.get("identifier"): m.get("path", "") for m in info if m.get("identifier")}


def loaded_settings() -> dict[str, dict] | None:
    """{identifier: {"context_length", "parallel"}} of the models LM Studio has loaded now (None if it cannot be asked).
    LM Studio's own keys in `lms ps --json` are contextLength and parallel."""
    info = lmstudio_info().get("loaded_models")
    if not isinstance(info, list):
        return None
    return {m.get("identifier"): {"context_length": m.get("contextLength"), "parallel": m.get("parallel")}
            for m in info if m.get("identifier")}


def recipe_mismatch(spec: dict, loaded: dict | None) -> list[str]:
    """How the loaded model differs from its load recipe in the configuration (`load`); [] if it agrees or if the
    model has no recipe. A model loaded with other settings would still answer, so only this check catches it."""
    want = spec.get("load")
    if not want:
        return []
    if not loaded:
        return ["context length and slots could not be read (`lms ps --json`)"]
    return [f"{k} {loaded.get(k)}, recipe {v}" for k, v in want.items() if loaded.get(k) != v]


def served_folder_ok(spec: dict, loaded_path: str) -> bool:
    """The folder LM Studio loaded must be the configured weights_dir (look-alike folders exist on this machine)."""
    want = spec["weights_dir"].rstrip("/").split("/.lmstudio/models/")[-1].lower()
    got = (loaded_path or "").lower()
    return got == want or got.startswith(want + "/")


def line_models(cfg, arm: str) -> dict:
    """Every model the line needs: the writers (the arm), the registered evaluator, and the two registered judges."""
    ev = cfg["arms"][arm].get("evaluator", arm)
    out = {f"writer:{arm}": cfg["arms"][arm], f"evaluator:{ev}": cfg["arms"][ev]}
    for role in ("primary", "second"):
        j = cfg["judging"].get(role)
        if j:
            out[f"judge-{role}:{j}"] = cfg["judges"][j]
    return out


def preflight(cfg, prompts, arm: str, mock: bool = False, only: str | None = None, detail: dict | None = None,
              smoke: bool = False) -> bool:
    """Check every model of the experiment that can be checked now. Local models are served one at a time, so a local
    model is checked (one tiny schema call, the identifier returned, the folder served, the context length and
    slots against its load recipe, the weights' hashes) only while it is loaded; run preflight again after loading
    the model of the next stage. API models need their key. `only`: check just this LM Studio identifier (the model
    loaded for the next step), and fail if it is not loaded. `detail`, if given, receives needs_person: True when a
    failure is one that no reload can fix (the served model is not the registered one)."""
    out, ok_all, checked = {"time_utc": datetime.now(timezone.utc).isoformat(), "arm": arm}, True, 0
    person = False
    loaded = {} if mock else loaded_identifiers()
    if loaded is None:
        print("FAIL: LM Studio cannot be reached (`lms server start`; `lms ps`)")
        loaded, ok_all = {}, False
    settings = {} if mock else (loaded_settings() or {})
    models = line_models(cfg, arm)
    if only is not None:
        models = {n: sp for n, sp in models.items() if sp.get("model") == only}
        if not models:
            print(f"FAIL: no model of this experiment is served as '{only}' (config/study.yaml)")
            ok_all, person = False, True
    for name, spec in models.items():
        local = spec["backend"] == "openai_compatible"
        if name.startswith("judge-second") and not local and only is None:
            # the second judge rates the archived proposals through the API after the offline run (PROTOCOL.md 4.5);
            # its key and model are checked when that step runs, not before the local stages. Named with --only (its
            # model id), it is checked now: one tiny request through the same path (a batch of one for the Batch API),
            # which shows before filing that the key, the account, and the model id work.
            print(f"--   {name}: through the API after the offline run; checked when it runs (or now: --only {spec['model']})"); continue
        if not mock and spec["backend"] in ("anthropic", "anthropic_batch") and not os.environ.get("ANTHROPIC_API_KEY"):
            print(f"FAIL {name}: ANTHROPIC_API_KEY is not set"); ok_all = False; continue
        if local and not mock and spec["model"] not in loaded:
            if only is not None:
                print(f"FAIL {name}: '{spec['model']}' is not loaded"); ok_all = False
            else:
                print(f"--   {name}: '{spec['model']}' is not loaded now; load it and run preflight again before its stage")
            out[name] = {"requested": spec["model"], "checked": False}
            continue
        ok, info = _ping(name, spec, mock)
        if ok and local and not mock:
            if info.get("returned") != spec["model"]:        # LM Studio returns the identifier it serves
                print(f"FAIL {name}: the server answered as '{info.get('returned')}', not '{spec['model']}'")
                ok, person = False, True
            if not served_folder_ok(spec, loaded.get(spec["model"], "")):
                print(f"FAIL {name}: LM Studio loaded '{loaded.get(spec['model'])}', not {spec['weights_dir']}")
                ok, person = False, True
            bad = recipe_mismatch(spec, settings.get(spec["model"]))
            if bad:
                print(f"FAIL {name}: loaded with {'; '.join(bad)} (reload it with the RUNBOOK's command)")
                ok = False
        if local and not mock:
            info["weights_sha256"] = weights_hash(spec["weights_dir"])
            reg = registered_files().get(spec["model"])
            if not reg:
                print(f"FAIL {name}: no registered files for {spec['model']} in config/model_files.json")
                ok, person = False, True
            elif reg != info["weights_sha256"]:
                bad = sorted(k for k in set(reg) | set(info["weights_sha256"]) if reg.get(k) != info["weights_sha256"].get(k))
                print(f"FAIL {name}: files differ from config/model_files.json: {bad}")
                ok, person = False, True
        out[name] = {**info, "checked": True}
        checked += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}: requested {spec['model']} returned {info.get('returned')} "
              f"{info.get('error') or ''}" + (f"; {len(info['weights_sha256'])} files hashed in {spec['weights_dir']}"
                                             if info.get("weights_sha256") else ""))
        ok_all &= ok
    if not mock:
        out["lmstudio"] = lmstudio_info()
    if checked == 0 and only is None:
        print("FAIL: no model of this experiment is loaded, so nothing could be checked"); ok_all = False
    if detail is not None:
        detail["needs_person"] = person
    with open(arm_dir(arm + ("-mock" if mock else ""), smoke=smoke or mock) / "preflight.jsonl", "a", encoding="utf-8") as f:
        f.write(scrub(json.dumps(out, ensure_ascii=False)) + "\n")
    print("PREFLIGHT PASSED" if ok_all else "PREFLIGHT FAILED")
    return ok_all
