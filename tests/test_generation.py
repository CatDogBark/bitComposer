"""
Regression tests for the generator. Stdlib only — run with:

    python3 -m unittest discover -s tests -v

They generate real .it files into a temp dir, parse them back with the
standalone analyzer in tools/, and assert on the properties that earlier
defects silently broke: determinism, drum density, pattern reuse, decodable
output, sane loop points, and the full option matrix not crashing.
"""

import importlib.util
import itertools
import os
import random
import struct
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bitcomposer import composer, it_format, melody, names, pattern, samples, theory  # noqa: E402
from bitcomposer.composer import compose_and_save, compose_song  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "analyze", os.path.join(ROOT, "tools", "analyze.py"))
analyze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze)


def _gen(tmp, seed, **kw):
    path = os.path.join(tmp, f"s{seed}.it")
    info = compose_and_save(path, seed=seed, **kw)
    return path, info


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


class Determinism(unittest.TestCase):
    def test_same_seed_same_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, _ = _gen(tmp, 11)
            data_a = _read(a)
            b, _ = _gen(tmp, 11)
            self.assertEqual(data_a, _read(b))

    def test_different_seeds_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, _ = _gen(tmp, 1)
            b, _ = _gen(tmp, 2)
            self.assertNotEqual(_read(a), _read(b))


class FileFormat(unittest.TestCase):
    def test_title_and_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, info = _gen(tmp, 3)
            m = analyze.IT(path)
            self.assertEqual(m.name, info["title"])
            self.assertLessEqual(len(info["title"]), names.MAX_TITLE)
            self.assertTrue(m.special & 1, "message flag not set")
            msg_len, msg_off = struct.unpack("<HI", m.raw[0x36:0x3C])
            msg = m.raw[msg_off:msg_off + msg_len].decode("ascii").split("\r")
            self.assertEqual(msg[0], info["title"])
            self.assertIn(f"{info['tempo']} BPM", msg[1])
            self.assertIn(info["style"], msg[2])
            self.assertIn("seed 3", msg[-1])
            # titles differ between seeds and depend only on the seed
            _, info_b = _gen(tmp, 4)
            self.assertNotEqual(info["title"], info_b["title"])
            self.assertEqual(compose_song(seed=3)["name"], info["title"])

    def test_header_and_channel_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, info = _gen(tmp, 3)
            m = analyze.IT(path)
            self.assertEqual(m.name, info["title"])
            self.assertEqual(m.patnum, info["num_patterns"])
            self.assertEqual(len(m.played()), info["num_orders"])
            # 14 channels enabled, the rest flagged disabled (bit 7 of the pan byte).
            pans = m.raw[0x40:0x80]
            self.assertTrue(all(p < 128 for p in pans[:pattern.NUM_CHANNELS]))
            self.assertTrue(all(p & 128 for p in pans[pattern.NUM_CHANNELS:]))
            self.assertEqual(len(composer.CHANNEL_VOLUMES), pattern.NUM_CHANNELS)

    def test_sample_headers_consistent(self):
        song = compose_song(seed=4, style_pref="snes")
        for s in song["samples"]:
            self.assertEqual(len(s.data), 2 * s.length, s.name)
            self.assertLessEqual(s.loop_end, s.length, s.name)
            self.assertLessEqual(s.loop_start, s.loop_end, s.name)
            self.assertGreater(s.c5_speed, 8000)

    def test_no_orphan_patterns(self):
        """Every pattern in the file is reachable from the order list."""
        for seed in (1, 2, 3):
            song = compose_song(seed=seed)
            self.assertEqual(set(song["orders"]), set(range(len(song["patterns"]))))


class Tempo(unittest.TestCase):
    def test_bpm_roundtrip(self):
        for bpm in (80, 100, 125, 150, 180):
            for speed in (4, 5, 6):
                t = it_format.bpm_to_it_tempo(bpm, speed)
                back = it_format.it_tempo_to_bpm(t, speed)
                self.assertAlmostEqual(back, bpm, delta=bpm * 0.03)

    def test_audible_tempo_in_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            for seed in range(1, 9):
                path, info = _gen(tmp, seed)
                r = analyze.analyze(path)
                self.assertTrue(75 <= r["bpm"] <= 185, (seed, r["bpm"]))
                self.assertAlmostEqual(r["bpm"], info["tempo"], delta=1.0)


