"""What SPC snapshots hold, and their samples as WAV files.

    python -m bitcomposer.spc song.spc [...]              tags, echo, voices, samples
    python -m bitcomposer.spc --export DIR song.spc [...]  every sample, once, as WAV + samples.json
    python -m bitcomposer.spc --notes [SECONDS] song.spc   run the driver: the notes it plays
    python -m bitcomposer.spc --to-it OUT.it [--seconds N] song.spc   the song as an IT module, one to one
    python -m bitcomposer.spc --pack OUT [--name NAME] FOLDER|ARCHIVE   a pack of a game's songs: its samples, its habits

Exported samples are 16-bit mono at 32 kHz, the rate the DSP plays them at
pitch 0x1000; samples.json gives each one's loop and the snapshots and
directory entries it came from. A sample shared by many songs is written
once. The files stay the user's: nothing here is meant to be published.
"""
import argparse
import hashlib
import json
import sys
import wave
from pathlib import Path

from . import RATE, SPCError, read


def describe(snap) -> str:
    t, e = snap.tags, snap.echo
    lines = [f"== {Path(snap.source).name}"]
    if t.title or t.game:
        lines.append(f"   {t.title or '?'}  ({t.game or '?'})" + (f", {t.artist}" if t.artist else ""))
    if t.length_s:
        lines.append(f"   plays {t.length_s} s" + (f", fades {t.fade_ms} ms" if t.fade_ms else ""))
    if e.on:
        lines.append(f"   echo {e.delay_ms} ms, feedback {e.feedback:+.2f}, volume {e.volume[0]:+.2f}/{e.volume[1]:+.2f}, "
                     f"on voices {list(e.voices)}, FIR {list(e.fir)}")
    else:
        lines.append("   echo off")
    samples = snap.samples()
    for v in snap.voices:
        if not v.sounding:
            continue
        env = (f"ADSR attack {v.attack} decay {v.decay} sustain {v.sustain_level}/{v.sustain_rate}" if v.adsr
               else f"GAIN {v.gain:#04x}")
        what = "noise" if v.noise else f"sample {v.sample}"
        lines.append(f"   voice {v.index}: {what}, pitch {v.pitch:#06x} ({RATE * v.pitch / 0x1000:7.0f} Hz playback), "
                     f"volume {v.volume[0]:+d}/{v.volume[1]:+d}, {env}{', echo' if v.echo else ''}")
    lines.append(f"   {len(samples)} samples in the directory")
    for n, s in samples.items():
        loop = f"loop {s.loop_start}-{s.loop_end}{'' if s.seamless else ' (seam)'}" if s.loops else "one-shot"
        lines.append(f"     {n:3d}: {len(s):6d} frames ({1000 * len(s) / RATE:6.0f} ms), {loop}")
    return "\n".join(lines)


