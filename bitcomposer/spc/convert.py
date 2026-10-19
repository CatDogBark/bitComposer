"""
SPC to IT, one to one: the notes a driver plays, written as an Impulse
Tracker module that plays the game's own samples, in IT instrument mode so
it opens in a tracker as a tracker song.

Step 4 of docs/SPC-IMPORT.md, the translator's proof: hear it against the
original. The pieces:

- Rows are the driver's own clock when it can be: a driver acts on a timer
  tick, and when its key-ons land on one of the snapshot's running timers
  (Secret of Evermore's 50 Hz) and IT can run that fast (102 ticks a second
  at most), every note falls exactly on a row. Drivers that do enough work
  a tick that their key-ons land anywhere in it (FFVI's, Secret of Mana's),
  or that tick faster than IT can (Mega Man X's 125 Hz), get IT's finest
  grid instead, 100 rows a second: every note within 5 ms of its time.
  (Echo repeats of a held, looped tone stack in phase on the SNES chip, its
  delay exact; on a 10 ms grid, and with each player rounding its ticks to
  whole samples at its own rate, they stack or cancel by chance, so a held
  tone's echo can come out stronger or weaker than the original's, right
  on average. Choosing the row rate to fit the delay was tried and only
  worked where one player's rounding happened to agree.)
- One IT sample per SNES sample, its C5Speed set so the song's notes fall on
  whole semitones; what is left (a few cents) and every pitch write while a
  note sounds (vibrato, slides) become fine pitch slides, row by row. Each is
  filtered as the SNES chip's Gaussian interpolation colours it (an IT player
  interpolates almost ideally): the SNES's softness is in the samples.
- One IT instrument per sample and envelope setting, its volume envelope
  simulated from the ADSR or GAIN registers.
- Note volume and pan from the voice's volumes, side for side: the SNES
  chip sets each side's level on its own and an IT player pans linearly,
  so the IT volume is the two sides' sum, the pan the right side's share.
  Swells in the volume column; a key-off is a note cut (the SNES chip's
  release takes under 8 ms).
- A note whose envelope registers are written while it sounds (a driver
  releasing notes with a GAIN fade instead of a key-off, as Mega Man X's
  does, or swelling a held note, as Secret of Evermore's wind does) plays
  an instrument without an envelope, its whole envelope simulated through
  the writes and carried in the volume column row by row (with one tick a
  row, as fine as an IT envelope), and is cut where it falls silent.
- The echo as repeats: each echoing note again on a channel of its own, a
  delay (EDL x 16 ms) late, until the repeats fall below -30 dB (as far as
  IT's 64 channels allow, shared among the voices that send), the k-th at
  the echo volume
  times the feedback to the k-1 and the filter's gain through k passes,
  measured over the note's own spectrum (echo_gains), left and right as
  the echo volumes have them (in surround when their signs differ and the
  voice is near the middle: surround plays centred). The
  repeats play a copy of the sample coloured by the filter (echo_coloured):
  a filter that passes little bass makes a thin, bright echo, and a
  full-range copy at its level sounds like a second instrument.
- The master volume as global volume, the song's start in the header and
  each change (a driver's fade-out) on a channel of its own: with the
  volumes side for side, the module plays at the original's level. The
  song runs as an SPC player plays it, the tag's length and then its fade
  (most songs loop), and the module ends on its last row.
- Noise voices play the SNES chip's own noise, rendered at its output rate
  for each noise clock a song uses (each value held until the next step,
  as the hardware holds it), so nothing is resampled.
- Pitch modulation (a voice's pitch bent by the output of the voice below,
  at audio rate: an FM timbre, or a noise-shaken tone) as the emulator
  played it: the voice's own output through the note, recorded, one
  recording for each way such notes are played.

The echo's colour is right at one pitch per sample, its gain at every pitch.
The files stay the user's: a converted song holds the game's samples.

The work is in three parts. snes_chip.py is the SNES chip's sound
(envelopes, interpolation, echo, noise) from the registers a note carries;
it_song.py writes an IT song on a row grid and knows nothing of the SNES;
this file decides how IT carries the one, in stages that each build on
the last: the samples, the instruments, the pitch-modulation recordings,
the echo's channels, the echo's coloured copies, then every note and its
repeats, then the master volume. IT's 255 samples and 99 instruments go
in that order: first the notes' own, then the recordings, then the copies.
"""
import bisect
import math
import struct
from array import array
from dataclasses import dataclass, field

from .. import it_format as itf
from . import RATE, brr, it_song, snes_chip, notes as notes_mod
from .emulate import CLOCK, run as emulate_run
from .it_song import KEYS, MAX_CHANNELS, MAX_INSTRUMENTS, MAX_SAMPLES, MAX_TICK_RATE, Line

FINE_GRID = 100.0                     # rows a second when the driver's clock cannot be the grid
ALIGNED = 0.6                         # how closely key-ons must line up with a timer to be its ticks
TAPS = 24                             # echo repeats a voice can have, at most
QUIET = 1 / 32                        # an echo repeat quieter than this against its note (-30 dB) is left out
CENTRED = 0.7                         # a voice this close to the middle (quieter side / louder) can play centred
ROWS_PER_PATTERN = it_song.ROWS_PER_PATTERN   # tools/spc_check.py reads it here


