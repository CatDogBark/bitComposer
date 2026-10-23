"""The tables framework: votes, backoff, scoring, draws, the round trip; and the rhythm units."""
import json
from collections import Counter
import math
import os
import random
import tempfile
import unittest
from fractions import Fraction

from bitcomposer.translate import rhythm, tables
from bitcomposer.translate.tables import Table, Unit
from bitcomposer.translate.vocab import Span


def _units():
    """Two games, three songs: game A's songs play "x" under (4,) mostly, game B's "y"."""
    out = []
    for song, game, seq in (("s1", "A", "xxxxy"), ("s2", "A", "xxxz"), ("s3", "B", "yyyy")):
        for i, o in enumerate(seq):
            out.append(Unit(song, game, o, {"meter": 4, "previous": seq[i - 1] if i else rhythm.START}))
    return out


class TableTests(unittest.TestCase):
    def test_a_song_votes_once_for_each_distinct_outcome(self):
        t = Table(("meter",)).fit(_units())
        self.assertEqual(t.votes[(4,)], {"x": 2, "y": 2, "z": 1})      # s1 played x four times: one vote
        self.assertEqual(t.songs[(4,)], 3)
        self.assertEqual(t.units[(4,)], 13)
        self.assertEqual(t.votes[()], t.votes[(4,)])                     # the coarser context counts the same here

    def test_probabilities_sum_to_one_over_known_outcomes_and_the_unseen_slot(self):
        t = Table(("meter", "game")).fit(_units())
        for ctx in ((4, "A"), (4, "B"), (4, "C"), (3, "A")):
            total = sum(t.p(o, ctx) for o in t.vocabulary) + t.p("never", ctx)
            self.assertAlmostEqual(total, 1.0, places=9, msg=str(ctx))

    def test_a_per_game_context_backs_off_to_the_shared_one(self):
        t = Table(("meter", tables.GAME)).fit(_units())
        self.assertGreater(t.p("x", (4, "A")), t.p("x", (4,)))          # game A plays x: its table leans to it
        self.assertLess(t.p("x", (4, "B")), t.p("x", (4,)))
        self.assertAlmostEqual(t.p("x", (4, "unknown game")), t.p("x", (4,)))   # a game never seen: the shared estimate
        self.assertGreater(t.p("never", (4, "B")), 0)                    # an outcome never seen keeps a little mass

    def test_witten_bell_weights(self):
        t = Table(()).fit(_units())
        # root: votes x 2, y 2, z 1 (n 5, t 3); below it an even share over 3 known + 1 unseen
        even = 1 / 4
        self.assertAlmostEqual(t.p("x", ()), (2 + 3 * even) / (5 + 3))
        self.assertAlmostEqual(t.p("never", ()), (0 + 3 * even) / (5 + 3))

    def test_score_is_mean_bits_and_a_fitting_context_scores_higher(self):
        us = _units()
        flat, by_game = Table(()).fit(us), Table((tables.GAME,)).fit(us)
        self.assertGreater(by_game.score(us), flat.score(us))
        self.assertAlmostEqual(flat.score(us), sum(math.log2(flat.p(u.outcome, ())) for u in us) / len(us))
        self.assertTrue(math.isnan(flat.score([])))

    def test_draws_follow_the_distribution_with_a_seed(self):
        t = Table((tables.GAME,)).fit(_units())
        rng = random.Random(7)
        drawn = [t.draw(("A",), rng) for _ in range(2000)]
        self.assertEqual(drawn, [t.draw(("A",), r) for r in [random.Random(7)] for _ in range(2000)])
        share = drawn.count("x") / len(drawn)
        self.assertAlmostEqual(share, t.p("x", ("A",)) / sum(t.p(o, ("A",)) for o in t.vocabulary), delta=0.05)
        self.assertIn("y", drawn)                                        # never the mode alone

    def test_half_is_phase_ones_split(self):
        self.assertEqual(tables.half("Final Fantasy VI"), tables.half("Final Fantasy VI"))
        self.assertEqual({tables.half(g) for g in ("Final Fantasy VI", "Chrono Trigger", "EarthBound", "Star Fox", "Plok")},
                         {tables.DEVELOPMENT, tables.HELD_OUT})

    def test_round_trip_through_json(self):
        t = Table(("meter", tables.GAME), "test").fit(_units())
        back = Table.from_json(json.loads(json.dumps(t.to_json())), "test")
        for ctx in ((4, "A"), (4, "B"), ()):
            for o in list(t.vocabulary) + ["never"]:
                self.assertAlmostEqual(back.p(o, ctx), t.p(o, ctx))
        self.assertEqual(back.songs[(4, "A")], 2)

    def test_shapes_and_compare_and_report(self):
        us = _units() + [Unit("s4", "Chrono Trigger", "y", {"meter": 4, "previous": "y"}),
                         Unit("s5", "EarthBound", "x", {"meter": 4, "previous": "x"})]
        shape_list = tables.shapes(("meter",), ("previous",))
        self.assertEqual(shape_list, [(), ("meter",), ("meter", "previous"),
                                      (tables.GAME,), ("meter", tables.GAME), ("meter", "previous", tables.GAME)])
        cs = tables.compare(us, shape_list, by="meter")
        self.assertEqual(len(cs), 6)
        self.assertTrue(all(cs[i].bits >= cs[i + 1].bits for i in range(len(cs) - 1)))
        text = tables.report(cs, columns=(4,))
        self.assertIn("(none)", text)
        self.assertIn("meter+previous", text)
        for c in cs:
            self.assertEqual(len(c.spread), 4)


