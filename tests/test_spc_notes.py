"""Running an SPC driver, its writes as notes, and sample tuning (synthetic: no
game files). Run with: python3 -m unittest discover -s tests"""
import math
import random
import unittest
from array import array

from support import unittest  # noqa: F401,F811
from bitcomposer import spc  # noqa: E402
from bitcomposer.spc import brr, emulate, notes, tuning  # noqa: E402
from bitcomposer.spc.emulate import CLOCK, Write  # noqa: E402


def snapshot(code: bytes = b"", pc: int = 0x0200, dsp: dict | None = None):
    data = bytearray(spc.SIZE)
    data[:len(spc.MAGIC)] = spc.MAGIC
    data[0x23] = 27                                   # no ID666 tag
    data[0x25:0x27] = pc.to_bytes(2, "little")
    data[0x2B] = 0xEF
    data[spc.RAM + pc:spc.RAM + pc + len(code)] = code
    for reg, v in (dsp or {}).items():
        data[spc.DSP + reg] = v
    return spc.read(bytes(data))


def sample(pcm, loop=None):
    a = array("h", (max(-32768, min(32767, int(v))) for v in pcm))
    if loop is None:
        return brr.Sample(a, None, None, True, 0, 0, 0)
    return brr.Sample(a, loop[0], loop[1], True, 0, 0, 0)


class Notes(unittest.TestCase):
    def test_writes_become_notes(self):
        snap = snapshot(dsp={0x04: 3, 0x14: 5, notes.EON: 0x01})
        t = lambda s: int(s * CLOCK)                  # noqa: E731
        writes = [Write(t(0.00), 0x02, 0x00), Write(t(0.00), 0x03, 0x10),      # voice 0: pitch 0x1000
                  Write(t(0.00), 0x00, 64), Write(t(0.00), 0x01, 0xC0),       # volume +64 / -64
                  Write(t(0.01), notes.KON, 0x01),
                  Write(t(0.05), 0x02, 0x40),                                 # a bend while it sounds
                  Write(t(0.10), notes.KOFF, 0x01),
                  Write(t(0.20), notes.KON, 0x02), Write(t(0.30), notes.KON, 0x02),   # voice 1, keyed twice
                  Write(t(0.40), notes.KOFF, 0x04), Write(t(0.41), notes.KON, 0x04)]  # keyed while held off
        found = notes.decode(snap, writes)
        self.assertEqual([n.voice for n in found], [0, 1, 1])
        a, b, c = found
        self.assertAlmostEqual(a.start, 0.01 + notes.KEY_ON_DELAY, places=6)
        self.assertAlmostEqual(a.end, 0.10, places=6)
        self.assertEqual((a.sample, a.pitch, a.volume, a.echo), (3, 0x1000, (64, -64), True))
        self.assertEqual([p for _, p in a.bends], [0x1040])
        self.assertEqual(b.sample, 5)
        self.assertAlmostEqual(b.end, 0.30, places=6)    # ended by its voice's next key-on
        self.assertIsNone(c.end)                         # still sounding when the writes ran out


class Tuning(unittest.TestCase):
    def test_a_loop_of_whole_cycles(self):
        # 500 Hz at 32 kHz: 64 samples a cycle, the loop holding ten
        pcm = [12000 * math.sin(2 * math.pi * i / 64) + 3000 * math.sin(4 * math.pi * i / 64) for i in range(1280)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm, (640, 1280))), 500.0, delta=0.5)

    def test_a_pluck_without_a_loop(self):
        pcm = [20000 * math.exp(-i / 9000) * math.sin(2 * math.pi * 220 * i / 32000) for i in range(8000)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm)), 220.0, delta=220 * 0.01)

    def test_noise_has_no_pitch(self):
        r = random.Random(3)
        self.assertIsNone(tuning.fundamental(sample([r.uniform(-20000, 20000) for _ in range(6000)])))

    def test_names(self):
        self.assertEqual(tuning.name(tuning.midi(440.0, 0x1000)), "A4")
        self.assertEqual(tuning.name(tuning.midi(440.0, 0x0800)), "A3")       # half the rate: an octave down
        self.assertEqual(tuning.name(69.25), "A4 +25c")


@unittest.skipUnless(emulate.available(), "needs the compiled emulator (bitcomposer-emu)")
class Emulator(unittest.TestCase):
    def test_a_driver_runs_and_its_writes_come_back(self):
        # MOV $F2,#$4C ; MOV $F3,#$01 (key on voice 0) ; BRA to itself
        snap = snapshot(bytes([0x8F, 0x4C, 0xF2, 0x8F, 0x01, 0xF3, 0x2F, 0xFE]))
        run = emulate.run(snap, 0.01)
        self.assertGreater(run.instructions, 1000)
        self.assertEqual([(w.reg, w.value) for w in run.writes], [(notes.KON, 0x01)])
        self.assertAlmostEqual(run.seconds, 0.01, delta=0.001)
        self.assertEqual(len(notes.decode(snap, run.writes)), 1)


if __name__ == "__main__":
    unittest.main()