def tick_rate(snap, writes) -> tuple[float, float]:
    """The driver's clock: of the timers the snapshot has running, the one
    whose period the key-on writes line up with best, as (Hz, how well
    they line up: 0 none, 1 exactly)."""
    ram = snap.ram
    control = ram[0xF1]
    candidates = []
    for t in range(3):
        if control >> t & 1:
            target = ram[0xFA + t] or 256
            candidates.append((16 if t == 2 else 128) * target)
    kons = [w.cycle for w in writes if w.reg == notes_mod.KON and w.value]
    best, best_r = None, 0.0
    for period in candidates:
        if len(kons) < 4:
            break
        c = sum(math.cos(2 * math.pi * k / period) for k in kons)
        s = sum(math.sin(2 * math.pi * k / period) for k in kons)
        r = math.hypot(c, s) / len(kons)
        if r > best_r:
            best, best_r = period, r
    return (CLOCK / best, best_r) if best else (0.0, 0.0)


def _keeps_pace(hz: float, seconds: float) -> bool:
    """Whether IT's rows can run on the driver's clock through the song: IT's
    tempo comes in steps of 0.4 rows a second, and rows off the clock fall
    behind it as the song goes (Factor 5's 62.5 Hz on 62.4 rows lost 0.1 s
    in a song, Jurassic Park 2's 49.38 Hz on 49.2 up to 2 s). Within half a
    row over the song, they do; else the fine grid, which runs exactly."""
    _, row_hz = it_song.tempo_for(hz)
    return abs(hz / row_hz - 1) * seconds < 0.5 / row_hz


def envelope(adsr1: int, adsr2: int, gain: int, tick_hz: float, seconds: float = 20.0) -> list[tuple[int, int]]:
    """The SNES chip's envelope for these registers, in IT envelope nodes:
    (tick, level 0-64), at most 25, the level held after the last."""
    return it_song.envelope_nodes(snes_chip.envelope_ticks(adsr1, adsr2, gain, tick_hz, it_song.ENV_TOP, seconds))


def _row_means(track, bounds) -> list[float]:
    """The RMS level of a breakpoint track over each [bounds[i], bounds[i+1])
    (as envelope() keeps its ticks)."""
    out, j = [], 0
    for a, b in zip(bounds, bounds[1:]):
        while j + 1 < len(track) and track[j + 1][0] <= a:
            j += 1
        total, k, x = 0.0, j, a
        while x < b:
            seg = min(b, track[k + 1][0]) if k + 1 < len(track) else b
            total += track[k][1] ** 2 * (seg - x)
            x = seg
            k += 1
        out.append(math.sqrt(total / (b - a)) if b > a else float(track[j][1]))
    return out


def _noise_sample(rate: int) -> itf.ITSample:
    """The SNES chip's noise at noise clock `rate` (snes_chip.noise), a
    second of it looped."""
    data = struct.pack(f"<{RATE}h", *snes_chip.noise(rate))
    return itf.ITSample(name=f"Noise, clock {rate}", filename=f"noise{rate}", data=data, length=RATE, loop=True,
                        loop_start=0, loop_end=RATE, c5_speed=RATE)


def _loop(s) -> tuple[int, int] | None:
    """A decoded sample's loop as (start, end), or None for a one-shot."""
    return (s.loop_start, s.loop_end or len(s)) if s.loops else None


def _sends(n) -> bool:
    """Whether a note sends to the echo, and the echo is heard."""
    return n.echo and n.echo_writes and n.echo_delay > 0


def _sends_at_once(n) -> bool:
    """Whether a note sends to an echo of delay 0 that is heard: a tone
    control on it rather than an echo (snes_chip.echo_response)."""
    return n.echo and n.echo_writes and n.echo_delay == 0 and any(n.echo_volume) and any(n.echo_filter) and not n.noise


def _at_once_sign(n) -> int:
    """-1 where both echo volumes are negative: an echo of delay 0 sounds with
    the note, so its sign counts, and its copy is inverted."""
    return -1 if max(n.echo_volume) < 0 else 1


def _instrument_key(n):
    """Notes with the same key play one instrument: the same sample (or noise
    clock) and envelope setting. A note whose driver rewrites its envelope as
    it sounds plays the sample's instrument without an envelope (its envelope
    is carried whole in the volume column)."""
    what = ("noise", n.noise_rate) if n.noise else n.brr
    if n.envelopes:
        return (what, None, None)
    return (what, n.adsr, n.gain if not n.adsr[0] & 0x80 else 0)


def _loudness(left, right, gl, gr):
    """(IT volume, IT pan or None) for voice volumes scaled by gains. The
    SNES chip sets each side's level on its own (volume / 128); an IT
    player pans linearly, a centred note at half its volume each side,
    so the IT volume is the two sides' sum over 128 (in 0-64), the pan
    the right side's share."""
    l, r = abs(left) * gl, abs(right) * gr
    vol = max(0, min(64, round((l + r) / 2)))
    pan = round(255 * r / (l + r)) if l + r > 0 else None
    return vol, pan


