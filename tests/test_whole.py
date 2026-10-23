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
        songs = ("s", "t")                                   # two songs: a plan's draw passes over a level one song alone stands behind
        units = [tables.Unit(sid, "g", "3", {"part": "form"}) for sid in songs] + [tables.Unit(sid, "g", "long", {"part": "form"}) for sid in songs]
        sizes = tables.Table(("part",), "sizes", votes=tables.SHARES).fit(units[:2])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit(units[2:])
        form = tables.Table(("part", "meter", "index"), "form", votes=tables.SHARES).fit([
            tables.Unit(sid, "g", kind, {"part": "form", "meter": 4, "index": i})
            for sid in songs for i, kind in ((1, "new"), (2, "new"), (3, "back"))])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit([
            tables.Unit(sid, "g", "8", {"part": "form", "meter": 4, "habit": "long"}) for sid in songs])
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
        tunits = [tables.Unit("s", "g", o, {"part": rhythm.ARRANGEMENT, "form": f, "index": i, "previous": p})
                  for o, f, i, p in (("no drums melody", "first", 1, rhythm.START), ("all", "middle", 2, "no drums melody"), ("no harmony", "last", 3, "all"))]
        texture = tables.Table(("part", "form", "previous"), "part textures", votes=tables.SHARES).fit(tunits)
        textures, plays = whole.plan_texture({"part_textures": texture}, parts, ["bass", "drums", "melody"], random.Random(2), [])
        self.assertEqual(textures[:4], textures[8:])
        self.assertEqual(len(set(textures[:4])), 1)                   # a texture a part
        self.assertEqual(textures[0], "bass")                         # the first part: no drums, no melody
        self.assertEqual(textures[4], "bass drums melody")
        self.assertEqual(sorted(plays), ["bass", "drums", "melody"])
        t = tables.Table(("part",), "x", votes=tables.SHARES, discount=0.75).fit([tables.Unit(str(i), "g", f"o{i}", {"part": "p"}) for i in range(6)])
        self.assertTrue(all(t.draw(("p",), random.Random(i), floored=False).startswith("o") for i in range(40)))


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


