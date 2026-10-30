"""
Command-line interface for bitcomposer.
"""

import argparse
import os
import sys
import time

from . import __version__
from .composer import compose_song, save_song, unique_path


def build_parser():
    parser = argparse.ArgumentParser(
        prog="bitcomposer",
        description="Procedural 16-bit chiptune music generator",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path (default: auto-generated name in current directory)",
    )
    parser.add_argument(
        "-d", "--output-dir",
        default=".",
        help="Output directory (used when -o is not specified)",
    )
    parser.add_argument(
        "--name",
        choices=["title", "timestamp"],
        default="title",
        help="How to name files when -o is not given: after the song's title "
             "(\"Haunted Orchard.it\", default) or bitcomposer_<timestamp>.it",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Text put before a title-named file's name, e.g. \"(auto) \" (the player's mark)",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help="Text appended to a title-named file before .it",
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible output",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        help="Number of songs to generate",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed info about generated songs",
    )
    parser.add_argument(
        "--tempo",
        choices=["slow", "medium", "fast", "random"],
        default="random",
        help="Tempo preference (default: random)",
    )
    parser.add_argument(
        "--energy",
        choices=["chill", "normal", "intense", "random"],
        default="random",
        help="Energy/density level (default: random)",
    )
    parser.add_argument(
        "--scale",
        choices=["minor", "major", "pentatonic", "random"],
        default="random",
        help="Scale preference (default: random)",
    )
    parser.add_argument(
        "--sound",
        choices=["chip", "snes", "genesis", "bit", "ffvi", "mana", "evermore", "megamanx", "random"],
        default="random",
        help="The sound in one word: a palette (chip, snes, genesis) or a style pack "
             "(ffvi, mana, evermore, megamanx). Overrides --style and --pack. "
             "random: drawn with the packs together weighing as much as plain snes (default)",
    )
    parser.add_argument(
        "--style",
        choices=["chip", "snes", "genesis", "random"],
        default="random",
        help="Sound palette: chip (square/triangle waves), snes (sampled strings, "
             "brass, plucks, gated drums), genesis (FM) (default: random)",
    )
    parser.add_argument(
        "--drum-density",
        choices=["sparse", "normal", "busy", "random"],
        default="random",
        help="Drum pattern density (default: random)",
    )
    parser.add_argument(
        "--no-fills",
        action="store_true",
        help="Disable drum fills at section transitions",
    )
    parser.add_argument(
        "--swing",
        choices=["off", "light", "heavy", "random"],
        default="random",
        help="Swing feel on hi-hats (default: random)",
    )
    parser.add_argument(
        "--melody",
        choices=["simple", "phrased", "random"],
        default="random",
        help="Melody style: simple (random walk) or phrased (motif-based) (default: random)",
    )
    parser.add_argument(
        "--harmony-voicing",
        choices=["thin", "full", "random"],
        default="random",
        help="Harmony voicing: thin (two voices) or full (three) (default: random)",
    )
    parser.add_argument(
        "--harmony-mode",
        choices=["stabs", "sustain", "rhythmic", "random"],
        default="random",
        help="Harmony style: stabs, sustain (pad), or rhythmic (default: random)",
    )
    parser.add_argument(
        "--bass-weight",
        choices=["heavy", "medium", "light", "random"],
        default="random",
        help="Bass weight: heavy (deep), medium (balanced), light (punchy/thin) (default: random)",
    )
    parser.add_argument(
        "--form",
        choices=["standard", "aaba", "rondo", "short", "linear", "random"],
        default="random",
        help="Song form (default: random)",
    )
    parser.add_argument(
        "--echo",
        choices=["on", "off", "random"],
        default="random",
        help="Delay echo on the lead, SNES style (default: random — 70%% of snes songs, never chip or genesis)",
    )
    parser.add_argument(
        "--echo-wet",
        choices=["light", "normal", "wet", "random"],
        default="random",
        help="How much of the lead, harmony and arp the echo carries (default: random — normal for now)",
    )
    parser.add_argument(
        "--echo-delay",
        choices=["eighth", "dotted", "quarter", "slap", "row", "random"],
        default="random",
        help="Beat fraction between echo repeats, slap (48 ms, under a row) or row (one row); default: random, weighted by tempo",
    )
    parser.add_argument(
        "--echo-stereo",
        choices=["bounce", "centre", "random"],
        default="random",
        help="bounce: repeats alternate sides; centre: repeats under their source, like the hardware",
    )
    parser.add_argument(
        "--pack",
        choices=["bit", "ffvi", "mana", "evermore", "megamanx", "none", "random"],
        default="random",
        help="Style pack: an instrument set with the habits of the scores it imitates (random: half of snes songs)",
    )
    parser.add_argument(
        "--pack-file",
        default=None, metavar="PACK.json",
        help="compose with a pack file: a pack as data, with its own voices as WAV files "
             "(docs/PACKS.md); overrides --pack and --sound",
    )
    parser.add_argument(
        "--lead-shift",
        type=int, default=None, metavar="SEMITONES",
        help="move the lead's window by this many semitones (negative lowers it); "
             "default: the sound's own setting",
    )
    parser.add_argument(
        "--keys",
        choices=["moving", "home"],
        default="moving",
        help="moving: choruses and bridges may change key (default); "
             "home: every section stays in the home key, for loops that must "
             "sit still or for A/B tests of other changes",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="render the song through the SNES back end: its voices as notes in time, "
             "the echo as the SNES chip's (phase 2 of docs/IDIOM.md; the chip and Genesis "
             "sounds are not changed by this)",
    )
    parser.add_argument(
        "--classic",
        action="store_true",
        help="compose with Classic, the 1.x generator, instead of writing from a vocabulary; the options above are its",
    )
    parser.add_argument(
        "--vocabulary",
        choices=_vocabulary_names() or ["default"],
        default="default",
        help="what the song is written from (docs/IDIOM.md, phase 6): 'default' (shipped; the README says where it was "
             "learned), 'library' (everything you have imported) or 'pack:NAME' (an imported game's own); on the sound set "
             "--pack names (bit, bitComposer's own and the default; ffvi, mana, evermore or megamanx, Classic's styled sets), the pack --pack-file names, or a pack vocabulary's own samples",
    )
    parser.add_argument(
        "--carry-theme",
        action=argparse.BooleanOptionalAction, default=None,
        help="the tune's phrases are drawn again until its theme comes back later in the song (the player's default; "
             "--no-carry-theme leaves it to the vocabulary's own rate)",
    )
    parser.add_argument(
        "--band-returns",
        action=argparse.BooleanOptionalAction, default=None,
        help="a theme never comes back with the tune alone: the chords, the bass or the accompaniment come with it "
             "(the player's default; --no-band-returns leaves it to the vocabulary)",
    )
    parser.add_argument(
        "--bare",
        action="store_true",
        help="the writer bare, with none of the player's performance (no theme asked for, the echo as the sound set's "
             "habit, no vibrato, the loop once): what the Song Checks and tools/whole.py write",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"bitcomposer {__version__}",
    )

    return parser


