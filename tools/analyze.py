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
CH_ECHO = (12, 13)
DRUM_NAMES = {6: "kick", 7: "snare", 8: "hat", 9: "tom", 10: "crash", 11: "ohat"}

ROWS_PER_BEAT = 4  # rows to a quarter note
ROWS_PER_BAR = 16  # 4 beats of 4 rows


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

    # Audible tempo, not the stored field. IT's tempo byte only equals BPM at
    # speed 6: a row lasts 2.5 * speed / tempo seconds, so with ROWS_PER_BEAT
    # rows to a quarter note the real tempo is 24 * tempo / (speed * rows per
    # beat). Choosing speed independently of tempo once pushed songs to 212 BPM
    # while the CLI cheerfully reported "141".
    out["bpm"] = 24.0 * m.tempo / (m.speed * ROWS_PER_BEAT)

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

    # Melody craft. Strong-beat chord fit: on beats 1 and 3, is the melody
    # note a chord tone of the chord the bass states at the bar's downbeat
    # (root, third of either kind, fifth, seventh)? End hold: how long the
    # last melody note of a pattern rings before it is cut. Climax position:
    # where in the pattern the highest note falls (0 = start, 1 = end); a
    # phrase that peaks late reads ~0.5-0.75. Register spread: how much the
    # per-pattern mean pitch moves across the song (verse low, chorus high).
    CHORD_INTERVALS = {0, 3, 4, 7, 10, 11}
    strong = fit = 0
    holds, climaxes, means = [], [], []
    for oi in real:
        pat = m.patterns[oi]
        mel = m.notes_on(oi, CH_MELODY)
        if not mel:
            continue
        for bar in range(0, len(pat), ROWS_PER_BAR):
            bass = pat[bar].get(CH_BASS)
            root = bass[0] % 12 if bass and bass[0] is not None and bass[0] < 120 else None
            if root is None:
                continue
            for r, n in mel:
                if bar <= r < bar + ROWS_PER_BAR and (r - bar) in (0, 8):
                    strong += 1
                    fit += (n - root) % 12 in CHORD_INTERVALS
        last_row = mel[-1][0]
        end = len(pat)
        for r in range(last_row + 1, len(pat)):
            e = pat[r].get(CH_MELODY)
            if e and e[0] is not None:
                end = r
                break
        holds.append(end - last_row)
        peak = max(mel, key=lambda x: (x[1], -x[0]))
        climaxes.append(peak[0] / max(len(pat) - 1, 1))
        means.append(statistics.mean(n for _, n in mel))
    out["mel_strong_fit_pct"] = 100.0 * fit / max(strong, 1)
    out["mel_end_hold"] = float(statistics.mean(holds)) if holds else 0.0
    out["mel_climax_pos"] = float(statistics.mean(climaxes)) if climaxes else 0.0
    out["mel_register_spread"] = float(statistics.pstdev(means)) if len(means) > 1 else 0.0

    # Cadences: at each pattern boundary, does the bass root in the last bar
    # of the pattern sit a fifth above (or a fourth below) the root the next
    # pattern opens on? That is V to I — a section ending that resolves.
    # Also the audible length of the song.
    def bar_root(pi, bar):
        pat = m.patterns[pi]
        for r in range(bar, min(bar + ROWS_PER_BAR, len(pat))):
            e = pat[r].get(CH_BASS)
            if e and e[0] is not None and e[0] < 120:
                return e[0] % 12
        return None
    v_i = boundaries = 0
    for a, b in zip(real, real[1:]):
        # The back half of a pattern starts at row 32; a walking bass puts a
        # chord tone, not the root, on later beats, so read the root there.
        ra, rb = bar_root(a, 32), bar_root(b, 0)
        if ra is None or rb is None:
            continue
        boundaries += 1
        v_i += (rb - ra) % 12 == 5
    out["v_to_i_pct"] = 100.0 * v_i / max(boundaries, 1)
    out["seconds"] = len(real) * 64 * 2.5 * m.speed / m.tempo

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

    # Arpeggio: how many distinct one-bar figures (row pattern + accent
    # pattern) the song uses, how dense it is next to the lead, and how many
    # distinct velocity levels it has (1 = flat, 2-3 = accented, many = jitter).
    figs = set()
    arp_notes = 0
    vols = set()
    for oi in real:
        pat = m.patterns[oi]
        for bar in range(0, len(pat), ROWS_PER_BAR):
            shape = []
            for r in range(bar, min(bar + ROWS_PER_BAR, len(pat))):
                e = pat[r].get(CH_ARP)
                if e and e[0] is not None and e[0] < 120:
                    shape.append((r - bar, e[2] if e[2] is not None else 64))
                    arp_notes += 1
                    vols.add(e[2] if e[2] is not None else 64)
            if shape:
                figs.add(tuple(shape))
    out["arp_figures"] = len(figs)
    out["arp_mel_ratio"] = arp_notes / max(len(seq), 1)
    out["arp_vol_levels"] = len(vols)

    # Drum density, in hits per bar — the metric that exposed the 4x grid stretch.
    bars = len(real) * 64 / ROWS_PER_BAR
    for ch, nm in DRUM_NAMES.items():
        hits = sum(len(m.notes_on(oi, ch)) for oi in real)
        out[f"{nm}_per_bar"] = hits / max(bars, 1)
    out["bars"] = bars

    # Drum variety: distinct one-bar shapes (which piece on which step, with
    # velocity), how often a bar repeats the one before, and how many
    # velocity levels the kick and snare use (1 = a machine).
    shapes = []
    kick_v, snare_v = set(), set()
    for oi in real:
        pat = m.patterns[oi]
        for bar in range(0, len(pat), ROWS_PER_BAR):
            shape = []
            for r in range(bar, min(bar + ROWS_PER_BAR, len(pat))):
                for ch, nm in DRUM_NAMES.items():
                    e = pat[r].get(ch)
                    if e and e[0] is not None and e[0] < 120:
                        v = e[2] if e[2] is not None else 64
                        shape.append((r - bar, nm))
                        if nm == "kick":
                            kick_v.add(v // 4)
                        elif nm == "snare":
                            snare_v.add(v // 4)
            shapes.append(tuple(shape))
    out["drum_shapes"] = len(set(shapes))
    out["drum_repeat_pct"] = 100.0 * sum(1 for a, b in zip(shapes, shapes[1:]) if a == b and a) / max(len(shapes) - 1, 1)
    out["kick_levels"] = len(kick_v)
    out["snare_levels"] = len(snare_v)
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
              CH_BASS: "bass", CH_ARP: "arp ", 12: "ech1", 13: "ech2"}
    labels.update({c: f"{n:<4}" for c, n in DRUM_NAMES.items()})
    for ch in sorted(labels):
        line = "".join(
            "X" if (ch in m.patterns[pat_idx][r]
                    and m.patterns[pat_idx][r][ch][0] is not None
                    and m.patterns[pat_idx][r][ch][0] < 120) else "-"
            for r in range(min(rows, len(m.patterns[pat_idx]))))
        if "X" in line:
            print(f"{labels[ch]} {line}")


KEYS = ["bpm", "orders", "patterns", "order_reuse_pct", "mel_uniq_pct",
        "odd_row_pct", "offgrid_pct", "motif_reuse_pct", "distinct_voicings",
        "voice_motion", "distinct_ioi", "n_fx", "arp_figures", "arp_mel_ratio",
        "arp_vol_levels", "drum_shapes", "drum_repeat_pct", "kick_levels", "snare_levels",
        "mel_strong_fit_pct", "mel_end_hold", "mel_climax_pos", "mel_register_spread",
        "v_to_i_pct", "seconds"]
DRUM_KEYS = ["kick_per_bar", "snare_per_bar", "hat_per_bar", "ohat_per_bar", "tom_per_bar", "crash_per_bar"]


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