class _Master:
    """The SNES chip's master volume through the song (notes.master_volume)."""

    def __init__(self, snap, writes):
        self.changes = notes_mod.master_volume(snap, writes)
        self.times = [t for t, _, _ in self.changes]
        self.lift = 1.0                  # what the global volume is raised by (_Song.lift)

    def at(self, t: float) -> tuple[int, int]:
        _, left, right = self.changes[max(0, bisect.bisect_right(self.times, t) - 1)]
        return left, right

    def start(self) -> int:
        """The song's start, as the IT global volume (1-128)."""
        _, left, right = self.changes[0]
        return max(1, min(128, round(max(abs(left), abs(right)) * self.lift)))

    def loudest(self) -> int:
        return max(1, max(max(abs(left), abs(right)) for _, left, right in self.changes))

    def past(self, t: float) -> float:
        """What an echo repeat at time t is raised by. The master volume (volume
        / 128, as the voices') is the IT global volume, but the SNES chip leaves
        the echo out of it (output = dry x master + echo x echo volume), and a
        global volume reaches every channel: so a repeat is raised by as much as
        the master volume lowers it (at FFVI's 63 the echo came out at half its
        strength). At least 8, so an echo under a silenced master cannot blow up."""
        left, right = self.at(t)
        return 128 / max(8, min(128, max(abs(left), abs(right))))


@dataclass
class _Song:
    """What a conversion's stages build, each from what the ones before built."""
    snap: object
    run: object                       # the emulator's run, the song's length
    notes: list                       # the notes that sound (notes.decode)
    row_hz: float
    master: _Master
    samples: list = field(default_factory=list)              # IT samples, numbered from 1 in this order
    instruments: list = field(default_factory=list)          # IT instruments, the same
    sample_of: dict = field(default_factory=dict)            # BRR addresses -> IT sample
    noise_sample: dict = field(default_factory=dict)         # noise clock -> IT sample
    decoded: dict = field(default_factory=dict)              # BRR addresses -> the sample as the voice reads it
    offset: dict = field(default_factory=dict)               # BRR addresses -> semitones its C5Speed sits off 32 kHz
    instrument_of: dict = field(default_factory=dict)        # _instrument_key -> IT instrument
    baked_of: dict = field(default_factory=dict)             # id(note) -> (instrument, key) of its recording
    unbaked: int = 0                                         # pitch-modulated notes IT had no room to record
    off_keys: int = 0                                        # notes no octave of their sample's brings onto IT's keys
    echo_channels: dict = field(default_factory=dict)        # voice -> its repeats' channels
    taps: int = 0                                            # repeats each sending voice has
    copies: int = 0                                          # echo-coloured copies a sample has (later repeats play the last)
    echo_instrument_of: dict = field(default_factory=dict)   # (_instrument_key, k) -> IT instrument of copy k
    coloured_at: dict = field(default_factory=dict)          # (BRR addresses, k) -> (semitone, filter, fit) of copy k
    at_once_instrument_of: dict = field(default_factory=dict)   # (key, filter, feedback, sign) -> IT instrument of a delay-0 echo's copy
    at_once_colour: dict = field(default_factory=dict)       # (sample, filter, feedback, sign) -> (semitone, fit) of that copy
    responses: dict = field(default_factory=dict)            # (filter, feedback) -> a delay-0 echo's response
    gains_of: dict = field(default_factory=dict)             # echo_gains, once each
    factors_of: dict = field(default_factory=dict)           # id(note) -> its envelope through its rows
    lift: float = 1.0                                        # channel volumes over it, the global volume times it

    @property
    def samples_left(self) -> int:
        return MAX_SAMPLES - len(self.samples)

    @property
    def instruments_left(self) -> int:
        return MAX_INSTRUMENTS - len(self.instruments)

    def end_of(self, n) -> float:
        return n.end if n.end is not None else self.run.seconds

    def it_semis(self, n, pitch: int) -> float:
        """Where a pitch falls on the IT note scale, on the note's sample."""
        if n.noise:
            return 60.0                  # its own sample, at the output rate
        return 60 + 12 * math.log2(pitch / 0x1000) - self.offset[n.brr]


def convert(snap, seconds: float | None = None, path: str | None = None, fade: float = 0.0) -> dict:
    """Convert a snapshot: run its driver, write the IT (to `path` if given).
    Returns the song dict write_it_file takes, with a summary in "info".
    Without `seconds`, the song as an SPC player plays it: the tag's length,
    then its fade (most songs loop, and a player fades them out); with it,
    that long, faded over its last `fade` seconds. The module ends where the
    song does."""
    if seconds is None:
        fade = (snap.tags.fade_ms or 0) / 1000
        seconds = float(snap.tags.length_s or 90) + fade
    fade = max(0.0, min(fade, seconds))
    run = emulate_run(snap, seconds)
    found = []
    for n in notes_mod.decode(snap, run.writes, keyons=run.keyons):
        if not n.pitch and not n.noise and n.bends:
            n.pitch = n.bends.pop(0)[1]  # keyed at pitch 0, its pitch written just after (EarthBound's sweeps up)
        if n.pitch or n.noise:
            found.append(n)
    for n in found:                      # what each note played: the SNES chip's own reading, else the snapshot's
        if n.brr is None and not n.noise:
            n.brr = snap.entry(n.sample)
    hz, aligned = tick_rate(snap, run.writes)
    on_ticks = aligned >= ALIGNED and 0 < hz <= MAX_TICK_RATE and _keeps_pace(hz, run.seconds)
    tempo, row_hz = it_song.tempo_for(hz if on_ticks else FINE_GRID)

    song = _Song(snap, run, found, row_hz, _Master(snap, run.writes))
    _lift(song)
    _add_samples(song)
    _add_instruments(song)
    _bake_pitch_modulation(song, seconds)
    channels = _plan_echo(song)
    _add_echo_copies(song)
    _add_at_once_copies(song)
    grid = it_song.Grid(run.seconds, row_hz, channels)
    placed, repeats, baked = _place_notes(song, grid)
    _master_channel(song, grid, channels - 1, fade)

    t = snap.tags
    message = "\r".join([
        f"{t.title or 'SPC'}{' - ' + t.game if t.game else ''}{' - ' + t.artist if t.artist else ''}",
        "Converted from an SPC snapshot by bitComposer: the game's own samples and the notes its",
        "driver played, one to one, the echo as repeats on channels of their own,",
        "pitch-modulated notes as the emulator played them.",
        (f"rows on the driver's clock, {hz:.2f} Hz" if on_ticks else
         f"rows at {row_hz:.0f} a second (the driver's key-ons do not sit on a tick IT can run)") + f"; {placed} notes ({baked} pitch-modulated), {repeats} echo repeats",
    ])
    samples, instruments = song.samples, song.instruments
    out = {"name": (t.title or "SPC")[:25], "samples": samples, "patterns": grid.patterns,
           "global_volume": song.master.start(), "orders": list(range(len(grid.patterns))), "tempo": tempo, "speed": 1,
           "instruments": instruments, "message": message,
           "info": {"notes": placed, "repeats": repeats, "channels": channels, "echo_channels": song.echo_channels,
                    "fade": fade, "baked": baked, "unbaked": song.unbaked, "off_keys": song.off_keys, "lift": song.lift,
                    "bakes": sum(1 for smp in samples if smp.filename.startswith("pmon")), "tick_hz": hz,
                    "aligned": aligned, "on_ticks": on_ticks, "row_hz": row_hz,
                    "samples": len(samples), "instruments": len(instruments), "seconds": run.seconds}}
    if path:
        it_song.write(path, out)
    return out


