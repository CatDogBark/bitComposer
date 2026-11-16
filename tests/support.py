"""Shared setup for the test modules: the repo on sys.path and the modules several files use. Classic's own tests
have their own (classic_support.py)."""
import itertools
import os
import random
import struct
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bitcomposer import it_format, names, pattern, samples  # noqa: E402,F401
