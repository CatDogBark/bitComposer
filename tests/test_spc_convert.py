"""IT instruments, and SPC to IT (synthetic: no game files).
Run with: python3 -m unittest discover -s tests"""
import ctypes
import math
import struct
import unittest

from support import os, tempfile, unittest  # noqa: F401,F811
from bitcomposer import it_format as itf  # noqa: E402
from bitcomposer import spc  # noqa: E402
from bitcomposer.spc import convert, emulate, it_song, notes, snes_chip  # noqa: E402
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


# the tiny driver's registers: DIR=0x10, voice 0 SRCN=0 PITCH=0x1000 VOL=100/100 GAIN direct 0x7F, KON voice 0;
# with an echo: 32 ms (EDL 2), echo volume 0x40, feedback 0x40, FIR passing straight, voice 0 sending
TINY = ((0x5D, 0x10), (0x04, 0), (0x02, 0x00), (0x03, 0x10), (0x00, 100), (0x01, 100),
        (0x05, 0x00), (0x07, 0x7F), (0x0C, 0x7F), (0x1C, 0x7F), (0x6D, 0x80), (0x7D, 0x02),
        (0x2C, 0x40), (0x3C, 0x40), (0x0D, 0x40), (0x0F, 0x7F), (0x4D, 0x01), (0x6C, 0x00))
KON0 = ((0x4C, 0x01),)


def tiny(regs=TINY + KON0):
    """A snapshot whose driver writes `regs` to the SNES chip, then spins: a
    looped square-ish sample at 0x0400, its directory entry 0 at 0x1000."""
    data = bytearray(spc.SIZE)
    data[:len(spc.MAGIC)] = spc.MAGIC
    data[0x23] = 27
    data[0x25:0x27] = (0x0200).to_bytes(2, "little")
    data[0x2B] = 0xEF
    smp = block(11, 0, [7, 7, 7, 7, -7, -7, -7, -7] * 2) + block(11, 0, [7, 7, 7, 7, -7, -7, -7, -7] * 2, loop=True, end=True)
    data[spc.RAM + 0x0400:spc.RAM + 0x0400 + len(smp)] = smp
    data[spc.RAM + 0x1000:spc.RAM + 0x1004] = (0x0400).to_bytes(2, "little") + (0x0409).to_bytes(2, "little")
    code = bytearray()
    for reg, val in regs:
        code += bytes([0x8F, reg, 0xF2, 0x8F, val, 0xF3])
    code += bytes([0x2F, 0xFE])
    data[spc.RAM + 0x0200:spc.RAM + 0x0200 + len(code)] = code
    return spc.read(bytes(data))


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

    def test_a_keyboard_maps_notes_to_samples(self):
        with tempfile.TemporaryDirectory() as d:
            keys = [(k, 0) for k in range(120)]
            keys[5] = (60, 1)                                                   # note 5 plays sample 1 at C-5
            raw, _ = self.write(d, [itf.ITInstrument(name="keys", keyboard=keys)])
            at = struct.unpack_from("<I", raw, 0xC0 + struct.unpack_from("<H", raw, 0x20)[0])[0]
            self.assertEqual(raw[at + 64 + 10:at + 64 + 12], bytes([60, 1]))
            self.assertEqual(raw[at + 64:at + 66], bytes([0, 0]))

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
        hi = snes_chip.echo_gains(self.sine(3000), (0, 3200), 0x1000, self.BANDPASS, 2)
        lo = snes_chip.echo_gains(self.sine(200), (0, 3200), 0x1000, self.BANDPASS, 2)
        self.assertAlmostEqual(hi[0], 1.06, delta=0.05)
        self.assertAlmostEqual(lo[0], 0.16, delta=0.03)
        self.assertAlmostEqual(hi[1], hi[0] ** 2, delta=0.05)                # two passes through the filter
        self.assertAlmostEqual(snes_chip.echo_gains(self.sine(200), (0, 3200), 0x1000 * 15, self.BANDPASS, 1)[0],
                               hi[0], delta=0.1)                             # the same sample, played 15x up

    def test_each_trip_round_the_echo_adds_the_filter_s_span(self):
        click = [0] * 100 + [10000] + [0] * 99
        for k in (1, 2, 3):                                                  # one tap 7 samples back: 7 later a trip
            data, _ = snes_chip.echo_coloured(click, None, 1.0, (127, 0, 0, 0, 0, 0, 0, 0), k)
            self.assertEqual(max(range(len(data)), key=lambda i: abs(data[i])), 100 + 7 * k)

    def test_the_coloured_copy_keeps_its_length_and_loses_the_bass(self):
        rms = lambda a: math.sqrt(sum(v * v for v in a) / len(a))      # noqa: E731
        for hz, keep in ((3000, 0.9), (200, 0.25)):
            data, fit = snes_chip.echo_coloured(self.sine(hz), (1600, 3200), 1.0, self.BANDPASS)
            self.assertEqual(len(data), 3200)
            ratio = rms(data[1600:]) / fit / rms(self.sine(hz)[1600:])
            self.assertGreater(ratio, keep) if hz == 3000 else self.assertLess(ratio, keep)


