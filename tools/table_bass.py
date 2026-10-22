"""A song's bass replaced by one written from the bass table (phase 3 of docs/IDIOM.md, the acceptance by ear):
the table fitted on every other song in the readings, the figures drawn bar by bar for the song's own chords,
played on the song's own bass sample in its own register, the rest of the song as decoded.

    python tools/table_bass.py FILE.spc --db READINGS.db -o OUT.it [--seed 1] [--seconds 60] [--title T] [--figures OUT.json]
                               [--stems DIR]

The bass written for is the bass LINE: of the voices the readers call bass, the one with the longest notes. A
second bass voice is one of three things beside it (measured over the readings, docs/idiom/phase-3-tables.md):
DOUBLING it (sounding at the same events: it then plays what the written line plays, at its own pitch offset,
on its own sample), ALTERNATING with it (the voices take turns so a note can ring past the next strike: the pair
is one part, the written line is read from both and its notes ring as the pair's do, each note going to the
voice that is free), or APART (a second part in the bass register with a rhythm of its own: left as it is, the
arrangement table's question, and the known limitation here).

Prints the figures drawn and what the readers make of the original and the written song. --stems: three more
modules beside, for a page that toggles the voice while the song plays: the rest of the song without the bass,
the bass voices written for, as the song plays them and as written (NAME rest.it, NAME bass original.it,
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

NEAR = 0.06                           # beats: onsets this close are one event
DOUBLING = 0.6                        # the share of the pair's events both voices sound at, for the second to double the first
ALTERNATING = 0.6                     # the share of single-voice events that change voice, for the pair to alternate
NOT_BOTH = 0.3                        # an alternating pair sounds together in under this share of its events

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


def relation(line, other) -> tuple:
    """What a second bass voice does beside the line (the module): ("doubling", semitones above the line),
    ("alternating",) or ("apart",)."""
    onsets = sorted([(n[0], 0, n) for n in line] + [(n[0], 1, n) for n in other])
    events = []
    for t, who, n in onsets:
        if events and t - events[-1][0] < NEAR:
            events[-1][1][who] = n
        else:
            events.append((t, {who: n}))
    both = sum(1 for _, d in events if len(d) == 2) / max(1, len(events))
    singles = [next(iter(d)) for _, d in events if len(d) == 1]
    alternation = sum(1 for a, b in zip(singles, singles[1:]) if a != b) / max(1, len(singles) - 1)
    if both >= DOUBLING:
        return ("doubling", round(statistics.median([d[1][2] - d[0][2] for _, d in events if len(d) == 2])))
    if alternation >= ALTERNATING and both < NOT_BOTH:
        return ("alternating",)
    return ("apart",)


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
    kinds = {t: relation(by_voice[v], by_voice[t]) for t in by_voice if t != v}
    partners = [t for t, k in kinds.items() if k[0] == "alternating"]
    doublings = [t for t, k in kinds.items() if k[0] == "doubling"]
    part = sorted(n for t in [v] + partners for n in by_voice[t])          # the line: one part across an alternating pair
    song.notes["bass"] = [(n[0], n[1], n[2], keys.get(int(n[5]), "noise")) for n in part if n[0] < end]
    print(f"{title} ({game}): bass voices {sorted(by_voice)}; the line on {v} (notes {length_of[v]:.2f} beats)"
          + "".join(f"; voice {t} {k[0]}" + (f" {k[1]:+d} semitones" if k[0] == "doubling" else "") for t, k in kinds.items()))
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
    # the written line onto the song's voices: the line voice, an alternating partner when the line is still ringing,
    # a doubling voice at every note; an apart voice is left as it is
    pair = [v] + partners
    settings = {t: settings_of([n for n in original.notes if n.voice == t], events) for t in pair + doublings}
    pair = [t for t in pair if settings[t] is not None]
    doublings = [t for t in doublings if settings[t] is not None]
    ring = statistics.median([n[1] for n in part if not math.isnan(n[1])]) if partners else None   # beats a note of the pair rings
    free = {t: -1.0 for t in pair}
    new = []
    for start_b, end_b, midi in notes:
        start = seconds_at(beats, start_b)
        if start >= original.seconds:
            continue
        end = min(seconds_at(beats, max(end_b, start_b + ring) if ring else end_b), original.seconds)
        idle = [t for t in pair if free[t] <= start + 0.001]
        voice = v if v in idle else (idle[0] if idle else min(pair, key=lambda t: free[t]))
        i = bisect.bisect_left(starts, start)
        near = min((mine[j] for j in (i - 1, i) if 0 <= j < len(mine)), key=lambda n: abs(n.start - start), default=None)
        at = near.volume if near is not None and abs(near.start - start) < 4.0 else None
        new.append(note_like(voice, start, end, midi, *settings[voice], at if voice == v else None))
        free[voice] = end
        for t in doublings:
            new.append(note_like(t, start, end, midi + kinds[t][1], *settings[t]))
    replaced = set(pair) | set(doublings)
    if partners or doublings:
        print(f"  written onto voices {sorted(replaced)}: {len(new)} notes" + (f", ringing {ring:.2f} beats" if ring else ""))
    kept = [n for n in original.notes if n.voice not in replaced]
    swapped = convert.Score(kept + new, original.seconds, original.voices, original.master, original.fade,
                            (a.title or f"{title} [table bass]")[:25], original.game, original.artist, original.row_hz,
                            original.tempo, original.tick_hz, original.aligned, original.on_ticks, original.snap,
                            dict(original.pcm_of), dict(original.key_of),
                            message=[f"{title}: the bass written from the bass table (phase 3 of docs/IDIOM.md)",
                                     f"the table fitted on every other song; seed {a.seed}; the rest as decoded"])
    info = convert.render(swapped, a.out)["info"]
    print(f"{a.out}: {info['notes']} notes, {info['channels']} channels; bass voices {sorted(replaced)} written, {len(new)} notes, usual volume {volume}")
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
