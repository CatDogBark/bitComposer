# Roadmap

What is worth doing next, in the order it would be heard. Items are
recorded here when they come up so they are not lost; nothing here is
promised. See `ANALYSIS.md` for how changes are judged (measure first, ear
second) and `CHANGELOG.md` for what has shipped.

## Sound quality

These change how every note sounds, not what notes are played.

- **Release envelopes.** Every note in every palette stops dead when it is
  cut, because samples without instrument envelopes have no release. This
  is the single biggest gap between "tracker demo" and "game soundtrack" at
  the sample level. Two routes, which can be combined:
  - *Fade before cut.* Where the generator writes a note-cut, write a short
    volume slide (DFx or Dx0 over the last 1–2 rows) first, so the cut lands
    on near-silence. Cheap, works in every palette, approximates a release.
  - *Sustain loops with a release tail.* Build sustained SNES voices with a
    sustain-loop region followed by a short decaying tail, and write
    note-off (`===`) instead of note-cut. libopenmpt then exits the sustain
    loop and plays the tail: a real release, per instrument. The IT writer
    needs the sustain-loop fields (currently zero) and the SNES voices need
    tails; chip and FM voices can get short synthetic ones.
- **Reverb/echo on more than the lead.** The SNES echo ran on most voices.
  Harmony and arp echo returns at lower level, on the existing two echo
  channels or two more.
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
- **Drum ghost notes and velocity shape.** Drums have humanised hats and
  nothing else: no ghost snares, no accent pattern across the bar.
- **Per-section instrumentation.** Beyond the layer map, a plan for which
  voice carries which role per section (e.g. the pad drops out of the verse,
  the lead swaps for the bridge — the alt-lead swap is the only case today).
- **Harmony colour on pads.** The SNES arp now takes 7ths and 9ths; the
  pad voicings could carry an add9 or a 7th in the same palette.

## Generation

From `ANALYSIS.md` §5, unchanged:

- **Corpus statistics, no neural net.** n-gram tables for chord transitions,
  melodic intervals conditioned on scale degree and chord tone, and real
  rhythm-template frequencies, trained offline from symbolic chiptune and
  shipped as JSON. Keeps the zero-dependency property.
- **A small conditioned model for the melody line only**, with structure
  and arrangement staying in deterministic code.
- **A local LLM as arranger**, producing a typed style brief (key, scale,
  progression set, form, palette, energy curve) that drives the engine.

## Player

- HiDPI control sizes (fonts and popup already scale; buttons and sliders
  are still fixed pixels).
- Social preview image for the repository.
