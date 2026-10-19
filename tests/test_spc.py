"""SPC snapshots and BRR samples (synthetic: no game files in the repository).
Run with: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import random
import unittest
import wave

from support import os, tempfile, unittest  # noqa: F401,F811
from bitcomposer import spc  # noqa: E402
from bitcomposer.spc import brr  # noqa: E402
from bitcomposer.spc.__main__ import main as spc_main  # noqa: E402


def block(shift, filt, nibbles, loop=False, end=False):
    """One BRR block from 16 nibbles in -8..7."""
    assert len(nibbles) == 16
    out = bytearray([shift << 4 | filt << 2 | (2 if loop else 0) | (1 if end else 0)])
    for i in range(0, 16, 2):
        out.append((nibbles[i] & 0xF) << 4 | (nibbles[i + 1] & 0xF))
    return bytes(out)


def bsnes_decode(blocks: bytes) -> list[int]:
    """A second decoder, written the way bsnes does it (the stored, doubled
    samples feed the filters), to check brr's formulation against."""
    buf, out = [0, 0], []
    for b in range(0, len(blocks), 9):
        hdr = blocks[b]
        shift, filt = hdr >> 4, (hdr >> 2) & 3
        for byte in blocks[b + 1:b + 9]:
            for nib in (byte >> 4, byte & 0xF):
                s = nib - 16 if nib > 7 else nib
                if shift <= 12:
                    s = (s << shift) >> 1
                else:
                    s = s & ~0x7FF
                p1, p2 = buf[-1], buf[-2] >> 1
                if filt == 1:
                    s += (p1 >> 1) + ((-p1) >> 5)
                elif filt == 2:
                    s += p1 - p2 + (p2 >> 4) + ((p1 * -3) >> 6)
                elif filt == 3:
                    s += p1 - p2 + ((p1 * -13) >> 7) + ((p2 * 3) >> 4)
                s = max(-32768, min(32767, s))
                s = ((s * 2) & 0xFFFF) - (0x10000 if (s * 2) & 0x8000 else 0)   # (int16)(s << 1)
                buf.append(s)
                out.append(s)
    return out


def snapshot_bytes(ram_at: dict, dsp_at: dict, tags: bytes = b"", text_tags=True) -> bytes:
    data = bytearray(spc.SIZE)
    data[:len(spc.MAGIC)] = spc.MAGIC
    data[0x21:0x23] = b"\x1a\x1a"
    data[0x23] = 26
    data[0x24] = 30
    data[0x25:0x27] = (0x0430).to_bytes(2, "little")
    data[0x27:0x2C] = bytes([1, 2, 3, 0x02, 0xEF])
    data[0x2E:0x2E + len(tags)] = tags
    for addr, b in ram_at.items():
        data[spc.RAM + addr:spc.RAM + addr + len(b)] = b
    for reg, v in dsp_at.items():
        data[spc.DSP + reg] = v
    return bytes(data)


class BRR(unittest.TestCase):
    def test_the_filters_are_the_hardware_arithmetic(self):
        """Random blocks, every shift and filter: brr agrees with a decoder
        written the bsnes way, sample for sample."""
        r = random.Random(7)
        for _ in range(200):
            blocks = b"".join(block(r.randrange(16), r.randrange(4), [r.randrange(-8, 8) for _ in range(16)])
                              for _ in range(4))
            out = brr.array("h")
            p1 = p2 = 0
            for b in range(0, len(blocks), 9):
                _, p1, p2 = brr.decode_block(blocks, b, p1, p2, out)
            self.assertEqual(list(out), bsnes_decode(blocks))

    def test_a_sum_past_15_bits_wraps_as_on_the_chip(self):
        ram = block(12, 0, [7] * 16) + block(12, 1, [7] * 16, end=True)
        s = brr.decode(ram, 0, 0)
        self.assertEqual(s.pcm[15], 28672)                  # 7 << 12 >> 1, doubled
        # 14336 + 14336 + (-14336 >> 4) = 27776, past 16383: bit 15 is lost
        self.assertEqual(s.pcm[16], 2 * (((27776 & 0x7FFF) ^ 0x4000) - 0x4000))
        self.assertFalse(s.loops)

    def test_a_loop_is_stored_as_it_sounds_on_the_repeats(self):
        """A loop block that predicts from the samples before it decodes
        one way on the first pass and another on the repeats; the sample's
        loop is a repeat pass, so it plays seamlessly round and round."""
        intro = block(8, 0, [3, -2, 5, 1] * 4)
        looped = block(8, 1, [1, 0, -1, 0] * 4, loop=True) + block(8, 0, [4, 4, -4, -4] * 4, loop=True, end=True)
        ram = intro + looped
        s = brr.decode(ram, 0, 9)
        self.assertTrue(s.loops and s.seamless)
        self.assertGreaterEqual(s.loop_start, 48)           # not the first pass's loop (frames 16-48)
        self.assertEqual(s.loop_end - s.loop_start, 32)
        # one more pass from the state the loop ends on reproduces it exactly
        tail = s.pcm[s.loop_end - 2:s.loop_end]
        again = brr.array("h")
        p1, p2 = tail[1] // 2, tail[0] // 2
        for b in (9, 18):
            _, p1, p2 = brr.decode_block(ram, b, p1, p2, again)
        self.assertEqual(list(again), list(s.pcm[s.loop_start:s.loop_end]))

    def test_an_unfiltered_loop_stays_where_it_was(self):
        ram = block(8, 0, [1] * 16) + block(8, 0, [2] * 16, loop=True, end=True)
        s = brr.decode(ram, 0, 9)
        self.assertEqual((s.loop_start, s.loop_end, len(s)), (16, 32, 32))

    def test_no_end_flag_is_no_sample(self):
        ram = bytearray(block(8, 0, [1] * 16) * 20)
        self.assertIsNone(brr.decode(ram, 0, 0, max_blocks=10))


