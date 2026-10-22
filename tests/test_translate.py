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

    def test_the_bar_s_phase_follows_where_the_song_repeats(self):
        # a four-bar phrase at 120 played four times: a melody a note a beat, a chord held through each bar from
        # its first beat, a drum on every beat and two more on every third, which the accents take for the one
        from bitcomposer.translate import phase
        b = 0.5
        tune = [60, 62, 64, 65, 67, 69, 71, 72, 74, 72, 71, 69, 67, 65, 64, 62]
        song = song_of({
            0: [(i * b, 0.4, tune[i % 16]) for i in range(64)],
            1: [(k * 4 * b, 4 * b, 48) for k in range(16)],
            2: [(i * b, 0.05, None) for i in range(64)],
            3: [((k * 4 + 2) * b, 0.05, None) for k in range(16)],
            4: [((k * 4 + 2) * b, 0.05, None) for k in range(16)],
        })
        g = beat.find([(p.start, p.level) for p in song.notes])
        self.assertEqual((round(g.bpm), g.meter), (120, 4))
        self.assertAlmostEqual(g.bar_times[0], g.beat_times[2], places=3)      # the accents' one: the third beat
        self.assertTrue(phase.find(g, song))
        self.assertAlmostEqual(g.bar_times[0], g.beat_times[0], places=3)      # the phrase's: the first
        self.assertEqual(len(g.bar_times), 16)

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

    def test_chords_change_by_the_bar_and_carry_through_a_rest(self):
        # eight bars at 120: C held two bars, the chord voices resting a bar, C two bars more, then F two bars and
        # the bass alone on F for the last: one C of five bars (a chord that stops and restarts is one chord), one F
        from bitcomposer.translate import harmony, roles
        b = 0.5
        tune = [72, 74, 76, 77, 79, 77, 76, 74]
        held = lambda bars, midi: [(k * 4 * b, 4 * b, midi) for k in bars]
        song = song_of({
            0: [(i * b, 0.4, tune[i % 8]) for i in range(32)],
            1: held((0, 1, 3, 4), 64) + held((5, 6), 69),
            2: held((0, 1, 3, 4), 67) + held((5, 6), 72),
            3: [n for k in range(5) for n in ((k * 4 * b, 2 * b, 36), (k * 4 * b + 2 * b, 2 * b, 43))]       # root and fifth
               + [n for k in (5, 6, 7) for n in ((k * 4 * b, 2 * b, 41), (k * 4 * b + 2 * b, 2 * b, 48))],
            4: [(i * b / 2, 0.05, None) for i in range(64)],
        })
        g = beat.find([(p.start, p.level) for p in song.notes])
        rl = roles.assign(song, g)
        self.assertEqual({r.voice: r.role for r in rl if r.voice in (1, 3)}, {1: roles.HARMONY, 3: roles.BASS})
        cs = harmony.chords(song, g, rl)
        self.assertEqual([(c.name, c.start, c.end, c.stated) for c in cs], [("C", 0, 20, True), ("F", 20, 32, True)])

    def test_a_bass_figure_under_a_tune_is_one_implied_chord(self):
        # Underground Castle's kind: a bass on D with a C under it every bar, a tune on top, no chord voice at all
        from bitcomposer.translate import harmony, roles
        b = 0.5
        tune = [62, 65, 69, 72, 74, 72, 69, 65]
        song = song_of({
            0: [(i * b, 0.4, tune[i % 8]) for i in range(64)],
            1: [n for k in range(16) for n in ((k * 4 * b, 3 * b, 38), (k * 4 * b + 3 * b, b, 36))],
            2: [(i * b / 2, 0.05, None) for i in range(128)],
        })
        g = beat.find([(p.start, p.level) for p in song.notes])
        cs = harmony.chords(song, g, roles.assign(song, g))
        self.assertEqual(len(cs), 1)
        self.assertEqual((cs[0].root, cs[0].stated, cs[0].start, cs[0].end), (2, False, 0, 64))


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
        # at the scale of sections, a four-bar part played twice at once is one section
        self.assertEqual([(p.label, p.bar, p.bars) for p in f.sections], [("A", 0, 2), ("B", 2, 8), ("C", 10, 4)])


class Events(unittest.TestCase):
    def test_a_sample_s_notes_are_named_against_its_own_tuning(self):
        # notes 8 cents flat together are named on the semitone; the offset is the sample's
        self.assertAlmostEqual(events._offset([60.92, 64.92, 67.92]), -0.08, places=6)
        self.assertAlmostEqual(events._offset([60.1, 62.1]), 0.1, places=6)


def tone(hz, seconds, rate=32000, noise=0.0, decay=None, seed=3):
    """A sine (and noise) as 16-bit samples, falling away over `decay` seconds if given."""
    import math
    from array import array
    r = random.Random(seed)
    out = array("h")
    for i in range(int(seconds * rate)):
        env = math.exp(-i / rate / decay) if decay else 1.0
        out.append(int(20000 / (1 + noise) * env * (math.sin(2 * math.pi * hz * i / rate) + r.uniform(-noise, noise))))
    return out


class Pack(unittest.TestCase):
    """A thin pack from a game's readings (no game files: what the readings counted, made up)."""

    @staticmethod
    def gathered():
        from bitcomposer.translate import pack, roles as R
        g = pack.Gathered(game="Test Quest", songs=4)
        g.uses[R.MELODY].update({"flute": 60, "oboe": 30, "bell": 1})   # the bell plays too little of it
        g.uses[R.ARP].update({"harp": 40, "hat": 5})                    # the hat read as an arp in a song
        g.uses[R.BASS].update({"bass": 80})
        g.uses[R.DRUMS].update({"hat": 200, "kick": 150, "snare": 120})
        g.f0 = {"flute": 440.0, "oboe": 220.0, "bell": 880.0, "harp": 261.63, "bass": 110.0}
        for k in ("hat", "kick", "snare"):
            g.pitches[k][0x1000] = 9
        g.tempos.update({"slow": 1, "medium": 2, "fast": 1})
        g.modes.update({"minor": 3, "major": 1})
        g.drumless = 1
        # echo on in three songs of four: a slap at 100 BPM (0.5 rows: 75 ms), a quarter, another slap
        g.echo = [(True, 0.5, 0.6, 0.5), (True, 4.1, 0.7, 0.9), (True, 0.45, 0.5, 0.2), (False, None, 0.0, 0.0)]
        return g

    def test_each_pool_takes_the_samples_its_part_is_played_with_most(self):
        from bitcomposer.translate import pack
        p = pack.pools(self.gathered())
        self.assertEqual(p["lead"], ["flute"] * 4 + ["oboe"] * 2)      # repeated by their share; no bell
        self.assertEqual(p["arp"], ["harp"] * 4)                        # a drum the game plays is no arp
        self.assertEqual(p["bass_heavy"], p["bass_light"])

    def test_the_kit_by_brightness_and_ring(self):
        from collections import Counter
        from bitcomposer.translate import pack
        g = self.gathered()
        sounds = {"kick": (tone(55, 0.2, decay=0.05), 32000), "snare": (tone(200, 0.2, noise=0.5, decay=0.05), 32000),
                  "hat": (tone(3000, 0.1, noise=1.5, decay=0.02), 32000)}
        self.assertEqual(pack.kit(g, sounds), {"kick": "kick", "hihat": "hat", "snare": "snare"})
        g.uses["drums"]["crash"] = 20                                   # a long bright one: the crash
        sounds["crash"] = (tone(2500, 1.5, noise=2.0, decay=0.6), 32000)
        self.assertEqual(pack.kit(g, sounds), {"kick": "kick", "hihat": "hat", "crash": "crash", "snare": "snare"})
        g.uses["drums"] = Counter({"kick": 9, "snare": 9})               # two drums: a kick and a snare
        self.assertEqual(pack.kit(g, sounds), {"kick": "kick", "snare": "snare"})

    def test_the_habits_the_readings_give_straight(self):
        from bitcomposer.translate import pack
        h = pack.habits(self.gathered())
        self.assertEqual(h["tempo"], {"slow": 1, "medium": 2, "fast": 1})
        self.assertEqual(h["scale_family"], {"minor": 3, "major": 1, "pentatonic": 0})
        self.assertEqual(h["drumless"], 0.25)
        self.assertEqual(h["echo"], 0.75)
        self.assertEqual(h["echo_delay"], {"slap": 2, "row": 0, "eighth": 0, "dotted": 0, "quarter": 1})
        self.assertEqual(h["echo_wet"], {"light": 1, "normal": 1, "wet": 1})
        lo, hi = h["echo_feedback"]
        self.assertTrue(0.5 <= lo <= hi <= 0.7)

    def test_a_pack_made_loads_and_composes(self):
        import tempfile
        from pathlib import Path
        from bitcomposer.composer import compose_song
        from bitcomposer.packs import PACKS, packfile
        from bitcomposer.translate import pack
        g = self.gathered()
        sounds = {"flute": 440, "oboe": 220, "bell": 880, "harp": 261.63, "bass": 110,
                  "kick": 55, "snare": 200, "hat": 3000}

        def decode(k):
            pcm = tone(sounds[k], 0.25, noise=0.0 if g.f0.get(k) else 1.0, decay=None if g.f0.get(k) else 0.05)
            return pcm, ((len(pcm) - 3200, len(pcm)) if g.f0.get(k) else None)
        data, files = pack.build(g, decode, "test_quest_spc")
        self.assertEqual(data["voices"]["lead"], ["sflute"] * 4 + ["soboe"] * 2)
        self.assertEqual(data["samples"]["sflute"]["note"], 69.0)
        self.assertEqual(data["samples"]["sbass"]["release"], "bass")
        self.assertTrue(data["samples"]["skick"]["percussion"])
        with tempfile.TemporaryDirectory() as d:
            name = packfile.load_pack_file(pack.write(data, files, Path(d)))
            self.addCleanup(packfile.unload, name)
            self.assertIn(name, PACKS)
            song = compose_song(seed=1, pack=name)
            self.assertTrue(song["patterns"])