class RhythmUnitTests(unittest.TestCase):
    def _song(self):
        # 4/4, sixteenth grid, three bars once through (numbers 0-2), one part of two bars at 0, a chord change in bar 1
        chords = [Span(0.0, 4.0, 0, "", 1.0), Span(4.0, 6.0, 7, "", 1.0), Span(6.0, 12.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0)], chords, bpm=100.0, sid="id", game="G",
                        numbers=[0, 1, 2], parts=[(0, 2)])
        s.notes["bass"] = [(0.0, 0.5, 36.0, "k"), (2.0, 0.5, 36.0, "k"), (4.0, 0.5, 36.0, "k"), (6.5, 0.25, 43.0, "k")]
        return s

    def test_part_weights_and_the_habits_carry_them(self):
        s = self._song()
        s.notes["melody"] = [(0.0, 1.0, 72.0, "m")]                          # one melody note against four of bass
        self.assertEqual(rhythm.part_weights(s), {"bass": "main", "melody": "half"})   # a fifth of the strikes: half, not minor
        hs = rhythm.habits(rhythm.bass_units([s]))
        self.assertEqual((hs[0].values["part"], hs[0].values["tempo"], hs[0].values["weight"]), ("bass", "medium", "main"))

    def test_units_carry_the_pattern_and_the_conditionings(self):
        us = rhythm.units([self._song()])
        self.assertEqual([u.outcome for u in us], ["0 2", "0 5/2", "-"])
        self.assertEqual([u.values["previous"] for u in us], [rhythm.START, "0 2", "0 5/2"])
        self.assertEqual([u.values["place"] for u in us], ["first", "last", "none"])
        self.assertEqual([u.values["chord"] for u in us], ["on", "inside", "same"])
        self.assertEqual(us[0].values["tempo"], "medium")
        self.assertEqual((us[0].song, us[0].game, us[0].values["part"], us[0].values["meter"]), ("id", "G", "bass", 4))

    def test_band_and_pattern(self):
        self.assertEqual([rhythm.band(b) for b in (60, 85, 129.9, 130, 200)], ["slow", "medium", "medium", "fast", "fast"])
        self.assertEqual(rhythm.pattern([Fraction(0), Fraction(1, 3), Fraction(3, 2)]), "0 1/3 3/2")
        self.assertEqual(rhythm.pattern([]), "-")

    def test_a_bar_of_another_length_breaks_the_chain(self):
        s = self._song()
        s.bars[1] = (4.0, 7.0)                     # a three-beat bar: left out, and the chain restarts after it
        us = rhythm.units([s])
        self.assertEqual([u.outcome for u in us], ["0 2", "-"])
        self.assertEqual(us[1].values["previous"], rhythm.START)


if __name__ == "__main__":
    unittest.main()


class VotesFloorSplitTests(unittest.TestCase):
    def test_share_votes_sum_to_one_a_song(self):
        t = Table(("meter",), votes=tables.SHARES).fit(_units())
        self.assertAlmostEqual(t.votes[(4,)]["x"], 4 / 5 + 3 / 4)       # s1: four of five bars; s2: three of four
        self.assertAlmostEqual(sum(t.votes[(4,)].values()), 3.0)         # three songs, one vote each
        self.assertEqual(t.songs[(4,)], 3)
        back = Table.from_json(t.to_json())
        self.assertEqual(back.by, tables.SHARES)

    def test_a_floor_model_gives_unseen_outcomes_their_likelihood_and_draws(self):
        class Floor:
            def p(self, outcome, values):
                return 0.5 if outcome == "never" else 0.1
            def draw(self, values, rng):
                return "floored"
        t = Table(("meter",), floor=Floor()).fit(_units())
        self.assertGreater(t.p("never", (4,)), Table(("meter",)).fit(_units()).p("never", (4,)))   # the floor lifts an unseen outcome
        rng = random.Random(1)
        self.assertIn("floored", {t.draw((9,), rng) for _ in range(50)})   # an unseen context draws from the floor
        root = (2 + 3 * 0.1) / (5 + 3)
        self.assertAlmostEqual(t.p("x", (4,), {}), (2 + 3 * root) / (5 + 3))

    def test_split_by_song_keeps_every_game_in_both_halves(self):
        us = [Unit(f"s{i}", "G", "x", {}) for i in range(40)]
        halves = {tables.half_of(u, tables.BY_SONG) for u in us}
        self.assertEqual(halves, {tables.DEVELOPMENT, tables.HELD_OUT})
        self.assertEqual({tables.half_of(u, tables.BY_GAME) for u in us}, {tables.half("G")})

    def test_cells_round_trip_and_the_bar_cells_floor(self):
        self.assertEqual(rhythm.cells("0 1/2 1 3/2 2 5/2 3 7/2", 4), ["0 1/2"] * 4)
        self.assertEqual(rhythm.cells("0 2 11/4", 4), ["0", "-", "0 3/4", "-"])
        self.assertEqual(rhythm.cells("-", 3), ["-", "-", "-"])
        for drawn in ("0 1/2 1 3/2 2 5/2 3 7/2", "0 2 11/4", "-", "1/3 2/3 1"):
            self.assertEqual(rhythm.pattern_of_cells(rhythm.cells(drawn, 4)), drawn)
        us = [Unit("s1", "G", "0 2", {"part": "bass", "meter": 4}), Unit("s2", "G", "0 1 2 3", {"part": "bass", "meter": 4})]
        floor = rhythm.BarCells(us)
        values = {"part": "bass", "meter": 4}
        self.assertGreater(floor.p("0 2", values), floor.p("1/3 1", values))       # a bar never seen whole still has mass
        self.assertGreater(floor.p("0 1 2", values), 0)
        drawn = floor.draw(values, random.Random(3))
        self.assertEqual(len(rhythm.cells(drawn, 4)), 4)
        t = Table(("part",), floor=floor).fit(us)
        self.assertGreater(t.p("0 1 2", ("bass",), values), 0)
        self.assertEqual(len(rhythm.cells(t.draw(("other",), random.Random(2), values), 4)), 4)


