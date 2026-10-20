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

    def test_a_voice_keyed_late_all_song_long_is_heard_with_the_others(self):
        # Wild West's: two of four voices 18 ms behind, every note; their lag is taken out, not a grid of 18 ms
        r = random.Random(5)
        period, out = 60 / 92, []
        for b in range(96):
            for k in range(4):                                   # sixteenths, on time
                out.append((b * period + k * period / 4 + r.uniform(-0.004, 0.004), 0.3, 0))
            for k in range(2):                                   # eighths, on time
                out.append((b * period + k * period / 2 + r.uniform(-0.004, 0.004), 0.6, 1))
            out.append((b * period + 0.018 + r.uniform(-0.003, 0.003), 1.0 if b % 2 == 0 else 0.7, 2))
            for k in range(2):                                   # late eighths, the bass
                out.append((b * period + k * period / 2 + 0.018 + r.uniform(-0.003, 0.003), 0.8, 3))
        g = beat.find(sorted(out))
        self.assertAlmostEqual(g.bpm, 92, delta=0.5)
        self.assertEqual(set(g.lags), {2, 3})
        self.assertAlmostEqual(g.lags[2], 0.018, delta=0.003)

    def test_a_roll_on_no_grid_of_the_song_s_is_left_out(self):
        # The Phantom Train's wheels: five notes to an eighth, louder than its grid of sixteenths can take
        r = random.Random(6)
        eighth, out = 60 / 162, []
        for i in range(192):
            t = i * eighth
            out.append((t + r.uniform(-0.003, 0.003), 1.0 if i % 3 == 0 else 0.5, 0))
            if i % 2 == 0:
                out.append((t + r.uniform(-0.003, 0.003), 0.7, 1))
                out.append((t + eighth / 2 + r.uniform(-0.003, 0.003), 0.4, 2))
            out += [(t + k * eighth / 5 + r.uniform(-0.004, 0.004), 0.3, 3) for k in range(5)]
        g = beat.find(sorted(out))
        self.assertEqual(g.ornaments, {3})
        self.assertAlmostEqual(g.unit, eighth / 2, delta=0.002)

    def test_a_swing_no_grid_holds_is_followed_loosely(self):
        # Swanky's Swing's: eighths swung 62:38, each note placed by hand (up to 12 ms off), at 103
        r = random.Random(7)
        period, out = 60 / 103, []
        for b in range(96):
            t = b * period
            out.append((t + r.uniform(-0.012, 0.012), 0.6, 0))
            out.append((t + 0.62 * period + r.uniform(-0.012, 0.012), 0.4, 0))
            out.append((t + r.uniform(-0.008, 0.008), 0.8, 1))                  # the bass, on the beat
            if b % 2 == 0:
                out.append((t + r.uniform(-0.008, 0.008), 0.5, 2))              # chords, every other beat
        g = beat.find(sorted(out))
        self.assertTrue(g.loose)
        self.assertAlmostEqual(g.bpm, 103, delta=1.5)
        self.assertAlmostEqual(g.swing, 0.62, delta=0.04)

    def test_free_time_has_no_beat(self):
        r = random.Random(3)
        t, out = 0.0, []
        for _ in range(80):
            t += r.uniform(0.15, 1.4)
            out.append((t, 1.0))
        self.assertIsNone(beat.find(out))