class Archives(unittest.TestCase):
    """A game's SPC files from a folder, a zip, or a set an archive program unpacks."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def test_a_folder_gives_its_own_files(self):
        from bitcomposer.translate import archives
        game = self.d / "Test Quest"
        (game / "extras").mkdir(parents=True)
        for f in ("01 Title.spc", "02 Field.SPC", "notes.txt", "extras/99 Unused.spc"):
            (game / f).write_bytes(b"SNES-SPC700")
        self.assertEqual([f.name for f in archives.spc_files([game], self.d / "unpacked")],
                         ["01 Title.spc", "02 Field.SPC"])                  # the folder's own, any case

    def test_a_zip_gives_every_one_in_it(self):
        import zipfile
        from bitcomposer.translate import archives
        zipped = self.d / "Test Quest.zip"
        with zipfile.ZipFile(zipped, "w") as z:
            z.writestr("Test Quest/01 Title.spc", b"one")
            z.writestr("Test Quest/disc 2/01 Title.spc", b"two")         # the same name in a folder of its own
            z.writestr("../../02 Escape.spc", b"three")                  # named out of the zip: lands inside
            z.writestr("Test Quest/info.txt", b"x")
        files = archives.spc_files([zipped], self.d / "unpacked")
        self.assertEqual([f.name for f in files], ["02 Escape.spc", "01 Title.spc", "01 Title (2).spc"])
        self.assertTrue(all(f.parent == self.d / "unpacked" / "Test Quest" for f in files))
        self.assertEqual(sorted(f.read_bytes() for f in files), [b"one", b"three", b"two"])
        (self.d / "broken.zip").write_bytes(b"not a zip")
        with self.assertRaises(ValueError):
            archives.spc_files([self.d / "broken.zip"], self.d / "unpacked")

    def seven_zip(self):
        """A .7z set (what an .rsn's RAR goes through the same way), made by 7-Zip."""
        import shutil
        import subprocess
        exe = shutil.which("7z") or shutil.which("7zz")
        if not exe:
            self.skipTest("no 7-Zip here")
        src = self.d / "src"
        (src / "disc 2").mkdir(parents=True)
        for f, data in (("01 Title.spc", b"one"), ("disc 2/01 Title.spc", b"two"), ("info.txt", b"x")):
            (src / f).write_bytes(data)
        out = self.d / "Test Quest.7z"
        subprocess.run([exe, "a", "-bd", str(out), "."], cwd=src, check=True, capture_output=True)
        return out

    def test_a_set_unpacked_by_7_zip(self):
        from bitcomposer.translate import archives
        files = archives.spc_files([self.seven_zip()], self.d / "unpacked")
        self.assertEqual([f.name for f in files], ["01 Title.spc", "01 Title (2).spc"])
        self.assertEqual([f.read_bytes() for f in files], [b"one", b"two"])
        self.assertEqual(sorted(p.name for p in (self.d / "unpacked").iterdir()), ["Test Quest"])   # nothing left over

    def test_a_set_unpacked_by_unar(self):
        import shutil
        from bitcomposer.translate import archives
        if not (shutil.which("unar") and shutil.which("lsar")):
            self.skipTest("no unar here")
        files = archives.unpack(self.seven_zip(), self.d / "unpacked" / "Test Quest", ("unar", shutil.which("unar")))
        self.assertEqual(sorted(f.read_bytes() for f in files), [b"one", b"two"])

    def test_without_an_archive_program_it_says_what_to_install(self):
        from bitcomposer.translate import archives
        original = archives.program
        archives.program = lambda: None
        self.addCleanup(setattr, archives, "program", original)
        (self.d / "Test Quest.rsn").write_bytes(b"Rar!")
        with self.assertRaisesRegex(ValueError, "7-Zip or unar"):
            archives.spc_files([self.d / "Test Quest.rsn"], self.d / "unpacked")


class Measures(unittest.TestCase):
    """The yardsticks read from notes: a reading's and a generated song's alike."""

    def test_a_score_s_melody_harmony_and_bars(self):
        from bitcomposer.translate.measures import Note, Score, measure
        notes = []
        tune = [(0, 72), (1, 74), (2, 76), (3, 77)]                  # a bar of quarters, played twice
        for bar in (0, 4):
            notes += [Note(bar + b, 1, m, "melody", 0) for b, m in tune]
            notes.append(Note(bar, 4, 48, "bass", 1))
            notes += [Note(bar, 4, m, "harmony", v) for v, m in ((2, 60), (3, 64), (4, 67))]
        notes.append(Note(8 + 1 / 3, 1, 79, "melody", 0))            # and a triplet's second note
        notes.append(Note(8, 1, None, "drums", 5))
        notes.sort(key=lambda n: n.beat)
        m = measure(Score(notes, [0, 4, 8], 12, 120, 6))
        self.assertEqual(m["melody_per_beat"], 9 / 12)
        self.assertEqual(m["mel_step_pct"], 100 * 7 / 8)            # C D E F, C D E F G: a leap back, the rest steps
        self.assertEqual(m["mel_bar_repeat_pct"], 100 / 3)          # the second bar of three
        self.assertEqual(m["mel_strong_fit_pct"], 100)              # C over C on beats one, E over C on beats three
        self.assertEqual(m["chord_tones"], 3)
        self.assertEqual(m["triplet_pct"], 100)
        self.assertEqual(m["drums_per_bar"], 1 / 3)

    def test_a_tune_heard_again_off_the_bar_lines_is_a_repeat(self):
        # Kefka's: a tune of two bars from a bar line, and again from a bar line's second beat (a bar read a
        # beat off): its three bars the second time are each a bar's length of it from an earlier beat
        from bitcomposer.translate.measures import Note, Score, measure
        tune = [60, 62, 64, 65, 67, 69, 71, 72]
        notes = [Note(4 + b, 1, m, "melody", 0) for b, m in enumerate(tune)]
        notes += [Note(17 + b, 1, m, "melody", 0) for b, m in enumerate(tune)]
        m = measure(Score(notes, [0, 4, 8, 12, 16, 20, 24], 28, 120, 14))
        self.assertEqual(m["mel_bar_repeat_pct"], 60)               # bars from 16, 20 and 24, of five with notes
        self.assertEqual(m["bar_repeat_pct"], 60)

    def test_a_composed_song_by_its_channel_layout(self):
        from bitcomposer.it_format import FX_SPECIAL, ITNote, ITPattern, NOTE_CUT
        from bitcomposer.translate.measures import of_composed
        pat = ITPattern(rows=16, channels=19)
        pat.data[0][0] = ITNote(note=72, instrument=1, volume=64)
        pat.data[4][0] = ITNote(note=74, instrument=1, volume=64, effect=FX_SPECIAL, effect_val=0xD3)
        pat.data[8][0] = ITNote(note=NOTE_CUT)
        pat.data[2][12] = ITNote(note=72, instrument=1, volume=30)   # the echo: left out
        pat.data[0][6] = ITNote(note=60, instrument=2, volume=64)    # a kick
        s = of_composed({"patterns": [pat], "orders": [0, 0, 255], "speed": 6, "tempo": 120})
        self.assertEqual(s.bpm, 120)
        self.assertEqual(s.bars, [0, 4])
        self.assertEqual(s.end, 8)
        mel = [(n.beat, n.beats, n.midi) for n in s.notes if n.group == "melody"]
        self.assertEqual(mel, [(0, 1.125, 72), (1.125, 0.875, 74), (4, 1.125, 72), (5.125, 0.875, 74)])
        self.assertEqual([(n.beat, n.midi) for n in s.notes if n.group == "drums"], [(0, None), (4, None)])


class Vocab(unittest.TestCase):
    """The harmony vocabulary counted from readings made up here: chord moves and voicings."""

    def test_numerals_in_the_key_keep_the_shape(self):
        from bitcomposer.translate.vocab import degree, numeral
        c = 0
        self.assertEqual([numeral(r, c, "major", s) for r, s in ((0, ""), (5, ""), (7, "7"), (2, "m7"), (10, ""),
                                                                 (11, "dim"), (6, ""), (9, "m"), (0, "5"), (0, "maj7"))],
                         ["I", "IV", "V7", "ii7", "bVII", "viidim", "#IV", "vi", "I5", "Imaj7"])
        a = 9
        self.assertEqual([numeral(r, a, "minor", s) for r, s in ((9, "m"), (7, ""), (8, "dim"), (5, ""), (4, ""),
                                                                 (2, "m"), (11, "m7b5"), (10, ""))],
                         ["i", "VII", "#viidim", "VI", "V", "iv", "ii7b5", "bII"])
        self.assertEqual([degree(n) for n in ("ii7", "bVII", "#viidim", "Isus4", "ii7b5", "Imaj7")],
                         ["II", "bVII", "#VII", "I", "II", "I"])

    def test_a_known_progression_gives_its_moves(self):
        from bitcomposer.translate.vocab import Song, Span, moves
        # C major: C F G7 C Am F, a silent beat, then C (no move across silence), then an unfit span
        major = Song("major", 0, "major", [Span(0, 4, 0, "", 0.9), Span(4, 6, 5, "", 0.9), Span(6, 8, 7, "7", 0.9),
                                            Span(8, 12, 0, "", 0.9), Span(12, 14, 9, "m", 0.9), Span(14, 16, 5, "", 0.9),
                                            Span(16, 17, None, "", 0.0), Span(17, 18, 0, "", 0.9),
                                            Span(18, 19, 2, "m", 0.3), Span(19, 20, 7, "", 0.9)])
        minor = Song("minor", 9, "minor", [Span(0, 2, 9, "m", 0.9), Span(2, 4, 2, "m", 0.9), Span(4, 6, 4, "", 0.9),
                                            Span(6, 8, 9, "m", 0.9), Span(8, 10, 2, "m", 0.9)])
        rows = {(m, a, b): (n, beats, held) for m, a, b, n, beats, held in moves([major, minor])}
        self.assertEqual(rows, {
            ("major", "I", "IV"): (1, 2, 2), ("major", "IV", "V7"): (1, 2, 2), ("major", "V7", "I"): (1, 4, 4),
            ("major", "I", "vi"): (1, 2, 2), ("major", "vi", "IV"): (1, 2, 2),
            ("minor", "i", "iv"): (2, 4, 2), ("minor", "iv", "V"): (1, 2, 2), ("minor", "V", "i"): (1, 2, 2)})
        self.assertEqual([r[1:3] for r in moves([major, minor])][0], ("i", "iv"))   # the most counted first

    def test_a_known_voicing_gives_its_tones_inversion_and_roles(self):
        from bitcomposer.translate.vocab import Song, Span, voicings
        # four beats of C major: the bass on E (first inversion), G C E held above, the melody on G then A;
        # then two beats of G5 struck staccato (G and D alternating, a fifth of a beat each), no bass
        s = Song("test", 0, "major", [Span(0, 4, 0, "", 0.9), Span(4, 6, 7, "5", 0.9)], {
            "bass": [(0, 4, 40)],
            "accompaniment": [(0, 4, 55), (0, 4, 60), (0, 4, 64)] + [(4 + i / 2, 0.2, 55 if i % 2 == 0 else 62) for i in range(4)],
            "melody": [(0, 3, 67), (3, 1, 69)],
        })
        v = voicings([s])
        self.assertEqual((v.songs, v.spans), (1, 2))
        self.assertEqual(v.tones, {"R 3 5": 1, "R 5": 1})
        self.assertEqual(v.inversion, {"third": 1, "root": 1})
        self.assertEqual((v.spread, v.spread_upper, v.sounding), ([24, 7], [9, 7], [4, 2]))
        self.assertEqual(v.by_role["bass"], {"third": 4})
        self.assertEqual(v.by_role["accompaniment"], {"root": 5, "third": 4, "fifth": 5})   # the struck ones an eighth each
        self.assertEqual(v.by_role["melody"], {"fifth": 3, "other": 1})
        self.assertEqual((v.above_bass, v.above_top), ([27.5], [3.5]))

    def test_songs_load_once_through_and_the_rest_are_left_out(self):
        from array import array
        from bitcomposer.translate import store
        from bitcomposer.translate.vocab import load
        db = store.connect(":memory:")
        row = lambda sid, bpm, tonic, loop: (sid, "", "", "Test Quest", sid, "", None, 8.0, store.VERSION, bpm, 4, 2,
                                             1.0, 0.5, tonic, "major" if tonic is not None else None, 0.8, 0,
                                             loop, 2 if loop is not None else None, 2.0 if loop is not None else None)
        for args in (("beat", 120.0, 0, 1), ("free", None, None, None), ("nokey", 120.0, None, None), ("quiet", 120.0, 0, None)):
            db.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row(*args))
        # 16 beats of half a second, bars of four; the song loops from bar two for two seconds: beat 8
        db.execute("INSERT INTO beats VALUES (?,?,?)", ("beat", array("d", [b / 2 for b in range(16)]).tobytes(),
                                                       array("d", [0.0, 2.0, 4.0, 6.0]).tobytes()))
        for sid in ("beat", "nokey"):
            for a, b, root in ((0, 4, 0), (4, 8, 5), (8, 12, 7), (12, 16, 0)):
                db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", (sid, a, b, root, "", 0.9))
        db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", ("quiet", 0, 12, None, "", 0.0))
        db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", ("quiet", 12, 16, 0, "", 0.9))
        notes = array("f", [0, 4, 36, 0.5, 0.5, 0, 4, 4, 41, 0.5, 0.5, 0, 8, 4, 43, 0.5, 0.5, 0,
                            12, float("nan"), 36, 0.5, 0.5, 0])
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", ("beat", 0, "bass", None, None, notes.tobytes()))
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", ("beat", 1, "drums", None, None, notes.tobytes()))
        songs, left_out = load(db)
        self.assertEqual(left_out, {"free time": 1, "no key": 1, "unfit": 1})
        self.assertEqual([s.title for s in songs], ["beat"])
        self.assertEqual([(c.start, c.end, c.root) for c in songs[0].chords], [(0, 4, 0), (4, 8, 5)])
        self.assertEqual(songs[0].notes, {"bass": [(0, 4, 36), (4, 4, 41)]})
        self.assertEqual(load(db, "Other Quest"), ([], {}))


