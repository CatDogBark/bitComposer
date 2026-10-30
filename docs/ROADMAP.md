# Roadmap

What is worth doing next, in the order it would be heard. Items are
recorded here when they come up so they are not lost; nothing here is
promised. See `ANALYSIS.md` for how changes are judged (measure first, ear
second), `CHANGELOG.md` for what has shipped, and `VISION.md` (at the top
of the repository) for where it is all heading.

## Release (1.0.0, shipped 2026-10-18)

Decided 2026-10-18. The product is the player: a program that generates
while you listen, the way the Plasma widget did, on Linux and Windows.
Only developers want the generator alone, so 1.0.0 ships with the player
(branch `player`), not after it. The window was tkinter at first, to keep
the package dependency-free; it is Qt since 2026-10-18 (see The player,
below).

- **Pipeline (done, branch `release-pipeline`).** A `v*` tag builds the
  sdist and wheel, checks the tag against `bitcomposer.__version__`, and
  publishes to PyPI through trusted publishing (`publish.yml`, environment
  `pypi`); the Windows build runs on every push to main and, on the
  tag, makes the GitHub release with the installer and the zip. The version lives in `bitcomposer/__init__.py` alone.
  First proven on `v1.0.0rc1`, a pre-release pip and pipx only install by
  exact version. The checklist is in `CONTRIBUTING.md`.
- **Linux install (done).** `pipx install bitcomposer` is the user's path;
  the player's first launch adds its menu entry. (The widget's installer
  and its `docs/INSTALL.md` went with the widget in 1.0.0rc3.)
- **Docs (done 2026-10-18).** README (install, the player, Windows, the
  code signing policy, privacy, contact), CONTRIBUTING, PORTABILITY and
  ANALYSIS (the release listen as §2e) brought up to 1.0.
- **Release candidates.** rc3 (the Qt player, media keys, start at login,
  the widget retired) and rc4 (the fixes from testing rc3 on Plasma and
  Windows, and GNOME, tested on GNOME Shell 50). Trying rc4's UPDATE
  button on Linux found it doing nothing: the check for a pipx install
  followed the venv's python link to the system python and decided the
  player was not pipx's. rc5 fixes it and puts an update screen over the
  window showing what the update is doing (pipx's own output on Linux; on
  Windows the download, then the installer's own progress window; rc3 to
  rc4 on Windows worked). An rc3 or rc4 install on Linux takes rc5 by
  hand once (`pipx install --force`). rc6 (the dead-code pass, no song
  changed; the tkinter window retired) was the update screen's first real
  run, rc5 to rc6 through the button on both platforms; 1.0.0 followed the
  same day.
- **Code signing.** Applied to the SignPath Foundation's open-source
  programme (2026-10-18); 1.0.0 ships unsigned, and signing joins the
  Windows build in a 1.0.x once it is approved (the workflow's Azure
  wiring stays dormant). The UPDATE button then checks a downloaded
  installer's signature before running it.