def _vocabulary_names() -> list:
    try:
        from .vocabularies import names as vocabulary_names
        return vocabulary_names()
    except OSError:
        return []


def compose_from_args(args, index: int = 0):
    """Compose one song the way the command line does and save it; returns
    the path written. The player calls this in-process with its own
    settings string parsed by build_parser, so the window's options and the
    command line's are one list."""
    seed = args.seed
    if seed is not None and args.count > 1:
        seed = seed + index
    if not getattr(args, "classic", False):
        return compose_written_from_args(args, seed, index)
    pack, sound = args.pack, args.sound
    if args.pack_file:
        from .packs.packfile import load_pack_file
        pack, sound = load_pack_file(args.pack_file), "random"
    song = compose_song(seed=seed,
                        tempo_pref=args.tempo, energy_pref=args.energy,
                        scale_pref=args.scale, style_pref=args.style,
                        drum_density=args.drum_density,
                        drum_fills=not args.no_fills,
                        drum_swing=args.swing,
                        melody_style=args.melody,
                        harmony_voicing=args.harmony_voicing,
                        harmony_mode=args.harmony_mode,
                        bass_weight=args.bass_weight,
                        song_form=args.form,
                        echo=args.echo, echo_wet=args.echo_wet,
                        echo_delay=args.echo_delay, echo_stereo=args.echo_stereo, keys=args.keys,
                        lead_shift=args.lead_shift,
                        pack=pack, sound=sound)
    os.makedirs(args.output_dir, exist_ok=True)
    if args.output and args.count == 1:
        filepath = args.output
    elif args.name == "title":
        # The file is the song: what the player shows is what the
        # folder shows.
        filepath = unique_path(args.output_dir, song["name"], args.suffix, prefix=args.prefix)
    else:
        timestamp = int(time.time())
        seed_str = f"_s{seed}" if seed is not None else ""
        filepath = os.path.join(args.output_dir, f"{args.prefix}bitcomposer_{timestamp}_{index}{seed_str}{args.suffix}.it")
    if getattr(args, "score", False):
        from . import score as score_mod
        from .spc import convert
        convert.render(score_mod.of_song(song), filepath)
    else:
        save_song(song, filepath)
    return filepath, song["info"]