class Rhythm(unittest.TestCase):
    """The rhythm vocabulary counted from readings made up here: patterns per part and bar, the bass's and
    the drums' figures, the melody's moves and lengths."""

    def test_positions_on_the_grid_and_their_drawing(self):
        from fractions import Fraction as F
        from bitcomposer.translate.rhythm import draw, place, position, value
        self.assertEqual([position(t, 4) for t in (0.0, 0.26, 1.49, 2.76)], [0, F(1, 4), F(3, 2), F(11, 4)])
        self.assertEqual(position(0.34, 12), F(1, 3))
        self.assertEqual([place(F(n, 12)) for n in (0, 6, 3, 4, 8, 2, 1, 18)],
                         ["beat", "eighth", "sixteenth", "triplet", "triplet", "triplet", "finer", "eighth"])
        self.assertEqual(draw([0, F(1, 2), 1, F(4, 3), F(5, 3), F(9, 4), F(23, 8)], 3), "x.x. xt.t .x.~")
        self.assertEqual(draw([0, F(1, 8)], 1), "x...")                 # a finer onset at a quarter's cell yields to it
        self.assertEqual(draw([], 4), "(rest)")
        self.assertEqual(draw([0, 2], 4, {0: "R", 2: "5"}), "R... .... 5... ....")
        self.assertEqual([value(F(1, 4)), value(F(1, 3)), value(F(1, 2)), value(F(3, 4)), value(1), value(F(7, 2)), value(9)],
                         ["a sixteenth", "a triplet eighth", "an eighth", "a dotted eighth", "a beat", "four beats", "longer"])

    def test_a_known_bar_gives_its_pattern(self):
        from bitcomposer.translate.rhythm import Song, rhythms
        # three bars of four, the last cut to two beats at a section join; chords struck in three voices on the
        # beats in the first bar, eighths in the second, a triplet tune in the melody
        chords = [(b, 1, m, "p") for b in range(4) for m in (60, 64, 67)] + [(4 + e / 2, 0.5, 60, "p") for e in range(8)]
        tune = [(0, 1, 72, "l"), (1 / 3, 1, 74, "l"), (2 / 3, 1, 76, "l"), (1, 3, 77, "l"), (4, 4, 79, "l")]
        s = Song("test", 4, 12, [(0, 4), (4, 8), (8, 10)], [], {"accompaniment": chords, "melody": tune})
        r = rhythms([s])
        self.assertEqual(dict(r.patterns["accompaniment", 4]), {"x... x... x... x...": 1, "x.x. x.x. x.x. x.x.": 1})
        self.assertEqual(dict(r.patterns["melody", 4]), {"xt.t x... .... ....": 1, "x... .... .... ....": 1})
        self.assertEqual(r.patterns["accompaniment", 4].songs["x... x... x... x..."], 1)
        self.assertEqual((r.songs["accompaniment"], r.bars["accompaniment"], r.onsets["accompaniment"]), (1, 2, 12))
        self.assertEqual(dict(r.places["accompaniment"]), {"beat": 8, "eighth": 4})
        self.assertEqual(dict(r.places["melody"]), {"beat": 3, "triplet": 2})
        self.assertEqual((dict(r.meters), dict(r.odd)), ({4: 1}, {4: 1}))
        self.assertEqual(r.off_eighths, [100 * 2 / 25])                 # as stage 2 counts: every pitched note
        self.assertEqual(r.triplets, [100.0])

    def test_a_known_bass_line_gives_its_figure(self):
        from bitcomposer.translate.rhythm import Song, bass
        from bitcomposer.translate.vocab import Span
        # a bar of C: C2 G2 C3 G2 (the octave bass); a bar of F: F A C and a B that is no tone of F
        line = [(0, 1, 36, "b"), (1, 1, 43, "b"), (2, 1, 48, "b"), (3, 1, 43, "b"),
                (4, 1, 41, "b"), (5, 1, 45, "b"), (6, 1, 48, "b"), (7, 1, 47, "b")]
        s = Song("test", 4, 4, [(0, 4), (4, 8)], [Span(0, 4, 0, "", 0.9), Span(4, 8, 5, "", 0.9)], {"bass": line})
        b = bass([s])
        self.assertEqual((b.songs, b.bars), (1, 2))
        self.assertEqual(dict(b.figures[4]), {"R... 5... r... 5...": 1, "R... 3... 5... +...": 1})
        self.assertEqual(dict(b.moves), {("fifth", "up"): 1, ("fourth", "up"): 1, ("fourth", "down"): 1, ("step", "down"): 2,
                                         ("third", "up"): 2})
        self.assertEqual(dict(b.semitones), {7: 1, 5: 1, -5: 1, -2: 1, 4: 1, 3: 1, -1: 1})
        # no chord read, or an unfit one, marks the note ?
        s.chords = [Span(0, 4, None, "", 0.0), Span(4, 8, 5, "", 0.3)]
        self.assertEqual(list(bass([s]).figures[4]), ["?... ?... ?... ?..."])

    def test_drum_sounds_are_named_by_how_they_play(self):
        from bitcomposer.translate.rhythm import Song, drums
        # four bars: a kick on one and three, a snare on two and four, a hat on the eighths
        hits = []
        for bar in range(4):
            hits += [(bar * 4, 0.3, float("nan"), "k"), (bar * 4 + 2, 0.3, float("nan"), "k")]
            hits += [(bar * 4 + 1, 0.3, float("nan"), "s"), (bar * 4 + 3, 0.3, float("nan"), "s")]
            hits += [(bar * 4 + e / 2, 0.1, float("nan"), "h") for e in range(8)]
        s = Song("test", 4, 4, [(0, 4), (4, 8), (8, 12), (12, 16)], [], {"drums": hits})
        d = drums([s])
        self.assertEqual({k: v["name"] for k, v in d.sounds.items()}, {"k": "kick", "s": "snare", "h": "hat"})
        self.assertEqual({v["how"] for v in d.sounds.values()}, {"play"})
        self.assertEqual((d.sounds["h"]["a_bar"], d.sounds["k"]["one"], d.sounds["k"]["three"], d.sounds["s"]["back"]), (8, 4, 4, 8))
        self.assertEqual(dict(d.figures[4]), {(("kick", "x... .... x... ...."), ("snare", ".... x... .... x..."),
                                               ("hat", "x.x. x.x. x.x. x.x.")): 4})
        self.assertEqual((d.songs, d.bars), (1, 4))

    def test_a_known_melody_gives_its_moves_and_lengths(self):
        from bitcomposer.translate.rhythm import Song, melody
        # C D E G E C C, the G struck with a lower B that the line leaves out; a rest after the last E
        tune = [(0, 0.5, 60, "l"), (0.5, 0.5, 62, "l"), (1, 1, 64, "l"), (2, 1, 67, "l"), (2, 1, 59, "l"),
                (3, 1, 64, "l"), (5, 2, 60, "l"), (7, 1, 60, "l")]
        s = Song("test", 4, 4, [(0, 4), (4, 8)], [], {"melody": tune})
        m = melody([s])
        self.assertEqual((m.songs, m.notes), (1, 7))
        self.assertEqual(dict(m.moves), {("step", "up"): 2, ("third", "up"): 1, ("third", "down"): 2, ("repeat", ""): 1})
        self.assertEqual(dict(m.semitones), {2: 2, 3: 1, -3: 1, -4: 1, 0: 1})
        self.assertEqual({float(k): v for k, v in m.lengths.items()}, {0.5: 2, 1: 2, 2: 2})
        self.assertEqual(m.sounded, [1, 1, 1, 1, 0.5, 1])

    def test_songs_load_once_through_with_their_bars_and_drums(self):
        from array import array
        from bitcomposer.translate import store
        from bitcomposer.translate.rhythm import load
        db = store.connect(":memory:")
        row = lambda sid, bpm, loop: (sid, "", "", "Test Quest", sid, "", None, 8.0, store.VERSION, bpm, 4, 2,
                                      1.0, 0.5, 0, "major", 0.8, 0, loop, 2 if loop is not None else None,
                                      2.0 if loop is not None else None)
        for args in (("beat", 120.0, 1), ("free", None, None), ("quiet", 120.0, None)):
            db.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row(*args))
        # 16 beats of half a second, bars of four; the song loops from bar two for two seconds: beat 8
        for sid in ("beat", "quiet"):
            db.execute("INSERT INTO beats VALUES (?,?,?)", (sid, array("d", [b / 2 for b in range(16)]).tobytes(),
                                                           array("d", [0.0, 2.0, 4.0, 6.0]).tobytes()))
        for a, b, root in ((0, 4, 0), (4, 8, 5), (8, 12, 7), (12, 16, 0)):
            db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", ("beat", a, b, root, "", 0.9))
        db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", ("quiet", 0, 16, None, "", 0.0))
        db.execute("INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?,?)", ("beat", 0, "kickkey", 0, 0, None, 0, 100, 0, None))
        bass = array("f", [0, 4, 36, 0.5, 0.5, 1, 4, 4, 41, 0.5, 0.5, 1, 6, 1, 43, 0, 0.5, 1, 8, 4, 43, 0.5, 0.5, 1])
        drum = array("f", [0, 0.5, float("nan"), 0.5, 0.5, 0, 2, 0.5, float("nan"), 0.5, 0.5, -1])
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", ("beat", 0, "bass", None, None, bass.tobytes()))
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", ("beat", 1, "drums", None, None, drum.tobytes()))
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", ("beat", 2, "melody", None, '{"roll": true}', bass.tobytes()))
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", ("beat", 3, "double", 0, None, bass.tobytes()))
        songs, left_out = load(db)
        self.assertEqual(left_out, {"free time": 1, "mostly silent": 1})
        self.assertEqual([s.title for s in songs], ["beat"])
        s = songs[0]
        self.assertEqual((s.meter, s.division, s.bars), (4, 2, [(0, 4), (4, 8)]))
        self.assertEqual([(c.start, c.end, c.root) for c in s.chords], [(0, 4, 0), (4, 8, 5)])
        self.assertEqual(s.notes["bass"], [(0, 4, 36, "noise"), (4, 4, 41, "noise")])   # the silent note and the loop's left out
        self.assertEqual([n[3] for n in s.notes["drums"]], ["kickkey", "noise"])
        self.assertEqual((list(s.rolls), len(s.rolls["melody"])), (["melody"], 2))
        self.assertNotIn("double", s.notes)


