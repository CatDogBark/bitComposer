"""IT instruments, and SPC to IT (synthetic: no game files).
Run with: python3 -m unittest discover -s tests"""
import ctypes
import math
import struct
import unittest

from support import os, tempfile, unittest  # noqa: F401,F811
from bitcomposer import it_format as itf  # noqa: E402
from bitcomposer import spc  # noqa: E402
from bitcomposer.spc import convert, emulate, notes  # noqa: E402
from bitcomposer.spc.emulate import CLOCK, Write  # noqa: E402


def _have_openmpt():
    try:
        from bitcomposer.player.openmpt import lib
        lib()
        return True
    except Exception:
        return False


def render(path, seconds=1.0):
    from bitcomposer.player.openmpt import Module
    m = Module(path)
    buf = (ctypes.c_int16 * 64000)()
    out = []
    while len(out) < 64000 * seconds:
        n = m.read_stereo(32000, buf, 32000)
        if not n:
            break
        out.extend(buf[:2 * n])
    return m, out


def block(shift, filt, nibbles, loop=False, end=False):
    out = bytearray([shift << 4 | filt << 2 | (2 if loop else 0) | (1 if end else 0)])
    for i in range(0, 16, 2):
        out.append((nibbles[i] & 0xF) << 4 | (nibbles[i + 1] & 0xF))
    return bytes(out)


class Instruments(unittest.TestCase):
    def write(self, d, instruments):
        n = 2000
        data = struct.pack(f"<{n}h", *(int(12000 * math.sin(2 * math.pi * i / 64)) for i in range(n)))
        smp = itf.ITSample(name="sine", data=data, length=n, loop=True, loop_start=0, loop_end=n, c5_speed=32000)
        pat = itf.ITPattern(rows=64, channels=1)
        pat.data[0][0] = itf.ITNote(note=60, instrument=1, volume=64)
        path = os.path.join(d, "song.it")
        itf.write_it_file(path, "test", [smp], [pat], [0], tempo=125, speed=6, num_channels=1,
                          instruments=instruments)
        with open(path, "rb") as fh:
            return fh.read(), path

    def test_instrument_mode_in_the_header_and_its_block(self):
        with tempfile.TemporaryDirectory() as d:
            ins = itf.ITInstrument(name="sine env", sample=1, envelope=[(0, 64), (10, 32), (20, 32)])
            raw, _ = self.write(d, [ins])
            ordnum, insnum, smpnum = struct.unpack_from("<HHH", raw, 0x20)
            flags = struct.unpack_from("<H", raw, 0x2C)[0]
            self.assertEqual((insnum, smpnum), (1, 1))
            self.assertTrue(flags & 4)                                          # instruments in use
            at = struct.unpack_from("<I", raw, 0xC0 + ordnum)[0]               # the instrument offset table
            self.assertEqual(raw[at:at + 4], b"IMPI")
            self.assertEqual(raw[at + 64:at + 66], bytes([0, 1]))              # note 0 plays sample 1
            env = raw[at + 304:at + 304 + 82]
            self.assertEqual((env[0] & 1, env[1]), (1, 3))                     # on, three nodes
            self.assertEqual(struct.unpack_from("<BH", env, 6 + 3), (32, 10))  # second node
            plain, _ = self.write(d, None)
            self.assertFalse(struct.unpack_from("<H", plain, 0x2C)[0] & 4)    # without: sample mode as before

    @unittest.skipUnless(_have_openmpt(), "needs libopenmpt")
    def test_libopenmpt_plays_it_and_the_envelope_shapes_it(self):
        with tempfile.TemporaryDirectory() as d:
            _, flat = self.write(d, [itf.ITInstrument(sample=1, envelope=[(0, 64)])])
            _, a = render(flat)
            _, falling = self.write(d, [itf.ITInstrument(sample=1, envelope=[(0, 64), (20, 0)])])
            _, b = render(falling)
            late = lambda x: sum(abs(v) for v in x[32000:64000])                # noqa: E731
            self.assertGreater(late(a), 0)
            self.assertLess(late(b), 0.1 * late(a))                          # faded out by then


class MasterVolume(unittest.TestCase):
    def test_master_volume_over_a_run(self):
        data = bytearray(spc.SIZE)
        data[:len(spc.MAGIC)] = spc.MAGIC
        data[spc.DSP + notes.MVOLL] = data[spc.DSP + notes.MVOLR] = 0x60
        snap = spc.read(bytes(data))
        writes = [Write(int(1.0 * CLOCK), notes.MVOLL, 0x30), Write(int(1.0 * CLOCK), notes.MVOLR, 0x30),
                  Write(int(2.0 * CLOCK), notes.MVOLL, 0x30)]                  # no change: not listed
        mv = notes.master_volume(snap, writes)
        self.assertEqual([(round(t, 3), l, r) for t, l, r in mv], [(0.0, 96, 96), (1.0, 48, 96), (1.0, 48, 48)])


