# Roadmap

What is worth doing next, in the order it would be heard. Items are
recorded here when they come up so they are not lost; nothing here is
promised. See `ANALYSIS.md` for how changes are judged (measure first, ear
second) and `CHANGELOG.md` for what has shipped.

## Sound quality

These change how every note sounds, not what notes are played.

- **Brightness and register across the SNES palette.** Measured against the
  Mega Man X bank: the game's lead keeps its spectral centroid at 2 to 2.5
  times the fundamental at every note; ours sat at 0.9 to 1.3 and fell as
  the pitch rose, which is why it read as dull. Three things to carry
  through every SNES voice, not just the Mega Man X set: (1) synthesise
  content relative to the note, so leads keep a centroid near twice the
  fundamental across the melody's two octaves; (2) distortion on one layer
  and chorus after it, the way a pedal sits after an amp, so detuned layers
  never intermodulate into growl; (3) cascaded filters for cabinet and
  presence shapes. Two things measured and ruled out: aliasing above 8 kHz
  is zero at every note, and the player's interpolation mode makes no
  audible difference, so a 32 kHz sample rate buys nothing for single-cycle
  voices (it only helps voices with non-periodic content: chorus smear,
  noise, decays). Register splitting, one sample for the low octave and one
  for the high, stays an option if one sample cannot hold the range.
- **Release envelopes — done (merged 2026-10-14, approved by ear).** Sustained
  voices now carry a sustain loop and a decaying tail; the generator writes
  note-off for them so each family releases at its own pace
  (`samples.RELEASE`, `samples.PRESET_RELEASE`). Lengths were judged right as drafted. One-shot voices (plucks, drums)
  still end on their own.
- **SNES echo as a real send.** The S-DSP echo was a per-voice send into one
  delay line with feedback and a filter, usually on lead, harmony and arp
  with the drums dry. We keep the result and drop the hardware's limits.
  Stage one (done): a decaying, darkening three-tap tail on the lead, sent
  per note. Stage two (done): harmony and arp sends with their own levels,
  a `layout:` line in the song message, one ECHO bus fader in the widget
  with an expand to LEAD / HARM / ARP, and `--echo-wet`. Stage three
  (done): per-song delay (eighth, dotted eighth or quarter, weighted by
  tempo), feedback and wetness drawn per song, sends opened in thin
  sections and pulled back in the chorus, and bounce / centre stereo with
  a pan per tap. Left for later: echo on the drums as a rare choice
  (gated snare), and a widget readout of the drawn settings.
