"""A song's bass replaced by one written from the bass table (phase 3 of docs/IDIOM.md, the acceptance by ear):
the table fitted on every other song in the readings, the figures drawn bar by bar for the song's own chords,
played on the song's own bass sample in its own register, the rest of the song as decoded.

    python tools/table_bass.py FILE.spc --db READINGS.db -o OUT.it [--seed 1] [--seconds 60] [--title T] [--figures OUT.json]
                               [--stems DIR]

The bass written for is the bass LINE: of the voices the readers call bass, the one with the longest notes, and
the manner is read from that voice alone. A song may layer its bass (Locke: a plucked line with a sustained tone
blipping at each of its attacks and a sixteenth after); a bass voice whose notes are shorter than TICK beats is
such a layer. Its notes that follow the line's attacks (the device: the offsets after an attack that DEVICE of
the doubled attacks have) are rebuilt on the written line, the same offsets, pitch relation and sample, a note
at the attack itself lasting as long as the line's note it doubles (Locke's second voice holds the walking
line's notes a whole beat, and blips only in its own intro pattern) and a note after it as long as the layer's
own are; its other notes, a rhythm of its own where the line rests, stay as they are.

Prints the figures drawn and what the readers make of the original and the written song. --stems: three more
modules beside, for a page that toggles the voice while the song plays: the rest of the song without the bass,
the bass (line and layers) as the song plays it, and as written (NAME rest.it, NAME bass original.it,
NAME bass written.it).
"""
import argparse
import bisect
import json
import math
import os
import statistics
import sys
from array import array
from collections import Counter

TICK = 0.3                            # beats: a bass voice whose notes are shorter than this doubles the line's attacks
DEVICE = 0.5                          # the share of the doubled attacks an offset must follow to be part of the device
NEAR = 0.06                           # beats: a layer note this close to a line attack doubles it

from bitcomposer import spc
from bitcomposer.spc import convert
from bitcomposer.translate import harmony, reading, rhythm, store, writer
import random


def seconds_at(beats: array, b: float) -> float:
    """A time in beats back to seconds on the beat times (vocab._beats_at's inverse)."""
    if len(beats) < 2:
        return b
    i = min(max(int(math.floor(b)), 0), len(beats) - 2)
    return beats[i] + (b - i) * (beats[i + 1] - beats[i])


def settings_of(mine, events):
    """A voice's usual settings (sample, brr, volume, envelope, echo: its most common) and a reference note with
    a known midi on that sample: (usual, like, pitch_ref, midi_ref); None when the voice has no such note."""
    usual = Counter((n.sample, n.brr, n.volume, n.adsr, n.gain, n.echo, n.echo_delay, n.echo_volume, n.echo_feedback,
                     n.echo_filter, n.echo_writes) for n in mine).most_common(1)
    for n in mine:
        p = events.get((n.voice, round(n.start, 4)))
        if p is not None and usual and (n.sample, n.brr) == usual[0][0][:2]:
            return usual[0][0], n, n.pitch, p.midi
    return None