class DiscountTests(unittest.TestCase):
    def test_absolute_discounting_sums_to_one_and_keeps_a_common_outcome_more(self):
        us = _units() + [Unit(f"s{i}", "A", "x", {"meter": 4}) for i in range(10, 30)] + \
            [Unit(f"s{i}", "A", f"rare{i}", {"meter": 4}) for i in range(30, 50)]      # x in 22 songs, 20 one-song outcomes
        wb = Table(("meter",)).fit(us)
        ad = Table(("meter",), discount=0.75).fit(us)
        for t in (wb, ad):
            total = sum(t.p(o, (4,)) for o in t.vocabulary) + t.p("never", (4,))
            self.assertAlmostEqual(total, 1.0, places=9)
        self.assertGreater(ad.p("x", (4,)), wb.p("x", (4,)))
        self.assertLess(ad.p("rare30", (4,)), wb.p("rare30", (4,)))
        rng = random.Random(5)
        drawn = [ad.draw((4,), rng) for _ in range(1000)]
        self.assertAlmostEqual(drawn.count("x") / 1000, ad.p("x", (4,)) / sum(ad.p(o, (4,)) for o in ad.vocabulary), delta=0.05)
        back = Table.from_json(json.loads(json.dumps(ad.to_json())))
        self.assertAlmostEqual(back.p("x", (4,)), ad.p("x", (4,)))

    def test_the_floor_alone_is_compared_too(self):
        class Floor:
            def __init__(self, units):
                pass
            def p(self, outcome, values):
                return 0.25
            def draw(self, values, rng):
                return "x"
        us = _units() + [Unit("s4", "Chrono Trigger", "y", {"meter": 4}), Unit("s5", "EarthBound", "x", {"meter": 4})]
        cs = tables.compare(us, [(), ("meter",)], floor=Floor, discount=0.5)
        self.assertEqual({c.shape for c in cs}, {(), ("meter",), tables.FLOOR})
        self.assertAlmostEqual(next(c.bits for c in cs if c.shape == tables.FLOOR), -2.0)
        self.assertIn("floor", tables.report(cs))


class CoversTests(unittest.TestCase):
    def test_a_covered_level_is_neither_counted_nor_backed_off_to(self):
        class Floor:
            def __init__(self, units=None):
                pass
            def p(self, outcome, values):
                return 0.3 if outcome == "x" else 0.01
            def draw(self, values, rng):
                return "x"
        us = _units()
        t = Table(("meter", tables.GAME), floor=Floor(), covers=1).fit(us)
        self.assertNotIn((), t.votes)                                    # the pooled root is never counted
        self.assertIn((4,), t.votes)
        root_free = (t.votes[(4,)]["x"] + 3 * 0.3) / (5 + 3)             # (4,) straight onto the floor
        self.assertAlmostEqual(t.p("x", (4,)), root_free)
        self.assertAlmostEqual(t.p("x", (4, "A")), (t.votes[(4, "A")]["x"] + 3 * root_free) / (4 + 3))   # x 2, y 1, z 1 under game A
        self.assertAlmostEqual(t.p("x", (9,)), 0.3)                      # an unseen context: the floor alone
        self.assertEqual(Table.from_json(t.to_json()).covers, 0)        # a floor is not in the json: nothing covered
        self.assertEqual(tables.shapes(("part", "meter"), ("tempo",), game=False, covers=2),
                         [("part", "meter"), ("part", "meter", "tempo")])
        self.assertEqual(Table(("meter",), covers=1).covers, 0)          # no floor: nothing to cover


class ValueUnitTests(unittest.TestCase):
    def test_value_units(self):
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1])
        # a line: a held quarter on the one, a detached eighth on the two, a note tied over the bar line, the last note (no next)
        s.notes["melody"] = [(0.0, 0.9, 60.0, "k"), (1.0, 0.2, 62.0, "k"), (1.5, 2.6, 64.0, "k"), (4.25, 1.0, 65.0, "k")]
        us = rhythm.value_units([s])
        self.assertEqual([u.outcome for u in us], ["held", "detached", "held"])
        self.assertEqual([u.values["value"] for u in us], ["1", "1/2", "11/4"])
        self.assertEqual([u.values["place"] for u in us], ["beat", "beat", "eighth"])
        self.assertEqual([u.values["beat"] for u in us], [0, 1, 1])
        self.assertEqual([u.values["previous"] for u in us], [rhythm.START, "held", "detached"])
        self.assertEqual(us[0].values["part"], "melody")


