"""Shared setup for Classic's own tests (test_classic_*.py): the repo on sys.path, the analyzer loaded from tools/, and
the two helpers they use. Classic lives behind its wall in bitcomposer/classic/; these tests are Classic's and reach
its modules directly, which code outside the wall does not (tests/test_classic_wall.py)."""
import importlib.util
import itertools  # noqa: F401
import os
import random  # noqa: F401
import struct  # noqa: F401
import sys
import tempfile  # noqa: F401
import unittest  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bitcomposer.classic import composer, it_format, melody, names, pattern, samples, theory  # noqa: E402,F401
from bitcomposer.classic.composer import compose_and_save, compose_song  # noqa: E402,F401

_spec = importlib.util.spec_from_file_location(
    "analyze", os.path.join(ROOT, "tools", "analyze.py"))
analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze)


def _gen(tmp, seed, **kw):
    path = os.path.join(tmp, f"s{seed}.it")
    info = compose_and_save(path, seed=seed, **kw)
    return path, info


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()
