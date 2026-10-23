"""The bass writer: tones from marks, a figure realized, a bass written from a table."""
import random
from fractions import Fraction
import unittest

from bitcomposer.translate import rhythm, tables, writer
from bitcomposer.translate.vocab import Span


def _song(sid="a", bars=4):
    chords = [Span(0.0, 8.0, 0, "", 1.0), Span(8.0, 16.0, 7, "m7", 1.0)]          # C, then G minor seventh
    s = rhythm.Song("t", 4, 4, [(4.0 * i, 4.0 * i + 4) for i in range(bars)], chords, bpm=120.0, sid=sid, game="G",
                    numbers=list(range(bars)))
    s.notes["bass"] = [(4.0 * i + x, 0.4, 36.0 if x < 2 else 43.0, "k") for i in range(bars) for x in (0.0, 1.0, 2.0, 3.0)]
    return s


class WriterTests(unittest.TestCase):
    def test_tones(self):
        major = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual([writer.tone(0, "", m, major) for m in ("R", "r", "?", "3", "5", "7", "s", "+")], [0, 0, 0, 4, 7, 10, 5, 2])
        self.assertEqual([writer.tone(7, "m7", m, major) for m in ("3", "5", "7")], [10, 2, 5])
        self.assertEqual(writer.tone(0, "dim", "5", major), 6)
        self.assertEqual(writer.tone(4, "", "+", major), 2)                  # on E in C major the step above (F#) is out: the step below (D)
        self.assertEqual(writer.tone(4, "", "+", {7, 9, 11, 0, 2, 4, 6}), 6)   # in G major F# is in

    def test_realize(self):
        s = _song()
        notes, root, last = writer.realize("0:R 1/2:r 1:5 2:3 3:+", 0.0, 4.0, s, 36, 0.5, {0, 2, 4, 5, 7, 9, 11}, 0)
        # the passing tone at the end steps on from E (40) in the line's falling direction: D (38)
        self.assertEqual([(a, b, m) for a, b, m in notes], [(0.0, 0.25, 36.0), (0.5, 0.75, 48.0), (1.0, 1.5, 43.0), (2.0, 2.5, 40.0), (3.0, 3.5, 38.0)])
        self.assertEqual((root, last), (0, 38.0))
        notes, _, _ = writer.realize("0:R 1:+ 2:3", 0.0, 4.0, s, 36, 1.0, {0, 2, 4, 5, 7, 9, 11}, 0)
        self.assertEqual([m for _, _, m in notes], [36.0, 38.0, 40.0])    # C, then a step toward E: D, then E
        notes, _, _ = writer.realize("0:5 1:+ 2:3", 0.0, 4.0, s, 36, 1.0, {0, 2, 4, 5, 7, 9, 11}, 0)
        self.assertEqual([m for _, _, m in notes], [43.0, 41.0, 40.0])    # G, then a step down toward E: F, then E
        notes, _, _ = writer.realize("0:+ 1:R", 0.0, 4.0, s, 36, 1.0, {0, 2, 4, 5, 7, 9, 11}, 0)
        self.assertEqual([m for _, _, m in notes], [38.0, 36.0])          # nothing before: the step above the root
        notes, root, last = writer.realize("0:R 2:7", 8.0, 12.0, s, 36, 1.0, set(), 0, 38.0)   # the G minor seventh bar
        self.assertEqual([m for _, _, m in notes], [43.0, 41.0])
        self.assertEqual((root, last), (7, 41.0))
        self.assertEqual(writer.realize("-", 0.0, 4.0, s, 36, 1.0, set(), 5, 40.0), ([], 5, 40.0))

    def test_place(self):
        self.assertEqual(writer.place(0, 36, None), 36)                     # the first note: lowest
        self.assertEqual(writer.place(0, 36, 46.0), 48)                     # C nearest to 46: 48, not 36
        self.assertEqual(writer.place(0, 36, 42.0), 36)                     # as near either way: the lower
        self.assertEqual(writer.place(7, 36, 36.0), 43)
        self.assertEqual(writer.place(7, 36, 50.0), 43)                     # 55 is beyond the reach (36 + 16)
        self.assertEqual(writer.place(0, 36, 50.0, octave_up=True), 48)

    def test_a_bass_written_from_a_table(self):
        others = [_song("b"), _song("c")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        self.assertIsInstance(model, tables.Cache)
        notes, figures = writer.bass(_song(), model, random.Random(1), key=(0, "major"))
        self.assertEqual(len(figures), 4)
        self.assertTrue(all(writer.on_grid(f, 4) and f != "-" for f in figures))
        self.assertTrue(all(f in model.table.vocabulary for f in figures))        # only bars some song played
        self.assertTrue(all(2 <= len(rhythm._tokens(f)) <= 6 for f in figures))   # _song plays 4 a bar: 2 to 6
        self.assertTrue(writer.fits("0:R 1:R", _song(), {"0:R 1:R"}, 4))
        self.assertFalse(writer.fits("0:R 1:R", _song(), set(), 4))
        self.assertFalse(writer.fits("0:R 1:R 2:R", _song(), {"0:R 1:R 2:R"}, 2))
        self.assertFalse(writer.fits("-", _song(), {"-"}, 4))
        resting = _song()
        resting.notes["bass"] = [n for n in resting.notes["bass"] if n[0] >= 4.0]      # the first bar rests
        _, figures = writer.bass(resting, model, random.Random(1), key=(0, "major"))
        self.assertEqual(figures[0], "-")
        self.assertTrue(all(f != "-" for f in figures[1:]))
        self.assertTrue(all(0.0 <= a < b <= 16.0 for a, b, _ in notes))
        self.assertTrue(all(36.0 <= m < 60.0 for _, _, m in notes))
        self.assertEqual(writer.sounded(_song().notes["bass"]), 0.4)
        again, _ = writer.bass(_song(), model, random.Random(1), key=(0, "major"))
        self.assertEqual(notes, again)                                        # the seed settles it
        self.assertTrue(writer.on_grid("0:R 1/2:r 3:5", 2))
        self.assertFalse(writer.on_grid("0:R 1/3:R", 4))
        self.assertTrue(writer.on_grid("-", 1))

    def test_spans_and_rhythm(self):
        self.assertEqual(writer.rhythm_of("0:R 1/2:r 3:5"), "0 1/2 3")
        self.assertEqual(writer.rhythm_of("-"), "-")
        self.assertEqual(writer.spans(list("aaaa")), [(0, 4, 1)])
        self.assertEqual(writer.spans(list("ababab")), [(0, 6, 2)])
        self.assertEqual(writer.spans(list("abcdabcdx")), [(0, 8, 4), (8, 1, 1)])
        self.assertEqual(writer.spans(list("xabab")), [(0, 1, 1), (1, 4, 2)])
        self.assertEqual(writer.spans(list("ab")), [(0, 1, 1), (1, 1, 1)])
        self.assertEqual(writer.spans([]), [])

    def test_a_span_holds_its_pattern(self):
        others = [_song("b"), _song("c"), _song("d")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 2.0)]
        others[2].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        s = _song(bars=8)                                            # eight bars, the same figure in each: one span of period 1
        s.chords = [Span(0.0, 32.0, 0, "", 1.0)]                      # one chord, so the song's own figures repeat exactly
        _, figures = writer.bass(s, model, random.Random(3), key=(0, "major"))
        self.assertEqual(len(set(figures)), 1)
        # a two-bar pattern through the song: four strikes (roots and fifths), then two (roots)
        s.notes["bass"] = [(4.0 * i + x, 0.4, 36.0 if (i % 2 or x < 2) else 43.0, "k") for i in range(8) for x in ((0.0, 2.0) if i % 2 else (0.0, 1.0, 2.0, 3.0))]
        _, figures = writer.bass(s, model, random.Random(3), key=(0, "major"))
        self.assertEqual(figures[0::2], [figures[0]] * 4)
        self.assertEqual(figures[1::2], [figures[1]] * 4)
        self.assertNotEqual(writer.rhythm_of(figures[0]), writer.rhythm_of(figures[1]))   # the pattern alternates
        s.notes["bass"] = [(4.0 * i + x, 0.4, 36.0 if (i >= 4 or x < 2) else 43.0, "k") for i in range(8) for x in ((0.0, 2.0) if i >= 4 else (0.0, 1.0, 2.0, 3.0))]
        _, figures = writer.bass(s, model, random.Random(3), key=(0, "major"))   # two spans of four bars: a change between them
        self.assertEqual(len(set(figures[:4])), 1)
        self.assertEqual(len(set(figures[4:])), 1)
        self.assertNotEqual(writer.rhythm_of(figures[0]), writer.rhythm_of(figures[4]))

    def test_a_bar_of_another_length_is_written_too(self):
        others = [_song("b"), _song("c")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        s = _song(bars=4)
        s.chords = [Span(0.0, 16.0, 0, "", 1.0)]
        s.bars = [(0.0, 4.0), (4.0, 7.0), (7.0, 11.0), (11.0, 15.0)]           # a three-beat bar second
        s.notes["bass"] = [(a + x, 0.4, 36.0 if x < 2 else 43.0, "k") for a, b in s.bars for x in range(int(b - a))]
        notes, figures = writer.bass(s, model, random.Random(1), key=(0, "major"))
        self.assertEqual(len(figures), 4)
        self.assertNotEqual(figures[1], "-")                                    # written, not left silent
        self.assertTrue(all(float(Fraction(t.partition(":")[0])) < 3 for t in rhythm._tokens(figures[1])))
        self.assertTrue(all(4.0 <= a < b <= 7.0 for a, b, _ in notes if 4.0 <= a < 7.0))

    def test_locked(self):
        self.assertTrue(writer.locked("0:R 2:5", None))
        self.assertTrue(writer.locked("0:R 2:5", ({Fraction(0), Fraction(2)}, {1, 3})))
        self.assertFalse(writer.locked("0:R 1:5", ({Fraction(0), Fraction(2)}, set())))   # misses the hit on beat three
        self.assertFalse(writer.locked("0:R 3/2:5", (set(), {1})))                        # strikes in a stop beat
        self.assertTrue(writer.locked("0:K 1:S", ({Fraction(0), Fraction(1), Fraction(2)}, set()), 2 / 3))   # two of three hits: enough for a drum group
        self.assertFalse(writer.locked("0:K", ({Fraction(0), Fraction(1), Fraction(2)}, set()), 2 / 3))
        others = [_song("b"), _song("c")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        s = _song(bars=4)
        s.chords = [Span(0.0, 16.0, 0, "", 1.0)]
        _, figures = writer.bass(s, model, random.Random(2), key=(0, "major"), lock={1: ({Fraction(0), Fraction(2)}, {1, 3})})
        self.assertTrue(writer.locked(figures[1], ({Fraction(0), Fraction(2)}, {1, 3})))

    def test_a_held_bar_keeps_the_songs_own_figure(self):
        others = [_song("b"), _song("c")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        s = _song(bars=4)
        s.chords = [Span(0.0, 16.0, 0, "", 1.0)]
        s.notes["bass"] = [(4.0 * i + x, 0.4, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in ((0.0, 1.0, 2.0, 3.0) if i != 2 else (0.0, 2.5))]
        _, figures = writer.bass(s, model, random.Random(1), key=(0, "major"), hold={2})
        self.assertEqual(figures[2], "0:R 5/2:5")                       # the song's own bar, air and all
        self.assertTrue(all(f in model.table.vocabulary for i, f in enumerate(figures) if i != 2))

    def test_a_changing_song_changes(self):
        others = [_song("b"), _song("c"), _song("d")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.5, 2.0)]
        others[2].notes["bass"] = [(4.0 * i + x, 0.5, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 2.0, 3.0)]
        model = writer.fit(rhythm.bass_units(others))
        s = _song(bars=6)
        s.chords = [Span(0.0, 24.0, 0, "", 1.0)]
        shapes = ((0.0, 1.0, 2.0, 3.0), (0.0, 1.5, 2.0), (0.0, 2.0, 3.0), (0.0, 1.0, 3.0), (0.0, 0.5, 2.0), (0.0, 2.5, 3.0))
        s.notes["bass"] = [(4.0 * i + x, 0.4, 36.0 if x < 2 else 43.0, "k") for i in range(6) for x in shapes[i]]   # a new rhythm every bar
        _, figures = writer.bass(s, model, random.Random(5), key=(0, "major"))
        self.assertTrue(all(writer.rhythm_of(a) != writer.rhythm_of(b) for a, b in zip(figures, figures[1:])))

    def test_the_songs_manner(self):
        known = {"0:R 1:5", "0:R 1:5 2:R 3:5", "0:R 1:R 2:5 3:5", "1:5 2:5 3:R", "0:R 1/2:R 1:R 3/2:5 2:R 5/2:R 3:5 7/2:R",
                 "0:R 1:R 2:5 11/4:R", "0:R 4/3:5 5/3:R 2:R", "0:R", "-"}
        m = writer.Manner(_song(), "bass", known)                 # quarters on every beat: 4 a bar, the one always struck
        self.assertEqual((m.low, m.high, m.downbeat, m.feel), (3, 5, True, {Fraction(0), Fraction(1), Fraction(2), Fraction(3)}))
        self.assertEqual((m.octaves, m.tones, m.pedal), (False, (2, 2), False))   # _song's bars: two tones each
        self.assertTrue(m.fits("0:R 1:5 2:R 3:5") and m.fits("0:R 1:R 2:5 3:5"))
        env = writer.envelope("0:R 1:R 2:5 3:5")                   # the song's own bar: four strikes, the one struck
        self.assertEqual(env, (2, 6, True, None))
        self.assertFalse(writer.within("0:R 1:R 2:5 3:5", writer.envelope("0:R 1:R 2:5", 3)))   # beat four in a 3-beat bar
        self.assertTrue(writer.within("0:R 1:R 2:5", writer.envelope("0:R 1:R 2:5", 3)))
        self.assertTrue(writer.within("0:R 1:5 2:R 3:5", env) and writer.within("0:R 2:5", env))
        self.assertFalse(writer.within("1:5 2:5 3:R", env))        # nothing on the one
        self.assertFalse(writer.within("0:R", env))                # too sparse for that bar
        self.assertFalse(writer.within("0:R 1/2:R 1:R 3/2:5 2:R 5/2:R 3:5 7/2:R", env))   # too dense for it
        self.assertEqual(writer.envelope("2:R"), (1, 1, False, None))   # a one-note bar off the one allows one note, anywhere
        self.assertFalse(m.fits("0:R 1/2:R 1:R 3/2:5 2:R 5/2:R 3:5 7/2:R"))   # eighths the song never plays
        self.assertFalse(m.fits("0:R 1:R 2:5 11/4:R"))             # a sixteenth the song never plays
        self.assertFalse(m.fits("0:R 4/3:5 5/3:R 2:R"))            # triplets the song never plays
        self.assertFalse(m.fits("-") or m.fits("0:R 3:5"))         # a rest; a bar no song played
        s = _song()
        s.division = 12                                             # a grid that holds triplets (a sixteenth grid would round them)
        s.notes["bass"] = [(4.0 * i + x, 0.3, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 4 / 3, 5 / 3, 2.0)]
        m = writer.Manner(s, "bass", known)
        self.assertEqual((m.feel, m.low, m.high), ({Fraction(0), Fraction(1), Fraction(4, 3), Fraction(5, 3), Fraction(2)}, 4, 6))
        self.assertTrue(m.fits("0:R 4/3:5 5/3:R 2:R"))
        self.assertFalse(m.fits("0:R 1:R 2:5 3:5"))                  # beat four: a position the song never strikes
        spread = _song(bars=8)
        spread.notes["bass"] = [(4.0 * i + x, 0.3, 36.0 if x < 2 else 43.0, "k") for i in range(8)
                                for x in ((0.0, 2.0), (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 2.0), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5))[i % 4]]
        m = writer.Manner(spread, "bass", known)                   # bars of 2, 4, 3 and 8 strikes: the middle half is 2.5 to 7
        self.assertEqual((m.low, m.high), (2, 8))

    def test_the_songs_tones(self):
        known = {"0:R 1:R 2:R 3:R", "0:R 1:R 2:3 3:5", "0:r 1:R 2:R 3:R", "0:R 1:+ 2:5 3:+", "0:5 1:5 2:5 3:5", "0:R 1:5 2:R"}
        roots = _song(bars=8)
        roots.chords = [Span(0.0, 32.0, 0, "", 1.0)]
        roots.notes["bass"] = [(4.0 * i + x, 0.4, 36.0, "k") for i in range(8) for x in (0.0, 1.0, 2.0, 3.0)]   # roots only, a pedal song
        m = writer.Manner(roots, "bass", known)
        self.assertEqual((m.octaves, m.tones, m.anchors, m.roots, m.pedal), (False, (1, 1), (1.0, 1.0), (1.0, 1.0), True))
        self.assertEqual(m.marks, {"R"})                               # the song plays roots and nothing else
        self.assertTrue(m.fits("0:R 1:R 2:R 3:R"))
        self.assertFalse(m.fits("0:5 1:5 2:5 3:5"))                 # a pedal on the fifth in a song of roots
        self.assertFalse(m.fits("0:R 1:R 2:3 3:5"))                 # three tones in a one-tone song
        self.assertFalse(m.fits("0:r 1:R 2:R 3:R"))                 # an octave the song never plays
        self.assertFalse(m.fits("0:R 1:+ 2:5 3:+"))                 # passing tones in a song all on anchors
        walking = _song(bars=8)
        walking.chords = [Span(0.0, 32.0, 0, "", 1.0)]
        walking.notes["bass"] = [(4.0 * i + x, 0.4, m_, "k") for i in range(8) for x, m_ in ((0.0, 36.0), (1.0, 38.0), (2.0, 43.0), (3.0, 41.0))]   # R + 5 +
        m = writer.Manner(walking, "bass", known)
        self.assertEqual((m.tones, m.anchors, m.roots, m.pedal), ((3, 3), (0.5, 0.5), (0.25, 0.25), False))
        self.assertEqual(m.marks, {"R", "5", "+"})
        self.assertFalse(m.fits("0:R 1:s 2:5 3:+"))                  # a sus tone the song never plays
        self.assertTrue(m.fits("0:R 1:+ 2:5 3:+"))
        self.assertFalse(m.fits("0:5 1:5 2:5 3:5"))                  # a pedal in a walking song
        self.assertFalse(m.fits("0:R 1:R 2:R 3:R"))                  # one tone, all anchors


if __name__ == "__main__":
    unittest.main()


class DrumWriterTests(unittest.TestCase):
    def _kit_song(self, sid="d", bars=4, figure=((0.0, "k"), (1.0, "s"), (2.0, "k"), (3.0, "s"), (0.5, "h"), (1.5, "h"), (2.5, "h"), (3.5, "h"))):
        chords = [Span(0.0, 4.0 * bars, 0, "", 1.0)]
        s = rhythm.Song("t", 4, 4, [(4.0 * i, 4.0 * i + 4) for i in range(bars)], chords, bpm=120.0, sid=sid, game="G",
                        numbers=list(range(bars)), pieces={"k": "kick", "s": "snare", "h": "hat", "t": "tom", "c": "cymbal"})
        s.notes["drums"] = [(4.0 * i + x, 0.1, float("nan"), key) for i in range(bars) for x, key in figure]
        return s

    def test_drum_manner(self):
        s = self._kit_song()
        m = writer.DrumManner(s, {"0:K 1:S 2:K 3:S", "0:K 1/2:h 1:S", "0:t 1:t", "0:K 1/4:K 1:S"})
        self.assertEqual(m.kit, {"K", "S", "h"})
        self.assertEqual(m.feel, {Fraction(k, 2) for k in range(8)})
        self.assertTrue(m.fits("0:K 1:S 2:K 3:S") and m.fits("0:K 1/2:h 1:S"))
        self.assertFalse(m.fits("0:t 1:t"))                           # a tom the kit lacks
        self.assertFalse(m.fits("0:K 1/4:K 1:S"))                      # a sixteenth the song never strikes
        self.assertFalse(m.fits("-"))

    def test_drum_envelope(self):
        env = writer.drum_envelope("0:K 1:S 2:K 3:S 0:h 1/2:h 1:h 3/2:h 2:h 5/2:h 3:h 7/2:h", 4)
        self.assertEqual(env[0], {"K": (1, 3), "S": (1, 3), "h": (4, 12)})
        self.assertTrue(writer.drum_within("0:K 1/2:h 1:S 3/2:h 2:K 5/2:h 3:S 7/2:h", env))
        self.assertFalse(writer.drum_within("0:S 1/4:S 1/2:S 3/4:S 1:S 5/4:S 3/2:S 7/4:S", env))   # a snare roll for a hat bar
        self.assertFalse(writer.drum_within("0:K 1:S 2:K 3:S", env))                               # no hat at all
        self.assertFalse(writer.drum_within("0:K 1/2:h 1:S 3/2:h 2:K 5/2:h 3:S 7/2:h 0:c", env))   # a cymbal the bar lacks
        self.assertFalse(writer.drum_within("1/2:h 1:S 3/2:h 2:K 5/2:h 3:S 7/2:h", env))         # nothing on the one

    def test_drums_written(self):
        others = [self._kit_song("b"), self._kit_song("c", figure=((0.0, "k"), (2.0, "s"), (0.5, "h"), (1.5, "h"), (2.5, "h"), (3.5, "h")))]
        models = {g: writer.fit(rhythm.drum_group_units(others, g), name="drums-" + "".join(g)) for g in rhythm.DRUM_GROUPS
                  if rhythm.drum_group_units(others, g)}
        self.assertEqual(set(models), {("K", "S", "t"), ("h",)})
        s = self._kit_song()
        hits, figures = writer.drums(s, models, random.Random(1))
        self.assertEqual(len(figures), 4)
        for f in figures:
            self.assertIn(rhythm.drum_group(f, ("K", "S", "t")), models[("K", "S", "t")].table.vocabulary)
            self.assertIn(rhythm.drum_group(f, ("h",)), models[("h",)].table.vocabulary)
        self.assertTrue(all(letter in {"K", "S", "h"} for _, letter in hits))
        self.assertTrue(all(0.0 <= t < 16.0 for t, _ in hits))
        again, _ = writer.drums(s, models, random.Random(1))
        self.assertEqual(hits, again)
        self.assertEqual(rhythm.drum_group("0:K 0:h 1:S 3/2:h", ("K", "S", "t")), "0:K 1:S")
        self.assertEqual(rhythm.drum_group("0:K 0:h 1:S 3/2:h", ("c",)), "-")


class GeneratedSongTests(unittest.TestCase):
    def test_a_generated_song_is_read_and_its_bass_and_drums_written_from_tables(self):
        from bitcomposer.composer import compose_song
        from bitcomposer.translate import harness, packtables
        song = compose_song(seed=5, pack="ffvi")
        ctx = harness.load_generated(song, "seed 5", "test", seconds=30.0)
        self.assertIsNotNone(ctx)
        roles = {role for role, _ in ctx.by_voice.values()}
        self.assertIn("bass", roles)
        self.assertIn("drums", roles)
        self.assertTrue(ctx.song.bars)
        # the song's own bars as the pack's tables: enough to run the writers through the pack path
        models = packtables.read({"tables": {k: v for k, v in {
            "bass": packtables.fit("bass", rhythm.bass_units([ctx.song])),
            **{"drums-" + "".join(g): packtables.fit("drums-" + "".join(g), rhythm.drum_group_units([ctx.song], g))
               for g in rhythm.DRUM_GROUPS}}.items() if v is not None}})
        ctx.models = models
        bass = harness.write_bass(ctx, seed=1)
        drums = harness.write_drums(ctx, seed=1)
        self.assertIsNotNone(bass)
        self.assertTrue(bass.notes and bass.figures)
        self.assertIsNotNone(drums)
        self.assertTrue(drums.notes)
        new = harness.score_with(ctx, [bass, drums], "seed 5 new", ["test"])
        self.assertEqual(len([n for n in new.notes if n.voice in bass.replaced]), len(bass.notes))


class FreeWritingTests(unittest.TestCase):
    def test_a_free_manner_takes_any_known_figure_on_the_kit(self):
        m = writer.FreeManner({"0:R 2:5", "0:K 2:S", "1:h"}, kit={"K", "S"})
        self.assertTrue(m.fits("0:K 2:S"))
        self.assertFalse(m.fits("1:h"))                          # a piece the song lacks
        self.assertFalse(m.fits("0:R 1:R"))                      # a bar no song played
        self.assertTrue(writer.FreeManner({"0:R 2:5"}).fits("0:R 2:5"))
        self.assertEqual(writer.free_envelope("sparse walking no-octaves")("0:R", 4), (1, 3, False, 4))
        self.assertEqual(writer.free_envelope("dense roots octaves")("0:R", 3)[:2], (5, 16))
        env = writer.free_drum_envelope({"K", "S"})("0:K", 4)
        self.assertTrue(writer.drum_within("0:K 2:S 7/2:S", env))
        self.assertFalse(writer.drum_within("0:K 2:h", env))

    def test_form_spans_follow_the_parts_and_copy_a_repeat(self):
        song = rhythm.Song("t", 4, 4, [(4.0 * k, 4.0 * k + 4.0) for k in range(14)], [], numbers=list(range(14)),
                           parts=[(0, 8, None, "A"), (8, 4, None, "B"), (12, 2, None, "C")])
        own = ["0:R"] * 14
        self.assertEqual(writer.form_spans(song, own), [(0, 8, 4, None), (8, 4, 4, None), (12, 2, 2, None)])
        song.parts = [(0, 4, None, "A"), (4, 4, 0, "A"), (8, 4, None, "B"), (12, 2, None, "C")]
        self.assertEqual(writer.form_spans(song, own)[1], (4, 4, 4, 0))          # A again: copied from bar 0
        song.parts = [(0, 4, None, "A"), (4, 8, 0, "A")]                          # a repeat of another length: written anew
        self.assertEqual(writer.form_spans(song, own)[1], (4, 8, 4, None))
        self.assertEqual(writer.form_spans(song, own)[2:], [(12, 1, 1, None), (13, 1, 1, None)])


class UpperPartTests(unittest.TestCase):
    def test_a_stack_follows_the_width_and_the_register(self):
        scale = {0, 2, 4, 5, 7, 9, 11}
        self.assertEqual(writer.stack(["R", "3", "5"], 0, "", scale, 60, None), [60, 64, 67])
        self.assertEqual(writer.stack(["R", "5"], 7, "", scale, 60, None), [67, 74])
        self.assertEqual(writer.stack(["R", "sus"], 0, "sus4", scale, 60, None), [60, 65])
        self.assertEqual(writer.stack([], 0, "", scale, 60, None), [])
        self.assertEqual(writer.in_register(94, (58, 68)), 58)                  # a bell two octaves up comes back down
        self.assertEqual(writer.in_register(50, (58, 68)), 62)
        self.assertEqual(writer.in_register(66, (60, 64)), 54)                  # under an octave of room: just under the ceiling
        block = [(k * 0.5, 0.4, m, "x") for k in range(8) for m in (60.0, 64.0, 67.0)]
        arp = [(k * 0.5, 0.4, (60.0, 64.0, 67.0)[k % 3], "x") for k in range(9)]
        self.assertEqual(rhythm.upper_motion(block), 0.0)
        self.assertEqual(rhythm.upper_motion(arp), 1.0)
        self.assertEqual(writer.thinned((2, 6, False, 4), 0.5), (1, 3, False, 4))
        self.assertEqual(writer.thinned((2, 6, False, 4), 0.1), (1, 1, False, 4))
        self.assertEqual(writer.thinned((2, 6, False, 4), 1.4), (2, 6, False, 4))       # a loud bar does not thicken the part
        self.assertLess(writer.BREAKDOWN, 1.0)                                          # a bar a hair under the median is not a breakdown
        self.assertTrue(writer.voiced("R 3 +") and writer.voiced("sus 5"))
        self.assertFalse(writer.voiced("+") or writer.voiced(""))
        self.assertEqual(writer.sounding_pcs([(0.0, 1.0, 60.0, "x"), (1.0, 1.0, 62.0, "x")], 0.5), {0})
        self.assertEqual(writer.unclashed(61, [61, 64, 67], {0}), 64)                  # a C# against the tune's C moves to E
        self.assertEqual(writer.unclashed(61, [61, 64, 67], {3}), 61)                  # nothing a semitone away: stays
        self.assertFalse(writer.FreeManner({"0 1/12 1/2"}, division=4).fits("0 1/12 1/2"))   # a triplet figure off a sixteenth grid
        self.assertTrue(writer.FreeManner({"0 1/12 1/2"}, division=12).fits("0 1/12 1/2"))

    def test_the_upper_parts_of_a_generated_song_are_written_from_tables(self):
        from bitcomposer.composer import compose_song
        from bitcomposer.translate import harness, packtables
        for seed in range(1, 13):                                # a seed whose harmony sustains enough to voice
            song = compose_song(seed=seed, pack="ffvi")
            ctx = harness.load_generated(song, f"seed {seed}", "test", seconds=30.0)
            if ctx is not None and rhythm.voicing_units([ctx.song]):
                break
        songs = [ctx.song]
        entries = {"rhythm": packtables.fit("rhythm", [u for u in rhythm.units(songs) if u.values["part"] in rhythm.UPPER]),
                   "voicings": packtables.fit("voicings", rhythm.voicing_units(songs)),
                   "widths": packtables.fit("widths", rhythm.width_units(songs)),
                   "habits": packtables.fit("habits", rhythm.rhythm_habit_units(songs)),
                   "voicing_habits": packtables.fit("voicing_habits", rhythm.voicing_habit_units(songs)),
                   "motions": packtables.fit("motions", rhythm.upper_motion_units(songs))}
        self.assertTrue(all(v is not None for v in entries.values()), entries.keys())
        ctx.models = packtables.read({"tables": entries})
        w = harness.write_upper(ctx, seed=1)
        self.assertIsNotNone(w)
        self.assertEqual(w.part, "upper")
        self.assertTrue(w.notes and w.figures and w.replaced)
        self.assertTrue(all(n.voice in w.replaced for n in w.notes))
        new = harness.score_with(ctx, [w], "seed 5 upper", ["test"])
        self.assertEqual(len([n for n in new.notes if n.voice in w.replaced]), len(w.notes))
