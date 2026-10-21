"""Compare two harness runs: what got fixed, what broke, and what is flaky."""

import json
import sys
from collections import defaultdict


def load(path):
    run = json.load(open(path))
    results = defaultdict(list)
    for case in run["testCases"]:
        results[case["input"]].append(case["success"])
    return run["identifier"], results


def status(passes):
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
        f"always fail {counts['always fail']} | flaky {counts['flaky']}"
    )


old_name, old = load(sys.argv[1])
new_name, new = load(sys.argv[2])
summary(old_name, old)
summary(new_name, new)

checks = {
    "Fixed": lambda a, b: a != "always pass" and b == "always pass",
    "Regressions": lambda a, b: a == "always pass" and b != "always pass",
    "Still failing": lambda a, b: b == "always fail",
}
for label, check in checks.items():
    rows = [q for q in new if q in old and check(status(old[q]), status(new[q]))]
    print(f"\n{label} ({len(rows)})")
    for q in rows:
        print(f"  {status(old[q]):11} -> {status(new[q]):11}  {q}")
