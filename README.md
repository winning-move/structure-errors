# Organizational structure and the errors of generation and evaluation

**Start here: the [Interactive Explorer](https://winning-move.github.io/structure-errors/explorer/)**, with every
proposal, vote, rationale, and judge reading (the same file is `explorer/index.html`). The text below is the study's
description as deposited before data collection.

---

Does organizational structure change what an organization proposes, and does that change alter what the organization
approves? Artificial organizations of four LLM role agents (compliance officer, lab director, researcher, and engineer)
respond to Article 12 of the EU AI Act. In a hierarchy, juniors read the stances and reasoning of their seniors before
writing, and a proposal is approved only if all four evaluators approve; in a polyarchy, the roles write independently,
and one approval suffices. A blind judge rates every proposal on the anchored subscales of novelty, workability, and
relevance of Dean, Hender, Rodgers, and Santanen (2006), and each proposal is classified by Dean's categories: a quality
proposal (workability and relevance at least 6 on the 2-8 scale), a creative proposal (a quality proposal with novelty at
least 6), or a proposal below the quality threshold.

Hypotheses (PROTOCOL.md 2): H1, hierarchies generate a smaller proportion of proposals below the quality threshold; H2a
and H2b, hierarchies approve fewer quality proposals (omission errors) and fewer proposals below the quality threshold
(commission errors) when each structure evaluates its own proposals under its own rule (Sah and Stiglitz, 1986; Csaszar,
2012). Welch t-tests over organizations, each at alpha .05.

Design: 84 organizations per structure, extended once by an internal pilot for H2 to at most 168. In the main
experiment Qwen 3.8 27B writes and Gemma 4 31B evaluates; a second experiment swaps them. Muse Glimmer 30B is the primary
judge; Claude Sonnet 5.5 (Anthropic) is the second judge. Every local model runs offline from open-weight files.

| file | contents |
|---|---|
| PROTOCOL.md | the complete protocol: hypotheses, design, procedure, models, sample size, analysis, failures, assumptions |
| RUNBOOK.md | how to run the study |
| DEVIATIONS.md | every change after registration |
| config/study.yaml | every registered setting |
| config/model_files.json | the SHA-256 of every file each local model is served from |
| prompts/ | every text a model receives |
| src/np_registered/ | the study code: allocation, the three stages, validation, preflight, the analysis, and the runner |
| run.sh | the one command that runs the study |
| power/ | the planning numbers of PROTOCOL.md 6 |
| tests/ | tests on a deterministic fake model and synthetic data |
| data/ | after the run: every record the run wrote (RUNBOOK 6); the raw call logs in compressed form |

```bash
uv sync                                  # Python and the pinned packages
uv run --group dev python -m pytest -q   # the tests
./run.sh                                 # the local part of the study (RUNBOOK.md)
./run.sh second-judge                    # then, with the internet on: the second judge and the analyses
```

After the run the data folder is committed here as written (the raw call logs compressed) and deposited in the
study's ResearchBox box.
