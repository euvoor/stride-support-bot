"""Compare two harness runs: what got fixed, what broke, and what is flaky.

Each run is a deepeval run ID, such as main-prompt-v2, or a saved run file.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.confident-ai.com/v1/test-runs"
GOLDENS = json.loads((Path(__file__).parent / "goldens.json").read_text())
REPEATS = 3  # the -r value of deepeval test run


def fetch(identifier):
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


def load(name):
    if Path(name).is_file():
        run = json.load(open(name))  # CI saves its run as a file
        name, cases = run["identifier"], run["testCases"]
    else:
        cases = fetch(name)
    # a golden with a missing result means an app call failed before scoring
    results = {g["input"]: [] for g in GOLDENS}
    for case in cases:
        results[case["input"]].append(case["success"])
    return name, results


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


old_name, old = load(sys.argv[1])
new_name, new = load(sys.argv[2])
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
