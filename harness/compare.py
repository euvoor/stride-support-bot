"""Compare two harness runs: what got fixed, what broke, and what is flaky.

Each run is a deepeval run ID, such as main-prompt-v2, or a saved run file.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

API = "https://api.confident-ai.com/v1/test-runs"
GOLDENS = json.loads((Path(__file__).parent / "goldens.json").read_text())
REPEATS = 3  # the -r value of deepeval test run


def fetch(identifier):
    import requests
    from dotenv import load_dotenv

    load_dotenv()
    # runs come newest first, so the first match is the latest run with this ID
    headers = {"CONFIDENT_API_KEY": os.environ["CONFIDENT_API_KEY"]}
    page = 1
    while True:
        params = {"page": page, "pageSize": 50}
        data = requests.get(API, headers=headers, params=params, timeout=30)
        data = data.json()["data"]
        for run in data["testRuns"]:
            if run["identifier"] == identifier:
                run = requests.get(f"{API}/{run['id']}", headers=headers, timeout=30)
                return run.json()["data"]["testCases"]
        if page * data["pageSize"] >= data["totalTestRuns"]:
            sys.exit(f"No run with the ID {identifier} in Confident AI")
        page += 1


def load(name, allow_legacy=False):
    if Path(name).is_file():
        run = json.loads(Path(name).read_text())  # CI saves its run as a file
        name, cases = run["identifier"], run["testCases"]
    else:
        cases = fetch(name)
    # DeepEval saves pytest's name, including the golden and repeat parameters.
    expected = {
        g["input"]: {f"test_support_bot[golden{i}-{r}-{REPEATS}]" for r in range(1, REPEATS + 1)}
        for i, g in enumerate(GOLDENS)
    }
    legacy = allow_legacy and bool(cases) and all("name" not in case for case in cases)
    if legacy:
        print(f"Warning: {name}: legacy baseline identity coverage is unverified; regenerate it.",
              file=sys.stderr)
    results = {g["input"]: [] for g in GOLDENS}
    observed = {q: Counter() for q in results}
    errors = []
    for case in cases:
        question = case.get("input")
        if not isinstance(question, str) or question not in results:
            errors.append(f"unknown question: {question!r}")
            continue
        if type(case.get("success")) is not bool:
            errors.append(f"non-boolean result: {question}")
            continue
        results[question].append(case["success"])
        if not legacy:
            identity = case.get("name")
            if not isinstance(identity, str) or identity not in expected[question]:
                errors.append(f"missing or unexpected repeat identity {identity!r}: {question}")
                continue
            observed[question][identity] += 1
    for question, passes in results.items():
        if len(passes) != REPEATS:
            errors.append(f"{len(passes)} of {REPEATS} results: {question}")
        if not legacy:
            for identity in sorted(expected[question]):
                count = observed[question][identity]
                if count != 1:
                    kind = "missing" if count == 0 else "duplicate"
                    errors.append(f"{kind} repeat {identity} ({count} results): {question}")
    return name, results, errors


def status(passes):
    # a lost run must not hide inside "always pass", so count them
    if len(passes) != REPEATS:
        return "error"
    if all(passes):
        return "always pass"
    if not any(passes):
        return "always fail"
    return "flaky"


def summary(name, results):
    counts = defaultdict(int)
    for passes in results.values():
        counts[status(passes)] += 1
    passed = sum(sum(p) for p in results.values())
    total = sum(len(p) for p in results.values())
    print(
        f"{name}: {passed} of {total} passed | "
        f"always pass {counts['always pass']} | "
        f"always fail {counts['always fail']} | flaky {counts['flaky']} | "
        f"error {counts['error']}"
    )


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("old")
parser.add_argument("new")
parser.add_argument("--allow-legacy-baseline", action="store_true",
                    help="allow an old baseline with no names; its identity coverage remains unverified")
args = parser.parse_args()
old_name, old, old_errors = load(args.old, allow_legacy=args.allow_legacy_baseline)
new_name, new, new_errors = load(args.new)
if old_errors or new_errors:
    for name, errors in ((old_name, old_errors), (new_name, new_errors)):
        if errors:
            print(f"{name}: invalid run ({len(errors)} errors)")
            for error in errors:
                print(f"  {error}")
    sys.exit(1)
summary(old_name, old)
summary(new_name, new)

checks = {
    "Fixed": lambda a, b: a != "always pass" and b == "always pass",
    "Regressions": lambda a, b: a == "always pass" and b == "always fail",
    "Now flaky, read these": lambda a, b: a == "always pass" and b == "flaky",
    "Still failing": lambda a, b: b == "always fail",
}
for label, check in checks.items():
    rows = [q for q in new if q in old and check(status(old[q]), status(new[q]))]
    print(f"\n{label} ({len(rows)})")
    for q in rows:
        print(f"  {status(old[q]):11} -> {status(new[q]):11}  {q}")

errors = [q for q in new if status(new[q]) == "error"]
print(f"\nErrors, missing results ({len(errors)})")
for q in errors:
    print(f"  {len(new[q])} of {REPEATS} results  {q}")

# fail CI when something that always passed now always fails, or when a
# result is missing; one flaky run is often the judge, so a person reads those
regressions = [q for q in new if checks["Regressions"](status(old[q]), status(new[q]))]
sys.exit(1 if regressions or errors else 0)