class Arrangement(unittest.TestCase):
    """Batch metrics over fixed seeds. Thresholds sit well under the measured
    means so they catch the historical defects (drum grid stretched 4x, zero
    reuse, no syncopation) rather than ordinary variance."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.rows = []
        for seed in range(1, 13):
            path, _ = _gen(cls.tmp.name, seed)
            cls.rows.append(analyze.analyze(path))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _mean(self, key):
        return sum(r[key] for r in self.rows) / len(self.rows)

    def test_drum_density_is_a_groove(self):
        self.assertGreater(self._mean("kick_per_bar"), 1.5)
        self.assertGreater(self._mean("snare_per_bar"), 0.9)
        self.assertGreater(self._mean("hat_per_bar"), 3.5)

    def test_melody_has_sixteenths(self):
        self.assertGreater(self._mean("odd_row_pct"), 3.0)

    def test_repeated_sections_share_music(self):
        # Forms with repeats must not be 100% unique melody patterns.
        self.assertLess(self._mean("mel_uniq_pct"), 95.0)

    def test_effects_reach_file(self):
        fx = set("".join(r["fx"] for r in self.rows))
        for letter in "DGHJQS":
            self.assertIn(letter, fx)

    def test_harmony_has_voicings(self):
        self.assertGreater(self._mean("distinct_voicings"), 2.0)


class OptionMatrix(unittest.TestCase):
    def test_every_form_style_and_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            combos = itertools.product(
                ["standard", "aaba", "rondo", "short", "linear"],
                ["chip", "snes", "genesis"], ["on", "off"])
            for i, (form, style, echo) in enumerate(combos):
                path = os.path.join(tmp, f"m{i}.it")
                info = compose_and_save(path, seed=100 + i, song_form=form,
                                        style=style, echo=echo)
                self.assertEqual(info["song_form"], form)
                self.assertEqual(info["style"], style)
                self.assertEqual(info["echo"], echo == "on")
                analyze.IT(path)  # parses

    def test_remaining_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            i = 0
            for tempo in ("slow", "medium", "fast"):
                for energy in ("chill", "normal", "intense"):
                    for scale in ("minor", "major", "pentatonic"):
                        i += 1
                        compose_and_save(os.path.join(tmp, f"o{i}.it"), seed=i,
                                         tempo=tempo, energy=energy, scale=scale)
            for voicing in ("thin", "full"):
                for mode in ("stabs", "sustain", "rhythmic"):
                    for weight in ("heavy", "medium", "light"):
                        for dens in ("sparse", "normal", "busy"):
                            i += 1
                            compose_and_save(os.path.join(tmp, f"o{i}.it"), seed=i,
                                             harmony_voicing=voicing, harmony_mode=mode,
                                             bass_weight=weight, drum_density=dens,
                                             drum_fills=(i % 2 == 0),
                                             drum_swing=("off", "light", "heavy")[i % 3],
                                             melody_style=("simple", "phrased")[i % 2])


class CliNaming(unittest.TestCase):
    def test_title_names_with_suffix_and_collisions(self):
        from bitcomposer import cli
        with tempfile.TemporaryDirectory() as tmp:
            import contextlib, io
            argv = sys.argv
            try:
                for extra in ([], ["--suffix", " (auto)"], []):
                    sys.argv = ["bitcomposer", "-s", "3", "-d", tmp, *extra]
                    with contextlib.redirect_stdout(io.StringIO()):
                        cli.main()
            finally:
                sys.argv = argv
            title = compose_song(seed=3)["name"]
            names = sorted(os.listdir(tmp))
            self.assertEqual(names, sorted([f"{title}.it", f"{title} (auto).it", f"{title} 2.it"]))


class Theory(unittest.TestCase):
    def test_progression_degrees_fit_their_scale(self):
        for scale, progs in theory.PROGRESSIONS.items():
            n = len(theory.SCALES[scale])
            for prog in progs:
                for entry in prog:
                    degree, ctype, shift = theory.unpack_chord(entry)
                    self.assertLess(degree, n, (scale, entry))
                    self.assertIn(ctype, theory.CHORD_INTERVALS)
                    self.assertIn(shift, (-1, 0, 1))

    def test_borrowed_chords_shift_root(self):
        scale = theory.build_scale(48, "major", octaves=2)
        self.assertEqual(theory.chord_root_for(48, scale, (6, "major", -1)), 48 + 10)
        self.assertEqual(theory.chord_root_for(48, scale, (4, "major")), 48 + 7)

    def test_secondary_chord_is_valid_entry(self):
        random.seed(5)
        for scale, progs in theory.PROGRESSIONS.items():
            n = len(theory.SCALES[scale])
            for prog in progs:
                for a, b in zip(prog, prog[1:] + prog[:1]):
                    degree, ctype, _ = theory.unpack_chord(theory.secondary_chord(scale, a, b))
                    self.assertLess(degree, n)
                    self.assertIn(ctype, theory.CHORD_INTERVALS)

    def test_arpeggio_param(self):
        # C major voiced from E: offsets to G (3) and C (8).
        self.assertEqual(it_format.arpeggio_param(64, [60, 64, 67]), 0x38)

    def test_rhythm_templates_include_odd_offsets(self):
        self.assertTrue(any(o % 2 for t in melody.RHYTHM_TEMPLATES for o in t))


class Samples(unittest.TestCase):
    def test_every_preset_renders(self):
        random.seed(1)
        for name in samples.INSTRUMENT_PRESETS:
            d = samples.generate_instrument(name)
            self.assertEqual(len(d["data"]), 2 * d["length"], name)
            self.assertLessEqual(d["loop_end"], d["length"], name)

    def test_looped_snes_voices_have_clean_seams(self):
        """A loop whose end does not meet its start clicks on every pass.

        The wrap step (last loop sample to first) must match the step the
        waveform takes at the same phase one period earlier; a saw-like tone
        legitimately has a big edge there, so the raw step is not the test.
        """
        random.seed(1)
        period = samples.SNES_PERIOD
        for name in samples.INSTRUMENT_PRESETS:
            if not name.startswith("snes_"):
                continue
            d = samples.generate_instrument(name)
            if not d["loop"]:
                continue
            x = struct.unpack(f"<{d['length']}h", d["data"])
            peak = max(abs(v) for v in x) or 1
            ls, le = d["loop_start"], d["loop_end"]
            self.assertEqual((le - ls) % period, 0, name)
            wrap = x[ls] - x[le - 1]
            internal = x[ls + period] - x[ls + period - 1] if le - ls >= 2 * period \
                else x[ls + 1] - x[ls]
            seam = abs(wrap - internal) / peak
            self.assertLess(seam, 0.06, f"{name} seam {seam:.3f}")

    def test_looped_genesis_and_chip_voices_have_clean_seams(self):
        """The wrap from loop end to loop start must be no bigger a jump than
        the waveform takes anywhere inside the loop region."""
        random.seed(1)
        for name in samples.INSTRUMENT_PRESETS:
            if not (name.startswith("gen_") or name.endswith("_pluck") or name == "psg_square"):
                continue
            d = samples.generate_instrument(name)
            if not d["loop"]:
                continue
            x = struct.unpack(f"<{d['length']}h", d["data"])
            region = x[d["loop_start"]:d["loop_end"]]
            max_step = max(abs(region[i] - region[i - 1]) for i in range(1, len(region))) or 1
            seam = abs(x[d["loop_start"]] - x[d["loop_end"] - 1]) / max_step
            self.assertLessEqual(seam, 1.05, f"{name} seam {seam:.2f}")

    def test_waveforms_are_tuned(self):
        d = samples.generate_instrument("square_lead")
        period = int(samples.SAMPLE_RATE / samples.BASE_NOTE_HZ)
        self.assertAlmostEqual(d["rate"] / period, samples.BASE_NOTE_HZ, delta=1.0)


class PatternOps(unittest.TestCase):
    def _pat(self):
        return it_format.ITPattern(rows=64, channels=pattern.NUM_CHANNELS)

    def test_echo_copies_and_scales(self):
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
        ringing = self._pat()
        ringing.data[60][0] = it_format.ITNote(note=60, instrument=1, volume=40)
        quiet = self._pat()
        pats = [ringing, quiet]
        pattern.silence_inactive_channels([0, 1], pats)
        self.assertEqual(len(pats), 2)
        self.assertEqual(quiet.data[0][0].note, it_format.NOTE_CUT)


if __name__ == "__main__":
    unittest.main()
