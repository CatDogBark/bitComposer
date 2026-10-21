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

    def test_envelope_writes_while_a_note_sounds(self):
        # a driver releasing with a GAIN fade: ADSR1 off, then GAIN 0x9E, while the note sounds
        snap = snapshot(dsp={0x05: 0xFF, 0x06: 0xE0, 0x07: 0xB8, 0x03: 0x10})
        t = lambda s: int(s * CLOCK)                  # noqa: E731
        writes = [Write(t(0.01), notes.KON, 0x01), Write(t(0.10), 0x05, 0x00), Write(t(0.10), 0x07, 0x9E),
                  Write(t(0.10), 0x07, 0x9E), Write(t(0.30), notes.KOFF, 0x01), Write(t(0.40), 0x07, 0x00)]
        n, = notes.decode(snap, writes)
        self.assertEqual((n.adsr, n.gain), ((0xFF, 0xE0), 0xB8))
        self.assertEqual([e[1:] for e in n.envelopes], [(0x00, 0xE0, 0xB8), (0x00, 0xE0, 0x9E)])  # repeats and after-end writes left out

    def test_pitch_modulation_while_a_note_sounds(self):
        snap = snapshot(dsp={0x13: 0x10, 0x23: 0x10})
        t = lambda s: int(s * CLOCK)                  # noqa: E731
        writes = [Write(t(0.01), notes.KON, 0x03), Write(t(0.05), notes.PMON, 0x03),   # voice 0's bit does nothing
                  Write(t(0.08), notes.PMON, 0x00), Write(t(0.10), notes.KON, 0x02)]
        found = notes.decode(snap, writes)
        self.assertEqual([(n.voice, n.pmon) for n in found], [(0, False), (1, True), (1, False)])

    def test_keyed_on_as_its_key_off_clears(self):
        # a driver keying voices off and on in one go and clearing KOFF just after (Factor 5's)
        snap = snapshot(dsp={0x03: 0x10, 0x13: 0x10})
        t = int(0.1 * CLOCK)
        sample = CLOCK // emulate.RATE
        writes = [Write(t, notes.KOFF, 0x03), Write(t, notes.KON, 0x03),
                  Write(t + sample // 2, notes.KOFF, 0x02),          # voice 0 let go half a sample later: it sounds
                  Write(t + 8 * sample, notes.KOFF, 0x00)]           # voice 1 eight samples later: released first
        self.assertEqual([n.voice for n in notes.decode(snap, writes)], [0])


class Tuning(unittest.TestCase):
    def test_a_loop_of_whole_cycles(self):
        # 500 Hz at 32 kHz: 64 samples a cycle, the loop holding ten
        pcm = [12000 * math.sin(2 * math.pi * i / 64) + 3000 * math.sin(4 * math.pi * i / 64) for i in range(1280)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm, (640, 1280))), 500.0, delta=0.5)

    def test_a_loop_of_cycles_a_fraction_of_a_sample_long(self):
        # 312.5 Hz at 32 kHz: 102.4 samples a cycle, the loop holding five (FFVI's bass loops are so):
        # no whole-sample divisor of the loop is one cycle, and the shortest clean one is all five
        f = 2 * math.pi * 312.5 / 32000
        pcm = [12000 * math.sin(f * i) + 6000 * math.sin(2 * f * i) + 2000 * math.sin(4 * f * i) for i in range(1024)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm, (512, 1024))), 312.5, delta=0.5)

    def test_a_pluck_without_a_loop(self):
        pcm = [20000 * math.exp(-i / 9000) * math.sin(2 * math.pi * 220 * i / 32000) for i in range(8000)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm)), 220.0, delta=220 * 0.01)

    def test_a_pluck_with_a_bright_noise_matching_an_octave_down(self):
        # a bass cycle of 139 samples (230 Hz) under a bright noise that repeats every second cycle (a
        # slap's, as FFVI's bass has): the wave as a whole repeats better two cycles on, but the cycle is the pitch
        r = random.Random(5)
        rough = [r.uniform(-4600, 4600) for _ in range(279)]
        noise = [b - a for a, b in zip(rough, rough[1:])]
        f = 2 * math.pi / 139
        pcm = [math.exp(-i / 12000) * (12000 * math.sin(f * i) + 6000 * math.sin(2 * f * i) + 5000 * math.sin(3 * f * i)
                                       + noise[i % 278]) for i in range(8000)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm)), 32000 / 139, delta=230 * 0.01)

    def test_a_struck_tone_whose_attack_glides(self):
        # a tom's pitch falls through its first 150 ms and holds (FFVI's low drum, Mt. Koltz's bass):
        # measured where it holds, not in the glide
        phase, pcm = 0.0, []
        for i in range(12000):
            hz = 227 + 120 * math.exp(-i / 1500)
            phase += 2 * math.pi * hz / 32000
            pcm.append(14000 * math.exp(-i / 20000) * math.sin(phase))
        self.assertAlmostEqual(tuning.fundamental(sample(pcm)), 227.0, delta=227 * 0.01)

    def test_a_loop_with_a_true_sub_harmonic(self):
        # 71 Hz under a stronger 142 Hz, the lower partial sounding (FFVI's strings' bass): the low
        # harmonics say the cycle is the long one, however much better the short lag matches on top
        f = 2 * math.pi * 71.2 / 32000
        pcm = [3000 * math.sin(f * i) + 12000 * math.sin(2 * f * i) + 3000 * math.sin(3 * f * i) + 3000 * math.sin(4 * f * i)
               for i in range(5840)]
        self.assertAlmostEqual(tuning.fundamental(sample(pcm, (0, 5840))), 71.2, delta=0.5)

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

    def test_the_snapshot_s_own_key_on(self):
        # taken as the song's first note keyed on: KON 01 in the snapshot, voice 0 set up (the tiny
        # driver's registers, no echo), and a driver that writes nothing: the note plays from the start
        from test_spc_convert import TINY, tiny
        data = bytearray(tiny(()).raw)
        for reg, v in TINY + ((0x4C, 0x01),):
            data[spc.DSP + reg] = 0 if reg == 0x4D else v
        snap = spc.read(bytes(data))
        run = emulate.run(snap, 0.1, audio=True)
        self.assertEqual(run.writes, [])
        self.assertGreater(max(map(abs, array("h", run.audio))), 1000)
        n, = notes.decode(snap, run.writes, keyons=run.keyons)
        self.assertAlmostEqual(n.start, notes.KEY_ON_DELAY, places=6)
        self.assertIsNotNone(n.brr)
        # dumped as the driver wrote that KON: its write, before the first poll, is the one key-on
        n, = notes.decode(snap, [Write(0, notes.KON, 0x01)] + run.writes, keyons=run.keyons)
        self.assertIsNotNone(n.brr)

    def test_a_key_on_under_key_off_sounds_as_the_snes_chip_says(self):
        # KOFF, KON, then KOFF cleared at once (sounds) or left set (released before it sounds), against the emulator
        from test_spc_convert import TINY, tiny
        for after, sounds in (((0x5C, 0x00),), True), ((), False):
            snap = tiny(TINY + ((0x5C, 0x01), (0x4C, 0x01)) + after)
            run = emulate.run(snap, 0.1, audio=True)
            self.assertEqual(max(map(abs, array("h", run.audio))) > 100, sounds)
            self.assertEqual(len(notes.decode(snap, run.writes, keyons=run.keyons)), int(sounds))

    @unittest.skipUnless(emulate.available() and hasattr(__import__("bitcomposer_emu"), "solos"), "needs emulator 0.3")
    def test_each_voice_alone_from_one_run(self):
        # two voices keyed, voice 0 sending to the echo (DIR 0x10, a looped sample at 0x0400): each voice alone
        # from one run is what a run with the other muted gives, sample for sample, echo and all
        regs = ((0x5D, 0x10), (0x04, 0), (0x03, 0x10), (0x00, 60), (0x01, 60), (0x07, 0x7F), (0x14, 0), (0x13, 0x08),
                (0x10, 40), (0x11, 70), (0x17, 0x7F), (0x0C, 0x7F), (0x1C, 0x7F), (0x6D, 0x80), (0x7D, 0x02), (0x2C, 0x40),
                (0x3C, 0x40), (0x0D, 0x50), (0x0F, 0x7F), (0x4D, 0x01), (0x6C, 0x00), (0x4C, 0x03))
        code = b"".join(bytes([0x8F, r, 0xF2, 0x8F, v, 0xF3]) for r, v in regs) + bytes([0x2F, 0xFE])
        data = bytearray(snapshot(code).raw)
        blk = bytes([0xB0] + [0x77, 0x77, 0x99, 0x99] * 2) + bytes([0xB3] + [0x77, 0x77, 0x99, 0x99] * 2)
        data[spc.RAM + 0x0400:spc.RAM + 0x0400 + len(blk)] = blk
        data[spc.RAM + 0x1000:spc.RAM + 0x1004] = (0x0400).to_bytes(2, "little") + (0x0409).to_bytes(2, "little")
        snap = spc.read(bytes(data))
        alone = emulate.solos(snap, 0.3)
        for v in (0, 1):
            muted = array("h", emulate.run(snap, 0.3, audio=True, mute=0xFF ^ (1 << v)).audio)
            self.assertGreater(max(map(abs, muted)), 100)
            self.assertEqual(alone[v], muted)
        self.assertFalse(any(alone[2]))


if __name__ == "__main__":
    unittest.main()
