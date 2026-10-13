# bitcomposer

Procedural 16-bit chiptune music generator. Creates Impulse Tracker (.it) module files using algorithmically composed melodies, bass lines, arpeggios, harmony, and drum patterns.

The generated music is inspired by the SNES and Sega Genesis era. Three sound palettes: **snes** — sampled strings, brass, choir, plucks and a gated drum kit rendered the way the SPC700 played them (16 kHz, looped, BRR-grained, with echo); **genesis** — FM bells, brass and bass; **chip** — square, pulse and triangle waves.

## Features

- **Motif-based melody** — phrase structure with contour shaping (arch, climb, valley, etc.), question-answer phrasing, and chorus callbacks so the hook comes back
- **Full harmony** — 2-3 note chord voicings across 3 channels, counter-melody generation, sustain/stabs/rhythmic modes, voiced in a lower octave to sit behind the melody
- **Mix mastering** — per-channel global volumes baked into the IT header so melody leads and harmony/drums sit in the background naturally, with volume decay slides on sustained notes
- **Dynamic arrangement** — energy curves across sections, gradual texture build, variable structure (tag/abrupt/fadeout endings, double bridges), instrument swaps between sections
- **Three palettes, 55 instruments** — SNES-style sampled voices (strings, brass, formant choir, flute, organ, e-piano, bell, marimba, pizzicato, harp, three basses, orchestra hit, gated drum kit) built at 16 kHz with loop points and a BRR codec model; FM (organ, brass, bell, pad, bass); and classic waveforms (square, pulse, triangle, saw, PWM, supersaw) with layered drums
- **Echo** — two delayed, panned copies of the lead, the SNES hardware-echo sound, as tracker channels
- **IT effects** — vibrato, portamento, J arpeggio on thin harmony, Q retrigger on fills, SDx note-delay swing, volume slides, velocity humanization, note-cut control
- **Drum system** — 6 drum channels, per-section pattern selection, fill patterns at transitions, swing/shuffle, sparse/busy density variants
- **Music theory** — 8 scales, 30 progressions including borrowed chords and secondary dominants, 7 chord types, two-bar harmonic rhythm within each pattern, progression variation between sections, key modulation (chorus up a semitone)
- **14-channel output** — melody, 3 harmony, bass, arp, kick, snare, hihat, tom, crash, open hihat, 2 echo
- **Named songs** — each module gets a seed-derived two-word title that leans with its scale ("Haunted Orchard", "Neon Causeway"), and a song message carrying key, BPM, palette, form, lead instruments and seed, which trackers and the companion player display
- **Reproducible** — optional seed parameter for deterministic output
- **Standard format** — outputs .it files playable by any tracker-compatible player (libopenmpt, VLC, Audacious, OpenMPT, etc.)
- **Zero dependencies** — pure Python, no external libraries required

## Install

```bash
pip install .
```

Or run directly:

```bash
python3 -m bitcomposer.cli
```

Tests (stdlib `unittest`, about 20 seconds):

```bash
python3 -m unittest discover -s tests -v
```

Measure a batch of output rather than trusting your ears — see `docs/ANALYSIS.md`:

```bash
python3 tools/analyze.py 'out/*.it'
```

## Usage

```bash
# Generate a single song
bitcomposer -o mysong.it

# Generate with verbose output
bitcomposer -v -o mysong.it

# Generate 5 songs into a directory
bitcomposer -n 5 -d ~/Music/Chiptune/

# Reproducible with a seed
bitcomposer -s 42 -o seed42.it
```

All style options default to `random`, so running `bitcomposer -o song.it` with no flags will randomize everything for maximum variety.

### Style Options

```bash
# Composition
--tempo slow|medium|fast|random
--energy chill|normal|intense|random
--scale minor|major|pentatonic|random
--style chip|snes|genesis|random
--echo on|off|random          # lead echo; always on for snes when random

# Drums
--drum-density sparse|normal|busy|random
--no-fills
--swing off|light|heavy|random

# Melody
--melody simple|phrased|random

# Harmony
--harmony-voicing thin|full|random
--harmony-mode stabs|sustain|rhythmic|random

# Bass
--bass-weight heavy|medium|light|random

# Song Form
--form standard|aaba|rondo|short|linear|random
```

