"""Prompt builders. Pure functions of the registered prompt files; no other text reaches a model.

No system prompt is used: the whole prompt is a single user message.
"""
from __future__ import annotations

import json

from .config import Prompts


def peer_block(prompts: Prompts, seniors: list[dict]) -> str:
    """Seniors' stance and reasoning, never their proposals."""
    names = prompts.roles["display_name"]
    return "\n\n".join(f"{names[s['role']]} (stance {s['stance']}/100): {s['reasoning']}" for s in seniors)


def generation_prompt(prompts: Prompts, role: str, seniors: list[dict] | None) -> str:
    """Polyarchy: seniors is None or []. Hierarchy: every senior's stance and reasoning, in seniority order."""
    parts = [prompts.roles["card"][role], prompts.policy]
    if seniors:
        parts.append(f"{prompts.hierarchy_peer_intro}\n\n{peer_block(prompts, seniors)}")
    parts += [prompts.stance_task, prompts.generation_task]
    return "\n\n".join(parts)


def proposal_text(p: dict) -> str:
    """The text evaluators and judges read."""
    return f"{p['title'].strip()}. {p['what'].strip()} {p['how'].strip()} {p['why'].strip()}"


def items_json(items: list[dict]) -> str:
    return json.dumps([{"id": it["id"], "text": it["text"]} for it in items], ensure_ascii=False, indent=2)


def evaluation_prompt(prompts: Prompts, role: str, items: list[dict]) -> str:
    tail = prompts.evaluation_items.replace("{n}", str(len(items))).replace("{items}", items_json(items))
    return "\n\n".join([prompts.roles["card"][role], prompts.policy, prompts.evaluation_task, tail])


def judge_plan(cfg: dict, blind_id: str, reading: int) -> list[tuple[str, tuple[str, str]]]:
    """The order of one judge call (PROTOCOL.md 4.4): the three dimensions in a random order, each followed by
    its two subscales in a random order; seeded by (design.seeds.judge_order, the proposal's blind id, the reading), so it
    is reproducible and differs between proposals and readings. Returns [(dimension, (subscale, subscale)), ...]."""
    import random
    from .schemas import JUDGE_DIMENSIONS
    rng = random.Random(f"{cfg['design']['seeds']['judge_order']}|{blind_id}|{reading}")
    dims = list(JUDGE_DIMENSIONS)
    rng.shuffle(dims)
    plan = []
    for d in dims:
        pair = list(JUDGE_DIMENSIONS[d])
        rng.shuffle(pair)
        plan.append((d, tuple(pair)))
    return plan


def judge_prompt_all(prompts: Prompts, items: list[dict], plan: list[tuple[str, tuple[str, str]]]) -> str:
    """One call rates all six subscales of one proposal (PROTOCOL.md 4.4), in the order of `plan`: the rater
    instruction, the Article 12 text, the stated problem with the decision frame, the dimension definitions, then each
    dimension's two anchored subscales in the plan's order (Dean et al., 2006, Appendices A and B), the protocol, and the
    proposal."""
    subs = [s for _, pair in plan for s in pair]
    head = ("DIMENSIONS TO RATE, IN THIS ORDER: " + "; ".join(f"{d} ({', '.join(pair)})" for d, pair in plan)
            + "\nSUBSCALES IN ORDER: " + ", ".join(subs))
    blocks = "\n".join(f"{d.upper()}\n" + "\n".join(prompts.judge_anchors[x] for x in pair) for d, pair in plan)
    tail = (prompts.judge_items.replace("{n}", str(len(items))).replace("{items}", items_json(items))
            .replace("{subscales}", ", ".join(subs)))
    return "\n\n".join([prompts.judge_persona, prompts.policy, prompts.judge_problem, prompts.judge_rubric,
                        head + "\n" + blocks, prompts.judge_protocol, tail])
