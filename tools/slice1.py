"""Phase 4, slice 1 (docs/idiom/phase-4-writing.md): the old generator's songs with the bass and the drums written
from a format 2 pack's tables, the old parts replaced.

    python tools/slice1.py PACK.json --seeds 1-8 -o OUT [--db READINGS] [--seconds 60] [--stems]

For each seed: the song composed with the pack (compose_song), read as a game's song (harness.load_generated),
the bass and the drums written from the pack's tables (harness.write_bass / write_drums with the pack's models),
rendered beside the old song (OUT/seed-N old.it, OUT/seed-N new.it; --stems: the page's modules too). With --db
(the games' readings), the measures: the old and the new bass and drum bars scored by mixtures fitted on every
game (a held-out song's number, to set beside the record's), and the spread (distinct figures a song, the
ostinato share) against the pack's game. A manifest (OUT/slice1.json) holds the seeds, the logs and the numbers.
"""
import argparse
import json
import os
import random
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from bitcomposer.composer import compose_song                                    # noqa: E402
from bitcomposer.packs import PACKS, packfile                                    # noqa: E402
from bitcomposer.spc import convert                                              # noqa: E402
from bitcomposer.translate import harness, packtables, reading, rhythm, store, tables, writer   # noqa: E402
from bitcomposer.translate import roles as R                                     # noqa: E402


def seeds_of(text: str) -> list[int]:
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def song_units(score: convert.Score, title: str, game: str) -> tuple:
    """A score read as a song: its bass and drum units, for the measures."""
    r = reading.of_score(score, game=game, title=title)
    if r.grid is None:
        return [], {}
    r.file, r.folder = f"{title}.measured", game
    db = store.connect(":memory:")
    store.keep(db, r)
    songs, _ = rhythm.load(db)
    if not songs:
        return [], {}
    s = songs[0]
    groups = {letters: rhythm.drum_group_units([s], letters) for letters in rhythm.DRUM_GROUPS}
    return rhythm.bass_units([s]), {k: v for k, v in groups.items() if any(u.outcome != "-" for u in v)}


SPAN = 32                            # bars: the spread's distinct figures are counted over the first SPAN bars a song
MIN_SONGS = 12                       # songs a game needs for its own table in the nearest-game test


def spread(units) -> tuple[float, float, float]:
    """Distinct figures a song over its first SPAN bars (songs differ in length), the ostinato share (a bar
    repeating the one before), and the mean bars a song, over the units' songs."""
    by_song = {}
    for u in units:
        by_song.setdefault(u.song, []).append(u.outcome)
    if not by_song:
        return 0.0, 0.0, 0.0
    distinct = statistics.mean(len(set(v[:SPAN])) for v in by_song.values())
    ostinato = statistics.mean(sum(1 for a, b in zip(v, v[1:]) if a == b) / max(1, len(v) - 1) for v in by_song.values())
    return distinct, ostinato, statistics.mean(len(v) for v in by_song.values())


