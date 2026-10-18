"""The registered (non-smoke) command path at full size on the mock model: allocate, the three stages, the
blinded extension check, the refusal of analyze before it, and analyze itself. Smoke runs never execute this path
(extend-check is skipped for them), so it is exercised here."""
import json
import time

import pytest

from np_registered import cli, stages
from np_registered.analysis import extension_candidates
from np_registered.backends import MockBackend
from np_registered.config import arm_dir, load_config, load_prompts


def test_registered_path_at_full_size(monkeypatch, tmp_path):
    monkeypatch.setenv("NP_DATA_DIR", str(tmp_path))
    cfg, pr = load_config(), load_prompts()
    n, arm = cfg["design"]["orgs_per_structure"], "qwen38"
    out = arm_dir(arm)
    cli.main(["allocate", "--arm", arm])
    alloc = stages.allocate(cfg, cfg["design"]["extension"]["max_per_structure"])
    quiet = lambda s: None
    t0 = time.time()
    stages.run_generation(cfg, pr, MockBackend(), out, arm, alloc, 4, n, progress=quiet)
    orgs = stages.registered_orgs(cfg, out, alloc, n)
    assert sum(o["structure"] == "hierarchy" for o in orgs) == n == sum(o["structure"] == "polyarchy" for o in orgs)
    props = stages.proposals_of(orgs)
    assert len(props) == 2 * n * 12
    stages.run_evaluation(cfg, pr, MockBackend(), out, arm, props, 4, progress=quiet, evaluator="gemma")
    floor = cfg["judging"]["readings"]["floor"]
    monkeypatch.setattr(cli, "_judge_backend", lambda cfg, judge, mock: MockBackend())
    def judge_with_rule(judge, judge_props, waves=None):
        with pytest.raises(SystemExit, match="is not complete"):
            cli.main(["readings-check", "--arm", arm, "--judge", judge])          # no readings yet
        stages.run_judge(cfg, pr, MockBackend(), out, arm, judge, judge_props, 4, progress=quiet, waves=waves)
        rows = stages.read_jsonl(out / f"ratings_{judge}.jsonl")
        assert {r["pass"] for r in rows} == set(range(1, floor + 1))                 # the floor first
        cli.main(["readings-check", "--arm", arm, "--judge", judge])                   # decides once
        rd = json.loads((out / f"readings_{judge}.json").read_text())
        assert floor <= rd["readings"] <= cfg["judging"]["readings"]["ceiling"] and "hierarchy" not in json.dumps(rd)
        cli.main(["readings-check", "--arm", arm, "--judge", judge])                   # idempotent
        assert json.loads((out / f"readings_{judge}.json").read_text())["decided_at"] == rd["decided_at"]
        monkeypatch.setattr(cli, "_judge_backend", lambda cfg, judge, mock: MockBackend())
        cli.main(["judge", "--arm", arm, "--judge", judge])                             # adds the remaining readings only
        rows = stages.read_jsonl(out / f"ratings_{judge}.jsonl")
        assert {r["pass"] for r in rows} == set(range(1, rd["readings"] + 1))
    judge_with_rule(cfg["judging"]["primary"], props)
    assert (out / "votes_gemma.jsonl").exists() and (out / f"ratings_{cfg['judging']['primary']}.jsonl").exists()
    # the registered order: no analysis before the extension decision
    with pytest.raises(SystemExit, match="extension.json is missing"):
        cli.main(["analyze", "--arm", arm])
    cli.main(["extend-check", "--arm", arm])
    ext = json.loads((out / "extension.json").read_text())
    assert ext["n_core"] == n and ext["target_per_structure"] in [n] + extension_candidates(cfg)
    assert len(ext["core_proposal_ids"]) == 2 * n * 12 and "decision" in ext
    cli.main(["status", "--arm", arm])
    # if the extension decision asks for more organizations (6.4), the same commands run only the new organizations
    target = ext["target_per_structure"]
    if target > n:
        monkeypatch.setattr(cli, "_arm_backend", lambda cfg, arm, mock: MockBackend())
        cli.main(["generate", "--arm", arm])
        cli.main(["evaluate", "--arm", arm])
        for judge in (cfg["judging"]["primary"],):
            cli.main(["judge", "--arm", arm, "--judge", judge])
        orgs2 = stages.registered_orgs(cfg, out, alloc, target)
        assert sum(o["structure"] == "hierarchy" for o in orgs2) == target
    # The second judge decides its readings only on the final sample (PROTOCOL.md 4.4, 4.5).
    second = cfg["judging"]["second"]
    final_props = stages.proposals_of(stages.registered_orgs(cfg, out, alloc, target))
    judge_with_rule(second, final_props, waves=[set(ext["core_proposal_ids"])])
    # no analysis before the second judge has rated the final sample (PROTOCOL.md 4.5), with either judge's categories
    sec = out / f"ratings_{cfg['judging']['second']}.jsonl"
    held = sec.with_suffix(".held")
    sec.rename(held)
    for extra in ([], ["--judge", cfg["judging"]["second"]]):
        with pytest.raises(SystemExit, match="not every stage is complete"):
            cli.main(["analyze", "--arm", arm, *extra])
    held.rename(sec)
    cli.main(["analyze", "--arm", arm])
    res = json.loads((out / "results" / f"analysis_{cfg['judging']['primary']}.json").read_text())
    for key in ("H1", "H2", "multiplicity", "rule_comparison", "power_check", "secondary", "readings"):
        assert key in res
    assert res["readings"]["judge"] == cfg["judging"]["primary"] and "readings" in res["readings"]
    assert res["H2"]["H2a_quality"]["n_hierarchy"] == target and 0 < res["rule_comparison"]["rule_comparison_quality"]["n_organizations"] <= 2 * n
    assert res["multiplicity"]["correction"] == "none"
    assert not res["smoke_test_not_data"]
    assert time.time() - t0 < 600


