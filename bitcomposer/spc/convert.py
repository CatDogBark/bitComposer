"""
SPC to IT, one to one: the notes a driver plays, written as an Impulse
Tracker module that plays the game's own samples, in IT instrument mode so
it opens in a tracker as a tracker song.

Step 4 of docs/SPC-IMPORT.md, the translator's proof: hear it against the
original. The pieces:

- Rows are the driver's own clock when it can be: a driver acts on a timer
  tick, and when its key-ons land on one of the snapshot's running timers
  (Secret of Evermore's 50 Hz) and IT can run that fast (102 ticks a second
  at most), every note falls exactly on a row. Drivers that do enough work
  a tick that their key-ons land anywhere in it (FFVI's, Secret of Mana's),
  or that tick faster than IT can (Mega Man X's 125 Hz), get IT's finest
  grid instead, 100 rows a second: every note within 5 ms of its time.
- One IT sample per SNES sample, its C5Speed set so the song's notes fall on
  whole semitones; what is left (a few cents) and every pitch write while a
  note sounds (vibrato, slides) become fine pitch slides, row by row.
- One IT instrument per sample and envelope setting, its volume envelope
  simulated from the ADSR or GAIN registers.
- Note volume and pan from the voice's volumes; swells in the volume column;
  a key-off is a note cut (the SNES chip's release takes under 8 ms).
- The echo as repeats: each echoing note again on a channel of its own, a
  delay (EDL x 16 ms) late, up to three times, the k-th at the echo volume
  times the filter's gain to the k and the feedback to the k-1, left and
  right as the echo volumes have them.
- The master volume (a driver's fade-out) as global volume, relative to
  the song's start, on a channel of its own.
- Noise voices play a white-noise sample at the noise clock's rate.

Not yet carried over: pitch modulation, the echo filter's colour (only its
gain is), phase-inverted volumes.
The files stay the user's: a converted song holds the game's samples.
"""
import math
import random
import struct
from array import array

from .. import it_format as itf
from . import RATE, brr, notes as notes_mod
from .emulate import CLOCK, run as emulate_run

ROWS_PER_PATTERN = 200
MAX_TICK_RATE = 102.0                 # IT tempo 255 is 102 ticks a second
FINE_GRID = 100.0                     # rows a second when the driver's clock cannot be the grid
ALIGNED = 0.6                         # how closely key-ons must line up with a timer to be its ticks
MAX_INSTRUMENTS = 99
TAPS = 3                              # echo repeats carried over, at most
FX_SET_GLOBAL_VOLUME = 22             # Vxx
ENV_NODES = 25

# The SNES chip's envelope rates: samples between steps (rate 0 never steps).
RATE_PERIOD = [0, 2048, 1536, 1280, 1024, 768, 640, 512, 384, 320, 256, 192, 160, 128, 96, 80,
               64, 48, 40, 32, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1]


def tick_rate(snap, writes) -> tuple[float, float]:
    """The driver's clock: of the timers the snapshot has running, the one
    whose period the key-on writes line up with best, as (Hz, how well
    they line up: 0 none, 1 exactly)."""
    ram = snap.ram
    control = ram[0xF1]
    candidates = []
    for t in range(3):
        if control >> t & 1:
            target = ram[0xFA + t] or 256
            candidates.append((16 if t == 2 else 128) * target)
    kons = [w.cycle for w in writes if w.reg == notes_mod.KON and w.value]
    best, best_r = None, 0.0
    for period in candidates:
        if len(kons) < 4:
            break
        c = sum(math.cos(2 * math.pi * k / period) for k in kons)
        s = sum(math.sin(2 * math.pi * k / period) for k in kons)
        r = math.hypot(c, s) / len(kons)
        if r > best_r:
            best, best_r = period, r
    return (CLOCK / best, best_r) if best else (0.0, 0.0)


