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
        notes, root = writer.realize("0:R 1/2:r 1:5 2:3 3:+", 0.0, 4.0, s, 36, 0.5, {0, 2, 4, 5, 7, 9, 11}, 0)
        self.assertEqual([(a, b, m) for a, b, m in notes], [(0.0, 0.25, 36.0), (0.5, 0.75, 48.0), (1.0, 1.5, 43.0), (2.0, 2.5, 40.0), (3.0, 3.5, 38.0)])
        self.assertEqual(root, 0)
        notes, root = writer.realize("0:R 2:7", 8.0, 12.0, s, 36, 1.0, set(), 0)   # the G minor seventh bar
        self.assertEqual([m for _, _, m in notes], [43.0, 41.0])
        self.assertEqual(root, 7)
        self.assertEqual(writer.realize("-", 0.0, 4.0, s, 36, 1.0, set(), 5), ([], 5))

    def test_a_bass_written_from_a_table(self):
        others = [_song("b"), _song("c")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(4) for x in (0.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        self.assertIsInstance(model, tables.Cache)
        notes, figures = writer.bass(_song(), model, random.Random(1), key=(0, "major"))
        self.assertEqual(len(figures), 4)
        self.assertTrue(all(writer.on_grid(f, 4) and f != "-" for f in figures))
        self.assertTrue(all(f in model.table.vocabulary for f in figures))        # only bars some song played
        self.assertTrue(all(len(rhythm._tokens(f)) <= 6 for f in figures))        # _song plays 4 a bar: at most 6
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
        others = [_song("b"), _song("c")]
        others[0].notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(4) for x in (0.0, 1.0, 2.0, 3.0)]
        others[1].notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(4) for x in (0.0, 2.0)]
        model = writer.fit(rhythm.bass_units(others))
        s = _song(bars=8)                                            # eight bars, the same figure in each: one span of period 1
        s.chords = [Span(0.0, 32.0, 0, "", 1.0)]                      # one chord, so the song's own figures repeat exactly
        _, figures = writer.bass(s, model, random.Random(3), key=(0, "major"))
        self.assertEqual(len(set(figures)), 1)
        s.notes["bass"] = [(4.0 * i + x, 0.4, 36.0, "k") for i in range(8) for x in ((0.0, 2.0) if i % 2 else (0.0, 1.0, 2.0, 3.0))]
        _, figures = writer.bass(s, model, random.Random(3), key=(0, "major"))   # a two-bar pattern through the song
        self.assertEqual(figures[0::2], [figures[0]] * 4)
        self.assertEqual(figures[1::2], [figures[1]] * 4)

    def test_the_songs_manner(self):
        known = {"0:R 1:R", "0:R 2:R", "0:R 1:R 2:R 3:R", "1:R", "0:R 1/2:R 1:R 3/2:R 2:R 5/2:R 3:R 7/2:R",
                 "0:R 1:R 2:R 11/4:R", "0:R 4/3:R 5/3:R 2:R", "0:R", "-"}
        m = writer.Manner(_song(), "bass", known)                 # quarters on every beat: 4 a bar, the one always struck
        self.assertEqual((m.low, m.high, m.downbeat, m.feel), (2, 6, True, {1}))
        self.assertTrue(m.fits("0:R 1:R") and m.fits("0:R 2:R") and m.fits("0:R 1:R 2:R 3:R"))
        self.assertFalse(m.fits("1:R"))                            # nothing on the one
        self.assertFalse(m.fits("0:R"))                            # too sparse
        self.assertFalse(m.fits("0:R 1/2:R 1:R 3/2:R 2:R 5/2:R 3:R 7/2:R"))   # too dense, and eighths
        self.assertFalse(m.fits("0:R 1:R 2:R 11/4:R"))             # a sixteenth the song never plays
        self.assertFalse(m.fits("0:R 4/3:R 5/3:R 2:R"))            # triplets the song never plays
        self.assertFalse(m.fits("-") or m.fits("0:R 3:R"))         # a rest; a bar no song played
        s = _song()
        s.division = 12                                             # a grid that holds triplets (a sixteenth grid would round them)
        s.notes["bass"] = [(4.0 * i + x, 0.3, 36.0, "k") for i in range(4) for x in (0.0, 1.0, 4 / 3, 5 / 3, 2.0)]
        m = writer.Manner(s, "bass", known)
        self.assertEqual(m.feel, {1, 3})
        self.assertTrue(m.fits("0:R 4/3:R 5/3:R 2:R"))


if __name__ == "__main__":
    unittest.main()
