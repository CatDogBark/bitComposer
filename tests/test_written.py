import hashlib
import os
import tempfile
import unittest

from bitcomposer import vocabularies, written
from bitcomposer.cli import build_parser, compose_from_args
from bitcomposer.spc import convert


class ShippedVocabularyTests(unittest.TestCase):
    def test_the_player_ships_final_fantasy_vi(self):
        """The shipped vocabulary is a format 2 pack's tables, fitted on the game's readings: statistics, no samples."""
        self.assertIn("ffvi", vocabularies.names())
        self.assertEqual(vocabularies.label("ffvi"), "Final Fantasy VI")
        src = vocabularies.source("ffvi")
        self.assertEqual((src["game"], src["songs"]), ("Final Fantasy VI", 67))
        models = vocabularies.load("ffvi")
        for name in ("rhythm", "balance", "habits", "moves", "voice_intervals", "tune_grain"):
            self.assertIn(name, models)
        self.assertGreaterEqual(len(models), 90)
        with self.assertRaises(KeyError):
            vocabularies.path("no-such-game")


class WrittenSongTests(unittest.TestCase):
    def test_a_seed_names_one_song_on_one_sound_set(self):
        """compose_written draws the sound set and the title from the seed and writes the same bytes twice."""
        digests, titles = [], []
        for _ in range(2):
            out = written.compose_written("ffvi", "mana", 7)
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "s.it")
                convert.render(out["score"], path)
                digests.append(hashlib.md5(open(path, "rb").read()).hexdigest())
            titles.append(out["title"])
        self.assertEqual(digests[0], digests[1])
        self.assertEqual(titles[0], titles[1])
        self.assertLessEqual(len(titles[0]), 25)
        self.assertEqual(out["sounds"], "mana")
        self.assertEqual(out["info"]["vocabulary"], "Final Fantasy VI")
        self.assertIn("melody", out["info"]["band"])
        self.assertTrue(any(l.startswith("Written by bitComposer from Final Fantasy VI's vocabulary on the mana sounds") for l in out["score"].message))
        self.assertTrue(any(l.startswith("layout: ") and "melody" in l for l in out["score"].message))

    def test_random_sounds_are_one_of_the_snes_sets_and_the_seed_picks_them(self):
        import random
        for pack in (None, "random", "none"):
            self.assertIn(written.sound_set(pack, random.Random(1)), written.SOUND_SETS)
        self.assertEqual(written.sound_set("evermore", random.Random(1)), "evermore")
        self.assertEqual(written.sound_set(None, random.Random(3)), written.sound_set(None, random.Random(3)))

    def test_the_command_line_writes_from_a_vocabulary(self):
        """--vocabulary ffvi takes the writer's path: an .it named by the song's title, the info the writer's."""
        with tempfile.TemporaryDirectory() as d:
            args = build_parser().parse_args(["--vocabulary", "ffvi", "--pack", "ffvi", "-s", "11", "-d", d, "--carry-theme", "--band-returns"])
            path, info = compose_from_args(args)
            self.assertTrue(os.path.exists(path) and path.endswith(".it"))
            self.assertEqual(os.path.basename(path)[:-3], info["title"])
            self.assertEqual((info["sounds"], info["seed"], info["carry_theme"], info["band_returns"]), ("ffvi", 11, True, True))
            raw = open(path, "rb").read()
            self.assertEqual(raw[:4], b"IMPM")
            self.assertIn(info["title"].encode("latin-1"), raw[:30])