class NewTablesTests(unittest.TestCase):
    """The tables the whole-song plan added to the kept set."""

    def _song(self, sid="a"):
        from bitcomposer.translate.vocab import Span
        bars = [(4.0 * i, 4.0 * i + 4) for i in range(8)]
        chords = [Span(0.0, 16.0, 0, "", 1.0), Span(16.0, 32.0, 7, "", 1.0)]          # C, then G
        s = rhythm.Song("t", 4, 4, bars, chords, bpm=120.0, sid=sid, game="G", numbers=list(range(8)),
                        parts=[(0, 4, None, "A"), (4, 4, None, "B")], tonic=0, mode="major")
        s.notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(8) for x in (0.0, 2.0)]
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "m") for i in range(4, 8) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0))]
        s.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "kick") for i in range(8) for x in (0.0, 2.0)] + \
                           [(4.0 * i + x, 0.25, float("nan"), "crash") for i in range(8) for x in (0.0,) if i % 4 == 0]
        s.pieces = {"kick": "kick", "crash": "cymbal"}
        return s

    def test_part_textures(self):
        units = rhythm.part_texture_units([self._song()])
        self.assertEqual([u.outcome for u in units], ["no melody", "all"])
        self.assertEqual([u.values["form"] for u in units], ["first", "last"])
        self.assertEqual(units[1].values["previous"], "no melody")

    def test_drum_group_habits_and_rests(self):
        units = rhythm.drum_group_habit_units([self._song()])
        parts = {u.values["part"]: u for u in units}
        self.assertIn("drums-KSt", parts)
        self.assertIn("drums-c", parts)
        self.assertTrue(all(u.values["habit"] == parts["drums-KSt"].values["habit"] for u in units))   # the kit's habit beside each group's own
        self.assertTrue(parts["drums-c"].outcome.startswith("sparse"))
        from bitcomposer.translate import writer
        self.assertFalse(writer.FreeManner({"0:K", "-"}).fits("-"))
        self.assertTrue(writer.FreeManner({"0:K", "-"}, rests=True).fits("-"))

    def test_the_whole_kit_writes_from_its_own_table(self):
        """A group of every letter is the kit: its figures come from the kit table's bars (part "drums"), not the floor's runs."""
        from bitcomposer.translate import packtables, writer
        s = self._song()
        s.notes["drums"] = [(4.0 * i + x, 0.25, float("nan"), "kick") for i in range(8) for x in (0.0, 2.0)] + \
                           [(4.0 * i + x, 0.25, float("nan"), "snare") for i in range(8) for x in (1.0, 3.0)]
        s.pieces = {"kick": "kick", "snare": "snare"}
        entry = packtables.fit("drums", rhythm.drum_units([s]))
        model = packtables.read({"tables": {"drums": entry}})["drums"]
        hits, figures = writer.drums(s, {tuple(rhythm.LETTERS.values()): model}, random.Random(1), habit="medium repeating", free=True, plays=[True] * 8)
        self.assertTrue(all(f in model.table.vocabulary for f in figures), figures)
        self.assertTrue(hits)

    def test_rolls_and_the_balance_with_its_layout(self):
        self.assertTrue(rhythm.is_roll(" ".join(f"{i}/12:R" for i in range(0, 48)), 4))
        self.assertFalse(rhythm.is_roll("0:R 1/2:5 1:R 3/2:5 2:R 5/2:5 3:R 7/2:5", 4))
        self.assertTrue(rhythm.is_roll(" ".join(f"{i}/12:h" for i in range(0, 20)) + " 0:K 2:S", 4))   # a hat roll
        self.assertFalse(rhythm.is_roll(" ".join(f"{i}/4:h" for i in range(0, 16)) + " 0:K 2:S", 4))   # sixteenth hats are a bar
        units = rhythm.balance_units([self._song()])
        self.assertEqual(len(units), 1)
        tokens = units[0].outcome.split()
        self.assertEqual(tokens[1], "drums")
        self.assertTrue(tokens[0].startswith("bass=") and tokens[0].count(":") == 3, tokens)   # weight:register:sounded share:voices
        self.assertIn("36-36", tokens[0])                                                       # the bass on one note
        ranges = rhythm.sample_range_units([self._song()])
        self.assertEqual({u.values["part"] for u in ranges}, {"sk", "sm"})

    def test_layers_and_the_voices_a_part(self):
        s = self._song()
        s.voice_notes = {0: ("bass", s.notes["bass"]), 1: ("melody", s.notes["melody"]),
                         2: ("melody", [(t + d, 0.2, m - 12.0, "m") for t, _, m, _ in s.notes["melody"] if t % 2 == 0 for d in (0.5, 0.75)])}   # a second voice an octave under, its own rhythm, as dense
        units = rhythm.layer_units([s])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].values["part"], "melody")
        self.assertEqual(units[0].outcome, "apart -12 like")
        self.assertIn("melody=main:68-72:0.9:2", rhythm.balance_units([s])[0].outcome)   # the tune's ambitus to the grain, two voices
        self.assertEqual(whole.allot(["bass", "drums", "melody", "counter"], {"bass": 1, "melody": 1, "counter": 2}), {"drums": 2, "bass": 1, "melody": 1, "counter": 2})
        self.assertEqual(sum(whole.allot(["bass", "accompaniment", "counter", "harmony", "melody", "drums"], {"accompaniment": 3, "counter": 3, "harmony": 3}).values()), 8)
        self.assertEqual(whole.layer_of({"layer": "apart -8 sparser"}), ("apart", -8, "sparser"))
        self.assertEqual(whole.layer_of({"layer": "doubling +4"}), ("doubling", 4))
        major = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual([m for _, _, m, _ in whole.diatonic([(0.0, 1.0, 60.0, 0), (1.0, 2.0, 62.0, 0)], 4, major, 1)], [64.0, 65.0])   # a third up: E, then F

    def test_phrase_letters_and_the_theme_body(self):
        s = self._song()
        # the tune over the song's eight bars: two parts of four; bars 0 and 4 open alike (the theme head), bar 4's phrase
        # keeps the theme's second bar too, bars 2-3 and 6-7 differ
        s.parts = [(0, 4, None, "A"), (4, 4, None, "B")]
        tune = {0: (67, 69, 71, 72), 1: (72, 71, 69, 67), 2: (60, 62, 64, 65), 3: (65, 64, 62, 60),
                4: (67, 69, 71, 72), 5: (72, 71, 69, 67), 6: (74, 76, 77, 79), 7: (79, 77, 76, 74)}
        s.notes["melody"] = [(4.0 * bar + x, 0.9, float(m), "m") for bar, ms in tune.items() for x, m in zip((0.0, 1.0, 2.0, 3.0), ms)]
        s.parts = [(0, 4, None, "A"), (4, 4, None, "B")]
        windows = rhythm.phrase_windows(s)
        self.assertEqual([w for _, w in windows], [[0, 1, 2, 3], [4, 5, 6, 7]])
        heads = rhythm.phrase_heads(s)
        self.assertEqual(heads[0][2], heads[1][2])
        units = rhythm.phrase_letter_units([s])
        self.assertEqual([(u.outcome, u.values["phrases"], u.values["form"]) for u in units], [("T", "1", "first"), ("T", "1", "last")])
        body = rhythm.theme_body_units([s])
        self.assertEqual([u.outcome for u in body], ["1"])                  # bar 5 repeats the theme's bar 1, bar 6 does not
        s.parts = [(0, 8, None, "A")]
        self.assertEqual([u.outcome for u in rhythm.theme_body_units([s])], ["1"])   # within one part: bar 5 repeats the theme's bar 1, bar 6 does not
        self.assertEqual(rhythm.phrase_letter_units([s])[0].outcome, "T T")

    def test_a_plan_draw_stays_at_the_part(self):
        """A register drawn for a counter never comes from the bass's: the draw stops at the part's level."""
        units = [tables.Unit(f"s{i}", "g", "28-40", {"part": "bass"}) for i in range(10)] + [tables.Unit(f"s{i}", "g", f"{60 + 4 * (i % 3)}-80", {"part": "counter"}) for i in range(3)]
        t = tables.Table(("part",), "registers", votes=tables.SHARES).fit(units)
        draws = {t.draw(("counter",), random.Random(i), floored=False, floor_k=1) for i in range(200)}
        self.assertNotIn("28-40", draws)
        self.assertIn("28-40", {t.draw(("counter",), random.Random(i), floored=False) for i in range(200)})   # without the floor it could

    def test_new_cell_rhythms(self):
        s = self._song()
        s.notes["melody"] = [(4.0 * i + x, 0.9, m, "m") for i in range(8) for x, m in ((0.0, 67.0), (1.0, 69.0), (2.0, 71.0), (3.0, 72.0 + (i % 3)))]
        units = rhythm.new_cell_rhythm_units([s])
        self.assertEqual(units[0].outcome, "new")                      # the first bar's cell is new, its rhythm too
        self.assertTrue(all(u.outcome == "previous" for u in units[1:3]))   # the same rhythm with a changed last interval: the bar before's rhythm
        self.assertEqual(len(units), 3)                                # three distinct cells in eight bars (i % 3)

    def test_chord_tone_habit_and_contour_sizes(self):
        units = rhythm.chord_tone_habit_units([self._song()])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].outcome, "0.5")            # G and B on the G chord, A and C off it
        from bitcomposer.translate import phrases, writer
        line = [(0.0, 1.0, 60.0), (4.0, 1.0, 64.0), (8.0, 1.0, 67.0), (12.0, 1.0, 72.0)]
        self.assertEqual(phrases.contour(line, 0.0, 16.0), "rising")
        x, y, z = phrases.thirds(line, 0.0, 16.0)
        self.assertLess(x, z)
        self.assertEqual(writer.contour_targets("rising", 8.0), (0, 4.0, 8.0))
        self.assertEqual(writer.contour_targets("valley", 3.0), (0, -3.0, 0))
        self.assertEqual(writer.contour_targets("rising"), (0, 2.0, 4.0))   # without a size, as before
