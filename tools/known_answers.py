"""The readers against songs with known answers: the generator's own (phase 1 of docs/IDIOM.md, step 3).

A composed song carries its plan in info["plan"] (the sections as played, each pattern's key, scale and
chord segments, the melody channel, the drum channels). Each song is read through the readers themselves
(roles.assign, harmony.key, harmony.chords, form.read) on the grid the generator wrote it to, and each
reader is scored against the plan:

    python tools/known_answers.py [--songs 120] [--seed 1]

- the key: tonic and mode (major or minor, the plan's modes folded as against.MINOR folds them); a reading
  of the mode's parent major, or of that key's relative, is its own kind of miss;
- the chords: beat by beat, the root's pitch class, and the shape's family (a third major, minor or none);
  the changes: the plan's chord changes against the read ones, within a beat;
- the form: the plan's section starts against the read parts' starts, within a bar;
- the parts: the melody channel read as the melody, the bass as the bass, the drum channels as drums;
- the drums: each kit preset named by its sound against the slot it fills.

The generator's songs are not played through the SNES chip, and they do nothing the games do that the
generator does not: a floor for the readers, not a pass.
"""
import argparse
import math
import sys
from collections import Counter, defaultdict

from bitcomposer import theory
from bitcomposer.composer import compose_song
from bitcomposer.pattern import CHANNEL_ROLES
from bitcomposer.translate import against, drums as drums_mod, form as form_mod, harmony, measures, reading, roles as R

FORMS = ("standard", "aaba", "rondo", "short", "linear")
FAMILIES = ("minor", "major", "pentatonic")
PARENT = {"dorian": 2, "phrygian": 4, "mixolydian": 7, "natural_minor": 9, "minor_pentatonic": 9, "major_pentatonic": 0, "major": 0}


class _Sample:
    def __init__(self, key):
        self.key = key


class _Note:
    def __init__(self, start, end, midi, level, voice, sample):
        self.start, self.end, self.midi, self.level, self.voice, self.sample, self.note = start, end, midi, level, voice, sample, None

    @property
    def length(self):
        return None if self.end is None else self.end - self.start


class _Song:
    def __init__(self, notes, seconds):
        self.notes, self.seconds, self.samples = notes, seconds, {}


class _Grid(against._Grid):
    """The generator's grid, with what the readers ask of a beat.Grid."""
    sections = ()
    loose = False

    def period_at(self, t):
        return 1.0


def third(intervals) -> str:
    return "major" if 4 in intervals else "minor" if 3 in intervals else "none"


def read_via_score(song: dict):
    """The song read as a game is: as a score (score.of_song), the beat found by the beat reader."""
    from bitcomposer import score as score_mod
    r = reading.of_score(score_mod.of_song(song), title=song.get("name", ""))
    return r


def read(song: dict):
    s = measures.of_composed(song)
    inst = song["info"].get("instruments", {})
    notes = []
    for n in s.notes:
        role = CHANNEL_ROLES[n.voice]
        key = inst.get(against.SLOTS.get(role, role), role) if role in against.DRUMS else f"ch{n.voice}"
        midi = None if n.midi is None or (isinstance(n.midi, float) and math.isnan(n.midi)) else n.midi
        notes.append(_Note(n.beat, s.end if n.beats is None else n.beat + n.beats, midi, n.level, n.voice, _Sample(key)))
    notes.sort(key=lambda p: (p.start, p.voice))
    like = _Song(notes, s.end * 60 / s.bpm)
    grid = _Grid(max(1, math.ceil(s.end)), list(s.bars))
    rl = R.assign(like, grid, R.echoes(like))
    chords = harmony.chords(like, grid, rl)
    return like, grid, rl, harmony.scale(like, grid, rl, chords), chords, form_mod.read(like, grid)