# The stages ----------------------------------------------------------------

def _add_samples(song: _Song) -> None:
    """One IT sample per SNES sample played (by its addresses), as the SNES
    chip's interpolation colours it, its C5Speed on the song's semitone
    lattice; one per noise clock a song uses."""
    for addr in sorted({n.brr for n in song.notes if not n.noise}):
        s = brr.decode(song.snap.ram, *addr) if 0 < addr[0] < 0xFFC0 else None
        if s is None or len(s) < 16:
            continue
        s.pcm = snes_chip.snes_interpolated(s.pcm, _loop(s))       # from here on, the sample as the voice plays it
        song.decoded[addr] = s
        fracs = [12 * math.log2(n.pitch / 0x1000) for n in song.notes if n.brr == addr and not n.noise and n.pitch]
        ang = [2 * math.pi * (f - math.floor(f)) for f in fracs]
        mean = math.atan2(sum(map(math.sin, ang)), sum(map(math.cos, ang))) / (2 * math.pi) if ang else 0.0
        # Whole octaves on top, so the sample's notes fall on IT's keys, 1-119 (a cell's note 0,
        # C-0, reads as none): DKC2's bass plays five octaves under its sample's rate. The
        # octaves that place the most of them (none where that is as many), so one note off
        # the rest (a sweep up from near 0) does not push the others off the top.
        if fracs:
            on_keys = lambda k: sum(1 <= round(60 + f - mean + 12 * k) <= 119 for f in fracs)   # noqa: E731
            mean -= 12 * max(range(-10, 11), key=lambda k: (on_keys(k), -abs(k)))
        song.offset[addr] = mean                            # semitones the C5Speed sits off 32 kHz
        data = s.pcm.tobytes() if s.pcm.itemsize == 2 else array("h", s.pcm).tobytes()
        song.samples.append(itf.ITSample(name=f"SNES sample at {addr[0]:04X}", filename=f"brr{addr[0]:04x}", data=data,
                                         length=len(s), loop=s.loops, loop_start=s.loop_start or 0,
                                         loop_end=s.loop_end or len(s), c5_speed=max(1, round(RATE * 2 ** (mean / 12)))))
        song.sample_of[addr] = len(song.samples)
    for rate in sorted({n.noise_rate for n in song.notes if n.noise and n.noise_rate}):
        song.samples.append(_noise_sample(rate))
        song.noise_sample[rate] = len(song.samples)


def _add_instruments(song: _Song) -> None:
    """One instrument per sample and envelope setting, its volume envelope
    simulated from the ADSR or GAIN registers; one per sample without an
    envelope for notes whose driver rewrites the envelope as they sound."""
    for n in song.notes:
        key = _instrument_key(n)
        if key in song.instrument_of or (n.brr not in song.sample_of if not n.noise else n.noise_rate not in song.noise_sample):
            continue
        if song.instruments_left <= 0:
            continue
        nodes = [] if key[1] is None else envelope(n.adsr[0], n.adsr[1], n.gain, song.row_hz)
        sample = song.noise_sample[n.noise_rate] if n.noise else song.sample_of[n.brr]
        label = "noise" if n.noise else f"sample {n.brr[0]:04X}"
        kind = "no env" if key[1] is None else f"env {len(song.instruments) + 1}"
        song.instruments.append(itf.ITInstrument(name=f"{label} {kind}", sample=sample, envelope=nodes))
        song.instrument_of[key] = len(song.instruments)


