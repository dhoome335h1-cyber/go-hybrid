"""Regression tests for unexpected checker process exits in the corpus harness.

Run from the repository root:
    python -m unittest discover -s tests -p test_corpus_harness_process_exit.py -v

The mock changes only subprocess.run; the harness itself is imported unchanged.
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HARNESS_FILE = Path(__file__).resolve().parents[1] / "tools" / "corpus_harness.py"
spec = importlib.util.spec_from_file_location("corpus_harness", HARNESS_FILE)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


def fake_checker(returncode, verdict="accept", errors=None, stderr=""):
    payload = {"summary": {"verdict": verdict}, "diagnostics": errors or []}
    return subprocess.CompletedProcess(
        args=["hyb", "check", "fixture.hy", "--json"],
        returncode=returncode,
        stdout=json.dumps(payload),
        stderr=stderr,
    )


class CheckerExitStatusTests(unittest.TestCase):
    def test_accept_exit_zero_keeps_working(self):
        with patch.object(harness.subprocess, "run", return_value=fake_checker(0)):
            summary, diagnostics = harness.run_checker("hyb", "fixture.hy")
        self.assertEqual(summary["verdict"], "accept")
        self.assertEqual(diagnostics, [])

    def test_reject_exit_one_keeps_working(self):
        diagnostics = [{"severity": "error", "tier0_rule": "A1", "code": "HYB-E3001"}]
        with patch.object(
            harness.subprocess,
            "run",
            return_value=fake_checker(1, "reject", diagnostics),
        ):
            summary, output = harness.run_checker("hyb", "fixture.hy")
        self.assertEqual(summary["verdict"], "reject")
        self.assertEqual(output, diagnostics)

    def test_unexpected_exit_two_rejected_despite_correct_json(self):
        with patch.object(harness.subprocess, "run", return_value=fake_checker(2, stderr="oops")):
            with self.assertRaisesRegex(RuntimeError, "exit 2"):
                harness.run_checker("hyb", "fixture.hy")

    def test_unexpected_exit_101_rejected_despite_correct_json(self):
        with patch.object(harness.subprocess, "run", return_value=fake_checker(101)):
            with self.assertRaisesRegex(RuntimeError, "exit 101"):
                harness.run_checker("hyb", "fixture.hy")

    def test_main_returns_disagreement_for_unexpected_checker_exit(self):
        # JSON from a failed checker must not yield a misleading 1/1 agreement.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "01-example.hy").write_text(
                "// EXPECTED-VERDICT: ACCEPT\nfn main() {}\n", encoding="utf-8"
            )
            capture = io.StringIO()
            with (
                patch.object(sys, "argv", ["harness", "--bin", sys.executable, "--corpus", tmp]),
                patch.object(harness.subprocess, "run", return_value=fake_checker(2, stderr="fault")),
                contextlib.redirect_stdout(capture),
            ):
                result = harness.main()
        self.assertEqual(result, 1)
        self.assertIn("harness-error", capture.getvalue())
        self.assertIn("verdict agreement: 0/1", capture.getvalue())


if __name__ == "__main__":
    unittest.main()
