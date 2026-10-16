"""Shared setup for the test modules: the repo on sys.path, the analyzer loaded
from tools/, and the two helpers every file uses."""
import importlib.util
import itertools
import os
import random
import struct
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bitcomposer import composer, it_format, melody, names, pattern, samples, theory  # noqa: E402
from bitcomposer.composer import compose_and_save, compose_song  # noqa: E402

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
