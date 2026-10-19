"""The translator: songs read as music (synthetic: no game files).
Run with: python3 -m unittest discover -s tests"""
import random

from support import unittest  # noqa: F401
from bitcomposer.translate import beat, events  # noqa: E402


def onsets(bpm, beats, per_beat=2, jitter=0.0, start=0.0, accent=(1.0,), seed=1):
    """Onsets on a grid: per_beat a beat, the first of each beat louder, a
    driver's timer jitter (uniform, in seconds)."""
    r = random.Random(seed)
    period = 60 / bpm
    out = []
    for b in range(beats):
        for k in range(per_beat):
            t = start + (b + k / per_beat) * period + r.uniform(-jitter, jitter)
            out.append((t, accent[b % len(accent)] if k == 0 else 0.4))
    return out


class Beat(unittest.TestCase):
    def test_a_steady_beat_through_timer_jitter(self):
        # eighths at 120 BPM, each onset off by up to 5 ms (AKAO's timer), 64 beats, the bar's first louder
        g = beat.find(onsets(120, 64, 2, jitter=0.005, accent=(1.0, 0.6, 0.8, 0.6)))
        self.assertAlmostEqual(g.bpm, 120, delta=0.5)
        self.assertEqual((g.division, g.meter), (2, 4))
        self.assertGreater(g.on_grid, 0.95)
        self.assertEqual(len(g.beat_times), 64)
        self.assertAlmostEqual(g.beats(g.beat_times[0] + 1.25), 2.5, places=1)

    def test_a_phase_jump_starts_a_section(self):
        # 32 beats, then a pause of a beat and a third (a fermata), then 32 more: two sections, every onset held
        first = onsets(100, 32, 2)
        later = onsets(100, 32, 2, start=first[-1][0] + 0.3 + 60 / 100 * 4 / 3)
        g = beat.find(first + later)
        self.assertEqual(len(g.sections), 2)
        self.assertGreater(g.on_grid, 0.95)
        self.assertAlmostEqual(g.bpm, 100, delta=0.5)

    def test_sixteenths_and_sextuplets_share_a_grid_of_twelfths(self):
        # Locke's: beats of four and beats of six, alternating
        period, out = 60 / 140, []
        for b in range(48):
            n = 4 if b % 2 == 0 else 6
            out += [(b * period + k * period / n, 1.0 if k == 0 else 0.5) for k in range(n)]
        g = beat.find(out)
        self.assertAlmostEqual(g.unit, period / 12, delta=0.0005)
        self.assertAlmostEqual(g.bpm, 140, delta=0.5)

    def test_free_time_has_no_beat(self):
        r = random.Random(3)
        t, out = 0.0, []
        for _ in range(80):
            t += r.uniform(0.15, 1.4)
            out.append((t, 1.0))
        self.assertIsNone(beat.find(out))


class Events(unittest.TestCase):
    def test_a_sample_s_notes_are_named_against_its_own_tuning(self):
        # notes 8 cents flat together are named on the semitone; the offset is the sample's
        self.assertAlmostEqual(events._offset([60.92, 64.92, 67.92]), -0.08, places=6)
        self.assertAlmostEqual(events._offset([60.1, 62.1]), 0.1, places=6)


if __name__ == "__main__":
    unittest.main()
