"""Compare two harness runs: what got fixed, what broke, and what is flaky."""

import json
import sys
from collections import defaultdict
from pathlib import Path

GOLDENS = json.loads((Path(__file__).parent / "goldens.json").read_text())


def load(path):
    run = json.load(open(path))
    # a golden with no result means the app call failed before scoring
    results = {g["input"]: [] for g in GOLDENS}
    for case in run["testCases"]:
        results[case["input"]].append(case["success"])
    return run["identifier"], results


def status(passes):
    if not passes:
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

# fail CI only when something that always passed now always fails;
# one flaky run is often the judge, so a person reads those instead
regressions = [q for q in new if checks["Regressions"](status(old[q]), status(new[q]))]
sys.exit(1 if regressions else 0)
