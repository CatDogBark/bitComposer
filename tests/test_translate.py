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


if __name__ == "__main__":
    unittest.main()
