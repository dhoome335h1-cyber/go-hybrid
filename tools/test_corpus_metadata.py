"""Regression tests for strict corpus registration metadata."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_harness(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HARNESSES = [load_harness("corpus_harness"), load_harness("differential_loop")]


class CorpusMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, text, name="case.hy"):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_and_unknown_verdicts_name_the_file(self):
        for text in ("fn main() {}\n", "// EXPECTED-VERDICT: ACCPET\nfn main() {}\n"):
            path = self.source(text)
            for harness in HARNESSES:
                with self.subTest(harness=harness.__name__, text=text):
                    with self.assertRaises(SystemExit) as error:
                        harness.read_expected(path)
                    self.assertIn(str(path), str(error.exception))
                    self.assertIn("EXPECTED-VERDICT", str(error.exception))

    def test_reject_requires_a_rule_on_the_same_line(self):
        for newline in ("\n", "\r\n"):
            path = self.source(f"// EXPECTED-VERDICT: REJECT{newline}fn main() {{}}{newline}")
            for harness in HARNESSES:
                with self.subTest(harness=harness.__name__, newline=newline):
                    with self.assertRaisesRegex(SystemExit, "REJECT without a rule id"):
                        harness.read_expected(path)

    def test_valid_headers_keep_their_meaning(self):
        cases = [
            ("ACCEPT", ("ACCEPT", None)),
            ("ACCEPT (CONTESTED)", ("ACCEPT", "(CONTESTED)")),
            ("ACCEPT-MANAGED", ("ACCEPT-MANAGED", None)),
            ("REJECT A1c", ("REJECT", "A1c")),
            ("REJECT LOAN-ESCAPE", ("REJECT", "LOAN-ESCAPE")),
        ]
        for header, expected in cases:
            path = self.source(f"// EXPECTED-VERDICT: {header}\nfn main() {{}}\n")
            for harness in HARNESSES:
                with self.subTest(harness=harness.__name__, header=header):
                    self.assertEqual(harness.read_expected(path)[:2], expected)

    def test_runtime_hazards_remain_registered(self):
        path = self.source(
            "// EXPECTED-VERDICT: ACCEPT-MANAGED\n"
            "// RUNTIME-HAZARD: Concurrent Map Writes\nfn main() {}\n"
        )
        self.assertEqual(HARNESSES[1].read_expected(path)[2], ["concurrent map writes"])

    def test_existing_corpus_still_has_a_registered_verdict(self):
        paths = list((ROOT / "tests" / "checker-corpus").glob("*.hy"))
        self.assertTrue(paths)
        for path in paths:
            for harness in HARNESSES:
                with self.subTest(harness=harness.__name__, path=path.name):
                    self.assertIn(
                        harness.read_expected(path)[0],
                        {"ACCEPT", "ACCEPT-MANAGED", "REJECT"},
                    )

    def run_main(self, harness):
        binary = self.root / "hyb"
        binary.touch()
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    sys,
                    "argv",
                    [harness.__name__, "--bin", str(binary), "--corpus", str(self.root)],
                )
            )
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            if harness.__name__ == "corpus_harness":
                stack.enter_context(
                    patch.object(
                        harness, "run_checker", return_value=({"verdict": "accept"}, [])
                    )
                )
            else:
                stack.enter_context(
                    patch.object(harness, "build_and_run", return_value=(True, "exit 0"))
                )
            try:
                code = harness.main()
            except SystemExit as error:
                return error.code, out.getvalue(), str(error)
        return code, out.getvalue(), err.getvalue()

    def test_valid_case_cannot_hide_an_unregistered_neighbour(self):
        self.source("// EXPECTED-VERDICT: ACCEPT\nfn main() {}\n", "01-valid.hy")
        self.source("fn main() {}\n", "02-unregistered.hy")
        for harness in HARNESSES:
            with self.subTest(harness=harness.__name__):
                code, output, error = self.run_main(harness)
                self.assertNotEqual(code, 0)
                self.assertIn("02-unregistered.hy", error)
                self.assertNotIn("FULL AGREEMENT", output)


if __name__ == "__main__":
    unittest.main()
