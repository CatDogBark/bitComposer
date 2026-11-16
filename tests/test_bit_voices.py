"""bitComposer's own voices (packs/bit_voices.py, docs/VOICES.md).

- A recipe describes a sound and holds none: levels in whole decibels, times in whole milliseconds, a few rates in
  hertz, no phase and no sample value.
- Every voice is the sound it was (bit_voices_lock.json: the sha256 of each voice's samples). A recipe changed on
  purpose rewrites the lock in the same change: `python tests/test_bit_voices.py --write`. Never to make a failing
  change pass.
- Every sample of the game the voices stand for has one voice, and a song on the voices is, note for note, the song a
  pack file of the same sounds writes.
- With the voices off nothing of them is loaded, and the sound sets taking turns in one process each write the file
  they write alone."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest import mock

import support  # noqa: F401  the repo on sys.path
from bitcomposer.packs import bit_voices, bit_voices_data as data  # noqa: E402
from bitcomposer.samples import recipe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOCK = os.path.join(HERE, "bit_voices_lock.json")
FIELDS = {"tone": {"kind", "rate", "period", "periods", "frames", "rms", "steady", "onset", "attack", "env", "chorus", "breath", "strike", "off",
                   "struck_as_kit"},
          "hit": {"kind", "rate", "frames", "peak", "env", "partials", "noise", "note", "moments", "rms", "delay"}}


def digests() -> dict:
    return {name: hashlib.sha256(recipe.voice(v["recipe"], v["seed"])[0]).hexdigest() for name, v in data.VOICES.items()}


def run(program: str, hash_seed: str = "0") -> list:
    r = subprocess.run([sys.executable, "-c", program], cwd=ROOT, capture_output=True, text=True, timeout=600,
                       env=dict(os.environ, PYTHONPATH=ROOT, PYTHONHASHSEED=hash_seed, PYTHONDONTWRITEBYTECODE="1"))
    if r.returncode != 0:
        raise AssertionError(r.stderr[-3000:])
    return r.stdout.split()


TURNS = """
import hashlib, os, sys, tempfile
from unittest import mock
from bitcomposer import written
from bitcomposer.spc import convert
for step in STEPS:
    kind, seed = step.split(":")
    with mock.patch.object(written, "OWN_VOICES", kind == "own"):
        out = written.compose_written(seed=int(seed), pack="mana" if kind == "mana" else None)
    with tempfile.TemporaryDirectory() as d:
        convert.render(out["score"], os.path.join(d, "s.it"))
        print(step + "=" + hashlib.sha256(open(os.path.join(d, "s.it"), "rb").read()).hexdigest())
