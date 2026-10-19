"""
Impulse Tracker (.it) file writer.

Implements enough of the IT 2.14 format spec to write playable module files.
Reference: https://github.com/schismtracker/schismtracker/wiki/ITTECH.TXT
"""

import struct
from dataclasses import dataclass, field

from .samples import SAMPLE_RATE


@dataclass
class ITSample:
    """A sample (waveform) in the IT file."""
    name: str = ""
    filename: str = ""
    data: bytes = b""
    length: int = 0
    loop_start: int = 0
    loop_end: int = 0
    loop: bool = True
    # Sustain loop: looped while the note is held; a note-off (===) exits it
    # and playback runs on through whatever follows — the release tail.
    sus_loop: bool = False
    sus_loop_start: int = 0
    sus_loop_end: int = 0
    c5_speed: int = SAMPLE_RATE  # Playback rate for C-5
    default_volume: int = 64
    global_volume: int = 64
    is_16bit: bool = True


@dataclass
class ITInstrument:
    """An IT instrument: a sample with a volume envelope, the way a tracker
    shows an instrument (the generator writes samples alone; the SPC
    converter writes instruments, so a converted song opens readable).

    envelope: (tick, level 0-64) nodes, at most 25; empty for none. The
    envelope runs in song ticks from the note's start and holds its last
    level. sustain: a node index the envelope holds at until a note-off.
    """
    name: str = ""
    sample: int = 1                  # 1-based: every note of the keyboard plays this sample
    keyboard: list | None = None     # or per note 0-119, the (note, sample) it plays instead
    envelope: list = field(default_factory=list)
    sustain: int | None = None
    nna: int = 0                     # new note action: 0 cut, 1 continue, 2 note off, 3 fade
    fadeout: int = 0
    global_volume: int = 128
    pan: int | None = None           # default pan 0-64, or None to leave the channel's


@dataclass
class ITNote:
    """A single note event in a pattern."""
    note: int = 0       # 0=none, 1-120=C-0 to B-9, 254=notecut, 255=noteoff
    instrument: int = 0  # 0=none, 1-99
    volume: int = 255    # 255=none, 0-64=set volume
    effect: int = 0      # Effect command
    effect_val: int = 0  # Effect parameter


@dataclass
class ITPattern:
    """A pattern — rows x channels of note data."""
    rows: int = 64
    channels: int = 8
    data: list = field(default_factory=list)  # [row][channel] = ITNote

    def __post_init__(self):
        if not self.data:
            self.data = [
                [ITNote() for _ in range(self.channels)]
                for _ in range(self.rows)
            ]


def _pack_pattern(pattern: ITPattern) -> bytes:
    """Pack a pattern into IT compressed format."""
    # IT uses a "packed" pattern format with channel masking.
    out = bytearray()

    for row in range(pattern.rows):
        for ch in range(pattern.channels):
            note = pattern.data[row][ch]

            # Skip empty notes
            if (note.note == 0 and note.instrument == 0 and
                    note.volume == 255 and note.effect == 0 and
                    note.effect_val == 0):
                continue

            # Build channel variable + mask variable
            mask = 0
            if note.note != 0:
                mask |= 1
            if note.instrument != 0:
                mask |= 2
            if note.volume != 255:
                mask |= 4
            if note.effect != 0 or note.effect_val != 0:
                mask |= 8

            # Channel byte: (channel + 1) with bit 7 set means "mask follows"
            chan_byte = (ch + 1) | 0x80
            out.append(chan_byte)
            out.append(mask)

            if mask & 1:
                out.append(note.note)
            if mask & 2:
                out.append(note.instrument)
            if mask & 4:
                out.append(note.volume)
            if mask & 8:
                out.append(note.effect)
                out.append(note.effect_val)

        # End of row marker
        out.append(0)

    return bytes(out)


