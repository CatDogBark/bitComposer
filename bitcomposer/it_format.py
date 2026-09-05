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
    c5_speed: int = SAMPLE_RATE  # Playback rate for C-5
    default_volume: int = 64
    global_volume: int = 64
    is_16bit: bool = True


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
    last_mask = [0] * 64
    last_note = [0] * 64
    last_inst = [0] * 64
    last_vol = [255] * 64
    last_cmd = [0] * 64
    last_cmdval = [0] * 64

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
    IT format stores notes as (octave * 12 + semitone) but starting from C-0."""
    # MIDI 0 = C-(-1), IT 0 = C-0
    # So IT note = MIDI note - 12 (but clamped)
    it_note = midi_note - 12
    return max(0, min(119, it_note))


NOTE_CUT = 254
NOTE_OFF = 255

# IT stores a "tempo" byte that is only the real BPM at speed 6. A row lasts
# 2.5 * speed / tempo seconds, so with rows_per_beat rows to a quarter note the
# musical tempo is 24 * tempo / (speed * rows_per_beat) — the 24 being 60
# seconds over 2.5. Treating the field as BPM while choosing speed separately
# scales the whole song by up to 1.5x.
_IT_TEMPO_FACTOR = 24


def bpm_to_it_tempo(bpm: float, speed: int, rows_per_beat: int = 4) -> int:
    """Convert a musical BPM to the value to store in the IT tempo field."""
    raw = round(bpm * speed * rows_per_beat / _IT_TEMPO_FACTOR)
    return max(32, min(255, raw))


def it_tempo_to_bpm(tempo: int, speed: int, rows_per_beat: int = 4) -> float:
    """Actual musical tempo of a module — inverse of bpm_to_it_tempo."""
    return _IT_TEMPO_FACTOR * tempo / (speed * rows_per_beat)

# IT effect commands (letter = number)
FX_SET_SPEED = 1       # Axx - set speed (ticks per row)
FX_VOLUME_SLIDE = 4    # Dxy - volume slide (x=up, y=down)
FX_PITCH_DOWN = 5      # Exx - pitch slide down
FX_PITCH_UP = 6        # Fxx - pitch slide up
FX_PORTAMENTO = 7      # Gxx - tone portamento (slide to note)
FX_VIBRATO = 8         # Hxy - vibrato (x=speed, y=depth)
FX_TREMOLO = 18        # Rxy - tremolo (x=speed, y=depth)
FX_SET_TEMPO = 20      # Txx - set tempo (BPM)


def write_it_file(
    filepath: str,
    song_name: str,
    samples: list[ITSample],
    patterns: list[ITPattern],
    orders: list[int],
    tempo: int = 125,
    speed: int = 6,
    global_volume: int = 128,
    mix_volume: int = 80,
    num_channels: int = 8,
    channel_volumes: list[int] | None = None,
) -> None:
    """Write a complete .it module file."""

    num_orders = len(orders)
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
    sample_offsets_start = orders_offset + len(order_list)
    pattern_offsets_start = sample_offsets_start + (num_samples * 4)
    data_start = pattern_offsets_start + (num_patterns * 4)

    # Pre-pack patterns to know their sizes
    packed_patterns = [_pack_pattern(p) for p in patterns]

    # Build sample headers and figure out data offsets
    # Sample headers are 80 bytes each, stored at offsets pointed to by the offset table.
    # Sample data follows after all headers and patterns.

    # Layout: header | orders | smp_offset_table | pat_offset_table |
    #         sample_headers | pattern_data | sample_data

    sample_headers_start = data_start
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

    # Now build the file
    f = bytearray()

    # ── IT Header (192 bytes) ──
    f.extend(b"IMPM")                              # Magic
    f.extend(song_name[:25].ljust(26, '\0').encode('ascii', errors='replace'))  # Song name
    f.extend(struct.pack("<H", 0))                 # PHilight
    f.extend(struct.pack("<H", len(order_list)))   # OrdNum
    f.extend(struct.pack("<H", 0))                 # InsNum (we use samples directly)
    f.extend(struct.pack("<H", num_samples))       # SmpNum
    f.extend(struct.pack("<H", num_patterns))      # PatNum
    f.extend(struct.pack("<H", 0x0214))            # Cwt/v (IT 2.14 compatible)
    f.extend(struct.pack("<H", 0x0214))            # Cmwt (compatible with IT 2.14)
    # Flags: bit 0=stereo, bit 2=use instruments (0=samples), bit 3=linear slides
    flags = 0x0009  # Stereo + linear slides
    f.extend(struct.pack("<H", flags))
    f.extend(struct.pack("<H", 0))                 # Special
    f.extend(struct.pack("<B", global_volume))     # GV
    f.extend(struct.pack("<B", mix_volume))        # MV
    f.extend(struct.pack("<B", speed))             # IS (initial speed)
    f.extend(struct.pack("<B", tempo))             # IT (initial tempo)
    f.extend(struct.pack("<B", 128))               # Sep (stereo separation, 128=max)
    f.extend(struct.pack("<B", 0))                 # PWD (pitch wheel depth)
    f.extend(struct.pack("<H", 0))                 # MsgLgth
    f.extend(struct.pack("<I", 0))                 # MsgOff
    f.extend(struct.pack("<I", 0))                 # Reserved

    # Channel pan (64 bytes) — alternate L/R for stereo spread
    for ch in range(64):
        if ch < num_channels:
            # Spread channels across stereo field
            pan = 16 + (ch * 32 // max(num_channels - 1, 1))
            pan = max(0, min(64, pan))
            f.append(pan)
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

    # ── Sample offset table ──
    for i in range(num_samples):
        f.extend(struct.pack("<I", sample_headers_start + i * 80))

    # ── Pattern offset table ──
    for i in range(num_patterns):
        f.extend(struct.pack("<I", pattern_positions[i]))

    # ── Sample headers (80 bytes each) ──
    for i, smp in enumerate(samples):
        sh = bytearray()
        sh.extend(b"IMPS")                         # Magic
        sh.extend(smp.filename[:12].ljust(13, '\0').encode('ascii', errors='replace'))
        sh.append(smp.global_volume)                # GvL
        # Flags: bit 0=sample exists, bit 1=16-bit, bit 4=loop
        sflags = 0x01  # Sample present
        if smp.is_16bit:
            sflags |= 0x02
        if smp.loop:
            sflags |= 0x10
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
        sh.extend(struct.pack("<I", 0))             # SusLoop begin
        sh.extend(struct.pack("<I", 0))             # SusLoop end
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

    with open(filepath, "wb") as fh:
        fh.write(bytes(f))
