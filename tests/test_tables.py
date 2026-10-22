"""The tables framework: votes, backoff, scoring, draws, the round trip; and the rhythm units."""
import json
import math
import random
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
