import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, "-m", "cachecraft", *args], cwd=str(ROOT),
                          capture_output=True, text=True)


class CliContractTests(unittest.TestCase):
    def test_words_must_be_positive(self):
        for bad in ("0", "-3", "x"):
            r = run("signals", "hello world", "--words", bad)
            self.assertEqual(r.returncode, 2, (bad, r.stderr))
            self.assertIn("error:", r.stderr)

    def test_inspect_missing_trace_is_a_cli_error(self):
        r = run("inspect", "nope.jsonl")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("error:", r.stderr)

    def test_bench_writes_into_a_new_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp, "trace.jsonl")
            trace.write_text('{"route":"chat","prompt":"hello there","cost_ms":100}\n', encoding="utf-8")
            out = Path(tmp, "reports", "bench.txt")
            r = run("bench", str(trace), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
