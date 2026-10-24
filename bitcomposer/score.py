"""A composed song as a score of voices (phase 2 of docs/IDIOM.md): the
bridge from the generator's rows to the converter's back end, so a SNES
pack's song is rendered by the stages a game's is (spc.convert.render) and
read by the readers a game's is (translate.reading.of_score).

of_song(song) walks the patterns the generator wrote, one channel a voice
(its own echo channels left out: the echo is the SNES chip's here), and
makes the decoder's kind of note (spc.notes.Note): a start and an end in
seconds; the preset as the sample, kept at its own rate, the pitch as the
SNES chip's register for it; the volumes from the volume column, the
sample's and the channel's, the pan from the channel's and Xxx; vibrato
(Hxy) and tone portamento (Gxx) as bends, the volume column and volume
slides (Dxy) as swells, note delays (SDx) and retriggers (Qxy) as starts.
Every note plays a flat envelope (GAIN direct, full) and ends on a cut, as
a decoded note does: a preset's release tail (its sustain loop) is not
played, as the SNES chip played none. Where the song uses echo, the melody,
harmony and arp voices send to the chip's echo: the delay the nearest step
of 16 ms to the generator's, up to the chip's 240 ms (the generator's
dotted eighths and quarters at a slow tempo ran longer); the generator's
feedback; a mild low-pass filter. The bass and the drums stay dry, as they
were. This bridge keeps the generator's grid; freeing it is phase 4's.
"""
import math
from array import array

from . import it_format as itf
from .echo import ECHO_DELAYS, ECHO_WETNESS
from .it_format import FX_PORTAMENTO, FX_RETRIGGER, FX_SET_PAN, FX_SPECIAL, FX_VIBRATO, FX_VOLUME_SLIDE, S_NOTE_DELAY, it_tempo_to_bpm
from .mix import channel_volumes_for
from .pattern import CH_ECHO_ALL, CHANNEL_ROLES, ROWS_PER_BEAT
from .spc import convert, it_song, notes as notes_mod

GAIN_FULL = 0x7F                     # GAIN direct at its top: a flat envelope, the note's own volumes shaping it
ECHO_STEP = 0.016                    # seconds: the SNES chip's echo delay comes in steps of this, to 15 of them
ECHO_WET = 0.4                       # the echo's volume against the voices, at wetness 1 (the generator sent its
                                     # lead at a half and the harmony and arp at a third)
ECHO_FILTER = (64, 32, 16, 8, 4, 2, 1, 0)   # FIR taps: a gentle low-pass, each trip round the echo darker
SENDS = {"melody", "harmony", "arp"}        # the parts that send to the echo
VIBRATO_DEPTH = 1 / 8                # semitones a unit of Hxy's depth swings, either way
VIBRATO_SPEED = 1 / 64               # cycles a tick a unit of Hxy's speed makes
PORTA_STEP = 1 / 16                  # semitones a tick a unit of Gxx slides


class _Pcm:
    """A preset's PCM as the converter takes a decoded sample (spc.brr.Sample's shape)."""

    def __init__(self, s: itf.ITSample):
        self.pcm = array("h")
        self.pcm.frombytes(s.data[:len(s.data) - len(s.data) % 2])
        self.loop_start = s.loop_start if s.loop else None
        self.loop_end = s.loop_end if s.loop else None
        self.seamless = True
        self.start, self.loop_addr, self.blocks = 0, 0, 0

    @property
    def loops(self) -> bool:
        return self.loop_start is not None

    def __len__(self):
        return len(self.pcm)


def _pitch(c5_speed: int, midi: float) -> int:
    """The SNES chip's pitch register that plays a sample recorded for C-5 at
    c5_speed at this midi note, under the converter's model (0x1000 is the
    sample at 32 kHz)."""
    return max(1, min(0x3FFF, round(0x1000 * c5_speed / 32000 * 2 ** ((midi - 60) / 12))))


def _sides(level: float, pan: float) -> tuple[int, int]:
    """Left and right volume registers for an IT loudness (0 to 1 of 64) at a pan (the right side's share):
    the converter sums the sides over two, so a centred note gets its loudness on each side."""
    v = 64 * max(0.0, min(1.0, level))
    return max(0, min(127, round(2 * v * (1 - pan)))), max(0, min(127, round(2 * v * pan)))


