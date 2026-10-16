# bitComposer

[![CI](https://github.com/CatDogBark/bitComposer/actions/workflows/ci.yml/badge.svg)](https://github.com/CatDogBark/bitComposer/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/CatDogBark/bitComposer)](https://github.com/CatDogBark/bitComposer/releases/latest)
![License](https://img.shields.io/badge/license-MIT-green)

Procedural 16-bit game music. Pure Python, no dependencies, writes Impulse
Tracker `.it` modules you can play in any tracker player.

Every run composes a new song: a motif-based melody with call-and-response
phrasing, voice-led harmony, bass, arpeggio and drums, arranged into a form
(verse–chorus, AABA, rondo, through-composed) with an energy curve and a real
ending. Three sound palettes:

- **snes + packs** — a style pack pairs an instrument set with the arrangement habits of the scores it imitates. `ffvi`: every voice modelled on the game's own sample bank: the chorused string section, string pad and choir, horn, trumpet and brass section, oboe, clarinet, flute and pan flute, piano, harp, pizzicato and music box, a flute-stop pipe organ, fingered and bowed basses and a kit of its own (bass drum, snare, hat, ride, crash, tom, rim, timpani), with ostinato strings, a horn counter-line in the chorus, timpani rolls into sections and the game's short, wet echo. `mana`: celesta, kalimba, steel drum, wind chimes, whistle, pan flute, a glassy pad and a hand-percussion kit (conga, shaker, tambourine, woodblock), with major and pentatonic keys, syncopated harmony, bouncy arps, light swing and the kick and snare set back. `evermore`: warm and dark pads that swell, a drone under the song, a breathy flute, an "oo" choir, tubular bells, frame drum and brushes, with slow tempos, sustained harmony, a drone bass, sparse or no drums, long linear forms and a wet, centred echo on a quarter or dotted-eighth delay. `megamanx`: a driven, chorused lead guitar, a chugging rhythm guitar on power chords, a dry pulse synth for arps and counter-lines, synth brass, a string pad, a snapping synth bass on a riff, and a tight kit, at fast tempos in minor keys with the game's 48 ms slapback echo. `--sound` picks a palette or a pack in one word; left to chance, the four packs together weigh as much as plain snes.
- **snes** — sampled-style voices rendered the way the SNES actually made sound: strings, brass, a formant choir, flute, organ, e-piano, bells, plucks and a gated drum kit at 16 kHz with loop points, passed through a BRR codec model for the grain, with the lead, harmony and arp through an echo modelled on the SNES unit's result: fading, darkening repeats on a beat fraction, drawn per song.
- **genesis** — FM bells, brass, organ and bass.
- **chip** — square, pulse and triangle waves. Closest to NES and Game Boy.

**[Listen in your browser](https://catdogbark.github.io/bitComposer/)** — the actual modules, played live by libopenmpt in WebAssembly: two seeds rendered in all three palettes, straight from the generator, regenerated with each release.

## Quick start

```bash
git clone https://github.com/CatDogBark/bitComposer.git
cd bitComposer
python3 -m bitcomposer -d out            # writes out/<Title>.it
python3 -m bitcomposer -d out -s 42 -v   # reproducible, with details
```

Play the result with [OpenMPT](https://openmpt.org/) (Windows),
[Schism Tracker](https://schismtracker.org/), VLC, Audacious, `xmp`, or
anything built on libopenmpt. To install the `bitcomposer` command:

```bash
pip install .
```

Python 3.10 or newer. Nothing else.

## What you can steer

Everything defaults to `random`.

```
--sound   chip|snes|genesis|ffvi|mana|evermore|megamanx  the sound in one word: a palette or a style pack (overrides the two below)
--style   chip|snes|genesis          sound palette
--pack    ffvi|mana|evermore|megamanx|none|random  style pack: an instrument set with the habits of the scores it imitates (a pack implies snes)
--echo    on|off|random              echo (random: 70% of snes songs, never chip or genesis)
--echo-wet    light|normal|wet|random  how much of the lead, harmony and arp the echo carries
--echo-delay  eighth|dotted|quarter|slap|random  beat fraction between repeats, or a 48 ms slap (random: weighted by tempo)
--echo-stereo bounce|centre|random     repeats alternate sides, or sit under their source
--keys    moving|home                moving: choruses/bridges may change key; home: stay put
--tempo   slow|medium|fast           80–110 / 110–140 / 140–180 BPM
--energy  chill|normal|intense       density and arrangement weight
--scale   minor|major|pentatonic
--form    standard|aaba|rondo|short|linear
--drum-density sparse|normal|busy    --no-fills    --swing off|light|heavy
--melody  simple|phrased             phrased = motif-based, has a hook
--harmony-voicing thin|full          --harmony-mode stabs|sustain|rhythmic
--bass-weight heavy|medium|light
--name    title|timestamp            file naming; --suffix adds a marker
-s SEED   -n COUNT   -o FILE   -d DIR   -v
```

Some starting points:

```bash
# Overworld — bright, sampled palette with echo
bitcomposer -d out --style snes --scale major --tempo medium --form standard

# FM boss fight
bitcomposer -d out --style genesis --tempo fast --energy intense --scale minor --drum-density busy --form short

# Game Boy flavour — square waves, thin harmony, no echo
bitcomposer -d out --style chip --echo off --harmony-voicing thin --bass-weight light --form short

# Credits roll
bitcomposer -d out --style snes --tempo slow --energy chill --scale major --drum-density sparse --no-fills --form linear
```

## How it works

1. Pick a key and a scale weighted toward game music (minor pentatonic, dorian, harmonic minor, mixolydian…), then a progression for it. The tables include borrowed chords and secondary dominants — ♭VII, ♭VI, V/V — not just the diatonic set.
2. Choose a form and its energy curve; decide which sections repeat. Repeated sections draw the same music from the same seed, so the hook comes back.
3. Generate a motif (rhythm template plus contour) and vary it per bar in statement/answer pairs. Fourteen rhythm templates, six of them with 16th-note pushes and pickups.
4. Each four-bar pattern holds a chord timeline; about half the time the back two bars move to a related chord. Melody resolves onto chord tones at each change; harmony is voiced from fixed register anchors so it steps rather than leaps; bass and arp follow and rest with the section's energy.
5. Drums come from one-bar templates by section and density, with fills, retriggered snare rolls and tick-level swing.
6. Instruments are synthesized per song from the chosen palette and written as samples. SNES voices get attack-then-loop sustain and the BRR treatment.
7. The echo: held lead notes and phrase endings come back as three fading, darkening repeats, the harmony and arp as lighter ones, each on return channels of their own, drums and bass dry. Everything is written as a 19-channel `.it` with the title and a song message (key, BPM, palette, form, seed, and a `layout:` line naming every channel's role) that trackers display.

Each song gets a seed-derived two-word title that leans with its scale:
*Haunted Orchard*, *Neon Causeway*, *Rusted Foundry*.

## Measuring instead of guessing

`tools/analyze.py` parses `.it` files back from disk (stdlib only, independent
of the generator) and scores a batch on the things that correlate with
"sounds like a song": section reuse, motif repetition, rhythmic grid, chord
voicing variety, voice motion, effect vocabulary, drum density.

```bash
python3 tools/analyze.py 'out/*.it'          # metric table
python3 tools/analyze.py --grid out/song.it  # tracker-style pattern dump
```

[docs/ANALYSIS.md](docs/ANALYSIS.md) is the story of this project: the
output was once limited by three silent arrangement bugs that nine commits
of ear-checking never caught, and every improvement since has been measured
before and after. Read it before changing the generator.

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## Windows

Every release carries `bitComposer-windows.zip` with two executables built by GitHub Actions: `bitComposer.exe`, a small window (palette, style pack, echo, energy, tempo, how many, save folder, Generate), and `bitcomposer-cli.exe`, the command line. Songs are `.it` files; [OpenMPT](https://openmpt.org) plays them and will play a whole folder as a playlist. The executables are not code-signed, so SmartScreen asks once. With Python installed instead, `pip install git+https://github.com/CatDogBark/bitComposer` gives the same two commands as `bitcomposer` and `bitcomposer-gui`.

## Companion player (optional, Linux + KDE Plasma 6)

<img src="docs/images/widget.png" alt="The Plasma widget: now playing, transport, gain, generate and settings, playlist" width="420">

`companion/` holds a desktop player stack: a libopenmpt D-Bus daemon with
MPRIS2, a Plasma 6 panel widget with transport, gain, generator settings,
presets and a per-channel mixer, and an auto-generate "radio" mode that
composes the next track as the current one ends.

```bash
./companion/install.sh --check   # see what it would do
./companion/install.sh           # install, enable the daemon
```

See [docs/INSTALL.md](docs/INSTALL.md). The generator does not depend on
any of this.

## License

MIT. Every instrument is synthesized; no samples were taken from any game.
