"""The one-command runner: content failures are counted and never stop the run (PROTOCOL.md 8.1);
recovery, registered stops, and the order of the steps."""
import subprocess

import pytest

from np_registered import run_all
from np_registered.config import load_config


def test_high_failure_counts_are_recorded_and_never_stop_the_run(monkeypatch, tmp_path):
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    run = run_all.Run(smoke=1, mock=True)

    class Done:
        returncode, stderr = 0, ""
        stdout = "  calls_generation.jsonl: 8 logical calls (6 done, 2 exhausted = 25.0%); 20 attempts completed, 14 content failures = 70.0%\n"

    run_all.scrub("prime")                  # the privacy scrub reads the computer's names once, before subprocess is faked
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Done())
    run.record_counts("generate main", "qwen38")                       # no SystemExit
    assert run.state["state"] != "STOPPED" and "14 content failures" in run.log_path.read_text()


def test_retryable_status_covers_context_pool_overflow():
    from np_registered.backends import retryable_status
    assert retryable_status(400, "Error code: 400 - Engine protocol predict stream returned an error: "
                                 "{\"code\":500,\"message\":\"Context size has been exceeded.\"}")
    assert retryable_status(400, "exceed_context_size_error: request (35367 tokens) exceeds the available context size")
    assert retryable_status(503, "service unavailable")
    assert not retryable_status(400, "invalid request: unknown field")
    assert not retryable_status(401, "unauthorized")


def _run(monkeypatch, tmp_path):
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    run = run_all.Run(smoke=1, mock=True)
    monkeypatch.setattr(run, "record_counts", lambda name, arm: None)
    monkeypatch.setattr(run, "restart_server", lambda: None)
    monkeypatch.setattr(run_all.time, "sleep", lambda s: None)
    return run


@pytest.mark.parametrize("rc, phrase", [(3, "registered stop"), (1, "no restart can fix"), (7, "no restart can fix")])
def test_step_stops_for_a_person_on_deterministic_exit_codes(monkeypatch, tmp_path, rc, phrase):
    run = _run(monkeypatch, tmp_path)
    monkeypatch.setattr(run, "np", lambda *a, **k: rc)
    with pytest.raises(SystemExit):
        run.step("generate main", None, ["generate", "--arm", "qwen38"])
    assert run.state["state"] == "STOPPED" and phrase in run.state["reason"]


@pytest.mark.parametrize("rc", [run_all.RC_TRANSPORT, run_all.RC_STALLED])
def test_step_recovers_on_transport_or_stall_then_stops(monkeypatch, tmp_path, rc):
    run = _run(monkeypatch, tmp_path)
    run.mock = False                                   # recovery is skipped in mock mode; exercise the real path
    monkeypatch.setattr(run, "load", lambda ident: None)
    calls = []
    monkeypatch.setattr(run, "np", lambda *a, **k: (calls.append(a), 0 if a[0] == "preflight" else rc)[1])
    with pytest.raises(SystemExit):
        run.step("generate main", "qwen38", ["generate", "--arm", "qwen38"])
    assert run.state["state"] == "STOPPED" and "six times" in run.state["reason"]
    assert sum(1 for a in calls if a[0] == "generate") == len(run_all.WAITS_MIN) + 1


def test_step_stops_when_preflight_says_the_model_is_not_the_registered_one(monkeypatch, tmp_path):
    run = _run(monkeypatch, tmp_path)
    run.mock = False
    monkeypatch.setattr(run, "load", lambda ident: None)
    monkeypatch.setattr(run, "np", lambda *a, **k: run_all.RC_REGISTERED_STOP if a[0] == "preflight" else 0)
    with pytest.raises(SystemExit):
        run.step("generate main", "qwen38", ["generate", "--arm", "qwen38"])
    assert "not the registered one" in run.state["reason"]


def test_step_marks_done_on_success(monkeypatch, tmp_path):
    run = _run(monkeypatch, tmp_path)
    monkeypatch.setattr(run, "np", lambda *a, **k: 0)
    run.step("generate main", None, ["generate", "--arm", "qwen38"])
    assert run.state["done"] == ["generate main:generate --arm qwen38"]


