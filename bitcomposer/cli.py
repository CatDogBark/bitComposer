"""
Command-line interface for bitcomposer.
"""

import argparse
import os
import sys
import time

from . import __version__
from .composer import compose_song, save_song, unique_path


def main():
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
        "--suffix",
        default="",
        help="Text appended to a title-named file before .it, e.g. \" (auto)\"",
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
        help="Harmony voicing: thin (1 note) or full (2-3 note chords) (default: random)",
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
        "--keys",
        choices=["moving", "home"],
        default="moving",
        help="moving: choruses and bridges may change key (default); "
             "home: every section stays in the home key, for loops that must "
             "sit still or for A/B tests of other changes",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"bitcomposer {__version__}",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(args.count):
        seed = args.seed
        if seed is not None and args.count > 1:
            seed = seed + i

        try:
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
                                echo=args.echo, echo_wet=args.echo_wet, keys=args.keys)
            info = song["info"]

            if args.output and args.count == 1:
                filepath = args.output
            elif args.name == "title":
                # The file is the song: what the player shows is what the
                # folder shows.
                filepath = unique_path(args.output_dir, song["name"], args.suffix)
            else:
                timestamp = int(time.time())
                seed_str = f"_s{seed}" if seed is not None else ""
                filepath = os.path.join(
                    args.output_dir,
                    f"bitcomposer_{timestamp}_{i}{seed_str}{args.suffix}.it"
                )
            save_song(song, filepath)
        except Exception as e:
            print(f"Error generating song: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        print(f"Generated: {filepath}")

        if args.verbose:
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
                print(f"  Chorus prog: alternate")
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