- **The player (1.0.0, branch `player`), one program on both platforms.**
  Decided 2026-10-18: rather than a KDE widget on Linux and a separate
  window on Windows, one player program with the widget's features and
  layout (auto-generate on track end, live mixer and ECHO bus, KEEP and
  prune, shuffle, gain, the readout of what the song drew) runs on both.
  Built: `bitcomposer/player/` (engine, window, libopenmpt and audio
  bindings), the Windows installer, the desktop entry. Verified headless
  in the tests; the window on Plasma and GNOME and the installer on
  Windows are checked by hand.
  - **One package.** The player lives in the `bitcomposer` package next to
    the generator: Qt for the window (below), libopenmpt through ctypes, audio
    out through the standard library
    (waveOut on Windows, paplay or ALSA on Linux). Generator
    and player are one version released by one tag, so there is nothing
    for an install to pull separately: a generator change reaches users
    when they upgrade the player, and the song message records which
    version wrote each file.
  - **Install and upgrade.** Linux: `pipx install bitcomposer`, then
    one `bitcomposer-player` from a terminal, which adds the app-menu
    entry itself (pip and pipx run nothing at install time; desktop.py).
    Windows: the installer from the release page (per-user, listed in
    Installed apps with its uninstaller), or the zip. On both the player
    checks GitHub releases, and its UPDATE button installs a newer one:
    `pipx install --force` of the new version on Linux, the new installer
    run silently on Windows, which reopens the player. PyPI stays the one
    source every Linux install is made from. Later, only if wanted: a
    winget manifest (Windows gets `winget upgrade`) and a Flatpak (see
    Player, below), both packaging over the same package.
  - **Developing it.** Run the player from the checkout
    (`python3 -m bitcomposer.player`), the way the generator is developed;
    no `.pth` and no `--dev`, since the player is not a system service.
  - **The window is Qt (decided 2026-10-18).** The first window was
    tkinter: plain, with a fixed 520x640 minimum and pixel-sized sliders,
    so at 1920x1080 and 150% (1280x720 logical) it ran off the screen.
    PySide6 was chosen, as a required dependency (PySide6-Essentials,
    ~80 MB download, 250 MB installed): a clone still runs the generator
    with nothing installed. The window (`player/qml/Main.qml`) is the
    widget's QML ported to plain QtQuick, its D-Bus polling replaced by a
    QObject over the engine (`player/backend.py`); sizes are logical
    pixels, the window opens no taller than its screen and scrolls, option
    rows wrap, Ctrl +/- zooms. JetBrains Mono ships in the package (SIL
    Open Font License 1.1). Tray icon (close keeps playing), one instance (a second launch
    shows the first). `bitcomposer-player --screenshot out.png --screen
    1920x1080 --scale 1.5 [--panels settings,mix]` renders it offscreen;
    the Windows build renders six setups from the frozen executable on
    every push. Windows build is a PyInstaller folder (onedir) so Qt
    starts at once; the installer is per-user by default and UPDATE runs
    it silently and relaunches.
  - **Media keys and start at login (done 2026-10-18).** MPRIS on Linux
    (`player/mpris.py`, jeepney rather than QtDBus: clients check the
    types, which PySide's variant conversion does not write exactly),
    RegisterHotKey on Windows (`player/mediakeys_win.py`, not yet tried on
    a real Windows desktop), start at login in the tray
    (`player/autostart.py`: XDG autostart, the per-user Run key) from
    SET → PLAYER or the tray menu. Windows has no SMTC entry yet (the
    volume flyout's media card); that is a WinRT job for later.
  - **The widget retired (1.0.0rc3).** The player does what the daemon
    did for the widget, so `companion/` (the Plasma widget, the D-Bus
    daemon, the helper scripts and their installer) and `docs/INSTALL.md`
    are gone.

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
  a `layout:` line in the song message, one ECHO bus fader in the mixer
  with an expand to LEAD / HARM / ARP, and `--echo-wet`. Stage three
  (done): per-song delay (eighth, dotted eighth or quarter, weighted by
  tempo), feedback and wetness drawn per song, sends opened in thin
  sections and pulled back in the chorus, and bounce / centre stereo with
  a pan per tap. Left for later: echo on the drums as a rare choice
  (gated snare). The player's readout of the drawn settings is done.
- **Style packs.** An instrument set paired with arrangement habits
  (`bitcomposer/packs.py`): voices per role, weighted draws for tempo,
  energy, scale, harmony mode, bass, drums and echo, a counter-line voice,
  orchestral fills, channel trims, arp figure weights. `ffvi` (orchestral)
  `mana` (Secret of Mana: mallets and air, hand percussion, bouncy habits)
  and `evermore` (Secret of Evermore: pads, drone bass, breathy flute,
  sparse or no drums; the atmospheric set) and `megamanx` (Mega Man X: driven
  guitars, pulse synth, synth brass, riff bass, slap echo; read off the
  game's own sample bank) are done; Evermore covers the ambient ground, so no
  separate Metroid pack. All four are built from their games' SPC
  snapshots (every voice profiled and re-synthesised, echo from the DSP
  registers) and borrow nothing; see Pack revisions. Rock grooves of their own (double-time hats, kick
  patterns under riffs) are the kit revision's job. A pack is data;
  the engine gaps that stay: riff-based bass, a detuned two-channel pad.
- **Road Rash pack (Genesis; next new pack, asked for 2026-10-18).** The
  first pack on the genesis style, after four SNES ones: Road Rash's
  YM2612 rock (overdriven FM lead and rhythm guitars, a hard picked FM
  bass, fast tempos, DAC drums) is the Genesis sound at its loudest. The
  source works differently from the SPC packs: a Genesis score has no
  sample bank to decode, its instruments are FM patches, so the source is
  a VGM log of the chip's register writes (the community's VGM packs, e.g.
  vgmrips.net). Each instrument's patch (algorithm, feedback, and per
  operator TL, AR/DR/SR/RR, MUL, DT) is read off the writes and re-rendered
  through the genesis palette's feedback-FM renderer
  (`samples/genesis.py`, `_fm_render`, extended to four operators where a
  patch needs them) into samples of our own at C-5, the DAC drums profiled
  and re-synthesised; the repository ships parameters and our renders,
  never the rip. Habits to measure from the logs: tempo, the riff bass,
  power-chord rhythm guitar (two FM channels a fifth apart), the lead's
  register, drum density. The rock machinery exists from `megamanx`
  (riff bass styles, `power_chords`, riff-vamp intros), so the pack is
  mostly data plus the VGM reader and the patch renderer.
- **Your own packs (after 1.0, asked for 2026-10-18; the format and
  loader shipped in 1.1.0, `docs/PACKS.md`, `--pack-file`; done in 1.2.0:
  the player's PACKS panel, step 6 of the SPC import plan, with a pack
  shared as one zip, EXPORT and ADD).** A pack added
  without touching the code: a pack file the player lists in its PACKS
  panel, apart from the built-in sounds. A pack is mostly data already
  (voices per role, weighted habits, channel trims), so the work is a
  file format for the PACK table (JSON or TOML, read by the standard
  library) checked on load with messages that say what is wrong and
  where; voices named from the built-in set (any registered voice of the
  pack's palette) or the user's own samples (WAV through the standard
  `wave` module, with a base note and loop points, written into the
  module the way the synthesised voices are); and a pack folder that can
  be shared as one zip. Data only, never code: a pack someone sends
  cannot run anything. The built-in packs stay Python (their voices are
  recipes), and a user pack points at their voices by name. The SPC
  sample banks item below is the same loader with a game's snapshot as
  the sample source.
- **Harmony rework (1.0.0 blocker, 2026-10-17; merged 2026-10-18 after the
  listen).** From the listen: the harmonies are the
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
- **Register plan (merged 2026-10-18).** The lead was heard as piercing after the octave fix of the
  17th: measured, the lead had gone up an octave with the fix (medians
  269-320 Hz before, 523-640 after) while the bass and the harmony were
  re-derived downward and the lead was not. On a page with the lead a
  fifth down and an octave down, the fifth was chosen (medians 349-453
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
  them; on a page with the leads placed there, by ear: way too high. Two
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
  −32.0 LUFS against the lead at −27.8). By ear: manageable, still off.
  Next things to measure before changing anything: the synth brass's
  spectrum against the game's sample at the register it is now played in
  (the 3rd and 4th partials land at 700 Hz to 3 kHz), the chug gallop's
  note length against the voice (83 ms notes at 180 BPM), and whether the
  rhythm guitar should take the chug modes instead of the brass in this
  pack. Measure parts alone: zero the other channels' header volumes in a
  copy of the file, render, ebur128.
- **Pack revisions (done 2026-10-16).** The approved plan: one
  SOUND picker (done), then each pack rebuilt from its game's SPC snapshots
  so it borrows nothing and carries its own kit: `ffvi` (done, branch
  `ffvi-spc`: 35 own voices, echo from the DSP registers), `megamanx`
  (re-checked against Kage's named rips: 20 matched, five voices renamed,
  nine added; 23 own voices), `mana` (done,
  branch `mana-spc`: 25 own voices, no table exists so voices are named by
  measured character), `evermore` (done, branch `evermore-spc`: 22 own
  voices, seven matched William Kage's named rips by length at
  https://www.williamkage.com/snes_soundfonts/ , the rest by character), then a readout of the drawn song and a mixer
  regrouped by part with a KIT fold (done 2026-10-16: `voices:` and
  `drew:` lines in the song message, voice labels on the faders, the KIT
  bus; the player reads them since the widget retired). Method and tools: `~/diags/bitcomposer/ffvi-spc/
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
- **SPC import: a pack from a game's own files (planned 2026-10-18; the
  plan is `docs/SPC-IMPORT.md`; shipped in 1.1.0 as a developer preview:
  the reader, the emulator, built from source, SPC-to-IT and its measuring
  tool, `docs/drivers/` the record of what it converts; 1.1.1 converts 39
  games of 20 music drivers, its songs as SPC players play them; the
  emulator's wheels on PyPI, `bitcomposer-emu`, from `emu.yml`, and the
  Windows build carrying it, its executable running IMPORT's worker
  itself; 1.2.0 makes packs: the translator's readings, a thin first pack
  from a soundtrack, step 5, and the PACKS panel, step 6, importing a
  folder, a zip, or an .rsn, .rar or .7z through the machine's 7-Zip or
  unar (`docs/TRANSLATOR.md`, stages 1, 2 and 5); open: the generator
  writing the way the readings show, Generation below).** The import reads a soundtrack's `.spc`
  snapshots (samples, envelopes, echo); an SPC700 emulator runs the game's
  own music driver and logs what it tells the DSP; a translator turns the
  log into notes, roles and measured habits. Two outputs: an SPC-to-IT
  conversion, one to one (the translator's proof), and a pack the generator
  composes with, chosen in a PACKS panel of its own (beside MIX; imported
  packs stay out of SOUND's random draw). Getting and unpacking the files is the user's business; the repo
  ships the code, never the samples, and imported packs stay on the
  user's machine. Built on the pack file format (Your own packs, above).
  Supersedes the per-game role map once planned here: the emulated notes
  say which sample is the melody.
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

- **Write the way the soundtracks do (`docs/IDIOM.md`; phases 1 to 4 done
  as developer tools in 1.2.0rc2, phase 4's rounds 23 to 66 in 1.2.0rc3,
  the housekeeping and the measurements for phase 6 in 1.2.0rc4; phase 6,
  the writer as the generator, next: `docs/idiom/phase-6-generator.md`).** The idiom's plan took
  this over from the translator's stages 3 and 4 on 2026-10-20: the
  readers scored on ground truth (phase 1), one score of voices through
  the SNES back end (phase 2), the vocabulary as tables read from the
  readings (phase 3), and the writing from them, measured against Final
  Fantasy VI's own songs round by round and passed by ear (phase 4,
  2026-10-24: every written song nearest FFVI among 37 games' tables, no
  four-bar phrase a game's). Phase 5 puts the pack's second format in the
  product: import writes the tables beside the voices and the PACKS panel
  writes with them (the generation scopes decided 2026-10-23 in
  `docs/idiom/phase-5-packs.md`). After phase 5, Mega Man X as the
  writing's generalization test, its own pack and twenty songs judged by
  ear and against its songs (the owner's call, 2026-10-24): riffs without
  pause, where the ride cymbal and the drums changing every other bar
  wait. 1.2.0's imported packs carry a game's sound and only the
  habits the readings give straight, so a song from one is still
  arranged the generator's way, and measured against the game's own it
  shows (FFVI, 2026-10-19): an arp in every song where FFVI has one in 5
  of 69, no triplets where a fifth of FFVI's off-beat notes are, two or
  three pitch classes under the melody where FFVI has three or four,
  tunes repeating more (44 to 54 % of melody bars heard before, FFVI's
  29 %) and ranging less. Stage 3 has the
  generator write in voices, through the SPC converter's back end (the IT
  instruments item below comes with it); stage 4 makes the vocabulary
  anew from the readings: voicings, how chords move, rhythms per part,
  the melody's shapes, bass and drum patterns as played. Imported packs
  use it first; the built-in packs move over only when chosen. Saving
  each import's readings in the database waits for it (decided
  2026-10-20).
- **The generator writes IT instruments (a later version, with a listening
  review; decided 2026-10-18).** Today's songs are sample mode: release
  tails baked into the sample data (a sustain loop and a decaying copy
  after it), stab lengths as note cuts, swells as volume slides. It sounds
  right, but a tracker shows nameless samples with their fades printed
  into the waveform. IT instruments (the writer has them since the SPC
  converter, `it_format.ITInstrument`) would give named instruments with
  release envelopes in place of baked tails, the two-sample bass as one
  instrument with a keyboard split, smaller files, cleaner patterns, and,
  as an option, new-note actions so plucked harmony and arp notes ring
  into each other. Every song's bytes change, so it is a version of its
  own, judged by ear; the baked tails are reproduced by envelope where the
  sound must not move.

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

After 1.0.0: how the player reaches people and fits their desktop.

- **In KDE Discover and GNOME Software, through Flathub (later: when there
  is an audience; decided 2026-10-18).** The ask: GUI users find the
  player in their software centre and press Install, instead of a
  terminal and GitHub. Flathub is the one listing both centres show (on
  by default on Fedora, Mint, Pop!_OS, KDE neon, the Steam Deck; Ubuntu's
  App Center shows Snaps, a second listing if ever wanted). Not now: a
  listing pays off when people go looking, and nothing has been announced
  yet; and every release would ship through a second channel (Flathub's
  bot opens the manifest bump, still ours to review, and a sandbox break
  is ours to fix) while releases are this frequent. Do it when releases
  slow down, and before any announcement. Waiting costs nothing: the app
  ID `io.github.CatDogBark.bitComposer` belongs to the GitHub account
  (which also earns Flathub's verified mark).
  The work, when it comes: a manifest on the Qt for Python base app
  (`io.qt.PySide.BaseApp`) over the KDE runtime, libopenmpt built as a
  module, an audio output that works in the sandbox (the unknown: paplay
  and pw-cat may be missing, so possibly an output on the PulseAudio
  library through ctypes), AppStream metainfo with screenshots (the
  `--screenshot` mode makes them) and a content rating, the UPDATE button
  hidden under `FLATPAK_ID` (Flathub apps do not update themselves;
  desktop.py already skips its menu entry there), start at login through
  the Background portal (the sandbox cannot write an autostart file; GNOME
  then lists the player under Background Apps), the tray's and MPRIS's
  D-Bus names allowed, then Flathub's review, days to weeks and not ours
  to hurry. A Flatpak can also give GNOME's overview a search provider
  (type a song's title, play it), which a pipx install cannot (GNOME reads
  them from system folders). An AppImage is the lighter fallback (one
  download, no store, no review) if Flathub stalls.
- **Desktop extras (ideas, nobody asked).** Notifications for a new song
  with a skip action; KDE global shortcuts (GENERATE, KEEP) that rebind in
  System Settings, a KRunner search, a generation's progress in the
  notification area; the system's light or dark scheme and accent colour,
  after `Main.qml`'s colours are tokens (22 are written inline) and a
  light palette is designed. GNOME's media card shows only the standard
  transport buttons, so KEEP and GENERATE cannot go there.
- Social preview image for the repository (set in the repository's
  settings; the logo SVGs make one).