class Echo(unittest.TestCase):
    BANDPASS = (52, 51, 0, -39, -27, 1, -4, -21)                         # passes 2-8 kHz, little at DC

    def sine(self, hz, n=3200):
        return [int(10000 * math.sin(2 * math.pi * hz * i / 32000)) for i in range(n)]

    def test_gains_follow_the_note_not_dc(self):
        hi = convert.echo_gains(self.sine(3000), (0, 3200), 0x1000, self.BANDPASS, 2)
        lo = convert.echo_gains(self.sine(200), (0, 3200), 0x1000, self.BANDPASS, 2)
        self.assertAlmostEqual(hi[0], 1.06, delta=0.05)
        self.assertAlmostEqual(lo[0], 0.16, delta=0.03)
        self.assertAlmostEqual(hi[1], hi[0] ** 2, delta=0.05)                # two passes through the filter
        self.assertAlmostEqual(convert.echo_gains(self.sine(200), (0, 3200), 0x1000 * 15, self.BANDPASS, 1)[0],
                               hi[0], delta=0.1)                             # the same sample, played 15x up

    def test_the_coloured_copy_keeps_its_length_and_loses_the_bass(self):
        rms = lambda a: math.sqrt(sum(v * v for v in a) / len(a))      # noqa: E731
        for hz, keep in ((3000, 0.9), (200, 0.25)):
            data, fit = convert.echo_coloured(self.sine(hz), (1600, 3200), 1.0, self.BANDPASS)
            self.assertEqual(len(data), 3200)
            ratio = rms(data[1600:]) / fit / rms(self.sine(hz)[1600:])
            self.assertGreater(ratio, keep) if hz == 3000 else self.assertLess(ratio, keep)


class Envelopes(unittest.TestCase):
    def test_a_gain_fade_written_mid_note(self):
        # ADSR FF/E0 holds at once; at sample 3200 the driver switches to GAIN 0x9E, a fast linear fade
        track = convert.envelope_track(0xFF, 0xE0, 0xB8, [(3200, 0x00, 0xE0, 0x9E)], 6400)
        level = dict(track)
        self.assertEqual(track[-1][1], 0)
        self.assertAlmostEqual(track[-1][0], 3200 + 128, delta=4)           # 2039 down by 32 every 2 samples
        self.assertEqual(max(lv for s, lv in track if s < 3200), 2047)
        self.assertEqual(len(convert.envelope_track(0xFF, 0xE0, 0xB8, [], 10 * 32000)), 3)   # attack, decay, held: no more
        self.assertIn(3200, level)

    def test_adsr_rises_decays_and_holds(self):
        # attack 15 (at once), decay 7, sustain level 3 (boundary 0x400), sustain rate 0 (hold)
        nodes = convert.envelope(0x8F | 0x70, 3 << 5, 0, 100.0)
        self.assertLessEqual(len(nodes), 25)
        self.assertGreater(nodes[0][1], 40)                                  # the swell, averaged over its tick
        self.assertAlmostEqual(nodes[-1][1], 32, delta=2)                  # held at the boundary

    def test_direct_gain_is_flat(self):
        nodes = convert.envelope(0x00, 0x00, 0x40, 100.0)                  # GAIN direct, level 0x40 << 4
        self.assertTrue(all(level == 32 for _, level in nodes))


@unittest.skipUnless(emulate.available() and _have_openmpt(), "needs the compiled emulator and libopenmpt")
class Convert(unittest.TestCase):
    def test_a_tiny_driver_becomes_a_playable_module(self):
        data = bytearray(spc.SIZE)
        data[:len(spc.MAGIC)] = spc.MAGIC
        data[0x23] = 27
        data[0x25:0x27] = (0x0200).to_bytes(2, "little")
        data[0x2B] = 0xEF
        # a looped square-ish sample at 0x0400, its directory entry 0 at 0x1000
        smp = block(11, 0, [7, 7, 7, 7, -7, -7, -7, -7] * 2) + block(11, 0, [7, 7, 7, 7, -7, -7, -7, -7] * 2, loop=True, end=True)
        data[spc.RAM + 0x0400:spc.RAM + 0x0400 + len(smp)] = smp
        data[spc.RAM + 0x1000:spc.RAM + 0x1004] = (0x0400).to_bytes(2, "little") + (0x0409).to_bytes(2, "little")
        # driver: DIR=0x10, V0 SRCN=0 PITCH=0x1000 VOL=100/100 GAIN direct 0x7F, KON voice 0, then spin
        code = bytearray()
        # with an echo: 32 ms (EDL 2), echo volume 0x40, feedback 0x40, FIR passing straight, voice 0 sending
        for reg, val in ((0x5D, 0x10), (0x04, 0), (0x02, 0x00), (0x03, 0x10), (0x00, 100), (0x01, 100),
                         (0x05, 0x00), (0x07, 0x7F), (0x0C, 0x7F), (0x1C, 0x7F), (0x6D, 0x80), (0x7D, 0x02),
                         (0x2C, 0x40), (0x3C, 0x40), (0x0D, 0x40), (0x0F, 0x7F), (0x4D, 0x01), (0x6C, 0x00),
                         (0x4C, 0x01)):
            code += bytes([0x8F, reg, 0xF2, 0x8F, val, 0xF3])
        code += bytes([0x2F, 0xFE])
        data[spc.RAM + 0x0200:spc.RAM + 0x0200 + len(code)] = code
        snap = spc.read(bytes(data))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tiny.it")
            song = convert.convert(snap, 1.0, path)
            info = song["info"]
            self.assertEqual(info["notes"], 1)
            self.assertEqual((info["samples"], info["instruments"]), (2, 2))    # the sample and its echo-coloured copy
            self.assertGreaterEqual(info["repeats"], 1)                          # the echo, as repeats
            # the first repeat: voice 0's first echo channel, 32 ms after the note
            hits = [(r, ch) for p, pat in enumerate(song["patterns"]) for r, row in enumerate(pat.data)
                    for ch, c in enumerate(row) if 0 < c.note < 120]
            (r0, _), = [h for h in hits if h[1] == 0]
            echoes = [r for r, ch in hits if ch == 8]
            self.assertTrue(echoes)
            self.assertAlmostEqual(echoes[0] - r0, round(0.032 * info["row_hz"]), delta=1)
            m, pcm = render(path, 0.5)
            self.assertGreater(max(abs(v) for v in pcm), 1000)               # the note sounds


if __name__ == "__main__":
    unittest.main()
