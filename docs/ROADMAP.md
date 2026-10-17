# Roadmap

What is worth doing next, in the order it would be heard. Items are
recorded here when they come up so they are not lost; nothing here is
promised. See `ANALYSIS.md` for how changes are judged (measure first, ear
second) and `CHANGELOG.md` for what has shipped.

## Sound quality

These change how every note sounds, not what notes are played.

- **Brightness and register across the SNES palette (pass done).** The
  survey tool (`~/diags/bitcomposer/bright/survey.py`) renders every
  sustaining voice at the three pitches the melody sounds at and measures
  centroid against the fundamental, power per harmonic band, and the swing
  of the fundamental's share across the chorus cycle. Findings: brightness
  was already consistent across the register for all but the flute,
  whistle, pan flute and horn (brightened); the real fault was the chorus,
  where equal detuned layers formed a comb that swung the fundamental's
  share by 60-90 points on every pad and string voice (fixed: dry tone at
  80%, copies at different offsets, swing now under 15). Ruled out by
  measurement: aliasing above 8 kHz (zero at every note), the player's
  interpolation mode, and a 32 kHz sample rate for single-cycle voices.
  Still open: register splitting (a low and a high sample per lead) if a
  voice ever needs it, and a proper delay-modulated chorus for the pads.
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
  (gated snare). The widget readout of the drawn settings is done.
- **Style packs.** An instrument set paired with arrangement habits
  (`bitcomposer/packs.py`): voices per role, weighted draws for tempo,
  energy, scale, harmony mode, bass, drums and echo, a counter-line voice,
  orchestral fills, channel trims, arp figure weights. `ffvi` (orchestral)
  `mana` (Secret of Mana: mallets and air, hand percussion, bouncy habits)
  and `evermore` (Secret of Evermore: pads, drone bass, breathy flute,
  sparse or no drums; the atmospheric set) and `megamanx` (Mega Man X: driven
  guitars, pulse synth, synth brass, riff bass, slap echo; read off the
  game's own sample bank) are done; Evermore covers the ambient ground, so no
  separate Metroid pack. Packs from the banks: `megamanx` and `ffvi` are
  built from their games' SPC snapshots (every voice profiled and
  re-synthesised, echo from the DSP registers) and borrow nothing; `mana`
  and `evermore` are next, the same way, kits included. Rock grooves of their own (double-time hats, kick
  patterns under riffs) are the kit revision's job. A pack is data;
  the engine gaps that stay: riff-based bass, a detuned two-channel pad.
- **Loudness and the brass (1.x, measured 2026-10-17).** Songs are written
  at one level whatever they contain, and over sixteen random seeds the
  result runs from −25.4 to −17.8 LUFS, a 7.6 dB spread that tracks kit hits
  per second: sparse slow songs quiet, busy fast ones hot. Northern Dawn
  (Mega Man X, seed 202; toms groove, 180 BPM, the pack's kit boost of
  40/40/30 over the base 36) is the extreme at −15.7. Fix: a density-aware
  kit level (scale the kit channels by hits per second against a reference)
  and the Mega Man X kit trims back to the base; verify with ebur128 over a
  seed set. Separately, Northern Dawn's brass harmony is still forward after
  the 2026-10-17 pass (no J arpeggio on hard voices, brass a fifth up and
  3 dB down, echo centred, invented attack removed; harmony with echo now
  −32.0 LUFS against the lead at −27.8). Troy: manageable, still off.
  Next things to measure before changing anything: the synth brass's
  spectrum against the game's sample at the register it is now played in
  (the 3rd and 4th partials land at 700 Hz to 3 kHz), the chug gallop's
  note length against the voice (83 ms notes at 180 BPM), and whether the
  rhythm guitar should take the chug modes instead of the brass in this
  pack. Measure parts alone: zero the other channels' header volumes in a
  copy of the file, render, ebur128.
- **Pack revisions (in progress, 2026-10-16).** The plan Troy approved: one
  SOUND picker (done), then each pack rebuilt from its game's SPC snapshots
  so it borrows nothing and carries its own kit: `ffvi` (done, branch
  `ffvi-spc`: 35 own voices, echo from the DSP registers), `megamanx`
  (re-checked against Kage's named rips: 20 matched, five voices renamed,
  nine added; 23 own voices), `mana` (done,
  branch `mana-spc`: 25 own voices, no table exists so voices are named by
  measured character), `evermore` (done, branch `evermore-spc`: 22 own
  voices, seven matched William Kage's named rips by length at
  https://www.williamkage.com/snes_soundfonts/ , the rest by character), then a widget readout of the drawn song and a mixer regrouped
  by part with a KIT fold (done 2026-10-16: `voices:` and `drew:` lines in
  the song message, `GetSongInfo` on the daemon, voice labels on the
  faders, the KIT bus). Method and tools: `~/diags/bitcomposer/ffvi-spc/
  tools` (`survey.py` decodes and profiles every unique sample across a set
  of snapshots, `voices.py` traces each through the voice registers,
  `fine.py` and `match.py` compare a sample's steady profile with ours,
  `table.py` matches samples to a documented instrument table by exact BRR
  size). Identify by size against a table, never by which songs carry a
  sample: for FFVI the song-based guesses were wrong for eight voices.
  Community references used: the FF6 BRR sample table (names, sizes, ADSR,
  loop points) at
  https://www.ff6hacking.com/wiki/doku.php?id=ff3:ff3us:music:brrsamples:ff6
  and the per-song instrument-set format (16 slots per track at
  $C53F95) at
  https://www.ff6hacking.com/wiki/doku.php?id=ff3:ff3us:doc:asm:fmt:instrument_sets
  with the song-data tutorial at
  https://ff6hacking.com/wiki/doku.php?id=ff3:ff3us:tutorial:music:songdata.
  Mana and Evermore have no table as complete; identify there by the
  voice-register trace and by ear, and look for a community sample list
  first. Left out of `ffvi` for the kit revision: congas, shaker,
  tambourine, maracas (the kit has seven fixed slots); one-song colours
  (banjo, bagpipe, synth drums, metal hits, crowd) stay out.
- **Windows player.** The Windows zip is the generator only: the window
  makes songs, OpenMPT or XMPlay plays them. The Plasma widget's features
  (auto-generate on track end, live mixer and ECHO bus, KEEP and prune,
  shuffle, gain) live in the Linux daemon on libopenmpt and D-Bus. Two steps
  up: a topped-up folder (the window keeps generating every few minutes with
  a cap that prunes unkept songs), then a real player: bundle libopenmpt's
  Windows DLL with the window and drive it the way the daemon does, since
  the ctypes bindings already exist.
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