def midi_to_it_note(midi_note: int) -> int:
    """Convert MIDI note number to IT note value.
    IT notes: 0=C-0, 1=C#0, ... 12=C-1, etc.
    MIDI: 0=C-(-1), 12=C-0, 24=C-1, 60=C-4
    IT format stores notes as (octave * 12 + semitone) but starting from C-0.

    IT note 60 is C-5, and C-5 is the note that plays a sample at its C5Speed;
    our samples carry one period of 261.6 Hz at that rate, so IT 60 sounds
    at middle C, which is MIDI 60. The numbers agree; there is no offset.
    Until 2026-10-17 this subtracted 12, so every tonal part sounded an
    octave below its label (label 60 rendered at 130.8 Hz, measured), and
    the registers were then tuned by ear around the error."""
    return max(0, min(119, midi_note))


NOTE_CUT = 254
NOTE_OFF = 255

# IT stores a "tempo" byte that is only the real BPM at speed 6. A row lasts
# 2.5 * speed / tempo seconds, so with rows_per_beat rows to a quarter note the
# musical tempo is 24 * tempo / (speed * rows_per_beat) — the 24 being 60
# seconds over 2.5. Treating the field as BPM while choosing speed separately
# scales the whole song by up to 1.5x.
_IT_TEMPO_FACTOR = 24


# Stereo placement by musical role, not by channel index. The previous layout
# spread pan linearly across the channel number, which put the lead hard left
# and every drum on the right — the whole rhythm section in one ear.
# Order matches bitcomposer.pattern: melody, harmony x3, bass, arp, then drums.
DEFAULT_CHANNEL_PANS = [
    32,          # melody   — the lead belongs in the middle
    20, 32, 44,  # harmony  — spread the chord around it
    32,          # bass     — centred, like the kick
    40,          # arp      — off to one side so it does not fight the lead
    32,          # kick     — centre
    32,          # snare    — centre, it anchors the backbeat with the kick
    38,          # hihat    — slightly right
    26,          # tom      — slightly left
    24,          # crash    — wide, it is an accent
    42,          # open hat — mirrors the closed hat
    12,          # lead echo, taps 1+3 — the SNES echo was wide; put the repeats out at the sides
    52,          # lead echo, tap 2 — opposite side, so the repeat bounces
    44, 32, 20,  # harmony echo — each voice's return on the far side of the voice
    16, 48,      # arp echo — the arp sits at 40; its repeats bounce around it
] + [32] * 45


def bpm_to_it_tempo(bpm: float, speed: int, rows_per_beat: int = 4) -> int:
    """Convert a musical BPM to the value to store in the IT tempo field."""
    raw = round(bpm * speed * rows_per_beat / _IT_TEMPO_FACTOR)
    return max(32, min(255, raw))


def it_tempo_to_bpm(tempo: int, speed: int, rows_per_beat: int = 4) -> float:
    """Actual musical tempo of a module — inverse of bpm_to_it_tempo."""
    return _IT_TEMPO_FACTOR * tempo / (speed * rows_per_beat)

# IT effect commands (letter = number)
FX_VOLUME_SLIDE = 4    # Dxy - volume slide (x=up, y=down)
FX_PORTA_DOWN = 5      # Exx - pitch down; EFx fine (x/16 semitone), EEx extra fine (x/64), once a row
FX_PORTA_UP = 6        # Fxx - pitch up, the same
FX_PORTAMENTO = 7      # Gxx - tone portamento (slide to note)
FX_VIBRATO = 8         # Hxy - vibrato (x=speed, y=depth)
FX_ARPEGGIO = 10       # Jxy - cycle note / note+x / note+y semitones per tick
FX_RETRIGGER = 17      # Qxy - retrigger note every y ticks (x = volume change)
FX_TREMOLO = 18        # Rxy - tremolo (x=speed, y=depth)
FX_SPECIAL = 19        # Sxy - command group; SDx delays the note by x ticks
FX_SET_TEMPO = 20      # Txx - set tempo
FX_SET_PAN = 24        # Xxx - set panning, 0 = left, 128 = centre, 255 = right