- **Style packs.** An instrument set paired with arrangement habits
  (`bitcomposer/packs.py`): voices per role, weighted draws for tempo,
  energy, scale, harmony mode, bass, drums and echo, a counter-line voice,
  orchestral fills, channel trims, arp figure weights. `ffvi` (orchestral)
  `mana` (Secret of Mana: mallets and air, hand percussion, bouncy habits)
  and `evermore` (Secret of Evermore: pads, drone bass, breathy flute,
  sparse or no drums; the atmospheric set) and `megamanx` (Mega Man X: driven
  guitars, pulse synth, synth brass, riff bass, slap echo; read off the
  game's own sample bank) are done; Evermore covers the ambient ground, so no
  separate Metroid pack. Rock grooves of their own (double-time hats, kick
  patterns under riffs) are the kit revision's job. A pack is data;
  the engine gaps that stay: riff-based bass, a detuned two-channel pad.
- **SPC sample banks.** An SPC snapshot holds the whole sound chip: the
  sample bank in BRR, every voice's envelope and pitch, the echo settings.
  A loader (`--spc-bank file.spc`) would decode a user-supplied snapshot
  and map its samples onto a pack's roles through a small per-game role
  map, falling back to the synthesised voices without one. The repo ships
  the code, never the samples: the rips are the publishers' recordings and
  do not belong in a public repository. The decoder and the bank profiler
  already exist from the Mega Man X analysis (`~/diags/bitcomposer/mmx`).
- **Mix by palette, fully.** Only the arp is palette-specific today. Per-
  palette tables for every channel, set by ear, the way the arp levels were.

## Arrangement

- **Chip chord stabs (J effect).** The `Jxy` arpeggio command cycles one
  channel through three notes fast enough to read as a chord — the
  definitive NES trick. Add it as an *occasional* arp figure in the chip
  palette (off-beat stabs where each hit carries the whole triad via J),
  not a default: on a track that already has a pulse lead, pulse harmony
  and a pluck arp it can turn to mush. Keep if it earns its place by ear.
- **Arp register motion.** Climbing figures alternate bars an octave up
  today. Let a figure sit low in the verse and high in the chorus, or fall
  into a chord change, with the existing melody-collision check so the arp
  stays out of the lead's register.
- **Drum ghost notes and velocity shape — done (merged 2026-10-14, approved by ear)**,
  along with phrase variation, the whole kit, fills by context and
  breakdowns; see `bitcomposer/drums.py`.
- **Per-section instrumentation.** Beyond the layer map, a plan for which
  voice carries which role per section (e.g. the pad drops out of the verse,
  the lead swaps for the bridge — the alt-lead swap is the only case today).
- **Harmony colour on pads.** The SNES arp now takes 7ths and 9ths; the
  pad voicings could carry an add9 or a 7th in the same palette.

## Melody

The engineering around the melody is now solid; the melody is the weak part
and the hit-or-miss part. Two steps, in order.

- **Motif grammar (next).** Motifs built from small cells with known shapes
  (step-step-leap, neighbour-and-return, repeated note, leap-and-fall); the
  rhythm fixed as the phrase's identity with pitches varying inside it;
  two-bar cells repeated exactly before the tail changes; tendency tones
  resolved (7→1, 4→3); leaps limited to a few sanctioned places (a fourth
  or fifth to launch a phrase, an octave for drama, steps back down).
  Measured by step-to-leap ratio, exact cell repetition rate and rhythmic
  self-similarity across bars; reviewed on an identical arrangement.
- **Corpus statistics, no neural net.** If the grammar is not enough: learn
  interval and rhythm tables from real NES/SNES-era melodies offline —
  intervals conditioned on scale degree, beat position and chord tone;
  rhythm-cell frequencies; phrase-ending patterns — and ship them as JSON
  the generator samples from under the same constraints. Corpus
  preparation is the work (a symbolic dataset such as NESMDB, a stdlib MIDI
  reader, melody-track selection); the tables are small and the
  zero-dependency property holds. Statistics are derived data, not songs.

## Generation

From `ANALYSIS.md` §5:

- **Corpus statistics** — see Melody above.
- **A small conditioned model for the melody line only**, with structure
  and arrangement staying in deterministic code.
- **A local LLM as arranger**, producing a typed style brief (key, scale,
  progression set, form, palette, energy curve) that drives the engine.

## Game integration

bitComposer is intended, eventually, as the music engine of a game the
author is building. Nothing here is near-term; it is recorded so the
composer's design keeps the door open.

- **The shape of it.** The game would not run Python. It needs a composer
  that produces module bytes and libopenmpt to play them; libopenmpt has
  C, C++, Rust and C# bindings and runs inside Unity and Godot today. The
  port of the composer is the only real work, and seeded determinism makes
  it verifiable byte for byte against this Python reference, which stays
  the design workbench.
- **Loop form.** Level music loops without an ending: a form whose last
  pattern leads back into its first.
- **Intensity layers.** The same seed rendered at two or three energy
  tiers with identical form, so a game can crossfade between them on the
  beat as the state changes. Seeded section reuse makes this natural.
- **Transitions and stingers.** Short fills or hits in the piece's key and
  palette to bridge one state to another.
- **Palette as a game parameter**, per area or faction.
- **Stable-key mode exists:** `--keys home` pins every section to the home
  key. Game loops that sit under a scene, tracks that must match a stinger,
  and A/B tests of other engine changes all want it; the default moving
  plan is tuned for browsing a generator.
- **In-browser generation** for the listening page is the same problem in
  miniature; Pyodide (CPython in WebAssembly, ~7 MB) would run the
  dependency-free generator unchanged and is the first thing to try.

## Player

- HiDPI control sizes (fonts and popup already scale; buttons and sliders
  are still fixed pixels).
- Social preview image for the repository.