def envelope(adsr1: int, adsr2: int, gain: int, tick_hz: float, seconds: float = 20.0) -> list[tuple[int, int]]:
    """The SNES chip's envelope for these registers, in IT envelope nodes:
    (tick, level 0-64), at most 25, the level held after the last."""
    env, mode, hidden = 0, "attack", 0
    levels = []
    per_tick = RATE / tick_hz
    next_tick, n = per_tick, 0
    acc = count = 0
    limit = int(RATE * seconds)
    stable = 0
    while n < limit:
        if adsr1 & 0x80:
            if mode == "attack":
                rate = (adsr1 & 0x0F) * 2 + 1
                step = 0x400 if rate == 31 else 0x20
            elif mode == "decay":
                rate, step = ((adsr1 >> 4) & 7) * 2 + 16, None
            else:
                rate, step = adsr2 & 0x1F, None
            boundary = adsr2 >> 5
        else:
            boundary = gain >> 5
            if not gain & 0x80:
                rate, step = 31, ("set", (gain & 0x7F) << 4)
            else:
                rate = gain & 0x1F
                step = ("gain", (gain >> 5) & 3)
        period = RATE_PERIOD[rate]
        if period and n % period == 0:
            if step is None:
                env -= 1
                env -= env >> 8
            elif isinstance(step, int):
                env += step
            elif step[0] == "set":
                env = step[1]
            else:
                g = step[1]
                if g == 0:
                    env -= 0x20
                elif g == 1:
                    env -= 1
                    env -= env >> 8
                elif g == 2:
                    env += 0x20
                else:
                    env += 0x20 if hidden < 0x600 else 8
            if mode == "decay" and (env >> 8) == boundary:
                mode = "sustain"
            hidden = env
            if env > 0x7FF or env < 0:
                env = 0 if env < 0 else 0x7FF
                if mode == "attack":
                    mode = "decay"
        acc += env
        count += 1
        if n + 1 >= next_tick:              # each tick carries its window's average: an IT envelope
            levels.append(round(64 * acc / count / 0x7FF))      # holds nothing finer than a tick
            acc = count = 0
            next_tick += per_tick
            stable = stable + 1 if len(levels) > 1 and levels[-1] == levels[-2] else 0
            if (env == 0 and mode != "attack") or stable > tick_hz:      # gone, or held for a second
                break
        n += 1
    return _simplify(levels)


def _simplify(levels: list[int]) -> list[tuple[int, int]]:
    """At most ENV_NODES nodes tracing the levels, the error kept smallest."""
    points = list(enumerate(levels))
    if len(points) <= 2:
        return points or [(0, 0)]
    tol = 0.5
    while True:
        keep = _rdp(points, tol)
        if len(keep) <= ENV_NODES:
            return keep
        tol *= 1.5


def _rdp(points, tol):
    if len(points) < 3:
        return points
    (x0, y0), (x1, y1) = points[0], points[-1]
    worst, at = 0.0, 0
    for i in range(1, len(points) - 1):
        x, y = points[i]
        line = y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0
        if abs(y - line) > worst:
            worst, at = abs(y - line), i
    if worst <= tol:
        return [points[0], points[-1]]
    return _rdp(points[:at + 1], tol)[:-1] + _rdp(points[at:], tol)


def _noise_sample() -> itf.ITSample:
    r = random.Random(0x4000)
    n = 8192
    data = struct.pack(f"<{n}h", *(r.randint(-16384, 16383) for _ in range(n)))
    return itf.ITSample(name="Noise", filename="noise", data=data, length=n, loop=True,
                        loop_start=0, loop_end=n, c5_speed=RATE)