class DrumsBySound(unittest.TestCase):
    """A drum sample named by its sound (drums.py): made-up sounds and the generator's named kits; how the
    sample is played no longer decides anything (the drum check: it agreed with the ear in 43 % of sounds)."""

    def test_made_up_sounds_are_named_by_what_they_are(self):
        from bitcomposer.translate import drums
        kick = drums.measure(tone(55, 0.3, decay=0.08), 32000)                 # a low decaying tone
        hat = drums.measure(tone(6000, 0.1, noise=20.0, decay=0.015), 32000)    # a short noise burst
        crash = drums.measure(tone(5000, 1.5, noise=20.0, decay=0.4), 32000)    # a longer bright ring
        snare = drums.measure(tone(200, 0.3, noise=2.0, decay=0.06), 32000)     # a noise-and-tone hit
        self.assertGreaterEqual(kick.low, 0.5)
        self.assertLess(kick.bright, drums.KICK_HZ)
        self.assertLess(hat.body, drums.BODY)
        self.assertLess(hat.ring, drums.BURST)
        self.assertGreaterEqual(crash.ring, drums.LONG)
        self.assertGreaterEqual(snare.body, drums.BODY)
        self.assertLess(snare.low, 0.5)
        self.assertEqual([drums.name(x) for x in (kick, hat, crash, snare)], ["kick", "hat", "cymbal", "snare"])
        # a tom: a low tone pitched above the kick's range that rings; a block: a mid tone with no body
        self.assertEqual(drums.name(drums.measure(tone(160, 0.3, decay=0.1), 32000)), "tom")
        self.assertEqual(drums.name(drums.measure(tone(2500, 0.05, decay=0.01), 32000)), "other")
        # a looped sample rings as long as the game holds it: a short noise loop held long is a cymbal
        loop = tone(5000, 0.05, noise=20.0)
        self.assertEqual(drums.name(drums.measure(loop, 32000, (0, len(loop)), held=0.08)), "hat")
        self.assertEqual(drums.name(drums.measure(loop, 32000, (0, len(loop)), held=1.0)), "cymbal")

    def test_the_sound_alone_settles_a_bright_burst_a_thud_and_a_held_tone(self):
        from bitcomposer.translate import drums
        burst = drums.measure(tone(5000, 0.3, noise=20.0, decay=0.04), 32000)   # a bright bodiless burst, 0.18 s
        self.assertTrue(drums.BURST <= burst.ring < drums.OPEN and burst.body < drums.BODY and burst.bright >= drums.BRIGHT)
        self.assertEqual(drums.name(burst), "hat")                                        # bright: a hat, not a gated snare
        self.assertEqual(drums.name(burst, {"hits": 10, "one": 7, "three": 1, "back": 1}), "hat")   # the play changes nothing
        thud = drums.measure(tone(130, 0.05, decay=0.01), 32000)              # a short low thud pitched above KICK_HZ
        self.assertTrue(thud.low >= 0.5 and drums.KICK_HZ <= thud.bright < drums.TOM_HZ and thud.ring < drums.THUD)
        self.assertEqual(drums.name(thud), "kick")
        held = drums.measure(tone(440, 1.0, decay=0.5), 32000)                # a pitched note held: no drum
        self.assertTrue(held.tone >= drums.INSTRUMENT and held.ring >= drums.RING)
        self.assertEqual(drums.name(held), "none")

    def test_the_generator_s_named_drums_come_out_right(self):
        from bitcomposer.translate import drums
        right, total, missed = drums.score()
        self.assertGreaterEqual(total, 40)
        # the chip palette's crash is a bright burst of 0.18 s, a hat by the rule: the known miss
        self.assertLessEqual({p for p, _, _ in missed}, {"crash"})
        self.assertGreaterEqual(right, total - 1)

    def test_a_kit_names_a_song_s_drums_from_its_presets_and_the_rhythm_counts_take_them(self):
        from bitcomposer.translate import drums
        from bitcomposer.translate.rhythm import Song, sounds
        hits = []
        for bar in range(4):
            hits += [(bar * 4, 0.3, float("nan"), "snes_kick"), (bar * 4 + 2, 0.3, float("nan"), "snes_kick")]
            hits += [(bar * 4 + 1, 0.3, float("nan"), "snes_snare"), (bar * 4 + 3, 0.3, float("nan"), "snes_snare")]
            hits += [(bar * 4 + e / 2, 0.1, float("nan"), "snes_crash") for e in range(8)]   # a crash kept as a hat
            hits += [(bar * 4 + 1, 0.3, float("nan"), "unknown")]
        s = Song("test", 4, 4, [(0, 4), (4, 8), (8, 12), (12, 16)], [], {"drums": hits})
        d = sounds([s], bank=drums.Kit())
        self.assertEqual({k: (v["name"], v["how"]) for k, v in d.items()},
                         {"snes_kick": ("kick", "sound"), "snes_snare": ("snare", "sound"), "snes_crash": ("cymbal", "sound"),
                          "unknown": ("snare", "play")})
        self.assertEqual(sounds([s], {"snes_crash": "hat"}, drums.Kit())["snes_crash"]["how"], "known")
        self.assertEqual(d["snes_kick"]["held"], 0.3 * 60 / 120)


