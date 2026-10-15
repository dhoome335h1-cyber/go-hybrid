"""Regression tests for fail-closed Kaggle output fetching."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


JOB_FILE = Path(__file__).with_name("job.py")
spec = importlib.util.spec_from_file_location("job", JOB_FILE)
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class KaggleFetchTests(unittest.TestCase):
    def test_failed_download_cannot_promote_stale_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            jobdir = Path(temporary)
            stale = jobdir / "result" / "raw" / "old" / "summary.json"
            stale.parent.mkdir(parents=True)
            stale.write_text('{"stale": true}\n', encoding="utf-8")
            with patch.object(job, "sh", return_value=(7, "download failed")):
                status = job.kaggle_fetch(str(jobdir), "owner/kernel")
            self.assertEqual(status, 7)
            self.assertFalse((jobdir / "result" / "summary.json").exists())

    def test_success_without_summary_is_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(job, "sh", return_value=(0, "download complete")):
                status = job.kaggle_fetch(temporary, "owner/kernel")
        self.assertEqual(status, 1)

    def test_success_copies_summary_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            jobdir = Path(temporary)

            def download(_cmd, timeout=120, cwd=None):
                summary = jobdir / "result" / "raw" / "run" / "summary.json"
                summary.parent.mkdir(parents=True)
                summary.write_text(json.dumps({"ok": True}), encoding="utf-8")
                return 0, "download complete"

            with patch.object(job, "sh", side_effect=download):
                status = job.kaggle_fetch(str(jobdir), "owner/kernel")
            self.assertEqual(status, 0)
            copied = json.loads((jobdir / "result" / "summary.json").read_text())
            self.assertEqual(copied, {"ok": True})

    def test_cli_propagates_fetch_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            argv = ["job.py", "kaggle", "fetch", temporary]
            with (
                patch.object(sys, "argv", argv),
                patch.object(job, "kaggle_fetch", return_value=9) as fetch,
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                job.main()
        self.assertEqual(raised.exception.code, 9)
        fetch.assert_called_once_with(str(Path(temporary).resolve()))


if __name__ == "__main__":
    unittest.main()
