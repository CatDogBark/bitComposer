"""What SPC snapshots hold, and their samples as WAV files.

    python -m bitcomposer.spc song.spc [...]              tags, echo, voices, samples
    python -m bitcomposer.spc --export DIR song.spc [...]  every sample, once, as WAV + samples.json

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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.spc", description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", metavar="FILE.spc")
    ap.add_argument("--export", metavar="DIR", help="write every sample, once, as WAV, with samples.json")
    args = ap.parse_args(argv)
    snaps = []
    for f in args.files:
        try:
            snaps.append(read(f))
        except SPCError as e:
            print(f"bitcomposer.spc: {e}", file=sys.stderr)
            return 1
    if args.export:
        n = export(snaps, Path(args.export))
        print(f"{n} samples from {len(snaps)} snapshot{'s' if len(snaps) != 1 else ''} -> {args.export}")
    else:
        print("\n\n".join(describe(s) for s in snaps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
