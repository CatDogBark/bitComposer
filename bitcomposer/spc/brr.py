"""
BRR, the SNES sample format, decoded as the S-DSP decodes it.

A BRR sample is a run of 9-byte blocks: a header (shift, one of four
prediction filters, the loop and end flags) and 16 four-bit samples. Each
sample is the nibble shifted, plus a prediction from the two before it; the
sum is clipped to 16 bits and then kept to 15 (bit 15 is lost, so a sum past
the 15-bit range wraps, which the hardware does and a few samples rely on),
and played doubled, as 16-bit. The filter arithmetic is the hardware's
(blargg's snes_spc, Nocash's fullsnes), integer for integer.

The research decoder the built-in packs were profiled with
(~/diags/bitcomposer/mmx/tools/spcinfo.py) did the same filters at half
scale without the 15-bit wrap: the two agree to the sample, times two,
wherever a sample stays in range.

A looped sample jumps from its end block to its loop address and carries
the filter state across. A loop whose first block predicts from the
samples before it therefore decodes differently on its first pass than on
the repeats, and a tracker that loops the first pass clicks at the seam.
decode() appends repeat passes until one decodes the same as the last
(within SEAM_TOLERANCE: the filters' rounding can leave a pass drifting by
a few steps for ever), and loops that one: the sample then sounds as the
chip plays it, every time round. Over the 258 snapshots the built-in packs
came from, 56 of the 61 played loops that never repeat exactly settle
within the tolerance; the rest drift by most of the range, and loop with a
seam (seamless False).
"""
from array import array

BLOCK = 9
MAX_BLOCKS = 0x10000 // BLOCK          # a sample cannot be longer than the RAM
MAX_PASSES = 8                         # loop passes tried before giving up on a seam
SEAM_TOLERANCE = 64                    # of 65536: passes this close count as the same (-60 dB)


class Sample:
    """A decoded sample: 16-bit PCM at 32 kHz (the DSP's rate at pitch
    0x1000), the loop region in frames (None for a one-shot), whether the
    loop repeats seamlessly, and where it came from in RAM."""

    def __init__(self, pcm: array, loop_start, loop_end, seamless: bool, start: int, loop_addr: int, blocks: int):
        self.pcm, self.loop_start, self.loop_end = pcm, loop_start, loop_end
        self.seamless, self.start, self.loop_addr, self.blocks = seamless, start, loop_addr, blocks

    @property
    def loops(self) -> bool:
        return self.loop_start is not None

    def __len__(self):
        return len(self.pcm)

    def __repr__(self):
        loop = f"loop {self.loop_start}-{self.loop_end}" if self.loops else "one-shot"
        return f"<Sample @{self.start:#06x} {len(self.pcm)} frames {loop}{'' if self.seamless else ' (seam)'}>"


def decode_block(ram, addr: int, p1: int, p2: int, out: array) -> tuple[int, int, int]:
    """Decode the block at addr onto out. p1, p2: the last two samples (in
    the 15-bit units the filters use). Returns (header, p1, p2)."""
    hdr = ram[addr & 0xFFFF]
    shift, filt = hdr >> 4, (hdr >> 2) & 3
    for i in range(1, BLOCK):
        byte = ram[(addr + i) & 0xFFFF]
        for nib in (byte >> 4, byte & 0x0F):
            s = nib - 16 if nib & 8 else nib
            if shift <= 12:
                s = (s << shift) >> 1
            else:                                  # shifts 13-15 give -2048 or 0
                s = -2048 if s < 0 else 0
            if filt == 1:
                s += p1 + ((-p1) >> 4)
            elif filt == 2:
                s += (p1 << 1) + ((-3 * p1) >> 5) - p2 + (p2 >> 4)
            elif filt == 3:
                s += (p1 << 1) + ((-13 * p1) >> 6) - p2 + ((3 * p2) >> 4)
            s = -32768 if s < -32768 else 32767 if s > 32767 else s
            s = ((s & 0x7FFF) ^ 0x4000) - 0x4000   # 15 bits: bit 15 is lost
            p2, p1 = p1, s
            out.append(s * 2)
    return hdr, p1, p2


def _run(ram, addr: int, p1: int, p2: int, out: array, limit: int) -> tuple[int, bool, int, int, int] | None:
    """Blocks from addr through the one with the end flag. Returns (address
    after it, its loop flag, p1, p2, blocks), or None when no end flag comes
    within limit blocks (not a sample)."""
    for n in range(1, limit + 1):
        hdr, p1, p2 = decode_block(ram, addr, p1, p2, out)
        addr = (addr + BLOCK) & 0xFFFF
        if hdr & 1:
            return addr, bool(hdr & 2), p1, p2, n
    return None


def _same(a: array, b: array) -> bool:
    return len(a) == len(b) and (a == b or max(abs(x - y) for x, y in zip(a, b)) <= SEAM_TOLERANCE)


def headers(ram, start: int, limit: int = MAX_BLOCKS) -> list[int]:
    """The block headers from start through the end block."""
    out = []
    for _ in range(limit):
        h = ram[start & 0xFFFF]
        out.append(h)
        if h & 1:
            break
        start += BLOCK
    return out


def plausible(ram, start: int) -> bool:
    """Whether the data at start looks like a sample an encoder wrote:
    every block's shift at most 12 (13-15 are no use, and encoders never
    write them) and the first block unfiltered (nothing comes before it to
    predict from). Over 258 snapshots this keeps 259 of the 262 samples the
    voices were playing, and drops 70% of the directory's other entries,
    most of which point at whatever the RAM holds now."""
    hs = headers(ram, start)
    return (hs[0] >> 2) & 3 == 0 and all(h >> 4 <= 12 for h in hs)


def decode(ram, start: int, loop_addr: int, max_blocks: int = MAX_BLOCKS) -> Sample | None:
    """The sample at start (with its directory entry's loop address), or
    None when the data runs on without an end flag."""
    pcm = array("h")
    got = _run(ram, start, 0, 0, pcm, max_blocks)
    if got is None:
        return None
    end, looped, p1, p2, blocks = got
    if not looped:
        return Sample(pcm, None, None, True, start, loop_addr, blocks)
    # The loop region as the first pass decoded it, when the loop address is
    # a block of the sample itself; then repeat passes, each fed the state
    # the pass before it ended on, until two in a row agree.
    prev = None
    off = loop_addr - start
    if 0 <= off < end - start and off % BLOCK == 0:
        prev = (off // BLOCK * 16, len(pcm))
    for _ in range(MAX_PASSES):
        seg = array("h")
        got = _run(ram, loop_addr, p1, p2, seg, max_blocks)
        if got is None:
            break
        _, still_loops, p1, p2, n = got
        blocks += n
        if prev is not None and _same(pcm[prev[0]:prev[1]], seg):
            return Sample(pcm, prev[0], prev[1], True, start, loop_addr, blocks)
        prev = (len(pcm), len(pcm) + len(seg))
        pcm.extend(seg)
        if not still_loops:                  # the loop's own end does not loop: it stops there
            return Sample(pcm, None, None, True, start, loop_addr, blocks)
    if prev is None:
        return Sample(pcm, None, None, True, start, loop_addr, blocks)
    return Sample(pcm, prev[0], prev[1], False, start, loop_addr, blocks)
