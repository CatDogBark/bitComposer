import os
import random
import tempfile
import unittest

from bitcomposer.translate import harmony, rhythm, tables, vocab, whole
from bitcomposer.translate import roles as R


class ChordNamesTests(unittest.TestCase):
    def test_a_numeral_goes_back_to_its_chord(self):
        for mode in ("major", "minor"):
            for tonic in (0, 3, 7, 10):
                for root in range(12):
                    for shape in harmony.SHAPES:
                        name = vocab.numeral(root, tonic, mode, shape)
                        self.assertEqual(whole.chord_of(name, tonic, mode), (root, shape), (name, tonic, mode))
        self.assertIsNone(whole.chord_of(rhythm.NO_CHORD, 0, "major"))
        self.assertIsNone(whole.chord_of("start", 0, "major"))


class PlanTests(unittest.TestCase):
    def test_a_plan_with_no_tables_is_consistent(self):
        p = whole.plan({}, seed=3, game="test")
        self.assertEqual(p.parts[0][0], 0)
        for i, (bar, n, of, label) in enumerate(p.parts):
            if i:
                self.assertEqual(bar, p.parts[i - 1][0] + p.parts[i - 1][1])
            if of is not None:
                self.assertLess(of, i)
                self.assertEqual(n, p.parts[of][1])
                self.assertEqual(label, p.parts[of][3])
        self.assertEqual(len(p.chords), p.bars)
        self.assertTrue(all(c is not None for c in p.chords))
        self.assertEqual(sorted(p.plays), sorted(p.band))
        self.assertTrue(all(len(v) == p.bars for v in p.plays.values()))
        self.assertLessEqual(sum(p.voices.values()), whole.VOICES)
        self.assertTrue(any("assumed" in line for line in p.log))

    def test_the_form_follows_the_tables(self):
        units = [tables.Unit("s", "g", "3", {"part": "form"}), tables.Unit("s", "g", "long", {"part": "form"})]
        sizes = tables.Table(("part",), "sizes", votes=tables.SHARES).fit(units[:1])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit(units[1:])
        form = tables.Table(("part", "meter", "index"), "form", votes=tables.SHARES).fit([
            tables.Unit("s", "g", "new", {"part": "form", "meter": 4, "index": 1}),
            tables.Unit("s", "g", "new", {"part": "form", "meter": 4, "index": 2}),
            tables.Unit("s", "g", "back", {"part": "form", "meter": 4, "index": 3})])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit([
            tables.Unit("s", "g", "8", {"part": "form", "meter": 4, "habit": "long"})])
        log = []
        parts = whole.plan_form({"sizes": sizes, "length_habits": habits, "form": form, "lengths": lengths}, random.Random(1), log)
        self.assertEqual([p[3] for p in parts], ["A", "B", "A"])
        self.assertEqual([p[1] for p in parts], [8, 8, 8])
        self.assertEqual(parts[2][2], 0)
        self.assertEqual(whole.loop_bar_of(parts), 0)                   # A comes back: no intro
        self.assertEqual(whole.loop_bar_of([(0, 4, None, "A"), (4, 8, None, "B"), (12, 8, 1, "B")]), 4)   # A never returns: the loop after it

    def test_the_chords_and_textures_of_a_repeated_part_are_kept(self):
        units = [tables.Unit("s", "g", o, {"part": R.HARMONY, "mode": "major", "previous": p})
                 for o, p in (("I", rhythm.START), ("IV", "I"), ("V", "IV"), ("I", "V"))]
        chords = tables.Cache.fit(units, ("part", "mode", "previous"), name="chords", votes=tables.SHARES)
        parts = [(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 0, "A")]
        names, chords_ = whole.plan_chords({"chords": chords}, parts, 0, 0, "major", random.Random(2), [])
        self.assertEqual(names[:4], names[8:])
        self.assertEqual(chords_[0], (0, ""))
        tunits = [tables.Unit("s", "g", o, {"part": rhythm.ARRANGEMENT, "meter": 4, "previous": p})
                  for o, p in (("bass", rhythm.START), ("bass drums melody", "bass"), ("bass drums melody", "bass drums melody"))]
        texture = tables.Cache.fit(tunits, ("part", "meter", "previous"), name="texture", votes=tables.SHARES)
        textures, plays = whole.plan_texture({"texture": texture}, parts, ["bass", "drums", "melody"], random.Random(2), [])
        self.assertEqual(textures[:4], textures[8:])
        self.assertTrue(all(set(t.split()) <= {"bass", "drums", "melody"} for t in textures))
        self.assertEqual(sorted(plays), ["bass", "drums", "melody"])


class WholeSongTests(unittest.TestCase):
    def test_a_whole_song_from_a_generated_songs_tables_is_written_rendered_and_read_back(self):
        from bitcomposer.composer import compose_song
        from bitcomposer.packs import PACKS
        from bitcomposer.spc import convert
        from bitcomposer.translate import harness, packtables
        song = compose_song(seed=5, pack="ffvi")
        ctx = harness.load_generated(song, "seed 5", "test", seconds=40.0)
        self.assertIsNotNone(ctx)
        models = packtables.read(packtables.build(ctx.db, "test"))
        for name in ("rhythm", "bass", "chords", "texture", "balance", "keys", "tempos", "registers", "form", "lengths", "sizes"):
            self.assertIn(name, models)
        out = whole.compose(models, PACKS["ffvi"], set(), "ffvi", seed=1, game="test", max_bars=32)
        p, written = out["plan"], out["written"]
        self.assertTrue(p.band)
        self.assertLessEqual(p.bars, 32)
        for role in p.band:
            if role in (R.COUNTER,):
                continue
            self.assertIn(role, written, role)
            if any(p.plays[role]):
                self.assertTrue(written[role].notes, role)
        score = out["score"]
        self.assertGreater(len(score.notes), 0)
        self.assertEqual(score.voices, sum(p.voices[r] for r in out["first"]))
        self.assertTrue(all(0 <= n.voice < score.voices for n in score.notes))
        self.assertTrue(all(n.end is not None and n.end >= n.start for n in score.notes))
        self.assertGreater(score.seconds, p.bars * 4 * 60.0 / p.bpm)          # the loop once more
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "whole.it")
            convert.render(score, path)
            self.assertGreater(os.path.getsize(path), 1000)
        back = out["read"]
        self.assertIsNotNone(back)
        self.assertEqual(len(back.bars), p.bars)
        self.assertEqual(sorted(back.notes), sorted(r for r in p.band if r in written and written[r].notes))
        m = out["measures"]
        self.assertEqual(m["bars"], p.bars)
        if R.MELODY in back.notes:
            self.assertIn("tune", m)
            self.assertLessEqual(m["tune"]["chord_tones"], 1.0)


if __name__ == "__main__":
    unittest.main()
