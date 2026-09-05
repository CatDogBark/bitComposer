"""
Command-line interface for bitcomposer.
"""

import argparse
import os
import sys
import time

from . import __version__
from .composer import compose_and_save


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
        choices=["snes", "genesis", "random"],
        default="random",
        help="Sound style (default: random)",
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

        if args.output and args.count == 1:
            filepath = args.output
        else:
            timestamp = int(time.time())
            seed_str = f"_s{seed}" if seed is not None else ""
            filepath = os.path.join(
                args.output_dir,
                f"bitcomposer_{timestamp}_{i}{seed_str}.it"
            )

        try:
            info = compose_and_save(filepath, seed=seed,
                                       tempo=args.tempo, energy=args.energy,
                                       scale=args.scale, style=args.style,
                                       drum_density=args.drum_density,
                                       drum_fills=not args.no_fills,
                                       drum_swing=args.swing,
                                       melody_style=args.melody,
                                       harmony_voicing=args.harmony_voicing,
                                       harmony_mode=args.harmony_mode,
                                       bass_weight=args.bass_weight,
                                       song_form=args.form)
        except Exception as e:
            print(f"Error generating song: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        print(f"Generated: {filepath}")

        if args.verbose:
            print(f"  Key:         {info['key']} {info['scale']}")
            print(f"  Tempo:       {info['tempo']} BPM "
                  f"(speed {info['speed']}, IT tempo {info['it_tempo']})")
            print(f"  Bass:        {info['bass_style']} ({info['bass_weight']})")
            print(f"  Arpeggio:    {info['arp_style']}")
            print(f"  Density:     {info['melody_density']}")
            print(f"  Melody:      {info['melody_style']} ({info['melody_contour']})")
            print(f"  Harmony:     {info['harmony_voicing']} / {info['harmony_mode']}")
            if info.get('chorus_modulated'):
                print(f"  Modulation:  chorus +1 semitone")
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
