# Run book

How to run the study. Read PROTOCOL.md first. Every command is run from this folder. The writers, evaluators, and
primary judge run locally through LM Studio, offline; the second judge (an Anthropic model) runs afterwards through the
Message Batches API, with ANTHROPIC_API_KEY in `.env`.

Two experiments, each an "arm" named after its writer (PROTOCOL.md 5.2):
- main experiment `qwen38`: Qwen 3.8 writes, Gemma 4 evaluates (votes in `data/qwen38/votes_gemma.jsonl`);
- second experiment `gemma`: Gemma 4 writes, Qwen 3.8 evaluates (votes in `data/gemma/votes_qwen38.jsonl`).

## 1. Setup

```bash
uv sync                                   # Python and the pinned packages (uv.lock), once, with the internet on
uv run --group dev python -m pytest -q    # the tests
```
After `uv sync`, the runner calls uv in offline mode (`uv run --offline`), so nothing needs the network.

LM Studio serves one model at a time from the folders in config/study.yaml (`weights_dir`); the three folders and the
template line each one adds are described in PROTOCOL.md 5.3, and config/model_files.json lists the SHA-256 of every file
in them. In LM Studio's settings, automatic engine updates and just-in-time model loading must be off (the runner stops
if either is on). The runner loads each model itself, with its recipe:

| model | load command |
|---|---|
| Qwen 3.8 27B | `lms load qwen3.8-27b-medium --identifier qwen38 -c 49152 --parallel 4 -y` |
| Gemma 4 31B | `lms load gemma-4-31b-it-think --identifier gemma4 -c 49152 --parallel 4 -y` |
| Muse Glimmer 30B | `lms load muse-glimmer-30b-medium --identifier glimmer -c 98304 --parallel 12 -y` |

`preflight` checks every loaded model against its recipe and its registered files before each stage. With other model
files, run `uv run python -m np_registered register-models` first to record them.

## 2. The run

Switch the network off and start, from a terminal window that stays open for the whole run:

```bash
./run.sh
```

It runs every stage of both experiments in the registered order (PROTOCOL.md 4.5): the main experiment through its
primary judge, its readings decision, its internal pilot, and any extension wave, then the second experiment the same
way. It loads each model with its recipe, checks it with preflight, keeps the computer awake, and recovers from LM
Studio failures by itself (restart the server, reload, resume; at most 5 times per stage). It ends with "OFFLINE PART
FINISHED". Then switch the network on, put ANTHROPIC_API_KEY into `.env`, and run

```bash
./run.sh second-judge
```

which sends one small request to check the model, has the second judge rate both experiments in batches (four readings,
its readings decision, the rest), and then writes the manifests and runs the analyses with each judge's categories. It
ends with "RUN FINISHED".

The window prints a progress panel every 5 minutes: the state, the step, a bar per stage, seconds per call, the time
left, and how long ago the last answer arrived. `./run.sh progress` shows it at any time from a second window.

Interrupting is safe: closing the window or a crash ends the process, and `./run.sh` again resumes without repeating a
completed call. Only one runner can work in a data folder at a time.

## 3. When the run stops

The run stops only when continuing would be wrong; the reason is on the screen and at the end of `data/run.log`.

| message | what to do |
|---|---|
| `STOPPED: ... a registered stop (reserves used up)` | do not resume; more organizations of one structure failed than there are replacements (PROTOCOL.md 8.3) |
| `STOPPED: preflight before <stage>: the loaded model is not the registered one` | a model folder changed; restore the registered files |
| `STOPPED: LM Studio settings changed` | turn engine updates and just-in-time loading off again, then `./run.sh` |
| `STOPPED: only N GB of disk free` | free space outside `data/`, then `./run.sh` |
| `STOPPED: <step> failed six times` | read the end of `data/run.log` and `data/lmstudio_logs/`, fix the cause (memory, a crashed engine), then `./run.sh` |
| `STOPPED: ANTHROPIC_API_KEY is not set` | put the key into `.env`, then `./run.sh second-judge` |

Unusable answers never stop the run; they are counted and reported (PROTOCOL.md 8.1).

## 4. Rules during the run

- Do not compute or inspect any outcome by structure before both experiments and both judges are complete. `status` is
  safe (calls, validity, tokens); readings_<judge>.json and extension.json hold pooled quantities only.
- Do not edit config/study.yaml, prompts/, PROTOCOL.md, or src/ after registration. A needed change is a deviation:
  record it in DEVIATIONS.md (date, what, why, which data are affected) before continuing.
- Never edit or delete anything in `data/`; the logs are append-only.
- The key lives only in `.env` (not committed) or the environment.

## 5. Results

`data/<arm>/results/` holds `analysis_<judge>.json` and a readable `REPORT_<judge>.md` for each judge, and the audit files
of failed attempts. The main experiment's report with the primary judge is the confirmatory result; the second
experiment is the replication; the second judge's reports repeat every test (PROTOCOL.md 7).

## 6. After the run: the archive, the data commit, the deposit

The runner zips the whole data folder into `archive/` twice: `data_offline_<time>.zip` when the offline part ends and
`data_final_<time>.zip` at RUN FINISHED. They are exact copies, kept locally as backups; the final one is the file
deposited in the ResearchBox box. `archive/` is never committed.

The data folder itself is committed to this repository after the run, as written, with one exception: the raw call
logs (`calls_*.jsonl`, the largest files) are committed in compressed form, because GitHub refuses a file over 100 MB.

```bash
./run.sh pack        # writes calls_<stage>.jsonl.gz next to each log (split into .partNN below 95 MB when needed)
git add data
git commit -m "Data"
git push
```

The uncompressed logs stay on disk and out of git (.gitignore). To read a compressed log: `gunzip -k <name>.jsonl.gz`;
if it is in parts: `cat <name>.jsonl.gz.part* > <name>.jsonl.gz` first. Nothing in `data/` is ever edited.

## 7. Commands one by one

`./run.sh` runs these in order; each is resumable and safe to repeat.

```bash
uv run python -m np_registered preflight --arm qwen38 --only qwen38   # check the loaded model
uv run python -m np_registered allocate --arm qwen38          # the seeded allocation and the replacements
uv run python -m np_registered generate --arm qwen38          # generation (the writer loaded)
uv run python -m np_registered evaluate --arm qwen38          # evaluation (the evaluator loaded)
uv run python -m np_registered judge    --arm qwen38          # the primary judge's first four readings (judge loaded)
uv run python -m np_registered readings-check --arm qwen38    # the readings rule -> readings_glimmer.json
uv run python -m np_registered judge    --arm qwen38          # the remaining readings, if any
uv run python -m np_registered extend-check --arm qwen38      # the internal pilot -> extension.json
# if extension.json extends: generate, evaluate, and judge again (only the new organizations)
uv run python -m np_registered judge --arm qwen38 --judge claude   # the second judge (and its readings-check), online
uv run python -m np_registered manifest --arm qwen38          # hashes and versions
uv run python -m np_registered analyze  --arm qwen38          # the registered tests (refuses until every stage is done)
uv run python -m np_registered analyze  --arm qwen38 --judge claude
uv run python -m np_registered status   --arm qwen38          # progress and validity, at any time
```

The same with `--arm gemma` for the second experiment. Other options: `--evaluator <arm>` (cross-evaluation, not
registered), `--concurrency N`, `--smoke N` (a test run of N organizations per structure, written outside this folder:
`./run.sh --smoke N`, then `./run.sh second-judge --smoke N`; the same order, panel, and zips as the registered run,
marked as not data), and `--mock` (a deterministic fake model, for testing the code).
