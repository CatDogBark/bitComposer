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
        self.assertEqual((seconds[0].values["part"], seconds[0].values["line"], seconds[0].values["onsets"]), ("bass", "0:R", "1"))
        self.assertEqual(seconds[0].outcome.count("R"), 8)                                      # eight roots a bar under the held one
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