class Bar(unittest.TestCase):
    def test_a_waltz_bass_sets_a_bar_of_three(self):
        # the accents gave four; the bass lands on every third beat (oom-pah-pah)
        g = beat.find(onsets(150, 48, 2, accent=(1.0, 0.7, 0.8, 0.7)))
        self.assertEqual(g.meter, 4)
        self.assertTrue(beat.rebar(g, [float(b) for b in range(1, 48, 3)]))
        self.assertEqual((g.meter, g.bar_times[0]), (3, g.beat_times[1]))

    def test_a_bass_on_every_beat_leaves_the_bar(self):
        g = beat.find(onsets(150, 48, 2, accent=(1.0, 0.7, 0.8, 0.7)))
        self.assertFalse(beat.rebar(g, [float(b) for b in range(48)]))

    def test_eighths_in_threes_of_twos_or_twos_of_threes(self):
        # one stream of eighths, its accents 3/4's (Kids Run Through the City) or 6/8's (dotted-quarter beats);
        # a loud downbeat makes the 3/4 louder every three eighths than every two, but it repeats every six
        def bars(accents, eighth, n=48):
            return [(i * eighth, accents[i % 6]) for i in range(6 * n)]
        g = beat.find(bars((1.6, 0.3, 0.5, 0.3, 0.5, 0.3), 60 / 220))
        self.assertEqual((round(g.bpm), g.division, g.meter), (110, 2, 3))
        g = beat.find(bars((1.0, 0.3, 0.3, 0.7, 0.3, 0.3), 60 / 330))
        self.assertEqual((round(g.bpm), g.division), (110, 3))

    def test_a_bass_of_three_three_and_two_still_beats_in_twos(self):
        # The Decisive Battle's: sixteenths, the bass and a chord on 0, 3 and 6 of eight, louder every three
        # eighths than every two; the pattern repeats every eight sixteenths (and so every twelve eighths too)
        sixteenth, out = 60 / 104 / 4, []
        for i in range(16 * 32):
            out.append((i * sixteenth, 0.4, 0))
            if i % 8 in (0, 3, 6):
                out += [(i * sixteenth, 1.0, 1), (i * sixteenth, 0.5, 2)]
        g = beat.find(sorted(out))
        self.assertEqual((round(g.bpm), g.division, g.meter), (104, 4, 4))

    def test_the_beat_holds_as_many_notes_as_a_tapped_one(self):
        # quarter notes at 160 and a bass every other one: heard at 80 (Kefka); add sixteenths: at 160 (Terra)
        q, tune = 60 / 160, []
        for i in range(128):
            tune.append((i * q, 1.0 if i % 2 == 0 else 0.7, 0))
            if i % 2 == 0:
                tune.append((i * q, 0.8, 1))
        self.assertAlmostEqual(beat.find(sorted(tune)).bpm, 80, delta=0.5)
        busy = tune + [(i * q / 4, 0.3, 2) for i in range(128 * 4)]
        self.assertAlmostEqual(beat.find(sorted(busy)).bpm, 160, delta=0.5)


def song_of(parts):
    """A Song from {voice: [(start, length, midi or None), ...]} at full level, centred."""
    from bitcomposer.translate.events import Played, Sample, Song
    samples = {}
    notes = []
    for v, ns in parts.items():
        s = samples.setdefault(v, Sample((v * 0x100, v * 0x100), f"s{v}", 440.0 if ns[0][2] is not None else None, 100, True))
        notes += [Played(v, t, t + n, s, m, 0.8, 0.5, None) for t, n, m in ns]
    notes.sort(key=lambda p: (p.start, p.voice))
    return Song("test", 30.0, notes, samples)


class Parts(unittest.TestCase):
    def test_drums_bass_melody_and_held_chords(self):
        from bitcomposer.translate import harmony, roles
        b = 0.5                                       # 120 BPM
        tune = [72, 74, 76, 77, 79, 77, 76, 74, 72, 71, 72, 74, 76, 74, 72, 67]
        song = song_of({
            0: [(i * b, 0.4, tune[i % 16]) for i in range(64)],                    # the melody, stepwise, on top
            1: [(i * 4 * b, 4 * b, m) for i, m in enumerate([60, 60, 57, 55] * 4)],  # held chords' root
            2: [(i * 4 * b, 4 * b, m) for i, m in enumerate([64, 64, 60, 59] * 4)],
            3: [(i * 2 * b, 2 * b, m) for i, m in enumerate([36, 36, 36, 36, 33, 33, 31, 31] * 4)],  # bass
            4: [(i * b / 2, 0.05, None) for i in range(128)],                      # drums: no pitch
        })
        g = beat.find([(p.start, p.level) for p in song.notes])
        parts = {r.voice: r.role for r in roles.assign(song, g)}
        self.assertEqual(parts, {0: roles.MELODY, 1: roles.HARMONY, 2: roles.HARMONY, 3: roles.BASS, 4: roles.DRUMS})
        tonic, mode, _ = harmony.key(song, g, roles.assign(song, g))
        self.assertEqual((harmony.NAMES[tonic], mode), ("C", "major"))
        first = harmony.chords(song, g, roles.assign(song, g))[0]
        self.assertEqual((first.name, first.end - first.start), ("C", 8))

    def test_a_voice_playing_another_s_notes_is_its_double(self):
        from bitcomposer.translate import roles
        b = 0.5
        line = [(i * b, 0.4, 60 + (i * 5) % 12) for i in range(48)]
        song = song_of({0: line, 1: [(t + 0.12, n, m + 12) for t, n, m in line],    # 0.12 s late, an octave up
                        2: [(i * 2 * b, 2 * b, 36 + (i % 3)) for i in range(24)]})
        g = beat.find([(p.start, p.level) for p in song.notes if p.voice != 1])
        double = [r for r in roles.assign(song, g) if r.voice == 1][0]
        self.assertEqual((double.role, double.of), (roles.DOUBLE, 0))


