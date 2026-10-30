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


class LibraryVocabularyTests(unittest.TestCase):
    """The vocabularies fitted on this machine: the library's over everything imported, and an imported pack's own."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("BITCOMPOSER_DATA_DIR")
        os.environ["BITCOMPOSER_DATA_DIR"] = self.tmp.name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BITCOMPOSER_DATA_DIR", None)
        else:
            os.environ["BITCOMPOSER_DATA_DIR"] = self.old
        self.tmp.cleanup()

    def test_the_library_and_a_tabled_pack_are_listed_and_ready_by_their_songs(self):
        import json
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_library import make_pack
        from bitcomposer.packs import library, packfile
        self.assertEqual(vocabularies.names(), vocabularies.shipped())
        tables = dict(vocabularies.raw("ffvi"))
        vocabularies.library_dir().mkdir(parents=True)
        thin = {"source": dict(tables["source"], game="library", label="My library", songs=10), "tables": tables["tables"]}
        vocabularies.library_path().write_text(json.dumps(thin), encoding="utf-8")
        self.assertIn("library", vocabularies.names())
        self.assertEqual((vocabularies.label("library"), vocabularies.songs("library"), vocabularies.ready("library")), ("My library", 10, False))
        thin["source"]["songs"] = 67
        vocabularies.library_path().write_text(json.dumps(thin), encoding="utf-8")
        self.assertTrue(vocabularies.ready("library"))
        folder = library.packs_dir() / "test_quest"
        folder.mkdir(parents=True)
        data = make_pack(folder)
        self.assertNotIn("pack:test_quest", vocabularies.names())            # a format 1 pack has no vocabulary
        data[packfile.KEY] = packfile.TABLED
        data[packfile.TABLES] = tables
        (folder / "pack.json").write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("pack:test_quest", vocabularies.names())
        self.assertEqual(vocabularies.pack_name("pack:test_quest"), "test_quest")
        self.assertTrue(vocabularies.ready("pack:test_quest"))
        kinds = {v["name"]: v["kind"] for v in vocabularies.listing()}
        self.assertEqual((kinds["ffvi"], kinds["library"], kinds["pack:test_quest"]), ("shipped", "library", "pack"))
        self.assertIn("pack:test_quest", build_parser().parse_args(["--vocabulary", "pack:test_quest"]).vocabulary)
        # written from the pack's vocabulary: on its own samples, unless a built-in set is named
        out = written.compose_written("pack:test_quest", None, 3)
        self.assertEqual(out["sounds"], "test_quest")
        self.assertEqual(out["info"]["vocabulary"], data.get("label", "test_quest"))
        out = written.compose_written("pack:test_quest", "mana", 3)
        self.assertEqual(out["sounds"], "mana")
        out = written.compose_written("ffvi", None, 3, pack_file=folder / "pack.json")
        self.assertEqual(out["sounds"], "test_quest")


class ImportCountsAVocabularyTests(unittest.TestCase):
    """What an import does after the pack is written (pack._make): the game's tables into the pack as format 2 and the
    library vocabulary over every song in the readings; here on a generated song's readings, without the emulator."""

    def test_the_tables_go_into_the_pack_and_the_library_is_counted(self):
        import json
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_library import make_pack
        from bitcomposer.composer import compose_song
        from bitcomposer.packs import library, packfile
        from bitcomposer.translate import harness, packtables
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BITCOMPOSER_DATA_DIR"); os.environ["BITCOMPOSER_DATA_DIR"] = tmp
            try:
                ctx = harness.load_generated(compose_song(seed=5, pack="ffvi"), "seed 5", "test", seconds=40.0)
                folder = library.packs_dir() / "test_quest"; folder.mkdir(parents=True)
                make_pack(folder)
                data = packtables.into(ctx.db, "test", folder / "pack.json")
                self.assertIn("rhythm", data["tables"])
                back = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
                self.assertEqual(back[packfile.KEY], packfile.TABLED)
                self.assertEqual(back[packfile.TABLES]["source"]["game"], "test")
                self.assertIn("pack:test_quest", vocabularies.names())
                self.assertEqual(vocabularies.songs("pack:test_quest"), 1)
                self.assertFalse(vocabularies.ready("pack:test_quest"))                # one song is far under MIN_SONGS
                path = vocabularies.refit_library(ctx.db)
                self.assertEqual(path, vocabularies.library_path())
                self.assertIn("library", vocabularies.names())
                self.assertEqual((vocabularies.label("library"), vocabularies.songs("library")), ("My library", 1))
                self.assertEqual(vocabularies.source("library")["games"], ["test"])
                self.assertNotIn("library", [v["name"] for v in vocabularies.listing() if v["ready"]])
            finally:
                if old is None:
                    os.environ.pop("BITCOMPOSER_DATA_DIR", None)
                else:
                    os.environ["BITCOMPOSER_DATA_DIR"] = old
