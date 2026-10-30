"""The tune's salience, measured on renders: each part alone under the whole song (RMS dBFS and K-weighted LUFS over the
first minute, through ffmpeg's libopenmpt), and the tune's margin over the loudest other pitched line.

    python tools/salience.py DIR [DIR ...] [--label NAME] [--seconds 60]

DIR holds whole songs and their stems, either as the whole-song writer leaves them ("Whole 12.it" with
"stems/Whole 12 melody.it", tools/whole.py --stems) or as the readings' per-part renders ("<sid>.it" with
"<sid>-melody.it"). Prints, per song, each part under the whole and the tune's margin; then the medians and quartiles.
Song Check 50 (2026-10-29): a tune on top, or within half a decibel of it, belonged in four songs of four; a tune three
decibels or more under did not in five of six. FFVI's own labelled melody sits a median 3.5 dB under (themed 4.7)."""
import argparse
import glob
import io
import math
import os
import re
import statistics
import subprocess
import wave
from collections import defaultdict

PITCHED = ("melody", "counter", "accompaniment", "harmony", "arp", "bass")


def rms_dbfs(path: str, seconds: float) -> float | None:
    d = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-t", str(seconds), "-i", path, "-ac", "1", "-ar", "32000", "-f", "wav", "-"],
                       capture_output=True).stdout
    try:
        w = wave.open(io.BytesIO(d))
    except Exception:
        return None
    frames = w.readframes(w.getnframes())
    import array
    x = array.array("h", frames[: len(frames) - len(frames) % 2])
    loud = [v for v in x if abs(v) > 50]
    return 20 * math.log10(math.sqrt(sum(v * v for v in loud) / len(loud)) / 32768) if loud else None


def lufs(path: str, seconds: float) -> float | None:
    o = subprocess.run(["ffmpeg", "-nostats", "-t", str(seconds), "-i", path, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", o)
    return float(m.group(1)) if m else None


def songs_in(folder: str) -> dict:
    """{name: (whole path, {part: stem path})} for either layout."""
    out = {}
    for whole in sorted(glob.glob(os.path.join(folder, "*.it"))):
        name = os.path.basename(whole)[:-3]
        if "-" in name and not name.startswith("Whole"):
            continue
        stems = {os.path.basename(p)[len(name) + 1:-3]: p for p in glob.glob(os.path.join(folder, "stems", f"{name} *.it"))}
        if not stems:
            stems = {os.path.basename(p)[len(name) + 1:-3]: p for p in glob.glob(os.path.join(folder, f"{name}-*.it"))}
        if stems:
            out[name] = (whole, stems)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--label", default="")
    ap.add_argument("--seconds", type=float, default=60.0)
    a = ap.parse_args(argv)
    under = defaultdict(lambda: defaultdict(list))
    margins = {"rms": [], "lufs": []}
    for folder in a.dirs:
        for name, (whole, stems) in songs_in(folder).items():
            w = {"rms": rms_dbfs(whole, a.seconds), "lufs": lufs(whole, a.seconds)}
            parts = {}
            for part, path in stems.items():
                parts[part] = {"rms": rms_dbfs(path, a.seconds), "lufs": lufs(path, a.seconds)}
            line = []
            for kind in ("rms", "lufs"):
                if w[kind] is None:
                    continue
                rel = {p: v[kind] - w[kind] for p, v in parts.items() if v[kind] is not None}
                for p, v in rel.items():
                    under[kind][p].append(v)
                others = [v for p, v in rel.items() if p in PITCHED and p != "melody"]
                if "melody" in rel and others:
                    margins[kind].append(rel["melody"] - max(others))
                    line.append(f"{kind} margin {rel['melody'] - max(others):+5.1f}")
                if kind == "lufs":
                    line.append(" ".join(f"{p} {v:+.1f}" for p, v in sorted(rel.items(), key=lambda kv: -kv[1])))
            print(f"{name:<22} " + " | ".join(line))
    label = a.label or ", ".join(a.dirs)
    for kind in ("rms", "lufs"):
        m = margins[kind]
        if m:
            q = statistics.quantiles(m, n=4) if len(m) > 3 else [min(m), statistics.median(m), max(m)]
            print(f"== {label} [{kind}] tune margin over the loudest other pitched line: median {statistics.median(m):.1f}, quartiles {q[0]:.1f} .. {q[2]:.1f}; "
                  f"on top (>= -0.5) {sum(1 for x in m if x >= -0.5)} of {len(m)}; 3 dB or more under {sum(1 for x in m if x <= -3)}")
            print(f"   each part under the whole (median): " + ", ".join(f"{p} {statistics.median(v):.1f}" for p, v in sorted(under[kind].items(), key=lambda kv: -statistics.median(kv[1]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