def nearest_games(models_by_game: dict, units) -> list[tuple[str, float]]:
    """Each game's table scoring the units, best first."""
    out = [(g, m.score(units)) for g, m in models_by_game.items()]
    return sorted(out, key=lambda x: -x[1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pack", help="the format 2 pack file")
    ap.add_argument("--seeds", default="1-8")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--db", help="the games' readings, for the measures")
    ap.add_argument("--seconds", type=float, default=None, help="cut the song to this (default: the whole song)")
    ap.add_argument("--stems", action="store_true", help="render the page's modules too")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    name = packfile.load_pack_file(args.pack)
    t = PACKS[name].get(packfile.TABLES)
    if not t:
        print(f"{args.pack}: no tables (not a format 2 pack)", file=sys.stderr)
        return 1
    models = packtables.read(t)
    game = t["source"]["game"]
    manifest = {"pack": name, "game": game, "songs": []}
    old_bass, old_drums, new_bass, new_drums = [], {}, [], {}
    for seed in seeds_of(args.seeds):
        title = f"seed {seed}"
        song = compose_song(seed=seed, pack=name)
        ctx = harness.load_generated(song, title, game, models, seconds=args.seconds)
        if ctx is None:
            print(f"{title}: the readers found no beat or no parts; skipped", file=sys.stderr)
            manifest["songs"].append({"seed": seed, "skipped": True})
            continue
        parts = [w for w in (harness.write_bass(ctx, seed), harness.write_drums(ctx, seed)) if w is not None]
        old_path = os.path.join(args.out, f"{title} old.it")
        new_path = os.path.join(args.out, f"{title} new.it")
        convert.render(ctx.original, old_path)
        new = harness.score_with(ctx, parts, f"{title} new", [f"{title}: the bass and the drums from {name}'s tables"])
        convert.render(new, new_path)
        entry = {"seed": seed, "title": title, "parts": {w.part: {"bars": len(w.figures), "notes": len(w.notes), "log": w.log,
                                                                  "figures": w.figures, "own": w.own} for w in parts},
                 "key": ctx.key, "bars": len(ctx.song.bars), "bpm": ctx.song.bpm}
        if args.stems:
            entry["stems"] = harness.stems(ctx, parts, os.path.join(args.out, "stems"))
        if args.db:
            ob, od = song_units(ctx.original, title, game)
            nb, nd = song_units(new, title, game)
            old_bass += ob; new_bass += nb
            for k, v in od.items():
                old_drums.setdefault(k, []).extend(v)
            for k, v in nd.items():
                new_drums.setdefault(k, []).extend(v)
        manifest["songs"].append(entry)
        print(f"{title}: " + "; ".join(f"{w.part} {len(w.figures)} bars, {len(w.notes)} notes" for w in parts), file=sys.stderr)
    if args.db:
        db = store.connect(args.db)
        songs, _ = rhythm.load(db)
        others = [s for s in songs if s.game != game]                  # the other games' idiom judges all three alike
        bass_all = rhythm.bass_units(songs)
        bass_model = writer.fit([u for u in bass_all if u.game != game])
        real_bass = [u for u in bass_all if u.game == game]
        rows = [("bass", bass_model, old_bass, new_bass, real_bass)]
        for letters in rhythm.DRUM_GROUPS:
            if letters not in new_drums and letters not in old_drums:
                continue
            units = rhythm.drum_group_units(songs, letters)
            rows.append(("drums-" + "".join(letters), writer.fit([u for u in units if u.game != game], name="drums-" + "".join(letters)),
                         old_drums.get(letters, []), new_drums.get(letters, []), [u for u in units if u.game == game]))
        print(f"\nmeasures against the other {len(others)} songs' tables ({game} out; bits a bar as a held-out song; "
              f"spread: distinct figures in the first {SPAN} bars / ostinato share / bars a song):")
        print(f"{'part':10} {'old bits':>9} {'new bits':>9} {'old spread':>18} {'new spread':>18} {game[:20] + ' real':>32}")
        manifest["measures"] = {}
        for part, model, old, new, real in rows:
            ob = model.score(old) if old else float("nan")
            nb = model.score(new) if new else float("nan")
            rb = statistics.mean(model.score([u for u in real if u.song == sid]) for sid in {u.song for u in real}) if real else float("nan")
            so, sn, sr = spread(old), spread(new), spread(real)
            print(f"{part:10} {ob:9.2f} {nb:9.2f} {so[0]:6.1f} / {so[1]:4.2f} / {so[2]:3.0f} {sn[0]:6.1f} / {sn[1]:4.2f} / {sn[2]:3.0f}   {rb:7.2f} bits, {sr[0]:5.1f} / {sr[1]:4.2f} / {sr[2]:3.0f}")
            manifest["measures"][part] = {"old_bits": ob, "new_bits": nb, "real_bits_in_table": rb, "old_spread": so, "new_spread": sn, "real_spread": sr}
        # the nearest game: each game's own bass and kick-snare tables score each song; where does the pack's game rank?
        games = Counter(u.game for u in bass_all)
        by_game = {g: writer.fit([u for u in bass_all if u.game == g]) for g, n in games.items() if n and len({u.song for u in bass_all if u.game == g}) >= MIN_SONGS}
        print(f"\nthe nearest game by its own bass table ({len(by_game)} games with {MIN_SONGS} songs or more):")
        ranks = {"old": [], "new": []}
        for label, pool in (("old", old_bass), ("new", new_bass)):
            for sid in sorted({u.song for u in pool}):
                order = nearest_games(by_game, [u for u in pool if u.song == sid])
                rank = next((i for i, (g, _) in enumerate(order) if g == game), None)
                ranks[label].append(rank)
                print(f"  {label} {sid[:12]:12}: {order[0][0][:22]} ({order[0][1]:.2f}); {game[:16]} rank {rank + 1 if rank is not None else '-'} ({dict(order).get(game, float('nan')):.2f})")
        for label in ("old", "new"):
            rs = [r for r in ranks[label] if r is not None]
            print(f"  {label}: {game} nearest in {sum(1 for r in rs if r == 0)} of {len(rs)}; median rank {statistics.median(rs) + 1 if rs else '-'} of {len(by_game)}")
        manifest["nearest"] = ranks
    with open(os.path.join(args.out, "slice1.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
