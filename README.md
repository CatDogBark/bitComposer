# bitComposer

[![CI](https://github.com/CatDogBark/bitComposer/actions/workflows/ci.yml/badge.svg)](https://github.com/CatDogBark/bitComposer/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/CatDogBark/bitComposer)](https://github.com/CatDogBark/bitComposer/releases/latest)
![License](https://img.shields.io/badge/license-MIT-green)

Procedural 16-bit game music. A player that composes the next song as the
current one ends, with a live mixer, on Linux and Windows; a command line
and a generator library underneath, pure Python with no dependencies,
writing Impulse Tracker `.it` modules any tracker player reads; and a KDE
Plasma widget for the panel.

Every run composes a new song: a motif-based melody with call-and-response
phrasing, voice-led harmony, bass, arpeggio and drums, arranged into a form
(verse–chorus, AABA, rondo, through-composed) with a drawn intro, an energy
curve and a real ending, titled after what it drew, between 1:15 and 3:30
long. Seven sounds, picked with `--sound`:

- **snes** — sampled-style voices built the way the SNES made sound, through a BRR codec model and the SNES echo.
- **ffvi**, **mana**, **evermore**, **megamanx** — style packs: an instrument set rebuilt from each game's own sound chip (every sample profiled, nothing copied) plus the arrangement habits of its score. Details under [Sounds](#sounds).
- **genesis** — FM bells, brass, organ and bass.
- **chip** — square, pulse and triangle waves. Closest to NES and Game Boy.

**[Listen in your browser](https://catdogbark.github.io/bitComposer/)** — the actual modules, played live by libopenmpt in WebAssembly: one song per sound, straight from the generator, regenerated with each release.

**Reproducible, not frozen.** The same seed on the same version gives the same song, byte for byte. A new version may change what a seed draws, and the song message records the version that wrote the file.

## Install

**Windows.** Every release carries `bitComposer-setup.exe`: the player, the
command line, a Start menu entry and an uninstaller; or `bitComposer-windows.zip`
with the two executables and nothing to install. No Python needed. See
[Windows](#windows).

**Linux.** From PyPI with [pipx](https://pipx.pypa.io/), so it lands on your
PATH without touching the system Python (Debian and Fedora refuse a plain
`pip install` there; `sudo apt install pipx libopenmpt0 python3-tk` or
`sudo dnf install pipx libopenmpt python3-tkinter` gets pipx, the module
library and the window toolkit):

```bash
pipx install bitcomposer
bitcomposer-player --install-desktop   # once: the app-menu entry
bitcomposer-player                     # the player
bitcomposer -d out -s 42 -v            # the command line, reproducible, with details
```

The player needs libopenmpt (above) and an audio output: `paplay`
(pulseaudio-utils), `pw-cat` (pipewire-bin) or `aplay` (alsa-utils).
`bitcomposer-player --check` says what it found. Upgrades are
`pipx upgrade bitcomposer`.

From a clone, for development:

```bash
git clone https://github.com/CatDogBark/bitComposer.git
cd bitComposer
python3 -m bitcomposer -d out
```

Play the result with [OpenMPT](https://openmpt.org/) (Windows),
[Schism Tracker](https://schismtracker.org/), VLC, Audacious, `xmp`, or
anything built on libopenmpt.

Python 3.10 or newer, no dependencies. The player and the small generate
window (`bitcomposer-gui`) use tkinter, which Debian and Ubuntu ship
separately as `python3-tk`.

## Sounds

A style pack pairs an instrument set with the arrangement habits of the score it imitates. Each is built from the game's SPC snapshots: every sample decoded and profiled, matched to the community's instrument tables where they exist, and re-synthesised; nothing from the games is in the repository.

- `ffvi`: every voice modelled on the game's own sample bank and named by its instrument table: the chorused string section, flutes in chords, the dark synth lead of Locke and the Returners, trumpet, trombone, oboe, Terra's and Cyan's pan flutes, cello, choir, pipe organ and rock organ, the Aria's soprano, the Battle theme's distortion guitar, piano, harp, picked string, acoustic guitar, tubular bell, xylophone, a bass guitar and a kit of its own (kick, snare, hats, cymbal, timpani, wood block), with ostinato strings, a brass counter-line in the chorus, timpani rolls into sections and the game's short, wet echo. 
- `mana`: every voice modelled on the game's own sample bank: a soft slow-breathed flute, bright chorused strings, an 'ah' choir, a high whistle, soft and synth brass, marimba, vibraphone, electric piano, tubular bell, reed, accordion, glass and sine pads, fingered, electric and slap basses and a kit of its own (kick, snare, hats, crash, tom, castanet), with major and pentatonic keys, syncopated harmony, bouncy arps, light swing, the kick and snare set back and the game's one-row echo. 
- `evermore`: every voice modelled on the game's own sample bank: a slow bright string swell, a warm pad, a dark pad, a glass bell, a breathy flute, a reed, an "oo" choir, harp, tinker music box, piano, pluck and kalimba, a textured drone and a wind loop, a bass, and a quiet kit (soft kick, frame drum, brushes, hat, cymbal, wood ping), with slow tempos, sustained harmony, a drone bass, sparse or no drums, long linear forms and the game's sparing 80 ms echo. 
- `megamanx`: every voice modelled on the game's own sample bank and named by it: a driven, chorused lead guitar, a chugging rhythm guitar on power chords, the overdrive guitar for arps and counter-lines, synth brass, strings, a guitar swell pad, a saw pad, organ, the boomer synth lead, square and bright leads, a hollow wave, a bell synth, an acoustic pluck, the orchestra hit for stabs, slap and synth basses on a riff, and a tight kit, at fast tempos in minor keys with the game's 48 ms slapback echo.

`--sound` picks a palette or a pack in one word; left to chance, the four packs together weigh as much as plain snes.

- **snes** — sampled-style voices rendered the way the SNES actually made sound: strings, brass, a formant choir, flute, organ, e-piano, bells, plucks and a gated drum kit at 16 kHz with loop points, passed through a BRR codec model for the grain, with the lead, harmony and arp through an echo modelled on the SNES unit's result: fading, darkening repeats on a beat fraction, drawn per song.
- **genesis** — FM bells, brass, organ and bass.
- **chip** — square, pulse and triangle waves.

## What you can steer

Everything defaults to `random`.

```
--sound   chip|snes|genesis|ffvi|mana|evermore|megamanx  the sound in one word: a palette or a style pack (overrides the two below)
--style   chip|snes|genesis          sound palette
--pack    ffvi|mana|evermore|megamanx|none|random  style pack: an instrument set with the habits of the scores it imitates (a pack implies snes)
--echo    on|off|random              echo (random: 70% of snes songs, never chip or genesis)
--echo-wet    light|normal|wet|random  how much of the lead, harmony and arp the echo carries
--echo-delay  eighth|dotted|quarter|slap|row|random  beat fraction between repeats, a 48 ms slap, or one row (random: weighted by tempo)
--echo-stereo bounce|centre|random     repeats alternate sides, or sit under their source
--keys    moving|home                moving: choruses/bridges may change key; home: stay put
--tempo   slow|medium|fast           80–110 / 110–140 / 140–180 BPM
--energy  chill|normal|intense       density and arrangement weight
--scale   minor|major|pentatonic
--form    standard|aaba|rondo|short|linear
--drum-density sparse|normal|busy    --no-fills    --swing off|light|heavy
--melody  simple|phrased             phrased = motif-based, has a hook
--harmony-voicing thin|full          two real voices, or three
--harmony-mode stabs|sustain|rhythmic
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
4. Each four-bar pattern holds a chord timeline; about half the time the back two bars move to a related chord. Melody resolves onto chord tones at each change. Harmony is two or three real voices placed near fixed anchors, so it steps rather than leaps and keeps the chord's third; the anchors are set per voice family (pads low and wide, brass and guitars mid and close), the top voice stays under the lead's line, and a stab holds for as long as the voice needs to speak. Bass and arp follow and rest with the section's energy.
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

## The player

<img src="docs/images/widget.png" alt="The Plasma widget: now playing, transport, gain, generate and settings, playlist" width="420">

`bitcomposer-player` (Linux) and `bitComposer.exe` (Windows) are the same
program: a folder of songs played through libopenmpt, GENERATE AND PLAY,
auto-generate when a track ends (the "radio"), the settings of what it
composes (sound, tempo, energy, scale, form, echo, bass, drums, harmony)
with presets, a live mixer per channel with the KIT and ECHO buses and
APPLY TO TRACK to write the mix into the file, gain with a soft limiter,
shuffle, and the playlist with KEEP: every track the player makes is
provisional (`<Title> (auto).it`) and pruned after ten unless kept. The
picture is the Plasma widget, which has the same layout. The player tells
you when a newer release exists.

## Windows

Every release carries `bitComposer-setup.exe` (the installer) and `bitComposer-windows.zip` (the same two executables, no install), built by GitHub Actions on every push to main and attached on the tag: `bitComposer.exe`, the player, with libopenmpt inside; and `bitcomposer-cli.exe`, the command line. Songs are `.it` files; [OpenMPT](https://openmpt.org) and XMPlay play them too. Nothing is code-signed, so SmartScreen asks once ("More info", "Run anyway"). With Python installed instead, `pipx install bitcomposer` gives the same programs as `bitcomposer-player` and `bitcomposer`.

## Plasma widget (optional, Linux + KDE Plasma 6)

`companion/` holds the panel version of the player: a libopenmpt D-Bus
daemon with MPRIS2 and a Plasma 6 widget with the same transport, gain,
settings, presets, mixer and radio mode, for people who want it in the
panel rather than in a window.

```bash
sudo apt install pipx libopenmpt0 python3-tk python3-dbus python3-gi qt6-tools pulseaudio-utils
pipx install bitcomposer         # the generator the player runs
./companion/install.sh --check   # see what it would do
./companion/install.sh           # install, enable the daemon
```

See [docs/INSTALL.md](docs/INSTALL.md). The generator does not depend on
any of this.

## License

MIT. Every instrument is synthesized; no samples were taken from any game.
