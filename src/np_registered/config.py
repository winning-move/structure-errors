"""Load the registered configuration and prompt files; hash everything that defines the protocol."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]          # registered/
CONFIG_PATH = ROOT / "config" / "study.yaml"
PROMPT_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"

PROMPT_FILES = [
    "policy.txt", "roles.json", "stance_task.txt", "generation_task.txt",
    "hierarchy_peer_intro.txt", "evaluation_task.txt", "evaluation_items.txt",
    "judge_persona.txt", "judge_problem.txt", "judge_rubric.txt", "judge_anchors.txt",
    "judge_protocol.txt", "judge_items.txt",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(name: str) -> str:
    # Files are stored with a trailing newline by some editors; the prompt text is the
    # content without trailing whitespace. Interior text is used byte for byte.
    return (PROMPT_DIR / name).read_text(encoding="utf-8").rstrip()


@dataclass(frozen=True)
class Prompts:
    policy: str
    roles: dict
    stance_task: str
    generation_task: str
    hierarchy_peer_intro: str
    evaluation_task: str
    evaluation_items: str
    judge_persona: str
    judge_problem: str
    judge_rubric: str
    judge_anchors: dict          # subscale -> its anchored levels (judge_anchors.txt, blocks headed "## <subscale>")
    judge_protocol: str
    judge_items: str


def parse_anchors(text: str) -> dict:
    blocks, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            blocks[cur] = []
        elif cur is not None:
            blocks[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in blocks.items()}


def load_prompts() -> Prompts:
    return Prompts(
        policy=_read_text("policy.txt"),
        roles=json.loads((PROMPT_DIR / "roles.json").read_text(encoding="utf-8")),
        stance_task=_read_text("stance_task.txt"),
        generation_task=_read_text("generation_task.txt"),
        hierarchy_peer_intro=_read_text("hierarchy_peer_intro.txt"),
        evaluation_task=_read_text("evaluation_task.txt"),
        evaluation_items=_read_text("evaluation_items.txt"),
        judge_persona=_read_text("judge_persona.txt"),
        judge_problem=_read_text("judge_problem.txt"),
        judge_rubric=_read_text("judge_rubric.txt"),
        judge_anchors=parse_anchors(_read_text("judge_anchors.txt")),
        judge_protocol=_read_text("judge_protocol.txt"),
        judge_items=_read_text("judge_items.txt"),
    )


def load_config(path: Path | None = None) -> dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def protocol_hashes() -> dict:
    """SHA-256 of the config and of every prompt file: the fingerprint of the protocol."""
    out = {"config/study.yaml": sha256_file(CONFIG_PATH)}
    for name in PROMPT_FILES:
        out[f"prompts/{name}"] = sha256_file(PROMPT_DIR / name)
    return out


def load_dotenv(path: Path | None = None):
    """Read KEY=VALUE lines from registered/.env (gitignored) into the environment, without
    overriding variables that are already set. Keys never appear in logs or manifests."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.removeprefix("export ").strip()
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def data_root() -> Path:
    """NP_DATA_DIR overrides the data root (used by the tests)."""
    return Path(os.environ["NP_DATA_DIR"]) if os.environ.get("NP_DATA_DIR") else DATA_DIR


def smoke_root() -> Path:
    """Where test runs (--smoke, --mock) write: under NP_DATA_DIR when it is set, otherwise a folder next to this one,
    so that nothing from a test run ever sits with the data."""
    return data_root() / "smoke" if os.environ.get("NP_DATA_DIR") else ROOT.parent / "registered_study_smoke"


def arm_dir(arm: str, smoke: bool = False) -> Path:
    """Data go to data/<arm>/; test runs to smoke_root()/<arm>/ (never data)."""
    d = smoke_root() / arm if smoke else data_root() / arm
    d.mkdir(parents=True, exist_ok=True)
    return d


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


# ----------------------------------------------------------------------------- privacy of the record
_NAMES: list[tuple[re.Pattern, str]] | None = None


def machine_names() -> list[str]:
    """Strings that identify this computer or its owner and must never enter a record: the home
    directory, the login name, and the computer's names (the DNS host name, the Bonjour name, and the name shown
    in Sharing). Computed once; short or empty values are left out so that nothing ordinary is ever replaced."""
    import getpass, platform, socket, subprocess
    found = [str(Path.home())]
    for get in (getpass.getuser, platform.node, socket.gethostname):
        try:
            found.append(str(get()))
        except Exception:  # noqa: BLE001 - informational only
            pass
    for key in ("LocalHostName", "ComputerName", "HostName"):
        try:
            r = subprocess.run(["scutil", "--get", key], capture_output=True, text=True, timeout=5)
            found.append(r.stdout.strip())
        except Exception:  # noqa: BLE001 - not macOS, or scutil missing
            pass
    out = []
    for n in found:
        for v in (n.strip(), n.strip().removesuffix(".local")):
            if v and v != "/" and len(v) >= 4 and v not in out:
                out.append(v)
    return out


def scrub(text: str) -> str:
    """The home directory path written as ~, the login name as 'user', and the computer's names as 'host', in any
    text that becomes part of the record (call logs, derived files, preflight, manifest, the run log). Nothing else
    in a record is altered: a model's answer passes through byte for byte unless it contains one of these strings."""
    # A server error can echo authentication material; remove it before it reaches any record or diagnostic.
    for key in ("ANTHROPIC_API_KEY",):
        value = os.environ.get(key)
        if value:
            for form in (value, json.dumps(value, ensure_ascii=False)[1:-1]):
                text = text.replace(form, "[redacted]")
    global _NAMES
    if _NAMES is None:
        import re as _re
        names = machine_names()
        home = str(Path.home())
        rules = [(_re.compile(_re.escape(home)), "~")] if home != "/" else []
        import getpass
        try:
            user = getpass.getuser()
        except Exception:  # noqa: BLE001
            user = ""
        for n in sorted(names, key=len, reverse=True):
            if n == home:
                continue
            if n == user:
                rules.append((_re.compile(r"(?<![A-Za-z0-9])" + _re.escape(n) + r"(?![A-Za-z0-9])", _re.I), "user"))
            else:
                rules.append((_re.compile(_re.escape(n), _re.I), "host"))
        _NAMES = rules
    for pat, rep in _NAMES:
        text = pat.sub(rep, text)
    return text