def _bake_pitch_modulation(song: _Song, seconds: float) -> None:
    """Pitch modulation: a note whose pitch the voice below it bent (PMON) is
    kept as the emulator played it, the voice's own output through the note
    (after its envelope, before its volumes), since IT cannot bend a pitch at
    audio rate. Notes played alike (the same sample, pitch, envelope, bends,
    and the same notes below them, as far as they overlap) share one
    recording, the longest. The recordings sit on the keyboards of
    instruments of their own, KEYS to an instrument, each key playing its
    recording at its own rate."""
    modulated = [n for n in song.notes if n.pmon and not n.noise and n.voice > 0]
    if not modulated:
        return
    tapped = emulate_run(song.snap, seconds, taps=sum({1 << n.voice for n in modulated})).tapped
    below = {}
    for n in song.notes:
        below.setdefault(n.voice + 1, []).append(n)
    end_of = song.end_of

    def played_alike(n):
        return (n.brr, n.pitch, n.adsr, n.gain, tuple(p for _, p in n.bends), tuple(e[1:] for e in n.envelopes),
                tuple((round(m.start - n.start, 2), m.brr, m.pitch, m.adsr, m.gain, m.noise, m.noise_rate,
                       tuple(p for _, p in m.bends), tuple(e[1:] for e in m.envelopes))
                      for m in below.get(n.voice, []) if m.start < end_of(n) and end_of(m) > n.start))

    groups = {}
    for n in modulated:
        groups.setdefault(played_alike(n), []).append(n)
    baked_ins = None
    for i, group in enumerate(sorted(groups.values(), key=len, reverse=True)):
        if song.samples_left <= 0 or (i % KEYS == 0 and song.instruments_left <= 0):
            song.unbaked += sum(len(g) for g in list(groups.values())[i:])
            break
        longest = max(group, key=lambda n: end_of(n) - n.start)
        out = tapped[longest.voice]
        pcm = out[max(0, round(longest.start * RATE) - 8):min(len(out), round(end_of(longest) * RATE) + snes_chip.RELEASE)]
        if not any(pcm):
            continue
        song.samples.append(itf.ITSample(name=f"voice {longest.voice} pitch-modulated", filename=f"pmon{i}",
                                         data=pcm.tobytes(), length=len(pcm), loop=False, c5_speed=RATE))
        if i % KEYS == 0:
            song.instruments.append(itf.ITInstrument(name=f"pitch-modulated {i // KEYS + 1}",
                                                     keyboard=[(k, 0) for k in range(120)]))
            baked_ins = len(song.instruments)
        key = 1 + i % KEYS
        song.instruments[baked_ins - 1].keyboard[key] = (60, len(song.samples))
        for n in group:
            song.baked_of[id(n)] = (baked_ins, key)


