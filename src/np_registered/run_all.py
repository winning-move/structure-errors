"""One command for the whole registered run (RUNBOOK 2). Runs every stage of the two local experiments in the
registered order, with no internet, and recovers from LM Studio failures by itself; a second command, with the
internet on afterwards, has the second judge (an Anthropic model, through the Message Batches API) rate the archived
proposals and then runs the analyses.

    ./run.sh                 the offline part: both local experiments, each to the end of its primary judging
    ./run.sh second-judge    after the offline part, with the internet and ANTHROPIC_API_KEY: the second judge for both
                             experiments, then the manifests and the analyses (none runs before both judges are done)
    ./run.sh --smoke 2       a test run: 2 organizations per structure, written to ../registered_study_smoke/ outside
                             the repository (never data); the same order, panel, and zips as the registered run, ending
                             with OFFLINE PART FINISHED; then ./run.sh second-judge --smoke 2 (a small API cost) runs
                             the second judge and both analyses on it, ending with TEST RUN FINISHED (not data)
    ./run.sh progress        the progress panel, read only, safe at any time from a second window
    ./run.sh pack            after RUN FINISHED: the raw call logs also as gzip files (split under 95 MB) so that data/
                             can be committed; the originals are untouched (RUNBOOK 6)
The data folder is zipped into archive/ after the offline part and again at the end (data_offline_<time>.zip,
data_final_<time>.zip): exact copies for the deposit and as backups; archive/ is never committed.

Order (each step resumes where it stopped; a finished step is skipped). The main experiment is complete before the
second experiment starts (PROTOCOL.md 4.5):
    main experiment (qwen38):   generate (Qwen 3.8 loaded), evaluate (Gemma 4), primary judge (Muse Glimmer: the floor
                                readings, readings-check without a model, the decided readings), extend-check (no
                                model; the internal pilot's one recalculation); if it extends, generate, evaluate, and
                                judge again (only the new organizations)
    second experiment (gemma):  the same with Gemma 4 writing and Qwen 3.8 evaluating
    second-judge (API, later):  one tiny request as a batch of one (the model returned must be the configured one); for
                                each experiment: the floor readings, readings-check, the decided readings (in batches);
                                then manifest and analyze for each experiment with each judge
Recovery: a step that stops on a transport failure is retried after restarting the LM Studio server and reloading
the model, at most 5 times, after waits of 1, 2, 5, 10, and 20 minutes (API steps wait without a restart). Content
failures (unusable answers) never stop the run: each call has its registered attempts, and the counts go into run.log.
Only what makes continuing wrong ends the run, with the reason (a registered stop, a wrong model identity, changed LM
Studio settings, a full disk, a sixth failure of one step); starting it again resumes.

The record of the run itself (PROTOCOL.md 10), besides the call logs of every stage (every attempt, with its request, raw
response, reasoning text, tokens, latency, and times): data/run.log (every line time-stamped: the runner's decisions,
each step's own output, every LM Studio command and its answer), data/system.jsonl (every 5 minutes: memory, swap,
load, disk, thermal state, and the models LM Studio has loaded), and data/lmstudio_logs/ (LM Studio's own server log for
the hours of the run, copied after every step, with home paths and computer names scrubbed like every record).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from .config import ROOT, load_config, scrub  # noqa: F401  (scrub: home paths and the computer's names never enter the run log)

LMS = str(Path.home() / ".lmstudio/bin/lms")
LOCAL_ARMS = ("qwen38", "gemma")                              # the main experiment first, then the second (4.5)
MODELS_USED = ("qwen38", "gemma4", "glimmer")                 # LM Studio identifiers the plan loads
WAITS_MIN = (1, 2, 5, 10, 20)
HEARTBEAT_S = 300         # data/system.jsonl: one line every 5 minutes
PANEL_S = 300             # the progress panel in the run window (not logged; ./run.sh progress shows it at any time)
LMS_LOGS = Path.home() / ".lmstudio/server-logs"
STALL_MIN = 45            # a model stage that writes no record for this long is restarted: every call has a 30-minute
                          #   limit and is logged even when it fails, so only a hung server stays silent longer
RC_TRANSPORT, RC_REGISTERED_STOP, RC_STALLED = 2, 3, 124    # exit codes of a step (np_registered: 2 = Abort, 3 = registered stop)
STAGES = ("generate", "evaluate", "judge")


def state_path() -> Path:
    from .config import data_root
    return data_root() / "run_state.json"



def _dir(arm: str, smoke: bool) -> Path:
    """The data folder of an arm, without creating it."""
    from .config import data_root
    return data_root() / "smoke" / arm if smoke else data_root() / arm


def stamp() -> str:
    return f"[{datetime.now():%Y-%m-%d %H:%M:%S}]"


def _out(*args, timeout=20) -> str:
    """The output of a small system command for the record (never fatal)."""
    try:
        r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return f"unavailable: {type(e).__name__}"


def system_snapshot() -> dict:
    """The machine at one moment: what could slow, stop, or change the run without any model call failing."""
    loaded = _out(LMS, "ps", "--json", timeout=60)
    try:
        loaded = [{k: m.get(k) for k in ("identifier", "path", "status", "contextLength", "maxContextLength")}
                  for m in json.loads(loaded)]
    except (ValueError, TypeError, AttributeError):
        pass
    mp = _out("memory_pressure", "-Q")
    return {"time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "memory_free_percent": mp.rsplit(":", 1)[-1].strip() if ":" in mp else mp,
            "swap": _out("sysctl", "-n", "vm.swapusage"), "load_avg": [round(x, 2) for x in os.getloadavg()],
            "disk_free_gb": round(shutil.disk_usage(Path.home()).free / 1e9, 1),
            "thermal": " ".join(_out("pmset", "-g", "therm").split()), "lmstudio_loaded": loaded}


def archive_lmstudio_logs(since: float, dest: Path) -> int:
    """Copy LM Studio's own server log files written since the run started into the data folder (scrubbed), so the
    engine's messages (loads, slots, timings, errors) stay with the data. A copy is replaced only by a longer version of
    the same file (LM Studio appends to a file until it rotates at about 10 MB). Never fatal; returns files copied."""
    n = 0
    try:
        for src in sorted(LMS_LOGS.glob("*/*.log")):
            st = src.stat()
            if st.st_mtime < since - 60:
                continue
            dst = dest / src.parent.name / src.name
            if dst.exists() and dst.stat().st_mtime >= st.st_mtime:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(scrub(src.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
            n += 1
    except Exception:  # noqa: BLE001 - the copy never stops the run; the originals stay in ~/.lmstudio/server-logs
        pass
    return n


class Run:
    def __init__(self, smoke: int, mock: bool = False, online: bool = False):
        self.cfg = load_config()
        self.smoke, self.mock, self.online = smoke, mock, online
        if (smoke or mock) and not os.environ.get("NP_DATA_DIR"):
            # a test run writes outside the study folder (config.smoke_root), inherited by every step
            os.environ["NP_DATA_DIR"] = str(ROOT.parent / "registered_study_smoke")
        from .config import data_root
        self.log_path = data_root() / ("smoke/run.log" if smoke else "run.log")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = {"state": "STARTING", "step": "", "attempt": 0, "started": datetime.now().isoformat(timespec="seconds"),
                      "smoke": smoke, "done": [], "reason": ""}
        self.loaded = None
        self.t0 = time.time()                             # this session's start: LM Studio logs from here on are copied
        self.child: subprocess.Popen | None = None       # the step running now (its own process group)
        self._lock_file = None

    # ------------------------------------------------------------------ helpers
    def kill_child(self, wait: bool = True) -> None:
        """End the step running now, with its whole process group (uv and the python it started). A group that has
        already ended raises; that is not an error. wait=False is for a signal handler, which runs inside the
        interrupted Popen.wait and therefore cannot wait on the same process: it sends the signals and sleeps."""
        proc = self.child
        if proc is None or proc.returncode is not None:
            return
        import signal
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for send in (lambda: os.killpg(proc.pid, sig), lambda: proc.send_signal(sig)):
                try:
                    send()
                except (ProcessLookupError, PermissionError):
                    pass
            if not wait:
                time.sleep(2)
                continue
            try:
                proc.wait(timeout=60)
                return
            except subprocess.TimeoutExpired:
                continue
            except OSError:
                return

    def interrupt(self, what: str) -> None:
        """Ctrl-C, a closed Terminal window, or a kill: stop the step too, so that no orphan keeps calling the server,
        then record the stop; starting ./run.sh again resumes."""
        self.kill_child(wait=False)
        self.archive()
        self.save(state="STOPPED", reason=f"interrupted ({what}); run ./run.sh again to resume")
        self.log(f"STOPPED: interrupted ({what})")
        sys.exit(130)
    def log(self, msg: str) -> None:
        line = scrub(f"{stamp()} {msg}")
        with open(self.log_path, "a") as f:
            f.write(line + "\n")
        try:
            print(line, flush=True)
        except OSError:                      # the Terminal window is gone (SIGHUP): the file has the line
            pass

    def save(self, **kw) -> None:
        self.state.update({k: (scrub(v) if isinstance(v, str) else v) for k, v in kw.items()})
        state_path().parent.mkdir(parents=True, exist_ok=True)
        state_path().write_text(json.dumps(self.state, indent=1))

    def spec_of(self, ident: str) -> dict:
        """The configuration entry served under this LM Studio identifier (the one with a load recipe)."""
        for group in ("arms", "judges"):
            for spec in self.cfg[group].values():
                if spec.get("model") == ident and spec.get("backend") == "openai_compatible" and spec.get("lms_key"):
                    return spec
        raise KeyError(f"no configuration entry with an lms_key and load recipe serves '{ident}'")

    def lms(self, *args, timeout=1800) -> subprocess.CompletedProcess:
        r = subprocess.run([LMS, *args], capture_output=True, text=True, timeout=timeout)
        out = "\n".join(l for l in (r.stdout + r.stderr).replace("\x1b[?25l", "\n").splitlines()
                        if l.strip() and not re.match(r"\s*Loading .*\d+%", l))     # the loading spinner is not a record
        with open(self.log_path, "a") as f:
            f.write(scrub(f"{stamp()}   lms {' '.join(args)} -> rc {r.returncode}\n{out[-2000:]}\n"))
        return r

    def load(self, ident: str) -> None:
        if self.mock or self.loaded == ident:
            return
        spec = self.spec_of(ident)
        self.lms("unload", "--all")
        r = self.lms("load", spec["lms_key"], "--identifier", ident, "-c", str(spec["load"]["context_length"]),
                     "--parallel", str(spec["load"]["parallel"]), "-y")
        if r.returncode != 0:
            raise RuntimeError(f"LM Studio could not load {spec['lms_key']} (see {self.log_path})")
        self.loaded = ident
        self.log(f"loaded {spec['lms_key']} as {ident}")

    def restart_server(self) -> None:
        self.loaded = None
        if self.online or self.mock:                 # API steps: nothing local to restart; the wait is the remedy
            return
        self.lms("server", "stop", timeout=120)
        r = self.lms("server", "start", timeout=300)
        if r.returncode != 0:
            subprocess.run(["open", "-a", "LM Studio"], capture_output=True)
            time.sleep(60)
            self.lms("server", "start", timeout=300)

    def np(self, *args, watch: Path | None = None) -> int:
        """One step of the harness, offline (uv never contacts the package index during the run). With `watch`, the
        step is a model stage: if no file in that folder changes for STALL_MIN minutes (no call completed, no retry
        logged), the step is stopped and reported as stalled, so that the recovery restarts the server."""
        cmd = ["uv", "run", "--offline", "python", "-m", "np_registered", *args]
        if self.smoke:
            cmd += ["--smoke", str(self.smoke)]
        if self.mock:
            cmd += ["--mock"]
        with open(self.log_path, "a") as f:
            f.write(f"{stamp()}   $ {' '.join(cmd)}\n")
            f.flush()
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            self.child = proc

            def copy_output():          # the step's own output, line by line, time-stamped, with home paths written as ~
                for raw in proc.stdout:
                    f.write(scrub(f"{stamp()}     " + raw.decode("utf-8", errors="replace")))
                    f.flush()
            output_thread = threading.Thread(target=copy_output, daemon=True)
            output_thread.start()
            try:
                if watch is None:
                    return proc.wait()
                last_change, last_seen = time.time(), newest_mtime(watch)
                while True:
                    try:
                        return proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        pass
                    now_seen = newest_mtime(watch)
                    if now_seen != last_seen:
                        last_change, last_seen = time.time(), now_seen
                    elif time.time() - last_change > STALL_MIN * 60:
                        self.kill_child()
                        self.log(f"no record written for {STALL_MIN} minutes: the stage was stopped for recovery")
                        return RC_STALLED
            finally:
                output_thread.join(timeout=120)  # drain the pipe before the log file is closed (never wait forever)
                self.child = None

    def record_counts(self, name: str, arm: str) -> None:
        """After each stage, the output of `status` (calls done, exhausted calls, content failures per attempt, tokens) goes
        into run.log. Content failures never stop the run (PROTOCOL.md 8.1); every failed attempt is kept in the call log
        and reported with the results (7.3, 8.4)."""
        cmd = ["uv", "run", "--offline", "python", "-m", "np_registered", "status", "--arm", arm]
        if self.smoke:
            cmd += ["--smoke", str(self.smoke)]
        if self.mock:
            cmd += ["--mock"]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        with open(self.log_path, "a") as f:
            f.write(scrub(f"{stamp()}   $ {' '.join(cmd)}\n{r.stdout}{r.stderr}"))
        if r.returncode != 0:
            self.log(f"note: the counts could not be read after {name} (status exit {r.returncode}); the run continues")

    def tail(self, n=40) -> str:
        try:
            return "\n".join(self.log_path.read_text().splitlines()[-n:])
        except OSError:
            return ""

    # ------------------------------------------------------------------ one step with recovery
    def step(self, name: str, model: str | None, args: list[str]) -> None:
        """One step with recovery. What happens after a failure follows the step's exit code: 3 is a registered stop
        and 1 a deterministic error (a wrong file, a missing stage, a bug), both for a person; 2 is a transport failure
        that did not clear and 124 a stall, both recovered by restarting the server and resuming, at most 5 times."""
        key = f"{name}:{' '.join(args)}"
        arm = args[args.index("--arm") + 1] if "--arm" in args else "qwen38"
        # the stall watchdog is for local model stages; an API step (the second judge) may wait on a batch for hours
        watch = _dir(arm, bool(self.smoke)) if args[0] in STAGES and not self.online else None
        for attempt in range(len(WAITS_MIN) + 1):
            self.save(state="RUNNING" if attempt == 0 else "RECOVERING", step=name, attempt=attempt)
            try:
                if model and not self.mock:
                    self.load(model)
                    pf = self.np("preflight", "--arm", arm, "--only", model)
                    if pf == RC_REGISTERED_STOP:
                        self.stop(f"preflight before {name}: the loaded model is not the registered one (identifier, "
                                  f"folder, or file hashes); see the end of {self.log_path}")
                    if pf != 0:
                        raise RuntimeError(f"preflight failed before {name} (exit {pf}); reloading")
                rc = self.np(*args, watch=watch)
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                rc = RC_TRANSPORT
                self.log(f"{name}: {e}")
            self.archive()
            if rc == 0:
                if args[0] in STAGES:
                    self.record_counts(name, arm)
                self.state["done"].append(key)
                self.log(f"done: {name}")
                return
            if rc == RC_REGISTERED_STOP:
                self.stop(f"{name}: a registered stop (reserves used up); see the end of {self.log_path}")
            if rc not in (RC_TRANSPORT, RC_STALLED):
                self.stop(f"{name} failed with exit {rc}, which no restart can fix; see the end of {self.log_path}")
            if attempt == len(WAITS_MIN) or self.mock:
                break
            wait = WAITS_MIN[attempt]
            self.log(f"{name} failed (exit {rc}); recovery {attempt + 1} of {len(WAITS_MIN)}: restart the server, "
                     f"wait {wait} min, reload, resume")
            self.save(state="RECOVERING", step=name, attempt=attempt + 1)
            self.restart_server()
            time.sleep(wait * 60)
        self.stop(f"{name} failed six times; see the end of {self.log_path}")

    def zip_data(self, label: str) -> None:
        """The whole data folder as one zip, after the offline part and at the end: archive/ next to data/ for the
        registered run; <smoke root>/archive/ for a test run (never for the mock)."""
        if self.mock:
            return
        from .config import data_root
        src = data_root() / "smoke" if self.smoke else data_root()
        out = zip_data(src, (data_root() if self.smoke else ROOT) / "archive", label)
        self.log(f"data archived: {out} ({out.stat().st_size / 1e6:.0f} MB)")

    def archive(self) -> None:
        """LM Studio's server log of this session into the data folder (local runs only)."""
        if self.mock or self.online:
            return
        from .config import data_root
        n = archive_lmstudio_logs(self.t0, data_root() / ("smoke/lmstudio_logs" if self.smoke else "lmstudio_logs"))
        if n:
            self.log(f"LM Studio server log: {n} file(s) copied to lmstudio_logs/")

    def api_ping(self, name: str, spec: dict) -> None:
        """Before the second judge's first call: one tiny request (not a study prompt) through the same API path, as a
        batch of one for a batch backend; the model returned must be the configured one (PROTOCOL.md 5.4)."""
        if self.mock:
            return
        from .preflight import _ping
        self.log(f"API preflight {name}: one tiny request through the same path (a batch of one: usually minutes, at most "
                 "an hour)")
        ok, info = _ping(f"judge-second:{name}", spec, False)
        self.log(f"API preflight {name}: {'ok' if ok else 'FAILED'}; requested {info.get('requested')}, returned "
                 f"{info.get('returned')}, stop {info.get('stop_reason')}, error {info.get('error')}")
        if not ok:
            self.stop(f"the API preflight of the second judge failed ({info.get('error') or info.get('returned')})")

    def stop(self, reason: str) -> None:
        self.archive()
        self.save(state="STOPPED", reason=reason)
        self.log("STOPPED: " + reason)
        sys.exit(1)

    # ------------------------------------------------------------------ checks before the first step
    def take_lock(self) -> None:
        """Only one runner per data folder: two would interleave calls and records in the same logs."""
        import fcntl
        lock = state_path().with_name("run.lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        handle = open(lock, "a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            reason = "another runner is working in this data folder; stop it first or wait"
            self.state.update(state="STOPPED", reason=reason)
            raise SystemExit(reason)       # do not overwrite the active runner's state or log
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self._lock_file = handle             # the kernel releases the lock on close or process exit

    def checks(self) -> None:
        self.take_lock()
        if self.mock:
            return
        if self.online:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                from .config import load_dotenv
                load_dotenv()
            if not os.environ.get("ANTHROPIC_API_KEY"):
                self.stop("ANTHROPIC_API_KEY is not set (registered/.env or the environment); the second judge needs it")
            return
        free = shutil.disk_usage(Path.home()).free / 1e9
        if free < 30:
            self.stop(f"only {free:.0f} GB of disk free (30 GB needed)")
        from .manifest import network_state
        self.log("network at start: " + "; ".join(f"{k}: {v}" for k, v in network_state().items()))
        bad = []
        try:
            s = json.loads((Path.home() / ".lmstudio/settings.json").read_text())
            if s.get("developer", {}).get("autoUpdateExtensionPacks", s.get("autoUpdateExtensionPacks")) is not False:
                bad.append("engine auto-update is on")
            h = json.loads((Path.home() / ".lmstudio/.internal/http-server-config.json").read_text())
            if h.get("justInTimeModelLoading") is not False:
                bad.append("just-in-time model loading is on")
        except Exception as e:  # noqa: BLE001
            bad.append(f"LM Studio settings could not be read ({e})")
        if bad:
            self.stop("LM Studio settings changed: " + "; ".join(bad))
        for ident in MODELS_USED:
            try:
                spec = self.spec_of(ident)
                spec["load"]["context_length"], spec["load"]["parallel"]
            except KeyError as e:
                self.stop(f"config/study.yaml: {e}")
        if not self.mock and self.lms("server", "start", timeout=300).returncode != 0:
            self.stop("the LM Studio server does not start")

    # ------------------------------------------------------------------ the plan
    def model_of(self, arm: str, role: str) -> str:
        """The LM Studio identifier of an experiment's writer or evaluator."""
        a = self.cfg["arms"][arm]
        return a["model"] if role == "writer" else self.cfg["arms"][a.get("evaluator", arm)]["model"]

    def experiment(self, arm: str) -> None:
        """One experiment to the end of its primary judging (PROTOCOL.md 4.5): the first wave, the primary judge with its
        readings decision, the internal pilot's one recalculation, and the extension wave if the recalculation asks for
        one."""
        name = "main" if arm == LOCAL_ARMS[0] else "second"
        primary = self.cfg["judging"]["primary"]
        pmodel = self.cfg["judges"][primary]["model"]
        self.step(f"generate {name}", self.model_of(arm, "writer"), ["generate", "--arm", arm])
        self.step(f"evaluate {name}", self.model_of(arm, "evaluator"), ["evaluate", "--arm", arm])
        self.judge_steps(arm, primary, pmodel, "primary")
        if self.smoke:
            return
        self.step(f"blinded check {name}", None, ["extend-check", "--arm", arm])
        n = self.cfg["design"]["orgs_per_structure"]
        if extension_target(_dir(arm + ("-mock" if self.mock else ""), bool(self.mock)), n) <= n:
            self.log(f"{name} experiment: no extension")
            return
        # the extension wave: each step adds only the new organizations
        self.step(f"generate {name} (extension)", self.model_of(arm, "writer"), ["generate", "--arm", arm])
        self.step(f"evaluate {name} (extension)", self.model_of(arm, "evaluator"), ["evaluate", "--arm", arm])
        self.step(f"judge {name} (primary, extension)", pmodel, ["judge", "--arm", arm, "--judge", primary])

    def judge_steps(self, arm: str, judge: str, model: str | None, label: str) -> None:
        """One judge of one experiment (PROTOCOL.md 4.4): the floor readings, the readings check (decides the judge's
        number once; skips if decided), then the same judge command again, which adds the remaining readings."""
        self.step(f"judge {arm} ({label})", model, ["judge", "--arm", arm, "--judge", judge])
        if not self.smoke:
            self.step(f"readings check {arm} ({label})", None, ["readings-check", "--arm", arm, "--judge", judge])
            self.step(f"judge {arm} ({label}, decided readings)", model, ["judge", "--arm", arm, "--judge", judge])

    def analyses(self) -> None:
        """Manifest and the analyses of every experiment, with each judge (the second judge's categories repeat every
        test, 7.4). Only after both judges have rated the final sample of every experiment (4.5)."""
        if not self.mock and not self.online:
            self.lms("unload", "--all")
        self.loaded = None
        second = self.cfg["judging"]["second"]
        for a in LOCAL_ARMS:
            self.step(f"manifest {a}", None, ["manifest", "--arm", a])
            self.step(f"analyze {a}", None, ["analyze", "--arm", a])
            if self.online or not self.smoke:
                self.step(f"analyze {a} (second judge)", None, ["analyze", "--arm", a, "--judge", second])

    def go(self) -> None:
        try:
            self.checks()
            self._go()
        finally:
            if self._lock_file is not None:
                self._lock_file.close()
                self._lock_file = None

    def _go(self) -> None:
        self.log(f"run started ({'smoke ' + str(self.smoke) if self.smoke else 'registered'}"
                 f"{', second judge' if self.online else ''}); log: {self.log_path}")
        self.log("code: " + code_version())
        threading.Thread(target=panel_loop, args=(self,), daemon=True).start()
        if not self.mock:
            threading.Thread(target=heartbeat_loop, args=(self,), daemon=True).start()
        second = self.cfg["judging"]["second"]
        second_spec = self.cfg["judges"][second]
        second_local = second_spec.get("backend") == "openai_compatible"
        if not self.online:
            for a in LOCAL_ARMS:
                self.experiment(a)
            self.archive()
            if self.smoke:                          # a test run: the primary judge's analysis now, marked as not data
                self.analyses()
                if second_local:
                    self.save(state="FINISHED", step="", reason="")
                    self.log("TEST RUN FINISHED (not data)")
                    return
            if not second_local:
                self.save(state="OFFLINE FINISHED", step="", reason="")
                self.zip_data("offline")
                self.log(f"{'TEST RUN: ' if self.smoke else ''}OFFLINE PART FINISHED. Next, with the internet on and ANTHROPIC_API_KEY in .env: ./run.sh second-judge"
                         f"{' --smoke ' + str(self.smoke) if self.smoke else ''} "
                         f"(the second judge, {second_spec.get('model')}, rates both experiments; then the analyses)")
                return
        elif second_local:
            self.stop("the second judge is a local model: ./run.sh runs it; second-judge is for an API judge")
        else:
            self.api_ping(second, second_spec)
        for a in LOCAL_ARMS:
            self.judge_steps(a, second, second_spec["model"] if second_local else None, "second")
        self.analyses()
        self.save(state="FINISHED", step="", reason="")
        self.zip_data("final")
        self.log("TEST RUN FINISHED (not data)" if self.smoke else "RUN FINISHED. Next: ./run.sh pack, then commit data/ (RUNBOOK 6)")


def zip_data(data: Path, dest_dir: Path, label: str) -> Path:
    """data/ as one zip, data_<label>_<local time>.zip, in dest_dir (never inside data/); the data folder is not touched."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"data_{label}_{datetime.now().strftime('%Y%m%d-%H%M')}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(x for x in data.rglob("*") if x.is_file()):
            z.write(f, Path("data") / f.relative_to(data))
    return out


def pack_data(data: Path, limit: int = 95 * 1024 * 1024) -> list[str]:
    """The raw call logs (calls_*.jsonl) as gzip files next to the originals, split into parts below `limit` bytes when
    needed, so that data/ can be committed (GitHub refuses a file over 100 MB). The originals are not touched and stay
    out of git (.gitignore). To rejoin: cat <name>.jsonl.gz.part* > <name>.jsonl.gz; gunzip <name>.jsonl.gz."""
    lines = []
    for src in sorted(data.rglob("calls_*.jsonl")):
        gz = src.with_name(src.name + ".gz")
        for old in src.parent.glob(src.name + ".gz*"):
            old.unlink()
        with open(src, "rb") as f, gzip.open(gz, "wb", compresslevel=6) as g:
            shutil.copyfileobj(f, g, 1 << 20)
        size = gz.stat().st_size
        if size > limit:
            n = 0
            with open(gz, "rb") as f:
                while chunk := f.read(limit):
                    n += 1
                    (src.parent / f"{gz.name}.part{n:02d}").write_bytes(chunk)
            gz.unlink()
            lines.append(f"{src.relative_to(data)}: {size / 1e6:.0f} MB compressed, in {n} parts")
        else:
            lines.append(f"{src.relative_to(data)}: {size / 1e6:.1f} MB compressed")
    return lines


# ---------------------------------------------------------------------- progress panel (counts only)
def extension_target(d: Path, n: int) -> int:
    """The target per structure of an experiment: n, or the larger target its blinded check wrote (extension.json)."""
    try:
        return max(n, int(json.loads((d / "extension.json").read_text()).get("target_per_structure", n)))
    except (OSError, ValueError, TypeError, AttributeError):
        return n


def readings_target(d: Path, cfg, judge: str) -> int:
    """The readings of a judge in an experiment: the number its readings check decided (readings_<judge>.json), else the floor."""
    try:
        return int(json.loads((d / f"readings_{judge}.json").read_text())["readings"])
    except (OSError, ValueError, TypeError, KeyError):
        return int(cfg["judging"]["readings"]["floor"])


def planned_calls(cfg, n: int, readings: int | None = None) -> dict:
    """Logical calls of one experiment at n per structure; `readings` per judge (default the floor)."""
    roles, props = 4, n * 2 * 12
    readings = readings or cfg["judging"]["readings"]["floor"]
    return {"generate": n * 2 * roles, "evaluate": roles * -(-props // cfg["evaluation"]["batch_size"]),
            "judge": readings * -(-props // cfg["judging"]["batch_size"])}   # one call per proposal and reading (all six subscales; 4.4)


def newest_mtime(folder: Path) -> float:
    """The latest modification time of any file in the folder (0 if none): the sign that a stage is alive."""
    try:
        return max((p.stat().st_mtime for p in folder.iterdir() if p.is_file()), default=0.0)
    except OSError:
        return 0.0


_SEEN: dict = {}     # path -> [offset, ids, secs]: the call logs grow to hundreds of megabytes; read only what is new


def done_calls(path: Path) -> tuple[int, float | None, float]:
    """(distinct valid batch calls, seconds per call, time of the last answer) from a call log, read incrementally."""
    if not path.exists():
        return 0, None, 0.0
    st = _SEEN.setdefault(str(path), [0, set(), []])
    size = path.stat().st_size
    if size < st[0]:                      # the file was replaced: start over
        st[:] = [0, set(), []]
    if size > st[0]:
        with open(path, "rb") as f:
            f.seek(st[0])
            chunk = f.read()
        cut = chunk.rfind(b"\n") + 1      # only complete lines; a line still being written is read next time
        st[0] += cut
        for line in chunk[:cut].decode("utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("valid") and ":single:" not in r.get("call_id", ""):
                st[1].add(r.get("call_id"))
                if r.get("latency_s"):
                    st[2].append(float(r["latency_s"]))
    secs = st[2][-40:]
    return len(st[1]), (sum(secs) / len(secs) if secs else None), path.stat().st_mtime


def panel(smoke: int = 0) -> str:
    cfg = load_config()
    n = smoke or cfg["design"]["orgs_per_structure"]
    st = json.loads(state_path().read_text()) if state_path().exists() else {"state": "NOT STARTED"}
    lines, last, total_left = [], 0.0, 0.0
    for arm in LOCAL_ARMS:
        d = _dir(arm, bool(smoke))
        target = extension_target(d, n)                         # grows when the blinded check extends
        plan = planned_calls(cfg, target)
        plan_j = {j: planned_calls(cfg, target, readings_target(d, cfg, j))["judge"]      # grows when a readings check decides
                  for j in (cfg["judging"]["primary"], cfg["judging"]["second"])}
        ev = cfg["arms"][arm].get("evaluator", arm)
        primary, second = cfg["judging"]["primary"], cfg["judging"]["second"]
        files = {"generate": d / "calls_generation.jsonl",
                 "evaluate": d / f"calls_evaluation{'' if ev == arm else '_' + ev}.jsonl",
                 "judge (primary)": d / f"calls_judge_{primary}.jsonl",
                 "judge (second)": d / f"calls_judge_{second}.jsonl"}
        by = {"generate": cfg["arms"][arm]["model"], "evaluate": cfg["arms"][ev]["model"],
              "judge (primary)": cfg["judges"][primary]["model"], "judge (second)": cfg["judges"][second]["model"]}
        for stage, f in files.items():
            k, spc, mt = done_calls(f)
            want = (plan_j[primary if stage == "judge (primary)" else second] if stage.startswith("judge")
                    else plan[stage])
            last = max(last, mt)
            bar = "#" * int(20 * min(1, k / want)) + "." * (20 - int(20 * min(1, k / want)))
            slots = (cfg["judges"][primary if stage == "judge (primary)" else second]
                     if stage.startswith("judge") else cfg["arms"][arm if stage == "generate" else ev]).get("concurrency", 4)
            left = max(0, want - k) * (spc or 0) / slots   # calls run at once: each model's registered concurrency
            total_left += left
            label = f"{'judge 2' if stage == 'judge (second)' else stage.split(' ')[0]} by {by[stage]}"
            lines.append(f"  {arm:7s} {label:29s} [{bar}] {k:5d}/{want:<5d}"
                         + (f"  {spc:5.0f} s/call  ~{left / 3600:4.1f} h left" if spc else ""))
    ago = time.time() - last if last else None
    head = [f"{datetime.now():%a %Y-%m-%d %H:%M:%S}  Registered run: {st.get('state')}"
            f"  {('step: ' + st.get('step', '')) if st.get('step') else ''}"
            + (f"  (recovery {st.get('attempt')} of 5)" if st.get("state") == "RECOVERING" else ""),
            "  exp.    stage by model                [done of planned]  done/planned  seconds per call  time left",
            f"  last answer received {ago:.0f} s ago" if ago is not None else "  no answer yet",
            f"  rough time left for the stages under way: {total_left / 3600:.1f} h; expected finish "
            f"{(datetime.now() + timedelta(seconds=total_left)):%a %H:%M} (the blinded check can add organizations)"]
    if st.get("state") == "STOPPED":
        head.append(f"  STOPPED: {st.get('reason')}  -> fix it, then run ./run.sh again (it resumes)")
    return "\n".join(head + lines)


def code_version() -> str:
    """The commit the run's code comes from, and whether any tracked file differs from it (for the record)."""
    head = _out("git", "-C", str(ROOT), "rev-parse", "HEAD")
    if not head or head.startswith(("fatal", "unavailable")) or len(head) < 40:
        return "not a git checkout (an exported copy)"
    changed = [l for l in _out("git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no", ".").splitlines() if l.strip()]
    return f"commit {head[:12]}" + (f"; {len(changed)} tracked file(s) differ from it" if changed else "; no tracked file differs")


def heartbeat_loop(run: Run) -> None:
    """data/system.jsonl: a snapshot of the machine every 5 minutes, with the runner's state (never stops the run)."""
    from .config import data_root
    path = data_root() / ("smoke/system.jsonl" if run.smoke else "system.jsonl")
    while True:
        try:
            rec = {**system_snapshot(), "state": run.state.get("state"), "step": run.state.get("step")}
            with open(path, "a", encoding="utf-8") as f:
                f.write(scrub(json.dumps(rec, ensure_ascii=False)) + "\n")
        except Exception:  # noqa: BLE001
            pass
        time.sleep(HEARTBEAT_S)


def panel_loop(run: Run) -> None:
    """The progress panel in the run window: once at the start, then every PANEL_S seconds (terminal only, never logged)."""
    while True:
        try:
            print("\n" + panel(run.smoke) + "\n", flush=True)
        except Exception:  # noqa: BLE001 - the panel never stops the run
            pass
        time.sleep(PANEL_S)


def main() -> None:
    ap = argparse.ArgumentParser(prog="run.sh")
    ap.add_argument("what", nargs="?", default="run", choices=["run", "second-judge", "progress", "pack"])
    ap.add_argument("--smoke", type=int, default=0)
    ap.add_argument("--mock", action="store_true", help="the mock model (tests of the runner only)")
    a = ap.parse_args()
    if a.what == "progress":
        print(panel(a.smoke))
        return
    if a.what == "pack":
        from .config import data_root
        lines = pack_data(data_root())
        print("\n".join(lines) if lines else "no call logs under data/")
        print("packed: the raw call logs are now also in compressed form; data/ can be committed (RUNBOOK 6)")
        return
    run = Run(a.smoke, a.mock, online=a.what == "second-judge")
    import signal
    for sig, name in ((signal.SIGINT, "Ctrl-C"), (signal.SIGTERM, "kill"), (signal.SIGHUP, "the Terminal window closed")):
        signal.signal(sig, lambda signum, frame, n=name: run.interrupt(n))
    try:
        run.go()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 - an unexpected error must still be reported, never a silent exit
        import traceback
        tb = traceback.format_exc()
        run.log("UNEXPECTED ERROR\n" + tb)
        run.save(state="STOPPED", step=run.state.get("step", ""), reason="unexpected error (see run.log)")
        print(tb, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