"""


class BitVoices(unittest.TestCase):
    def test_a_recipe_describes_a_sound_and_holds_none(self):
        for name, v in data.VOICES.items():
            r = v["recipe"]
            self.assertIn(r["kind"], FIELDS, name)
            self.assertLessEqual(set(r), FIELDS[r["kind"]], name)
            levels = [*r.get("steady", ()), *r.get("onset", ()), *(db for row in r.get("noise", ()) for db in row),
                      *(db for p in r.get("partials", ()) for db in p["db"]), *(pt[1] for pt in r.get("env", ()))]
            self.assertTrue(all(isinstance(x, int) and -80 <= x <= 20 for x in levels), name)     # levels in whole decibels
            self.assertTrue(all(len(pt) == 2 and isinstance(pt[0], int) for pt in r.get("env", ())), name)   # times in whole ms
            self.assertLessEqual(len(r.get("steady", ())), 128, name)                                   # a harmonic a level, no more
            self.assertLessEqual(len(r.get("onset", ())), 128, name)
            self.assertLessEqual(len(r.get("partials", ())), 24, name)
            for p in r.get("partials", ()):
                self.assertEqual(set(p), {"hz", "db"}, name)
                self.assertEqual(len(p["hz"]), 2, name)                                            # where it starts and ends
            self.assertTrue(all(len(row) <= len(recipe.BAND_EDGES) for row in r.get("noise", ())), name)
            at = r.get("moments")
            if at:                                                                          # moments in whole ms, rising, a level a moment
                self.assertTrue(all(isinstance(m, int) for m in at) and at == sorted(set(at)) and at[0] == 0, name)
                self.assertTrue(len(at) <= 12, name)
                self.assertEqual(len(r["noise"]), len(at) - 1, name)
                self.assertTrue(all(len(p["db"]) == len(at) - 1 for p in r.get("partials", ())), name)
            else:
                self.assertTrue(all(len(p["db"]) == 4 for p in r.get("partials", ())), name)   # four quarters
            self.assertIsInstance(r.get("delay", 0), int, name)
            for k in ("breath", "strike", "chorus"):
                self.assertTrue(all(isinstance(x, (int, float)) for x in (r.get(k) or {}).values()), name)
            self.assertLessEqual(len(json.dumps(r)), 4096, name)
            self.assertIsInstance(v["seed"], int, name)

    def test_every_sample_of_the_game_has_one_voice(self):
        g = data.GAMES["ffvi"]
        by = bit_voices.stands("ffvi")
        self.assertEqual(set(by), set(g["samples"]))
        self.assertTrue(all(v["stands_for"].get("ffvi") for v in data.VOICES.values()))
        used = {sid for pool in g["pools"].values() for sid in pool} | set(g["kit"].values())
        self.assertLessEqual(used, set(g["samples"]))
        self.assertTrue(all(n.startswith("bit_") and n == n.lower() for n in data.VOICES))
        self.assertEqual(sorted(bit_voices.names()), sorted(data.VOICES))

    def test_every_voice_is_the_sound_it_was(self):
        held = json.load(open(LOCK, encoding="utf-8"))["voices"]
        now = digests()
        self.assertEqual(sorted(now), sorted(held))
        self.assertEqual(sorted(n for n in held if now[n] != held[n]), [], "these voices are not the sounds they were")
        names = sorted(data.VOICES)[:4]
        program = ("import hashlib\nfrom bitcomposer.packs import bit_voices_data as d\nfrom bitcomposer.samples import recipe\n"
                   f"for n in {names!r}:\n    v = d.VOICES[n]\n    print(n + '=' + hashlib.sha256(recipe.voice(v['recipe'], v['seed'])[0]).hexdigest())\n")
        self.assertEqual(dict(x.split("=") for x in run(program, "4242")), {n: held[n] for n in names})   # under another hash seed

    def test_a_song_on_the_voices_is_the_song_a_pack_file_of_them_writes(self):
        from bitcomposer import written
        from bitcomposer.packs import packfile
        made = bit_voices.rendered()
        shaped = dict(bit_voices.pack_data(sounds=made), name="bitvoicestest")
        with tempfile.TemporaryDirectory() as d:
            for fname, (pcm, frames, rate) in bit_voices.audio(sounds=made).items():
                with wave.open(os.path.join(d, fname), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
            with open(os.path.join(d, "pack.json"), "w") as fh:
                json.dump(shaped, fh)
            self.addCleanup(packfile.unload, "bitvoicestest")
            for seed in (3, 11):
                a = written.compose_written(seed=seed, pack_file=os.path.join(d, "pack.json"))
                with mock.patch.object(written, "OWN_VOICES", True):
                    b = written.compose_written(seed=seed)
                self.assertEqual(b["sounds"], "bit")
                rows = lambda out: sorted((n.voice, round(n.start, 6), round(n.end or 0, 6), n.pitch, n.volume, n.adsr, n.gain,   # noqa: E731
                                           tuple(n.bends or ()), out["score"].key_of[n.brr]) for n in out["score"].notes)
                self.assertEqual(rows(a), rows(b), seed)
                self.assertLessEqual(set(b["score"].key_of.values()), set(data.GAMES["ffvi"]["samples"]))   # every voice on a sample id it stands for

    def test_with_the_voices_off_a_song_loads_none_of_them(self):
        program = ("import re, sys\nfrom bitcomposer import written, samples\nwritten.compose_written(seed=3)\n"
                   "print(any(re.match(r'^bit_s[0-9a-f]{10}', k) for k in samples.INSTRUMENT_PRESETS), 'bitcomposer.packs.bit_voices' in sys.modules)\n")
        self.assertEqual(run(program), ["False", "False"])

    def test_the_sets_take_turns_in_one_process(self):
        steps = ["own:3", "mana:4", "first:5", "own:6", "first:5", "own:3"]
        together = dict(x.split("=", 1) for x in run(TURNS.replace("STEPS", repr(steps))) if "=" in x)
        for step in sorted(set(steps)):
            alone = dict(x.split("=", 1) for x in run(TURNS.replace("STEPS", repr([step]))) if "=" in x)
            self.assertEqual(together[step], alone[step], step)
        self.assertEqual(len(together), len(set(steps)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        with open(LOCK, "w", encoding="utf-8") as fh:
            json.dump({"what": "bitComposer's own voices as they are: each voice's name and the sha256 of its 16-bit samples as "
                               "samples/recipe.py makes them from its recipe and seed", "voices": digests()}, fh, indent=1)
            fh.write("\n")
        print("wrote", LOCK)
    else:
        unittest.main()