@pytest.fixture
def completed_cli(tmp_path, monkeypatch):
    cfg, pr = load_config(), load_prompts()
    cfg['design']['orgs_per_structure'] = 2
    cfg['design']['extension']['max_per_structure'] = 4
    monkeypatch.setattr(cli, 'load_config', lambda: cfg)
    monkeypatch.setattr(cli, 'arm_dir', lambda *a, **k: tmp_path)
    alloc = stages.allocate(cfg, 4)
    orgs = stages.run_generation(cfg, pr, MockBackend(), tmp_path, 'qwen38', alloc, 2, 2, progress=lambda *_: None)
    props = stages.proposals_of(orgs)
    (tmp_path / 'extension.json').write_text(json.dumps({'core_org_ids': [o['org_id'] for o in orgs],
        'core_proposal_ids': [p['proposal_id'] for p in props], 'target_per_structure': 2}))
    votes = [{'proposal_id': p['proposal_id'], 'role': role, 'decision': None} for p in props for role in pr.roles['order']]
    stages._write_jsonl(tmp_path / 'votes_gemma.jsonl', votes)
    for judge in (cfg['judging']['primary'], cfg['judging']['second']):
        rows = [{'proposal_id': p['proposal_id'], 'pass': k, 'missing': True} for p in props for k in range(1, 5)]
        stages._write_jsonl(tmp_path / f'ratings_{judge}.jsonl', rows)
        (tmp_path / f'readings_{judge}.json').write_text(json.dumps({'readings': 4}))
    called = []
    monkeypatch.setattr('np_registered.analysis.analyze', lambda *a, **k: called.append(True))
    monkeypatch.setattr('np_registered.report.write_report', lambda *a, **k: 'report')
    return cfg, props, called


@pytest.mark.parametrize('missing', ['role', 'reading', 'registered_votes'])
def test_analysis_gate_requires_complete_registered_stages(completed_cli, tmp_path, missing):
    cfg, props, called = completed_cli
    extra = []
    if missing == 'role':
        file = tmp_path / 'votes_gemma.jsonl'
        stages._write_jsonl(file, stages.read_jsonl(file)[1:])
    elif missing == 'reading':
        file = tmp_path / f"ratings_{cfg['judging']['second']}.jsonl"
        stages._write_jsonl(file, stages.read_jsonl(file)[1:])
    else:
        (tmp_path / 'votes.jsonl').write_bytes((tmp_path / 'votes_gemma.jsonl').read_bytes())
        (tmp_path / 'votes_gemma.jsonl').unlink()
        extra = ['--evaluator', 'qwen38']
    with pytest.raises(SystemExit, match='not every stage is complete'):
        cli.main(['analyze', '--arm', 'qwen38', *extra])
    assert not called


def test_analysis_gate_accepts_terminal_missing_outcomes(completed_cli):
    cfg, props, called = completed_cli
    cli.main(['analyze', '--arm', 'qwen38'])
    assert called == [True]


@pytest.mark.parametrize('command', ['judge', 'readings-check'])
@pytest.mark.parametrize('unfinished', ['extension', 'primary'])
def test_second_judge_waits_for_final_primary_sample(completed_cli, tmp_path, monkeypatch, command, unfinished):
    cfg, props, called = completed_cli
    second = cfg['judging']['second']
    (tmp_path / f'readings_{second}.json').unlink()
    if unfinished == 'extension':
        (tmp_path / 'extension.json').unlink()
    else:
        f = tmp_path / f"ratings_{cfg['judging']['primary']}.jsonl"
        stages._write_jsonl(f, stages.read_jsonl(f)[1:])
    backend_calls = []
    monkeypatch.setattr(cli, '_judge_backend', lambda *a, **k: backend_calls.append(True) or MockBackend())
    monkeypatch.setattr(stages, 'run_judge', lambda *a, **k: [])
    with pytest.raises(SystemExit, match='second judge requires'):
        cli.main([command, '--arm', 'qwen38', '--judge', second])
    assert not backend_calls


def test_extension_guidance_keeps_second_judging_before_analysis(completed_cli, tmp_path, monkeypatch, capsys):
    cfg, props, called = completed_cli
    (tmp_path / 'extension.json').unlink()
    monkeypatch.setattr('np_registered.analysis.extension_check', lambda *a, **k: {
        'target_per_structure': 4, 'decision': 'extend to 4 per structure', 'pooled': {}, 'power': {}})
    cli.main(['extend-check', '--arm', 'qwen38'])
    guidance = capsys.readouterr().out
    assert 'second judge' in guidance
    assert guidance.index('second judge') < guidance.rindex('analyze')
