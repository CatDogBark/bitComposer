"""The bass writer: tones from marks, a figure realized, a bass written from a table."""
import random
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
        self.assertEqual((m.low, m.high, m.downbeat, m.feel), (3, 5, True, {1}))
        self.assertEqual((m.octaves, m.tones, m.pedal), (False, (2, 2), False))   # _song's bars: two tones each
        self.assertTrue(m.fits("0:R 1:5 2:R 3:5") and m.fits("0:R 1:R 2:5 3:5"))
        env = writer.envelope("0:R 1:R 2:5 3:5")                   # the song's own bar: four strikes, the one struck
        self.assertEqual(env, (2, 6, True))
        self.assertTrue(writer.within("0:R 1:5 2:R 3:5", env) and writer.within("0:R 2:5", env))
        self.assertFalse(writer.within("1:5 2:5 3:R", env))        # nothing on the one
        self.assertFalse(writer.within("0:R", env))                # too sparse for that bar
        self.assertFalse(writer.within("0:R 1/2:R 1:R 3/2:5 2:R 5/2:R 3:5 7/2:R", env))   # too dense for it
        self.assertEqual(writer.envelope("2:R"), (1, 1, False))    # a one-note bar off the one allows one note, anywhere
        self.assertFalse(m.fits("0:R 1/2:R 1:R 3/2:5 2:R 5/2:R 3:5 7/2:R"))   # eighths the song never plays
        self.assertFalse(m.fits("0:R 1:R 2:5 11/4:R"))             # a sixteenth the song never plays
        self.assertFalse(m.fits("0:R 4/3:5 5/3:R 2:R"))            # triplets the song never plays
        self.assertFalse(m.fits("-") or m.fits("0:R 3:5"))         # a rest; a bar no song played
        s = _song()
        s.division = 12                                             # a grid that holds triplets (a sixteenth grid would round them)
        s.notes["bass"] = [(4.0 * i + x, 0.3, 36.0 if x < 2 else 43.0, "k") for i in range(4) for x in (0.0, 1.0, 4 / 3, 5 / 3, 2.0)]
        m = writer.Manner(s, "bass", known)
        self.assertEqual((m.feel, m.low, m.high), ({1, 3}, 4, 6))
        self.assertTrue(m.fits("0:R 4/3:5 5/3:R 2:R"))
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