def note_like(voice, start, end, midi, usual, like, pitch_ref, midi_ref, volume=None):
    """A note on the voice in its usual settings at this midi (volume: the usual's unless given)."""
    _, _, usual_volume, adsr, gain, echo, e_delay, e_volume, e_feedback, e_filter, e_writes = usual
    pitch = max(1, min(0x3FFF, round(pitch_ref * 2 ** ((midi - midi_ref) / 12))))
    return convert.notes_mod.Note(voice, start, like.sample, pitch, volume or usual_volume, adsr, gain, echo, False,
                                  brr=like.brr, echo_delay=e_delay, echo_volume=e_volume, echo_feedback=e_feedback,
                                  echo_filter=e_filter, echo_writes=e_writes, end=end)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/table_bass.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("spc")
    ap.add_argument("--db", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--title", help="the module's title (25 characters show in a player)")
    ap.add_argument("--figures", help="write the figures drawn and the song's own beside, as JSON")
    ap.add_argument("--stems", help="write the rest, the original bass and the written bass as modules of their own here")
    a = ap.parse_args(argv)
    db = store.connect(a.db)
    row = db.execute("SELECT id, game, title, key_tonic, key_mode FROM songs WHERE file = ?", (os.path.basename(a.spc),)).fetchone()
    if not row:
        print(f"{a.spc}: not in the readings", file=sys.stderr)
        return 1
    sid, game, title, tonic, mode = row
    songs, _ = rhythm.load(db)
    song = next((s for s in songs if s.sid == sid), None)
    if song is None or rhythm.R.BASS not in song.notes:
        print(f"{title}: not counted, or no bass read", file=sys.stderr)
        return 1
    # the bass line: of the voices read as bass, the one with the longest notes; its notes alone are the song's bass
    # for the writer (the manner, the habit, the spans, the rests, the volume)
    keys = {idx: key for idx, key in db.execute("SELECT idx, key FROM samples WHERE song = ?", (sid,))}
    by_voice = {}
    for voice, blob in db.execute("SELECT voice, notes FROM voices WHERE song = ? AND role = 'bass'", (sid,)):
        by_voice[voice] = [n for n in store.unpack(blob) if n[3] > 0 and not math.isnan(n[2])]
    length_of = {voice: statistics.median([n[1] for n in ns if not math.isnan(n[1])] or [0.0]) for voice, ns in by_voice.items()}
    v = max(by_voice, key=lambda voice: (length_of[voice], len(by_voice[voice])))
    end = song.bars[-1][1] if song.bars else math.inf
    song.notes["bass"] = [(n[0], n[1], n[2], keys.get(int(n[5]), "noise")) for n in by_voice[v] if n[0] < end]
    layers = [voice for voice in by_voice if voice != v and length_of[voice] < TICK]
    print(f"{title} ({game}): bass voices {sorted(by_voice)} (notes {length_of[v]:.2f} beats long on {v}, the line"
          + (f"; layers {layers}" if layers else "") + ")")
    units = rhythm.bass_units(songs)
    table = writer.fit([u for u in units if u.song != sid])
    own = [u.outcome for u in rhythm.bass_units([song])]
    notes, figures = writer.bass(song, table, random.Random(a.seed), key=(tonic, mode) if tonic is not None else None)
    print(f"  habit {rhythm.bass_units([song])[0].values['habit']}, {len(figures)} bars written, {len(notes)} notes")
    for i, (f, o) in enumerate(zip(figures, own)):
        print(f"  bar {i:3d}  written {f:40.40}  own {o}")
    # the song as decoded, the line's notes swapped for the written ones, a layer rebuilt on them
    snap = spc.read(a.spc)
    original = convert.score_of(snap, a.seconds, fade=0.0)
    r = reading.of_score(original)
    # the voice's usual settings (its most common sample, volume, envelope and echo), not its first note's:
    # a song fading its bass in starts near silence (Terra's first bass note plays at 6 of 127, panned left)
    events = {(p.voice, round(p.start, 4)): p for p in r.song.notes if p.midi is not None}
    mine = [n for n in original.notes if n.voice == v]
    found = settings_of(mine, events)
    if found is None:
        print("no reference note on the bass voice", file=sys.stderr)
        return 1
    usual, like, pitch_ref, midi_ref = found
    volume = usual[2]
    beats = array("d")
    beats.frombytes(db.execute("SELECT beats FROM beats WHERE song = ?", (sid,)).fetchone()[0])
    starts = [n.start for n in mine]                      # the song's own line, for its volume at each moment (a fade-in kept)
    new = []
    for start_b, end_b, midi in notes:
        start, end = seconds_at(beats, start_b), seconds_at(beats, end_b)
        if start >= original.seconds:
            continue
        i = bisect.bisect_left(starts, start)
        near = min((mine[j] for j in (i - 1, i) if 0 <= j < len(mine)), key=lambda n: abs(n.start - start), default=None)
        at = near.volume if near is not None and abs(near.start - start) < 4.0 else volume
        new.append(note_like(v, start, min(end, original.seconds), midi, usual, like, pitch_ref, midi_ref, at))
    replaced = {v}
    line_starts = sorted(n[0] for n in by_voice[v])
    for t in layers:
        # the device: which of the line's attacks the layer doubles (a note within NEAR of it), and the offsets after
        # a doubled attack its notes fall on; a layer note under neither is the layer's own and stays
        doubled, offsets, diffs, following = set(), Counter(), [], set()
        for n in by_voice[t]:
            i = bisect.bisect_right(line_starts, n[0] + NEAR) - 1
            if i < 0:
                continue
            off = n[0] - line_starts[i]
            if off < NEAR:
                doubled.add(i)
                m = next((x[2] for x in by_voice[v] if abs(x[0] - line_starts[i]) < 0.03), None)
                if m is not None:
                    diffs.append(n[2] - m)
        for n in by_voice[t]:
            i = bisect.bisect_right(line_starts, n[0] + NEAR) - 1
            if i >= 0 and i in doubled and n[0] - line_starts[i] < 1.0:
                offsets[round((n[0] - line_starts[i]) * 4) / 4] += 1
        device = sorted(off for off, c in offsets.items() if c >= DEVICE * len(doubled)) if doubled else []
        found_t = settings_of([n for n in original.notes if n.voice == t], events)
        if not device or found_t is None:
            print(f"  layer voice {t}: doubles {len(doubled)} of the line's {len(line_starts)} attacks, no device read; left as it is")
            continue
        for n in by_voice[t]:                              # the layer's notes on the device: replaced below
            i = bisect.bisect_right(line_starts, n[0] + NEAR) - 1
            if i >= 0 and i in doubled and round((n[0] - line_starts[i]) * 4) / 4 in device and n[0] - line_starts[i] < 1.0:
                following.add(round(seconds_at(beats, n[0]), 3))
        usual_t, like_t, pitch_t, midi_t = found_t
        diff = round(statistics.median(diffs)) if diffs else 0
        held = length_of[t]
        ticks = []
        for start_b, end_b, midi in notes:
            for off in device:
                start = seconds_at(beats, start_b + off)
                until = seconds_at(beats, end_b if off < NEAR else start_b + off + held)   # at the attack: as long as the line's note
                if start < original.seconds:
                    ticks.append(note_like(t, start, min(until, original.seconds), midi + diff, usual_t, like_t, pitch_t, midi_t))
        own_layer = [n for n in original.notes if n.voice == t and round(n.start, 3) not in following]
        new += ticks + own_layer
        replaced.add(t)
        print(f"  layer voice {t}: doubles {len(doubled)} of the line's {len(line_starts)} attacks at offsets {device} beats, {diff:+d} semitones, "
              f"its own notes {held:.2f} beats; {len(ticks)} rebuilt on the written line, {len(own_layer)} of its own kept")
    kept = [n for n in original.notes if n.voice not in replaced]
    swapped = convert.Score(kept + new, original.seconds, original.voices, original.master, original.fade,
                            (a.title or f"{title} [table bass]")[:25], original.game, original.artist, original.row_hz,
                            original.tempo, original.tick_hz, original.aligned, original.on_ticks, original.snap,
                            dict(original.pcm_of), dict(original.key_of),
                            message=[f"{title}: the bass written from the bass table (phase 3 of docs/IDIOM.md)",
                                     f"the table fitted on every other song; seed {a.seed}; the rest as decoded"])
    info = convert.render(swapped, a.out)["info"]
    print(f"{a.out}: {info['notes']} notes, {info['channels']} channels; bass voices {sorted(replaced)}, {len(new)} written notes, usual volume {volume}")
    for label, sc in (("original", original), ("written", swapped)):
        rr = reading.of_score(sc)
        role = next((x.role for x in rr.roles if x.voice == v), "-")
        key = f"{harmony.NAMES[rr.key[0]]} {rr.key[1]}" if rr.key else "-"
        print(f"  {label:9s} voice {v} read as {role:14s} key {key:10s} tempo {rr.grid.bpm if rr.grid else 0:6.1f} chords {len(rr.chords)}")
    if a.figures:
        with open(a.figures, "w") as f:
            json.dump({"song": title, "game": game, "seed": a.seed, "written": figures, "own": own}, f, indent=1)
    if a.stems:
        os.makedirs(a.stems, exist_ok=True)
        for label, part in (("rest", kept), ("bass original", [n for n in original.notes if n.voice in replaced]), ("bass written", new)):
            stem = convert.Score(part, original.seconds, original.voices, original.master, original.fade,
                                 f"{title} {label}"[:25], original.game, original.artist, original.row_hz, original.tempo,
                                 original.tick_hz, original.aligned, original.on_ticks, original.snap,
                                 dict(original.pcm_of), dict(original.key_of), message=[f"{title}: {label} (a stem for the Substitution Check)"])
            path = os.path.join(a.stems, f"{title} {label}.it")
            convert.render(stem, path)
            print(f"  stem {path}: {len(part)} notes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
