# Stride support bot

A small AI support bot for a made-up shoe store, used in the
[Evals and Tracing series](https://www.linkedin.com/pulse/evals-tracing-101-tony-cueva-bravo-jlhae/).
Part 2, "Build Your Eval Harness", builds an eval harness around it.

- `stride/` is the app: a FastAPI server (`POST /chat`), a help center search, and the bot, traced with `confident-trace`.
- `harness/` is the eval harness: it calls the running app over HTTP, scores every answer with DeepEval, and compares runs.

## Run the app

```bash
cp .env.example .env   # add your OpenAI and Confident AI keys
pip install -r requirements.txt
uvicorn stride.server:app --port 8000
```

Or deploy it on Render with `render.yaml` (free plan).

## Follow Part 2

The tag `part-2-start` is the bot before the fixes, with the bugs that Part 2 finds.
To follow the guide step by step, copy in that bot and keep the latest harness.
`main` has the fixed bot.

```bash
git checkout part-2-start -- stride
```

## Run the harness

```bash
pip install -r harness/requirements.txt
cd harness
python send_traffic.py                # customer-style questions, traced in Confident AI
python pull_traces.py 24              # pull the last 24 hours of customer traces for review
deepeval test run test_harness.py -id my-change -r 3
python compare.py main-prompt-v2 my-change   # run IDs from Confident AI, exits 1 on regressions or missing results
```

CI runs the harness on every pull request that changes `stride/` or the goldens.

The comparator validates each question's exact three repeat names in both runs,
not just the number of results. It expects the names emitted by the harness's
`deepeval test run test_harness.py -r 3` command, such as
`test_support_bot[golden0-1-3]`. Keep the golden order and harness parameter names
the same between runs; regenerate the baseline when they change. Missing,
duplicate, unexpected or unnamed repeats fail comparison before scoring.

The checked-in historical `harness/baseline.json` contains only inputs and scores.
CI explicitly uses `--allow-legacy-baseline` for that file. This permits a wholly
unnamed old baseline with complete counts and warns that its identity coverage is
unverified. It never permits an unnamed candidate or a partly named baseline.
Replace the baseline with a fresh saved run to remove this exception; do not invent
repeat names for historical scores.

Run the comparator's offline regression tests without model calls or dependencies:

```bash
python -m unittest discover -s harness -p test_compare.py
```