class Form(unittest.TestCase):
    """A song's parts and loop, from where it repeats itself."""

    @staticmethod
    def song_in_parts(order, jitter=0.004, seed=8):
        """A song at 120 (bars of two seconds) played part by part: an intro of two bars, A and B of four,
        each a melody of its own (a note a beat), a bass on each bar's first beat and a drum every half
        beat, each note up to `jitter` off its time (AKAO's timer)."""
        r = random.Random(seed)
        tunes = {"I": [60, 62, 64, 65], "A": [67, 65, 64, 62, 60, 62, 64, 67], "B": [72, 71, 69, 67, 69, 71, 72, 74]}
        tunes["C"] = tunes["B"]                                       # B with a bar more: another ending
        bars = {"I": 2, "A": 4, "B": 4, "C": 5}
        parts = {0: [], 1: [], 2: []}
        t = 0.0
        for name in order:
            for bar in range(bars[name]):
                for beat in range(4):
                    at = t + bar * 2 + beat * 0.5
                    j = lambda: r.uniform(-jitter, jitter)
                    parts[0].append((at + j(), 0.4, tunes[name][(bar * 4 + beat) % len(tunes[name])]))
                    parts[2] += [(at + j(), 0.05, None), (at + 0.25 + j(), 0.05, None)]
                parts[1].append((t + bar * 2 + j(), 1.8, {"I": 36, "A": 43, "B": 41, "C": 41}[name] + bar % 2))
            t += bars[name] * 2
        for v in parts:
            parts[v].sort()
        return song_of(parts)

    def test_a_loop_and_its_parts(self):
        from bitcomposer.translate import form
        song = self.song_in_parts("IABABAB")
        g = beat.find([(p.start, p.level, p.voice) for p in song.notes])
        f = form.read(song, g)
        self.assertEqual((f.loop_bar, f.loop_bars), (2, 8))          # back to the first A, eight bars a pass
        self.assertEqual([(p.label, p.bar, p.bars) for p in f.parts], [("A", 0, 2), ("B", 2, 4), ("C", 6, 4)])

    def test_a_loop_whose_second_time_through_runs_a_bar_longer(self):
        # Kefka's: the second time round one part has a bar more, everything after it a bar later
        from bitcomposer.translate import form
        song = self.song_in_parts("IABACA")
        f = form.read(song, beat.find([(p.start, p.level, p.voice) for p in song.notes]))
        self.assertEqual((f.loop_bar, f.loop_bars), (2, 8))

    def test_a_part_played_again_has_its_letter_and_no_loop_is_heard_once(self):
        from bitcomposer.translate import form
        song = self.song_in_parts("IAAB")
        f = form.read(song, beat.find([(p.start, p.level, p.voice) for p in song.notes]))
        self.assertIsNone(f.loop_bar)
        self.assertEqual(f.letters, "A B B C")


class Events(unittest.TestCase):
    def test_a_sample_s_notes_are_named_against_its_own_tuning(self):
        # notes 8 cents flat together are named on the semitone; the offset is the sample's
        self.assertAlmostEqual(events._offset([60.92, 64.92, 67.92]), -0.08, places=6)
        self.assertAlmostEqual(events._offset([60.1, 62.1]), 0.1, places=6)


if __name__ == "__main__":
    unittest.main()
