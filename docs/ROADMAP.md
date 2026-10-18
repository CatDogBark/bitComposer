# Roadmap

What is worth doing next, in the order it would be heard. Items are
recorded here when they come up so they are not lost; nothing here is
promised. See `ANALYSIS.md` for how changes are judged (measure first, ear
second) and `CHANGELOG.md` for what has shipped.

## Release (1.0.0)

Decided 2026-10-18. The product is the generator and, on top of it, a player
that generates while you listen, the way the Plasma widget does, on Linux
and Windows as far as each allows. The 1.0.0 gate holds both the generator
and the Linux companion; the cross-platform player is 1.x.

- **Pipeline (done, branch `release-pipeline`).** A `v*` tag builds the
  sdist and wheel, checks the tag against `bitcomposer.__version__`, and
  publishes to PyPI through trusted publishing (`publish.yml`, environment
  `pypi`); the Windows build runs on every push to main and attaches its
  zip on the tag. The version lives in `bitcomposer/__init__.py` alone.
  First proven on `v1.0.0rc1`, a pre-release pip and pipx only install by
  exact version. The checklist is in `CONTRIBUTING.md`.
- **Linux install (done, branch `companion-path`, to verify on Troy's
  machine).** `pipx install bitcomposer` is the user's path. The companion
  (KDE Plasma 6, Debian-style paths, the scope for 1.0) runs `bitcomposer`
  on PATH and falls back to `python3 -m bitcomposer.cli`; the installer's
  `--dev` keeps the checkout on the import path (a `.pth` and a daemon
  drop-in) for development, and `--check` reports which generator plays.
  `docs/INSTALL.md` is rewritten around that.
- **Docs.** README install section (pipx, Windows zip, developer clone, the
  tkinter line) done; the listening page is regenerated at the tag.
