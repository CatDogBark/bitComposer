"""The written mix: channel volumes, the sustaining-arp level, pack trims and
the master gain."""
import random
import zlib

from . import __version__
from . import theory
from . import names
from . import samples as smp
from . import structure as struct
from .it_format import (
    ITSample, ITPattern, ITNote, midi_to_it_note, NOTE_CUT,
    write_it_file, bpm_to_it_tempo, it_tempo_to_bpm,
)
from . import pattern as pattern_mod
from .pattern import (
    CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
    CH_ECHO1, CH_ECHO2, CH_ECHO_HARMONY, CH_ECHO_ARP, CH_ECHO_ALL, CHANNEL_ROLES,
    NUM_CHANNELS, ROWS_PER_PATTERN, ROWS_PER_BAR, ROWS_PER_BEAT,
    humanize_volume, apply_notes_to_pattern, apply_vibrato,
    apply_portamento, apply_harmony_fade, apply_fade, apply_echo_taps, apply_echo_spill_taps,
    apply_sustain_safety_net, silence_inactive_channels,
    apply_chord_arpeggio, end_note,
)
from .drums import pick_grooves, pick_fill, render_drums
from .packs import PACKS, PACK_NAMES, pack_weights, pack_value
from .melody import (
    generate_motif, vary_motif, generate_melody,
    generate_counter_melody, add_melody_cuts,
)
from .harmony import generate_harmony_timeline
from .bass import generate_bass_timeline, pick_section_bass
from .arp import pick_figures, generate_arp




# Channel mix — tuned by ear via the widget's master panel. Order matches
# bitcomposer.pattern: melody, harmony x3, bass, arp, six drums, two echo taps.
# The echo channels sit at the melody's level; the taps are already quieter
# through their volume columns.
#
# Measured by rendering each part alone (2026-10-14, 60 s, dBFS): melody sits
# 6-14 dB under the drums and the arp 1-4 dB under the melody on every palette.
CHANNEL_VOLUMES = [
    13,              # melody
    25, 25, 25,      # harmony
    8,               # bass
    33,              # arp
    36, 36, 36, 36, 36, 36,  # kick, snare, hihat, tom, crash, open hat
    13, 13,          # lead echo — at the melody's level; the sends set the wetness
    25, 25, 25,      # harmony echo — at the harmony's level
    33, 33,          # arp echo — at the arp's level
]
# Levels no longer differ by palette: samples.generate_instrument normalises
# sustaining voices to one loop loudness and, on the arp, struck voices to
# one strike loudness, so a pluck, bell or pizz hits the arp at the same
# level whatever the song drew. The arp channel's 33 was set for struck
# voices, which peak and die within the step; a sustaining voice on the arp
# (the genesis PSG square, the Mega Man X pulse synth) holds full level for
# the whole step and came out 3-6 dB over the melody, so it takes this
# level instead (set by ear for the PSG square, Lower Cistern, 2026-10-13).
SUSTAINING_ARP_LEVEL = 17

# Master gain on every written channel volume. The table above and every
# trim were tuned against each other for balance with the level never
# revisited: songs came out at -27 LUFS on average, ten dB under anything
# streamed. With the module's mix volume at 128 (it was 80) and this gain,
# eighteen seeds across the palettes average about -20 LUFS with the loudest
# song's true peak a decibel clear of full scale; the dynamics are untouched.
MASTER_GAIN = 1.25


def channel_volumes_for(info: dict) -> list[int]:
    vols = [min(64, round(v * MASTER_GAIN)) for v in _channel_volumes_base(info)]
    return vols


def _channel_volumes_base(info: dict) -> list[int]:
    vols = list(CHANNEL_VOLUMES)
    for role, vol in (PACKS[info["pack"]].get("trims", {}) if info.get("pack") else {}).items():
        for ch, r in enumerate(CHANNEL_ROLES):
            if r == role:
                vols[ch] = vol
    if not info.get("struck", {}).get("arp", True):
        for ch in (CH_ARP, *CH_ECHO_ARP):
            vols[ch] = SUSTAINING_ARP_LEVEL
    return vols