def test_preflight_only_reports_whether_a_person_is_needed(monkeypatch, tmp_path):
    from np_registered import preflight
    from np_registered.config import load_config, load_prompts
    cfg, pr = load_config(), load_prompts()
    monkeypatch.setattr(preflight, "loaded_identifiers", lambda: {})
    monkeypatch.setattr(preflight, "loaded_settings", lambda: {})
    monkeypatch.setattr(preflight, "lmstudio_info", lambda: {})
    monkeypatch.setattr(preflight, "arm_dir", lambda name, smoke=False: tmp_path)
    d = {}
    assert preflight.preflight(cfg, pr, "qwen38", only="qwen38", detail=d) is False and d["needs_person"] is False
    d = {}
    assert preflight.preflight(cfg, pr, "qwen38", only="no-such-model", detail=d) is False and d["needs_person"] is True


def test_newest_mtime_and_incremental_done_calls(tmp_path):
    import json
    f = tmp_path / "calls_generation.jsonl"
    assert run_all.newest_mtime(tmp_path) == 0.0
    f.write_text(json.dumps({"call_id": "gen:a", "valid": True, "latency_s": 10}) + "\n")
    assert run_all.newest_mtime(tmp_path) > 0
    assert run_all.done_calls(f)[0] == 1
    with open(f, "a") as h:
        h.write(json.dumps({"call_id": "gen:b", "valid": True, "latency_s": 30}) + "\n" + '{"call_id": "gen:c", "val')
    k, spc, _ = run_all.done_calls(f)
    assert k == 2 and spc == 20            # the torn last line is left for the next read


def test_lock_refuses_a_second_live_runner(monkeypatch, tmp_path):
    import os
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    first = run_all.Run(smoke=1, mock=True)
    first.take_lock()
    assert (tmp_path / "run.lock").read_text() == str(os.getpid())
    second = run_all.Run(smoke=1, mock=True)
    monkeypatch.setattr(os, "getpid", lambda: 999999)          # the second runner is another process
    with pytest.raises(SystemExit):
        second.take_lock()
    assert "another runner" in second.state["reason"]
    first._lock_file.close()                                 # the first runner exits before its metadata is stale
    (tmp_path / "run.lock").write_text("4194304")              # a stale lock from a process that is gone
    third = run_all.Run(smoke=1, mock=True)
    third.take_lock()
    assert (tmp_path / "run.lock").read_text() == "999999"