class Games(unittest.TestCase):
    """The counts across games on a database made up here: four games of two songs, two to a driver, the
    headline numbers set by what each game's songs do."""

    @staticmethod
    def database():
        from array import array
        from bitcomposer.translate import store
        db = store.connect(":memory:")
        nan = float("nan")

        def song(sid, game, composer, driver, mode, bpm, swing, walking, drums, fifths, free=False):
            # 16 beats of four bars at 120 BPM (half a second a beat), looping over all of it
            db.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (sid, sid + ".spc", game, game, sid, composer, driver, 8.0, store.VERSION, None if free else bpm,
                        4, 4, 1.0, swing, 0, mode, 0.8, 0, None, None, None))
            if free:
                return
            db.execute("INSERT INTO beats VALUES (?,?,?)", (sid, array("d", [b / 2 for b in range(16)]).tobytes(),
                                                           array("d", [0.0, 2.0, 4.0, 6.0]).tobytes()))
            for a, b, root in ((0, 4, 0), (4, 8, 5), (8, 12, 7), (12, 16, 0)):     # I IV V I, a chord a bar
                db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", (sid, a, b, root, "5" if fifths else "", 0.9))
            bass = array("f")
            for bar, root in enumerate((36, 41, 43, 36)):
                pitches = (root, root + 2, root + 4, root + 5) if walking else (root, root + 12, root, root + 12)
                for beat, m in enumerate(pitches):
                    bass.extend((bar * 4 + beat, 1, m, 0.5, 0.5, -1))
            db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", (sid, 0, "bass", None, None, bass.tobytes()))
            tune = array("f")                                                       # eighths by step, C D E F G A B C
            for i, m in enumerate((60, 62, 64, 65, 67, 69, 71, 72) * 4):
                tune.extend((i / 2, 0.5, m, 0.8, 0.5, -1))
            db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", (sid, 1, "melody", None, None, tune.tobytes()))
            if drums:
                hits = array("f")
                for beat in range(16):
                    hits.extend((beat, 0.2, nan, 0.5, 0.5, -1))
                db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", (sid, 2, "drums", None, None, hits.tobytes()))
        # Alpha and Beta share a driver and a composer; Gamma and Delta share the other driver
        song("a1", "Alpha", "A. Composer", "one", "major", 120.0, 0.5, True, True, False)
        song("a2", "Alpha", "A. Composer", "one", "major", 130.0, 0.5, True, True, False)
        song("b1", "Beta", "A. Composer, B. Composer", "one", "major", 110.0, 0.5, True, False, False)
        song("b2", "Beta", "A. Composer, B. Composer", "one", "minor", 120.0, 0.5, True, True, False)
        song("b3", "Beta", "A. Composer, B. Composer", "one", "minor", 120.0, 0.5, True, True, False, free=True)
        song("c1", "Gamma", "C. Composer", "two", "minor", 90.0, 0.67, False, True, True)
        song("c2", "Gamma", "C. Composer", "two", "minor", 90.0, 0.67, False, True, True)
        song("d1", "Delta", "D. Composer", "two", "minor", 80.0, 0.67, False, False, True)
        song("d2", "Delta", "D. Composer", "two", "major", 100.0, 0.5, False, False, True)
        db.commit()
        return db

    def test_each_game_s_headline_numbers_are_its_songs(self):
        from bitcomposer.translate import games
        table = games.games(self.database())
        by = {g.name: g for g in table}
        self.assertEqual([g.name for g in table], ["Alpha", "Beta", "Delta", "Gamma"])
        self.assertEqual((by["Beta"].counted, by["Beta"].total, by["Beta"].left_out), (2, 3, {"free time": 1}))
        a, c = by["Alpha"].numbers, by["Gamma"].numbers
        self.assertEqual((a["tempo"], a["minor"], a["chords"], a["fifths"]), (125.0, 0.0, 1.0, 0.0))
        self.assertEqual((c["minor"], c["fifths"], c["swung"], by["Alpha"].numbers["swung"]), (100.0, 100.0, 100.0, 0.0))
        self.assertAlmostEqual(a["bass_step"], 100 * 12 / 15)                      # steps within the bar, leaps between
        self.assertEqual(c["bass_step"], 0.0)
        self.assertAlmostEqual(c["bass_oct"], 100 * 12 / 15)
        self.assertEqual((a["iv_i"], round(a["v_i"]), by["Alpha"].top_move[:8]), (0.0, 33, "I -> IV ")) # I IV V I: I->IV, IV->V, V->I
        self.assertEqual((a["mel_step"], a["mel16"], a["mel_trip"], a["mel_long"]), (100 * 28 / 31, 0.0, 0.0, 0.0))
        self.assertEqual((a["off"], a["triplet"]), (0.0, 0.0))
        self.assertEqual((a["drums"], a["drumless"], by["Beta"].numbers["drumless"], by["Delta"].numbers["drums"]), (4.0, 0.0, 50.0, 0.0))
        self.assertEqual(games.composer_of(by["Beta"]), "A. Composer")

    def test_the_spread_and_what_the_driver_explains(self):
        from bitcomposer.translate import games
        table = games.games(self.database())
        rows = {r[0]: r for r in games.spread(table)}
        self.assertEqual(rows["chords"][7], "shared")                               # a chord a bar in every game
        self.assertEqual((rows["fifths"][7], rows["fifths"][4][1], rows["fifths"][5][1]), ("own", "Alpha", "Gamma"))
        self.assertEqual(rows["bass_step"][7], "own")
        exp = games.explained(table, lambda g: g.driver, shuffles=50)
        self.assertEqual(exp["fifths"][:1] + exp["fifths"][2:], (1.0, 4, 2))      # the driver splits the fifths wholly
        self.assertLess(exp["fifths"][1], 1.0)                                      # shuffled, it does not
        self.assertEqual(games.explained(table, games.composer_of, shuffles=10), {})  # no two games share a composer
        text = games.report(table, shuffles=10)
        self.assertIn("4 games, 8 songs counted of 9", text)
        self.assertIn("bare 5ths", text)
        self.assertRegex(text, r"bare 5ths +1\.00 \(\d\.\d\d\)\*")


