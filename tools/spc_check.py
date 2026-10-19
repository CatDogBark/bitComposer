#!/usr/bin/env python3
"""
Measures SPC-to-IT conversions against the emulator's own output.

The emulator plays an SPC file's own driver on the SNES chip; the converter
writes the same song as an IT module. This renders both and compares them,
the whole mix and then voice by voice: the emulator can leave voices out of
its output, and a converted song says which of its channels carry a voice,
so a problem shows up in the voice it is in.

Usage:
    python3 tools/spc_check.py voice FILE.spc [--seconds 30] [--voices 0,3] [--trace 3] [--bands]
    python3 tools/spc_check.py sweep SPC_ROOT OUT_DIR [--workers 8] [--seconds 30]
    python3 tools/spc_check.py report OUT_DIR/results.jsonl
    python3 tools/spc_check.py traits SPC_ROOT OUT.json [--workers 8]
    python3 tools/spc_check.py doc SPC_ROOT TRAITS.json RESULTS.jsonl [--docs docs/drivers]

The numbers:
- contour: the correlation of the two loudness contours (RMS in 50 ms
  windows), on each side the original sounds on, averaged. A steady sound
  (a wind bed) scores low even when it matches, since all a correlation
  sees there is flicker; read it with
- gap: the median distance in dB between the two contours, over the windows
  where the original sounds.
- level: the module's RMS over the original's.
- tone: the correlation of the two averaged log spectra, 100 Hz to 12 kHz.
  A wrong timbre at the right loudness (a steady beep where a hiss belongs)
  shows only here, and only voice by voice: in the whole mix one voice's
  tone is lost under the rest.
- echo/dry: a voice's echo against its dry sound. The original's echo is the
  voice's solo output less its dry signal (its own output, tapped from the
  emulator, times its volumes and the master volume); the module's is its
  repeat channels against its own channel.

`traits` records what each song's driver does with the SNES chip, over its
first minute: its clock, how it shapes envelopes, its pitch writes, pitch
modulation and noise, its echo and master volume, its density; and prints
them per game. `doc` writes the measured parts of docs/drivers/ from these
and a sweep: each driver file's games, traits and scores, the SNES scores,
and the index of games and composers, between "generated" markers; what is
written by hand around them stays. A driver family with no file yet gets one
to fill in.

A sweep converts every SPC under SPC_ROOT/<game>/ at full length (to catch
failures and IT's limits) and measures the first --seconds. A drivers.json in
SPC_ROOT names each game folder's music driver, the unit a result says the
most about: {"<game folder>": {"driver": "<driver file, as akao>", "game":
"<its name>", "composer": "<a fuller credit than the tags'>"}} (game and
composer optional; a plain string is the driver alone). The converted modules
go to OUT_DIR/it/: they hold the games' samples, and stay where they are.

Needs the emulator (bitcomposer-emu, CONTRIBUTING.md) and libopenmpt.
docs/SPC-IMPORT.md records what these measurements found.
"""
import argparse
import array
import cmath
import ctypes
import glob
import json
import math
import os
import sys
import tempfile
import time
import traceback
from collections import defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitcomposer import it_format as itf  # noqa: E402
from bitcomposer import spc  # noqa: E402
from bitcomposer.spc import convert, emulate, notes  # noqa: E402

RATE = 32000
WINDOW = 1600                 # samples: the 50 ms a loudness contour steps by
N = 1024                      # samples a spectrum frame holds
BANDS = [(88, 177), (177, 354), (354, 707), (707, 1414), (1414, 2828), (2828, 5657), (5657, 11314)]
MVOLL, MVOLR, EVOLL, EVOLR, EFB, EDL, EON, PMON = 0x0C, 0x1C, 0x2C, 0x3C, 0x0D, 0x7D, 0x4D, 0x2D


def _s8(b: int) -> int:
    return b - 256 if b & 0x80 else b


# Rendering -----------------------------------------------------------------

def render_it(path: str, seconds: float) -> array.array:
    """A module's first `seconds` as libopenmpt plays it: 32 kHz stereo."""
    from bitcomposer.player.openmpt import Module
    m = Module(path)
    buf = (ctypes.c_int16 * (2 * RATE))()
    pcm = array.array("h")
    while len(pcm) < 2 * RATE * seconds:
        n = m.read_stereo(RATE, buf, RATE)
        if not n:
            break
        pcm.extend(buf[:2 * n])
    return pcm[:int(2 * RATE * seconds)]


def emulated(snap, seconds: float, voice: int | None = None) -> array.array:
    """The emulator's output (32 kHz stereo), of one voice alone when given."""
    mute = 0 if voice is None else 0xFF ^ (1 << voice)
    return array.array("h", emulate.run(snap, seconds, audio=True, mute=mute).audio)