def test_interrupt_kills_the_running_step_and_records_the_stop(monkeypatch, tmp_path):
    import os
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    run = run_all.Run(smoke=1, mock=True)
    killed = []

    class Child:
        pid, returncode = 4242, None
        def send_signal(self, sig):
            killed.append(("pid", sig))
    run.child = Child()
    monkeypatch.setattr(os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(run_all.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as e:
        run.interrupt("Ctrl-C")
    assert e.value.code == 130 and killed and killed[0][0] == 4242
    assert run.state["state"] == "STOPPED" and "interrupted" in run.state["reason"]


def test_scrub_writes_home_paths_as_tilde(monkeypatch, tmp_path):
    from pathlib import Path
    home = str(Path.home())
    assert run_all.scrub(f"log: {home}/x/data/run.log") == "log: ~/x/data/run.log"
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    run = run_all.Run(smoke=1, mock=True)
    run.log(f"wrote {home}/something")
    run.save(state="STOPPED", reason=f"see {home}/data/run.log")
    assert home not in run.log_path.read_text() and home not in run_all.state_path().read_text()


def test_extension_target_and_panel_follow_the_blinded_check(tmp_path):
    """The planned counts of the panel grow with an experiment's extension.json (the first wave is 84)."""
    import json
    assert run_all.extension_target(tmp_path, 84) == 84
    (tmp_path / "extension.json").write_text(json.dumps({"target_per_structure": 120, "decision": "extend"}))
    assert run_all.extension_target(tmp_path, 84) == 120
    (tmp_path / "extension.json").write_text("not json")
    assert run_all.extension_target(tmp_path, 84) == 84
    cfg = run_all.load_config()
    assert run_all.planned_calls(cfg, 120)["generate"] == 120 * 2 * 4
    assert run_all.planned_calls(cfg, 120)["judge"] > run_all.planned_calls(cfg, 84)["judge"]
    # the judge plan follows the readings decision of that judge (the floor until readings-check writes the file)
    j = cfg["judging"]["primary"]
    assert run_all.readings_target(tmp_path, cfg, j) == cfg["judging"]["readings"]["floor"]
    (tmp_path / f"readings_{j}.json").write_text(json.dumps({"readings": 7}))
    assert run_all.readings_target(tmp_path, cfg, j) == 7
    assert run_all.planned_calls(cfg, 84, 7)["judge"] == 7 * run_all.planned_calls(cfg, 84, 1)["judge"]


def test_manifest_records_machine_network_and_stage_times(tmp_path):
    import json
    from np_registered import manifest as M
    info = M.machine_info()
    assert set(info) >= {"hw_model", "chip", "memory_bytes", "macos", "wifi", "ethernet_en0"}
    assert all(isinstance(v, str) for v in info.values())
    f = tmp_path / "calls_generation.jsonl"
    f.write_text("\n".join(json.dumps({"time_utc": t}) for t in ("2026-10-11T02:00:00", "2026-10-11T01:00:00")) + "\n")
    st = M.stage_times(tmp_path)
    assert st["calls_generation.jsonl"] == {"first_utc": "2026-10-11T01:00:00", "last_utc": "2026-10-11T02:00:00", "attempts": 2}


def _record_plan(monkeypatch, run):
    steps = []
    monkeypatch.setattr(run, "step", lambda name, model, args: steps.append((name, model, args)))
    monkeypatch.setattr(run_all, "panel_loop", lambda r: None)
    return steps


def _arm(args):
    return args[args.index("--arm") + 1] if "--arm" in args else None


def test_plan_finishes_the_main_experiment_first_and_analyzes_only_after_both_judges(monkeypatch, tmp_path):
    """PROTOCOL.md 4.5: the main experiment (generation, evaluation, primary judge, readings and extension checks) is
    complete before the second experiment starts; the offline part never analyzes when the second judge is an API
    model; `second-judge` rates both experiments with the second judge and only then writes manifests and analyses."""
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    cfg = load_config()
    r = run_all.Run(smoke=0, mock=True)
    steps = _record_plan(monkeypatch, r)
    r.go()
    arms = [_arm(a) for _, _, a in steps]
    assert arms.index("gemma") > max(i for i, a in enumerate(arms) if a == "qwen38")
    assert [a[0] for _, _, a in steps if _arm(a) == "qwen38"] == ["generate", "evaluate", "judge", "readings-check", "judge",
                                                                   "extend-check"]
    assert not any(a[0] in ("analyze", "manifest") for _, _, a in steps)
    assert all(a[a.index("--judge") + 1] == cfg["judging"]["primary"] for _, _, a in steps if a[0] == "judge")
    assert r.state["state"] == "OFFLINE FINISHED"
    r2 = run_all.Run(smoke=0, mock=True, online=True)
    steps2 = _record_plan(monkeypatch, r2)
    r2.go()
    kinds = [a[0] for _, _, a in steps2]
    judged = [i for i, k in enumerate(kinds) if k in ("judge", "readings-check")]
    assert judged and max(judged) < kinds.index("manifest") < kinds.index("analyze")
    assert all(a[a.index("--judge") + 1] == cfg["judging"]["second"] and m is None
               for _, m, a in steps2 if a[0] == "judge")
    assert {tuple(a) for _, _, a in steps2 if a[0] == "analyze"} == {
        ("analyze", "--arm", x, *extra) for x in run_all.LOCAL_ARMS for extra in ((), ("--judge", cfg["judging"]["second"]))}
    assert r2.state["state"] == "FINISHED"


def test_unreadable_counts_are_noted_and_the_run_continues(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setenv('NP_DATA_DIR', str(tmp_path))
    r = run_all.Run(smoke=1, mock=True)
    monkeypatch.setattr(run_all.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1, stdout='', stderr='status failed'))
    r.record_counts('generation', 'qwen38')                            # no SystemExit
    assert 'the run continues' in r.log_path.read_text()


def test_the_runner_sends_no_notifications():
    assert not hasattr(run_all, 'notify')
    assert 'osascript' not in (run_all.ROOT / 'src' / 'np_registered' / 'run_all.py').read_text()


def test_runner_lock_survives_stale_metadata_without_overwriting_state(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv('NP_DATA_DIR', str(tmp_path))
    first = run_all.Run(smoke=1, mock=True)
    first.take_lock()
    first.save(state='RUNNING', step='generation')
    before = run_all.state_path().read_bytes()
    (tmp_path / 'run.lock').write_text('4194304')
    second = run_all.Run(smoke=1, mock=True)
    try:
        with pytest.raises(SystemExit):
            second.take_lock()
        assert run_all.state_path().read_bytes() == before
    finally:
        if getattr(first, '_lock_file', None):
            first._lock_file.close()


def test_api_analyses_do_not_require_the_local_engine(monkeypatch, tmp_path):
    monkeypatch.setenv('NP_DATA_DIR', str(tmp_path))
    run = run_all.Run(smoke=0, mock=False, online=True)
    monkeypatch.setattr(run, 'lms', lambda *a, **k: pytest.fail('analysis invoked the local engine'))
    steps = []
    monkeypatch.setattr(run, 'step', lambda name, model, args: steps.append(args))
    run.analyses()
    assert sum(args[0] == 'manifest' for args in steps) == 2
    assert sum(args[0] == 'analyze' for args in steps) == 4


def test_step_drains_output_before_closing_the_run_log(monkeypatch, tmp_path):
    import threading
    import time
    monkeypatch.setenv('NP_DATA_DIR', str(tmp_path))
    run = run_all.Run(smoke=1, mock=True)
    finished = threading.Event()
    class Child:
        def wait(self, *args, **kwargs):
            finished.set()
            return 0
        @property
        def stdout(self):
            def lines():
                assert finished.wait(timeout=1)
                time.sleep(.02)
                yield b'last complete output line\n'
            return lines()
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: Child())
    assert run.np('status', '--arm', 'qwen38') == 0
    assert 'last complete output line' in run.log_path.read_text()


def test_record_of_the_run_is_time_stamped_and_archived(monkeypatch, tmp_path):
    """run.log lines carry a time stamp; LM Studio's server log of the session is copied (scrubbed) into the data
    folder, and a longer version of the same file replaces the copy; older files are left out."""
    import os
    import time as _time
    logs = tmp_path / "lms" / "2026-10"
    logs.mkdir(parents=True)
    old = logs / "2026-10-01.1.log"
    old.write_text("old\n")
    os.utime(old, (1, 1))
    new = logs / "2026-10-16.1.log"
    new.write_text(f"[2026-10-16 12:00:00][INFO] loaded from {os.path.expanduser('~')}/.lmstudio/models\n")
    monkeypatch.setattr(run_all, "LMS_LOGS", tmp_path / "lms")
    dest = tmp_path / "data" / "lmstudio_logs"
    assert run_all.archive_lmstudio_logs(_time.time() - 10, dest) == 1
    copy = dest / "2026-10" / "2026-10-16.1.log"
    assert "~/.lmstudio/models" in copy.read_text() and not (dest / "2026-10" / "2026-10-01.1.log").exists()
    assert run_all.archive_lmstudio_logs(_time.time() - 10, dest) == 0          # unchanged: not copied again
    _time.sleep(0.05)
    new.write_text(new.read_text() + "[2026-10-16 12:05:00][ERROR] slot failed\n")
    assert run_all.archive_lmstudio_logs(_time.time() - 10, dest) == 1
    assert "slot failed" in copy.read_text()
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path / "data"))
    run = run_all.Run(smoke=1, mock=True)
    run.log("hello")
    assert run.log_path.read_text().splitlines()[-1].startswith("[20")


