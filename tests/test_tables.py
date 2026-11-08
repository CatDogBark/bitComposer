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
        s.voice_notes = {1: ("bass", [(4.0 * k, 3.0, 36.0, "b") for k in range(8)]), 5: ("bass", [(4.0 * k, 0.5, 48.0, "p") for k in range(8)])}
        self.assertEqual(rhythm.layer_units([s])[0].outcome, "doubling +12")      # the second bass voice an octave over the line, struck with it


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


class BalanceLevelTests(unittest.TestCase):
    def test_a_kit_s_unread_level_never_reaches_the_token(self):
        """A drum voice's levels the import could not read are NaN. A median over them was NaN, three FFVI tokens carried
        a "nan" drums level, and a written song played its kit at full (2026-10-30). The token leaves the field empty,
        so the plan's levels draw stands in, and the loudest part is the loudest of the levels read."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1],
                        parts=[(0, 2)], pieces={"k": "kick", "s": "snare", "h": "hat", "x": "none"})
        s.notes["melody"] = [(0.0, 1.0, 72, "sa"), (1.0, 1.0, 74, "sa"), (2.0, 1.0, 76, "sa"), (3.0, 1.0, 77, "sa"),
                             (4.0, 2.0, 79, "sa"), (6.0, 2.0, 76, "sa")]
        s.notes["drums"] = [(0.0, 0.1, float("nan"), "k"), (1.0, 0.1, float("nan"), "s"), (2.0, 0.1, float("nan"), "k"),
                            (3.0, 0.1, float("nan"), "s"), (4.0, 0.1, float("nan"), "k"), (5.0, 0.1, float("nan"), "s")]
        s.voice_notes = {1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        s.voice_levels = {1: 0.5, 2: float("nan")}
        s.levels = {"melody": 0.5, "drums": float("nan")}
        token = rhythm.balance_units([s])[0].outcome
        self.assertNotIn("nan", token)
        self.assertIn("melody=main::1.0:1:1.0", token)

    def test_the_kits_pieces_carry_the_note_they_are_struck_at(self):
        """Round 75: a piece's most struck note follows its level in the kit field (`o=o@0.40@62`; `o=o@@62` without a
        level, the old form where the reading heard no note). FFVI's "other" pieces are tonal samples in ten tokens of
        eleven, and the written kit had hammered them at the kit's one note."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1],
                        parts=[(0, 2)], pieces={"k": "kick", "o": "other"})
        s.notes["melody"] = [(0.0, 1.0, 72, "sa"), (1.0, 1.0, 74, "sa"), (2.0, 1.0, 76, "sa"), (3.0, 1.0, 77, "sa"),
                             (4.0, 2.0, 79, "sa"), (6.0, 2.0, 76, "sa")]
        s.notes["drums"] = [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)] + [(x, 0.1, 62.0, "o") for x in (0.0, 4.0)]
        s.voice_notes = {1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        s.voice_levels = {1: 0.5, 2: 0.1}
        s.levels = {"melody": 0.5, "drums": 0.1}
        s.kit_levels = {"k": 0.8, "o": 0.2}
        s.kit_pitches, s.kit_rates = {"o": 62}, {"k": 48}                           # round 78: a drum piece's note slot is the chip's rate, "r48"
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@r48@@m,o=o@0.40@62@@s")      # since round 81 the strike class ends the slot
        self.assertEqual(rhythm.kit_token(s), "K=k@@r48@@m,o=o@@62@@s")                 # no top, no level: the note still
        del s.kit_rates["k"]
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@@@m,o=o@0.40@62@@s")       # a piece without a note keeps the old form
        self.assertIn("drums=:::Ko:0.2:::K=k@1.60@@@m,o=o@0.40@62@@s", rhythm.balance_units([s])[0].outcome)   # the channels field since round 87
        s.kit_holds = {"k": 0.5, "o": 6.95}                                        # round 77: each piece's hold follows the note's slot
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@@0.50@m,o=o@0.40@62@6.95@s")   # (the kick has no note: its slot kept empty)
        del s.kit_pitches["o"]
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@@0.50@m,o=o@0.40@@6.95@s")
        s.kit_levels = {}
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@@@0.50@m,o=o@@@6.95@s")
        # round 79: with a key, a tonal piece's note is a degree of it (scale steps from the tonic's fourth-octave note, 7 an
        # octave; semitones with a c where the note is off the scale), a drum piece the game tunes carries a t on its rate,
        # and the balance token carries the key before the top
        s.kit_levels, s.kit_holds = {"k": 0.8, "o": 0.2}, {}
        s.kit_pitches, s.kit_rates = {"o": 62}, {"k": 48}
        s.tonic, s.mode = 0, "major"
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@r48@@m,o=o@0.40@d1@@s")             # D4 is one step above C4 in C major
        self.assertEqual(rhythm.kit_token(s, 0.5, tuned=frozenset({"k"})), "K=k@1.60@r48t@@m,o=o@0.40@d1@@s")
        s.kit_pitches["o"] = 75                                                            # D#5: off C major, 15 semitones above C4
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@r48@@m,o=o@0.40@c15@@s")
        s.tonic, s.mode = 9, "minor"                                                       # A minor: D#5 off it too, 6 above A4
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@r48@@m,o=o@0.40@c6@@s")
        s.kit_pitches["o"] = 76                                                            # E5 in A minor: four steps above A4, a fifth
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@r48@@m,o=o@0.40@d4@@s")
        self.assertEqual(rhythm.kit_degree(s, 69), "d0"); self.assertEqual(rhythm.kit_degree(s, 57), "d-7")
        token = rhythm.balance_units([s])[0].outcome.split()
        self.assertIn("key=9:minor", token)
        self.assertLess(token.index("key=9:minor"), token.index("tempo=medium"))
        # a sample the game strikes at another rate in another song is tuned; one it strikes at one rate in most songs is a sound
        s2 = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id2", game="G", numbers=[0, 1], parts=[(0, 2)], pieces={"k": "kick"})
        s2.notes["drums"] = s.notes["drums"]; s2.voice_notes = {2: ("drums", s2.notes["drums"])}
        s2.kit_rates = {"k": 52}
        self.assertEqual(rhythm.tuned_samples([s, s2]), frozenset({"k"}))
        s2.kit_rates = {"k": 48}
        self.assertEqual(rhythm.tuned_samples([s, s2]), frozenset())
        s3 = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id3", game="G", numbers=[0, 1], parts=[(0, 2)], pieces={"k": "kick"})
        s3.notes["drums"] = s.notes["drums"]; s3.voice_notes = {2: ("drums", s3.notes["drums"])}; s3.kit_rates = {"k": 36}
        self.assertEqual(rhythm.tuned_samples([s, s2, s3]), frozenset())                    # one outlier in three: the same rate holds two

    def test_the_kits_slot_takes_the_sample_the_kit_leans_on(self):
        """Round 80: a piece letter struck on two samples takes the loudest of those with a fifth of its hits or more, not the
        most struck (Battle Theme's rattle had taken the snare slot from the backbeat snare); the most struck where no level
        is known or where the two are within a decibel; a sample under the fifth is not in the running however loud. Since
        round 99 the other sample rides the token as the slot's second (after a "+", with its share of the letter's hits)
        where it has eight hits or more, and the slot's class counts both."""
        from collections import Counter
        counts = Counter({("S", "rattle"): 354, ("S", "backbeat"): 100, ("K", "kick"): 197, ("S", "accent"): 3})
        self.assertEqual(rhythm.kit_slot_samples(counts, {"rattle": 0.18, "backbeat": 0.46, "kick": 0.46, "accent": 0.9}), {"S": "backbeat", "K": "kick"})
        self.assertEqual(rhythm.kit_slot_samples(counts, {}), {"S": "rattle", "K": "kick"})
        self.assertEqual(rhythm.kit_slot_samples(counts, {"rattle": 0.18}), {"S": "rattle", "K": "kick"})   # the only level known is the rattle's
        self.assertEqual(rhythm.kit_slot_samples(counts, {"rattle": 0.300, "backbeat": 0.310}), {"S": "rattle", "K": "kick"})   # as loud: the most struck
        self.assertEqual(rhythm.kit_slot_samples(counts, {"rattle": 0.300, "backbeat": 0.340}), {"S": "backbeat", "K": "kick"})  # 1.1 dB louder
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)],
                        pieces={"rattle": "snare", "backbeat": "snare", "k": "kick"})
        s.notes["drums"] = [(x / 4, 0.1, float("nan"), "rattle") for x in range(12)] + [(x, 0.1, float("nan"), "backbeat") for x in (1.0, 3.0, 5.0, 7.0)] + \
                           [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)]
        s.voice_notes = {2: ("drums", s.notes["drums"])}
        s.kit_levels = {"rattle": 0.1, "backbeat": 0.4, "k": 0.5}
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.00@@@m,S=backbeat@0.80@@@d+rattle@0.20@@@0.75")   # the slot's level is the pick's; the rattle
        del s.kit_levels["backbeat"]                                                                        # its second with 12 of the 16 hits (round 99)
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.00@@@m,S=rattle@0.20@@@d")                      # the backbeat's four hits: no second

    def test_a_letters_figure_is_its_slots_samples_hits(self):
        """Round 81: the written kit played one sample a letter, so a letter's figure counted its slot's sample's hits alone
        (the backbeats, not the rattle's eighths beside them); the slot carries its strike class after the hold (a under a
        hit a bar, s to two, m to six, d over); the drum units and the limbs' units carry the kit's classes as a value. Since
        round 99 the written kit plays the letter's second sample too, so the figure and the class count both samples' hits
        where the other has eight or more (the rattle's eighths beside the backbeats: a dense snare), the slot's alone under."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)],
                        pieces={"rattle": "snare", "backbeat": "snare", "k": "kick", "x": "none"})
        s.notes["drums"] = [(x / 2, 0.1, float("nan"), "rattle") for x in range(12)] + [(x, 0.1, float("nan"), "backbeat") for x in (1.0, 3.0, 5.0, 7.0)] + \
                           [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)] + [(3.5, 0.1, float("nan"), "x")]
        s.voice_notes = {2: ("drums", s.notes["drums"])}
        s.kit_levels = {"rattle": 0.1, "backbeat": 0.4, "k": 0.5}
        self.assertEqual(rhythm.kit_slots(s), {"K": "k", "S": "backbeat"})
        self.assertEqual(rhythm.kit_second_samples(s), {"S": "rattle"})                                          # twelve hits: the snare's second (round 99)
        self.assertEqual([u.outcome for u in rhythm.drum_units([s])], ["0:K 0:S 1/2:S 1:S 3/2:S 2:K 2:S 5/2:S 3:S 7/2:S 7/2:o", "0:K 0:S 1/2:S 1:S 3/2:S 2:K 3:S"])
        self.assertEqual(rhythm.kit_classes(s), {"K": "m", "S": "d"})                                            # both samples' hits: eight a bar; a letter
        self.assertEqual({u.values["classes"] for u in rhythm.drum_units([s])}, {"Km Sd"})                       # without a slot keeps its hit
        self.assertEqual({u.values["classes"] for u in rhythm.drum_group_units([s], ("K", "S", "t"))}, {"Km Sd"})
        self.assertEqual({(u.values["limb1"], u.values["limb2"], u.values["limb3"]) for u in rhythm.drum_group_units([s], ("K", "S", "t"))}, {("Sd", "Km", "-")})
        self.assertEqual({u.values["classes"] for u in rhythm.drum_group_units([s], ("o",))}, {"-"})
        self.assertEqual(rhythm.class_values(rhythm.kit_classes(s), ("K", "S", "t")), {"limb1": "Sd", "limb2": "Km", "limb3": "-"})   # the densest first
        notes = s.notes["drums"]
        s.notes["drums"] = [n for n in notes if n[3] != "rattle"] + [(x / 2, 0.1, float("nan"), "rattle") for x in range(7)]
        self.assertEqual(rhythm.kit_second_samples(s), {})                                                       # seven rattle hits: no second, and round 81's
        self.assertEqual([u.outcome for u in rhythm.drum_units([s])], ["0:K 1:S 2:K 3:S 7/2:o", "0:K 1:S 2:K 3:S"])   # figure and class stand: the slot's alone
        self.assertEqual(rhythm.kit_classes(s), {"K": "m", "S": "m"})
        self.assertEqual(rhythm.class_values(rhythm.kit_classes(s), ("K", "S", "t")), {"limb1": "Km", "limb2": "Sm", "limb3": "-"})   # a tie: the kick first
        s.notes["drums"] = notes
        self.assertEqual(rhythm.class_values(rhythm.kit_classes(s), ("h",)), {"classes": "-"})
        self.assertEqual(rhythm.habit_class(rhythm.kit_classes(s), ("K", "S", "t")), "Sd")                      # the dense snare leads the limb (round 99)
        self.assertEqual(rhythm.limb_order({"K": "a", "S": "d", "t": "m"}, {"K", "S", "t"}), ["S", "t", "K"])                        # the densest first
        self.assertEqual(rhythm.habit_of(0.3, rhythm.SLOT_CLASSES), "x"); self.assertEqual(rhythm.habit_of(0.7, rhythm.SLOT_CLASSES), "a")   # rare under half
        self.assertEqual(rhythm.classes_value(rhythm.kit_classes(s), ("S", "h")), "Sd")
        self.assertEqual([h.outcome for h in rhythm.drum_habit_units([s])], ["dense varied"])                  # 11 and 7 hits a bar, the rattle in (round 99)
        del s.kit_levels["backbeat"]                                                                              # the rattle takes the slot: its hits are the figure,
        self.assertEqual(rhythm.kit_slots(s), {"K": "k", "S": "rattle"})                                          # the backbeat's four hits no second
        self.assertEqual(rhythm.kit_second_samples(s), {})
        self.assertEqual([len([t for t in rhythm._tokens(u.outcome) if t.endswith(":S")]) for u in rhythm.drum_units([s])], [8, 4])
        self.assertEqual(rhythm.kit_classes(s), {"K": "m", "S": "d"})
        self.assertEqual([h.outcome for h in rhythm.drum_habit_units([s])], ["dense varied"])

    def test_the_token_carries_where_its_samples_are_played(self):
        """Round 86: the eighth field carries the range the song plays the part's sample over, and each voice beyond the
        line its own sample's; a part with fewer than eight pitched notes on its sample keeps the bare id."""
        chords = [Span(0.0, 16.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(float(i * 4), float(i * 4 + 4)) for i in range(4)], chords, bpm=100.0, sid="id", game="G",
                        numbers=[0, 1, 2, 3], parts=[(0, 4)], tonic=0, mode="major")
        line = [(float(i), 1.0, 36.0 + (i % 12), "bass0123456789") for i in range(16)]            # 36 to 47 on one sample
        second = [(float(i), 1.0, 55.0 + (i % 5), "slap0123456789") for i in range(0, 16, 2)]      # 55 to 59
        s.notes["bass"] = line + second
        s.voice_notes = {0: ("bass", line), 1: ("bass", second)}
        s.voice_levels = {0: 0.5, 1: 0.3}; s.levels = {"bass": 0.5}
        self.assertEqual(rhythm.part_sample_id(s, "bass"), "sbass012345")
        lo, hi = rhythm.part_register(line, ambitus=True)
        self.assertEqual(rhythm.part_sample_field(s, "bass"), f"sbass012345@{lo}-{hi}")
        lo2, hi2 = rhythm.part_register(second, ambitus=True)
        self.assertTrue(rhythm.layer_tokens(s, "bass")[0].endswith(f"@{lo2}-{hi2}"), rhythm.layer_tokens(s, "bass"))
        s.notes["melody"] = [(float(i), 1.0, 72.0, "lead0123456789") for i in range(6)]            # six notes: no range
        s.voice_notes[2] = ("melody", s.notes["melody"]); s.voice_levels[2] = 0.4; s.levels["melody"] = 0.4
        self.assertEqual(rhythm.part_sample_field(s, "melody"), "slead012345")

    def test_the_kits_channels_ride_the_token(self):
        """Round 87: the drums token's fourth field names the pieces each game channel plays, in the song's channel order
        with the letters in LETTERS' order; a slot's channel is the one its sample is struck on most."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)],
                        pieces={"k": "kick", "sn": "snare", "h": "hat"}, tonic=0, mode="major")
        kick = [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)]
        snare = [(x, 0.1, float("nan"), "sn") for x in (1.0, 3.0, 5.0, 7.0)]
        hat = [(x + 0.5, 0.1, float("nan"), "h") for x in range(8)]
        s.notes["drums"] = kick + snare + hat
        s.notes["melody"] = [(float(i), 1.0, 72.0, "sa") for i in range(8)]
        s.voice_notes = {0: ("melody", s.notes["melody"]), 3: ("drums", hat), 5: ("drums", kick + snare)}
        s.voice_levels = {0: 0.5, 3: 0.2, 5: 0.4}; s.levels = {"melody": 0.5, "drums": 0.3}
        self.assertEqual(rhythm.kit_channels(s), "h|KS")                                            # the song's channel order, hat first
        drums = next(t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("drums="))
        self.assertEqual(drums.split("=", 1)[1].split(":")[3], "h|KS")
        s.voice_notes[5] = ("drums", kick); s.voice_notes[6] = ("drums", snare)
        self.assertEqual(rhythm.kit_channels(s), "h|K|S")                                           # three channels, one piece each
        self.assertEqual(rhythm.kit_channels(rhythm.Song("t", 4, 4, [(0.0, 4.0)], chords, notes={"melody": s.notes["melody"]})), "")

    def test_the_pans_ride_the_token(self):
        """Round 84: a pitched part's token carries its voices' pans as a tenth field, the line voice first, each the median
        right-side share of the voice's notes kept to twentieths; a kit slot carries its sample's pan after the echo mark; a
        song whose readings hold no pans keeps the old forms."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)],
                        pieces={"k": "kick", "h": "hat"}, tonic=0, mode="major")
        kick = [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)]
        hat = [(x + 0.5, 0.1, float("nan"), "h") for x in range(8)]
        line = [(float(i), 1.0, 72.0, "sa") for i in range(8)]
        second = [(float(i), 1.0, 67.0, "sb") for i in range(0, 8, 2)]
        s.notes["drums"] = kick + hat
        s.notes["accompaniment"] = line + second
        s.voice_notes = {0: ("accompaniment", line), 1: ("accompaniment", second), 2: ("drums", kick), 3: ("drums", hat)}
        s.voice_levels = {0: 0.5, 1: 0.3, 2: 0.4, 3: 0.2}
        s.levels = {"accompaniment": 0.5, "drums": 0.3}
        s.kit_levels = {"k": 0.4, "h": 0.2}
        self.assertEqual(rhythm.pan_field(s, "accompaniment"), "")                                    # no pans read: no field
        self.assertTrue(rhythm.kit_token(s, 0.5).endswith("@m"), rhythm.kit_token(s, 0.5))            # and the slots end at their class
        s.voice_pans = {0: 0.37, 1: 0.63, 2: 0.5, 3: 0.58}
        s.kit_pans = {"k": 0.5, "h": 0.58}
        self.assertEqual(rhythm.pan_field(s, "accompaniment"), "0.35/0.65")                           # the line first, kept to twentieths
        acc = next(t for t in rhythm.balance_units([s])[0].outcome.split() if t.startswith("accompaniment="))
        self.assertEqual(acc.split(":")[9], "0.35/0.65")                                              # the tenth field
        kit = rhythm.kit_token(s, 0.5).split(",")
        self.assertTrue(kit[0].endswith("@m@@0.50"), kit)                                             # the kick's pan after an empty echo mark
        self.assertTrue(kit[1].endswith("@m@@0.60"), kit)                                             # the hat's 0.58 kept to 0.60
        s.voice_pans.pop(1)
        self.assertEqual(rhythm.pan_field(s, "accompaniment"), "0.35")                                # a voice without a pan: the line's alone

    def test_a_voice_in_two_places(self):
        """Round 85: a voice whose pans make stays of a bar or more in exactly two places carries them as its word, back and
        forth or moving once; jitter under a bar and a voice in one place keep the median."""
        from bitcomposer.translate.rhythm import readings
        nan = float("nan")
        def rows(pans):                                     # a note a beat, 4/4: pans[k] for beat k
            return [(float(k), 1.0, 60.0, 0.5, p, 0, nan) for k, p in enumerate(pans)]
        self.assertEqual(readings.pan_moves(rows([0.6] * 20 + [0.45] * 52 + [0.6] * 20 + [0.45] * 52), 4), (0.6, 5, 0.45, 13))
        self.assertEqual(readings.pan_moves(rows([0.35] * 16 + [0.65] * 100), 4), (0.35, 4, 0.65, None))
        self.assertIsNone(readings.pan_moves(rows([0.5] * 64), 4))                                   # one place
        self.assertIsNone(readings.pan_moves(rows([0.45, 0.55] * 32), 4))                            # jitter a note at a time: no stay
        self.assertIsNone(readings.pan_moves(rows([0.3] * 16 + [0.5] * 16 + [0.7] * 16), 4))        # three places
        self.assertIsNone(readings.pan_moves(rows([0.6] * 16 + [0.65] * 16), 4))                       # a twentieth apart: a bin's edge, no move
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)], tonic=0, mode="major")
        line = [(float(i), 1.0, 72.0, "sa") for i in range(8)]
        s.notes["melody"] = line
        s.voice_notes = {0: ("melody", line)}
        s.voice_levels = {0: 0.5}; s.levels = {"melody": 0.5}
        s.voice_pans = {0: 0.52}
        self.assertEqual(rhythm.pan_word(s, 0), "0.50")
        s.voice_pan_moves = {0: (0.6, 5, 0.45, 13)}
        self.assertEqual(rhythm.pan_word(s, 0), "0.60x5|0.45x13")
        s.voice_pan_moves = {0: (0.35, 4, 0.65, None)}
        self.assertEqual(rhythm.pan_field(s, "melody"), "0.35x4>0.65")

    def test_the_kits_echo_rides_the_token(self):
        """Round 82: a slot whose sample's hits sit on drum voices that send to echo carries an e after its class (the chip's
        echo is per channel: Wild West sends its blip and keeps its kick dry), and the balance token carries the song's echo
        word before the key, as the echo table counts it."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)],
                        pieces={"k": "kick", "blip": "other"}, tonic=4, mode="minor")
        kick = [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)]
        blip = [(x, 0.23, 71.0, "blip") for x in (1.0, 3.0, 5.0, 7.0)]
        s.notes["drums"] = kick + blip
        s.notes["melody"] = [(float(i), 1.0, 72.0, "sa") for i in range(8)]
        s.voice_notes = {0: ("melody", s.notes["melody"]), 2: ("drums", kick), 3: ("drums", blip)}
        s.voice_levels = {0: 0.5, 2: 0.4, 3: 0.2}
        s.levels = {"melody": 0.5, "drums": 0.3}
        s.kit_levels = {"k": 0.4, "blip": 0.2}
        s.kit_pitches = {"blip": 71}
        self.assertEqual(rhythm.kit_echo(s), set())                                                    # no sends read: no mark
        self.assertNotIn("@e", rhythm.kit_token(s, 0.5))
        s.echo, s.echo_sends = (0.2, 80.0, 0.78), {0: 1.0, 2: 0.0, 3: 1.0}
        self.assertEqual(rhythm.kit_echo(s), {"o"})
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@0.80@@@m,o=blip@0.40@d4@@m@e")                 # the blip's slot sends, the kick's is dry
        token = rhythm.balance_units([s])[0].outcome.split()
        self.assertIn("echo=0.20:80:0.78:drums+melody:-", token)                                      # one of two drum voices sends: half, so the part sends
        self.assertLess(token.index("echo=0.20:80:0.78:drums+melody:-"), token.index("key=4:minor"))
        self.assertEqual(rhythm.echo_outcome(s), "0.20:80:0.78:drums+melody:-")
        s.echo_sends[2] = 1.0
        self.assertEqual(rhythm.kit_echo(s), {"K", "o"})
        self.assertEqual(rhythm.echo_outcome(s), "0.20:80:0.78:drums+melody:-")
        s.echo_sample_sends = {"blip": 1.0, "k": 0.2}                                                 # the sample's own share where read: the kick's
        self.assertEqual(rhythm.kit_echo(s), {"o"})                                                   # notes on a sending voice mostly dry
        from types import SimpleNamespace
        from bitcomposer.translate import reading
        note = lambda v, send, smp: SimpleNamespace(voice=v, echo=send, echo_writes=True, echo_delay=0.08, echo_volume=(-0.2, 0.2), echo_feedback=0.78, sample=smp)   # noqa: E731
        echo = reading.echo_of_notes([note(4, False, 3), note(4, False, 3), note(4, True, 5), note(4, False, 3)], {3: "hatkey", 5: "blipkey"})
        self.assertEqual((echo["voice_4"], echo["sample_hatkey"], echo["sample_blipkey"]), (0.25, 0.0, 1.0))   # one channel, the hat dry and the blip wet

    def test_the_kits_pieces_carry_their_own_levels(self):
        """Round 68: a song's kit field carries each piece's level beside its sample, the median level of the notes struck
        on that sample as a share of the loudest part's in tenths (`K=k@1.6,S=s@0.6,h=h@0.2`). The part's one level is the
        median over every drum note, the most frequent piece's (the hat's), and Blackjack's kick had played as quiet as
        its hat. A piece whose level the readings never heard (NaN) keeps the old form; the part's level stays beside."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1],
                        parts=[(0, 2)], pieces={"k": "kick", "s": "snare", "h": "hat"})
        s.notes["melody"] = [(0.0, 1.0, 72, "sa"), (1.0, 1.0, 74, "sa"), (2.0, 1.0, 76, "sa"), (3.0, 1.0, 77, "sa"),
                             (4.0, 2.0, 79, "sa"), (6.0, 2.0, 76, "sa")]
        s.notes["drums"] = [(x, 0.1, float("nan"), "k") for x in (0.0, 2.0, 4.0, 6.0)] + [(x, 0.1, float("nan"), "s") for x in (1.0, 3.0, 5.0, 7.0)] + \
                           [(x / 2, 0.1, float("nan"), "h") for x in range(16)]
        s.voice_notes = {1: ("melody", s.notes["melody"]), 2: ("drums", s.notes["drums"])}
        s.voice_levels = {1: 0.5, 2: 0.1}
        s.levels = {"melody": 0.5, "drums": 0.1}            # the part's median: the hat's, 0.2 of the tune
        s.kit_levels = {"k": 0.8, "s": 0.3, "h": 0.1}       # the kick louder than the tune, the snare at 0.6 of it
        self.assertEqual(rhythm.kit_token(s), "K=k@@@@m,S=s@@@@m,h=h@@@@d")               # the old form without a top
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@@@m,S=s@0.60@@@m,h=h@0.20@@@d")   # in hundredths since round 70
        token = rhythm.balance_units([s])[0].outcome
        self.assertIn("drums=:::KSh:0.2:::K=k@1.60@@@m,S=s@0.60@@@m,h=h@0.20@@@d", token)   # one channel, three pieces (round 87)
        s.kit_levels["s"] = float("nan")
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@1.60@@@m,S=s@@@@m,h=h@0.20@@@d")   # an unread level never reaches the token
        s.kit_levels = {}
        self.assertEqual(rhythm.kit_token(s, 0.5), "K=k@@@@m,S=s@@@@m,h=h@@@@d")

    def test_the_songs_echo_is_a_counted_word(self):
        """Round 70: the song's echo as the chip had it at key-on (reading.echo_of_notes: the volume of full, the delay in
        ms, the feedback, each voice's share of notes that send) is kept with the readings and counted as the `echo`
        word, one unit a song: the triple with the parts that send and the parts that stay dry. FFVI's echo volume is
        0.20 of full in 70 of 82 songs and its delay 80 ms in every one; the written songs had sent at 0.4."""
        from types import SimpleNamespace
        from bitcomposer.translate import reading
        note = lambda v, send, vol=0.2, ms=0.08, fb=0.78: SimpleNamespace(voice=v, echo=send, echo_writes=True, echo_delay=ms, echo_volume=(-vol, vol), echo_feedback=fb)   # noqa: E731
        notes = [note(0, True) for _ in range(8)] + [note(1, False) for _ in range(8)] + [note(2, True), note(2, False), note(2, False), note(2, False)] + [note(3, True, 0.25, 0.08, 0.55)]
        echo = reading.echo_of_notes(notes)
        self.assertEqual((echo["volume"], echo["delay_ms"], echo["feedback"]), (0.2, 80.0, 0.78))
        self.assertEqual({k: v for k, v in echo.items() if k.startswith("voice_")}, {"voice_0": 1.0, "voice_1": 0.0, "voice_2": 0.25, "voice_3": 1.0})
        self.assertEqual(reading.echo_of_notes([note(0, False)]), {"voice_0": 0.0, "volume": 0.0, "delay_ms": 0.0, "feedback": 0.0})
        self.assertEqual(reading.echo_of_notes([note(0, True, 0.2, 0.0)])["volume"], 0.0)          # no delay: nothing sends
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)])
        s.notes["melody"] = [(float(i), 1.0, 72.0, "sa") for i in range(8)]
        s.notes["bass"] = [(float(i), 1.0, 36.0, "sb") for i in range(8)]
        s.notes["accompaniment"] = [(float(i), 1.0, 60.0, "sc") for i in range(8)]
        s.voice_notes = {0: ("melody", s.notes["melody"]), 1: ("bass", s.notes["bass"]), 2: ("accompaniment", s.notes["accompaniment"][:4]),
                         3: ("accompaniment", s.notes["accompaniment"][4:])}
        self.assertEqual(rhythm.echo_units([s]), [])                                                 # never read: no unit
        s.echo, s.echo_sends = (0.2, 80.0, 0.78), {0: 1.0, 1: 0.0, 2: 0.25, 3: 1.0}
        u = rhythm.echo_units([s])[0]
        self.assertEqual((u.outcome, u.values), ("0.20:80:0.78:accompaniment+melody:bass", {"part": "echo"}))   # one of two voices sending: the part sends
        s.echo_sends[3] = 0.4
        self.assertEqual(rhythm.echo_units([s])[0].outcome, "0.20:80:0.78:melody:accompaniment+bass")
        s.echo = (0.0, 0.0, 0.0); s.echo_sends = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        self.assertEqual(rhythm.echo_units([s])[0].outcome, "0.00:0:0.00:-:accompaniment+bass+melody")
        from bitcomposer.translate import packtables
        self.assertIn("echo", packtables.KEPT)

    def test_a_parts_vibrato_is_a_counted_word(self):
        """Round 72: a note's pitch writes while it sounds (spc.notes.Note.bends) read as vibrato where they swing back
        and forth (reading.note_vibrato: depth, rate, onset; a slide is not), each voice's held notes counted by length
        class and kept with the readings (vibrato_of_notes, features of source "vibrato"), and counted as the
        `vibrato` word, one unit a part a song: the shares by class, then the depth, rate and onset."""
        import math
        from types import SimpleNamespace
        from bitcomposer.translate import packtables, reading
        p0 = 0x1000

        def wobble(voice, start, length, depth=30.0, rate=5.7, onset=0.5):
            bends, t = [], onset
            while t < length:
                bends.append((start + t, round(p0 * 2 ** (depth * math.sin(2 * math.pi * rate * (t - onset)) / 1200))))
                t += 0.005
            return SimpleNamespace(voice=voice, start=start, end=start + length, pitch=p0, bends=bends, noise=False)
        plain = lambda voice, start, length: SimpleNamespace(voice=voice, start=start, end=start + length, pitch=p0, bends=[], noise=False)   # noqa: E731
        v = reading.note_vibrato(wobble(0, 0.0, 2.0))
        self.assertAlmostEqual(v["depth"], 30.0, delta=1.0)
        self.assertAlmostEqual(v["rate"], 5.7, delta=0.2)
        self.assertAlmostEqual(v["onset"], 0.5, delta=0.02)
        self.assertFalse(v["trill"])
        self.assertIsNone(reading.note_vibrato(SimpleNamespace(voice=0, start=0.0, end=1.0, pitch=p0, bends=[(0.1 * k, p0 + 30 * k) for k in range(1, 9)], noise=False)))   # a slide
        self.assertIsNone(reading.note_vibrato(plain(0, 0.0, 1.0)))
        self.assertTrue(reading.note_vibrato(wobble(0, 0.0, 2.0, depth=100.0))["trill"])
        notes = [wobble(0, 0.0, 2.0), wobble(0, 2.0, 1.5), plain(0, 4.0, 1.5), plain(0, 6.0, 0.4), plain(0, 7.0, 0.2),   # the tune: 2 of 3 long, 0 of 1 short
                 plain(1, 0.0, 0.6), plain(1, 1.0, 0.6), wobble(1, 2.0, 0.6, depth=15.0, rate=6.0, onset=0.1)]            # the counter: 1 of 3 at 0.5-1 s
        f = reading.vibrato_of_notes(notes)
        self.assertEqual((f["voice_0_held"], f["voice_0_vib"], f["voice_0_held_0"], f["voice_0_vib_0"], f["voice_0_held_2"], f["voice_0_vib_2"], f["voice_0_held_3"], f["voice_0_vib_3"]),
                         (4.0, 2.0, 1.0, 0.0, 2.0, 1.0, 1.0, 1.0))
        self.assertEqual((f["voice_1_held"], f["voice_1_vib"], f["voice_1_held_1"], f["voice_1_vib_1"]), (3.0, 1.0, 3.0, 1.0))
        self.assertAlmostEqual(f["voice_1_depth"], 15.0, delta=1.0)
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)])
        s.notes["melody"] = [(float(i), 1.0, 72.0, "sa") for i in range(8)]
        s.notes["counter"] = [(float(i), 1.0, 60.0, "sc") for i in range(8)]
        s.voice_notes = {0: ("melody", s.notes["melody"]), 1: ("counter", s.notes["counter"])}
        self.assertEqual(rhythm.vibrato_units([s]), [])                                               # never read: no unit
        s.vibrato = rhythm.readings.vibrato_of_features(f)
        units = {u.values["part"]: u.outcome for u in rhythm.vibrato_units([s])}
        self.assertEqual(units["melody"], "0.0/-/0.5/1.0:30:5.5:0.5")
        self.assertEqual(units["counter"], "-/0.3/-/-:15:6.0:0.1")
        self.assertEqual(rhythm.vibrato_word(units["melody"]), {"shares": [0.0, None, 0.5, 1.0], "depth": 30.0, "rate": 5.5, "onset": 0.5})
        self.assertIsNone(rhythm.vibrato_word("nonsense"))
        self.assertIn("vibrato", packtables.KEPT)

    def test_the_parts_level_and_sample_are_the_line_voices(self):
        """Round 70: a layered part's level on the token (the fifth field) is its LINE voice's median level, not the median
        over every voice's notes, and its sample (the eighth field) the line voice's; the sixth field's shares are counted
        against the line already, so line x share reproduces every voice. Troops March on's counter line sat at 0.27 of
        the top and played at 0.40 (the pooled median), its bass line on sa692eac0a6 played on the second voice's
        s1d296a2572. The bass's line is the voice with the longest notes; a part of one voice keeps its median."""
        chords = [Span(0.0, 32.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(4.0 * k, 4.0 * k + 4) for k in range(8)], chords, bpm=100.0, sid="id", game="G", numbers=list(range(8)),
                        parts=[(0, 8)])
        s.notes["melody"] = [(4.0 * k + i, 1.0, 72.0 + i, "sm") for k in range(8) for i in range(4)]
        line = [(4.0 * k + 0.5 * i, 0.4, 60.0, "sa") for k in range(8) for i in range(8)]       # the busiest voice: the line
        second = [(4.0 * k + i, 0.9, 52.0, "sb") for k in range(8) for i in range(4)]
        s.notes["accompaniment"] = line + second
        sustained = [(4.0 * k, 3.0, 36.0, "slong") for k in range(8)]                            # the bass's line: the longest notes
        slap = [(4.0 * k + 0.5 * i, 0.2, 48.0, "sshort") for k in range(8) for i in range(8)]
        s.notes["bass"] = sustained + slap
        s.voice_notes = {1: ("melody", s.notes["melody"]), 3: ("accompaniment", line), 4: ("accompaniment", second),
                         5: ("bass", sustained), 6: ("bass", slap)}
        s.voice_levels = {1: 0.5, 3: 0.2, 4: 0.5, 5: 0.31, 6: 0.5}
        pooled = {"melody": 0.5, "accompaniment": 0.3, "bass": 0.45}                             # the medians over every voice's notes
        self.assertEqual(rhythm.part_levels(s, pooled), {"melody": 0.5, "accompaniment": 0.2, "bass": 0.31})
        s.voice_levels[3] = float("nan")
        self.assertEqual(rhythm.part_levels(s, pooled)["accompaniment"], 0.3)                     # the line's level never read: the pooled median
        s.voice_levels[3] = 0.2
        s.levels = rhythm.part_levels(s, pooled)
        self.assertEqual(rhythm.part_sample_id(s, "accompaniment"), "sa")                         # the line voice's sample, not the most played
        self.assertEqual(rhythm.part_sample_id(s, "bass"), "slong")
        self.assertEqual(rhythm.part_sample_id(s, "melody"), "sm")
        tokens = {t.partition("=")[0]: t.partition("=")[2].split(":") for t in rhythm.balance_units([s])[0].outcome.split() if "=" in t}
        self.assertEqual(tokens["accompaniment"][4], "0.4")                                         # the line at 0.2 of the top 0.5
        self.assertEqual(tokens["accompaniment"][5].split("@")[0], "2.5")                          # the second voice at 2.5 of the line: 0.5 of full
        self.assertEqual(tokens["accompaniment"][7].split("@")[0], "sa")                      # round 86: its played range follows the id
        self.assertEqual((tokens["bass"][4], tokens["bass"][5].split("@")[0], tokens["bass"][7].split("@")[0]), ("0.6", "1.6", "slong"))   # round 86: the range after the id
        self.assertEqual(tokens["melody"][4], "1.0")