def channels_of(song: dict, voice: int) -> tuple[int, list[int], int]:
    """A converted song's channels for a voice: (its own, its echo repeats', the master volume's)."""
    info = song["info"]
    n = info["channels"]
    if "echo_channels" in info:
        echo = list(info["echo_channels"].get(voice, []))
    else:                                    # every voice with its repeats, three or none
        taps = (n - 9) // 8
        echo = [8 + voice * taps + k for k in range(taps)]
    return voice, echo, n - 1


def write_channels(song: dict, keep: set, path: str) -> None:
    """The song with only the channels in `keep` playing."""
    empty = itf.ITNote()
    pats = []
    for p in song["patterns"]:
        q = itf.ITPattern(rows=p.rows, channels=p.channels)
        q.data = [[cell if c in keep else empty for c, cell in enumerate(row)] for row in p.data]
        pats.append(q)
    n = song["info"]["channels"]
    itf.write_it_file(path, "check", song["samples"], pats, song["orders"], tempo=song["tempo"], speed=song["speed"],
                      global_volume=song.get("global_volume", 128), mix_volume=128, num_channels=n,
                      channel_pans=[32] * n, instruments=song["instruments"])


def render_channels(song: dict, keep: set, seconds: float) -> array.array:
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "check.it")
        write_channels(song, keep, path)
        return render_it(path, seconds)


# Measures ------------------------------------------------------------------

def corr(a, b) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else 0.0


def rms(x) -> float:
    return math.sqrt(sum(v * v for v in x) / len(x)) if len(x) else 0.0


def contour(side, w: int = WINDOW) -> list[float]:
    """RMS in w-sample windows, from every sample: a stride lands on the same
    points of a loop whose period it divides (a BRR loop of 8 or 16 samples
    read every fourth sample measured a softened square 4 dB low)."""
    return [math.sqrt(sum(v * v for v in side[s:s + w]) / w) for s in range(0, len(side) - w, w)]


def ac_rms(side, w: int = WINDOW) -> float:
    """RMS with each window's mean taken out: a voice that is only DC (a noise
    voice whose clock never steps) counts as silent."""
    tot = cnt = 0
    for s0 in range(0, len(side) - w, w):
        seg = side[s0:s0 + w:4]
        m = sum(seg) / len(seg)
        tot += sum((v - m) ** 2 for v in seg)
        cnt += len(seg)
    return math.sqrt(tot / cnt) if cnt else 0.0


def active_sides(stereo) -> tuple[int, ...]:
    """The sides the original sounds on: a voice panned hard to one side leaves
    the other silent, and silence correlates with nothing."""
    a = [ac_rms(stereo[k::2]) for k in (0, 1)]
    return tuple(k for k in (0, 1) if a[k] >= max(20.0, 0.05 * max(a)))