def test_system_snapshot_never_fails(monkeypatch):
    snap = run_all.system_snapshot()
    assert {"time", "memory_free_percent", "swap", "load_avg", "disk_free_gb", "thermal", "lmstudio_loaded"} <= set(snap)


def test_zip_data_and_pack(tmp_path):
    """The data folder is zipped as one file outside data/, and pack writes compressed (and, above the limit, split)
    copies of the raw call logs next to untouched originals; joining the parts and gunzipping gives the original."""
    import gzip
    import json
    import zipfile
    data = tmp_path / "data"
    (data / "qwen38").mkdir(parents=True)
    (data / "run.log").write_text("started\n")
    big = (data / "qwen38" / "calls_generation.jsonl")
    big.write_text("".join(json.dumps({"call_id": i, "text": "x" * 200}) + "\n" for i in range(3000)))
    (data / "qwen38" / "orgs.jsonl").write_text("{}\n")
    out = run_all.zip_data(data, tmp_path / "archive", "offline")
    assert out.parent.name == "archive" and out.name.startswith("data_offline_") and out.suffix == ".zip"
    with zipfile.ZipFile(out) as z:
        assert set(z.namelist()) == {"data/run.log", "data/qwen38/calls_generation.jsonl", "data/qwen38/orgs.jsonl"}
    before = big.read_bytes()
    lines = run_all.pack_data(data, limit=4096)
    assert len(lines) == 1 and "parts" in lines[0]
    parts = sorted((data / "qwen38").glob("calls_generation.jsonl.gz.part*"))
    assert len(parts) >= 2 and not (data / "qwen38" / "calls_generation.jsonl.gz").exists()
    assert gzip.decompress(b"".join(p.read_bytes() for p in parts)) == before and big.read_bytes() == before
    run_all.pack_data(data)                       # the default limit: one small gz file, old parts removed
    assert (data / "qwen38" / "calls_generation.jsonl.gz").exists() and not list((data / "qwen38").glob("*.part*"))
    assert gzip.decompress((data / "qwen38" / "calls_generation.jsonl.gz").read_bytes()) == before