def _plan_echo(song: _Song) -> int:
    """The channels: the eight voices; for each voice that sends to the echo,
    its repeats, as many as the echo needs to fall to QUIET (a strong
    feedback rings for seconds: FFVI's Dark World, 0.78 at 80 ms, for about
    1.1 s) within IT's 64 channels; the master volume last. Returns how
    many."""
    sending = sorted({n.voice for n in song.notes if _sends(n) or _sends_at_once(n)})
    taps = 0
    if sending:
        needed = 1                       # an echo of delay 0 is one copy, on the first
        for ev, fb, filt in {(max(map(abs, n.echo_volume)), abs(n.echo_feedback), n.echo_filter)
                             for n in song.notes if n.voice in sending and not _sends_at_once(n)}:
            peak = snes_chip.echo_filter_peak(filt)
            loop = fb * peak
            k = TAPS if loop >= 1 else 1
            if loop < 1:
                while k < TAPS and ev * peak * loop ** (k - 1) >= QUIET:
                    k += 1
            needed = max(needed, k)
        taps = max(1, min(TAPS, needed, (MAX_CHANNELS - 9) // len(sending)))
    song.taps = taps
    song.echo_channels = {v: [8 + i * taps + k for k in range(taps)] for i, v in enumerate(sending)}
    return 8 + len(sending) * taps + 1


def _add_echo_copies(song: _Song) -> None:
    """The echo's colour and timing: for each sample an echoing note plays, a
    copy per repeat as the echo hands it back after that many trips round
    its loop (snes_chip.echo_coloured, at the pitch the sample's echoing
    notes mostly have), and an instrument for each beside each of the
    sample's own: as many repeats as the samples and instruments IT has left
    allow (the pitch-modulation recordings came first); later repeats play
    the last."""
    sends = [n for n in song.notes if _sends(n) and not n.noise and n.pitch]
    addrs = sorted({n.brr for n in sends if n.brr in song.sample_of})
    keys_of = {a: [key for key in song.instrument_of if key[0] == a] for a in addrs}
    if addrs and song.taps:
        song.copies = max(0, min(song.taps, song.samples_left // len(addrs),
                                 song.instruments_left // max(1, sum(map(len, keys_of.values())))))
    for addr in addrs if song.copies else []:
        echoing = [n for n in sends if n.brr == addr]
        semis = sorted(round(12 * math.log2(n.pitch / 0x1000)) for n in echoing)
        mid, filt = semis[len(semis) // 2], echoing[0].echo_filter
        s = song.decoded[addr]
        dry = song.samples[song.sample_of[addr] - 1]
        for k in range(1, song.copies + 1):
            data, fit = snes_chip.echo_coloured(s.pcm, _loop(s), 2 ** (mid / 12), filt, k)
            song.samples.append(itf.ITSample(name=f"echo {k} of {addr[0]:04X}", filename=f"e{k}{addr[0]:04x}",
                                             data=data.tobytes(), length=len(data), loop=dry.loop,
                                             loop_start=dry.loop_start, loop_end=dry.loop_end, c5_speed=dry.c5_speed))
            song.coloured_at[(addr, k)] = (mid, filt, fit)
            for key in keys_of[addr]:
                src = song.instruments[song.instrument_of[key] - 1]
                song.instruments.append(itf.ITInstrument(name=f"echo {k} {src.name}"[:25], sample=len(song.samples),
                                                         envelope=src.envelope))
                song.echo_instrument_of[(key, k)] = len(song.instruments)


def _at_once_response(song: _Song, filt, fb: float) -> list[float]:
    if (filt, fb) not in song.responses:
        song.responses[(filt, fb)] = snes_chip.echo_response(filt, feedback=fb)
    return song.responses[(filt, fb)]


def _add_at_once_copies(song: _Song) -> None:
    """For notes sending to an echo of delay 0: a copy of each sample (or
    pitch-modulation recording) they play as the echo's loop hands it back,
    every trip summed (snes_chip.echo_response), at the pitch they mostly
    have (a recording at its own rate, so exactly), each with instruments
    beside the sample's own, as far as IT's samples and instruments allow.
    Secret of Mana's Flammie Coming sends every voice to one; left out, its
    lows came out at half and it sounded bright."""
    groups = {}
    for n in song.notes:
        if _sends_at_once(n) and n.voice in song.echo_channels:
            what = ("baked",) + song.baked_of[id(n)] if id(n) in song.baked_of else n.brr
            groups.setdefault((what, n.echo_filter, n.echo_feedback, _at_once_sign(n)), []).append(n)
    for (what, filt, fb, sign), ns in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if song.samples_left <= 0 or song.instruments_left <= 0:
            break
        h = _at_once_response(song, filt, fb)
        if what[0] == "baked":
            _, baked_ins, key = what
            recording = song.samples[song.instruments[baked_ins - 1].keyboard[key][1] - 1]
            pcm = array("h")
            pcm.frombytes(recording.data)
            data, fit = snes_chip.echo_coloured(pcm, None, 1.0, filt, feedback=fb)
            mid = None
        elif what in song.sample_of:
            s = song.decoded[what]
            semis = sorted(round(12 * math.log2(n.pitch / 0x1000)) for n in ns)
            mid = semis[len(semis) // 2]
            data, fit = snes_chip.echo_coloured(s.pcm, _loop(s), 2 ** (mid / 12), filt, feedback=fb)
        else:
            continue
        if sign < 0:
            data = array("h", (max(-32767, -v) for v in data))
        if what[0] == "baked":
            song.samples.append(itf.ITSample(name=f"echo 0 of {recording.name}"[:25], filename=f"e0{recording.filename}"[:12],
                                             data=data.tobytes(), length=len(data), loop=False, c5_speed=recording.c5_speed))
            where = (("baked", baked_ins), filt, fb, sign)
            if where not in song.at_once_instrument_of:
                song.instruments.append(itf.ITInstrument(name=f"echo 0 of pitch-modulated"[:25],
                                                         keyboard=[(k, 0) for k in range(120)]))
                song.at_once_instrument_of[where] = len(song.instruments)
            song.instruments[song.at_once_instrument_of[where] - 1].keyboard[key] = (60, len(song.samples))
        else:
            dry = song.samples[song.sample_of[what] - 1]
            song.samples.append(itf.ITSample(name=f"echo 0 of {what[0]:04X}", filename=f"e0{what[0]:04x}", data=data.tobytes(),
                                             length=len(data), loop=dry.loop, loop_start=dry.loop_start,
                                             loop_end=dry.loop_end, c5_speed=dry.c5_speed))
            for key in sorted({_instrument_key(n) for n in ns if _instrument_key(n) in song.instrument_of}, key=str):
                if song.instruments_left <= 0:
                    break
                src = song.instruments[song.instrument_of[key] - 1]
                song.instruments.append(itf.ITInstrument(name=f"echo 0 {src.name}"[:25], sample=len(song.samples),
                                                         envelope=src.envelope))
                song.at_once_instrument_of[(key, filt, fb, sign)] = len(song.instruments)
        song.at_once_colour[(what, filt, fb, sign)] = (mid, fit)


def _at_once(song: _Song, n) -> tuple[int | None, float]:
    """(the instrument, the gain over the note's volumes) of a note's delay-0
    echo copy: its response's gain at the note's pitch over the copy's, and
    over the factor the copy was scaled down by to fit."""
    sign = _at_once_sign(n)
    if id(n) in song.baked_of:
        baked_ins, key = song.baked_of[id(n)]
        ins = song.at_once_instrument_of.get((("baked", baked_ins), n.echo_filter, n.echo_feedback, sign))
        colour = song.at_once_colour.get((("baked", baked_ins, key), n.echo_filter, n.echo_feedback, sign))
        return (ins, 1 / colour[1]) if ins and colour else (None, 0.0)
    ins = song.at_once_instrument_of.get((_instrument_key(n), n.echo_filter, n.echo_feedback, sign))
    colour = song.at_once_colour.get((n.brr, n.echo_filter, n.echo_feedback, sign))
    if not ins or not colour:
        return None, 0.0
    mid, fit = colour
    s = song.decoded[n.brr]
    h = _at_once_response(song, n.echo_filter, n.echo_feedback)
    key = ("at once", n.brr, n.pitch, n.echo_filter, n.echo_feedback)
    if key not in song.gains_of:
        song.gains_of[key] = snes_chip.echo_response_gain(s.pcm, _loop(s), n.pitch, h)
    mid_key = ("at once", n.brr, mid, n.echo_filter, n.echo_feedback)
    if mid_key not in song.gains_of:
        song.gains_of[mid_key] = snes_chip.echo_response_gain(s.pcm, _loop(s), round(0x1000 * 2 ** (mid / 12)), h)
    return ins, (song.gains_of[key] / song.gains_of[mid_key] / fit if song.gains_of[mid_key] else 0.0)


def _place_notes(song: _Song, grid: it_song.Grid) -> tuple[int, int, int]:
    """Every note on its voice's channel, and its echo repeats on theirs.
    Returns (notes placed, repeats placed, of the notes the recordings)."""
    placed = repeats = baked = 0
    for n in sorted(song.notes, key=lambda n: (n.start, n.voice)):
        if id(n) in song.baked_of:
            ins, note = song.baked_of[id(n)]
        else:
            ins = song.instrument_of.get(_instrument_key(n))
            if ins is None or (n.noise and not n.noise_rate):
                continue
            note = round(song.it_semis(n, n.pitch))
            if not 1 <= note <= 119:
                song.off_keys += 1
                continue
        if not _place(song, grid, n, n.voice, note, ins, 0, 1.0, 1.0, baked=id(n) in song.baked_of):
            continue
        placed += 1
        baked += id(n) in song.baked_of
        # The echo, as repeats: the k-th comes k delays late, at the echo
        # volume times the feedback to the k-1 and the filter's gain through
        # k passes, played from the copy that holds k passes of the filter
        # (its colour and its span) where there is one.
        if n.voice in song.echo_channels and _sends(n):
            gains, fb = _repeat_gains(song, n), abs(n.echo_feedback)
            ev = n.echo_volume
            # Echo volumes of opposite signs: surround inverts one side, but
            # plays centred, so only a voice near the middle keeps its place.
            sides = sorted((abs(n.volume[0]), abs(n.volume[1])))
            inverted = ev[0] * ev[1] < 0 and sides[1] > 0 and sides[0] / sides[1] >= CENTRED
            for k in range(1, song.taps + 1):
                kk = min(k, song.copies)
                echo_ins = song.echo_instrument_of.get((_instrument_key(n), kk))
                colour = song.coloured_at.get((n.brr, kk))
                if id(n) not in song.baked_of and echo_ins is not None and colour[1] == n.echo_filter:
                    mid_gain = _gains_at(song, n.brr, colour[0], n.echo_filter)[kk - 1]
                    passed = gains[k - 1] / mid_gain / colour[2] if mid_gain else 0.0
                else:
                    echo_ins, passed = ins, gains[k - 1]
                scale = passed * fb ** (k - 1) * song.master.past(n.start + k * n.echo_delay)
                gl, gr = abs(ev[0]) * scale, abs(ev[1]) * scale
                if inverted:
                    gl = gr = max(gl, gr)
                if max(gl, gr) < QUIET:
                    break
                shift = round(k * n.echo_delay * song.row_hz)
                if _place(song, grid, n, song.echo_channels[n.voice][k - 1], note, echo_ins, shift, gl, gr, inverted,
                          id(n) in song.baked_of):
                    repeats += 1
        # An echo of delay 0: one copy, on the note's own row, coloured by
        # every trip round the loop, at the echo volume.
        elif n.voice in song.echo_channels and _sends_at_once(n):
            echo_ins, passed = _at_once(song, n)
            ev = n.echo_volume
            sides = sorted((abs(n.volume[0]), abs(n.volume[1])))
            inverted = ev[0] * ev[1] < 0 and sides[1] > 0 and sides[0] / sides[1] >= CENTRED
            gl, gr = (abs(e) * passed * song.master.past(n.start) for e in ev)
            if inverted:
                gl = gr = max(gl, gr)
            if echo_ins and max(gl, gr) >= QUIET and _place(song, grid, n, song.echo_channels[n.voice][0], note, echo_ins,
                                                           0, gl, gr, inverted, id(n) in song.baked_of):
                repeats += 1
    return placed, repeats, baked


def _lift(song: _Song) -> None:
    """A note's loudness is its channel's volume times the global volume (the
    master volume's), and both are whole numbers: the channel's 0-64, the
    global 0-128. Every channel's volume is raised, and the global volume
    lowered by as much, as far as the loudest voice (or its echo's first
    repeat) reaches 64, with the global volume kept at 32 or more: IT's
    volumes are coarse at the bottom (Kirby swells a voice to 3 of 127, IT
    volume 1.5, which rounds a third too loud). The other way where the
    master leaves room: DKC2's voices reach 123 under a master of 60, and IT
    stops at 64."""
    def demand(n):
        dry = max((abs(left) + abs(right)) / 2 for left, right in (n.volume, *((sl, sr) for _, sl, sr in n.swells)))
        if _sends(n):
            return max(dry, dry * max(map(abs, n.echo_volume)) * song.master.past(n.start))
        if _sends_at_once(n):
            peak = snes_chip.response_peak(_at_once_response(song, n.echo_filter, n.echo_feedback))
            return max(dry, dry * max(map(abs, n.echo_volume)) * song.master.past(n.start) * peak)
        return dry
    master = song.master.loudest()
    lift = max(max(map(demand, song.notes), default=0) / 64, min(1.0, 32 / master))
    song.lift = song.master.lift = min(lift, max(1.0, 128 / master))


def _master_channel(song: _Song, grid: it_song.Grid, ch: int, fade: float) -> None:
    """On the last channel, the master volume's changes (a driver's own fades)
    and the fade over the song's last `fade` seconds, as a player fades it."""
    row_hz, fade_from = song.row_hz, song.run.seconds - fade
    rows = {round(t * row_hz) for t, _, _ in song.master.changes[1:]}
    if fade > 0:
        rows |= set(range(round(fade_from * row_hz), grid.last_row + 1))
    changes = []
    for r in sorted(rows):
        t = (r + 0.5) / row_hz
        left, right = song.master.at(t)
        faded = 1.0 if fade <= 0 or t < fade_from else max(0.0, 1 - (t - fade_from) / fade)
        changes.append((r, max(0, min(128, round(max(abs(left), abs(right)) * faded * song.master.lift)))))
    grid.global_volume(ch, song.master.start(), changes)


# A note on its rows --------------------------------------------------------

def _place(song: _Song, grid: it_song.Grid, n, ch: int, note: int, ins: int, shift: int, gl: float, gr: float,
           inverted: bool = False, baked: bool = False) -> bool:
    """Write note n into channel ch, `shift` rows late, its volumes scaled by
    gl (left) and gr (right): the note, its pan (or surround, when the two
    sides are `inverted`), its bends, swells and envelope changes row by
    row, its cut. A `baked` note's recording holds its bends and envelope
    already. False when it is past the song's end or silent throughout."""
    row_hz = song.row_hz
    row = round(n.start * row_hz) + shift
    if not grid.has(row):
        return False
    gl, gr = gl / song.lift, gr / song.lift
    vol, pan = _loudness(*n.volume, gl, gr)
    if vol == 0 and not any(_loudness(sl, sr, gl, gr)[0] for _, sl, sr in n.swells):
        return False                     # silent throughout (a driver may key a note silent, then swell it up)
    end_row = (round(n.end * row_hz) + shift) if n.end is not None else grid.last_row + 1
    end_row = max(end_row, row + 1)      # a note shorter than half a row still gets its row, and its cut after
    factors = None
    if n.envelopes and not baked:
        factors, silent = _envelope_factors(song, n, row - shift, end_row - shift)
        if silent is not None:
            end_row = min(end_row, max(row + 1, silent + shift))
    scaled = lambda v, r: v if factors is None else max(0, min(64, round(v * factors[r - row])))  # noqa: E731
    bends, swells = [] if baked else list(n.bends), list(n.swells)
    pitch, base = 0 if baked else n.pitch, vol
    volumes, targets, pans, side = [scaled(vol, row)], [], [pan], pan
    for r in range(row, min(end_row, grid.last_row + 1)):
        t = (r - shift + 0.5) / row_hz
        while bends and bends[0][0] <= t:
            pitch = bends.pop(0)[1]
        while swells and swells[0][0] <= t:
            _, sl, sr = swells.pop(0)
            base, moved = _loudness(sl, sr, gl, gr)
            side = moved if moved is not None else side
        if r > row:
            volumes.append(scaled(base, r))
            pans.append(side)
        targets.append(round(64 * (song.it_semis(n, pitch) - note)) if pitch else None)
    # the hardware's noise runs on between notes: start each somewhere else
    offset = 1 + round(n.start * RATE) * 40503 % (RATE // 256 - 1) if n.noise else None
    grid.write(ch, Line(row=row, end=end_row, note=note, instrument=ins, volumes=volumes, pan=pan, surround=inverted,
                        pitch=targets, offset=offset, pans=pans))
    return True


def _envelope_factors(song: _Song, n, first: int, stop: int):
    """For a note whose envelope registers were written while it sounded (it
    plays an instrument without an envelope): per row from `first` to
    `stop` (unshifted), its envelope's level (0-1), and the row from which
    it is silent for good (or None)."""
    if id(n) in song.factors_of:
        return song.factors_of[id(n)]
    start = snes_chip.envelope_start(n.start)
    length = snes_chip.seen(song.end_of(n)) - start
    changes = [(snes_chip.seen(t) - start, a1, a2, g) for t, a1, a2, g in n.envelopes]
    real = snes_chip.envelope_track(*n.adsr, n.gain, changes, length, start)
    bounds = [max(0, round(r / song.row_hz * RATE) - start) for r in range(first, stop + 1)]
    f = [level / 0x7FF for level in _row_means(real, bounds)]
    silent = None
    if real[-1][1] == 0 and real[-1][0] < length:
        silent = math.ceil((n.start + real[-1][0] / RATE) * song.row_hz)
    song.factors_of[id(n)] = f, silent
    return f, silent


def _gains_at(song: _Song, what, semis: int, filt) -> list[float]:
    """snes_chip.echo_gains for a sample (or "noise") at a semitone, once each."""
    key = (what, semis, filt)
    if key not in song.gains_of:
        s = None if what == "noise" else song.decoded[what]
        song.gains_of[key] = snes_chip.echo_gains(None if s is None else s.pcm, _loop(s) if s is not None else None,
                                                  0x1000 * 2 ** (semis / 12), filt, song.taps)
    return song.gains_of[key]


def _repeat_gains(song: _Song, n) -> list[float]:
    return _gains_at(song, "noise" if n.noise else n.brr, round(12 * math.log2(max(1, n.pitch) / 0x1000)), n.echo_filter)