def gap_db(rc, ic) -> float | None:
    """The median gap in dB between two contours, over the windows where the
    original (rc) sounds."""
    floor = max(10.0, 0.01 * max(rc, default=0))
    gaps = sorted(abs(20 * math.log10(max(1.0, b) / a)) for a, b in zip(rc, ic) if a > floor)
    return gaps[len(gaps) // 2] if gaps else None


def compare(ref, it, sides=(0, 1)) -> dict:
    """contour, gap (dB) and level of `it` against `ref` (stereo) over `sides`."""
    if not sides:
        return {"contour": None, "gap_db": None, "level": None}
    cs, gs = [], []
    for k in sides:
        rc, ic = contour(ref[k::2]), contour(it[k::2])
        cs.append(corr(rc, ic))
        g = gap_db(rc, ic)
        if g is not None:
            gs.append(g)
    r = rms(ref)
    return {"contour": sum(cs) / len(cs), "gap_db": sum(gs) / len(gs) if gs else None,
            "level": rms(it) / r if r else None}


_WIN = [0.5 - 0.5 * math.cos(2 * math.pi * i / N) for i in range(N)]
_TWIDDLE = [cmath.exp(-2j * math.pi * k / N) for k in range(N // 2)]
_REVERSE = [int(f"{i:0{N.bit_length() - 1}b}"[::-1], 2) for i in range(N)]


def _fft(x) -> list[complex]:
    a = [complex(x[_REVERSE[i]]) for i in range(N)]
    size = 2
    while size <= N:
        half, step = size // 2, N // size
        for start in range(0, N, size):
            for k in range(half):
                t = _TWIDDLE[k * step] * a[start + k + half]
                u = a[start + k]
                a[start + k], a[start + k + half] = u + t, u - t
        size *= 2
    return a


def spectrum(side) -> list[float]:
    """The averaged power spectrum (N/2 bins), a Hann frame every WINDOW samples."""
    acc = [0.0] * (N // 2)
    for s in range(0, len(side) - N, WINDOW):
        sp = _fft([side[s + i] * _WIN[i] for i in range(N)])
        for k in range(N // 2):
            acc[k] += abs(sp[k]) ** 2
    return acc


def tone(ref, it, sides=(0, 1), lo_hz: int = 100, hi_hz: int = 12000) -> float | None:
    """The correlation of the averaged log spectra over `sides`: the timbre, whatever its timing."""
    if not sides:
        return None
    lo, hi = int(lo_hz * N / RATE), int(hi_hz * N / RATE)
    a, b = [], []
    for c in sides:
        a += [math.log10(1e-9 + x) for x in spectrum(ref[c::2])[lo:hi]]
        b += [math.log10(1e-9 + x) for x in spectrum(it[c::2])[lo:hi]]
    return corr(a, b)


def band_levels(ref, it, side: int) -> list[float]:
    """Per octave in BANDS, the module's amplitude over the original's."""
    sr, si = spectrum(ref[side::2]), spectrum(it[side::2])
    out = []
    for lo, hi in BANDS:
        k0, k1 = int(lo * N / RATE), int(hi * N / RATE) + 1
        e = sum(sr[k0:k1])
        out.append(math.sqrt(sum(si[k0:k1]) / e) if e else 0.0)
    return out


def echo_split(snap, voice: int, seconds: float, solo=None) -> tuple[list[int], list[int]]:
    """The original's dry sound and echo for a voice, interleaved stereo: its
    own output, tapped, times its volumes and the master volume as the driver
    wrote them, and its solo output less that."""
    run = emulate.run(snap, seconds, taps=1 << voice)
    solo = solo if solo is not None else emulated(snap, seconds, voice)
    regs = {r: _s8(snap.dsp[r]) for r in (voice * 0x10, voice * 0x10 + 1, MVOLL, MVOLR)}
    events = sorted((w.cycle // 32, w.reg, _s8(w.value)) for w in run.writes if w.reg in regs)
    tap, ei, dry, echo = run.tapped[voice], 0, [], []
    for i in range(len(solo) // 2):
        while ei < len(events) and events[ei][0] <= i:
            regs[events[ei][1]] = events[ei][2]
            ei += 1
        o = tap[i] if i < len(tap) else 0
        for side, vreg, mreg in ((0, voice * 0x10, MVOLL), (1, voice * 0x10 + 1, MVOLR)):
            d = ((o * regs[vreg]) >> 7) * regs[mreg] >> 7
            dry.append(d)
            echo.append(solo[2 * i + side] - d)
    return dry, echo


def echo_settings(snap, writes, end_cycle: int | None = None) -> dict:
    """The echo the song runs with for the longest (each setting weighed by
    how long it holds, to `end_cycle` or the last write), and the voices it
    pitch-modulates."""
    echo_regs = {EDL, EFB, EVOLL, EVOLR, EON} | {0x0F + 0x10 * k for k in range(8)}
    regs, held, pmon = bytearray(snap.dsp), defaultdict(int), snap.dsp[PMON]

    def state():
        return (regs[EDL] & 15, _s8(regs[EFB]), _s8(regs[EVOLL]), _s8(regs[EVOLR]),
                tuple(_s8(regs[0x0F + 0x10 * k]) for k in range(8)), regs[EON])
    since, current = 0, state()
    for w in writes:
        if w.reg == PMON:
            pmon |= w.value
        if w.reg in echo_regs and regs[w.reg] != w.value:
            held[current] += w.cycle - since
            regs[w.reg] = w.value
            since, current = w.cycle, state()
        else:
            regs[w.reg] = w.value
    end = end_cycle if end_cycle is not None else (writes[-1].cycle if writes else 0)
    held[current] += max(1, end - since)
    edl, efb, evl, evr, fir, eon = max(held, key=held.get)
    return {"delay_ms": edl * 16, "feedback": efb / 128, "echo_volume": (evl / 128, evr / 128),
            "filter_dc": sum(fir) / 128, "sending": [v for v in range(8) if eon >> v & 1],
            "pitch_modulated": [v for v in range(1, 8) if pmon >> v & 1]}


# voice ---------------------------------------------------------------------

def _fmt(x, spec=".2f", none="  -  "):
    return none if x is None else format(x, spec)


def cmd_voice(args) -> int:
    snap = spc.read(args.file)
    secs = args.seconds
    song = convert.convert(snap, secs + 2)
    run = emulate.run(snap, secs)
    e = echo_settings(snap, run.writes, int(run.seconds * emulate.CLOCK))
    info = song["info"]
    print(f"{os.path.basename(args.file)}: {info['notes']} notes, {info['channels']} channels, rows at {info['row_hz']:.0f} a second; "
          f"echo {e['delay_ms']} ms, feedback {e['feedback']:+.2f}, volume {e['echo_volume'][0]:+.2f}/{e['echo_volume'][1]:+.2f}, "
          f"filter at DC {e['filter_dc']:+.2f}, sending {e['sending']}; pitch-modulated {e['pitch_modulated'] or 'none'}")
    mix = compare(emulated(snap, secs), render_channels(song, set(range(info["channels"])), secs))
    print(f"whole mix: contour {_fmt(mix['contour'])}, gap {_fmt(mix['gap_db'], '.1f')} dB, level {_fmt(mix['level'])}")
    print(f"{'voice':5s} {'sides':5s} {'rms':>6s} {'contour':>7s} {'gap dB':>6s} {'level':>5s} {'tone':>5s} | echo/dry: original  IT")
    voices = [int(v) for v in args.voices.split(",")] if args.voices else range(8)
    for v in voices:
        ref = emulated(snap, secs, v)
        sides = active_sides(ref)
        if not sides:
            continue
        own, echo, master = channels_of(song, v)
        it = render_channels(song, {own, master, *echo}, secs)
        m = compare(ref, it, sides)
        line = (f"{v:5d} {''.join('LR'[k] for k in sides):5s} {rms(ref):6.0f} {_fmt(m['contour']):>7s} "
                f"{_fmt(m['gap_db'], '.1f'):>6s} {_fmt(m['level']):>5s} {_fmt(tone(ref, it, sides)):>5s}")
        dry = echo_ = None
        if v in e["sending"] and echo:
            dry, echo_ = echo_split(snap, v, secs, ref)
            k = sides[0]
            it_dry = render_channels(song, {own, master}, secs)
            it_echo = render_channels(song, {master, *echo}, secs)
            original = rms(echo_[k::2]) / rms(dry[k::2]) if rms(dry[k::2]) else 0.0
            ours = rms(it_echo[k::2]) / rms(it_dry[k::2]) if rms(it_dry[k::2]) else 0.0
            line += f" |          {original:6.2f} {ours:5.2f}"
        print(line, flush=True)
        if args.bands:
            print("      by octave (module / original): " + "  ".join(
                f"{lo}-{hi} Hz {x:.2f}" for (lo, hi), x in zip(BANDS, band_levels(ref, it, sides[0]))))
        if args.trace == v:
            _trace(snap, song, v, secs, args.step, ref, it, sides[0], dry, echo_)
    return 0


def _trace(snap, song, v, secs, step, ref, it, side, dry, echo):
    """One voice over time: RMS per `step` seconds on one side, the original's and the module's,
    and their echoes apart where the voice sends."""
    own, echo_ch, master = channels_of(song, v)
    it_echo = render_channels(song, {master, *echo_ch}, secs) if echo is not None else None
    w = int(step * RATE)
    print(f"      voice {v} over time, side {'LR'[side]}: original | module" + ("  (echo: original | module)" if it_echo else ""))
    for i in range(int(secs / step)):
        a, b = 2 * i * w + side, 2 * (i + 1) * w + side
        line = f"      {i * step:6.2f} s  {rms(ref[a:b:2]):6.0f} | {rms(it[a:b:2]):6.0f}"
        if it_echo is not None:
            line += f"    {rms(echo[a:b:2]):6.0f} | {rms(it_echo[a:b:2]):6.0f}"
        print(line)


# sweep ---------------------------------------------------------------------

_OUT, _DRIVERS, _SECONDS = None, {}, 30.0


def _init(out, drivers, seconds):
    global _OUT, _DRIVERS, _SECONDS
    _OUT, _DRIVERS, _SECONDS = out, drivers, seconds


def measure(path: str) -> dict:
    """One song for a sweep: converted at full length, then its mix and each voice measured."""
    game = os.path.basename(os.path.dirname(path))
    rec = {"game": game, "driver": _DRIVERS.get(game, game), "song": os.path.basename(path)[:-4]}
    t0 = time.time()
    try:
        snap = spc.read(path)
        it_path = os.path.join(_OUT, "it", f"{game} - {rec['song']}.it")
        info = convert.convert(snap, None, it_path)["info"]
        rec.update({k: info.get(k) for k in ("notes", "samples", "instruments", "baked", "bakes", "unbaked",
                                             "repeats", "row_hz", "on_ticks", "seconds", "channels")})
        rec["size"] = os.path.getsize(it_path)
        secs = min(_SECONDS, info["seconds"])
        ref = emulated(snap, secs)
        rec["emu_rms"] = rms(ref)
        rec.update(compare(ref, render_it(it_path, secs), active_sides(ref)))
        short = convert.convert(snap, secs + 2)   # small patterns, quick to rewrite per voice
        rec["voices"] = {}
        for v in range(8):
            vref = emulated(snap, secs, v)
            sides = active_sides(vref)
            if not sides:
                continue
            own, echo, master = channels_of(short, v)
            vit = render_channels(short, {own, master, *echo}, secs)
            m = compare(vref, vit, sides)
            rec["voices"][v] = {"rms": round(rms(vref)), "sides": "".join("LR"[k] for k in sides),
                                "tone": round(tone(vref, vit, sides), 3),
                                **{k: (round(x, 3) if x is not None else None) for k, x in m.items()}}
    except Exception as e:                       # noqa: BLE001 - a sweep reports every failure and goes on
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["trace"] = traceback.format_exc()[-1500:]
    rec["time"] = round(time.time() - t0, 1)
    return rec


def cmd_sweep(args) -> int:
    files = sorted(glob.glob(os.path.join(args.spc_root, "*", "*.spc")))
    if not files:
        print(f"spc_check: no SPC files under {args.spc_root}/<game>/", file=sys.stderr)
        return 1
    drivers = {k: v["driver"] for k, v in load_manifest(args.spc_root).items()}
    os.makedirs(os.path.join(args.out_dir, "it"), exist_ok=True)
    results = os.path.join(args.out_dir, "results.jsonl")
    t0 = time.time()
    with Pool(args.workers, initializer=_init, initargs=(args.out_dir, drivers, args.seconds)) as pool, \
            open(results, "w") as fh:
        for i, rec in enumerate(pool.imap_unordered(measure, files), 1):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if i % 25 == 0 or i == len(files):
                print(f"{i}/{len(files)} songs, {time.time() - t0:.0f} s", flush=True)
    print(f"{results}: {len(files)} songs in {time.time() - t0:.0f} s; "
          f"python3 tools/spc_check.py report {results}")
    return 0


# traits --------------------------------------------------------------------

def song_traits(path: str) -> dict:
    """What a song's driver does with the SNES chip over its first minute."""
    snap = spc.read(path)
    t = snap.tags
    run = emulate.run(snap, min(60.0, float(t.length_s or 60)))
    ns = [n for n in notes.decode(snap, run.writes, keyons=run.keyons) if n.pitch or n.noise]
    hz, aligned = convert.tick_rate(snap, run.writes)
    e = echo_settings(snap, run.writes, int(run.seconds * emulate.CLOCK))
    masters, since = defaultdict(int), 0                     # each master volume weighed by how long it holds
    current = max(abs(_s8(snap.dsp[MVOLL])), abs(_s8(snap.dsp[MVOLR])))
    for when, left, right in convert.notes_mod.master_volume(snap, run.writes)[1:]:
        cycle = int(when * emulate.CLOCK)
        masters[current] += cycle - since
        since, current = cycle, max(abs(left), abs(right))
    masters[current] += max(1, int(run.seconds * emulate.CLOCK) - since)
    pitched = [n for n in ns if not n.noise]
    lengths = sorted(n.length for n in pitched if n.length)
    share = lambda f: sum(1 for n in pitched if f(n)) / len(pitched) if pitched else 0.0   # noqa: E731
    return {"game_folder": os.path.basename(os.path.dirname(path)), "song": os.path.basename(path)[:-4],
            "game": t.game, "artist": t.artist, "title": t.title, "length_s": t.length_s,
            "notes": len(ns), "voices": len({n.voice for n in ns}), "tick_hz": round(hz, 2), "on_ticks": aligned >= convert.ALIGNED,
            "adsr_share": share(lambda n: n.adsr[0] & 0x80), "rewritten_share": share(lambda n: n.envelopes),
            "envelope_writes_per_note": sum(len(n.envelopes) for n in pitched) / len(pitched) if pitched else 0.0,
            "pitch_writes_per_note": sum(len(n.bends) for n in pitched) / len(pitched) if pitched else 0.0,
            "noise_notes": sum(1 for n in ns if n.noise), "pitch_modulated": bool(e["pitch_modulated"]),
            "echo_delay_ms": e["delay_ms"], "echo_feedback": e["feedback"], "echo_volume": max(map(abs, e["echo_volume"])),
            "echo_inverted": e["echo_volume"][0] * e["echo_volume"][1] < 0, "echo_filter_dc": e["filter_dc"],
            "echo_sending": len(e["sending"]), "master_volume": max(masters, key=masters.get),
            "median_note_s": lengths[len(lengths) // 2] if lengths else None}


def cmd_traits(args) -> int:
    files = sorted(glob.glob(os.path.join(args.spc_root, "*", "*.spc")))
    if not files:
        print(f"spc_check: no SPC files under {args.spc_root}/<game>/", file=sys.stderr)
        return 1
    with Pool(args.workers) as pool:
        recs = pool.map(song_traits, files)
    with open(args.out, "w") as fh:
        json.dump(recs, fh, indent=1)
    for game in sorted({r["game_folder"] for r in recs}):
        rs = [r for r in recs if r["game_folder"] == game]
        print(f"{game}: {len(rs)} songs; game {_counted(rs, lambda r: r['game'], 1)}; composer {_counted(rs, lambda r: r['artist'], 2)}")
        for name, text in trait_rows(rs):
            print(f"  {name}: {text}")
    print(f"{args.out}: {len(recs)} songs")
    return 0


def _counted(recs, key, n: int = 3) -> str:
    """The commonest values of key over recs, each with how many songs have it."""
    counts = defaultdict(int)
    for r in recs:
        counts[key(r)] += 1
    top = sorted(counts.items(), key=lambda kc: (-kc[1], str(kc[0])))[:n]
    return "; ".join(f"{k} ({c}{' songs' if i == 0 else ''})" for i, (k, c) in enumerate(top))


def trait_rows(recs) -> list[tuple[str, str]]:
    """What a driver does, over songs' traits: (trait, measured), medians across the songs
    (over those with more than 20 notes, where a sound effect would skew them)."""
    busy = [r for r in recs if r["notes"] > 20] or recs
    n = len(recs)
    med = lambda key, p=.5: _pct([key(r) for r in busy], p)           # noqa: E731

    def clock(r):
        hz = round(r["tick_hz"])
        return f"{hz} Hz, " + ("on its ticks" if r["on_ticks"] else "key-ons anywhere in a tick") if hz else "none found"
    return [
        ("Clock", _counted(recs, clock)),
        ("Envelopes", f"ADSR at key-on: {100 * med(lambda r: r['adsr_share']):.0f} % of notes; rewritten as they sound: "
                      f"{100 * med(lambda r: r['rewritten_share']):.0f} % ({med(lambda r: r['envelope_writes_per_note']):.1f} writes a note)"),
        ("Pitch writes", f"{med(lambda r: r['pitch_writes_per_note']):.1f} a note (90 %: {med(lambda r: r['pitch_writes_per_note'], .9):.1f})"),
        ("Pitch modulation", f"in {sum(r['pitch_modulated'] for r in recs)} of {n} songs"),
        ("Noise", f"in {sum(1 for r in recs if r['noise_notes'])} of {n} songs"),
        ("Echo", _counted(recs, lambda r: f"{r['echo_delay_ms']} ms, feedback {round(r['echo_feedback'], 2)}", 4)),
        ("Echo volume", _counted(recs, lambda r: round(r["echo_volume"], 2), 2)),
        ("Echo sides inverted", f"in {sum(r['echo_inverted'] for r in recs)} of {n} songs"),
        ("Echo filter at DC", _counted(recs, lambda r: round(r["echo_filter_dc"], 2), 2)),
        ("Master volume", _counted(recs, lambda r: r["master_volume"], 2)),
        ("Density", f"{_pct([r['notes'] for r in recs], .5)} notes in a song's first minute; a note {med(lambda r: r['median_note_s']):.2f} s"),
    ]


# the driver record ---------------------------------------------------------

def load_manifest(spc_root: str) -> dict:
    """SPC_ROOT/drivers.json as {game folder: {"driver": ..., "game"?: ..., "composer"?: ...}}."""
    path = os.path.join(spc_root, "drivers.json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        raw = json.load(fh)
    return {k: (dict(v) if isinstance(v, dict) else {"driver": v}) for k, v in raw.items()}


def fill(text: str, name: str, content: str) -> str:
    """text with what stands between its <!-- generated: name --> and <!-- end generated --> replaced."""
    begin, end = f"<!-- generated: {name} -->\n", "<!-- end generated -->"
    i = text.find(begin)
    if i < 0:
        raise ValueError(f"no '<!-- generated: {name} -->' block")
    j = text.index(end, i)
    return text[:i + len(begin)] + content.rstrip("\n") + "\n" + text[j:]


def _commonest(values):
    values = [v for v in values if v]
    return max(set(values), key=values.count) if values else None


def _credit(artist: str | None) -> str:
    """A composer as the tags credit them: a full 32-character field was most likely cut off."""
    if not artist:
        return "(not in the tags)"
    return f'"{artist}" (cut off)' if len(artist) >= 32 else artist


def _scores(rs) -> str:
    c, g, lv = [r["contour"] for r in rs], [r["gap_db"] for r in rs], [r["level"] for r in rs]
    vt = [x["tone"] for r in rs for _, x in _voices_that_matter(r)]
    return (f"{len(rs)} | {_pct(c, .5):.2f} ({_pct(c, .1):.2f}) | {_pct(g, .5):.2f} ({_pct(g, .9):.2f}) | "
            f"{_pct(lv, .5):.2f} ({_pct(lv, .1):.2f}-{_pct(lv, .9):.2f}) | {_pct(vt, .5):.2f} ({_pct(vt, .1):.2f})")


SCORES_HEAD = "Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %)"
NEW_DRIVER = """# {slug}

(What the driver is, and whose: to write.)

## Games

<!-- generated: games -->
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
<!-- end generated -->

(What these numbers mean for this driver: to write.)

## Scores

<!-- generated: scores -->
<!-- end generated -->

## The converter

(What the converter does for this driver: to write.)

## For generation

(What defines its sound: to write.)

## Open

(Found by the sweep, not yet looked into: to write.)
"""


def cmd_doc(args) -> int:
    manifest = load_manifest(args.spc_root)
    with open(args.traits) as fh:
        traits = json.load(fh)
    with open(args.results) as fh:
        results = [json.loads(line) for line in fh]
    scored = [r for r in results if "error" not in r and r.get("contour") is not None and r["emu_rms"] >= 50]
    console = os.path.join(args.docs, "snes")
    by_driver = defaultdict(list)
    for folder in sorted({t["game_folder"] for t in traits}):
        by_driver[manifest.get(folder, {}).get("driver", folder)].append(folder)
    games, composers, names = [], defaultdict(lambda: (set(), set())), {}
    for slug, folders in sorted(by_driver.items()):
        path = os.path.join(console, f"{slug}.md")
        if not os.path.exists(path):
            with open(path, "w") as fh:
                fh.write(NEW_DRIVER.format(slug=slug))
            print(f"{path}: new, to fill in")
        with open(path) as fh:
            text = fh.read()
        names[slug] = text.splitlines()[0].lstrip("# ").strip()
        rows = []
        for folder in folders:
            ts = [t for t in traits if t["game_folder"] == folder]
            entry = manifest.get(folder, {})
            game = entry.get("game") or _commonest(t["game"] for t in ts) or folder
            credit = entry.get("composer") or _credit(_commonest(t["artist"] for t in ts))
            songs = f"{len(ts)} ({sum(1 for r in scored if r['game'] == folder)})"
            rows.append(f"| {game} | {credit} | {songs} |")
            games.append((game, credit, slug, songs))
            composers[credit][0].add(game)
            composers[credit][1].add(slug)
        ts = [t for t in traits if t["game_folder"] in folders]
        rs = [r for r in scored if r["game"] in folders]
        text = fill(text, "games", "| Game | Composer (as the tags credit) | Songs (scored) |\n|---|---|---|\n" + "\n".join(rows))
        text = fill(text, "traits", "| Trait | Measured |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in trait_rows(ts)))
        text = fill(text, "scores", f"| {SCORES_HEAD} |\n|---|---|---|---|---|\n| {_scores(rs)} |" if rs else "No song scored yet.")
        with open(path, "w") as fh:
            fh.write(text)
    path = os.path.join(console, "README.md")
    with open(path) as fh:
        text = fh.read()
    lines = [f"| [{names[slug]}]({slug}.md) | {_scores([r for r in scored if r['game'] in folders])} |"
             for slug, folders in sorted(by_driver.items(), key=lambda kv: names[kv[0]]) if any(r["game"] in folders for r in scored)]
    text = fill(text, "scores", f"| Driver | {SCORES_HEAD} |\n|---|---|---|---|---|---|\n" + "\n".join(lines)
                + f"\n| **All** | {_scores(scored)} |")
    with open(path, "w") as fh:
        fh.write(text)
    path = os.path.join(args.docs, "README.md")
    with open(path) as fh:
        text = fh.read()
    text = fill(text, "games snes", "| Game | Composer (as the tags credit) | Music driver | Songs (scored) |\n|---|---|---|---|\n"
                + "\n".join(f"| {g} | {c} | [{names[s]}](snes/{s}.md) | {n} |" for g, c, s, n in sorted(games)))
    text = fill(text, "composers snes", "| Composer (as the tags credit) | Games | Drivers |\n|---|---|---|\n"
                + "\n".join(f"| {c} | {', '.join(sorted(gs))} | {', '.join(f'[{names[s]}](snes/{s}.md)' for s in sorted(ss))} |"
                             for c, (gs, ss) in sorted(composers.items(), key=lambda kv: kv[0].strip('"').lower())))
    with open(path, "w") as fh:
        fh.write(text)
    print(f"{args.docs}: {len(by_driver)} drivers, {len(games)} games, {len(scored)} songs scored")
    return 0


# report --------------------------------------------------------------------

def _pct(xs, p):
    xs = sorted(x for x in xs if x is not None)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")


def _voices_that_matter(r):
    """A song's voices carrying at least 5% of its loudest voice's RMS."""
    vs = r.get("voices", {})
    loud = max((x["rms"] for x in vs.values()), default=0)
    return [(int(v), x) for v, x in vs.items() if x["rms"] >= 0.05 * loud and x.get("contour") is not None]


def cmd_report(args) -> int:
    recs = [json.loads(line) for line in open(args.results)]
    ok = [r for r in recs if "error" not in r]
    failed = [r for r in recs if "error" in r]
    silent = [r for r in ok if r["emu_rms"] < 50 or r.get("contour") is None]
    scored = [r for r in ok if r not in silent]
    print(f"{len(recs)} songs: {len(scored)} measured, {len(silent)} near-silent in the emulator (not scored), {len(failed)} failed")
    by_driver = defaultdict(list)
    for r in scored:
        by_driver[r.get("driver", r["game"])].append(r)
    w = max([len(k) for k in by_driver] + [len("ALL")]) + 1
    print(f"\n{'music driver':{w}s} {'songs':>5s} | {'contour 10%':>11s} {'median':>6s} | {'gap dB 50%':>10s} {'90%':>5s} | "
          f"{'level 10%':>9s} {'median':>6s} {'90%':>5s} | {'voices':>6s} {'tone 10%':>8s} {'median':>6s}")
    for drv, rs in sorted(by_driver.items()) + [("ALL", scored)]:
        vt = [x["tone"] for r in rs for _, x in _voices_that_matter(r)]
        print(f"{drv:{w}s} {len(rs):5d} | {_pct([r['contour'] for r in rs], .1):11.2f} {_pct([r['contour'] for r in rs], .5):6.2f} | "
              f"{_pct([r['gap_db'] for r in rs], .5):10.2f} {_pct([r['gap_db'] for r in rs], .9):5.2f} | "
              f"{_pct([r['level'] for r in rs], .1):9.2f} {_pct([r['level'] for r in rs], .5):6.2f} {_pct([r['level'] for r in rs], .9):5.2f} | "
              f"{len(vt):6d} {_pct(vt, .1):8.2f} {_pct(vt, .5):6.2f}")
    vs = [(r, v, x) for r in scored for v, x in _voices_that_matter(r)]
    print("\nVoices sounding different (lowest tone):")
    for r, v, x in sorted(vs, key=lambda t: t[2]["tone"])[:args.top]:
        print(f"  tone {x['tone']:5.2f}  gap {_fmt(x['gap_db'], '4.1f')} dB  level {_fmt(x['level'], '4.2f')}  "
              f"{r['game']}/{r['song']} voice {v}")
    print("\nVoices whose loudness over time is off (largest gap):")
    for r, v, x in sorted(vs, key=lambda t: -(t[2]["gap_db"] or 0))[:args.top]:
        print(f"  gap {x['gap_db']:5.1f} dB  contour {x['contour']:5.2f}  level {_fmt(x['level'], '4.2f')}  "
              f"{r['game']}/{r['song']} voice {v}")
    print("\nSongs with the lowest contour (with a small gap: a steady sound that matches):")
    for r in sorted(scored, key=lambda r: r["contour"])[:args.top]:
        print(f"  contour {r['contour']:5.2f}  gap {_fmt(r['gap_db'], '4.1f')} dB  level {r['level']:4.2f}  {r['game']}/{r['song']}")
    limits = [r for r in ok if (r.get("instruments") or 0) >= convert.MAX_INSTRUMENTS or (r.get("samples") or 0) >= 255
              or r.get("unbaked")]
    print(f"\nAt an IT limit, or with pitch-modulated notes left unbaked: {len(limits)}")
    for r in limits:
        print(f"  {r['game']}/{r['song']}: {r['instruments']} instruments, {r['samples']} samples, {r['unbaked']} unbaked")
    if silent:
        print("\nNear-silent in the emulator: " + ", ".join(f"{r['game']}/{r['song']}" for r in silent))
    for r in failed:
        print(f"\nFAILED {r['game']}/{r['song']}: {r['error']}\n{r['trace']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="spc_check", description="Measure SPC-to-IT conversions against the emulator.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("voice", help="one song, voice by voice")
    v.add_argument("file")
    v.add_argument("--seconds", type=float, default=30.0)
    v.add_argument("--voices", help="comma-separated voices (default: every voice that sounds)")
    v.add_argument("--bands", action="store_true", help="each voice's octave levels, module over original")
    v.add_argument("--trace", type=int, metavar="VOICE", help="one voice's loudness over time")
    v.add_argument("--step", type=float, default=0.5, help="seconds a --trace line covers")
    s = sub.add_parser("sweep", help="every SPC file under SPC_ROOT/<game>/, in parallel")
    s.add_argument("spc_root")
    s.add_argument("out_dir")
    s.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    s.add_argument("--seconds", type=float, default=30.0, help="seconds of each song measured")
    d = sub.add_parser("doc", help="the measured parts of docs/drivers/, from traits and a sweep")
    d.add_argument("spc_root")
    d.add_argument("traits")
    d.add_argument("results")
    d.add_argument("--docs", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "drivers"))
    t = sub.add_parser("traits", help="what each song's driver does with the SNES chip, per game")
    t.add_argument("spc_root")
    t.add_argument("out")
    t.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    r = sub.add_parser("report", help="summarise a sweep's results.jsonl")
    r.add_argument("results")
    r.add_argument("--top", type=int, default=15, help="lines in each list")
    args = ap.parse_args(argv)
    try:
        return {"voice": cmd_voice, "sweep": cmd_sweep, "report": cmd_report, "traits": cmd_traits,
                "doc": cmd_doc}[args.cmd](args)
    except emulate.EmulatorMissing as e:
        print(f"spc_check: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
