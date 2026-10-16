"""Pattern operations: echo copies, fades, boundary cuts. Run with: python3 -m unittest discover -s tests"""
import unittest

from support import (it_format, pattern, unittest)  # noqa: F401



class PatternOps(unittest.TestCase):
    def _pat(self):
        return it_format.ITPattern(rows=64, channels=pattern.NUM_CHANNELS)

    def test_echo_copies_and_scales(self):
        pattern.RELEASE_INSTRUMENTS.clear()
        pat = self._pat()
        pat.data[0][0] = it_format.ITNote(note=60, instrument=1, volume=40)
        pat.data[8][0] = it_format.ITNote(note=it_format.NOTE_CUT)
        pat.data[62][0] = it_format.ITNote(note=62, instrument=1, volume=40)
        pattern.apply_echo(pat, 0, pattern.CH_ECHO1, 3, 0.5)
        self.assertEqual(pat.data[3][pattern.CH_ECHO1].volume, 20)
        self.assertEqual(pat.data[11][pattern.CH_ECHO1].note, it_format.NOTE_CUT)
        # a tap that would land past the pattern end is dropped, not wrapped
        self.assertEqual(pat.data[1][pattern.CH_ECHO1].note, 0)

    def test_fade_in_scales_volume_up(self):
        pat = self._pat()
        pat.data[0][0] = it_format.ITNote(note=60, instrument=1, volume=40)
        pat.data[12][0] = it_format.ITNote(note=60, instrument=1, volume=40)
        pattern.apply_fade(pat, 0, fade_in=True, rows_count=16)
        self.assertLess(pat.data[0][0].volume, pat.data[12][0].volume)
        self.assertLess(pat.data[12][0].volume, 40)

    def test_boundary_cut_is_in_place(self):
        pattern.RELEASE_INSTRUMENTS.clear()   # composed songs register theirs; not this one
        ringing = self._pat()
        ringing.data[60][0] = it_format.ITNote(note=60, instrument=1, volume=40)
        quiet = self._pat()
        pats = [ringing, quiet]
        pattern.silence_inactive_channels([0, 1], pats)
        self.assertEqual(len(pats), 2)
        self.assertEqual(quiet.data[0][0].note, it_format.NOTE_CUT)


if __name__ == "__main__":
    unittest.main()
