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
python compare.py main-prompt-v2 my-change   # run IDs from Confident AI, exits 1 on regressions
```

CI runs the harness on every pull request that changes `stride/` or the goldens.
