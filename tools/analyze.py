#!/usr/bin/env python3
"""
Generation-quality regression harness for BitComposer.

Parses .it files back from disk and scores them on the metrics that correlate
with "sounds like a song" — pattern reuse, motif repetition, rhythmic grid,
chord voicing variety, harmony movement, and effect vocabulary.

Deliberately standalone: stdlib only, and it does NOT import bitcomposer. It
reads the actual bytes that were written, so it catches bugs in the writer as
well as the generator.

Usage:
    python3 tools/analyze.py '/tmp/out/*.it'       # batch metric table
    python3 tools/analyze.py --grid song.it        # tracker-style pattern dump
    python3 tools/analyze.py --grid song.it -p 3   # ...for pattern index 3

See docs/ANALYSIS.md for what the numbers mean and what baseline they replaced.
"""

import argparse
import glob
import statistics
import struct
from collections import Counter

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
EFF = ".ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # IT command letters, 1=A

# Channel layout (mirrors bitcomposer.pattern)
CH_MELODY, CH_BASS, CH_ARP = 0, 4, 5
CH_HARMONY = (1, 2, 3)
DRUM_NAMES = {6: "kick", 7: "snare", 8: "hat", 9: "tom", 10: "crash", 11: "ohat"}

ROWS_PER_BAR = 16  # 4 rows per quarter note at IT's standard speed/tempo pairing


def note_str(n):
    if n == 255:
        return "=="
    if n == 254:
        return "^^"
    if n >= 120:
        return "~~"
    return f"{NOTE_NAMES[n % 12]}{n // 12}"