class Against(unittest.TestCase):
    """A composed song read for the counts: its parts the generator's, its chords and key the reader's."""

    def _plain_song(self) -> dict:
        """Four bars, C F C G held a bar each in the three harmony channels over the bass on the root, a tune
        above, a kick on one and three, a snare on two and four, hats on the eighths."""
        from bitcomposer.it_format import ITNote, ITPattern
        pat = ITPattern(rows=64, channels=19)

        def put(row, ch, note):
            pat.data[row][ch] = ITNote(note=note, instrument=1, volume=64)
        for row, notes in ((0, (60, 64, 67)), (16, (65, 69, 72)), (32, (60, 64, 67)), (48, (67, 71, 74))):
            for ch, m in zip((1, 2, 3), notes):
                put(row, ch, m)
            put(row, 4, notes[0] - 24)
        for row, m in ((0, 72), (4, 74), (8, 76), (12, 77), (16, 81), (24, 79), (32, 76), (40, 74), (48, 74), (56, 71)):
            put(row, 0, m)
        for bar in range(0, 64, 16):
            put(bar, 6, 60)
            put(bar + 8, 6, 60)
            put(bar + 4, 7, 60)
            put(bar + 12, 7, 60)
            for e in range(0, 16, 2):
                put(bar + e, 8, 60)
        return {"name": "plain", "key": 60, "scale": "major", "speed": 6, "tempo": 120, "patterns": [pat], "orders": [0, 255]}

    def test_a_plain_song_reads_as_written(self):
        from collections import Counter
        from bitcomposer.translate import against, measures
        song = self._plain_song()
        v, r, home = against.read(song)
        self.assertEqual(home, (0, "major", "major"))
        self.assertEqual((v.tonic, v.mode), (0, "major"))
        self.assertEqual([(c.start, c.end, c.root, c.shape) for c in v.chords], [(0, 4, 0, ""), (4, 8, 5, ""), (8, 12, 0, ""), (12, 16, 7, "")])
        self.assertEqual(against.parts(measures.of_composed(song)),
                         {0: "melody", 1: "harmony", 2: "harmony", 3: "harmony", 4: "bass", 6: "drums", 7: "drums", 8: "drums"})
        self.assertEqual(set(v.notes), {"melody", "harmony", "bass"})
        self.assertEqual(v.notes["bass"][:3], [(0, 4, 36), (4, 4, 41), (8, 4, 36)])
        self.assertEqual(v.notes["bass"][3][::2], (12, 43))                        # still sounding at the end: no length
        self.assertEqual(r.bars, [(0, 4), (4, 8), (8, 12), (12, 16)])
        self.assertEqual(Counter(n[3] for n in r.notes["drums"]), {"kick": 8, "snare": 8, "hihat": 32})
        rows = against.rows([v], [r], [home], against.DRUMS)
        self.assertEqual(rows["songs"][2], ("the key read is the generator's home key", "1 of 1 (the key its scale's notes spell 0, another 0)", None))
        self.assertEqual(sorted(rows["chord moves by degree alone, major keys"]), [("I -> IV", "33 %", 1), ("I -> V", "33 %", 1), ("IV -> I", "33 %", 1)])
        self.assertEqual(rows["chord shapes read (share of spans)"], [("major", "100 %", 4)])
        self.assertEqual(rows["bass figures (R root, 3 third, 5 fifth, 7 seventh, + another, ? no chord, r the root an octave up)"],
                         [("R... .... .... ....", "100 % (1)", 4)])
        drums = dict((row[0], row[1]) for row in rows["drum sounds, named by their sound (the generator's as it names them)"])
        self.assertEqual(drums, {"named kick": "kick", "named snare": "snare", "named hat": "hihat", "named tom": "", "named cymbal": "",
                                 "named other": "", "the namer names the generator's as they are": "3 of 3"})   # the chip palette's kick, snare and hihat
        self.assertEqual(rows["drum figures, bars of 4 beats (K kick, S snare, h hat, t tom, c cymbal, o another)"],
                         [("K x... .... x... ....\nS .... x... .... x...\nh x.x. x.x. x.x. x.x.", "100 % (1)", 4)])
        text = against.table({"game": rows, "pack": rows}, top=3)
        self.assertIn("  I -> IV               33 %  33 %", text)
        self.assertIn("  S .... x... .... x...\n  h x.x. x.x. x.x. x.x.", text)

    def test_a_composed_song_s_parts_are_its_channels_and_its_plain_chords_read_as_written(self):
        """A fixed seed of the hand-made ffvi pack (sustained chords, the bass driving): where the generator
        plays a chord plain (the bass on one pitch class, the harmony channels striking the two other tones of
        a major or minor triad on it), the chord read over the bar is that triad. The generator changing
        changes the song: pick another seed that holds chords plain then."""
        from collections import Counter
        from bitcomposer.composer import compose_song
        from bitcomposer.translate import against, measures
        song = compose_song(seed=16, sound="ffvi")
        v, r, home = against.read(song)
        s = measures.of_composed(song)
        parts = against.parts(s)
        self.assertEqual((parts[0], parts[4], parts[5]), ("melody", "bass", "arp"))
        self.assertTrue(all(parts[ch] == "drums" for ch in parts if ch >= 6))
        self.assertTrue(all(parts[ch] in ("harmony", "accompaniment", "counter", "arp") for ch in (1, 2, 3) if ch in parts))
        self.assertEqual((v.tonic, v.mode), home[:2])
        triads = {frozenset({r_, (r_ + 4) % 12, (r_ + 7) % 12}): (r_, "") for r_ in range(12)}
        triads.update({frozenset({r_, (r_ + 3) % 12, (r_ + 7) % 12}): (r_, "m") for r_ in range(12)})
        plain = agree = 0
        for a, b in r.bars:
            struck = lambda ok: {round(n.midi) % 12 for n in s.notes if ok(n) and a - 0.06 <= n.beat < b - 0.06}
            bass, chord = struck(lambda n: parts[n.voice] == "bass"), struck(lambda n: n.voice in (1, 2, 3))
            triad = triads.get(frozenset(chord | bass))
            if len(bass) != 1 or not chord or not triad or triad[0] not in bass:
                continue
            plain += 1
            held = Counter()
            for c in v.chords:
                if c.start < b and c.end > a and v.kept(c):
                    held[c.root, c.shape] += min(c.end, b) - max(c.start, a)
            agree += held and held.most_common(1)[0][0] == triad
        self.assertGreater(plain, 0)
        self.assertEqual(agree, plain)
        rows = against.rows([v], [r], [home], against.DRUMS)
        self.assertEqual(rows["songs"][2][1], "1 of 1 (the key its scale's notes spell 0, another 0)")
        self.assertEqual(rows["the melody's moves"][0], ("songs / notes", f"1 / {len(r.notes['melody'])}", None))