class BassUnitTests(unittest.TestCase):
    def test_cells_keep_marks(self):
        self.assertEqual(rhythm.cells("0:R 1/2:r 2:5 11/4:?", 4), ["0:R 1/2:r", "-", "0:5 3/4:?", "-"])
        self.assertEqual(rhythm.pattern_of_cells(rhythm.cells("0:R 1/2:r 2:5 11/4:?", 4)), "0:R 1/2:r 2:5 11/4:?")

    def test_bass_units(self):
        chords = [Span(0.0, 4.0, 0, "", 1.0), Span(4.0, 8.0, 7, "m", 1.0)]      # C major, then G minor
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=140.0, sid="id", game="G", numbers=[0, 1])
        s.notes["bass"] = [(0.0, 0.5, 36.0, "k"), (1.0, 0.5, 48.0, "k"), (2.0, 0.5, 43.0, "k"),   # C, C up an octave, G
                           (4.0, 0.5, 43.0, "k"), (5.0, 0.5, 46.0, "k")]                           # G, Bb
        us = rhythm.bass_units([s])
        self.assertEqual([u.outcome for u in us], ["0:R 1:r 2:5", "0:R 1:3"])
        self.assertEqual([u.values["shape"] for u in us], ["major", "m"])
        self.assertEqual([u.values["next"] for u in us], ["on", "same"])
        self.assertEqual([u.values["previous"] for u in us], [rhythm.START, "0:R 1:r 2:5"])
        self.assertEqual(us[0].values["tempo"], "fast")

    def test_habits(self):
        self.assertEqual([rhythm.habit_of(x) for x in (0.0, 0.33, 0.5, 0.67, 1.0)], ["detached", "detached", "mixed", "held", "held"])
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1])
        s.notes["melody"] = [(0.0, 0.9, 60.0, "k"), (1.0, 0.9, 62.0, "k"), (2.0, 0.2, 64.0, "k"), (3.0, 1.0, 65.0, "k")]
        us = rhythm.value_units([s])
        self.assertEqual({u.values["habit"] for u in us}, {"held"})
        hs = rhythm.habit_units([s])
        self.assertEqual([(h.song, h.outcome, h.values["part"]) for h in hs], [("id", "held", "melody")])


class StyleHabitTests(unittest.TestCase):
    def test_rhythm_and_bass_habits(self):
        chords = [Span(0.0, 16.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0), (12.0, 16.0)], chords, bpm=100.0, sid="id",
                        game="G", numbers=[0, 1, 2, 3])
        s.notes["bass"] = [(b + x, 0.4, 36.0 if x < 2 else 48.0, "k") for b in (0.0, 4.0, 8.0, 12.0) for x in (0.0, 1.0, 2.0, 3.0)]
        us = rhythm.bass_units([s])
        self.assertEqual({u.outcome for u in us}, {"0:R 1:R 2:r 3:r"})
        self.assertEqual({u.values["habit"] for u in us}, {"medium roots octaves"})
        rs = rhythm.units([s])
        self.assertEqual({u.values["habit"] for u in rs}, {"medium repeating"})
        self.assertEqual([(h.outcome, h.values["part"]) for h in rhythm.bass_habit_units([s])], [("medium roots octaves", "bass")])
        self.assertEqual([(h.outcome, h.values["part"]) for h in rhythm.rhythm_habit_units([s])], [("medium repeating", "bass")])
        self.assertEqual(rhythm.habit_of(1.0, rhythm.DENSITIES), "sparse")
        self.assertEqual(rhythm.habit_of(7.0, rhythm.DENSITIES), "dense")


class DrumUnitTests(unittest.TestCase):
    def test_drum_units(self):
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1],
                        parts=[(0, 2)], pieces={"k": "kick", "s": "snare", "h": "hat", "x": "none"})
        s.notes["drums"] = [(0.0, 0.1, float("nan"), "k"), (0.0, 0.1, float("nan"), "h"), (1.0, 0.1, float("nan"), "s"),
                            (2.0, 0.1, float("nan"), "k"), (3.0, 0.1, float("nan"), "s"), (3.5, 0.1, float("nan"), "x"),
                            (4.0, 0.1, float("nan"), "k"), (5.0, 0.1, float("nan"), "s")]
        us = rhythm.drum_units([s])
        self.assertEqual([u.outcome for u in us], ["0:K 0:h 1:S 2:K 3:S 7/2:o", "0:K 1:S"])
        self.assertEqual([u.values["place"] for u in us], ["first", "last"])
        self.assertEqual({u.values["kit"] for u in us}, {"KSho"})
        self.assertEqual(us[1].values["previous"], us[0].outcome)
        self.assertEqual(rhythm.cells(us[0].outcome, 4), ["0:K 0:h", "0:S", "0:K", "0:S 1/2:o"])
        self.assertEqual([h.outcome for h in rhythm.drum_habit_units([s])], ["medium varied"])