class AttackUnitTests(unittest.TestCase):
    def test_a_part_s_sample_is_struck_or_sustaining_by_its_strike_over_its_body(self):
        """The attacks word (round 73): a part's line plays a struck sample when the sample's strike is more than twice
        its loop body, a sustaining one otherwise; nothing is counted for a sample whose loudness is not set."""
        chords = [Span(0.0, 8.0, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(0.0, 4.0), (4.0, 8.0)], chords, bpm=100.0, sid="id", game="G", numbers=[0, 1], parts=[(0, 2)])
        s.notes["melody"] = [(0.0, 1.0, 72, "pianokey01"), (1.0, 1.0, 74, "pianokey01"), (2.0, 2.0, 76, "pianokey01")]
        s.notes["bass"] = [(0.0, 2.0, 40, "padkey0001"), (2.0, 2.0, 43, "padkey0001")]
        s.notes["accompaniment"] = [(0.0, 1.0, 60, "unknownkey")]
        try:
            rhythm.set_loudness({"spianokey01": 0.1, "spadkey0001": 0.3}, {"spianokey01": 0.5, "spadkey0001": 0.4})
            units = {u.values["part"]: u.outcome for u in rhythm.attack_units([s])}
        finally:
            rhythm.set_loudness({})
        self.assertEqual(units, {"melody": "struck", "bass": "sustaining"})
        self.assertEqual(rhythm.attack_units([s]), [])
