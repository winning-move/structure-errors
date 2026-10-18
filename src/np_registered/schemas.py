"""Output schemas and the client-side validation every answer must pass before it is used (PROTOCOL.md 8.2).

Numeric ranges are not sent (the endpoints do not enforce them); they are checked here. The number of items of each
list is sent to the local server as minItems = maxItems (with_count), which its grammar enforces, so an answer cannot
return an empty list; the API backend strips the item counts (not supported there).
"""
from __future__ import annotations

import copy
import re

GEN_ITEM = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "what": {"type": "string"},
                   "how": {"type": "string"}, "why": {"type": "string"}},
    "required": ["title", "what", "how", "why"],
    "additionalProperties": False,
}

GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "stance": {"type": "integer"},
        "proposals": {"type": "array", "items": GEN_ITEM},
    },
    "required": ["reasoning", "stance", "proposals"],
    "additionalProperties": False,
}

VOTE_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "rationale": {"type": "string"},
        "decision": {"type": "string", "enum": ["approve", "reject"]},
        "promise": {"type": "integer"},
    },
    "required": ["id", "rationale", "decision", "promise"],
    "additionalProperties": False,
}

EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {"screenings": {"type": "array", "items": VOTE_ITEM}},
    "required": ["screenings"],
    "additionalProperties": False,
}

JUDGE_DIMENSIONS = {  # the three dimensions the categories use, each with its two subscales (Dean et al., 2006, Table 11)
    "novelty": ("originality", "paradigm_relatedness"),
    "workability": ("acceptability", "implementability"),
    "relevance": ("applicability", "effectiveness"),
}

JUDGE_SCALES = {  # subscale: (min, max); specificity is not rated
    "originality": (1, 4), "paradigm_relatedness": (1, 4),
    "acceptability": (1, 4), "implementability": (1, 4),
    "applicability": (1, 4), "effectiveness": (1, 4),
}


JUDGE_SUBSCALES = tuple(s for pair in JUDGE_DIMENSIONS.values() for s in pair)   # the six rated subscales, Dean's order


def judge_schema_for(subscales: tuple) -> dict:
    """The output schema of one judge call: per proposal the id and, for each subscale in the order the call shows them,
    one sentence of evidence first and then the integer level (PROTOCOL.md 4.4). A call rates all six subscales of one
    proposal in the call's random order, and the schema lists them in that order. Ranges are checked client-side
    (check_subscales)."""
    subscales = tuple(subscales)
    assert subscales and set(subscales) <= set(JUDGE_SUBSCALES) and len(set(subscales)) == len(subscales), subscales
    props, req = {"id": {"type": "string"}}, ["id"]
    for s in subscales:
        props[f"{s}_evidence"] = {"type": "string"}
        props[s] = {"type": "integer"}
        req += [f"{s}_evidence", s]
    item = {"type": "object", "properties": props, "required": req, "additionalProperties": False}
    return {"type": "object", "properties": {"ratings": {"type": "array", "items": item}},
            "required": ["ratings"], "additionalProperties": False}


JUDGE_SCHEMA = judge_schema_for(JUDGE_SUBSCALES)      # the shape of a judge call (all six subscales, Dean's order)


def with_count(schema: dict, key: str, n: int) -> dict:
    """The schema with the list `key` fixed to exactly n items (minItems = maxItems = n)."""
    out = copy.deepcopy(schema)
    out["properties"][key] = {**out["properties"][key], "minItems": n, "maxItems": n}
    return out


class Invalid(ValueError):
    """A completed response that does not meet the registered validity rules."""


_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


def words(s: str) -> list[str]:
    return _WORD.findall(s or "")


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _check_text(s, min_words: int, min_unique: int, what: str):
    if not isinstance(s, str):
        raise Invalid(f"{what}: not a string")
    w = words(s)
    if len(w) < min_words:
        raise Invalid(f"{what}: {len(w)} words < {min_words}")
    if len({x.lower() for x in w}) < min_unique:
        raise Invalid(f"{what}: fewer than {min_unique} distinct words")


def validate_generation(obj: dict, vcfg: dict, n_proposals: int = 3) -> dict:
    if not isinstance(obj, dict):
        raise Invalid("not an object")
    _check_text(obj.get("reasoning"), vcfg["min_words_reasoning"], vcfg["min_unique_words"], "reasoning")
    st = obj.get("stance")
    if not _is_int(st) or not 0 <= st <= 100:
        raise Invalid(f"stance {st!r} not an integer in 0-100")
    props = obj.get("proposals")
    if not isinstance(props, list) or len(props) != n_proposals:
        raise Invalid(f"expected exactly {n_proposals} proposals, got {len(props) if isinstance(props, list) else props!r}")
    seen = set()
    for i, p in enumerate(props):
        if not isinstance(p, dict) or set(p) != {"title", "what", "how", "why"}:
            raise Invalid(f"proposal {i}: wrong fields")
        for k in ("title", "what", "how", "why"):
            if not isinstance(p[k], str) or not p[k].strip():
                raise Invalid(f"proposal {i}: empty {k}")
        full = " ".join(p[k] for k in ("title", "what", "how", "why"))
        _check_text(full, vcfg["min_words_proposal"], vcfg["min_unique_words"], f"proposal {i}")
        key = re.sub(r"\s+", " ", full.lower()).strip()
        if key in seen:
            raise Invalid(f"proposal {i}: duplicate of an earlier proposal")
        seen.add(key)
    return obj


def validate_items(obj: dict, key: str, expected_ids: list[str], item_check) -> dict:
    """Every expected id exactly once, nothing else; order is not required (results are keyed by id)."""
    if not isinstance(obj, dict) or not isinstance(obj.get(key), list):
        raise Invalid(f"missing list '{key}'")
    got = [it.get("id") if isinstance(it, dict) else None for it in obj[key]]
    if sorted(map(str, got)) != sorted(expected_ids) or len(set(got)) != len(got):
        raise Invalid(f"ids returned {got} do not match ids sent {expected_ids}")
    for it in obj[key]:
        item_check(it)
    return obj


def check_vote(it: dict):
    if it.get("decision") not in ("approve", "reject"):
        raise Invalid(f"{it.get('id')}: decision {it.get('decision')!r}")
    if not _is_int(it.get("promise")) or not 0 <= it["promise"] <= 100:
        raise Invalid(f"{it.get('id')}: promise {it.get('promise')!r}")
    if not isinstance(it.get("rationale"), str) or not it["rationale"].strip():
        raise Invalid(f"{it.get('id')}: empty rationale")


def check_subscales(it: dict, subscales):
    """Every subscale rated in the call: an integer in range and a non-empty sentence of evidence each."""
    for s in subscales:
        lo, hi = JUDGE_SCALES[s]
        v = it.get(s)
        if not _is_int(v) or not lo <= v <= hi:
            raise Invalid(f"{it.get('id')}: {s}={v!r} outside {lo}-{hi}")
        ev = it.get(f"{s}_evidence")
        if not isinstance(ev, str) or not ev.strip():
            raise Invalid(f"{it.get('id')}: empty evidence for {s}")
