"""The generator's song as a score (score.py) and the module the converter's back end makes of it
(phase 2 of docs/IDIOM.md), without the emulator. Run with: python3 -m unittest discover -s tests"""
import io
import math

from support import unittest  # noqa: F401
from bitcomposer.composer import compose_song  # noqa: E402
from bitcomposer import score as score_mod  # noqa: E402
from bitcomposer.spc import convert  # noqa: E402
from bitcomposer.translate import measures, reading  # noqa: E402


class Bridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.song = compose_song(seed=2, sound="ffvi")           # echo on: the slap
        cls.score = score_mod.of_song(cls.song)

    def test_every_voice_s_notes_are_there_in_seconds(self):
        s, song = self.score, self.song
        rows = measures.of_composed(song)                        # the yardsticks' count of the same rows
        self.assertEqual(s.voices, 12)
        self.assertGreaterEqual(len(s.notes), len(rows.notes))   # retriggers add notes, nothing drops them
        self.assertAlmostEqual(s.seconds, rows.seconds, places=3)
        first = min(s.notes, key=lambda n: n.start)
        self.assertGreaterEqual(first.start, 0.0)
        self.assertTrue(all(n.end is not None and n.end >= n.start for n in s.notes))
        self.assertEqual({n.voice for n in s.notes} - set(range(12)), set())

    def test_a_pitch_lands_on_a_whole_semitone_of_its_sample(self):
        # the converter's model plays a sample at 32 kHz for pitch 0x1000; a preset recorded for C-5 at its own
        # rate gets the register that plays that rate at midi 60, and whole semitones from there
        self.assertEqual(score_mod._pitch(32000, 60), 0x1000)
        self.assertEqual(score_mod._pitch(32000, 72), 0x2000)
        self.assertAlmostEqual(math.log2(score_mod._pitch(44100, 69) / score_mod._pitch(44100, 57)), 1.0, places=3)

    def test_the_echo_is_the_chip_s(self):
        s, info = self.score, self.song["info"]
        self.assertTrue(info["echo"])
        sending = [n for n in s.notes if n.echo]
        self.assertTrue(sending)
        self.assertTrue(all(0.016 <= n.echo_delay <= 0.240 for n in sending))
        self.assertEqual({round(n.echo_delay / 0.016) for n in sending}, {round(sending[0].echo_delay / 0.016)})
        self.assertAlmostEqual(sending[0].echo_feedback, info["echo_feedback"], places=2)
        voices_sending = {n.voice for n in sending}
        self.assertTrue(voices_sending <= {0, 1, 2, 3, 5})       # the melody, the harmony, the arp; not the bass or drums
        self.assertFalse(any(n.echo for n in s.notes if n.voice in (4, 6, 7, 8, 9, 10, 11)))

    def test_the_back_end_renders_it_within_it_s_channels(self):
        out = convert.render(self.score)
        info = out["info"]
        self.assertLessEqual(info["channels"], 64)
        self.assertGreaterEqual(info["notes"], 0.99 * len(self.score.notes))
        self.assertGreater(info["repeats"], 0)
        self.assertEqual(info["off_keys"], 0)
        self.assertEqual(len(out["samples"]), info["samples"])
        self.assertTrue(out["message"].startswith(self.song["name"]))

    def test_the_readers_read_it_as_they_read_a_game(self):
        r = reading.of_score(self.score, title=self.song["name"])
        self.assertIsNotNone(r.grid)
        ratio = r.grid.bpm / self.song["info"]["tempo"]              # the tempo, or its half or double (a level the ear allows)
        self.assertTrue(any(abs(ratio - k) <= 0.02 * k for k in (0.5, 1.0, 2.0)), ratio)
        self.assertTrue(r.chords)
        self.assertIn("melody", {x.role for x in r.roles})


if __name__ == "__main__":
    unittest.main()