class Noise(unittest.TestCase):
    def test_the_hardware_noise_held_at_its_clock(self):
        smp = convert._noise_sample(22)                                    # a step every 16 samples
        v = struct.unpack(f"<{smp.length}h", smp.data)
        self.assertEqual((smp.length, smp.c5_speed), (32000, 32000))
        self.assertEqual(len(set(v[16:32])), 1)
        self.assertNotEqual(v[15], v[16])
        rms = math.sqrt(sum(x * x for x in v) / len(v))
        self.assertGreater(rms, 15000)                                     # full scale, as the hardware's


class Interpolation(unittest.TestCase):
    def test_samples_soften_as_the_snes_chip_reads_them(self):
        rms = lambda a: math.sqrt(sum(v * v for v in a) / len(a))      # noqa: E731
        for f, gain in ((0.02, 1.0), (0.25, 0.63), (0.4, 0.30)):          # the hardware's Gaussian, measured
            pcm = [round(10000 * math.sin(2 * math.pi * f * i)) for i in range(4000)]
            out = snes_chip.snes_interpolated(pcm, None)
            self.assertAlmostEqual(rms(out[100:-100]) / rms(pcm[100:-100]), gain, delta=0.02)

    def test_a_loop_is_filtered_as_it_repeats(self):
        pcm = [1000] * 50 + [5000, -5000] * 25 + [7, 7, 7]                 # a tail past the loop end is dropped
        out = snes_chip.snes_interpolated(pcm, (50, 100))
        self.assertEqual(len(out), 100)
        self.assertEqual(out[10], 1000)                                       # DC as it was
        self.assertAlmostEqual(abs(out[99]), 0.18 * 5000, delta=50)           # the loop's end, its start after it


class Envelopes(unittest.TestCase):
    def test_steps_fall_on_the_shared_counter(self):
        # GAIN 0xC6: a linear rise at rate 6, a step every 640 samples where the sample number is 536 mod 640
        on_note = snes_chip.envelope_track(0x00, 0x00, 0xC6, [], 3000)
        on_counter = snes_chip.envelope_track(0x00, 0x00, 0xC6, [], 3000, start=1000)
        self.assertEqual(on_note[:2], [(0, 32), (640, 64)])                  # from the note's start (an IT envelope)
        self.assertEqual(on_counter[:2], [(0, 0), (176, 32)])                # sample 1176 = 640 + 536
        self.assertEqual([s - t for (s, _), (t, _) in zip(on_counter[2:], on_counter[1:])], [640] * (len(on_counter) - 2))

    def test_a_gain_fade_written_mid_note(self):
        # ADSR FF/E0 holds at once; at sample 3200 the driver switches to GAIN 0x9E, a fast linear fade
        track = snes_chip.envelope_track(0xFF, 0xE0, 0xB8, [(3200, 0x00, 0xE0, 0x9E)], 6400)
        level = dict(track)
        self.assertEqual(track[-1][1], 0)
        self.assertAlmostEqual(track[-1][0], 3200 + 128, delta=4)           # 2039 down by 32 every 2 samples
        self.assertEqual(max(lv for s, lv in track if s < 3200), 2047)
        self.assertEqual(len(snes_chip.envelope_track(0xFF, 0xE0, 0xB8, [], 10 * 32000)), 3)   # attack, decay, held: no more
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