def compose_written_from_args(args, seed, index: int = 0):
    """A song from a vocabulary (phase 6), saved as compose_from_args saves Classic's."""
    from .spc import convert
    from .written import compose_written
    from .performance import Performance
    out = compose_written(args.vocabulary, args.pack, seed, carry_theme=args.carry_theme, band_returns=args.band_returns,
                          pack_file=args.pack_file, performance=Performance.none() if args.bare else None)
    os.makedirs(args.output_dir, exist_ok=True)
    if args.output and args.count == 1:
        filepath = args.output
    elif args.name == "title":
        filepath = unique_path(args.output_dir, out["title"], args.suffix, prefix=args.prefix)
    else:
        filepath = os.path.join(args.output_dir, f"{args.prefix}bitcomposer_{int(time.time())}_{index}_s{out['seed']}{args.suffix}.it")
    convert.render(out["score"], filepath)
    return filepath, out["info"]


def main():
    args = build_parser().parse_args()

    for i in range(args.count):
        try:
            filepath, info = compose_from_args(args, i)
        except Exception as e:
            print(f"Error generating song: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        print(f"Generated: {filepath}")

        if args.verbose and "vocabulary" in info:
            print(f"  Title:       {info['title']}")
            print(f"  Written on the {info['sounds']} sounds, seed {info['seed']}" + ("" if info['vocabulary'] == "bitComposer" else f", from {info['vocabulary']}"))
            print(f"  Key:         {info['key']}")
            print(f"  Tempo:       {info['tempo']} BPM")
            print(f"  Form:        {info['form']} ({info['bars']} bars, {info['seconds']} s)")
            print(f"  Band:        {', '.join(info['band'])}")
            print()
        elif args.verbose:
            print(f"  Title:       {info['title']}")
            print(f"  Key:         {info['key']} {info['scale']}")
            print(f"  Tempo:       {info['tempo']} BPM "
                  f"(speed {info['speed']}, IT tempo {info['it_tempo']})")
            print(f"  Bass:        {info['bass_style']} ({info['bass_weight']})")
            f = info['arp_figures']
            print(f"  Arp figures: verse {f['verse']}, chorus {f['chorus']}, bridge {f['bridge']}")
            g = info['grooves']
            print(f"  Grooves:     verse {g['verse']}, chorus {g['chorus']}, bridge {g['bridge']}")
            print(f"  Density:     {info['melody_density']}")
            print(f"  Melody:      {info['melody_style']} ({info['melody_contour']})")
            print(f"  Harmony:     {info['harmony_voicing']} / {info['harmony_mode']}")
            print(f"  Style:       {info['style']}"
                  f"{' + echo' if info.get('echo') else ''}")
            print(f"  Chord moves: {info['half_pattern_changes']} half-pattern changes")
            kp = info['key_plan']
            if any(v[0] for v in kp.values()):
                print("  Keys:        " + ", ".join(f"{k} {'+' if v[0] > 0 else ''}{v[0]} ({v[1].replace('_', ' ')})" for k, v in kp.items() if v[0]))
            print(f"  Harm rhythm: {info['harmonic_rhythm']}")
            if info.get('chorus_alt_prog'):
                print("  Chorus prog: alternate")
            print(f"  Form:        {info['song_form']}")
            print(f"  Ending:      {info['ending_style']}")
            if info.get('alt_lead'):
                print(f"  Alt lead:    {info['alt_lead']}")
            print(f"  Patterns:    {info['num_patterns']}")
            print(f"  Orders:      {info['num_orders']}")
            print(f"  Instruments: {', '.join(info['instruments'].values())}")
            print(f"  Progression: {info['progression']}")
            print(f"  Structure:   {' > '.join(info['structure'])}")
            print()


if __name__ == "__main__":
    main()
