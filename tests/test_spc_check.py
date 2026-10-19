"""tools/spc_check.py: its measures, and a conversion measured against the
emulator (synthetic: no game files). Run with: python3 -m unittest discover -s tests"""
import importlib.util
import math
import random
from array import array

from support import ROOT, os, unittest  # noqa: F401
from test_spc_convert import KON0, TINY, _have_openmpt, tiny  # noqa: E402
from bitcomposer.spc import convert, emulate  # noqa: E402

_spec = importlib.util.spec_from_file_location("spc_check", os.path.join(ROOT, "tools", "spc_check.py"))
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


class Measures(unittest.TestCase):
    def test_the_gap_and_the_sides_a_sound_is_on(self):
        self.assertAlmostEqual(check.gap_db([100.0] * 50, [200.0] * 50), 6.02, places=2)   # twice as loud
        self.assertEqual(check.gap_db([100.0] * 50, [100.0] * 50), 0.0)
        left = array("h", (v for i in range(16000) for v in (int(8000 * math.sin(i / 5)), 0)))
        self.assertEqual(check.active_sides(left), (0,))                     # a hard-left voice: the right is not scored

    def test_tone_tells_a_hiss_from_a_beep(self):
        r = random.Random(1)
        hiss = [r.randint(-8000, 8000) for _ in range(2 * 16000)]
        beep = [int(8000 * math.sin(2 * math.pi * 1000 * (i // 2) / 32000)) for i in range(2 * 16000)]
        self.assertGreater(check.tone(hiss, hiss), 0.99)
        self.assertLess(check.tone(hiss, beep), 0.5)


@unittest.skipUnless(emulate.available() and _have_openmpt(), "needs the compiled emulator and libopenmpt")
class Conversion(unittest.TestCase):
    def test_a_tiny_driver_measures_as_itself(self):
        # without its echo (a steady tone's repeats stack as the hardware's only by chance on IT's
        # 10 ms rows: docs/SPC-IMPORT.md) and at a volume IT can reach (50 a side is IT volume 50 of
        # 64; the tiny driver's 100 would need 100): this is about the measuring
        quiet = {0x4D: 0, 0x00: 50, 0x01: 50}
        snap = tiny(tuple((r, quiet.get(r, v)) for r, v in TINY) + KON0)
        song = convert.convert(snap, 1.5)
        ref = check.emulated(snap, 1.0, 0)
        own, echo, master = check.channels_of(song, 0)
        it = check.render_channels(song, {own, master, *echo}, 1.0)
        sides = check.active_sides(ref)
        m = check.compare(ref, it, sides)
        self.assertEqual(sides, (0, 1))
        self.assertLess(m["gap_db"], 1.5)
        self.assertAlmostEqual(m["level"], 1.0, delta=0.25)
        self.assertGreater(check.tone(ref, it, sides), 0.9)
        dry, wet = check.echo_split(snap, 0, 1.0, ref)
        self.assertLess(check.rms(wet[0::2]), 0.01 * check.rms(dry[0::2]))      # no echo sent: the solo is all dry
        echoing = tiny()
        dry, wet = check.echo_split(echoing, 0, 1.0)
        self.assertGreater(check.rms(wet[0::2]) / check.rms(dry[0::2]), 0.2)  # the echo, apart from the dry sound


@unittest.skipUnless(emulate.available(), "needs the compiled emulator")
class Traits(unittest.TestCase):
    def test_what_the_tiny_driver_does(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tiny"))
            path = os.path.join(d, "tiny", "one note.spc")
            with open(path, "wb") as fh:
                fh.write(tiny().raw)
            t = check.song_traits(path)
        self.assertEqual((t["game_folder"], t["song"], t["notes"]), ("tiny", "one note", 1))
        self.assertEqual((t["echo_delay_ms"], t["echo_feedback"], t["echo_sending"]), (32, 0.5, 1))
        self.assertEqual((t["adsr_share"], t["master_volume"]), (0.0, 127))      # GAIN direct, the master full
        self.assertFalse(t["pitch_modulated"])


if __name__ == "__main__":
    unittest.main()