class CacheTests(unittest.TestCase):
    def _units(self):
        out = []
        for song, seq in (("s1", "xxxyxxzx"), ("s2", "yyyy"), ("s3", "xzxzxz")):
            for i, o in enumerate(seq):
                out.append(Unit(song, "G", o, {"part": "bass", "habit": "h"}))
        return out

    def test_recall_units(self):
        rs = tables.recall_units(self._units())
        self.assertEqual([r.outcome for r in rs if r.song == "s1"], ["new", "same", "same", "new", "earlier", "same", "new", "earlier"])
        self.assertEqual([r.outcome for r in rs if r.song == "s3"], ["new", "new", "earlier", "earlier", "earlier", "earlier"])
        self.assertEqual(rs[0].values, {"part": "bass", "habit": "h"})

    def test_the_mixture_is_a_distribution_and_scores_a_loyal_song_higher(self):
        us = self._units()
        m = tables.Cache.fit(us, ("part",))
        unit = Unit("t", "G", "x", {"part": "bass", "habit": "h"})
        for previous, cache in ((None, Counter()), ("x", Counter(x=3)), ("y", Counter(x=2, y=1, z=1))):
            total = sum(m.p(Unit("t", "G", o, unit.values), previous, cache) for o in list(m.table.vocabulary) + ["never"])
            self.assertAlmostEqual(total, 1.0, places=9, msg=str((previous, cache)))
        loyal = [Unit("t", "G", o, unit.values) for o in "xxxxxxxx"]
        fickle = [Unit("t", "G", o, unit.values) for o in "xyzxyzxy"]
        self.assertGreater(m.score(loyal), m.table.score(loyal))
        self.assertGreater(m.score(loyal), m.score(fickle))
        self.assertTrue(math.isnan(m.score([])))

    def test_draws_and_the_comparison(self):
        us = self._units()
        m = tables.Cache.fit(us, ("part",))
        unit = Unit("t", "G", "x", {"part": "bass", "habit": "h"})
        rng = random.Random(2)
        self.assertEqual(m.draw(unit, None, Counter(), rng, keep=lambda o: o == "z"), "z")   # a new draw kept only when z
        drawn = [m.draw(unit, "x", Counter(x=5, y=1), random.Random(i)) for i in range(200)]
        self.assertGreater(drawn.count("x") / 200, 0.3)                      # loyal more often than the table alone would be
        cs = tables.compare(us + [Unit("s4", "Chrono Trigger", "x", {"part": "bass", "habit": "h"})] * 3, [("part",)], cache=True)
        self.assertEqual({c.shape for c in cs}, {("part",), ("part", tables.CACHE)})
        self.assertIn("part+cache", tables.report(cs))


class VoicingUnitTests(unittest.TestCase):
    def test_voicing_and_width_units(self):
        chords = [Span(0.0, 4.0, 0, "", 1.0), Span(4.0, 8.0, 7, "m", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1])
        s.notes["bass"] = [(0.0, 4.0, 36.0, "k"), (4.0, 4.0, 43.0, "k")]                       # C under C; G under Gm
        s.notes["harmony"] = [(0.0, 4.0, 64.0, "k"), (0.0, 4.0, 67.0, "k"), (4.0, 4.0, 70.0, "k"), (4.0, 4.0, 74.0, "k")]   # E G; Bb D
        s.notes["accompaniment"] = [(0.0, 4.0, 48.0, "k"), (4.0, 4.0, 55.0, "k")]                # C; G
        us = rhythm.voicing_units([s])
        by = {(u.values["part"], u.values["shape"]): u for u in us}
        self.assertEqual(by[("harmony", "major")].outcome, "3 5")
        self.assertEqual(by[("harmony", "m")].outcome, "3 5")
        self.assertEqual(by[("accompaniment", "major")].outcome, "R")
        self.assertEqual(by[("harmony", "m")].values["previous"], "3 5")
        self.assertEqual(by[("harmony", "major")].values["bass"], "R")
        self.assertEqual(by[("harmony", "major")].values["width"], "wide")            # 48 to 67: 19 semitones
        self.assertIn(by[("harmony", "major")].values["habit"], ("thin", "full", "rich"))
        ws = rhythm.width_units([s])
        self.assertEqual([w.outcome for w in ws], ["3:wide", "3:wide"])
        self.assertEqual(ws[0].values["parts"], "ha")
        self.assertEqual(ws[1].values["previous"], "3:wide")
        self.assertEqual([rhythm.width_of(x) for x in (0, 7, 8, 14, 15)], ["close", "close", "open", "open", "wide"])


class HarmonyUnitTests(unittest.TestCase):
    def _song(self, tonic=0):
        # C major, 4/4, six bars once through, two parts (0-3, 4-5), loop at bar 0:
        # | I | IV | V | I | vi (two beats) I | I |
        chords = [Span(0.0, 4.0, 0, "", 1.0), Span(4.0, 8.0, 5, "", 1.0), Span(8.0, 12.0, 7, "", 1.0),
                  Span(12.0, 16.0, 0, "", 1.0), Span(16.0, 18.0, 9, "m", 1.0), Span(18.0, 24.0, 0, "", 1.0)]
        return rhythm.Song("t", 4, 4, [(4.0 * k, 4.0 * k + 4.0) for k in range(6)], chords, bpm=100.0, sid="id",
                           game="G", numbers=list(range(6)), parts=[(0, 4, None), (4, 2, None)],
                           tonic=tonic, mode="major", loop_bar=0)

    def test_the_tonic_gate(self):
        self.assertTrue(rhythm.tonic_sure(self._song()))
        self.assertFalse(rhythm.tonic_sure(self._song(tonic=7)))        # G is played four beats of twenty-four
        self.assertEqual(rhythm.chord_units([self._song(tonic=7)]), [])
        self.assertEqual([u.outcome for u in rhythm.chord_units([self._song(tonic=7)], sure_only=False)][:2], ["IV", "bVII"])

    def test_chord_units(self):
        us = rhythm.chord_units([self._song()])
        self.assertEqual([u.outcome for u in us], ["I", "IV", "V", "I", "vi", "I"])   # bar 4: a tie, the first chord
        self.assertEqual([u.values["previous"] for u in us], [rhythm.START, "I", "IV", "V", rhythm.START, "vi"])
        self.assertEqual([u.values["before"] for u in us], [rhythm.START, rhythm.START, "I", "IV", rhythm.START, rhythm.START])
        self.assertEqual([u.values["place"] for u in us], ["first", "middle", "middle", "last", "first", "last"])
        self.assertEqual([u.values["form"] for u in us], ["first"] * 4 + ["last"] * 2)
        self.assertEqual((us[0].values["habit"], us[0].values["motion"]), ("several", "moving"))
        self.assertEqual((us[0].values["part"], us[0].values["mode"], us[0].values["meter"], us[0].values["tempo"]),
                         ("harmony", "major", 4, "medium"))
        s = self._song()
        s.parts = [(0, 4, None), (4, 2, 0)]                              # the second part repeats the first: left out
        self.assertEqual(len(rhythm.chord_units([s])), 4)
        ds = rhythm.degree_units([self._song()])
        self.assertEqual([u.outcome for u in ds], ["I", "IV", "V", "I", "VI", "I"])
        self.assertEqual([u.values["previous"] for u in ds][:3], [rhythm.START, "I", "IV"])
        ss = rhythm.shape_units([self._song()])
        self.assertEqual([u.outcome for u in ss], ["major"] * 4 + ["m", "major"])
        self.assertEqual([u.values["degree"] for u in ss], ["I", "IV", "V", "I", "VI", "I"])

    def test_change_units(self):
        us = rhythm.change_units([self._song()])
        self.assertEqual([u.outcome for u in us], ["0", "0", "0", "0", "0 2", "none"])
        self.assertEqual([u.values["previous"] for u in us], [rhythm.START, "0", "0", "0", rhythm.START, "0 2"])
        self.assertEqual(us[0].values["habit"], "moving")
        self.assertEqual(len(rhythm.change_units([self._song(tonic=7)])), 6)   # every song counts

    def test_cadence_and_loop_units(self):
        us = rhythm.cadence_units([self._song()])
        self.assertEqual([u.outcome for u in us], ["V -> I", "another -> I"])
        self.assertEqual([u.values["length"] for u in us], ["2 to 4 chords", "2 to 4 chords"])
        self.assertEqual([u.values["form"] for u in us], ["first", "last"])
        ls = rhythm.loop_units([self._song()])
        self.assertEqual((ls[0].outcome, ls[0].values["last"], ls[0].values["mode"]), ("I", "I", "major"))
        self.assertEqual(rhythm.loop_units([self._song(tonic=7)]), [])