def truth_chords(song: dict) -> list:
    """The planned chord on every beat: [(root pc, family) or None]."""
    plan = song["info"]["plan"]
    rpp, rpb = plan["rows_per_pattern"], plan["rows_per_beat"]
    per_pattern = rpp // rpb
    out = []
    for o in song["orders"]:
        p = plan["patterns"][o]
        beats = [None] * per_pattern
        for r0, r1, root, ctype in p["chords"]:
            for b in range(r0 // rpb, min(per_pattern, math.ceil(r1 / rpb))):
                beats[b] = (root, third(theory.CHORD_INTERVALS[ctype]))
        out += beats
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/known_answers.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--songs", type=int, default=120)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--via", choices=["layout", "score"], default="layout",
                    help="layout: the readers on the generator's own grid and channel roles (the counts' path); "
                         "score: the whole path a game goes through, the beat reader finding the grid")
    a = ap.parse_args(argv)
    beat_kinds = Counter(); bar_place = Counter()
    key_kinds = Counter(); key_by_scale = defaultdict(Counter); scale_hits = Counter(); key_by_move = defaultdict(Counter)
    chord_beats = Counter(); change_hits = Counter(); form_hits = Counter(); parts = Counter(); drum_hits = Counter()
    scales, keys = Counter(), Counter()
    misses = defaultdict(list)
    for i in range(a.songs):
        seed = a.seed + i
        song = compose_song(seed=seed, scale_pref=FAMILIES[i % 3], song_form=FORMS[i % 5], keys="home" if i % 4 == 3 else "moving",
                            harmony_mode=("stabs", "sustain", "rhythmic")[i % 3], bass_weight=("heavy", "medium", "light")[(i // 3) % 3])
        info = song["info"]
        scales[info["scale"]] += 1; keys[info["key"]] += 1
        if a.via == "score":
            r = read_via_score(song)
            if r.grid is None:
                beat_kinds["free time"] += 1
                continue
            like, grid, rl, chords, form = r.song, r.grid, r.roles, r.chords, r.form
            tonic, scale_name, _ = r.scale
            # the beat: the tempo against the generator's (its half and double allowed, as the tap rounds did),
            # and the planned bar lines against the read ones
            bpm = info["tempo"]; ratio = grid.bpm / bpm
            level = next((k for k in (1.0, 2.0, 0.5, 3.0, 1 / 3, 1.5, 2 / 3, 4 / 3, 0.75, 4.0, 0.25) if abs(ratio - k) <= 0.03 * k), None)
            beat_kinds[{1.0: "same", 2.0: "double", 0.5: "half", None: "other"}.get(level, "compound")] += 1
            beat_seconds = 60 / bpm
            bars = list(grid.bar_times)
            for k in range(1, int(like.seconds / (4 * beat_seconds))):
                t = k * 4 * beat_seconds
                i = max(0, min(len(bars) - 2, __import__("bisect").bisect_right(bars, t) - 1))
                if bars[i] <= t < bars[i + 1]:
                    f = (t - bars[i]) / (bars[i + 1] - bars[i]); d = min(f, 1 - f)
                    bar_place["on the line" if d <= 0.12 else "a half bar off" if abs(f - 0.5) <= 0.12 else "elsewhere"] += 1
            in_beats = grid.beats                                   # seconds -> read beats
        else:
            like, grid, rl, (tonic, scale_name, _), chords, form = read(song)
            in_beats = lambda t: t * info["tempo"] / 60            # the generator's own beats
        mode = "major" if scale_name in harmony.MAJOR_MODES else "minor"
        # the key
        t_tonic = theory.NOTE_NAMES.index(info["key"]); t_mode = "minor" if info["scale"] in against.MINOR else "major"
        scale_hits["songs"] += 1; scale_hits["scale and tonic right"] += (tonic, scale_name) == (t_tonic, info["scale"])
        scale_hits["scale right"] += scale_name == info["scale"]
        if (tonic, mode) == (t_tonic, t_mode):
            kind = "right"
        else:
            parent = (t_tonic - PARENT.get(info["scale"], 0)) % 12
            relative = {(parent, "major"), ((parent + 9) % 12, "minor")}
            kind = "parent or relative" if (tonic, mode) in relative else "tonic right, mode wrong" if tonic == t_tonic else "other"
        key_kinds[kind] += 1; key_by_scale[info["scale"]][kind] += 1
        moves = info.get("chorus_modulated") or any(v[0] for v in info.get("key_plan", {}).values())
        key_by_move["modulating" if moves else "one key"][kind] += 1
        if kind != "right":
            misses["key"].append(f"seed {seed} {info['key']} {info['scale']} read {theory.NOTE_NAMES[tonic]} {scale_name} ({kind})")
        # the chords, beat by beat
        truth = truth_chords(song)
        beat_seconds = 60 / info["tempo"]
        starts = [c.start for c in chords]
        def read_chord(beat_of_plan: int):
            rb = in_beats((beat_of_plan + 0.5) * beat_seconds)
            i = __import__("bisect").bisect_right(starts, rb) - 1
            return chords[i] if 0 <= i < len(chords) and chords[i].start <= rb < chords[i].end else None
        for b, t in enumerate(truth):
            if t is None:
                continue
            c = read_chord(b)
            chord_beats["beats"] += 1
            if c is None or c.root is None:
                chord_beats["no chord read"] += 1
            elif c.root == t[0]:
                chord_beats["root right"] += 1
                chord_beats["root and family right"] += third(harmony.SHAPES[c.shape]) == t[1]
            else:
                chord_beats["root wrong"] += 1
        t_changes = [in_beats(b * beat_seconds) for b in range(1, len(truth)) if truth[b] and truth[b - 1] and truth[b][0] != truth[b - 1][0]]
        r_changes = []
        prev = None
        for c in chords:
            if c.root is not None:
                if prev is not None and c.root != prev:
                    r_changes.append(c.start)
                prev = c.root
        change_hits["planned"] += len(t_changes); change_hits["read"] += len(r_changes)
        change_hits["planned found"] += sum(1 for b in t_changes if any(abs(r - b) <= 1 for r in r_changes))
        change_hits["read planned"] += sum(1 for r in r_changes if any(abs(r - b) <= 1 for b in t_changes))
        # the form: section starts in bars
        per_pattern_bars = song["info"]["plan"]["rows_per_pattern"] // (song["info"]["plan"]["rows_per_beat"] * 4)
        t_starts = [in_beats(first * per_pattern_bars * 4 * beat_seconds) / 4 for name, first, n in song["info"]["plan"]["sections"] if first > 0]
        r_starts = [p.bar for p in form.parts if p.bar > 0]
        if a.via == "score":                                        # the read bars, in read beats over the read bar
            bar_beats = [grid.beats(t) for t in grid.bar_times]
            r_starts = [bar_beats[p.bar] / 4 for p in form.parts if 0 < p.bar < len(bar_beats)]
        form_hits["planned"] += len(t_starts); form_hits["read"] += len(r_starts)
        form_hits["planned found"] += sum(1 for b in t_starts if any(abs(r - b) <= 1 for r in r_starts))
        form_hits["read planned"] += sum(1 for r in r_starts if any(abs(r - b) <= 1 for b in t_starts))
        # the parts
        role_of = {x.voice: x.role for x in rl}
        mel = song["info"]["plan"]["melody_channel"]
        parts["songs"] += 1
        parts["melody channel read as melody"] += role_of.get(mel) == R.MELODY
        parts["another channel read as melody"] += any(r == R.MELODY and v != mel for v, r in role_of.items())
        parts["bass channel read as bass"] += role_of.get(CHANNEL_ROLES.index("bass")) == R.BASS
        drum_ch = [int(k) for k in song["info"]["plan"]["drum_channels"]]
        played_drums = [v for v in drum_ch if v in role_of]
        parts["drum channels"] += len(played_drums)
        parts["drum channels read as drums"] += sum(1 for v in played_drums if role_of[v] == R.DRUMS)
        if role_of.get(mel) != R.MELODY:
            misses["melody"].append(f"seed {seed}: channel {mel} read as {role_of.get(mel)}, melody read in {[v for v, r in role_of.items() if r == R.MELODY]}")
        # the drums: the kit's presets by their sound
        for preset, piece in against.kit(song).items():
            if preset in drum_hits_seen:
                continue
            drum_hits_seen.add(preset)
            got = drums_mod.name(drums_mod.of_preset(preset))
            drum_hits["presets"] += 1; drum_hits["right"] += got == piece
            if got != piece:
                misses["drums"].append(f"{preset} ({piece}) named {got}")
    n = sum(key_kinds.values())
    print(f"{n} songs, seeds {a.seed} to {a.seed + a.songs - 1}, read via the {a.via}; scales {dict(scales)}; keys {len(keys)} of 12")
    if a.via == "score":
        t = sum(beat_kinds.values()); bp = sum(bar_place.values())
        print(f"\nthe beat: tempo " + ", ".join(f"{k} {v} ({100 * v / t:.0f} %)" for k, v in beat_kinds.most_common())
              + f"; the planned bar lines {bp}: " + ", ".join(f"{k} {v} ({100 * v / max(1, bp):.0f} %)" for k, v in bar_place.most_common()))
    print(f"\nthe key (tonic and major/minor): " + ", ".join(f"{k} {v} ({100 * v / n:.0f} %)" for k, v in key_kinds.most_common()))
    print(f"the scale by name: tonic and scale right in {scale_hits['scale and tonic right']} ({100 * scale_hits['scale and tonic right'] / n:.0f} %), the scale alone right in {scale_hits['scale right']} ({100 * scale_hits['scale right'] / n:.0f} %)")
    for mv, c in sorted(key_by_move.items()):
        t = sum(c.values()); print(f"    {mv:17s} {t:3d}: right {100 * c['right'] / t:3.0f} %, parent or relative {100 * c['parent or relative'] / t:3.0f} %, other {100 * c['other'] / t:3.0f} %")
    for sc, c in sorted(key_by_scale.items()):
        t = sum(c.values()); print(f"    {sc:17s} {t:3d}: right {100 * c['right'] / t:3.0f} %, parent or relative {100 * c['parent or relative'] / t:3.0f} %, mode wrong {100 * c['tonic right, mode wrong'] / t:3.0f} %, other {100 * c['other'] / t:3.0f} %")
    cb = chord_beats
    print(f"\nthe chords, beat by beat ({cb['beats']} beats): root right {100 * cb['root right'] / cb['beats']:.0f} %, root and family right {100 * cb['root and family right'] / cb['beats']:.0f} %, root wrong {100 * cb['root wrong'] / cb['beats']:.0f} %, no chord read {100 * cb['no chord read'] / cb['beats']:.0f} %")
    ch = change_hits
    print(f"the chord changes: planned {ch['planned']}, read {ch['read']}; recall {100 * ch['planned found'] / max(1, ch['planned']):.0f} %, precision {100 * ch['read planned'] / max(1, ch['read']):.0f} % (within a beat)")
    fh = form_hits
    print(f"\nthe form: section starts planned {fh['planned']}, parts read {fh['read']}; recall {100 * fh['planned found'] / max(1, fh['planned']):.0f} %, precision {100 * fh['read planned'] / max(1, fh['read']):.0f} % (within a bar)")
    p = parts
    print(f"\nthe parts: melody channel read as the melody in {p['melody channel read as melody']} of {p['songs']} songs ({100 * p['melody channel read as melody'] / p['songs']:.0f} %), another channel as the melody in {p['another channel read as melody']}; "
          f"bass right in {p['bass channel read as bass']}; drum channels read as drums {p['drum channels read as drums']} of {p['drum channels']}")
    d = drum_hits
    print(f"\nthe drums: {d['right']} of {d['presets']} kit presets named as their slot")
    for kind, ms in misses.items():
        print(f"\nmisses, {kind} ({len(ms)}):")
        for m in ms[:12]:
            print("   ", m)
        if len(ms) > 12:
            print(f"    ... {len(ms) - 12} more")
    return 0


drum_hits_seen: set = set()

if __name__ == "__main__":
    sys.exit(main())