class IT:
    """Minimal Impulse Tracker module reader — enough to inspect note data."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            d = fh.read()
        self.raw = d
        self.path = path
        if d[:4] != b"IMPM":
            raise ValueError(f"{path}: not an IT module (bad magic)")
        self.name = d[4:30].split(b"\0")[0].decode("latin1")
        (self.ordnum, self.insnum, self.smpnum, self.patnum,
         self.cwt, self.cmwt, self.flags, self.special) = struct.unpack(
            "<8H", d[0x20:0x30])
        (self.gv, self.mv, self.speed, self.tempo,
         self.sep, self.pwd) = struct.unpack("<6B", d[0x30:0x36])
        self.chnvol = list(d[0x80:0xC0])

        o = 0xC0
        self.orders = list(d[o:o + self.ordnum])
        o += self.ordnum
        o += 4 * self.insnum  # instrument offsets (unused — we write samples)
        self.smpoff = list(struct.unpack(f"<{self.smpnum}I", d[o:o + 4 * self.smpnum]))
        o += 4 * self.smpnum
        self.patoff = list(struct.unpack(f"<{self.patnum}I", d[o:o + 4 * self.patnum]))
        self.patterns = [self._pattern(x) for x in self.patoff]

    def _pattern(self, off):
        """Return rows: list of {channel: (note, ins, vol, cmd, cmdval)}."""
        if off == 0 or off + 8 > len(self.raw):
            return [{} for _ in range(64)]
        length, rows = struct.unpack("<HH", self.raw[off:off + 4])
        data = self.raw[off + 8:off + 8 + length]
        out = [dict() for _ in range(rows)]
        lastmask, lastnote, lastins = {}, {}, {}
        lastvol, lastcmd, lastval = {}, {}, {}
        p, row = 0, 0
        while row < rows and p < len(data):
            cv = data[p]
            p += 1
            if cv == 0:
                row += 1
                continue
            ch = (cv - 1) & 63
            if cv & 128:
                lastmask[ch] = data[p]
                p += 1
            m = lastmask.get(ch, 0)
            note = ins = vol = cmd = val = None
            if m & 1:
                note = data[p]; p += 1; lastnote[ch] = note
            if m & 2:
                ins = data[p]; p += 1; lastins[ch] = ins
            if m & 4:
                vol = data[p]; p += 1; lastvol[ch] = vol
            if m & 8:
                cmd, val = data[p], data[p + 1]; p += 2
                lastcmd[ch], lastval[ch] = cmd, val
            if m & 16:
                note = lastnote.get(ch)
            if m & 32:
                ins = lastins.get(ch)
            if m & 64:
                vol = lastvol.get(ch)
            if m & 128:
                cmd, val = lastcmd.get(ch), lastval.get(ch)
            if row < rows:
                out[row][ch] = (note, ins, vol, cmd, val)
        return out

    def played(self):
        """Order list filtered to real pattern indices (drops 254/255 markers)."""
        return [o for o in self.orders if o < len(self.patterns)]

    def notes_on(self, pat_idx, ch):
        """[(row, note)] for real notes on a channel — excludes cut/off."""
        return [(r, rd[ch][0]) for r, rd in enumerate(self.patterns[pat_idx])
                if ch in rd and rd[ch][0] is not None and rd[ch][0] < 120]


def analyze(path):
    m = IT(path)
    real = m.played()
    tonal = (CH_MELODY,) + CH_HARMONY + (CH_BASS, CH_ARP)
    out = {"name": path.rsplit("/", 1)[-1],
           "orders": len(real), "patterns": len(m.patterns)}

    # How much of the song replays earlier material? 0 = through-composed.
    counts = Counter(real)
    out["order_reuse_pct"] = 100.0 * sum(n - 1 for n in counts.values()) / max(len(real), 1)

    # Melody patterns that are byte-identical to another. 100% unique = no hook.
    sigs = [s for s in (tuple(m.notes_on(oi, CH_MELODY)) for oi in real) if s]
    out["mel_uniq_pct"] = 100.0 * len(set(sigs)) / max(len(sigs), 1)

    # Rhythmic grid: onsets on odd rows = 16th-note syncopation exists at all.
    odd = tot = offgrid = 0
    for oi in real:
        for ch in tonal:
            for r, _ in m.notes_on(oi, ch):
                tot += 1
                odd += r % 2
                offgrid += r % 4 != 0
    out["odd_row_pct"] = 100.0 * odd / max(tot, 1)
    out["offgrid_pct"] = 100.0 * offgrid / max(tot, 1)

    # Motif reuse: repeated 4-gram interval sequences across the whole melody.
    seq = [n for oi in real for _, n in m.notes_on(oi, CH_MELODY)]
    iv = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    grams = Counter(tuple(iv[i:i + 4]) for i in range(len(iv) - 3))
    total_grams = sum(grams.values())
    out["motif_reuse_pct"] = 100.0 * sum(
        n for n in grams.values() if n > 1) / max(total_grams, 1)
    out["mel_notes"] = len(seq)

    # Distinct chord shapes actually sounding on the harmony channels.
    voicings = set()
    for oi in real:
        for rd in m.patterns[oi]:
            stack = sorted(e[0] for ch, e in rd.items()
                           if ch in CH_HARMONY and e[0] is not None and e[0] < 120)
            if len(stack) >= 2:
                voicings.add(tuple(stack[i + 1] - stack[i]
                                   for i in range(len(stack) - 1)))
    out["distinct_voicings"] = len(voicings)

    # Voice leading: mean absolute semitone motion of each harmony voice from
    # one pattern to the next. This is the metric that shows whether chords are
    # voiced smoothly. Note that "does a voice hold its pitch WITHIN a pattern"
    # is not a defect — a pattern carries a single chord, so holding is correct.
    # 0 means the harmony never moves; a large value means it leaps between
    # root positions. Smooth voice leading sits around 1-3 semitones.
    motion = []
    for a, b in zip(real, real[1:]):
        for ch in CH_HARMONY:
            na = m.notes_on(a, ch)
            nb = m.notes_on(b, ch)
            if na and nb:
                motion.append(abs(nb[0][1] - na[0][1]))
    out["voice_motion"] = float(statistics.mean(motion)) if motion else 0.0

    # Melodic rhythm variety, and the IT effect vocabulary that reached the file.
    iois = []
    for oi in real:
        rows = [r for r, _ in m.notes_on(oi, CH_MELODY)]
        iois.extend(rows[i + 1] - rows[i] for i in range(len(rows) - 1))
    out["distinct_ioi"] = len(set(iois))
    out["ioi_top"] = Counter(iois).most_common(3)

    fx = Counter(EFF[e[3]] for oi in real for rd in m.patterns[oi]
                 for e in rd.values() if e[3])
    out["fx"] = "".join(sorted(fx))
    out["n_fx"] = len(fx)

    # Drum density, in hits per bar — the metric that exposed the 4x grid stretch.
    bars = len(real) * 64 / ROWS_PER_BAR
    for ch, nm in DRUM_NAMES.items():
        hits = sum(len(m.notes_on(oi, ch)) for oi in real)
        out[f"{nm}_per_bar"] = hits / max(bars, 1)
    out["bars"] = bars
    return out


def grid(path, pat_idx=None, rows=64):
    """Tracker-style dump of one pattern — the view that makes rhythm obvious."""
    m = IT(path)
    real = m.played()
    if pat_idx is None:  # default: the pattern with the most drum activity
        def drumhits(oi):
            return sum(len(m.notes_on(oi, c)) for c in DRUM_NAMES)
        pat_idx = max(real, key=drumhits)
    print(f"{path} — pattern {pat_idx}  (| = bar, + = quarter note)")
    print("      " + "".join(
        "|" if r % ROWS_PER_BAR == 0 else ("+" if r % 4 == 0 else ".")
        for r in range(rows)))
    labels = {CH_MELODY: "mel ", 1: "hrm1", 2: "hrm2", 3: "hrm3",
              CH_BASS: "bass", CH_ARP: "arp "}
    labels.update({c: f"{n:<4}" for c, n in DRUM_NAMES.items()})
    for ch in sorted(labels):
        line = "".join(
            "X" if (ch in m.patterns[pat_idx][r]
                    and m.patterns[pat_idx][r][ch][0] is not None
                    and m.patterns[pat_idx][r][ch][0] < 120) else "-"
            for r in range(min(rows, len(m.patterns[pat_idx]))))
        if "X" in line:
            print(f"{labels[ch]} {line}")


KEYS = ["orders", "patterns", "order_reuse_pct", "mel_uniq_pct", "odd_row_pct",
        "offgrid_pct", "motif_reuse_pct", "distinct_voicings", "voice_motion",
        "distinct_ioi", "n_fx"]
DRUM_KEYS = ["kick_per_bar", "snare_per_bar", "hat_per_bar"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", help="path or glob of .it files")
    ap.add_argument("--grid", action="store_true", help="dump one pattern instead")
    ap.add_argument("-p", "--pattern", type=int, default=None,
                    help="pattern index for --grid (default: busiest drums)")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.files)) or [args.files]
    if args.grid:
        grid(paths[0], args.pattern)
        return

    rows = [analyze(p) for p in paths]
    hdr = f"{'file':<10}" + "".join(f"{k[:9]:>11}" for k in KEYS) + "  fx"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['name']:<10}" + "".join(
            f"{r[k]:>11.1f}" if isinstance(r[k], float) else f"{r[k]:>11}"
            for k in KEYS) + f"  {r['fx']}")
    print("-" * len(hdr))
    print(f"{'MEAN':<10}" + "".join(
        f"{statistics.mean([r[k] for r in rows]):>11.1f}" for k in KEYS))

    print("\ndrum hits per bar (a real groove is ~2-4 kick, ~2 snare, 4-8 hat):")
    print(f"  {'file':<10}" + "".join(f"{k.split('_')[0]:>9}" for k in DRUM_KEYS))
    for r in rows:
        print(f"  {r['name']:<10}" + "".join(f"{r[k]:>9.2f}" for k in DRUM_KEYS))
    print(f"  {'MEAN':<10}" + "".join(
        f"{statistics.mean([r[k] for r in rows]):>9.2f}" for k in DRUM_KEYS))

    print("\nmelody inter-onset intervals (top 3):")
    for r in rows:
        print(f"  {r['name']}: {r['ioi_top']}  ({r['mel_notes']} notes)")


if __name__ == "__main__":
    main()