class Snapshots(unittest.TestCase):
    def make(self, **kw):
        sample = block(10, 0, [5, -5] * 8) + block(10, 0, [1, 2] * 8, loop=True, end=True)
        garbage = block(14, 3, [7] * 16, end=True)           # shift 14: no encoder writes it
        ram = {0x1000: (0x0400).to_bytes(2, "little") + (0x0409).to_bytes(2, "little")
                       + (0x0500).to_bytes(2, "little") + (0x0500).to_bytes(2, "little"),
               0x0400: sample, 0x0500: garbage}
        dsp = {0x00: 100, 0x01: 0xF6, 0x02: 0x00, 0x03: 0x10, 0x04: 0, 0x05: 0x8F, 0x06: 0xE0, 0x08: 90,
               spc.DIR: 0x10, spc.EON: 0x01, spc.EDL: 5, spc.EFB: 0x50, spc.EVOLL: 0x20, spc.EVOLR: 0xE0,
               spc.FIR[0]: 0x7F, spc.MVOLL: 0x40, spc.MVOLR: 0x40}
        tags = (b"Battle Theme".ljust(32, b"\0") + b"Some Game".ljust(32, b"\0") + b"dumper".ljust(16, b"\0")
                + b"".ljust(32, b"\0") + b"10/18/2026\0" + b"120" + b"10000" + b"Composer".ljust(32, b"\0"))
        return snapshot_bytes(ram, dsp, kw.get("tags", tags))

    def test_what_a_snapshot_holds(self):
        snap = spc.read(self.make())
        self.assertEqual((snap.pc, snap.a, snap.x, snap.y, snap.sp), (0x0430, 1, 2, 3, 0xEF))
        t = snap.tags
        self.assertEqual((t.title, t.game, t.artist, t.date, t.length_s, t.fade_ms, t.binary),
                         ("Battle Theme", "Some Game", "Composer", "10/18/2026", 120, 10000, False))
        v = snap.voices[0]
        self.assertEqual((v.volume, v.pitch, v.sample, v.adsr, v.attack, v.decay, v.sustain_level),
                         ((100, -10), 0x1000, 0, True, 15, 0, 7))
        self.assertTrue(v.sounding and v.echo and not v.noise)
        self.assertFalse(snap.voices[1].sounding)
        e = snap.echo
        self.assertEqual((e.delay_ms, e.feedback, e.volume, e.fir[0], e.voices), (80, 0.625, (0.25, -0.25), 127, (0,)))
        self.assertTrue(e.on)
        self.assertEqual(snap.main_volume, (0.5, 0.5))
        # the playing sample decodes; the garbage entry is left out unless everything is asked for
        self.assertEqual(list(snap.samples()), [0])
        s = snap.samples()[0]
        self.assertEqual((len(s), s.loop_start, s.loop_end, s.seamless), (32, 16, 32, True))
        self.assertIn(1, snap.samples(everything=True))

    def test_binary_tags(self):
        tags = bytearray(b"Title".ljust(32, b"\0") + b"Game".ljust(32, b"\0") + bytes(16 + 32))
        tags += (20261018).to_bytes(4, "little") + bytes(7) + (95).to_bytes(3, "little") + (8000).to_bytes(4, "little")
        tags += b"Artist".ljust(32, b"\0")
        t = spc.read(self.make(tags=bytes(tags))).tags
        self.assertEqual((t.binary, t.date, t.length_s, t.fade_ms, t.artist), (True, "2026-10-18", 95, 8000, "Artist"))

    def test_not_an_spc(self):
        with self.assertRaises(spc.SPCError):
            spc.read(b"RIFF....WAVE")
        with self.assertRaises(spc.SPCError):
            spc.read(spc.MAGIC + b"short")

    def test_export_writes_each_sample_once(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("a.spc", "b.spc"):
                with open(os.path.join(d, name), "wb") as fh:
                    fh.write(self.make())
            out = os.path.join(d, "out")
            with contextlib.redirect_stdout(io.StringIO()):
                code = spc_main(["--export", out, os.path.join(d, "a.spc"), os.path.join(d, "b.spc")])
            self.assertEqual(code, 0)
            index = json.load(open(os.path.join(out, "samples.json")))
            self.assertEqual(index["rate"], 32000)
            self.assertEqual(len(index["samples"]), 1)                    # shared by both: written once
            row = index["samples"][0]
            self.assertEqual([f["snapshot"] for f in row["from"]], ["a.spc", "b.spc"])
            with wave.open(os.path.join(out, row["file"])) as w:
                self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()),
                                 (32000, 1, 2, row["frames"]))


if __name__ == "__main__":
    unittest.main()
