"""One voice of a decoded song replaced by a generated one (phase 2 of docs/IDIOM.md, the substitution harness):
the rest as decoded, rendered through the same back end, read by the same readers.

    python tools/substitute.py FILE.spc --voice V [--take 0] [--seed 1] [--sound snes] [--seconds 60] -o OUT.it

--voice: the decoded voice (0 to 7) that is replaced; --take: the generated song's voice that replaces it
(0 the melody, 4 the bass, 6 the kick...). The generated voice keeps its own tempo and length (cut to the
decoded song's), its preset as its sample, and takes the decoded voice's echo setting. Prints what the readers
make of the original and the substituted song: the voice's role, the key, the chords.
"""
import argparse
import sys

from bitcomposer import spc
from bitcomposer import score as score_mod
from bitcomposer.composer import compose_song
from bitcomposer.spc import convert
from bitcomposer.translate import harmony, reading


def substitute(score: convert.Score, voice: int, generated: convert.Score, take: int) -> convert.Score:
    """The score with `voice` replaced by the generated score's `take` voice."""
    kept = [n for n in score.notes if n.voice != voice]
    like = next((n for n in score.notes if n.voice == voice), None)
    base = 0xF000                                  # addresses no snapshot's sample has, for the generated samples
    pcm_of, key_of = dict(score.pcm_of), dict(score.key_of)
    moved = {}
    for addr, s in generated.pcm_of.items():
        moved[addr] = (base + len(moved), 0)
        pcm_of[moved[addr]] = s
        key_of[moved[addr]] = generated.key_of.get(addr, f"generated {len(moved)}")
    new = []
    for n in generated.notes:
        if n.voice != take or n.start >= score.seconds:
            continue
        m = convert.notes_mod.Note(voice, n.start, n.sample, n.pitch, n.volume, n.adsr, n.gain,
                                   like.echo if like else False, False, brr=moved[n.brr],
                                   echo_delay=like.echo_delay if like else 0.0, echo_volume=like.echo_volume if like else (0.0, 0.0),
                                   echo_feedback=like.echo_feedback if like else 0.0,
                                   echo_filter=like.echo_filter if like else n.echo_filter, echo_writes=like.echo_writes if like else True,
                                   end=min(n.end, score.seconds) if n.end is not None else None,
                                   bends=list(n.bends), swells=list(n.swells))
        new.append(m)
    out = convert.Score(kept + new, score.seconds, score.voices, score.master, score.fade, score.title, score.game,
                        score.artist, score.row_hz, score.tempo, score.tick_hz, score.aligned, score.on_ticks, score.snap,
                        pcm_of, key_of,
                        message=[f"{score.title}: voice {voice} replaced by a generated {['melody', 'harmony', 'harmony', 'harmony', 'bass', 'arp', 'kick', 'snare', 'hat', 'tom', 'crash', 'open hat'][take] if take < 12 else take}",
                                 "the rest as decoded, through the same back end (phase 2 of docs/IDIOM.md)"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/substitute.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("spc"); ap.add_argument("--voice", type=int, required=True); ap.add_argument("--take", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--sound", default="snes"); ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    snap = spc.read(a.spc)
    original = convert.score_of(snap, a.seconds, fade=0.0)
    generated = score_mod.of_song(compose_song(seed=a.seed, sound=a.sound))
    swapped = substitute(original, a.voice, generated, a.take)
    info = convert.render(swapped, a.out)["info"]
    print(f"{a.out}: {info['notes']} notes, {info['repeats']} repeats, {info['channels']} channels")
    for label, sc in (("original", original), ("substituted", swapped)):
        r = reading.of_score(sc)
        role = next((x.role for x in r.roles if x.voice == a.voice), "-")
        key = f"{harmony.NAMES[r.key[0]]} {r.key[1]}" if r.key else "-"
        print(f"  {label:12s} voice {a.voice} read as {role:14s} key {key:10s} tempo {r.grid.bpm if r.grid else 0:6.1f} chords {len(r.chords)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