def convert(snap, seconds: float | None = None, path: str | None = None) -> dict:
    """Convert a snapshot: run its driver, write the IT (to `path` if given).
    Returns the song dict write_it_file takes, with a summary in "info"."""
    if seconds is None:
        seconds = float(snap.tags.length_s or 90)
    run = emulate_run(snap, seconds)
    found = [n for n in notes_mod.decode(snap, run.writes, keyons=run.keyons) if n.pitch or n.noise]
    for n in found:                      # what each note played: the SNES chip's own reading, else the snapshot's
        if n.brr is None and not n.noise:
            n.brr = snap.entry(n.sample)
    hz, aligned = tick_rate(snap, run.writes)
    on_ticks = aligned >= ALIGNED and 0 < hz <= MAX_TICK_RATE
    tempo = max(32, min(255, round(2.5 * (hz if on_ticks else FINE_GRID))))
    row_hz = tempo / 2.5

    # Samples: one per SNES sample played (by its addresses), C5Speed on the song's semitone lattice.
    samples, sample_of, offset = [], {}, {}
    for addr in sorted({n.brr for n in found if not n.noise}):
        s = brr.decode(snap.ram, *addr) if 0 < addr[0] < 0xFFC0 else None
        if s is None or len(s) < 16:
            continue
        fracs = [12 * math.log2(n.pitch / 0x1000) for n in found if n.brr == addr and not n.noise and n.pitch]
        ang = [2 * math.pi * (f - math.floor(f)) for f in fracs]
        mean = math.atan2(sum(map(math.sin, ang)), sum(map(math.cos, ang))) / (2 * math.pi) if ang else 0.0
        offset[addr] = mean                                 # semitones the C5Speed sits off 32 kHz
        data = s.pcm.tobytes() if s.pcm.itemsize == 2 else array("h", s.pcm).tobytes()
        smp = itf.ITSample(name=f"SNES sample at {addr[0]:04X}", filename=f"brr{addr[0]:04x}", data=data, length=len(s),
                           loop=s.loops, loop_start=s.loop_start or 0, loop_end=s.loop_end or len(s),
                           c5_speed=max(1000, round(RATE * 2 ** (mean / 12))))
        samples.append(smp)
        sample_of[addr] = len(samples)
    noise_sample = None
    if any(n.noise for n in found):
        samples.append(_noise_sample())
        noise_sample = len(samples)
        offset["noise"] = 0.0

    # Instruments: one per sample and envelope setting.
    instruments, instrument_of = [], {}
    def key_of(n):
        return ("noise" if n.noise else n.brr, n.adsr, n.gain if not n.adsr[0] & 0x80 else 0)

    for n in found:
        key = key_of(n)
        if key in instrument_of or (not n.noise and n.brr not in sample_of):
            continue
        if len(instruments) >= MAX_INSTRUMENTS:
            continue
        nodes = envelope(n.adsr[0], n.adsr[1], n.gain, row_hz)
        sample = noise_sample if n.noise else sample_of[n.brr]
        label = "noise" if n.noise else f"sample {n.brr[0]:04X}"
        instruments.append(itf.ITInstrument(name=f"{label} env {len(instruments) + 1}", sample=sample, envelope=nodes))
        instrument_of[key] = len(instruments)

    # Channels: the eight voices; for each voice up to TAPS echo repeats; the master volume last.
    voices_echo = any(n.echo and n.echo_writes and n.echo_delay > 0 for n in found)
    taps = TAPS if voices_echo else 0
    channels = 8 + 8 * taps + 1
    master_ch = channels - 1
    total_rows = int(run.seconds * row_hz) + 2
    n_patterns = min(200, math.ceil(total_rows / ROWS_PER_PATTERN))
    patterns = [itf.ITPattern(rows=ROWS_PER_PATTERN, channels=channels) for _ in range(n_patterns)]
    last_row = n_patterns * ROWS_PER_PATTERN - 1

    def cell(row, ch):
        return patterns[row // ROWS_PER_PATTERN].data[row % ROWS_PER_PATTERN][ch] if 0 <= row <= last_row else None

    def it_semis(n, pitch):
        if n.noise:
            per = RATE_PERIOD[n.noise_rate] or 1
            return 60 + 12 * math.log2(1 / per)
        return 60 + 12 * math.log2(pitch / 0x1000) - offset[n.brr]

    def loudness(left, right, gl, gr):
        """(IT volume, IT pan or None) for voice volumes scaled by gains."""
        l, r = abs(left) * gl, abs(right) * gr
        vol = max(0, min(64, round(64 * max(l, r) / 127)))
        pan = round(255 * (0.5 + 0.5 * (r - l) / (l + r))) if l + r > 0 else None
        return vol, pan

    pans = {}

    def place(n, ch, note, ins, shift, gl, gr) -> bool:
        """Write note n into channel ch, `shift` rows late, its volumes scaled
        by gl (left) and gr (right): the note, its pan, its bends and swells
        row by row, its cut."""
        row = round(n.start * row_hz) + shift
        c = cell(row, ch)
        if c is None:
            return False
        vol, pan = loudness(*n.volume, gl, gr)
        if vol == 0 and not any(loudness(sl, sr, gl, gr)[0] for _, sl, sr in n.swells):
            return False                 # silent throughout (a driver may key a note silent, then swell it up)
        c.note, c.instrument, c.volume = note, ins, vol
        if pan is not None and pan != pans.get(ch):
            c.effect, c.effect_val = itf.FX_SET_PAN, pan
            pans[ch] = pan
        end_row = (round(n.end * row_hz) + shift) if n.end is not None else last_row + 1
        bends, swells = list(n.bends), list(n.swells)
        cur, pitch, last_vol = 0, n.pitch, vol
        for r in range(row, min(end_row, last_row + 1)):
            t = (r - shift + 0.5) / row_hz
            while bends and bends[0][0] <= t:
                pitch = bends.pop(0)[1]
            v = last_vol
            while swells and swells[0][0] <= t:
                _, sl, sr = swells.pop(0)
                v = loudness(sl, sr, gl, gr)[0]
            cc = cell(r, ch)
            if r > row and v != last_vol and cc.volume == 255 and cc.note == 0:
                cc.volume, last_vol = v, v
            if not pitch:
                continue
            target = round(64 * (it_semis(n, pitch) - note))
            delta = target - cur
            if delta and cc.effect == 0:
                d = abs(delta)
                if d <= 15:
                    val, moved = 0xE0 | d, d
                else:
                    x = min(15, round(d / 4))
                    val, moved = 0xF0 | x, 4 * x
                cc.effect = itf.FX_PORTA_UP if delta > 0 else itf.FX_PORTA_DOWN
                cc.effect_val = val
                cur += moved if delta > 0 else -moved
        if end_row <= last_row:
            cc = cell(end_row, ch)
            if cc.note == 0:
                cc.note = itf.NOTE_CUT
        return True

    placed = repeats = 0
    for n in sorted(found, key=lambda n: (n.start, n.voice)):
        ins = instrument_of.get(key_of(n))
        if ins is None or (n.noise and not n.noise_rate):
            continue
        note = round(it_semis(n, n.pitch))
        if not 0 <= note <= 119:
            continue
        if not place(n, n.voice, note, ins, 0, 1.0, 1.0):
            continue
        placed += 1
        # The echo, as repeats: the k-th comes k delays late, at the echo
        # volume times the filter's gain to the k and the feedback to the k-1.
        if taps and n.echo and n.echo_writes and n.echo_delay > 0:
            g, fb = abs(n.echo_fir), abs(n.echo_feedback)
            for k in range(1, taps + 1):
                scale = g ** k * fb ** (k - 1)
                gl, gr = abs(n.echo_volume[0]) * scale, abs(n.echo_volume[1]) * scale
                if max(gl, gr) < 1 / 32:
                    break
                shift = round(k * n.echo_delay * row_hz)
                if place(n, 8 + n.voice * taps + k - 1, note, ins, shift, gl, gr):
                    repeats += 1

    # The master volume, relative to where the song starts (fades, mostly).
    mv = notes_mod.master_volume(snap, run.writes)
    base = max(abs(mv[0][1]), abs(mv[0][2])) or 127
    level = 128
    for t_mv, ml, mr in mv[1:]:
        gv = max(0, min(128, round(128 * max(abs(ml), abs(mr)) / base)))
        c = cell(round(t_mv * row_hz), master_ch)
        if c is not None and gv != level:
            c.effect, c.effect_val = FX_SET_GLOBAL_VOLUME, gv
            level = gv

    t = snap.tags
    message = "\r".join([
        f"{t.title or 'SPC'}{' - ' + t.game if t.game else ''}{' - ' + t.artist if t.artist else ''}",
        "Converted from an SPC snapshot by bitComposer: the game's own samples and the notes its",
        "driver played, one to one, the echo as repeats on channels of their own.",
        "Not carried over yet: pitch modulation, the echo filter's colour.",
        (f"rows on the driver's clock, {hz:.2f} Hz" if on_ticks else
         f"rows at {row_hz:.0f} a second (the driver's key-ons do not sit on a tick IT can run)") + f"; {placed} notes, {repeats} echo repeats",
    ])
    song = {"name": (t.title or "SPC")[:25], "samples": samples, "patterns": patterns,
            "orders": list(range(n_patterns)), "tempo": tempo, "speed": 1, "instruments": instruments,
            "message": message,
            "info": {"notes": placed, "repeats": repeats, "channels": channels, "tick_hz": hz, "aligned": aligned, "on_ticks": on_ticks, "row_hz": row_hz,
                     "samples": len(samples), "instruments": len(instruments), "seconds": run.seconds}}
    if path:
        itf.write_it_file(path, song["name"], samples, patterns, song["orders"], tempo=tempo, speed=1,
                          global_volume=128, mix_volume=128, num_channels=channels, channel_pans=[32] * channels,
                          message=message, instruments=instruments)
    return song