# Sub-command of Sxy: note delay. Parameter is 0xD0 | ticks.
S_NOTE_DELAY = 0xD0


def arpeggio_param(played_note: int, chord_notes: list[int]) -> int:
    """Jxy parameter that voices chord_notes upward from played_note.

    J cycles the channel between the note, note+x and note+y semitones once
    per tick, which is how a chip with few channels fakes a whole chord on
    one of them. Offsets are taken modulo an octave from whatever note the
    voice actually landed on, so inversions arpeggiate correctly too.
    """
    base = played_note % 12
    offsets = sorted({(n % 12 - base) % 12 for n in chord_notes})
    upper = [o for o in offsets if o != 0][:2]
    while len(upper) < 2:
        upper.append(0)
    return ((upper[0] & 0x0F) << 4) | (upper[1] & 0x0F)


def write_it_file(
    filepath: str,
    song_name: str,
    samples: list[ITSample],
    patterns: list[ITPattern],
    orders: list[int],
    tempo: int = 125,
    speed: int = 6,
    global_volume: int = 128,
    mix_volume: int = 128,
    num_channels: int = 8,
    channel_volumes: list[int] | None = None,
    channel_pans: list[int] | None = None,
    message: str = "",
    instruments: list | None = None,
) -> None:
    """Write a complete .it module file.

    `message` goes into the module's song message (shown by trackers and
    returned by libopenmpt as metadata "message"); lines are separated by
    \r as the format requires. It is stored after the sample data.

    `instruments` (ITInstrument) switches the file to instrument mode:
    pattern notes then name instruments, not samples. Without them the
    file is written exactly as it always was (sample mode).
    """

    instruments = list(instruments or [])
    num_instruments = len(instruments)
    num_samples = len(samples)
    num_patterns = len(patterns)

    # Pad orders to even number (IT requirement)
    order_list = list(orders)
    if len(order_list) % 2 != 0:
        order_list.append(255)  # 255 = end of song marker

    # Calculate header size and offsets
    header_size = 192
    # After header: orders, then sample offsets, then pattern offsets
    orders_offset = header_size
    instrument_offsets_start = orders_offset + len(order_list)
    sample_offsets_start = instrument_offsets_start + (num_instruments * 4)
    pattern_offsets_start = sample_offsets_start + (num_samples * 4)
    data_start = pattern_offsets_start + (num_patterns * 4)

    # Pre-pack patterns to know their sizes
    packed_patterns = [_pack_pattern(p) for p in patterns]

    # Build sample headers and figure out data offsets
    # Sample headers are 80 bytes each, stored at offsets pointed to by the offset table.
    # Sample data follows after all headers and patterns.

    # Layout: header | orders | smp_offset_table | pat_offset_table |
    #         sample_headers | pattern_data | sample_data

    instrument_headers_start = data_start
    sample_headers_start = instrument_headers_start + (num_instruments * INSTRUMENT_SIZE)
    pattern_data_start = sample_headers_start + (num_samples * 80)

    # Calculate pattern data positions
    pattern_positions = []
    pos = pattern_data_start
    for packed in packed_patterns:
        pattern_positions.append(pos)
        # Pattern in file: 2 bytes length + 2 bytes rows + 4 bytes reserved + packed data
        pos += 8 + len(packed)

    # Calculate sample data positions
    sample_data_start = pos
    sample_data_positions = []
    pos = sample_data_start
    for smp in samples:
        sample_data_positions.append(pos)
        pos += len(smp.data)

    # Song message, if any, after the sample data. 8000 bytes is the format's cap.
    msg_bytes = message.replace("\r\n", "\r").replace("\n", "\r").encode(
        "ascii", errors="replace")[:7999] if message else b""
    msg_offset = pos if msg_bytes else 0

    # Now build the file
    f = bytearray()

    # ── IT Header (192 bytes) ──
    f.extend(b"IMPM")                              # Magic
    f.extend(song_name[:25].ljust(26, '\0').encode('ascii', errors='replace'))  # Song name
    f.extend(struct.pack("<H", 0))                 # PHilight
    f.extend(struct.pack("<H", len(order_list)))   # OrdNum
    f.extend(struct.pack("<H", num_instruments))   # InsNum (0: samples directly)
    f.extend(struct.pack("<H", num_samples))       # SmpNum
    f.extend(struct.pack("<H", num_patterns))      # PatNum
    f.extend(struct.pack("<H", 0x0214))            # Cwt/v (IT 2.14 compatible)
    f.extend(struct.pack("<H", 0x0214))            # Cmwt (compatible with IT 2.14)
    # Flags: bit 0=stereo, bit 2=use instruments (0=samples), bit 3=linear slides
    flags = 0x0009  # Stereo + linear slides
    if num_instruments:
        flags |= 0x0004  # instruments
    f.extend(struct.pack("<H", flags))
    f.extend(struct.pack("<H", 1 if msg_bytes else 0))  # Special: bit 0 = message attached
    f.extend(struct.pack("<B", global_volume))     # GV
    f.extend(struct.pack("<B", mix_volume))        # MV
    f.extend(struct.pack("<B", speed))             # IS (initial speed)
    f.extend(struct.pack("<B", tempo))             # IT (initial tempo)
    f.extend(struct.pack("<B", 128))               # Sep (stereo separation, 128=max)
    f.extend(struct.pack("<B", 0))                 # PWD (pitch wheel depth)
    f.extend(struct.pack("<H", len(msg_bytes)))    # MsgLgth
    f.extend(struct.pack("<I", msg_offset))        # MsgOff
    f.extend(struct.pack("<I", 0))                 # Reserved

    # Channel pan (64 bytes). 0 = hard left, 32 = centre, 64 = hard right.
    for ch in range(64):
        if ch < num_channels:
            pan = channel_pans[ch] if channel_pans else DEFAULT_CHANNEL_PANS[ch]
            f.append(max(0, min(64, pan)))
        else:
            f.append(32 | 128)  # Center + disabled

    # Channel volume (64 bytes)
    for ch in range(64):
        if ch < num_channels and channel_volumes:
            f.append(max(0, min(64, channel_volumes[ch])))
        else:
            f.append(64 if ch < num_channels else 0)

    assert len(f) == 192, f"Header should be 192 bytes, got {len(f)}"

    # ── Orders ──
    f.extend(bytes(order_list))

    # ── Instrument offset table ──
    for i in range(num_instruments):
        f.extend(struct.pack("<I", instrument_headers_start + i * INSTRUMENT_SIZE))

    # ── Sample offset table ──
    for i in range(num_samples):
        f.extend(struct.pack("<I", sample_headers_start + i * 80))

    # ── Pattern offset table ──
    for i in range(num_patterns):
        f.extend(struct.pack("<I", pattern_positions[i]))

    # ── Instrument headers ──
    for ins in instruments:
        f.extend(_instrument_header(ins))

    # ── Sample headers (80 bytes each) ──
    for i, smp in enumerate(samples):
        sh = bytearray()
        sh.extend(b"IMPS")                         # Magic
        sh.extend(smp.filename[:12].ljust(13, '\0').encode('ascii', errors='replace'))
        sh.append(smp.global_volume)                # GvL
        # Flags: bit 0=sample exists, bit 1=16-bit, bit 4=loop, bit 5=sustain loop
        sflags = 0x01  # Sample present
        if smp.is_16bit:
            sflags |= 0x02
        if smp.loop:
            sflags |= 0x10
        if smp.sus_loop:
            sflags |= 0x20
        sh.append(sflags)
        sh.append(smp.default_volume)               # Vol
        sh.extend(smp.name[:25].ljust(26, '\0').encode('ascii', errors='replace'))
        # Cvt: bit 0 = signed samples
        sh.append(0x01)                             # Cvt (signed)
        sh.append(0x00)                             # DfP (default panning, 0=off)
        sh.extend(struct.pack("<I", smp.length))    # Length (in samples)
        loop_end = smp.loop_end if smp.loop_end > 0 else smp.length
        sh.extend(struct.pack("<I", smp.loop_start))
        sh.extend(struct.pack("<I", loop_end))
        sh.extend(struct.pack("<I", smp.c5_speed))  # C5Speed
        sh.extend(struct.pack("<I", smp.sus_loop_start if smp.sus_loop else 0))  # SusLoop begin
        sh.extend(struct.pack("<I", smp.sus_loop_end if smp.sus_loop else 0))    # SusLoop end
        sh.extend(struct.pack("<I", sample_data_positions[i]))  # SamplePointer
        sh.append(0)                                # ViS (vibrato speed)
        sh.append(0)                                # ViD (vibrato depth)
        sh.append(0)                                # ViR (vibrato rate)
        sh.append(0)                                # ViT (vibrato type)
        assert len(sh) == 80, f"Sample header should be 80 bytes, got {len(sh)}"
        f.extend(sh)

    # ── Pattern data ──
    for i, packed in enumerate(packed_patterns):
        # Pattern header: length (of packed data), rows, reserved
        f.extend(struct.pack("<H", len(packed)))
        f.extend(struct.pack("<H", patterns[i].rows))
        f.extend(struct.pack("<I", 0))  # Reserved
        f.extend(packed)

    # ── Sample data ──
    for smp in samples:
        f.extend(smp.data)

    # ── Song message ──
    if msg_bytes:
        assert len(f) == msg_offset
        f.extend(msg_bytes)

    with open(filepath, "wb") as fh:
        fh.write(bytes(f))