class FormUnitTests(unittest.TestCase):
    def _song(self):
        s = rhythm.Song("t", 4, 4, [(4.0 * k, 4.0 * k + 4.0) for k in range(24)], [], bpm=100.0, sid="id", game="G",
                        numbers=list(range(24)))
        s.parts = [(0, 4, None, "A"), (4, 4, None, "B"), (8, 4, 1, "B"), (12, 8, None, "C"), (20, 4, 1, "B")]
        s.sections = [(0, 4, None, "A"), (4, 8, None, "B"), (12, 8, None, "C"), (20, 4, 1, "B")]
        return s

    def test_form_units(self):
        us = rhythm.form_units([self._song()])
        self.assertEqual([u.outcome for u in us], ["new", "new", "again", "new", "back"])
        self.assertEqual([u.values["letters"] for u in us], [0, 1, 2, 2, 3])
        self.assertEqual([u.values["previous"] for u in us], [rhythm.START, "new", "new", "again", "new"])
        self.assertEqual((us[0].values["index"], us[4].values["index"], us[0].values["habit"]), (1, 5, "several"))
        self.assertEqual([u.outcome for u in rhythm.form_units([self._song()], level="section")], ["new", "new", "new", "back"])

    def test_length_and_letters_units(self):
        us = rhythm.length_units([self._song()])
        self.assertEqual([u.outcome for u in us], ["4", "4", "4", "8", "4"])
        self.assertEqual([u.values["kind"] for u in us], ["new", "new", "again", "new", "back"])
        self.assertEqual([u.values["previous"] for u in us][:2], [rhythm.START, "4"])
        self.assertEqual(us[0].values["habit"], "short")
        ls = rhythm.letters_units([self._song()])
        self.assertEqual((ls[0].outcome, ls[0].values["parts"]), ("A B B C B", "several"))
        self.assertEqual(rhythm.letters_units([self._song()], level="section")[0].outcome, "A B C B")
        self.assertEqual(rhythm.form_units([rhythm.Song("t", 4, 4, [], [])]), [])