def export(snaps, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    found = {}
    for snap in snaps:
        playing = {v.sample for v in snap.voices if v.sounding and not v.noise}
        for n, s in snap.samples().items():
            key = hashlib.sha1(s.pcm.tobytes()).hexdigest()[:10]
            entry = found.setdefault(key, {"file": f"brr_{key}.wav", "frames": len(s),
                                           "loop": [s.loop_start, s.loop_end] if s.loops else None,
                                           "seamless": s.seamless, "from": [], "_pcm": s.pcm})
            entry["from"].append({"snapshot": Path(snap.source).name, "entry": n, "playing": n in playing})
    for e in found.values():
        pcm = e.pop("_pcm")
        with wave.open(str(out / e["file"]), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
            w.writeframes(pcm.tobytes() if sys.byteorder == "little" else _swapped(pcm))
    rows = sorted(found.values(), key=lambda e: (-len(e["from"]), e["file"]))
    (out / "samples.json").write_text(json.dumps({"rate": RATE, "samples": rows}, indent=1))
    return len(rows)


def _swapped(pcm) -> bytes:
    a = pcm[:]
    a.byteswap()
    return a.tobytes()


def show_notes(snap, seconds: float) -> str:
    from . import emulate, notes, tuning
    run = emulate.run(snap, seconds)
    found = notes.decode(snap, run.writes)
    f0 = {}
    for n in found:
        if n.sample not in f0:
            s = snap.sample(n.sample)
            f0[n.sample] = tuning.fundamental(s) if s is not None and not n.noise else None
    lines = [f"== {Path(snap.source).name}: {len(found)} notes in {run.seconds:.1f} s "
             f"({run.instructions / 1e6:.1f} M instructions, {len(run.writes)} SNES chip writes)"]
    for n in found:
        what = "noise" if n.noise else (tuning.name(tuning.midi(f0[n.sample], n.pitch)) if f0.get(n.sample) else "-")
        length = f"{n.length:6.3f}" if n.length is not None else "  open"
        extra = (f" {len(n.bends)} bends" if n.bends else "") + (f" {len(n.swells)} swells" if n.swells else "")
        lines.append(f"  {n.start:8.3f}  voice {n.voice}  sample {n.sample:3d}  {what:10s} {length} s  "
                     f"vol {n.volume[0]:+4d}/{n.volume[1]:+4d}{'  echo' if n.echo else ''}{extra}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.spc", description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", metavar="FILE.spc", help="snapshots (with --pack, folders of them too, or a set: zip, rsn, rar, 7z)")
    ap.add_argument("--export", metavar="DIR", help="write every sample, once, as WAV, with samples.json")
    ap.add_argument("--notes", nargs="?", type=float, const=20.0, metavar="SECONDS",
                    help="run the driver (default 20 s) and list the notes it plays")
    ap.add_argument("--to-it", metavar="OUT.it", help="convert the song to an IT module, one to one")
    ap.add_argument("--seconds", type=float, help="with --to-it: how much of the song (default: its tag's length, or 90 s)")
    ap.add_argument("--pack", metavar="OUT", help="read a game's songs and write a pack of them into OUT "
                    "(pack.json and its samples; see docs/TRANSLATOR.md, stage 2); play it with bitcomposer --pack-file")
    ap.add_argument("--name", help="with --pack: the pack's name (default: from the folder's)")
    ap.add_argument("--progress", metavar="FILE",
                    help="with --pack: add a line 'progress DONE TOTAL' to FILE after each song, and "
                         "'error WHY' if it stops (the player's PACKS panel reads it)")
    args = ap.parse_args(argv)
    if args.pack:
        from ..translate import pack
        from .emulate import EmulatorMissing

        def note(line):
            if args.progress:
                with open(args.progress, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        try:
            pack.make(args.files, args.pack, args.name, progress=lambda done, total: note(f"progress {done} {total}"))
        except (EmulatorMissing, ValueError, SPCError) as e:
            note(f"error {e}")
            print(f"bitcomposer.spc: {e}", file=sys.stderr)
            return 1
        except Exception as e:                   # said where the player looks, then the traceback
            note(f"error {type(e).__name__}: {e}")
            raise
        return 0
    snaps = []
    for f in args.files:
        try:
            snaps.append(read(f))
        except SPCError as e:
            print(f"bitcomposer.spc: {e}", file=sys.stderr)
            return 1
    if args.to_it:
        from .convert import convert
        from .emulate import EmulatorMissing
        if len(snaps) != 1:
            print("bitcomposer.spc: --to-it converts one file at a time", file=sys.stderr)
            return 1
        try:
            song = convert(snaps[0], args.seconds, args.to_it)
        except EmulatorMissing as e:
            print(f"bitcomposer.spc: {e}", file=sys.stderr)
            return 1
        i = song["info"]
        print(f"{args.to_it}: {i['notes']} notes in {i['seconds']:.1f} s, {i['samples']} samples, "
              f"{i['instruments']} instruments; rows at {i['row_hz']:.1f} a second "
              f"({'the driver clock' if i['on_ticks'] else 'the finest grid'}; key-ons {i['aligned']:.2f} aligned with a "
              f"{i['tick_hz']:.1f} Hz timer)" + (f"; {i['baked']} pitch-modulated notes kept as played, in {i['bakes']} "
              f"recordings" if i['baked'] else "") + (f"; {i['unbaked']} more did not fit" if i['unbaked'] else ""))
        return 0
    if args.notes is not None:
        from .emulate import EmulatorMissing
        try:
            print("\n\n".join(show_notes(s, args.notes) for s in snaps))
        except EmulatorMissing as e:
            print(f"bitcomposer.spc: {e}", file=sys.stderr)
            return 1
        return 0
    if args.export:
        n = export(snaps, Path(args.export))
        print(f"{n} samples from {len(snaps)} snapshot{'s' if len(snaps) != 1 else ''} -> {args.export}")
    else:
        print("\n\n".join(describe(s) for s in snaps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