INSTRUMENT_SIZE = 554


def _envelope(nodes, sustain: int | None = None) -> bytes:
    """An IT envelope block (82 bytes): on when it has nodes."""
    nodes = list(nodes)[:25]
    flags = (1 if nodes else 0) | (4 if sustain is not None and nodes else 0)
    sus = min(sustain or 0, max(len(nodes) - 1, 0))
    b = bytearray([flags, len(nodes), 0, 0, sus, sus])
    for tick, level in nodes:
        b.append(max(0, min(64, level)))
        b.extend(struct.pack("<H", max(0, min(9999, tick))))
    b.extend(bytes(3 * (25 - len(nodes))))
    b.append(0)
    assert len(b) == 82
    return bytes(b)


def _instrument_header(ins: "ITInstrument") -> bytes:
    """An IT 2.14 instrument (IMPI, 554 bytes)."""
    h = bytearray(b"IMPI")
    h.extend(ins.name[:12].ljust(13, "\0").encode("ascii", errors="replace")[:12])   # DOS filename
    h.append(0)
    h.extend(bytes([ins.nna & 3, 0, 0]))                    # NNA, duplicate check type and action
    h.extend(struct.pack("<H", max(0, min(256, ins.fadeout))))
    h.extend(bytes([0, 60]))                                # pitch-pan separation, centre
    h.append(max(0, min(128, ins.global_volume)))
    h.append(128 | 32 if ins.pan is None else max(0, min(64, ins.pan)))
    h.extend(bytes([0, 0]))                                 # random volume, random pan
    h.extend(bytes(4))                                      # tracker version, sample count, unused
    h.extend(ins.name[:25].ljust(26, "\0").encode("ascii", errors="replace")[:26])
    h.extend(bytes([0, 0, 0, 0]))                           # filter cutoff, resonance, MIDI channel, program
    h.extend(struct.pack("<H", 0))                          # MIDI bank
    for note in range(120):                                 # the keyboard: every note, this sample, unless mapped
        h.extend(bytes(ins.keyboard[note] if ins.keyboard else (note, ins.sample)))
    h.extend(_envelope(ins.envelope, ins.sustain))          # volume
    h.extend(_envelope([]))                                 # panning
    h.extend(_envelope([]))                                 # pitch
    h.extend(bytes(4))
    assert len(h) == INSTRUMENT_SIZE, len(h)
    return bytes(h)
