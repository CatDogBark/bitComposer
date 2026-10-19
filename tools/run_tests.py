#!/usr/bin/env python3
"""
Runs the test suite in parallel: every test in a fresh process of its own,
as many at once as the machine has threads.

The suite run one test at a time takes a few minutes, nearly all of it a
handful of long tests (a song composed, a player started) waiting on one
core. Spread over a 16-thread machine it takes as long as its longest test.
A process per test keeps tests from sharing anything (Qt allows one
application a process; some tests set the environment), at the cost of a
second or so of start-up each.

Usage:
    python3 tools/run_tests.py                 # the whole suite, a worker per thread
    python3 tools/run_tests.py --workers 4     # fewer (a laptop that throttles when hot)
    python3 tools/run_tests.py test_spc        # the test modules whose names start so

Prints what `unittest` prints for a failure or an error, then a line like
`Ran 130 tests in 14.2 s` and OK or FAILED; exits non-zero on a failure.
Runs Qt offscreen unless QT_QPA_PLATFORM is set.
"""
import argparse
import io
import os
import sys
import time
import unittest
from multiprocessing import get_context

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")


def _ids(suite) -> list[str]:
    out = []
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            out += _ids(t)
        else:
            out.append(t.id())
    return out


def discover(prefix: str = "") -> tuple[list[str], list[str]]:
    """Every test's id, and the modules that failed to import (as unittest reports them)."""
    sys.path.insert(0, TESTS)
    suite = unittest.TestLoader().discover(TESTS, pattern=f"{prefix}*.py" if prefix else "test*.py")
    ids = _ids(suite)
    broken = [i for i in ids if i.startswith("unittest.loader._FailedTest")]
    return [i for i in ids if i not in broken], broken


def run_one(test_id: str) -> tuple:
    """One test, in this (fresh) process: (id, outcome, report, seconds)."""
    sys.path.insert(0, TESTS)
    os.chdir(ROOT)
    start = time.time()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(unittest.TestLoader().loadTestsFromName(test_id))
    if result.errors or result.failures:
        outcome = "error" if result.errors else "fail"
        report = "\n".join(text for _, text in result.errors + result.failures)
    elif result.skipped:
        outcome, report = "skip", result.skipped[0][1]
    else:
        outcome, report = "ok", ""
    return test_id, outcome, report, time.time() - start


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the test suite in parallel, a process a test.")
    ap.add_argument("prefix", nargs="?", default="", help="only the test modules whose names start so (e.g. test_spc)")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--slowest", type=int, default=5, help="list the slowest tests (0: none)")
    args = ap.parse_args(argv)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    ids, broken = discover(args.prefix)
    if broken:
        print("Test modules that do not import (run them with unittest to see why): " + ", ".join(broken), file=sys.stderr)
    start = time.time()
    results = []
    # spawn, not fork: each test starts as a fresh interpreter, nothing carried over
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_one, ids):
            results.append(r)
            if r[1] in ("fail", "error"):
                print(f"{r[1].upper()}: {r[0]}\n{r[2]}", flush=True)
    took = time.time() - start
    bad = [r for r in results if r[1] in ("fail", "error")]
    skipped = sum(1 for r in results if r[1] == "skip")
    if args.slowest:
        print("Slowest: " + ", ".join(f"{r[0].split('.', 1)[1]} {r[3]:.1f} s"
                                     for r in sorted(results, key=lambda r: -r[3])[:args.slowest]))
    print(f"Ran {len(results)} tests in {took:.1f} s with {args.workers} workers")
    if bad or broken:
        print(f"FAILED ({len(bad)} failed{f', {len(broken)} modules did not import' if broken else ''})")
        return 1
    print("OK" + (f" (skipped={skipped})" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
