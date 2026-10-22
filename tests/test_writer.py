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
        for s in others:
            s.notes["bass"] = [(4.0 * i + x, 0.5, 36.0, "k") for i in range(4) for x in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)]
        model = writer.fit(rhythm.bass_units(others))
        self.assertIsInstance(model, tables.Cache)
        notes, figures = writer.bass(_song(), model, random.Random(1), key=(0, "major"))
        self.assertEqual(len(figures), 4)
        self.assertTrue(all(writer.on_grid(f, 4) for f in figures))
        self.assertTrue(all(0.0 <= a < b <= 16.0 for a, b, _ in notes))
        self.assertTrue(all(36.0 <= m < 60.0 for _, _, m in notes))
        self.assertEqual(writer.sounded(_song().notes["bass"]), 0.4)
        again, _ = writer.bass(_song(), model, random.Random(1), key=(0, "major"))
        self.assertEqual(notes, again)                                        # the seed settles it
        self.assertTrue(writer.on_grid("0:R 1/2:r 3:5", 2))
        self.assertFalse(writer.on_grid("0:R 1/3:R", 4))
        self.assertTrue(writer.on_grid("-", 1))


if __name__ == "__main__":
    unittest.main()
