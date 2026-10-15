"""Regression tests for tools/job.py command-line arity validation."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


JOB_FILE = Path(__file__).with_name("job.py")
spec = importlib.util.spec_from_file_location("job", JOB_FILE)
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class JobCliArityTests(unittest.TestCase):
    def run_usage_error(self, argv):
        output = io.StringIO()
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                job.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("job.py actions dispatch", output.getvalue())

    def test_dispatch_missing_maxparallel_reports_usage(self):
        self.run_usage_error(
            ["job.py", "actions", "dispatch", "heavy", "abc", "check", "4"]
        )

    def test_dispatch_rejects_extra_arguments(self):
        self.run_usage_error(
            [
                "job.py", "actions", "dispatch", "heavy", "abc", "check",
                "4", "2", "extra",
            ]
        )

    def test_dispatch_exact_arity_parses_numeric_arguments(self):
        argv = [
            "job.py", "actions", "dispatch", "heavy", "abc", "check", "4", "2",
        ]
        with patch.object(sys, "argv", argv), patch.object(job, "actions_dispatch") as call:
            job.main()
        call.assert_called_once_with("heavy", "abc", "check", 4, 2)

    def test_wait_rejects_extra_arguments(self):
        self.run_usage_error(
            ["job.py", "kaggle", "wait", "5", "owner/kernel", "extra"]
        )

    def test_wait_accepts_documented_optional_slug(self):
        argv = ["job.py", "kaggle", "wait", "5", "owner/kernel"]
        with patch.object(sys, "argv", argv), patch.object(job, "kaggle_wait", return_value=0) as call:
            with self.assertRaises(SystemExit) as raised:
                job.main()
        self.assertEqual(raised.exception.code, 0)
        call.assert_called_once_with(5.0, "owner/kernel")

    def test_watch_rejects_extra_arguments(self):
        self.run_usage_error(["job.py", "actions", "watch", "123", "extra"])

    def test_watch_accepts_documented_optional_run_id(self):
        argv = ["job.py", "actions", "watch", "123"]
        with patch.object(sys, "argv", argv), patch.object(job, "actions_watch") as call:
            job.main()
        call.assert_called_once_with(123)


if __name__ == "__main__":
    unittest.main()
