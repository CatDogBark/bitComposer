# Pack files

A pack is a sound for the generator: a palette (the chip it imitates),
voices for each part, and the habits of the scores it follows. The four
built-in packs are code; a **pack file** is the same thing as data, so a
pack can be added without touching the code. The SPC importer writes
them from a game's songs (`python -m bitcomposer.spc --pack OUT FOLDER`,
a first thin pack: `TRANSLATOR.md`, stage 2).

A pack file is a JSON file, with the pack's own voices as WAV files
beside it. It is data only: a pack someone sends you cannot run anything.

```bash
bitcomposer --pack-file mypack/pack.json -s 7 -v
```

composes a song with it. `--pack-file` takes the place of `--pack` and
`--sound`; the other options work as usual. A pack file is never drawn by
a random sound, only used when named.

## An example

```json
{
  "bitcomposer_pack": 1,
  "name": "myrpg",
  "label": "My RPG",
  "palette": "snes",
  "voices": {
    "lead": ["flute", "flute", "snes_synth_lead"],
    "harmony": ["strings"],
    "drums": {"kick": "thump"}
  },
  "habits": {
    "tempo": {"slow": 2, "medium": 3, "fast": 0},
    "harmony_mode": {"sustain": 3, "stabs": 1},
    "echo": 1.0,
    "echo_delay": {"eighth": 1, "dotted": 2}
  },
  "trims": {"hihat": 20},
  "samples": {
    "flute":   {"file": "flute.wav", "note": 72, "loop": [1200, 5400], "release": "flute"},
    "strings": {"file": "strings.wav", "hz": 220, "loop": [3000, 9000], "release": "strings", "volume": 58},
    "thump":   {"file": "kick.wav"}
  }
}
```

## Fields

- **`bitcomposer_pack`**: `1`. Marks the file as a pack file and says
  which version of this format it is.
- **`name`**: lower-case letters, digits and `_`, starting with a letter,
  at most 24 characters, and not the name of a built-in sound. The pack's
  own voices are known by `<name>_<voice>` in songs and the mixer.
- **`label`**: a short name to show. Defaults to `name`.
- **`palette`**: `chip`, `snes` or `genesis`: the chip whose engine rules
  the pack plays by (the SNES echo, the mix, the voices it can borrow).
- **`voices`**: the voices each part draws from. Any role left out keeps
  the palette's own voices, so a pack can change as little as its lead.
  - Lists of voice names, one drawn per song, a name repeated to draw it
    more often: `lead`, `alt_lead` (the bridge's lead; defaults to `lead`),
    `harmony`, `counter` (the counter-line), `arp`, `bass_heavy`,
    `bass_medium`, `bass_light`.
  - `bass_hi`: one voice, the bass line's upper-register sample.
  - `drums`: kit pieces and their voices: `kick`, `snare`, `hihat`, `tom`,
    `crash`, `open_hihat`, `rim`. Pieces left out keep the palette's kit;
    the chip palette has none, so a chip pack gives all seven.

  A voice name is one of the pack's own `samples`, or a built-in voice
  (any voice the palettes and packs have: `snes_strings`, `ffvi_harp`,
  `gen_lead`, ...).
- **`habits`**: weighted draws and settings the composer follows. Any
  habit left out is drawn the way the palette draws it. The list is below.
- **`trims`**: channel volumes (0 to 64) by part, over the mix: `melody`,
  `harmony`, `bass`, `arp`, `kick`, `snare`, `hihat`, `tom`, `crash`,
  `openhat`, `echo.melody`, `echo.harmony`, `echo.arp`.
- **`samples`**: the pack's own voices, by name (see below).

## Samples

Each of the pack's own voices is a WAV file (PCM, 8, 16, 24 or 32-bit,
mono or stereo, any rate; stereo is averaged to mono; at most two million
frames).

- **`file`**: the WAV, named relative to the pack file.
- **`note`** or **`hz`**: the pitch the recording sounds at its own rate,
  as a MIDI note (60 is middle C; fractions are cents) or in Hz. The voice
  is tuned from it. A kit voice may leave both out: it then plays as
  recorded.