### Example Presets

```bash
# Genesis boss fight — heavy, aggressive
bitcomposer -v -o boss.it --tempo fast --energy intense --style genesis --drum-density busy --swing heavy --harmony-mode rhythmic --bass-weight heavy --form short

# Chill exploration — light, airy, sampled SNES palette with echo
bitcomposer -v -o chill.it --tempo slow --energy chill --scale pentatonic --style snes --drum-density sparse --no-fills --swing light --bass-weight light --form aaba

# Game Boy flavour — square waves, no echo
bitcomposer -v -o gb.it --style chip --echo off --harmony-voicing thin --bass-weight light --form short

# Dark dungeon — medium, atmospheric
bitcomposer -v -o dungeon.it --tempo slow --energy chill --scale minor --drum-density sparse --no-fills --harmony-voicing thin --harmony-mode stabs --bass-weight medium --form rondo

# Credits roll — light, gentle
bitcomposer -v -o credits.it --tempo slow --energy chill --scale major --style snes --drum-density sparse --no-fills --bass-weight light --form linear
```

## Song Forms

Five song forms control the high-level architecture:

- **standard** — intro → verse → chorus → verse → chorus → bridge → chorus → outro (classic pop/game structure, optional double bridge)
- **aaba** — intro → verse → verse → bridge → verse → outro (no chorus, classic pop/jazz feel, sometimes doubles the form)
- **rondo** — intro → theme → episode → theme → episode → theme → outro (main theme returns between contrasting sections)
- **short** — 2-3 sections with no intro/outro (compact, great for game level music)
- **linear** — intro → 4-6 unique sections → outro (through-composed, no repeats, RPG/adventure feel)

Each form has its own energy curve. Endings are weighted toward fadeout (45%) and tag (40%), with abrupt endings rare (15%). Fadeout endings gradually ramp energy down across the outro patterns for a smooth wind-down. Short forms skip tag endings.

## How It Works

1. **Pick a key and scale** — randomly selects from game-music-friendly scales (minor pentatonic, dorian, harmonic minor, etc.)
2. **Choose chord progressions** — selects progressions for verse and chorus (50% chance of different chorus chords), with optional key modulation
3. **Generate motifs** — creates rhythmic+melodic templates with contour shapes that repeat and vary across sections, giving the melody recognizable phrases
4. **Select instruments** — picks a palette (snes / genesis / chip) and draws lead, harmony, arp, bass and kit from it, with an alternate lead for later sections. SNES voices are rendered at 16 kHz with attack-then-loop sustain and passed through a BRR codec model so they carry the SPC700's grain
5. **Compose layers**:
   - **Melody** — motif-based phrases with question-answer structure, vibrato, register variation, note-cuts to prevent droning
   - **Chords** — each four-bar pattern holds a chord timeline; about half the time the back two bars move to the next chord, the plagal neighbour or the dominant
   - **Harmony** — 2-3 note voicings led smoothly from fixed register anchors, decay matched to the voicing mode, optional counter-melody in chorus/bridge
   - **Bass** — root movement with weight control (heavy/medium/light affects register, volume, rhythm density, sustain, and sample selection)
   - **Arpeggio** — chord tones in patterns (up, down, up-down, random)
   - **Drums** — per-section patterns with fills at transitions, swing on hi-hats, crash on downbeats
   - **Echo** — the lead copied to two echo channels, 3 and 6 rows late
6. **Arrange** — energy curves scale volumes and density across sections (intro 50% → final chorus 100%), variable structure with multiple ending styles
7. **Master** — per-channel volume mixing (melody leads, harmony pushed back, drums balanced), sustain safety nets prevent notes ringing across section boundaries
8. **Write** — outputs a valid 14-channel Impulse Tracker module file

## License

MIT