- **The player (1.x), one program on both platforms.** Decided
  2026-10-18: rather than a KDE widget on Linux and a separate window on
  Windows, one player program with the widget's features and layout
  (auto-generate on track end, live mixer and ECHO bus, KEEP and prune,
  shuffle, gain, the readout of what the song drew) runs on both.
  - **One package.** The player lives in the `bitcomposer` package next to
    the generator, stdlib-only like it: tkinter for the window, libopenmpt
    through the ctypes code the daemon already has, audio out through
    ctypes as well (waveOut on Windows, paplay or ALSA on Linux). Generator
    and player are one version released by one tag, so there is nothing
    for an install to pull separately: a generator change reaches users
    when they upgrade the player, and the song message records which
    version wrote each file.
  - **Install and upgrade.** Linux: `pipx install bitcomposer`, then
    `bitcomposer-player --install-desktop` once for the app-menu entry;
    upgrade with `pipx upgrade bitcomposer`. Windows: the release zip,
    later an installer; the player checks GitHub releases and says when a
    newer one exists. PyPI stays the one source every install is made
    from. Later, only if wanted: a winget manifest (Windows gets
    `winget upgrade`) and a Flatpak (the software centre's update button),
    both packaging over the same package.
  - **Order.** 1.1: the engine lifted out of the daemon into
    `bitcomposer/player/` (module loading, mixing, channel volumes, the
    prune and KEEP rules, auto-generate; no D-Bus in it), the window on
    top of it with the widget's layout, the `bitcomposer-player` entry
    point, the Windows build bundling libopenmpt's DLL, the update check.
    Windows first: the window exists there and the player part does not.
    1.2: the daemon re-based on the same engine so the widget and the
    player share one implementation; the Plasma widget becomes an optional
    front end; then the keep-or-retire call. `companion/install.sh` exists
    as long as the widget does.
  - **Developing it.** Run the player from the checkout
    (`python3 -m bitcomposer.player`), the way the generator is developed;
    no `.pth` and no `--dev`, since the player is not a system service.
  - **Open choice, made when 1.1 starts.** tkinter keeps the
    zero-dependency promise and ships sooner but looks plainer than the
    widget; Qt through PySide6 looks like a desktop app and costs a
    150 MB dependency on every install. The engine is the same either way.

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
- **Harmony rework (1.0.0 blocker, 2026-10-17; merged 2026-10-18 after the
  listen).** Troy: the harmonies are the
  weakest part and fixing them lifts everything. The week's measurements
  listed five failings in order of damage; what was found and done:
  1. **One voice is not a chord.** The thin voicing was one channel and the J
     arpeggio; and under every stab a per-tick volume slide (D02) had the
     note silent 250 ms after its attack, so Strike of the Factory's strings
     swelled for 100 ms and were gone by 260 ms (measured on the part alone),
     warbling. Thin is now two real voices, full three, no J; the voicing
     rule keeps a chord's colour tone in (a two-voice pad is a tenth, a
     two-voice brass a sixth or a third).
  2. **Voice and mode.** A stab's hold comes from the voice: its family's
     length or three times its measured attack, in rows at the tempo, no
     slide, a note-off into the release. A struck voice never draws the
     sustain mode (this also closes the orchestra-hit item below).
  3. **Register and spacing.** Per family: pads, strings, choir low and wide
     (lowest voice C3-D3, the top a tenth up), brass and guitars a close
     triad at 196-330 Hz, the top voice under the lead's lower quartile per
     pattern.
  4. **Level per family.** Measured: every harmony-pool preset on one chord
     figure through ebur128 lands within 1.5 dB across the sustaining
     families, so the family table is flat except brass (2 dB by ear) and
     struck voices (+1 dB). What was wrong was the whole part: with real
     voices holding, the harmony channels at 25 put a strings chord's hits
     at the lead's level; at 9 the review set sits 6 to 10 dB under the lead
     (momentary loudness, 95th percentile); a hit shorter than the ear's
     200 ms integration is written up by the square root of the ratio, so
     the one-row chug lands with the held chords.
  5. **The counter-line** has the third harmony channel and its own level
     (32 against the lead's 42), no chord fade.
  Open after the listen: the brass trim is still a by-ear number (K-weighted
  loudness says brass is not louder; if it still reads forward the next
  measurement is its spectrum at the new register); the 200 ms hit rule;
  whether thin stabs want three voices on some packs.
- **Register plan (branch `register-plan`, 2026-10-18, under review by
  ear).** Troy heard the lead as piercing after the octave fix of the
  17th: measured, the lead had gone up an octave with the fix (medians
  269-320 Hz before, 523-640 after) while the bass and the harmony were
  re-derived downward and the lead was not. On a page with the lead a
  fifth down and an octave down, Troy chose the fifth (medians 349-453
  Hz) on every song. Doing that alone would have been a patch on a
  bigger problem: each part placed itself from its own numbers and
  pairwise rules kept them apart, so lowering the lead let the
  chord-under-the-lead cap drag Northern Dawn's brass back into the
  147-262 Hz band it had been moved out of (half its chords re-voiced,
  top 370 → 262 Hz). The plan (`registers.py`) places the parts once per
  song, in order: the chord in its family's register, never pushed; the
  lead in its voice's range (53-76 until a voice has a measured one), its
  window's floor at most four semitones under the chord's top anchor,
  its phrases starting above it; the counter-line in the lead's window.
  The cap is gone. Measured over the review set: chord registers
  unchanged from the harmony page; lead medians 415-480 Hz by sound;
  rows with the lead under the chord's top voice 0-18% (the fifth-down
  page had up to 34%). The phrase floor turned out a weak lever (it
  binds only in the lowest-energy sections; the window's floor does the
  work); kept, and said so. Tried and reverted the same day: per-voice
  lead windows from the packs' SPC traces (`voices.py` in each
  `*-spc/tools`: the sample's fundamental times the DSP pitch register,
  per voice slot, per snapshot). The traces put the games' flutes,
  whistles and synth leads an octave or more above the plan's window
  (FFVI flute 1 median 1763 Hz over 28 uses, Mana flute 881, Evermore
  strings 1104) and leave harp, bell and marimba where the plan has
  them; on a page with the leads placed there, Troy: way too high. Two
  reasons it does not transfer: a snapshot's voice slots do not say
  which one is the melody, so doublings, trills and chord tops pull the
  medians up; and our leads are fuller stacks than the games' thin
  samples, played denser, so the same register pierces where theirs did
  not. The SNES Gaussian filter is not the difference: it softens a
  sample relative to its own rate and that shape moves up with the
  pitch. The traces stay in the diags as the target for the
  voice-fidelity work (the "spectrum at the register" item): when a
  lead's spectrum matches the game's at the game's register, its traced
  window becomes usable, one voice at a time. Still ahead in this item:
  the bass and the arp join the plan.
- **Orchestra hit under sustain harmony (1.x).** The
  Mega Man X orchestra hit is a one-shot in the harmony pool; drawn with the
  sustain mode it leaves gaps between hits. Restrict it to the stab and chug
  modes, the way the mode-fit rule already steers slow voices away from the
  rhythmic modes.
- **The Evermore 'oo' choir is the one voice built without a measurement**:
  William Kage's set shows a long vocal sample none of the 72 snapshots holds
  whole. The recipe stays as designed by ear; if the sample turns up in
  another set, profile it the usual way.
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
- **Windows player.** See "The player" under Release above: one program
  on both platforms, Windows first.
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