class Clock(unittest.TestCase):
    def test_rows_on_the_driver_s_clock_only_where_it_keeps_pace(self):
        self.assertTrue(convert._keeps_pace(80.0, 300))               # 8000/100 Hz: IT tempo 200, exact
        self.assertTrue(convert._keeps_pace(62.5, 2))                 # 62.4 rows: 3 ms behind after 2 s
        self.assertFalse(convert._keeps_pace(62.5, 60))               # 0.1 s behind after a minute
        self.assertFalse(convert._keeps_pace(8000 / 162, 30))         # 49.38 Hz on 49.2 rows


@unittest.skipUnless(emulate.available(), "needs the compiled emulator")
class ITSong(unittest.TestCase):
    """The IT half alone: lines written as cells, no emulator."""

    def test_a_line_as_cells(self):
        grid = it_song.Grid(1.0, 100.0, 2)
        grid.write(0, it_song.Line(row=10, end=20, note=60, instrument=1, volumes=[40] * 5 + [20] * 5, pan=128,
                                   pitch=[None, None] + [32] * 8))
        col = [grid.cell(r, 0) for r in range(100)]
        self.assertEqual((col[10].note, col[10].instrument, col[10].volume), (60, 1, 40))
        self.assertEqual((col[10].effect, col[10].effect_val), (itf.FX_SET_PAN, 128))
        self.assertEqual([c.volume for c in col[11:16]], [255, 255, 255, 255, 20])     # only where it changes
        self.assertEqual((col[12].effect, col[12].effect_val), (itf.FX_PORTA_UP, 0xF8))  # half a semitone: 8 x 4/64
        self.assertEqual(col[13].effect, 0)                                             # reached
        self.assertEqual(col[20].note, itf.NOTE_CUT)

    def test_pan_and_surround_only_where_the_channel_changes(self):
        grid = it_song.Grid(1.0, 100.0, 1)
        for row, pan, surround in ((0, 64, False), (10, 64, False), (20, 64, True), (30, 64, False), (40, 64, False)):
            grid.write(0, it_song.Line(row=row, end=row + 5, note=60, instrument=1, volumes=[40] * 5, pan=pan,
                                       surround=surround))
        fx = [(grid.cell(r, 0).effect, grid.cell(r, 0).effect_val) for r in (0, 10, 20, 30, 40)]
        self.assertEqual(fx, [(itf.FX_SET_PAN, 64), (0, 0), (itf.FX_SPECIAL, it_song.SURROUND_ON),
                              (itf.FX_SPECIAL, it_song.SURROUND_OFF), (itf.FX_SET_PAN, 64)])   # the pan again after

    def test_a_held_note_panned_as_it_sounds(self):
        # the pan moves on rows 3 and 6; on row 6 a pitch slide holds the effect column
        grid = it_song.Grid(1.0, 100.0, 1)
        grid.write(0, it_song.Line(row=0, end=10, note=60, instrument=1, volumes=[40] * 10, pan=0,
                                   pans=[0, 0, 0, 128, 128, 128, 255, 255, 255, 255], pitch=[None] * 6 + [8] * 4))
        col = [grid.cell(r, 0) for r in range(10)]
        self.assertEqual([(c.effect, c.effect_val) for c in col[:4]], [(itf.FX_SET_PAN, 0), (0, 0), (0, 0), (itf.FX_SET_PAN, 128)])
        self.assertEqual((col[6].effect, col[6].volume), (itf.FX_PORTA_UP, it_song.VOLUME_PAN + 64))
        grid.write(0, it_song.Line(row=20, end=25, note=60, instrument=1, volumes=[40] * 5, pan=255))
        self.assertEqual(grid.cell(20, 0).effect, 0)                                  # the channel is there already

    def test_the_song_ends_on_its_last_row(self):
        grid = it_song.Grid(1.37, 100.0, 1)
        self.assertEqual((sum(p.rows for p in grid.patterns), grid.last_row), (137, 136))
        self.assertFalse(grid.has(137))
        grid.write(0, it_song.Line(row=130, end=200, note=60, instrument=1, volumes=[40] * 7))
        self.assertTrue(all(grid.cell(r, 0).note != itf.NOTE_CUT for r in range(137)))   # its cut falls past the end
        grid.global_volume(0, 64, [(0, 64), (5, 32), (6, 32), (500, 10)])
        self.assertEqual([r for r in range(137) if grid.cell(r, 0).effect == it_song.FX_SET_GLOBAL_VOLUME], [5])

    def test_an_envelope_in_at_most_25_nodes(self):
        levels = [round(64 * abs(math.sin(i / 9))) for i in range(300)]
        nodes = it_song.envelope_nodes(levels)
        self.assertLessEqual(len(nodes), it_song.ENV_NODES)
        self.assertEqual((nodes[0], nodes[-1]), ((0, levels[0]), (299, levels[-1])))


