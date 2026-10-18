#!/bin/sh
# The whole registered run with one command, without internet (RUNBOOK 2). From this folder:
#   ./run.sh               the registered run
#   ./run.sh --smoke 2     a test run (2 organizations per structure; written outside the study folder); then
#   ./run.sh second-judge --smoke 2   its online part (the second judge through the API; a small cost)
#   ./run.sh progress      the progress panel, read only, from a second window
#   ./run.sh pack          after RUN FINISHED: the raw call logs also in compressed form, so that data/ can be committed
cd "$(dirname "$0")"
exec caffeinate -i uv run --offline python -m np_registered.run_all "$@"
