"""Offline comparator regression tests: python -m unittest discover -s harness -p test_compare.py."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).parent
GOLDENS = json.loads((HERE / "goldens.json").read_text())


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            {"input": golden["input"], "success": True,
             "name": f"test_support_bot[golden{index}-{repeat}-3]"}
            for index, golden in enumerate(GOLDENS) for repeat in range(1, 4)
        ]

    def compare(self, new, old=None, *options):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("old.json", "new.json")]
            for path, cases in zip(paths, (self.cases if old is None else old, new)):
                path.write_text(json.dumps({"identifier": path.stem, "testCases": cases}))
            return subprocess.run(
                [sys.executable, str(HERE / "compare.py"), *map(str, paths), *options],
                capture_output=True, text=True,
            )

    def test_complete_and_reordered(self):
        self.assertEqual(self.compare(list(reversed(self.cases))).returncode, 0)

    def test_duplicate_replaces_missing_repeat(self):
        new = copy.deepcopy(self.cases)
        new[2] = copy.deepcopy(new[1])
        result = self.compare(new)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("duplicate", result.stdout)
        self.assertIn("missing repeat", result.stdout)
        self.assertIn("new: invalid run", result.stdout)
        self.assertNotIn("old: invalid run", result.stdout)
        self.assertNotIn("of 60 passed", result.stdout)

    def test_out_of_range_repeat(self):
        new = copy.deepcopy(self.cases)
        new[2]["name"] = "test_support_bot[golden0-4-3]"
        self.assertEqual(self.compare(new).returncode, 1)

    def test_identity_belongs_to_different_question(self):
        new = copy.deepcopy(self.cases)
        new[2]["name"] = new[5]["name"]
        self.assertEqual(self.compare(new).returncode, 1)

    def test_missing_and_extra_repeat(self):
        for cases in (self.cases[:-1], self.cases + [self.cases[0]]):
            with self.subTest(length=len(cases)):
                self.assertEqual(self.compare(cases).returncode, 1)

    def test_missing_identity(self):
        new = copy.deepcopy(self.cases)
        del new[0]["name"]
        self.assertEqual(self.compare(new).returncode, 1)

    def test_invalid_baseline(self):
        old = copy.deepcopy(self.cases)
        old[2] = copy.deepcopy(old[1])
        self.assertEqual(self.compare(self.cases, old).returncode, 1)

    def test_non_boolean_score(self):
        for value in (None, "true", 1):
            with self.subTest(value=value):
                new = copy.deepcopy(self.cases)
                new[0]["success"] = value
                self.assertEqual(self.compare(new).returncode, 1)

    def test_regression_still_fails(self):
        new = copy.deepcopy(self.cases)
        for case in new[:3]:
            case["success"] = False
        self.assertEqual(self.compare(new).returncode, 1)

    def test_flaky_still_reported_without_failure(self):
        new = copy.deepcopy(self.cases)
        new[0]["success"] = False
        result = self.compare(new)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Now flaky, read these (1)", result.stdout)

    def test_legacy_baseline_requires_explicit_option(self):
        old = [{"input": c["input"], "success": c["success"]} for c in self.cases]
        self.assertEqual(self.compare(self.cases, old).returncode, 1)
        result = self.compare(self.cases, old, "--allow-legacy-baseline")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("identity coverage is unverified", result.stderr)
        self.assertEqual(self.compare(old, old, "--allow-legacy-baseline").returncode, 1)

    def test_legacy_option_does_not_hide_partial_identity(self):
        old = copy.deepcopy(self.cases)
        del old[0]["name"]
        self.assertEqual(self.compare(self.cases, old, "--allow-legacy-baseline").returncode, 1)

    def test_legacy_option_keeps_count_and_candidate_checks(self):
        old = [{"input": c["input"], "success": c["success"]} for c in self.cases]
        for incomplete in (old[:-1], old + [old[0]], []):
            with self.subTest(length=len(incomplete)):
                self.assertEqual(
                    self.compare(self.cases, incomplete, "--allow-legacy-baseline").returncode, 1,
                )
        new = copy.deepcopy(self.cases)
        new[2] = copy.deepcopy(new[1])
        self.assertEqual(self.compare(new, old, "--allow-legacy-baseline").returncode, 1)

    def test_checked_in_baseline(self):
        old = json.loads((HERE / "baseline.json").read_text())["testCases"]
        self.assertEqual(self.compare(self.cases, old, "--allow-legacy-baseline").returncode, 0)

    def test_unknown_question(self):
        new = copy.deepcopy(self.cases)
        new[0]["input"] = "not a golden"
        result = self.compare(new)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown question", result.stdout)


if __name__ == "__main__":
    unittest.main()