- **`loop`**: `[start, end]` in sample frames, the part repeated while a
  note is held. Without one, the sample plays once (a pluck, a drum).
- **`release`**: how a held note fades when it ends, by family: `strings`,
  `choir`, `pad`, `brass`, `flute`, `organ`, `lead`, `keys`, `bass`, `psg`.
  Needs a loop. Without one, a note ends where it is cut.
- **`percussion`**: `true` for a kit voice: it is left at its own level
  rather than evened out with the tonal voices. Defaults to `true` for a
  voice the `drums` use and `false` otherwise.
- **`volume`**: the default note volume, 1 to 64. Defaults to 60.

Tonal voices are evened out the way the built-in ones are: a sustaining
voice by its loop, so like voices sit at like levels. A voice whose loop
is much quieter than its attack, or that has no loop, counts as struck (a
pluck, a bell), which the harmony and the arp take into account.

## Habits

Weighted draws, as `{"name": weight}`; a name weighted 0 is never drawn,
and names left out are out:

| habit | names |
|---|---|
| `tempo` | `slow`, `medium`, `fast` |
| `energy` | `chill`, `normal`, `intense` |
| `scale_family` | `minor`, `major`, `pentatonic` |
| `harmony_voicing` | `full`, `thin` |
| `harmony_mode` | `stabs`, `sustain`, `rhythmic`, `ostinato`, `pulse`, `chug_sync`, `chug_offbeat`, `chug_gallop` |
| `bass_weight` | `heavy`, `medium`, `light` |
| `bass_style` | `steady`, `walking`, `octave`, `driving`, `drone`, `riff` |
| `riffs` | the bass riff when `bass_style` draws `riff`: `rock`, `gallop`, `drop`, `fifth_bounce`, `funk`, `octaves`, `pedal_push` |
| `drum_density` | `sparse`, `normal`, `busy` |
| `drum_swing` | `off`, `light`, `heavy` |
| `form` | `standard`, `aaba`, `rondo`, `short`, `linear` |
| `intro` | `arp_bed`, `pad_hook`, `riff_vamp`, `drum_pickup` |
| `arp_figures` | the arpeggio figures, `classic_up`, `up_down`, `broken_octave`, `cascade`, `sync_push`, `run16`, `gallop`, `offbeat_stabs`, `quarter_up`, `pedal_bounce`, `sparse_pulse` |
| `echo_wet` | `light`, `normal`, `wet` |
| `echo_delay` | `eighth`, `dotted`, `quarter`, `slap` (48 ms), `row` (one row) |
| `echo_stereo` | `bounce`, `centre` |

Chances, from 0 to 1:

- `echo`: that a song has echo at all.
- `counter_line`: that a chorus or bridge pattern carries a counter-line
  (0.3 without the habit).
- `drumless`: that a whole song has no kit.
- `crash_chance`: that a phrase start gets a crash.

Others:

- `section_rolls` (`true`/`false`): a tom roll into the next section.
- `fill_crash` (`true`/`false`): crashes in the drum fills.
- `hat_stroke` (0 to 1): the level of every second hi-hat hit, a
  player's back stroke; 1 plays them alike.
- `lead_shift` (semitones, -24 to 24): moves the lead's register.
- `echo_feedback` (`[low, high]`): each repeat's level relative to the
  last, drawn per song between the two.
- `power_chords`: `true` for fifths under every harmony voice, or a list
  of the harmony voices that play them.
- `lead_ranges`: lead voices and their `[lowest, highest]` MIDI notes.

The program checks all of this when it loads a pack, and a mistake is
reported with where it is (`habits.tempo.medum: not one of slow, medium,
fast`).

## Where it is checked

`bitcomposer/packs/packfile.py` reads the format; the tests in
`tests/test_packfile.py` read every built-in pack back through it, so the
format can say everything the built-in packs say.