def test_test_run_mirrors_the_registered_order_including_the_online_part(monkeypatch, tmp_path):
    """A test run (--smoke N) with an API second judge ends its offline part like the registered run (OFFLINE FINISHED,
    after the primary judge's analysis marked as not data) and `second-judge --smoke N` then rates it with the second
    judge, analyzes with both judges, and finishes."""
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    cfg = load_config()
    r = run_all.Run(smoke=1, mock=True)
    steps = _record_plan(monkeypatch, r)
    r.go()
    kinds = [a[0] for _, _, a in steps]
    assert "analyze" in kinds and {"generate", "evaluate", "judge"} <= set(kinds)      # --smoke is added by step() itself
    assert not any("--judge" in a and a[a.index("--judge") + 1] == cfg["judging"]["second"] for _, _, a in steps)
    assert r.state["state"] == "OFFLINE FINISHED" and "TEST RUN: OFFLINE PART FINISHED" in r.log_path.read_text()
    r2 = run_all.Run(smoke=1, mock=True, online=True)
    steps2 = _record_plan(monkeypatch, r2)
    r2.go()
    judged = [a for _, _, a in steps2 if a[0] == "judge"]
    assert judged and all(a[a.index("--judge") + 1] == cfg["judging"]["second"] for a in judged)
    assert [a for _, _, a in steps2 if a[0] == "analyze" and "--judge" in a]
    assert r2.state["state"] == "FINISHED" and "TEST RUN FINISHED (not data)" in r2.log_path.read_text()
