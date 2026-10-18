"""Nothing that identifies the computer or its owner enters a record or the study folder."""
import getpass
import json
import os
from pathlib import Path

from np_registered import config, stages
from np_registered.config import ROOT, machine_names, scrub
from np_registered.runner import CallLog

HOME = str(Path.home())
NAMES = [n for n in machine_names() if n != HOME]


def test_scrub_replaces_home_login_and_computer_names():
    assert scrub(f"OSError: {HOME}/.lmstudio/models/x.gguf") == "OSError: ~/.lmstudio/models/x.gguf"
    for n in NAMES:
        out = scrub(f"server {n} refused; path {HOME}/a")
        assert n.lower() not in out.lower() and HOME not in out, (n, out)
    assert scrub("a plain answer about users and hosts") == "a plain answer about users and hosts"


def test_scrub_leaves_ordinary_text_untouched():
    text = json.dumps({"text": "The host organization's users saw ~ nothing unusual.", "stance": 40})
    assert scrub(text) == text


def test_every_writer_scrubs(tmp_path):
    rec = {"call_id": "x", "valid": False, "error": f"APIConnectionError: {HOME}/x on {' '.join(NAMES)}"}
    log = CallLog(tmp_path / "calls.jsonl")
    log.append(rec)
    stages.append_jsonl(tmp_path / "fail.jsonl", rec)
    stages._write_jsonl(tmp_path / "rows.jsonl", [rec])
    for f in ("calls.jsonl", "fail.jsonl", "rows.jsonl"):
        text = (tmp_path / f).read_text()
        assert HOME not in text and all(n.lower() not in text.lower() for n in NAMES), f
        assert "~/x" in text
    assert log.n_invalid == {} and "x" not in log.done


def test_registered_tree_never_names_the_owner():
    """Every committed text file under registered/ (outside data/ and results/), read as text."""
    user = getpass.getuser()
    skip = {"data", "results", ".venv", "__pycache__", ".pytest_cache", "export"}
    bad = []
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for f in files:
            p = Path(dirpath) / f
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            low = t.lower()
            if HOME in t or (len(user) >= 4 and user.lower() in low) or any(n.lower() in low for n in NAMES):
                bad.append(str(p.relative_to(ROOT)))
    assert bad == [], bad


def test_configured_credential_is_redacted_from_transport_errors(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import anthropic
    from np_registered.backends import AnthropicBackend
    from np_registered.runner import Abort, run_call
    import pytest
    credential = ' '.join(('private', 'credential', 'marker'))
    monkeypatch.setenv('ANTHROPIC_API_KEY', credential)
    def stream(**kwargs):
        raise RuntimeError('request refused: ' + credential)
    backend = AnthropicBackend.__new__(AnthropicBackend)
    backend._anthropic = anthropic
    backend.client = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    backend.model, backend.effort, backend.max_tokens, backend.display = 'mock-model', 'medium', 10, None
    log = CallLog(tmp_path / 'calls.jsonl')
    with pytest.raises(Abort) as error:
        run_call(backend, log, 'call', {}, 'prompt', {}, 'judge', lambda obj: None,
                 {'content_attempts': 3, 'transport_attempts': 1})
    assert credential not in str(error.value)
    assert credential not in log.path.read_text()
    assert credential not in scrub('record: ' + credential)