class PhraseUnitTests(unittest.TestCase):
    def _song(self):
        from bitcomposer.translate import phrases
        # C major, 4/4, two parts of four bars; a rising phrase, then the same phrase moved up a fifth
        bars = [(4.0 * k, 4.0 * k + 4.0) for k in range(8)]
        notes = [(4.0 * k + 1.0 * i, 1.0, 60 + 2 * i + 12 * (k // 4) * 0) for k in range(4) for i in range(4)]
        rise = [(t, 1.0, 60 + i) for i, t in enumerate(range(0, 16))]            # 16 beats climbing a semitone a beat
        again = [(t + 16.0, l, m + 7) for t, l, m in rise]
        s = phrases.Song("t", 0, "major", 4, bars, [], notes={"melody": rise + again},
                         parts=[phrases.Part("A", 0, 4), phrases.Part("B", 4, 4)], loop_bar=0, sid="id", game="G")
        return s

    def test_phrase_units(self):
        from bitcomposer.translate import phrases
        cs = phrases.contour_units([self._song()], length=4)
        self.assertEqual([u.outcome for u in cs], ["rising", "rising"])
        self.assertEqual([u.values["relation"] for u in cs], ["first", "moved up"])
        self.assertEqual([u.values["previous"] for u in cs], [rhythm.START, "rising"])
        self.assertEqual([u.values["form"] for u in cs], ["first", "last"])
        self.assertEqual((cs[0].values["place"], cs[0].values["ends_part"], cs[0].values["last"], cs[1].values["last"]),
                         ("only", "yes", "no", "yes"))
        self.assertEqual(cs[0].values["habit"], "mixed")                       # one of two phrases moves the one before
        rs = phrases.relation_units([self._song()], length=4)
        self.assertEqual([u.outcome for u in rs], ["moved up"])              # the song's first phrase is no relation
        self.assertEqual((rs[0].values["contour"], rs[0].values["previous"]), ("rising", rhythm.START))
        ms = phrases.move_units([self._song()], length=4)
        self.assertEqual(len(ms), 30)                                        # two phrases of sixteen notes: fifteen moves each
        self.assertTrue(all(u.outcome == "+1" for u in ms))                  # a semitone a beat, climbing
        self.assertEqual((ms[0].values["previous"], ms[1].values["previous"]), (rhythm.START, "+1"))
        self.assertEqual(ms[0].values["place"], "strong")
        self.assertEqual((ms[0].values["contour"], ms[0].values["quarter"], ms[14].values["quarter"]), ("rising", "first quarter", "last"))
        self.assertEqual((ms[0].values["habit"], ms[0].values["repeats"]), ("stepwise", "rare"))
        self.assertEqual(ms[0].values["tone"], "no chord")                   # the fixture has no chords
        es = phrases.ending_units([self._song()], length=2)
        self.assertEqual(len(es), 4)
        self.assertEqual([u.values["place"] for u in es], ["first", "last", "first", "last"])
        self.assertEqual(es[0].values["part"], "melody")


class ArrangementUnitTests(unittest.TestCase):
    def _song(self):
        # 4/4, six bars, two parts (0-3, 4-5): the bass plays bars 0-3 and holds a note from bar 3 into bar 4,
        # the melody plays bars 1-5, the drums bars 0-5 but rest in bar 2 (a break)
        s = rhythm.Song("t", 4, 4, [(4.0 * k, 4.0 * k + 4.0) for k in range(6)], [], bpm=100.0, sid="id", game="G",
                        numbers=list(range(6)), parts=[(0, 4, None, "A"), (4, 2, None, "B")])
        s.notes["bass"] = [(4.0 * k, 1.0, 36.0, "b") for k in range(3)] + [(12.0, 6.0, 36.0, "b")]
        s.notes["melody"] = [(4.0 * k + 0.5, 0.5, 72.0, "m") for k in range(1, 6)]
        s.notes["drums"] = [(4.0 * k, 0.25, float("nan"), "k") for k in (0, 1, 3, 4, 5)]
        s.voices = [(0, "melody", None, {}), (1, "bass", None, {}), (2, "drums", None, {}),
                    (3, "double", 0, {"echo_ms": 120}), (4, "double", 1, {"delay": 0.0})]
        return s

    def test_sounding_bars(self):
        s = self._song()
        self.assertEqual(rhythm.sounding_bars(s, "bass"), {0, 1, 2, 3, 4})      # held a whole beat into bar 4
        self.assertEqual(rhythm.sounding_bars(s, "melody"), {1, 2, 3, 4, 5})
        self.assertEqual(rhythm.sounding_bars(s, "drums"), {0, 1, 3, 4, 5})

    def test_texture_and_presence_units(self):
        ts = rhythm.texture_units([self._song()])
        self.assertEqual([u.outcome for u in ts], ["bass drums", "bass drums melody", "bass melody", "bass drums melody",
                                                   "bass drums melody", "drums melody"])
        self.assertEqual([u.values["previous"] for u in ts][:2], [rhythm.START, "bass drums"])
        self.assertEqual(ts[4].values["previous"], rhythm.START)                 # bar 4 opens the second part
        self.assertEqual((ts[0].values["form"], ts[5].values["form"], ts[0].values["habit"]), ("first", "last", "bass drums melody"))
        ps = rhythm.presence_units([self._song()])
        drums = [u for u in ps if u.values["part"] == "drums"]
        self.assertEqual([u.outcome for u in drums], ["plays", "plays", "rests", "plays", "plays", "plays"])
        self.assertEqual([u.values["others"] for u in drums], ["1", "2", "2", "2", "2", "1"])
        self.assertEqual([u.values["previous"] for u in drums], [rhythm.START, "plays", "plays", "rests", rhythm.START, "plays"])
        self.assertEqual(drums[0].values["habit"], "mostly")
        self.assertEqual([u.values["place"] for u in drums], ["first", "middle", "middle", "last", "first", "last"])

    def test_song_level_units(self):
        s = self._song()
        self.assertEqual(rhythm.band_units([s])[0].outcome, "bass drums melody")
        self.assertEqual((rhythm.voices_units([s])[0].outcome, rhythm.voices_units([s])[0].values["band"]), ("5", 3))
        self.assertEqual(rhythm.double_units([s])[0].outcome, "bass unison / melody echo")
        ps = {u.values["part"]: u.outcome for u in rhythm.parts_units([s])}
        self.assertEqual(ps, {"drums": "yes", "bass": "yes", "melody": "yes", "counter": "no", "chordal": "no", "double": "yes"})
        s.voices = s.voices[:3]
        self.assertEqual(rhythm.double_units([s])[0].outcome, "none")
        self.assertEqual(rhythm.layer_units([s]), [])
        s.bass_voices = {1: [(4.0 * k, 3.0, 36.0, "b") for k in range(8)], 5: [(4.0 * k, 0.5, 48.0, "p") for k in range(8)]}
        self.assertEqual(rhythm.layer_units([s])[0].outcome, "doubling")


class PackTableTests(unittest.TestCase):
    def _bass_units(self):
        songs = [RhythmUnitTests._song(self)]
        s2 = RhythmUnitTests._song(self)
        s2.sid, s2.game = "id2", "H"
        s2.notes["bass"] = [(0.0, 0.5, 36.0, "k"), (1.0, 0.5, 36.0, "k"), (4.0, 0.5, 36.0, "k"), (5.0, 0.25, 43.0, "k")]
        return rhythm.bass_units(songs + [s2])

    def test_a_table_on_the_cell_floor_round_trips_with_its_floor(self):
        us = self._bass_units()
        t = Table(("part", "meter", "previous"), "bass", votes=tables.SHARES, floor=rhythm.BarCells(us), discount=0.75,
                  covers=2).fit(us)
        back = Table.from_json(json.loads(json.dumps(t.to_json())), "bass")
        self.assertIsInstance(back.floor, rhythm.BarCells)
        self.assertEqual(back.covers, 2)
        for u in us:
            self.assertAlmostEqual(back.p(u.outcome, back.context(u), u.values), t.p(u.outcome, t.context(u), u.values))
        self.assertAlmostEqual(back.p("0 1/2 1 3/2 2", ("bass", 4, rhythm.START), us[0].values),   # a bar never counted: the floor's
                               t.p("0 1/2 1 3/2 2", ("bass", 4, rhythm.START), us[0].values))

    def test_a_mixture_draws_new_as_new_to_the_song(self):
        """A "new" draw is an outcome the song has not played, as recall_units counts it; the same and earlier draws as before."""
        units = [tables.Unit("s", "g", o, {"part": "p", "previous": p}) for o, p in (("a", "start"), ("a", "a"), ("b", "a"), ("c", "b"), ("a", "c"))]
        m = tables.Cache.fit(units, ("part", "previous"), name="x", votes=tables.SHARES)
        played = Counter({"a": 3, "b": 1})
        draws = Counter(m.draw(tables.Unit("s", "g", "", {"part": "p", "previous": "b"}), "b", played, random.Random(i)) for i in range(300))
        self.assertTrue(draws["b"] > 0 and draws["a"] > 0 and draws["c"] > 0, draws)
        shares = m.shares(tables.Unit("s", "g", "", {"part": "p", "previous": "b"}), "b", played)
        self.assertAlmostEqual(draws["c"] / 300, shares[2], delta=0.08)     # the new draws are c, the one outcome not yet played
        self.assertEqual(m.draw_new(tables.Unit("s", "g", "", {"part": "p", "previous": "b"}), played, random.Random(3)), "c")
        self.assertIn(m.draw_new(tables.Unit("s", "g", "", {"part": "p", "previous": "b"}), Counter({"a": 1, "b": 1, "c": 1}), random.Random(3)), ("a", "b", "c"))

    def test_a_mixture_round_trips(self):
        us = self._bass_units()
        m = tables.Cache.fit(us, ("part", "meter", "habit", "previous"), name="bass", votes=tables.SHARES,
                             floor=rhythm.BarCells(us), discount=0.75, covers=2)
        back = tables.Cache.from_json(json.loads(json.dumps(m.to_json())), "bass")
        self.assertAlmostEqual(back.score(us), m.score(us))
        rng1, rng2 = random.Random(3), random.Random(3)
        self.assertEqual(tables.simulate_cache(back, us, rng1), tables.simulate_cache(m, us, rng2))

    def test_kept_tables_fit_and_read_back(self):
        from bitcomposer.translate import packtables
        us = self._bass_units()
        entry = packtables.fit("bass", us)
        self.assertEqual((entry["mixture"], entry["shape"], entry["units"], entry["songs"]), (True, list(packtables.FIGURE), len(us), 2))
        models = packtables.read(json.loads(json.dumps({"tables": {"bass": entry}})))
        self.assertIsInstance(models["bass"], tables.Cache)
        self.assertIsInstance(models["bass"].table.floor, rhythm.BarCells)
        plain = packtables.fit("bass_habits", rhythm.habits(us))
        self.assertFalse(plain["mixture"])
        self.assertIsInstance(packtables.read({"tables": {"bass_habits": plain}})["bass_habits"], Table)
        self.assertIsNone(packtables.fit("layers", []))
        for name, (module, builder, *_) in packtables.KEPT.items():
            self.assertTrue(hasattr(packtables.MODULES[module], builder), name)


class ReferenceSetTests(unittest.TestCase):
    def test_phrases_as_rhythm_and_intervals_and_their_lookup(self):
        from bitcomposer.translate import reference
        s = PhraseUnitTests._song(self)
        rows = reference.phrases_of([s], 4)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["rhythm"], [12 * i for i in range(16)])
        self.assertEqual(rows[0]["intervals"], [1] * 15)
        self.assertEqual((rows[0]["bar"], rows[1]["bar"], rows[0]["song"]), (0, 4, "id"))
        idx = reference.Index({"phrases": rows})
        self.assertEqual(len(idx.matches(rows[0]["rhythm"], rows[0]["intervals"])), 2)          # the same tune twice
        self.assertEqual(len(idx.matches(rows[0]["rhythm"], [2] * 15, how="rhythm")), 2)
        self.assertEqual(idx.matches(rows[0]["rhythm"], [2] * 15), [])
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "ref.json")
            data = {"phrases": rows}
            json.dump(data, open(out, "w"))
            self.assertEqual(len(reference.Index(reference.load(out)).rows), 2)