@unittest.skipUnless(emulate.available(), "needs the compiled emulator")
class Voices(unittest.TestCase):
    def test_a_voice_muted_and_tapped(self):
        snap = tiny()
        loud = struct.unpack(f"<{6400 * 2}h", emulate.run(snap, 0.2, audio=True).audio[:6400 * 4])
        quiet = emulate.run(snap, 0.2, audio=True, mute=0x01).audio
        self.assertGreater(max(map(abs, loud)), 1000)
        self.assertFalse(any(quiet))                                     # voice 0 and its echo left out
        run = emulate.run(snap, 0.2, taps=0x03)
        self.assertEqual(set(run.tapped), {0, 1})
        self.assertAlmostEqual(len(run.tapped[0]), 0.2 * 32000, delta=2)
        self.assertGreater(max(map(abs, run.tapped[0])), 1000)              # its own output, before its volumes
        self.assertFalse(any(run.tapped[1]))                                # never keyed on


@unittest.skipUnless(emulate.available() and _have_openmpt(), "needs the compiled emulator and libopenmpt")
class Convert(unittest.TestCase):
    def test_pitch_modulation_is_kept_as_played(self):
        # voice 1 plays the same sample with its pitch bent by voice 0's output (PMON bit 1)
        voice1 = ((0x14, 0), (0x12, 0x00), (0x13, 0x10), (0x10, 100), (0x11, 100), (0x15, 0x00), (0x17, 0x7F), (0x2D, 0x02))
        snap = tiny(TINY + voice1 + ((0x4C, 0x03),))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "fm.it")
            song = convert.convert(snap, 1.0, path)
            info = song["info"]
            self.assertEqual((info["notes"], info["baked"], info["bakes"]), (2, 1, 1))
            keys = [ins.keyboard for ins in song["instruments"] if ins.keyboard]
            self.assertEqual(len(keys), 1)
            recording = next(i for i, smp in enumerate(song["samples"], 1) if smp.filename.startswith("pmon"))
            self.assertEqual(keys[0][1], (60, recording))                    # key 1: the recording, at its own rate
            m, pcm = render(path, 0.5)
            self.assertGreater(max(abs(v) for v in pcm), 1000)

    def test_the_echo_rings_out_and_stays_out_of_the_master_volume(self):
        # master volume at half, echo volume 0.5 with feedback 0.75: the hardware leaves the echo
        # out of the master volume, so the first repeat sounds as loud as the note (0.5 x 2), and
        # repeats go on until they fall to -30 dB: 0.5 x 0.75^(k-1) >= 1/32 for k up to 10
        voice = ((0x00, 50), (0x01, 50), (0x0C, 0x40), (0x1C, 0x40), (0x0D, 0x60))
        song = convert.convert(tiny(TINY + voice + KON0), 3.0)
        info = song["info"]
        rows = [row for pat in song["patterns"] for row in pat.data]
        master = [row[info["channels"] - 1] for row in rows if row[info["channels"] - 1].effect == it_song.FX_SET_GLOBAL_VOLUME]
        self.assertEqual(master[0].effect_val, round(0x40 * info["lift"]))   # the driver sets the master volume at the start
        self.assertIn(len(info["echo_channels"][0]), (10, 11))
        dry = next(row[0] for row in rows if 0 < row[0].note < 120)
        first = next(row[info["echo_channels"][0][0]] for row in rows if 0 < row[info["echo_channels"][0][0]].note < 120)
        self.assertAlmostEqual(first.volume / dry.volume, 1.0, delta=0.1)

    def test_the_module_ends_with_the_song_and_fades_as_a_player_would(self):
        song = convert.convert(tiny(), 1.37, fade=0.5)
        self.assertEqual(sum(p.rows for p in song["patterns"]), 137)          # to the last row, the last pattern short
        master = song["info"]["channels"] - 1
        levels = [(r, row[master].effect_val) for r, row in enumerate(song["patterns"][0].data)
                  if row[master].effect == it_song.FX_SET_GLOBAL_VOLUME and r > 0]     # row 0: the driver's own
        self.assertGreaterEqual(levels[0][0], 85)                            # the fade starts 0.5 s from the end
        self.assertEqual([v for _, v in levels], sorted((v for _, v in levels), reverse=True))
        self.assertLessEqual(levels[-1][1], 3)                               # and ends near silence

    def test_a_note_shorter_than_a_row(self):
        # keyed on, its GAIN rewritten and keyed off within a millisecond: it takes its row, the cut the next
        snap = tiny(TINY + KON0 + ((0x07, 0x40), (0x5C, 0x01)))
        song = convert.convert(snap, 0.5)
        rows = [row[0] for pat in song["patterns"] for row in pat.data]
        start = next(r for r, c in enumerate(rows) if 0 < c.note < 120)
        self.assertEqual(rows[start + 1].note, itf.NOTE_CUT)

    def test_notes_under_it_s_lowest_key(self):
        # a sample played five octaves and more under its rate (DKC2's bass): pitch 0x0080 is C-0 on a
        # 32 kHz C5Speed, which a cell cannot write (its note 0 reads as none), and 0x0070 is under it;
        # the sample's C5Speed goes an octave down, and both sound as loud as in the emulator
        dry = {0x4D: 0, 0x00: 50, 0x01: 50}
        for pitch in (0x0080, 0x0070):
            regs = tuple((r, dry.get(r, v)) for r, v in TINY if r not in (0x02, 0x03)) + ((0x02, pitch & 0xFF), (0x03, pitch >> 8))
            snap = tiny(regs + KON0)
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "low.it")
                song = convert.convert(snap, 1.0, path)
                m, pcm = render(path, 0.5)
            self.assertEqual((song["info"]["notes"], song["info"]["off_keys"]), (1, 0))
            self.assertAlmostEqual(song["samples"][0].c5_speed / 16000, 1.0, delta=0.03)       # an octave down
            emu = struct.unpack(f"<{16000 * 2}h", emulate.run(snap, 0.5, audio=True).audio[:16000 * 4])
            level = lambda a: math.sqrt(sum(v * v for v in a[6400:]) / len(a[6400:]))   # noqa: E731
            self.assertAlmostEqual(level(pcm[:len(emu)]) / level(emu), 1.0, delta=0.1)

    def test_a_held_note_panned_by_its_driver(self):
        # keyed hard left, then after a wait (0.38 s: 256 x 256 loops) moved hard right, still held:
        # the module follows, its left side silent after the move as the emulator's is
        start = tuple((r, {0x4D: 0, 0x00: 60, 0x01: 0}.get(r, v)) for r, v in TINY) + KON0
        writes = lambda regs: b"".join(bytes([0x8F, r, 0xF2, 0x8F, v, 0xF3]) for r, v in regs)  # noqa: E731
        wait = bytes([0x8F, 0x00, 0x10, 0x8D, 0x00, 0xFE, 0xFE, 0x6E, 0x10, 0xF9])   # $10 x Y loops
        code = writes(start) + wait + writes(((0x00, 0), (0x01, 60))) + bytes([0x2F, 0xFE])
        data = bytearray(tiny(start).raw)
        data[spc.RAM + 0x0200:spc.RAM + 0x0200 + len(code)] = code
        snap = spc.read(bytes(data))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "panned.it")
            convert.convert(snap, 1.0, path)
            m, pcm = render(path, 1.0)
        emu = struct.unpack(f"<{32000 * 2}h", emulate.run(snap, 1.0, audio=True).audio[:32000 * 4])
        side = lambda a, ch, t0, t1: math.sqrt(sum(v * v for v in a[2 * int(t0 * 32000) + ch:2 * int(t1 * 32000):2]) / (32000 * (t1 - t0)))  # noqa: E731
        for a in (emu, pcm):
            self.assertGreater(side(a, 0, 0.1, 0.3), 1000)                           # left, before the move
            self.assertLess(side(a, 0, 0.5, 0.9), 0.02 * side(a, 0, 0.1, 0.3))       # silent after it
            self.assertGreater(side(a, 1, 0.5, 0.9), 1000)                           # right
        self.assertAlmostEqual(side(pcm, 1, 0.5, 0.9) / side(emu, 1, 0.5, 0.9), 1.0, delta=0.15)

    def test_a_note_keyed_at_pitch_0_and_given_its_pitch_after(self):
        # keyed with its pitch at 0, the pitch written a moment later (EarthBound sweeps up from 0)
        start = tuple((r, {0x4D: 0, 0x00: 50, 0x01: 50, 0x02: 0, 0x03: 0}.get(r, v)) for r, v in TINY) + KON0
        wait = bytes([0x8F, 0x08, 0x10, 0x8D, 0x00, 0xFE, 0xFE, 0x6E, 0x10, 0xF9])   # 8 x 256 loops: 12 ms
        code = b"".join(bytes([0x8F, r, 0xF2, 0x8F, v, 0xF3]) for r, v in start) + wait + \
            bytes([0x8F, 0x03, 0xF2, 0x8F, 0x10, 0xF3, 0x2F, 0xFE])
        data = bytearray(tiny(start).raw)
        data[spc.RAM + 0x0200:spc.RAM + 0x0200 + len(code)] = code
        snap = spc.read(bytes(data))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sweep.it")
            song = convert.convert(snap, 0.5, path)
            m, pcm = render(path, 0.5)
        self.assertEqual(song["info"]["notes"], 1)
        self.assertGreater(max(abs(v) for v in pcm), 1000)

    def test_a_voice_over_it_s_volume_ceiling_under_a_low_master(self):
        # voice volume 100 (IT's stop at 64) under a master of 0x40: the global volume rises to 100
        # and the channel's volume falls to 64, the product the same, so the note is as loud as played
        regs = tuple((r, {0x4D: 0, 0x0C: 0x40, 0x1C: 0x40}.get(r, v)) for r, v in TINY) + KON0
        snap = tiny(regs)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "lifted.it")
            song = convert.convert(snap, 1.0, path)
            m, pcm = render(path, 0.5)
        last = song["info"]["channels"] - 1
        master = [row[last].effect_val for pat in song["patterns"] for row in pat.data if row[last].effect == it_song.FX_SET_GLOBAL_VOLUME]
        self.assertEqual(master[0], 100)                                      # the driver's 0x40, lifted
        emu = struct.unpack(f"<{16000 * 2}h", emulate.run(snap, 0.5, audio=True).audio[:16000 * 4])
        level = lambda a: math.sqrt(sum(v * v for v in a[6400:]) / len(a[6400:]))   # noqa: E731
        self.assertAlmostEqual(level(pcm[:len(emu)]) / level(emu), 1.0, delta=0.1)

    def test_a_tiny_driver_becomes_a_playable_module(self):
        snap = tiny()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tiny.it")
            song = convert.convert(snap, 1.0, path)
            info = song["info"]
            self.assertEqual(info["notes"], 1)
            copies = len(info["echo_channels"][0])                          # a copy per repeat: k passes of the echo
            self.assertEqual((info["samples"], info["instruments"]), (1 + copies, 1 + copies))
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