def of_song(song: dict) -> convert.Score:
    """The composed song (compose_song's dict) as a score for the converter's back end."""
    info = song.get("info", {})
    speed = song["speed"]
    bpm = it_tempo_to_bpm(song["tempo"], speed, ROWS_PER_BEAT)
    row_s = 60 / (bpm * ROWS_PER_BEAT)                  # seconds a row of the generator's grid
    tick_s = row_s / speed
    samples = song["samples"]
    channel_vol = channel_volumes_for(info) if info else [64] * len(CHANNEL_ROLES)
    voices = [ch for ch in range(len(CHANNEL_ROLES)) if ch not in CH_ECHO_ALL]
    voice_of = {ch: i for i, ch in enumerate(voices)}
    pans = {ch: itf.DEFAULT_CHANNEL_PANS[ch] / 64 if ch < len(itf.DEFAULT_CHANNEL_PANS) else 0.5 for ch in voices}
    # the echo, as the chip's
    use_echo = bool(info.get("echo"))
    delay_rows = ECHO_DELAYS.get(info.get("echo_delay"), 3) if use_echo else 0
    steps = max(1, min(15, round(delay_rows * row_s / ECHO_STEP))) if use_echo else 0
    wet = ECHO_WETNESS.get(info.get("echo_wet"), 1.0) * ECHO_WET
    feedback = float(info.get("echo_feedback") or 0.0)
    sends = {ch for ch in voices if CHANNEL_ROLES[ch] in SENDS} if use_echo else set()

    pcm_of, key_of, addr_of = {}, {}, {}
    def addr_for(instrument: int) -> tuple[int, int] | None:
        if not 0 < instrument <= len(samples):
            return None
        if instrument not in addr_of:
            s = samples[instrument - 1]
            addr = (0x100 * instrument, 0)
            pcm_of[addr] = _Pcm(s)
            key_of[addr] = s.filename or s.name or f"preset {instrument}"
            addr_of[instrument] = addr
        return addr_of[instrument]

    def level_of(cell, ch: int) -> float:
        s = samples[cell.instrument - 1] if 0 < cell.instrument <= len(samples) else None
        column = cell.volume if cell.volume <= 64 else (s.default_volume if s else 64)
        return column / 64 * (s.global_volume / 64 if s else 1.0) * channel_vol[ch] / 64

    notes: list = []
    open_: dict = {}                                    # channel -> (note, its sample's c5_speed, its midi, its level)
    phase: dict = {}                                    # channel -> the vibrato's phase, in cycles
    row0 = 0

    def close(ch: int, t: float) -> None:
        if ch in open_:
            n, *_ = open_.pop(ch)
            n.end = max(n.start, t)

    def start(ch: int, t: float, midi: float, instrument: int, level: float, pan: float) -> None:
        close(ch, t)
        addr = addr_for(instrument)
        if addr is None:
            return
        c5 = samples[instrument - 1].c5_speed
        n = notes_mod.Note(voice_of[ch], t, instrument, _pitch(c5, midi), _sides(level, pan), (0, 0), GAIN_FULL,
                           ch in sends, False, brr=addr,
                           echo_delay=steps * ECHO_STEP, echo_volume=(wet, wet) if ch in sends else (0.0, 0.0),
                           echo_feedback=feedback, echo_filter=ECHO_FILTER, echo_writes=True)
        notes.append(n)
        open_[ch] = [n, c5, midi, level]

    for o in song["orders"]:
        if o >= len(song["patterns"]):
            continue
        pat = song["patterns"][o]
        for r, row in enumerate(pat.data):
            t_row = (row0 + r) * row_s
            for ch in voices:
                if ch >= len(row):
                    continue
                cell = row[ch]
                pan = pans[ch]
                if cell.effect == FX_SET_PAN:
                    pan = pans[ch] = max(0.0, min(1.0, cell.effect_val / 255))
                    if ch in open_:
                        n, c5, midi, level = open_[ch]
                        n.swells.append((t_row, *_sides(level, pan)))
                delay = (cell.effect_val & 0x0F) * tick_s if cell.effect == FX_SPECIAL and cell.effect_val & 0xF0 == S_NOTE_DELAY else 0.0
                t = t_row + delay
                if cell.note in (itf.NOTE_CUT, itf.NOTE_OFF):
                    close(ch, t)
                elif 1 <= cell.note <= 119 and cell.volume != 0:
                    level = level_of(cell, ch)
                    instrument = cell.instrument or (open_[ch][0].sample if ch in open_ else 0)
                    if cell.effect == FX_PORTAMENTO and ch in open_:
                        # a slide from the sounding note to this one, PORTA_STEP a unit a tick
                        n, c5, midi, _ = open_[ch]
                        rate = max(1, cell.effect_val) * PORTA_STEP
                        ticks = max(1, math.ceil(abs(cell.note - midi) / rate))
                        for k in range(1, ticks + 1):
                            m = midi + (cell.note - midi) * min(1.0, k / ticks)
                            n.bends.append((t + k * tick_s, _pitch(c5, m)))
                        open_[ch][2] = float(cell.note)
                        if level != open_[ch][3]:
                            n.swells.append((t, *_sides(level, pan)))
                            open_[ch][3] = level
                    elif cell.effect == FX_RETRIGGER and cell.effect_val & 0x0F:
                        every = (cell.effect_val & 0x0F) * tick_s
                        k = 0
                        while t + k * every < t_row + row_s - 1e-9:
                            start(ch, t + k * every, float(cell.note), instrument, level, pan)
                            k += 1
                    else:
                        start(ch, t, float(cell.note), instrument, level, pan)
                elif cell.note == 0 and cell.volume <= 64 and ch in open_:
                    # the volume column alone: the sounding note's level from here
                    n, c5, midi, _ = open_[ch]
                    level = level_of(cell, ch)
                    n.swells.append((t_row, *_sides(level, pan)))
                    open_[ch][3] = level
                if ch in open_ and cell.effect == FX_VOLUME_SLIDE and cell.effect_val:
                    # Dxy: up x or down y a tick, on every tick but the first
                    n, c5, midi, level = open_[ch]
                    x, y = cell.effect_val >> 4, cell.effect_val & 0x0F
                    per_tick = (x if y == 0 else -y) / 64 * (samples[n.sample - 1].global_volume / 64 if 0 < n.sample <= len(samples) else 1.0) * channel_vol[ch] / 64
                    for k in range(1, speed):
                        level = max(0.0, min(1.0, level + per_tick))
                        n.swells.append((t_row + k * tick_s, *_sides(level, pan)))
                    open_[ch][3] = level
                if ch in open_ and cell.effect == FX_VIBRATO and cell.effect_val:
                    n, c5, midi, level = open_[ch]
                    sp, depth = cell.effect_val >> 4, cell.effect_val & 0x0F
                    ph = phase.get(ch, 0.0)
                    for k in range(speed):
                        ph += sp * VIBRATO_SPEED
                        n.bends.append((t_row + k * tick_s, _pitch(c5, midi + depth * VIBRATO_DEPTH * math.sin(2 * math.pi * ph))))
                    phase[ch] = ph % 1.0
                elif ch in open_ and ch in phase and cell.effect != FX_VIBRATO:
                    n, c5, midi, level = open_[ch]
                    n.bends.append((t_row, _pitch(c5, midi)))      # the vibrato ends: back to the note
                    del phase[ch]
        row0 += pat.rows
    seconds = row0 * row_s
    for ch in list(open_):
        close(ch, seconds)
    for n in notes:
        n.bends.sort(key=lambda b: b[0])
        n.swells.sort(key=lambda w: w[0])
    tempo, row_hz = it_song.tempo_for(convert.FINE_GRID)
    pack = info.get("pack") or info.get("style") or ""
    return convert.Score(notes, seconds, len(voices), [(0.0, 127, 127)], 0.0, song.get("name", "bitComposer"), "bitComposer", pack,
                         row_hz, tempo, 0.0, 0.0, False, None, pcm_of, key_of,
                         message=[f"{song.get('name', '')} - {info.get('key', '')} {str(info.get('scale', '')).replace('_', ' ')} - {round(bpm)} BPM",
                                  "Composed by bitComposer and rendered through its SNES back end: the",
                                  "voices as notes in time, the echo as the SNES chip's, on channels of their own."])
