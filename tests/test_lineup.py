"""Writers and evaluators from different models: cross-screening files,
the registered evaluator's votes in the analysis, and preflight with one local model loaded at a time."""
import json
from types import SimpleNamespace

import pytest

from np_registered import cli, preflight, stages
from np_registered.backends import MockBackend, Reply
from np_registered.config import load_config, load_prompts

CFG, PR = load_config(), load_prompts()


def test_eval_suffix_names_who_screened():
    assert stages.eval_suffix("gemma", None) == ""
    assert stages.eval_suffix("gemma", "gemma") == ""
    assert stages.eval_suffix("qwen38", "gemma") == "_gemma"


def test_cross_screening_writes_separate_logs_with_identical_batches(tmp_path):
    alloc = stages.allocate(CFG, 2)
    be = MockBackend()
    orgs = stages.run_generation(CFG, PR, be, tmp_path, "w", alloc, 4, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    v_reg = stages.run_evaluation(CFG, PR, MockBackend(model="ev-a"), tmp_path, "w", props, 4,
                                  progress=lambda *_: None, evaluator="a")
    v_x = stages.run_evaluation(CFG, PR, MockBackend(model="ev-b"), tmp_path, "w", props, 4,
                                progress=lambda *_: None, evaluator="b")
    assert (tmp_path / "votes_a.jsonl").exists() and (tmp_path / "votes_b.jsonl").exists()
    assert not (tmp_path / "votes.jsonl").exists()
    # the same batches in the same order for both evaluators; separate call logs
    key = lambda v: (v["role"], v["batch"], v["proposal_id"])
    assert sorted(map(key, v_reg)) == sorted(map(key, v_x))
    la = [json.loads(l) for l in open(tmp_path / "calls_evaluation_a.jsonl")]
    lb = [json.loads(l) for l in open(tmp_path / "calls_evaluation_b.jsonl")]
    assert {r["model_returned"] for r in la} == {"ev-a"} and {r["model_returned"] for r in lb} == {"ev-b"}
    assert all(r["meta"]["evaluator"] == "a" for r in la if "meta" in r)


def test_cli_mock_line_with_other_evaluator(tmp_path, monkeypatch):
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    arm = next(a for a, s in CFG["arms"].items() if s.get("evaluator") not in (None, a))
    ev = CFG["arms"][arm]["evaluator"]
    for cmd in (["generate"], ["evaluate"], ["evaluate", "--evaluator", arm], ["judge"]):
        cli.main(cmd + ["--arm", arm, "--mock", "--smoke", "2"])
    d = tmp_path / "smoke" / f"{arm}-mock"
    assert (d / f"votes_{ev}.jsonl").exists() and (d / "votes.jsonl").exists()   # registered + self-screening
    cli.main(["analyze", "--arm", arm, "--mock", "--smoke", "2"])
    cli.main(["analyze", "--arm", arm, "--mock", "--smoke", "2", "--evaluator", arm])
    j = CFG["judging"]["primary"]
    reg = json.loads((d / "results" / f"analysis_{j}.json").read_text())
    cross = json.loads((d / "results" / f"analysis_{j}_eval-{arm}.json").read_text())
    assert reg["votes_file"] == f"votes_{ev}.jsonl" and reg["evaluator"] == ev
    assert cross["votes_file"] == "votes.jsonl" and cross["evaluator"] == arm


def test_line_models_and_preflight_skips_unloaded(monkeypatch, capsys, tmp_path):
    arm = next(a for a, s in CFG["arms"].items() if s.get("evaluator") not in (None, a))
    names = list(preflight.line_models(CFG, arm))
    assert names[0] == f"writer:{arm}" and names[1].startswith("evaluator:") and any("judge-primary" in n for n in names)
    # nothing loaded: every local model is reported as not loaded, and the check fails because nothing was checked
    monkeypatch.setattr(preflight, "loaded_identifiers", lambda: {})
    monkeypatch.setattr(preflight, "lmstudio_info", lambda: {})
    monkeypatch.setattr(preflight, "arm_dir", lambda name, smoke=False: tmp_path)
    assert preflight.preflight(CFG, PR, arm) is False
    out = capsys.readouterr().out
    assert "is not loaded now" in out and "PREFLIGHT FAILED" in out


def test_preflight_fails_when_served_files_differ_from_registered(monkeypatch, capsys, tmp_path):
    arm = next(a for a, s in CFG["arms"].items() if s.get("evaluator") not in (None, a))
    ident = CFG["arms"][arm]["model"]
    from np_registered.backends import Reply
    rel = CFG["arms"][arm]["weights_dir"].split("/.lmstudio/models/")[-1]
    monkeypatch.setattr(preflight, "loaded_identifiers", lambda: {ident: rel})
    monkeypatch.setattr(preflight, "loaded_settings", lambda: {ident: dict(CFG["arms"][arm]["load"])})
    monkeypatch.setattr(preflight, "lmstudio_info", lambda: {})
    monkeypatch.setattr(preflight, "arm_dir", lambda name, smoke=False: tmp_path)
    monkeypatch.setattr(preflight, "_ping", lambda name, spec, mock: (True, {"returned": spec["model"]}))
    monkeypatch.setattr(preflight, "weights_hash", lambda d: {"model.safetensors": "aa", "chat_template.jinja": "bb"})
    monkeypatch.setattr(preflight, "registered_files", lambda: {ident: {"model.safetensors": "aa", "chat_template.jinja": "cc"}})
    assert preflight.preflight(CFG, PR, arm) is False
    assert "chat_template.jinja" in capsys.readouterr().out
    monkeypatch.setattr(preflight, "registered_files", lambda: {ident: {"model.safetensors": "aa", "chat_template.jinja": "bb"}})
    assert preflight.preflight(CFG, PR, arm) is True

    # a look-alike folder loaded under the right identifier fails
    monkeypatch.setattr(preflight, "loaded_identifiers", lambda: {ident: rel + "-lookalike"})
    assert preflight.preflight(CFG, PR, arm) is False


def test_every_registered_local_model_has_a_load_recipe():
    arm = next(a for a, s in CFG["arms"].items() if s.get("evaluator") not in (None, a))
    for name, spec in preflight.line_models(CFG, arm).items():
        if spec["backend"] == "openai_compatible":
            assert set(spec["load"]) == {"context_length", "parallel"}, name
            assert spec["load"]["parallel"] == spec["concurrency"], name


def test_preflight_fails_when_loaded_settings_differ_from_the_recipe(monkeypatch, capsys, tmp_path):
    arm = next(a for a, s in CFG["arms"].items() if s.get("evaluator") not in (None, a))
    ident, recipe = CFG["arms"][arm]["model"], dict(CFG["arms"][arm]["load"])
    rel = CFG["arms"][arm]["weights_dir"].split("/.lmstudio/models/")[-1]
    monkeypatch.setattr(preflight, "loaded_identifiers", lambda: {ident: rel})
    monkeypatch.setattr(preflight, "lmstudio_info", lambda: {})
    monkeypatch.setattr(preflight, "arm_dir", lambda name, smoke=False: tmp_path)
    monkeypatch.setattr(preflight, "_ping", lambda name, spec, mock: (True, {"returned": spec["model"]}))
    monkeypatch.setattr(preflight, "weights_hash", lambda d: {"f": "aa"})
    monkeypatch.setattr(preflight, "registered_files", lambda: {ident: {"f": "aa"}})
    for loaded in ({**recipe, "parallel": recipe["parallel"] + 2},
                   {**recipe, "context_length": recipe["context_length"] // 2}):
        monkeypatch.setattr(preflight, "loaded_settings", lambda loaded=loaded: {ident: loaded})
        assert preflight.preflight(CFG, PR, arm) is False
        assert "reload it with the RUNBOOK's command" in capsys.readouterr().out
    monkeypatch.setattr(preflight, "loaded_settings", lambda: None)     # LM Studio could not report the settings
    assert preflight.preflight(CFG, PR, arm) is False
    monkeypatch.setattr(preflight, "loaded_settings", lambda: {ident: recipe})
    assert preflight.preflight(CFG, PR, arm) is True
    # a model without a recipe in the configuration is not checked
    assert preflight.recipe_mismatch({"model": "x"}, None) == []


def test_preflight_requires_registered_files(monkeypatch, tmp_path):
    cfg = load_config()
    spec = cfg['arms']['qwen38']
    ident = spec['model']
    monkeypatch.setattr(preflight, 'loaded_identifiers', lambda: {ident: spec['weights_dir'].split('/.lmstudio/models/')[-1]})
    monkeypatch.setattr(preflight, 'loaded_settings', lambda: {ident: spec['load']})
    monkeypatch.setattr(preflight, 'lmstudio_info', lambda: {})
    monkeypatch.setattr(preflight, 'arm_dir', lambda *a, **k: tmp_path)
    monkeypatch.setattr(preflight, '_ping', lambda *a: (True, {'returned': ident}))
    monkeypatch.setattr(preflight, 'weights_hash', lambda *a: {'model.gguf': 'registered-content'})
    monkeypatch.setattr(preflight, 'registered_files', lambda: {})
    detail = {}
    assert not preflight.preflight(cfg, load_prompts(), 'qwen38', only=ident, detail=detail)
    assert detail['needs_person']


@pytest.mark.parametrize('text, stop', [('not JSON', 'end_turn'), ('{"ok":""}', 'end_turn'), ('{"other":"yes"}', 'end_turn'),
                                        ('["yes"]', 'end_turn'), ('{"ok":"yes"}', 'refusal'), ('{"ok":"yes"}', 'length')])
def test_preflight_ping_checks_schema_and_completion(monkeypatch, text, stop):
    be = SimpleNamespace(complete=lambda *a: Reply(True, text, stop, 'm', {}, {}, {}, 0), describe=lambda: {})
    monkeypatch.setattr(preflight, 'make_backend', lambda *a, **k: be)
    assert not preflight._ping('writer', {'backend': 'openai_compatible', 'model': 'm'}, False)[0]


@pytest.mark.parametrize('text', ['{"ok":"yes"}', '{"ok": "Yes."}'])
def test_preflight_ping_accepts_any_wording_of_a_schema_valid_answer(monkeypatch, text):
    """The ping checks the schema round-trip, not the model's wording: a reload loop over "Yes" would stop a run."""
    be = SimpleNamespace(complete=lambda *a: Reply(True, text, 'stop', 'm', {}, {}, {}, 0), describe=lambda: {})
    monkeypatch.setattr(preflight, 'make_backend', lambda *a, **k: be)
    assert preflight._ping('writer', {'backend': 'openai_compatible', 'model': 'm'}, False)[0]


def test_preflight_checks_the_api_judge_only_when_named(monkeypatch, capsys, tmp_path):
    """Before the local stages the API second judge is skipped (checked when it runs); named with --only, its model is
    pinged now, so the key, the account, and the model id can be confirmed before filing."""
    monkeypatch.setattr(preflight, "loaded_identifiers", lambda: {})
    monkeypatch.setattr(preflight, "lmstudio_info", lambda: {})
    monkeypatch.setattr(preflight, "arm_dir", lambda name, smoke=False: tmp_path)
    second = CFG["judges"][CFG["judging"]["second"]]
    assert second["backend"] != "openai_compatible"
    pinged = []
    monkeypatch.setattr(preflight, "_ping", lambda name, spec, mock: (pinged.append(name), (True, {"returned": spec["model"]}))[1])
    assert preflight.preflight(CFG, PR, "qwen38", mock=True) is True
    name = f"judge-second:{CFG['judging']['second']}"
    assert name not in pinged and "checked when it runs" in capsys.readouterr().out   # skipped before the local stages
    pinged.clear()
    assert preflight.preflight(CFG, PR, "qwen38", mock=True, only=second["model"]) is True
    assert pinged == [name]                                                            # named: checked now, alone
