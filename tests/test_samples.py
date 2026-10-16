"""Samples: every preset renders, loops are clean, releases end in silence. Run with: python3 -m unittest discover -s tests"""
import unittest

from support import (compose_song, it_format, random, samples, struct, unittest)  # noqa: F401



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

    def test_release_tails_end_in_silence(self):
        random.seed(1)
        seen = 0
        for name, family in samples.PRESET_RELEASE.items():
            d = samples.generate_instrument(name)
            if not d["sus_loop"]:
                continue
            seen += 1
            x = struct.unpack(f"<{d['length']}h", d["data"])
            peak = max(abs(v) for v in x) or 1
            self.assertLess(max(abs(v) for v in x[-48:]) / peak, 0.03, name)
            self.assertAlmostEqual(d["release"], samples.RELEASE[family])
            self.assertLessEqual(d["loop_end"], d["length"] - int(d["rate"] * d["release"]) + 1)
        self.assertGreater(seen, 20)

    def test_released_voices_end_with_note_off(self):
        song = compose_song(seed=4, style_pref="snes")
        released = {i + 1 for i, s in enumerate(song["samples"]) if s.sus_loop}
        self.assertTrue(released)
        offs = cuts = 0
        for pat in song["patterns"]:
            for row in pat.data:
                for cell in row:
                    offs += cell.note == it_format.NOTE_OFF
                    cuts += cell.note == it_format.NOTE_CUT
        self.assertGreater(offs, 0)

    def test_waveforms_are_tuned(self):
        d = samples.generate_instrument("square_lead")
        period = int(samples.SAMPLE_RATE / samples.BASE_NOTE_HZ)
        self.assertAlmostEqual(d["rate"] / period, samples.BASE_NOTE_HZ, delta=1.0)


if __name__ == "__main__":
    unittest.main()
