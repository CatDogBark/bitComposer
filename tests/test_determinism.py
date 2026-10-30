import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAM = """
import hashlib, os, tempfile
from bitcomposer.spc import convert
from bitcomposer.written import compose_written
out = compose_written("ffvi", "ffvi", 7)
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "song.it"); convert.render(out["score"], path)
    print(out["title"], hashlib.md5(open(path, "rb").read()).hexdigest())
"""


VOICE_PROGRAM = """
import random
from bitcomposer.translate import rhythm, tables, writer
iv = tables.Table(("part", "kind", "line", "previous"), "voice_intervals", votes=tables.SHARES).fit(
    [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "line": "scale", "previous": rhythm.START})
     for i in range(6) for o in ("-2", "-5", "0", "2", "5", "7", "-7", "3", "-3", "4")])
mv = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
    [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "place": "with"}) for i in range(6) for o in ("0", "1", "-1", "2", "-2")])
rng = random.Random(7)
scale = {0, 2, 4, 5, 7, 9, 11}
print(" ".join(str(writer.beside_pitch({"voice_intervals": iv, "voice_moves": mv}, "counter", "other", scale, rng, 72.0, rhythm.START, None, 0)[0]) for _ in range(40)))
"""


def run_under(program: str, hash_seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONPATH=ROOT)
    r = subprocess.run([sys.executable, "-c", program], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-2000:])
    return r.stdout.strip()


class DeterminismTests(unittest.TestCase):
    def test_a_voice_beside_the_line_draws_the_same_notes_under_any_hash_seed(self):
        """interval_weights walks a table's vocabulary, a set of strings, in a fixed order: unordered, the dict the draw
        walks (and so the note the random number lands on) changed with PYTHONHASHSEED (round 66, found by the module
        splits' byte check)."""
        self.assertEqual(run_under(VOICE_PROGRAM, "0"), run_under(VOICE_PROGRAM, "1"))

    def test_a_written_song_is_the_same_under_any_hash_seed(self):
        """A seed names one song on every machine: no draw may ride the order of a set or a dict built from one (round 66
        found interval_weights iterating a table's vocabulary, a set of strings, so the counter's notes changed with
        PYTHONHASHSEED). The same seed is written from the shipped vocabulary in two processes with different hash
        seeds and must give the same title and the same bytes."""
        self.assertEqual(run_under(PROGRAM, "0"), run_under(PROGRAM, "1"), "the same seed wrote different songs under two hash seeds")