if __name__ == "__main__":
    unittest.main()


class Phrases(unittest.TestCase):
    """Progressions by part and the melody's phrase shapes (phrases.py) on readings made up here."""

    def test_a_known_progression_through_a_part_gives_its_numerals_and_cadence(self):
        from bitcomposer.translate.phrases import Part, Song, cadence, cycle, progressions
        from bitcomposer.translate.vocab import Span
        self.assertEqual(cycle(["I", "IV", "V", "I", "IV", "V", "I"]), ("I", "IV", "V"))
        self.assertEqual(cycle(["I", "IV", "V", "I"]), ("I", "IV", "V", "I"))
        self.assertEqual((cycle(["I"]), cycle(["I", "IV", "I", "IV"])), (("I",), ("I", "IV")))
        self.assertEqual([cadence(s) for s in (["I", "IV", "I"], ["IV", "V", "I"], ["I", "bVII", "I"], ["I", "VII", "I"],
                                                ["I", "II", "I"], ["I", "V"], ["I", "IV"], ["I"], [])],
                         ["IV -> I", "V -> I", "bVII -> I", "bVII -> I", "another -> I", "half (on V)", "elsewhere", "one chord", "elsewhere"])
        # C major, bars of four: A is C | F G | C with a passing Dm on its fourth beat | G C; B is Am F twice;
        # C repeats A (left out); D holds G; the song loops back to B
        chords = [Span(0, 4, 0, "", 0.9), Span(4, 6, 5, "", 0.9), Span(6, 8, 7, "", 0.9), Span(8, 11, 0, "", 0.9),
                  Span(11, 12, 2, "m", 0.9), Span(12, 14, 7, "", 0.9), Span(14, 16, 0, "", 0.9)]
        chords += [Span(16 + 4 * k, 20 + 4 * k, 9 if k % 2 == 0 else 5, "m" if k % 2 == 0 else "", 0.9) for k in range(4)]
        chords += [Span(32 + 4 * k, 36 + 4 * k, 0 if k < 2 else 5, "", 0.9) for k in range(4)] + [Span(48, 64, 7, "", 0.9)]
        s = Song("test", 0, "major", 4, [(4 * b, 4 * b + 4) for b in range(16)], chords,
                 parts=[Part("A", 0, 4), Part("B", 4, 4), Part("A", 8, 4, 0), Part("D", 12, 4)], loop_bar=4)
        p = progressions([s])
        self.assertEqual((p.songs, p.parts, p.counted), (1, 4, 3))
        self.assertEqual(dict(p.built["major"]), {("I", "IV", "V", "I", "V", "I"): 1, ("VI", "IV"): 1, ("V",): 1})
        self.assertEqual(p.built["major"].songs[("VI", "IV")], 1)
        self.assertEqual(dict(p.runs["major"]), {("I", "IV", "V"): 1, ("IV", "V", "I"): 1, ("V", "I", "V"): 1, ("I", "V", "I"): 1,
                                                 ("VI", "IV", "VI"): 1, ("IV", "VI", "IV"): 1})
        self.assertEqual((dict(p.begins), dict(p.ends)), ({"I": 1, "VI": 1, "V": 1}, {"I": 1, "IV": 1, "V": 1}))
        self.assertEqual(dict(p.cadences), {"V -> I": 1, "elsewhere": 1, "one chord": 1})
        self.assertEqual(dict(p.lengths), {"5 to 8": 1, "2 to 4 chords": 1, "one chord": 1})
        self.assertEqual((dict(p.loops), dict(p.loops_on)), ({"elsewhere": 1}, {"VI": 1}))     # G back to Am
        self.assertEqual(p.levels, {"beat": 6 + 3 + 0, "half bar": 5 + 3 + 0, "bar": 3 + 3 + 0})  # the passing Dm counts at the beat only
        self.assertEqual(p.rates, [(1, 2.0, 2), (1, 1.0, 1), (1, 0.0, 0)])

    def test_a_known_melody_phrase_gives_its_contour_peak_range_ends_and_relation(self):
        from bitcomposer.translate.phrases import Part, Song, phrases, shapes
        from bitcomposer.translate.vocab import Span
        # C major over one C chord; two-bar phrases of quarters: an arch, the arch moved up a step (diatonic), the arch
        # again, the same rhythm with another tune, a dotted figure, a rest, and a bar the counter-line carries
        tune = [(b, 1, m) for b, m in enumerate((60, 62, 64, 67, 72, 67, 64, 60))]
        tune += [(8 + b, 1, m) for b, m in enumerate((62, 64, 65, 69, 74, 69, 65, 62))]
        tune += [(16 + b, 1, m) for b, m in enumerate((60, 62, 64, 67, 72, 67, 64, 60))]
        tune += [(24 + b, 1, m) for b, m in enumerate((60, 64, 67, 72, 67, 64, 55, 60))]
        tune += [(32, 1.5, 60), (33.5, 1.5, 62), (35, 5, 64)]
        counter = [(48 + b, 1, m) for b, m in enumerate((67, 65, 64, 62))]
        s = Song("test", 0, "major", 4, [(4 * b, 4 * b + 4) for b in range(14)], [Span(0, 56, 0, "", 0.9)],
                 {"melody": tune, "counter": counter}, [Part("A", 0, 8), Part("B", 8, 6)], loop_bar=0)
        ph = phrases(s, 2)
        self.assertEqual([(p.start, p.end, p.source, p.ends_part, p.last) for p in ph],
                         [(0, 8, "melody", False, False), (8, 16, "melody", False, False), (16, 24, "melody", False, False),
                          (24, 32, "melody", True, False), (32, 40, "melody", False, False), (40, 48, "resting", False, False),
                          (48, 56, "counter", True, True)])
        self.assertEqual([p.final[2] for p in ph if p.line], [60, 62, 60, 60, 64, 62])   # the longest held of the last bar, the later at a tie
        c = shapes([s], 2)
        self.assertEqual((c.phrases, dict(c.source)), (7, {"melody": 5, "resting": 1, "counter": 1}))
        self.assertEqual(dict(c.contour), {"arch": 4, "rising": 1, "falling": 1})
        self.assertEqual(dict(c.peak), {"third": 3, "second": 2, "first quarter": 1})
        self.assertEqual(c.ranges, [12, 12, 12, 17, 4, 5])
        self.assertEqual(dict(c.starts_key), {"1": 4, "another degree": 1, "5": 1})
        self.assertEqual(dict(c.starts_chord), {"root": 4, "another tone": 1, "fifth": 1})
        self.assertEqual(dict(c.ends_key), {"1": 3, "another degree": 2, "3": 1})
        self.assertEqual(dict(c.ends_chord), {"root": 3, "another tone": 2, "third": 1})
        self.assertEqual(dict(c.part_ends), {(False, True): 2, (False, False): 2, (True, True): 1, (True, False): 1})
        self.assertEqual(dict(c.song_ends), {"another degree": 1})
        self.assertEqual(dict(c.relation), {"first": 1, "moved up": 1, "moved down": 1, "answered": 1, "new": 2})
        # the same at four bars and over the part: the part A's phrase is its eight bars
        self.assertEqual([(p.start, p.end) for p in phrases(s, 4)], [(0, 16), (16, 32), (32, 48), (48, 56)])
        self.assertEqual([(p.start, p.end) for p in phrases(s, "part")], [(0, 32), (32, 56)])

    def test_songs_load_with_their_parts_and_a_composed_song_s_are_read(self):
        from array import array
        from bitcomposer.translate import against, phrases, store
        db = store.connect(":memory:")
        row = lambda sid: (sid, sid + ".spc", "test", "Test Quest", sid, "", None, 8.0, store.VERSION, 120.0, 4, 2,
                           1.0, 0.5, 0, "major", 0.8, 0, 1, 2, 2.0)
        for sid in ("form", "noform"):
            db.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row(sid))
            db.execute("INSERT INTO beats VALUES (?,?,?)", (sid, array("d", [b / 2 for b in range(16)]).tobytes(),
                                                           array("d", [0.0, 2.0, 4.0, 6.0]).tobytes()))
            for a, b, root in ((0, 4, 0), (4, 8, 5), (8, 12, 7), (12, 16, 0)):
                db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", (sid, a, b, root, "", 0.9))
            tune = array("f", [0, 1, 60, 0.8, 0.5, -1, 1, 1, 64, 0.8, 0.5, -1, 2, 1, 67, 0.8, 0.5, -1, 9, 1, 72, 0.8, 0.5, -1])
            db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", (sid, 0, "melody", None, None, tune.tobytes()))
        db.execute("INSERT INTO form VALUES (?,?,?,?,?,?,?,?)", ("form", 0, "A", 0, 2, 0.0, None, "part"))
        db.execute("INSERT INTO form VALUES (?,?,?,?,?,?,?,?)", ("form", 1, "A", 2, 2, 4.0, 0, "part"))
        db.execute("INSERT INTO form VALUES (?,?,?,?,?,?,?,?)", ("form", 2, "A", 0, 4, 0.0, None, "section"))
        songs, left_out = phrases.load(db)
        self.assertEqual((left_out, [s.title for s in songs]), ({"no form": 1}, ["form"]))
        s = songs[0]
        self.assertEqual((s.tonic, s.mode, s.meter, s.loop_bar), (0, "major", 4, 1))
        self.assertEqual(s.bars, [(0, 4), (4, 8)])                                  # once through: to the loop's end at beat 8
        self.assertEqual([(p.label, p.bar, p.bars, p.of) for p in s.parts], [("A", 0, 2, None), ("A", 2, 2, 0)])
        self.assertEqual(s.notes, {"melody": [(0, 1, 60), (1, 1, 64), (2, 1, 67)]})
        self.assertEqual(phrases.load(db, song="noform"), ([], {"no form": 1}))
        # a composed song: a plain pattern twice, another twice, the first twice again; its parts read as a game's
        plain = Against._plain_song(self)
        other = Against._plain_song(self)
        for ch, up in ((0, 5), (1, 3), (2, 3), (3, 3), (4, 3)):
            for r in range(64):
                cell = other["patterns"][0].data[r][ch]
                if cell.note:
                    cell.note += up
        song = {**plain, "patterns": [plain["patterns"][0], other["patterns"][0]], "orders": [0, 0, 1, 1, 0, 0, 255],
                "info": {"structure": ["verse", "chorus", "verse"]}}
        v, r, _ = against.read(song)
        p = phrases.of_composed(song, v, r)
        self.assertEqual((p.tonic, p.mode, len(p.bars), set(p.notes)), (0, "major", 24, {"melody"}))
        self.assertEqual([(x.label, x.bar) for x in p.parts], [("A", 0), ("A", 4), ("B", 8), ("B", 12), ("A", 16)])   # a pattern a part
        self.assertEqual(phrases.progressions([p]).built["major"][("I", "IV", "I", "V")], 1)

    def test_the_games_table_and_the_parts_marked_by_ear(self):
        import json
        import os
        import tempfile
        from bitcomposer.translate import phrases
        db = Games.database()
        for sid, in db.execute("SELECT id FROM songs WHERE bpm IS NOT NULL").fetchall():
            db.execute("INSERT INTO form VALUES (?,?,?,?,?,?,?,?)", (sid, 0, "A", 0, 2, 0.0, None, "part"))
            db.execute("INSERT INTO form VALUES (?,?,?,?,?,?,?,?)", (sid, 1, "B", 2, 2, 4.0, None, "part"))
        table = phrases.games(db)
        by = {g.name: g for g in table}
        self.assertEqual([(g.name, g.counted, g.total) for g in table], [("Alpha", 2, 2), ("Beta", 2, 3), ("Delta", 2, 2), ("Gamma", 2, 2)])
        a = by["Alpha"].numbers
        self.assertEqual((a["parts"], a["short"], a["begin_i"], a["v_i"], a["half"]), (4, 100.0, 50.0, 50.0, 0.0))   # I IV | V I
        self.assertEqual((a["rising"], a["repeated"], a["new"]), (100.0, 100.0, 0.0))       # a scale up, every bar alike
        text = phrases.games_report(table, shuffles=10)
        self.assertIn("4 games, 8 songs with a form counted of 9", text)
        self.assertNotIn("\n  parts ", text.split("spread over")[1])                             # a count is no habit
        # the parts marked by ear: one song's A at 0 and B marked a quarter bar late, a C the reader did not read
        heard = {"_about": "", "Alpha/a1.spc": {"set": 2, "marks_s": [["A", 0.0], ["B", 4.5], ["C", 6.0]], "starts_over_s": None}}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "heard.json")
            with open(path, "w") as fh:
                json.dump(heard, fh)
            lines, read, marked = phrases.heard(db, path)
        self.assertEqual(lines[0], "a1                             part    1 of 2 marked starts read, 1 read")
        self.assertEqual(lines[-1], "parts: 1 of 2 marked starts read (recall 0.50), 1 read (precision 1.00)")
        self.assertEqual([(p.label, p.bar, p.bars) for p in read[0].parts], [("A", 0, 2), ("B", 2, 2)])
        self.assertEqual([(p.label, p.bar, p.bars) for p in marked[0].parts], [("A", 0, 2), ("B", 2, 1), ("C", 3, 1)])
