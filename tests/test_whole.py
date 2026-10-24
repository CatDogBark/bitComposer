import os
import random
import tempfile
import unittest

from bitcomposer.translate import harmony, pack, rhythm, tables, vocab, whole, writer
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
        self.assertEqual((units[0].values["part"], units[0].values["rank"]), ("melody", "2"))
        self.assertEqual(units[0].outcome, "apart -12 like")
        s.voice_notes[3] = ("melody", [(t, 0.2, m + 12.0, "m") for t, _, m, _ in s.notes["melody"]])   # a third voice doubling the line an octave up
        units = rhythm.layer_units([s])
        self.assertEqual([(u.values["rank"], u.outcome) for u in units], [("2", "apart -12 like"), ("3", "doubling +12")])
        del s.voice_notes[3]
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

    def test_what_comes_back_with_the_theme(self):
        s = self._song()
        s.parts = [(0, 8, None, "A")]
        tune = {0: (67, 69, 71, 72), 1: (72, 71, 69, 67), 2: (60, 62, 64, 65), 3: (65, 64, 62, 60),
                4: (67, 69, 71, 72), 5: (72, 71, 69, 67), 6: (74, 76, 77, 79), 7: (79, 77, 76, 74)}
        s.notes["melody"] = [(4.0 * bar + x, 0.9, float(m), "m") for bar, ms in tune.items() for x, m in zip((0.0, 1.0, 2.0, 3.0), ms)]
        from bitcomposer.translate.vocab import Span
        s.chords = [Span(0.0, 32.0, 0, "", 1.0)]               # one chord throughout: the bass's two-note bar and the chord come back with the theme
        units = rhythm.return_band_units([s])
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].outcome, "chords bass")
        s.chords = [Span(0.0, 16.0, 0, "", 1.0), Span(16.0, 32.0, 7, "", 1.0)]   # the chord changes under the return: the bass's marks change with it
        self.assertEqual(rhythm.return_band_units([s])[0].outcome, "none")
        from bitcomposer.translate import writer
        s2 = self._song()
        s2.copies = {"bass": [(4, 2, 0)]}                       # the plan: the bass comes back with the theme at bar 4, two bars
        units = [tables.Unit(f"s{i}", "g", f, {"part": "bass", "meter": 4, "habit": "medium walking no-octaves", "previous": rhythm.START})
                 for i, f in enumerate(("0:R 2:5", "0:R 1:+ 2:5 3:+", "0:R 3/2:R 2:5", "0:R 1:R 2:R 3:R"))]
        cache = tables.Cache.fit(units, ("part", "meter", "habit", "previous"), name="bass", votes=tables.SHARES)
        bars = [(a, b, []) for a, b in s2.bars]
        figs = writer._free_figures(s2, "bass", cache, writer.FreeManner(cache.table.vocabulary, division=4), ["0"] * 8, bars,
                                    "medium walking no-octaves", random.Random(3), (), {}, envelope_of=writer.free_envelope("medium"))
        self.assertEqual(figs[4:6], figs[0:2])                 # the theme's bars again under the return
        self.assertTrue(all(f in cache.table.vocabulary for f in figs))

    def test_a_themed_plan_returns_to_its_theme(self):
        """With phrase letters and the tune playing throughout, a themed plan has a later phrase open with the theme."""
        letters = tables.Table(("part", "phrases", "form"), "phrase letters", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "melody", "phrases": "2", "form": f}) for i, (o, f) in enumerate(
                (("T n", "first"), ("n n", "last"), ("n n", "last"), ("n T", "last"), ("n n", "middle")))])
        returns = tables.Table(("part",), "return band", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "return"}) for i, o in enumerate(("none", "none", "chords bass accompaniment", "accompaniment"))])
        sizes = tables.Table(("part",), "sizes", votes=tables.SHARES).fit([tables.Unit("s", "g", "2", {"part": "form"}), tables.Unit("t", "g", "2", {"part": "form"})])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit(
            [tables.Unit(sid, "g", "8", {"part": "form", "meter": 4, "habit": "short"}) for sid in ("s", "t")])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit([tables.Unit(sid, "g", "short", {"part": "form"}) for sid in ("s", "t")])
        models = {"phrase_letters": letters, "return_band": returns, "sizes": sizes, "lengths": lengths, "length_habits": habits}
        themed = sum(1 for seed in range(1, 13) if any(r for r in whole.plan(models, seed, "test", themed=True, band_returns=True).extras.get("melody", {}).get("returns", [])))
        self.assertEqual(themed, 12)                            # every themed plan returns to its theme
        p = whole.plan(models, 3, "test", themed=True, band_returns=True)
        self.assertTrue(all(r["with"] for r in p.extras["melody"]["returns"]))   # and never with the tune alone
        self.assertEqual((p.extras["options"]["themed"], p.extras["options"]["band_returns"], p.extras["options"]["plan_draws"]), (True, True, 1))
        plain = sum(1 for seed in range(1, 13) if whole.plan(models, seed, "test").extras.get("melody", {}).get("returns"))
        self.assertLess(plain, 12)                              # without the switch, the table's own rate

    def test_a_themed_plan_is_drawn_again_when_its_tune_has_one_phrase(self):
        """A one-part four-bar form gives the tune one phrase, so no letter draw can bring a theme back: the plan is drawn again
        until the form has room (two four-bar parts), and a game whose forms never have room ends unthemed and says so."""
        letters = tables.Table(("part", "phrases", "form"), "phrase letters", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "melody", "phrases": "2", "form": f}) for i, (o, f) in enumerate((("T n", "first"), ("n T", "last")))])
        lengths = tables.Table(("part", "meter", "habit"), "lengths", votes=tables.SHARES).fit(
            [tables.Unit(sid, "g", "4", {"part": "form", "meter": 4, "habit": "short"}) for sid in ("s", "t")])
        habits = tables.Table(("part",), "length habits", votes=tables.SHARES).fit([tables.Unit(sid, "g", "short", {"part": "form"}) for sid in ("s", "t")])
        mixed = tables.Table(("part",), "sizes", votes=tables.SHARES).fit([tables.Unit("s", "g", "1", {"part": "form"}), tables.Unit("t", "g", "2", {"part": "form"})])
        models = {"phrase_letters": letters, "sizes": mixed, "lengths": lengths, "length_habits": habits}
        plans = [whole.plan(models, seed, "test", themed=True) for seed in range(1, 13)]
        self.assertTrue(all(p.extras["melody"]["returns"] for p in plans))                 # every song came back to its theme
        self.assertTrue(any(p.extras["options"]["plan_draws"] > 1 for p in plans))         # some needed a second form
        self.assertTrue(all(len(p.parts) >= 2 for p in plans))                             # the one-part forms were drawn past
        narrow = tables.Table(("part",), "sizes", votes=tables.SHARES).fit([tables.Unit("s", "g", "1", {"part": "form"}), tables.Unit("t", "g", "1", {"part": "form"})])
        p = whole.plan({**models, "sizes": narrow}, 1, "test", themed=True)
        self.assertFalse(p.extras["melody"].get("returns"))
        self.assertEqual(p.extras["options"]["plan_draws"], whole.PLAN_TRIES)
        self.assertTrue(any("unthemed" in line for line in p.log))

    def test_the_line_and_its_second_voice(self):
        """The figure table counts an upper part's own line where it holds two voices; the second voice's bar is its own unit
        under the line's bar."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, 60.0, "a") for k in range(4) for i in range(8)]        # every eighth
        second = [(4.0 * k + i, 0.9, 52.0, "a") for k in range(4) for i in range(4)]            # the beats, with the line
        s = rhythm.Song("t", 4, 12, bars, [], notes={"accompaniment": line + second}, sid="s", game="g")
        s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", second)}
        self.assertEqual(rhythm.line_notes(s, "accompaniment"), line)
        patterns = {u.outcome for u in rhythm.units([s]) if u.values["part"] == "accompaniment"}
        self.assertEqual(patterns, {"0 1/2 1 3/2 2 5/2 3 7/2"})                                 # the line's bar, not the voices merged
        units = rhythm.second_figure_units([s])
        self.assertEqual(len(units), 4)
        self.assertEqual((units[0].outcome, units[0].values), ("1 0 1 0 1 0 1 0", {"part": "accompaniment", "feel": "duple", "tempo": rhythm.band(120.0), "onsets": "8", "line": "0 1/2 1 3/2 2 5/2 3 7/2"}))
        F = __import__("fractions").Fraction
        self.assertEqual(rhythm.second_mask([F(0), F(1), F(2), F(3)], [F(0), F(2), F(7, 2)]), "1 0 1 0 | 7/2")
        self.assertEqual(rhythm.apply_mask("0 1/2 1 3/2 2 5/2 3 7/2", "1 0 1 0 1 0 1 0"), "0 1 2 3")
        self.assertEqual(rhythm.apply_mask("0 1 2 3", "1 0 | 7/2"), "0 2 7/2")                       # a short mask read around the line
        self.assertEqual(rhythm.apply_mask("0 1 2 3", "-"), "-")
        self.assertEqual([u.outcome for u in rhythm.layer_sample_units([s])], ["sa sa"])      # both voices on sample "a" here
        self.assertEqual([rhythm.density_bin(n) for n in (1, 3, 4, 6, 7, 9, 10, 24)], ["1-3", "1-3", "4-6", "4-6", "7-9", "7-9", "10+", "10+"])
        s.voice_notes = {3: ("accompaniment", line)}
        self.assertIsNone(rhythm.line_notes(s, "accompaniment"))                                 # one voice: the part's bar
        self.assertEqual(rhythm.second_figure_units([s]), [])

    def test_the_theme_doubled_and_carried(self):
        """Where the tune plays its theme cell another part may play it too (theme_doubling, with the interval); a phrase
        whose tune is not the theme may have it carried by the bass (theme_carrier)."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        cell = lambda a, base: [(a, 0.9, base, "m"), (a + 1.0, 0.9, base + 2.0, "m"), (a + 2.0, 1.9, base + 4.0, "m")]   # noqa: E731
        other = lambda a, base: [(a, 0.4, base + 7.0, "m"), (a + 0.5, 0.4, base + 5.0, "m"), (a + 1.0, 2.9, base + 4.0, "m")]   # noqa: E731
        tune = cell(0.0, 60.0) + other(4.0, 60.0) + other(8.0, 60.0) + other(12.0, 60.0) + cell(16.0, 60.0) + other(20.0, 60.0) + other(24.0, 60.0) + other(28.0, 60.0)
        counter = other(0.0, 72.0) + other(4.0, 72.0) + other(8.0, 72.0) + other(12.0, 72.0) + cell(16.0, 72.0) + other(20.0, 72.0)
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune, "counter": counter}, sid="s", game="g", parts=[(0, 8, None, "A")])
        units = rhythm.theme_doubling_units([s])
        self.assertEqual([(u.outcome, u.values["place"]) for u in units], [("none", "statement"), ("counter:+12", "later")])
        self.assertEqual([u.outcome for u in rhythm.theme_carrier_units([s])], [])             # the second phrase opens with the theme: nothing to carry
        tune2 = cell(0.0, 60.0) + other(4.0, 60.0) + other(8.0, 60.0) + other(12.0, 60.0) + other(16.0, 62.0) + other(20.0, 60.0) + other(24.0, 60.0) + other(28.0, 60.0)
        bass = other(0.0, 36.0) + other(4.0, 36.0) + other(8.0, 36.0) + other(12.0, 36.0) + cell(16.0, 36.0) + other(20.0, 36.0) + other(24.0, 36.0) + other(28.0, 36.0)
        s2 = rhythm.Song("t", 4, 12, bars, [], notes={"melody": tune2, "bass": bass}, sid="s", game="g", parts=[(0, 8, None, "A")])
        self.assertEqual([u.outcome for u in rhythm.theme_carrier_units([s2])], ["bass"])      # bars 4-5 of the bass are the theme phrase's first two
        self.assertEqual([u.outcome for u in rhythm.theme_doubling_units([s2])], ["none"])

    def test_the_band_passes_copy_the_theme_and_the_repeats(self):
        """double_theme copies the tune's theme bar into the drawn part at the drawn interval; carry_theme puts the theme phrase into
        the bass's register under a phrase that is not the theme; copy_repeats makes a repeated part note for note."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={}, sid="s", game="g", parts=[(0, 4, None, "A"), (4, 4, 0, "A")])
        tune = [(0.0, 0.9, 60.0, 0), (1.0, 1.9, 62.0, 0), (2.0, 3.9, 64.0, 0)] + [(4.0 + k + 0.5 * i, 4.4 + k + 0.5 * i, 67.0 + i, 0) for k in range(0, 12, 4) for i in range(2)]
        s.notes["melody"] = [(a, b - a, m, "melody") for a, b, m, _ in tune]
        counter = [(t, u, m + 12.0, 0) for t, u, m, _ in tune]
        s.notes["counter"] = [(a, b - a, m, "counter") for a, b, m, _ in counter]
        bass = [(4.0 * k, 3.9, 36.0, 0) for k in range(8)]
        s.notes["bass"] = [(a, b - a, m, "bass") for a, b, m, _ in bass]
        written = {"melody": whole.Part("melody", list(tune), ["0 1 2"] + ["0 1/2 1 3/2"] * 7),
                   "counter": whole.Part("counter", list(counter), ["0 1 2"] + ["0 1/2 1 3/2"] * 7),
                   "bass": whole.Part("bass", list(bass), ["0"] * 8)}
        plays = [True] * 8
        plan = whole.Plan(1, "g", "t", 0, "major", 120.0, s.parts, 0, ["I"] * 8, [None] * 8, ["bass", "melody", "counter"], {}, [], {"melody": plays, "bass": plays, "counter": plays},
                          {"melody": (60, 80), "counter": (60, 84), "bass": (30, 45)}, {}, {}, {"melody": {"theme_bars": [0, 1, 2, 3], "letters": {0: "T"}}}, {}, [])
        doubling = tables.Table(("part", "place"), "theme doubling", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "counter:+12", {"part": "theme", "place": p}) for i, p in enumerate(("statement", "later", "statement"))])
        carrier = tables.Table(("part",), "theme carrier", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "bass", {"part": "carrier"}) for i in range(3)])
        models = {"theme_doubling": doubling, "theme_carrier": carrier}
        rng = random.Random(1)
        log = whole.double_theme(plan, s, written, models, rng)
        self.assertEqual(log, ["bar 0: the counter doubles the theme's cell (+12)"])
        self.assertEqual([n for n in written["counter"].notes if n[0] < 4.0], [(0.0, 0.9, 72.0, 0), (1.0, 1.9, 74.0, 0), (2.0, 3.9, 76.0, 0)])
        self.assertEqual([n[2] for n in s.notes["counter"] if n[0] < 4.0], [72.0, 74.0, 76.0])
        plan.extras["melody"]["letters"] = {0: "T", 1: "n"}
        log = whole.carry_theme(plan, s, written, models, rng)
        self.assertEqual(log, ["bar 4: the bass carries the theme phrase (-24)"])
        self.assertEqual([n for n in written["bass"].notes if 16.0 <= n[0] < 20.0][:3], [(16.0, 16.9, 36.0, 0), (17.0, 17.9, 38.0, 0), (18.0, 19.9, 40.0, 0)])
        log = whole.copy_repeats(plan, s, written)
        self.assertEqual(log, ["A (bars 4-7) plays A (bars 0-3) again note for note"])
        for role in ("melody", "counter", "bass"):
            first = [(round(t, 6), round(u, 6), m) for t, u, m, _ in written[role].notes if t < 16.0]
            again = [(round(t - 16.0, 6), round(u - 16.0, 6), m) for t, u, m, _ in written[role].notes if t >= 16.0]
            self.assertEqual(first, again, role)
            self.assertEqual(written[role].figures[4:], written[role].figures[:4])

    def test_the_backing_period_and_its_holds(self):
        """A bass playing the same two bars through a part has a period of 2 there; the bars inside it are held but the one varied."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        riff = lambda a: [(a, 0.9, 36.0, "b"), (a + 1.5, 0.4, 43.0, "b"), (a + 2.0, 0.9, 36.0, "b"), (a + 4.0, 0.9, 36.0, "b"), (a + 6.0, 1.9, 38.0, "b")]   # noqa: E731
        bass = [n for j in range(4) for n in riff(8.0 * j)]
        bass[-1] = (bass[-1][0], bass[-1][1], 48.0, "b")                                      # the last bar varied: an octave where a passing tone was
        chords = [vocab.Span(0.0, 32.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 12, bars, chords, notes={"bass": bass}, sid="s", game="g", parts=[(0, 8, None, "A")], tonic=0)
        self.assertEqual([(u.outcome, u.values) for u in rhythm.period_units([s])], [("2", {"part": "bass", "length": "medium", "tempo": rhythm.band(120.0)})])
        holds = [u.outcome for u in rhythm.period_hold_units([s])]
        self.assertEqual((len(holds), holds.count("varied")), (6, 1))
        self.assertEqual([rhythm.part_length(n) for n in (4, 5, 8, 9)], ["short", "medium", "medium", "long"])
        s.notes["bass"] = [n for j in range(8) for n in riff(4.0 * j)[:3]]                     # one bar, every bar: a period of 1
        self.assertEqual([u.outcome for u in rhythm.period_units([s])], ["1"])

    def test_the_moves_know_their_landing(self):
        """A moves table drawn by the beat and the tone left follows them, and the chord weighting stays out of its way."""
        t = tables.Table(("part", "mode", "place", "tone", "previous"), "moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "+4", {"part": "melody", "mode": "major", "place": "strong", "tone": "root", "previous": "start"}) for i in range(6)]
            + [tables.Unit(f"t{i}", "g", "+2", {"part": "melody", "mode": "major", "place": "strong", "tone": "another tone", "previous": "start"}) for i in range(6)])
        rng = random.Random(3)
        every = set(range(12))
        from_root = [writer.draw_move(t, "start", "major", 60.0, rng, (48, 84), every, True, (0, ""), set(), None, tone="root") for _ in range(30)]
        from_other = [writer.draw_move(t, "start", "major", 60.0, rng, (48, 84), every, True, (0, ""), set(), None, tone="another tone") for _ in range(30)]
        self.assertGreaterEqual(from_root.count(4), 22)
        self.assertGreaterEqual(from_other.count(2), 22)

    def test_the_feel_and_the_layered_bass(self):
        """A song's feel is triple from a quarter of its onsets on triplet positions; a two-voice bass's figure table counts its
        sustained line, the busy voice is the second line's unit, and the two voices' note lengths are counted apart."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        straight = [(4.0 * k + 0.5 * i, 0.4, 60.0, "m") for k in range(4) for i in range(8)]
        shuffle = [(4.0 * k + i + d, 0.3, 60.0, "m") for k in range(4) for i in range(4) for d in (0.0, 2 / 3)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"melody": straight}, sid="s", game="g")
        self.assertEqual(rhythm.song_feel(s), "duple")
        s2 = rhythm.Song("t", 4, 12, bars, [], notes={"melody": shuffle}, sid="s", game="g")
        self.assertEqual((rhythm.song_feel(s2), rhythm.feel_units([s2])[0].outcome), ("triple", "triple"))
        chords = [vocab.Span(0.0, 16.0, 0, "", 1.0)]
        long = [(4.0 * k, 3.9, 36.0, "b") for k in range(4)]                                   # the sustained line
        busy = [(4.0 * k + 0.5 * i, 0.2, 36.0, "b") for k in range(4) for i in range(8)]        # the staccato voice under it
        s3 = rhythm.Song("t", 4, 12, bars, chords, notes={"bass": long + busy}, sid="s", game="g", tonic=0, parts=[(0, 4, None, "A")])
        s3.voice_notes = {2: ("bass", long), 5: ("bass", busy)}
        self.assertEqual(rhythm.line_notes(s3, "bass"), long)
        self.assertEqual({u.outcome for u in rhythm.bass_units([s3])}, {"0:R"})                 # the line's bar, one root held
        seconds = rhythm.second_figure_units([s3])
        self.assertEqual(len(seconds), 4)
        self.assertEqual((seconds[0].values["part"], seconds[0].values["line"], seconds[0].values["onsets"]), ("bass", "0", "1"))
        self.assertEqual(seconds[0].outcome, "1 | 1/2 1 3/2 2 5/2 3 7/2")                         # with the held root, then seven of its own (the mask, round 27)
        sounds = {(u.values["voice"]): u.outcome for u in rhythm.layer_sound_units([s3])}
        self.assertGreater(float(sounds["line"]), float(sounds["second"]))
        self.assertEqual(sounds["second"], "0.4")
        s3.voice_notes = {2: ("bass", [(t, u, m, "long1234567890") for t, u, m, _ in long]), 5: ("bass", [(t, u, m, "short123456789") for t, u, m, _ in busy])}
        self.assertEqual([(u.outcome, u.values) for u in rhythm.layer_sample_units([s3])], [("slong123456 sshort12345", {"part": "bass"})])
        self.assertEqual([u.values["tempo"] for u in rhythm.second_figure_units([s3])][:1], [rhythm.band(120.0)])

    def test_the_kit_from_the_namers_names_and_the_group_caps(self):
        """The pack's kit takes each piece's most-played sample by the drum namer's name, a second hat as the open hat and the
        busiest other sound as the rim; a plan's drum group habits cap a free-drawn kit bar's hits a letter."""
        from collections import Counter
        uses = Counter({"a": 100, "b": 90, "c": 80, "d": 70, "e": 60, "f": 50, "g": 10, "h": 5})
        labels = {"a": "kick", "b": "snare", "c": "hat", "d": "hat", "e": "cymbal", "f": "tom", "g": "other", "h": "snare"}
        self.assertEqual(pack.kit_from_names(uses, labels), {"kick": "a", "snare": "b", "hihat": "c", "open_hihat": "d", "crash": "e", "tom": "f", "rim": "g"})
        self.assertEqual(pack.kit_from_names(uses, {"a": "kick", "c": "hat"}), {})                 # no snare named: the brightness kit instead
        self.assertEqual(writer.group_caps({("c",): "sparse mixed", ("h",): "dense varied", ("K", "S", "t"): "medium mixed"}), {"c": 2, "h": 16})
        self.assertEqual(writer.group_caps("dense mixed"), {})
        env = writer.free_drum_envelope({"K", "S", "c"}, {"c": 2})(None, 4)
        self.assertEqual((env[0]["c"], env[0]["K"]), ((0, 2), (0, 16)))
        self.assertTrue(writer.drum_within("0:K 1:c 2:S 3:c", env))
        self.assertFalse(writer.drum_within("0:K 1/2:c 1:c 3/2:c 2:S", env))

    def test_the_sample_for_a_register_and_the_line_voices_register(self):
        """The sample for a part is the pool's whose game-played range covers the register best, the part's top weighing most; the
        pack's other samples when the pool reaches nowhere near the top; a layered part's register is its line voice's."""
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "56-68", {"part": "sa"}) for i in range(3)] + [tables.Unit(f"t{i}", "g", "72-88", {"part": "sb"}) for i in range(3)]
            + [tables.Unit(f"u{i}", "g", "84-96", {"part": "sc"}) for i in range(3)])
        raw = lambda n: n[len("p_"):] if n.startswith("p_") else n   # noqa: E731
        rng = random.Random(1)
        self.assertEqual(whole.best_sample(ranges, ["p_sa", "p_sa", "p_sb"], (60, 70), rng, raw), "p_sa")
        self.assertEqual(whole.best_sample(ranges, ["p_sa", "p_sa", "p_sb"], (74, 88), rng, raw), "p_sb")
        self.assertEqual(whole.best_sample(ranges, ["p_sa", "p_sa"], (84, 96), rng, raw, others=["sc", "sb"]), "sc")   # the pool reaches nowhere near 96
        self.assertEqual(whole.best_sample(ranges, ["p_sa"], (60, 72), rng, raw, others=["sc"]), "p_sa")             # within REACH: the pool's
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, 60.0 + (i % 4) * 2, "a") for k in range(4) for i in range(8)]
        high = [(4.0 * k + i, 0.9, 88.0 + (i % 2) * 3, "a") for k in range(4) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"accompaniment": line + high}, sid="s", game="g")
        s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", high)}
        self.assertEqual(rhythm.register_notes(s, "accompaniment"), line)
        self.assertEqual([u.outcome for u in rhythm.register_units([s])], ["60-64"])                  # the line's (its 90th percentile 66, to the grain), not 60-92
        s.voice_notes = {3: ("accompaniment", line)}
        self.assertIsNone(rhythm.register_notes(s, "accompaniment"))

    def test_the_voice_beside_the_line_takes_its_interval_from_the_table(self):
        """voice_intervals counts a voice's interval to the line in scale steps where they strike together, voice_moves its
        own move at every onset by place; the upper writer draws the voice's pitch from the two words' product with the line
        and from its move alone, never a pitch another voice holds."""
        from fractions import Fraction
        from bitcomposer.translate import writer, tables, vocab
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, [64.0, 67.0, 72.0, 67.0][i % 4], "a") for k in range(4) for i in range(8)]   # eighths on E G C G
        second = []
        for k in range(4):
            second += [(4.0 * k, 0.9, 60.0, "b"), (4.0 * k + 2.0, 0.9, 60.0, "b"), (4.0 * k + 2.25, 0.4, 62.0, "b")]   # with the line a third below, then alone a step up
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={"accompaniment": line + second}, sid="s", game="g", tonic=0, mode="major")
        s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", second)}
        iv = rhythm.voice_interval_units([s])
        self.assertEqual({u.outcome for u in iv}, {"-2"})                                      # C under E: a third below, every time
        self.assertEqual([u.values["previous"] for u in iv][:3], [rhythm.START, "-2", "-2"])
        self.assertEqual(iv[0].values["kind"], "apart")
        mv = rhythm.voice_move_units([s])
        self.assertEqual([u.outcome for u in mv if u.values["place"] == "alone"], ["1"] * 4)   # alone: a step up from its own C
        self.assertEqual({u.outcome for u in mv if u.values["place"] == "with"}, {"0", "-1"})  # with the line: back to C from C or from D
        # the writer: tables that say "an octave above the line" and "hold your note" with the line, "a step up" alone
        iv_t = tables.Table(("part", "kind", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "7", {"part": "accompaniment", "kind": "apart", "previous": p}) for i in range(20) for p in (rhythm.START, "7")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "accompaniment", "kind": "apart", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("1", "alone"))])
        song = rhythm.Song("w", 4, 12, bars[:2], [vocab.Span(0.0, 8.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        shared = {}
        for k in range(2):
            for pos in range(4):                                                               # a line that repeats middle C on every beat
                shared[(k, Fraction(pos))] = ((0, ""), "R 3 5", ["R", "3", "5"])
                shared[("line", (k, Fraction(pos)))] = 60
                shared.setdefault(("taken", (k, Fraction(pos))), set()).add(60)
        notes, figures, _ = writer.upper(song, "accompaniment", [1], {1: (60, 96)}, {"voice_intervals": iv_t, "voice_moves": mv_t}, random.Random(1),
                                         "dense", "triad", 0.5, key=(0, "major"), plays=[True, True], figures=["0 2 5/2", "0 2 5/2"], shared=shared,
                                         tone_index=writer.ANY_TONE, kind="apart")
        got = {(round(a, 2), int(m)) for a, b, m, v in notes}
        self.assertEqual(got, {(0.0, 72), (2.0, 72), (2.5, 74), (4.0, 72), (6.0, 72), (6.5, 74)})   # the octave above, held; a step up alone (the
        # smoothing leaves the table's other outcome a few percent at every draw: the seed is one where the words' own answers come up)
        self.assertTrue(all(int(m) != 60 for a, b, m, v in notes))

    def test_a_floor_steps_down_from_a_one_outcome_context(self):
        """A chain floored on a habit context with one outcome draws that outcome alone (all rests: a song without drums);
        with FLOOR_OUTCOMES the floor steps down to a level that holds a choice. A one-song context with bars of its own stays."""
        from bitcomposer.translate import tables
        units = [tables.Unit("s1", "g", "-", {"part": "drums", "habit": "thin", "previous": rhythm.START})] * 6
        units += [tables.Unit(f"s{i}", "g", "0:K 2:S", {"part": "drums", "habit": "full", "previous": rhythm.START}) for i in range(2, 6)]
        t = tables.Table(("part", "habit", "previous"), "x").fit(units)
        rng = random.Random(1)
        floored = {t.draw(("drums", "thin", rhythm.START), rng, floored=False, floor_k=2) for _ in range(30)}
        self.assertEqual(floored, {"-"})
        stepped = {t.draw(("drums", "thin", rhythm.START), rng, floored=False, floor_k=2, floor_outcomes=tables.FLOOR_OUTCOMES) for _ in range(30)}
        self.assertIn("0:K 2:S", stepped)
        self.assertEqual(tables.FLOOR_OUTCOMES, 2)
        units2 = [tables.Unit("s1", "g", o, {"part": "drums", "habit": "own", "previous": rhythm.START}) for o in ("-", "0:K", "0:K 2:S")] * 3
        t2 = tables.Table(("part", "habit", "previous"), "x").fit(units2 + units[6:])
        stays = {t2.draw(("drums", "own", rhythm.START), rng, floored=False, floor_k=2, floor_outcomes=tables.FLOOR_OUTCOMES) for _ in range(40)}
        self.assertTrue(stays <= {"-", "0:K", "0:K 2:S"})                                  # one song, three bars: its own vocabulary, kept

    def test_the_pair_of_samples_applies_whole_and_within_reach(self):
        """layer_samples counts the counter-line's pairs too; a pair is taken only from the part's own pairs and only where the
        pack holds both samples; a kit slot takes only a sample the game plays as a drum."""
        from bitcomposer.translate import tables, pack
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(2)]
        line = [(4.0 * k + i, 0.9, 72.0, "aaaaaaaaaa1") for k in range(2) for i in range(4)]
        other = [(4.0 * k + i + 0.5, 0.4, 60.0, "bbbbbbbbbb2") for k in range(2) for i in range(4)]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"counter": line + other}, sid="s", game="g")
        s.voice_notes = {3: ("counter", line), 4: ("counter", other)}
        self.assertEqual([(u.values["part"], u.outcome) for u in rhythm.layer_sample_units([s])], [("counter", "saaaaaaaaaa sbbbbbbbbbb")])
        pairs = tables.Table(("part",), "layer_samples", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "sline ssecond", {"part": "accompaniment"}) for i in range(3)])
        rng = random.Random(1)
        self.assertIsNone(whole.pair_for({"layer_samples": pairs}, "counter", {"sline", "ssecond"}, rng))      # no counter pairs: none, not another part's
        self.assertIsNone(whole.pair_for({"layer_samples": pairs}, "accompaniment", {"ssecond"}, rng))         # the pack lacks the line's: none, not half
        self.assertEqual(whole.pair_for({"layer_samples": pairs}, "accompaniment", {"sline", "ssecond"}, rng), ("sline", "ssecond"))
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "36-48", {"part": "slow"}) for i in range(3)])
        self.assertFalse(whole.reaches(ranges, "slow", (52, 64), rng))                                          # a bass sample under a voice an octave above it
        self.assertTrue(whole.reaches(ranges, "slow", (40, 52), rng))
        self.assertTrue(whole.reaches(ranges, "unknown", (80, 92), rng))
        g = pack.Gathered(game="g")
        g.uses["drums"].update({"kick": 50, "mallet": 57}); g.uses["melody"].update({"mallet": 300}); g.uses["counter"].update({"mallet": 347})
        self.assertEqual(pack.drum_uses(g), {"kick": 50})

    def test_levels_arc_and_one_timbre_pairs(self):
        """The levels words count a part's level against the song's loudest and a second voice's against its line's; the arc
        words place a tune's climax and the other phrases under it; a pair with one sample for both voices applies as the
        line's sample; the pack carries each sample's envelope and gives the kit's other slot to the game's own other strikes."""
        from bitcomposer.translate import phrases, tables, pack
        s = rhythm.Song("t", 4, 12, [(0.0, 4.0)], [], notes={}, sid="s", game="g")
        s.levels = {"melody": 0.22, "bass": 0.28, "accompaniment": 0.19}
        self.assertEqual({u.values["part"]: u.outcome for u in rhythm.level_units([s])}, {"melody": "0.8", "bass": "1.0", "accompaniment": "0.7"})
        line = [(0.5 * i, 0.4, 60.0, "a") for i in range(8)]; other = [(float(i), 0.9, 52.0, "b") for i in range(4)]
        s.notes = {"accompaniment": line + other}; s.voice_notes = {3: ("accompaniment", line), 4: ("accompaniment", other)}
        s.voice_levels = {3: 0.20, 4: 0.12}
        self.assertEqual([u.outcome for u in rhythm.layer_level_units([s])], ["0.6"])
        self.assertEqual([phrases.place_of(i, 5) for i in range(5)], ["opening", "early", "middle", "late", "closing"])
        self.assertEqual(phrases.place_of(0, 1), "opening")
        self.assertEqual((phrases._class(0, phrases.BELOW), phrases._class(4, phrases.BELOW), phrases._class(12, phrases.BELOW), phrases._class(6, phrases.ABOVE)), ("0", "3-5", "10+", "6+"))
        pairs = tables.Table(("part",), "layer_samples", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "sx sx", {"part": "accompaniment"}) for i in range(3)])
        self.assertEqual(whole.pair_for({"layer_samples": pairs}, "accompaniment", set(), random.Random(1)), ("same", "same"))
        g = pack.Gathered(game="g")
        g.envelopes["k"].update({("adsr", 0xFF, 0xE0): 5, ("gain", 0x7F): 1}); g.envelopes["j"].update({("gain", 0x60): 2})
        self.assertEqual((pack.envelope_of(g, "k"), pack.envelope_of(g, "j"), pack.envelope_of(g, "z")), ({"adsr": [255, 224]}, {"gain": 96}, None))
        g.other.update({"snare": 500, "mallet": 57, "hit": 15})
        self.assertEqual(pack.other_slot(g, {"snare": 1, "mallet": 1}), "snare")
        self.assertIsNone(pack.other_slot(g, {}))

    def test_a_notes_gap_runs_into_the_next_bar_and_its_share_follows_the_gap(self):
        """A bar's last note runs to the next bar's first onset (the gap the share was counted against); the share a note
        sounds may come by the gap's class (gap_sounds); the second bass voice follows the line's pitch where they strike together."""
        from bitcomposer.translate import writer, tables, vocab
        bars = [(0.0, 4.0), (4.0, 8.0)]
        song = rhythm.Song("w", 4, 12, bars, [vocab.Span(0.0, 8.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        figures = ["0:R 3:R", "1/2:R 2:R"]
        self.assertEqual(writer.first_onset(figures, bars, 1), 4.5)
        self.assertIsNone(writer.first_onset(figures, bars, 2))
        notes, _, _ = writer.realize(figures[0], 0.0, 4.0, song, 36, 1.0, {0, 2, 4, 5, 7, 9, 11}, 0, None, runs_to=4.5)
        self.assertEqual([(a, b) for a, b, m in notes], [(0.0, 3.0), (3.0, 4.5)])                 # the last note runs on to 4.5, not 4.0
        shares = {"<1": 0.5, "1-2": 0.5, "2-4": 1.0, "4+": 1.0}
        self.assertEqual((writer.share_at(shares, 0.5), writer.share_at(shares, 3.0), writer.share_at(0.7, 3.0)), (0.5, 1.0, 0.7))
        s = rhythm.Song("t", 4, 12, bars, [], notes={}, sid="s", game="g")
        line = [(0.0, 3.9, 36.0, "a"), (4.0, 1.0, 36.0, "a"), (6.0, 1.9, 38.0, "a")]
        second = [(0.0, 0.25, 36.0, "b"), (0.5, 0.25, 36.0, "b"), (1.0, 2.9, 36.0, "b"), (4.0, 0.25, 36.0, "b"), (4.5, 3.4, 36.0, "b")]
        s.notes = {"bass": line + second}; s.voice_notes = {1: ("bass", line), 2: ("bass", second)}
        units = rhythm.gap_sound_units([s])
        by = {(u.values["voice"], u.values["gap"]): u.outcome for u in units}
        self.assertEqual((by[("line", "4+")], by[("second", "<1")], by[("second", "2-4")]), ("1.0", "0.5", "1.0"))
        self.assertEqual(rhythm.gap_class(0.5), "<1"); self.assertEqual(rhythm.gap_class(4.0), "4+")
        # the second bass voice on the line's pitch: a table that says "the same note" with the line and "hold" alone
        iv = tables.Table(("part", "kind", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "0", {"part": "bass", "kind": "apart", "previous": p}) for i in range(20) for p in (rhythm.START, "0")])
        mv = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "bass", "kind": "apart", "place": pl}) for i in range(20) for o, pl in (("2", "with"), ("0", "alone"))])   # with the line it moves as the line does
        shared = {("line", (0, __import__("fractions").Fraction(0))): 40.0, ("line", (0, __import__("fractions").Fraction(2))): 43.0}
        midi, steps = writer.beside_pitch({"voice_intervals": iv, "voice_moves": mv}, "bass", "apart", {0, 2, 4, 5, 7, 9, 11}, random.Random(1), 43.0, "0", 40.0, 2)
        self.assertEqual((midi, steps), (43, 0))
        midi, steps = writer.beside_pitch({"voice_intervals": iv, "voice_moves": mv}, "bass", "apart", {0, 2, 4, 5, 7, 9, 11}, random.Random(1), None, "0", 43.0, 0)
        self.assertEqual((midi, steps), (43, None))

    def test_the_second_bass_voice_is_a_mask_over_the_line(self):
        """The second bass voice's bar is counted as a mask over the sustained line's onsets plus its own (as the chord parts'
        are), and written from the line's figure: the line's marks where it strikes with the line, the root at its own onsets."""
        from fractions import Fraction
        from bitcomposer.translate import writer
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        line = [(4.0 * k + i, 0.9, [36.0, 36.0, 43.0, 43.0][i], "a") for k in range(4) for i in range(4)]          # the beats
        slap = [(4.0 * k + t, 0.2, 36.0, "b") for k in range(4) for t in (0.0, 0.5, 1.0, 2.0, 2.5, 3.5)]            # beats 1, 2, 3 and three of its own
        s = rhythm.Song("t", 4, 12, bars, [], notes={"bass": line + slap}, sid="s", game="g", bpm=120.0)
        s.voice_notes = {1: ("bass", line), 2: ("bass", slap)}
        units = [u for u in rhythm.second_figure_units([s]) if u.values["part"] == "bass"]
        self.assertEqual(len(units), 4)
        self.assertEqual((units[0].outcome, units[0].values["onsets"], units[0].values["line"]), ("1 1 1 0 | 1/2 5/2 7/2", "4", "0 1 2 3"))
        self.assertEqual(writer.mask_figure("0:R 1:R 2:5 3:5", "1 1 1 0 | 1/2 5/2 7/2"), "0:R 1/2:R 1:R 2:5 5/2:R 7/2:R")
        self.assertEqual(writer.mask_figure("0:R 1:R 2:5 3:5", "-"), writer.REST)
        self.assertEqual(writer.mask_figure(writer.REST, "1 1"), writer.REST)

    def test_the_bass_locks_to_the_kits_accents(self):
        """The kit's accents are the positions where two pieces strike together; bass_locks counts the share of them the bass
        strikes with; a table's floor may step down where its context has too few songs."""
        from bitcomposer.translate import tables
        bars = [(0.0, 4.0), (4.0, 8.0)]
        drums = [(t, 0.1, float("nan"), "kick") for t in (0.0, 2.0, 4.0, 6.0)] + [(t, 0.1, float("nan"), "hat") for t in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0)]
        self.assertEqual(rhythm.kit_accents(drums, bars, 12), {0: {0, 2}, 1: {0, 2}})
        bass = [(0.0, 0.9, 36.0, "b"), (2.0, 0.9, 36.0, "b"), (4.0, 0.9, 36.0, "b"), (5.5, 0.4, 38.0, "b")]
        s = rhythm.Song("t", 4, 12, bars, [], notes={"bass": bass, "drums": drums}, sid="s", game="g")
        s.voice_notes = {1: ("bass", bass)}
        self.assertEqual([u.outcome for u in rhythm.bass_lock_units([s])], ["0.8"])                 # three of the four accents carry a bass note
        units = [tables.Unit("s1", "g", "1 1", {"part": "bass", "onsets": "2"})] * 4 + [tables.Unit(f"s{i}", "g", "1 0 | 1/2", {"part": "bass", "onsets": "3"}) for i in range(2, 6)]
        t = tables.Table(("part", "onsets"), "m").fit(units)
        rng = random.Random(1)
        held = {t.draw(("bass", "2"), rng, floored=False, floor_k=2) for _ in range(20)}
        self.assertEqual(held, {"1 1"})                                                               # the one-song floor, as it stands
        stepped = {t.draw(("bass", "2"), rng, floored=False, floor_k=2, floor_songs=2) for _ in range(40)}
        self.assertIn("1 0 | 1/2", stepped)                                                           # the floor steps down to the part: its other songs' masks reach

    def _tune_and_counter(self):
        """A four-bar song: the tune on the beats of bars 0 to 2 (resting in bar 3), the counter with it on beats 1 and 3,
        its own on the and of 4, and alone in bar 3; the counter on another sample, a third below."""
        from bitcomposer.translate import vocab
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        tune = [(4.0 * k + i, 0.9, [64.0, 65.0, 67.0, 65.0][i], "lead") for k in range(3) for i in range(4)]
        counter = [(4.0 * k + t, 0.9, m, "ctr") for k in range(3) for t, m in ((0.0, 60.0), (2.0, 64.0), (3.5, 62.0))] + [(12.0, 1.9, 60.0, "ctr"), (14.0, 1.9, 62.0, "ctr")]
        s = rhythm.Song("t", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={"melody": tune, "counter": counter}, sid="s", game="g", bpm=120.0, tonic=0, mode="major")
        s.voice_notes = {1: ("melody", tune), 2: ("counter", counter)}
        s.levels = {"melody": 0.20, "counter": 0.20}
        return s, bars

    def test_the_counter_is_a_mask_over_the_tune(self):
        """counter_figures counts the counter-line's bar as a mask over the tune's onsets plus its own (the tune's line as the
        line), and its own onsets alone where the tune rests; apply_mask gives those own onsets at a resting line."""
        s, _ = self._tune_and_counter()
        units = rhythm.counter_figure_units([s])
        self.assertEqual([u.outcome for u in units], ["1 0 1 0 | 7/2"] * 3 + ["| 0 2"])
        self.assertEqual(units[0].values, {"part": "counter", "feel": "duple", "tempo": rhythm.band(120.0), "onsets": "4", "line": "0 1 2 3"})
        self.assertEqual((units[3].values["onsets"], units[3].values["line"]), ("0", "-"))
        self.assertEqual(rhythm.apply_mask("0 1 2 3", "1 0 1 0 | 7/2"), "0 2 7/2")
        self.assertEqual(rhythm.apply_mask("-", "| 0 2"), "0 2")                                   # the tune rests: the counter's own onsets
        self.assertEqual(rhythm.apply_mask("-", "-"), "-")
        self.assertEqual(rhythm.second_mask([], []), "-")
        s.notes["counter"] = s.notes["counter"][:3]                                                 # the counter in bar 0 only: bars 1 and 2 rest
        s.voice_notes[2] = ("counter", s.notes["counter"])                                          # under the tune, bar 3 (both rest) is not counted
        self.assertEqual([u.outcome for u in rhythm.counter_figure_units([s])], ["1 0 1 0 | 7/2", "-", "-"])
        del s.notes["counter"]
        self.assertEqual(rhythm.counter_figure_units([s]), [])

    def test_the_counter_takes_its_pitch_beside_the_tune(self):
        """The voice words count the counter beside the tune with the kind its sample relation (counter_samples: same or
        other); writer.counter writes it over the mask's positions: the tune's pitch and the drawn interval where they strike
        together, its own move between, its own onsets alone where the tune rests."""
        from fractions import Fraction
        from bitcomposer.translate import writer, tables, vocab
        s, bars = self._tune_and_counter()
        self.assertEqual([u.outcome for u in rhythm.counter_sample_units([s])], ["other"])
        s.notes["counter"] = [n[:3] + ("lead",) for n in s.notes["counter"]]; s.voice_notes[2] = ("counter", s.notes["counter"])
        self.assertEqual(rhythm.counter_kind(s), "same")
        iv = [u for u in rhythm.voice_interval_units([s]) if u.values["part"] == "counter"]
        self.assertEqual(({u.outcome for u in iv}, iv[0].values["kind"], iv[0].values["previous"], iv[1].values["previous"]), ({"-2"}, "same", rhythm.START, "-2"))
        mv = [u for u in rhythm.voice_move_units([s]) if u.values["part"] == "counter"]
        self.assertEqual(sorted({(u.outcome, u.values["place"]) for u in mv}), [("-1", "alone"), ("-1", "with"), ("1", "alone"), ("2", "with")])
        # the writer: a table that says "a third below the tune" and "hold the note" with the tune, "a step up" alone
        iv_t = tables.Table(("part", "kind", "previous"), "voice_intervals", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "-2", {"part": "counter", "kind": "other", "previous": p}) for i in range(20) for p in (rhythm.START, "-2")])
        mv_t = tables.Table(("part", "kind", "place"), "voice_moves", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", o, {"part": "counter", "kind": "other", "place": pl}) for i in range(20) for o, pl in (("0", "with"), ("1", "alone"))])
        vals = tables.Table(("part", "value", "habit"), "values", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "held", {"part": "counter", "value": "1", "habit": "held"}) for i in range(3)])
        song = rhythm.Song("w", 4, 12, bars, [vocab.Span(0.0, 16.0, 0, "", 1.0)], notes={}, sid="w", game="g", tonic=0, mode="major")
        tune = [(4.0 * k + i, 4.0 * k + i + 0.9, 72.0, 0) for k in range(3) for i in range(4)]           # the tune repeats C on every beat
        tune_figs = ["0 1 2 3"] * 3 + [writer.REST]
        notes, figures, log = writer.counter(song, tune, tune_figs, ["1 0 1 0 | 7/2", "1 1 1 1", writer.REST, "| 0 2"], (48, 96),
                                             {"voice_intervals": iv_t, "voice_moves": mv_t, "values": vals}, random.Random(1), "other",
                                             key=(0, "major"), articulation="held", register=(60, 84))
        self.assertEqual(figures, ["0 2 7/2", "0 1 2 3", writer.REST, "0 2"])
        got = {round(a, 2): int(m) for a, b, m in notes}
        self.assertEqual(got, {0.0: 69, 2.0: 69, 3.5: 71, 4.0: 69, 5.0: 69, 6.0: 69, 7.0: 69, 12.0: 71, 14.0: 72})   # A under C; a step up alone, the
        self.assertAlmostEqual(notes[1][1] - notes[1][0], 1.5 * writer.HELD, places=3)           # tune's rest in bar 3 filled from where it left off
        self.assertAlmostEqual(notes[2][1] - notes[2][0], 0.5 * writer.HELD, places=3)           # a bar's last note runs to the next bar's first onset
        self.assertAlmostEqual(notes[6][1] - notes[6][0], 1.0 * writer.HELD, places=3)           # ...but stops at the bar line before a rest bar
        self.assertIn("6 with the tune's onsets, 3 its own", log[0])
        # the plan draws the kind and the level once a song, and the rendering gives a "same" counter the tune's sample
        kinds = tables.Table(("part",), "counter_samples", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "same", {"part": "counter"}) for i in range(3)])
        self.assertEqual(whole._draw({"counter_samples": kinds}, "counter_samples", ("counter",), random.Random(1)), "same")

    def test_the_counters_level_is_a_share_of_the_tunes(self):
        """counter_levels counts the counter's level over the tune's in tenths; the plan sets the counter's level to the tune's
        times the drawn share instead of a draw of its own."""
        from bitcomposer.translate import tables
        s, _ = self._tune_and_counter()
        s.levels = {"melody": 0.20, "counter": 0.16}
        self.assertEqual([u.outcome for u in rhythm.counter_level_units([s])], ["0.8"])
        s.levels = {"melody": 0.10, "counter": 0.30}
        self.assertEqual([u.outcome for u in rhythm.counter_level_units([s])], ["1.5"])            # capped, as layer_levels is
        del s.notes["counter"]
        self.assertEqual(rhythm.counter_level_units([s]), [])
        units = lambda name, outcome, part: [tables.Unit(f"s{i}", "g", outcome, {"part": part}) for i in range(3)]   # noqa: E731
        models = {"balance": tables.Table(("part",), "balance", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "bass=half counter=half melody=main", {"part": rhythm.ARRANGEMENT}) for i in range(3)]),
                  "levels": tables.Table(("part",), "levels", votes=tables.SHARES).fit(units("levels", "0.8", "melody") + units("levels", "0.4", "counter") + units("levels", "1.0", "bass")),
                  "counter_levels": tables.Table(("part",), "counter_levels", votes=tables.SHARES).fit(units("counter_levels", "1.2", "counter")),
                  "counter_samples": tables.Table(("part",), "counter_samples", votes=tables.SHARES).fit(units("counter_samples", "same", "counter"))}
        p = whole.plan(models, 1, "g")
        self.assertEqual((p.levels["melody"], round(p.levels["counter"], 2), p.levels["bass"]), (0.8, 0.96, 1.0))
        self.assertEqual((p.extras["counter"]["sample"], p.extras["counter"]["level"]), ("same", 1.2))
        self.assertIn("counter beside the tune: same sample, level 1.2 of the tune's", p.log)

    def test_the_counters_sample_is_the_games_pair_with_the_tunes(self):
        """counter_pairs counts the counter's sample under the tune's where the counter plays another (the pack's ids); at the
        rendering the draw under the tune's sample is taken where the pack holds it and it reaches the written register, the
        part's level (over all tunes) is still a count, and only where nothing counted fits does the pool rule remain."""
        s, _ = self._tune_and_counter()
        units = rhythm.counter_pair_units([s])
        self.assertEqual([(u.outcome, u.values) for u in units], [("sctr", {"part": "counter", "tune": "slead"})])
        s.notes["counter"] = [n[:3] + ("lead",) for n in s.notes["counter"]]; s.voice_notes[2] = ("counter", s.notes["counter"])
        self.assertEqual(rhythm.counter_pair_units([s]), [])                                        # on the tune's sample: counter_samples' "same", no pair
        pairs = tables.Table(("part", "tune"), "counter_pairs", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "sb", {"part": "counter", "tune": "sa"}) for i in range(3)]
            + [tables.Unit(f"t{i}", "g", "sd", {"part": "counter", "tune": "sc"}) for i in range(3)])
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit(
            [tables.Unit(f"s{i}", "g", "60-72", {"part": "sb"}) for i in range(3)] + [tables.Unit(f"t{i}", "g", "36-48", {"part": "sd"}) for i in range(3)])
        models, rng = {"counter_pairs": pairs}, random.Random(1)
        w = pairs.weights(("counter", "sa"), floor_k=whole.PLAN_FLOOR, min_songs=whole.PLAN_SONGS)   # the tune's context at 3 / (3 + 1) of the
        self.assertEqual({k: round(v, 3) for k, v in w.items()}, {"sb": 0.875, "sd": 0.125})           # mass, the part's level (sb and sd even) the rest
        self.assertEqual(pairs.weights(("counter", "sx"), floor_k=whole.PLAN_FLOOR, min_songs=whole.PLAN_SONGS), {"sb": 0.5, "sd": 0.5})   # unseen: the part's alone
        self.assertEqual(pairs.weights(("counter", "sx"), floor_k=None, min_songs=0), {"sb": 0.5, "sd": 0.5})
        self.assertEqual(pairs.weights(("harmony", "sx")), {"sb": 0.5, "sd": 0.5})                    # another part: the root's, as draw() backs off
        for _ in range(8):                                                                               # sd is out of reach two octaves down: sb
            self.assertEqual(whole.counter_pair_for(models, "sa", {"sa", "sb", "sd"}, ranges, (60, 72), rng), ("sb", "tune", ["sd out of reach of 60-72"]))
            self.assertEqual(whole.counter_pair_for(models, "sx", {"sa", "sb", "sd"}, ranges, (60, 72), rng)[:2], ("sb", "part"))   # a tune sample the game never had
        got = whole.counter_pair_for(models, "sa", {"sa", "sd"}, ranges, (60, 72), rng)              # the pack lacks sb: nothing counted fits,
        self.assertEqual(got, (None, None, ["sb not in the pack", "sd out of reach of 60-72"]))       # the pool rule stands
        self.assertEqual(whole.counter_pair_for(models, "sa", {"sa", "sb", "sd"}, ranges, (88, 100), rng)[:2], (None, None))   # out of reach
        one = tables.Table(("part", "tune"), "counter_pairs", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "sb", {"part": "counter", "tune": "sa"}) for i in range(3)])
        self.assertEqual(whole.counter_pair_for({"counter_pairs": one}, "sb", {"sa", "sb"}, ranges, (60, 72), rng), (None, None, ["sb the tune's own"]))   # not "other"
        self.assertEqual(whole.counter_pair_for({}, "sa", {"sa", "sb"}, ranges, (60, 72), rng), (None, None, None))                    # no table: the rule, unlogged

    def test_the_samples_playing_habits(self):
        """A sample's shortest note and fastest bars in the game are counted per song; the sample choice weighs the part's speed;
        a drawn floor holds a note's length."""
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(4)]
        fast = [(4.0 * k + 0.25 * i, 0.1, 60.0, "quick12345678") for k in range(4) for i in range(16)]    # sixteenths, 50 ms at 120 BPM
        slow = [(4.0 * k + i, 0.9, 48.0, "pad1234567890") for k in range(4) for i in range(4)]              # quarters, 450 ms
        s = rhythm.Song("t", 4, 12, bars, [], notes={"accompaniment": fast, "bass": slow}, sid="s", game="g", bpm=120.0)
        lengths = {u.values["part"]: u.outcome for u in rhythm.sample_length_units([s])}
        speeds = {u.values["part"]: u.outcome for u in rhythm.sample_speed_units([s])}
        self.assertEqual((lengths["squick12345"], lengths["spad1234567"]), ("60", "long"))
        self.assertEqual((speeds["squick12345"], speeds["spad1234567"]), ("8", "2"))
        ranges = tables.Table(("part",), "ranges", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "56-68", {"part": n}) for i in range(3) for n in ("sa", "sb")])
        sp = tables.Table(("part",), "speeds", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", o, {"part": n}) for i in range(3) for n, o in (("sa", "3"), ("sb", "12"))])
        raw = lambda n: n   # noqa: E731
        rng = random.Random(2)
        self.assertEqual(whole.best_sample(ranges, ["sa", "sb"], (58, 66), rng, raw, speed=8.0, models={"sample_speeds": sp}), "sb")   # the part runs at 8 a second: the pad loses
        self.assertIn(whole.best_sample(ranges, ["sa", "sb"], (58, 66), rng, raw, speed=1.0, models={"sample_speeds": sp}), ("sa", "sb"))
        self.assertEqual(whole.best_sample(ranges, ["sa", "sb"], (58, 66), rng, raw, speed=20.0, models={"sample_speeds": sp}), "sb")   # none this fast: the least excess over the game's fastest ever
        self.assertEqual(whole.sample_speed({"sample_speeds": sp}, "sb", rng), (12.0, 12.0))
        fl = tables.Table(("part",), "lengths", votes=tables.SHARES).fit([tables.Unit(f"s{i}", "g", "80", {"part": "sa"}) for i in range(3)])
        self.assertEqual(whole.sample_floor({"sample_lengths": fl}, "sa", rng), 0.08)
        self.assertEqual(whole.sample_floor({"sample_lengths": fl}, "sz", rng), 0.0)

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
