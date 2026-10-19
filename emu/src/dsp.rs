//! The SNES chip (S-DSP): eight voices walking their BRR samples, Gaussian
//! interpolation, the ADSR and GAIN envelopes, noise, pitch modulation, the
//! echo with its FIR filter and feedback, and the mixer, one output sample
//! every 32 CPU cycles (32 kHz).
//!
//! Drivers read its state back (Secret of Evermore's polls every voice's
//! envelope level and the end flags), so it runs whether or not anyone
//! listens; the mixed output exists to check it against a reference player
//! (and a conversion, a voice at a time: `mute`), and a voice's own output
//! can be recorded (`taps`) for what a converter cannot rebuild.
//!
//! Written from Nocash's fullsnes ("SNES APU DSP" chapters): the Gaussian
//! table and the interpolation's overflow behaviour, the envelope steps and
//! mode changes, KON/KOFF polled every other sample with the 5-sample
//! key-on delay, ENDX set when an end block is entered, the mixer and the
//! echo's arithmetic. The rate counter (when each envelope or noise rate
//! steps) is the commonly used model of the hardware: a global counter
//! counting down from 30719, with a phase per rate.

/// The hardware's interpolation table (fullsnes).
const GAUSS: [i32; 512] = [
    0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000, 0x000,
    0x001, 0x001, 0x001, 0x001, 0x001, 0x001, 0x001, 0x001, 0x001, 0x001, 0x001, 0x002, 0x002, 0x002, 0x002, 0x002,
    0x002, 0x002, 0x003, 0x003, 0x003, 0x003, 0x003, 0x004, 0x004, 0x004, 0x004, 0x004, 0x005, 0x005, 0x005, 0x005,
    0x006, 0x006, 0x006, 0x006, 0x007, 0x007, 0x007, 0x008, 0x008, 0x008, 0x009, 0x009, 0x009, 0x00a, 0x00a, 0x00a,
    0x00b, 0x00b, 0x00b, 0x00c, 0x00c, 0x00d, 0x00d, 0x00e, 0x00e, 0x00f, 0x00f, 0x00f, 0x010, 0x010, 0x011, 0x011,
    0x012, 0x013, 0x013, 0x014, 0x014, 0x015, 0x015, 0x016, 0x017, 0x017, 0x018, 0x018, 0x019, 0x01a, 0x01b, 0x01b,
    0x01c, 0x01d, 0x01d, 0x01e, 0x01f, 0x020, 0x020, 0x021, 0x022, 0x023, 0x024, 0x024, 0x025, 0x026, 0x027, 0x028,
    0x029, 0x02a, 0x02b, 0x02c, 0x02d, 0x02e, 0x02f, 0x030, 0x031, 0x032, 0x033, 0x034, 0x035, 0x036, 0x037, 0x038,
    0x03a, 0x03b, 0x03c, 0x03d, 0x03e, 0x040, 0x041, 0x042, 0x043, 0x045, 0x046, 0x047, 0x049, 0x04a, 0x04c, 0x04d,
    0x04e, 0x050, 0x051, 0x053, 0x054, 0x056, 0x057, 0x059, 0x05a, 0x05c, 0x05e, 0x05f, 0x061, 0x063, 0x064, 0x066,
    0x068, 0x06a, 0x06b, 0x06d, 0x06f, 0x071, 0x073, 0x075, 0x076, 0x078, 0x07a, 0x07c, 0x07e, 0x080, 0x082, 0x084,
    0x086, 0x089, 0x08b, 0x08d, 0x08f, 0x091, 0x093, 0x096, 0x098, 0x09a, 0x09c, 0x09f, 0x0a1, 0x0a3, 0x0a6, 0x0a8,
    0x0ab, 0x0ad, 0x0af, 0x0b2, 0x0b4, 0x0b7, 0x0ba, 0x0bc, 0x0bf, 0x0c1, 0x0c4, 0x0c7, 0x0c9, 0x0cc, 0x0cf, 0x0d2,
    0x0d4, 0x0d7, 0x0da, 0x0dd, 0x0e0, 0x0e3, 0x0e6, 0x0e9, 0x0ec, 0x0ef, 0x0f2, 0x0f5, 0x0f8, 0x0fb, 0x0fe, 0x101,
    0x104, 0x107, 0x10b, 0x10e, 0x111, 0x114, 0x118, 0x11b, 0x11e, 0x122, 0x125, 0x129, 0x12c, 0x130, 0x133, 0x137,
    0x13a, 0x13e, 0x141, 0x145, 0x148, 0x14c, 0x150, 0x153, 0x157, 0x15b, 0x15f, 0x162, 0x166, 0x16a, 0x16e, 0x172,
    0x176, 0x17a, 0x17d, 0x181, 0x185, 0x189, 0x18d, 0x191, 0x195, 0x19a, 0x19e, 0x1a2, 0x1a6, 0x1aa, 0x1ae, 0x1b2,
    0x1b7, 0x1bb, 0x1bf, 0x1c3, 0x1c8, 0x1cc, 0x1d0, 0x1d5, 0x1d9, 0x1dd, 0x1e2, 0x1e6, 0x1eb, 0x1ef, 0x1f3, 0x1f8,
    0x1fc, 0x201, 0x205, 0x20a, 0x20f, 0x213, 0x218, 0x21c, 0x221, 0x226, 0x22a, 0x22f, 0x233, 0x238, 0x23d, 0x241,
    0x246, 0x24b, 0x250, 0x254, 0x259, 0x25e, 0x263, 0x267, 0x26c, 0x271, 0x276, 0x27b, 0x280, 0x284, 0x289, 0x28e,
    0x293, 0x298, 0x29d, 0x2a2, 0x2a6, 0x2ab, 0x2b0, 0x2b5, 0x2ba, 0x2bf, 0x2c4, 0x2c9, 0x2ce, 0x2d3, 0x2d8, 0x2dc,
    0x2e1, 0x2e6, 0x2eb, 0x2f0, 0x2f5, 0x2fa, 0x2ff, 0x304, 0x309, 0x30e, 0x313, 0x318, 0x31d, 0x322, 0x326, 0x32b,
    0x330, 0x335, 0x33a, 0x33f, 0x344, 0x349, 0x34e, 0x353, 0x357, 0x35c, 0x361, 0x366, 0x36b, 0x370, 0x374, 0x379,
    0x37e, 0x383, 0x388, 0x38c, 0x391, 0x396, 0x39b, 0x39f, 0x3a4, 0x3a9, 0x3ad, 0x3b2, 0x3b7, 0x3bb, 0x3c0, 0x3c5,
    0x3c9, 0x3ce, 0x3d2, 0x3d7, 0x3dc, 0x3e0, 0x3e5, 0x3e9, 0x3ed, 0x3f2, 0x3f6, 0x3fb, 0x3ff, 0x403, 0x408, 0x40c,
    0x410, 0x415, 0x419, 0x41d, 0x421, 0x425, 0x42a, 0x42e, 0x432, 0x436, 0x43a, 0x43e, 0x442, 0x446, 0x44a, 0x44e,
    0x452, 0x455, 0x459, 0x45d, 0x461, 0x465, 0x468, 0x46c, 0x470, 0x473, 0x477, 0x47a, 0x47e, 0x481, 0x485, 0x488,
    0x48c, 0x48f, 0x492, 0x496, 0x499, 0x49c, 0x49f, 0x4a2, 0x4a6, 0x4a9, 0x4ac, 0x4af, 0x4b2, 0x4b5, 0x4b7, 0x4ba,
    0x4bd, 0x4c0, 0x4c3, 0x4c5, 0x4c8, 0x4cb, 0x4cd, 0x4d0, 0x4d2, 0x4d5, 0x4d7, 0x4d9, 0x4dc, 0x4de, 0x4e0, 0x4e3,
    0x4e5, 0x4e7, 0x4e9, 0x4eb, 0x4ed, 0x4ef, 0x4f1, 0x4f3, 0x4f5, 0x4f6, 0x4f8, 0x4fa, 0x4fb, 0x4fd, 0x4ff, 0x500,
    0x502, 0x503, 0x504, 0x506, 0x507, 0x508, 0x50a, 0x50b, 0x50c, 0x50d, 0x50e, 0x50f, 0x510, 0x511, 0x511, 0x512,
    0x513, 0x514, 0x514, 0x515, 0x516, 0x516, 0x517, 0x517, 0x517, 0x518, 0x518, 0x518, 0x518, 0x518, 0x519, 0x519,
];

/// Samples between steps, per 5-bit rate (rate 0 never steps).
const RATE_PERIOD: [u32; 32] = [
    COUNTER_RANGE + 1, 2048, 1536, 1280, 1024, 768, 640, 512, 384, 320, 256, 192, 160, 128, 96, 80,
    64, 48, 40, 32, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1,
];
/// Where in the global counter's cycle each rate steps.
const RATE_PHASE: [u32; 32] = [
    1, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536,
    0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 0, 0,
];
const COUNTER_RANGE: u32 = 2048 * 5 * 3;

// Register numbers: per voice (add 0x10 * voice) and global.
const V_VOLL: usize = 0x0;
const V_VOLR: usize = 0x1;
const V_PITCHL: usize = 0x2;
const V_PITCHH: usize = 0x3;
const V_SRCN: usize = 0x4;
const V_ADSR1: usize = 0x5;
const V_ADSR2: usize = 0x6;
const V_GAIN: usize = 0x7;
const V_ENVX: usize = 0x8;
const V_OUTX: usize = 0x9;
const MVOLL: usize = 0x0C;
const MVOLR: usize = 0x1C;
const EVOLL: usize = 0x2C;
const EVOLR: usize = 0x3C;
pub const KON: usize = 0x4C;
const KOFF: usize = 0x5C;
const FLG: usize = 0x6C;
pub const ENDX: usize = 0x7C;
const EFB: usize = 0x0D;
const PMON: usize = 0x2D;
const NON: usize = 0x3D;
const EON: usize = 0x4D;
const DIR: usize = 0x5D;
const ESA: usize = 0x6D;
const EDL: usize = 0x7D;

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
enum Env {
    #[default]
    Release,
    Attack,
    Decay,
    Sustain,
}

#[derive(Clone, Default)]
struct Voice {
    /// The decoded samples ahead of and behind the play position, doubled
    /// 15-bit values; `pos` is where the next four go (the oldest).
    buf: [i32; 12],
    pos: usize,
    /// The pitch counter: 0x1000 per sample, four samples a decode.
    interp: u32,
    /// The current BRR block and the byte in it the next decode starts at.
    brr_addr: u16,
    brr_offset: u16,
    /// The block's 16 samples, decoded when it is entered.
    block: [i32; 16],
    p1: i32,
    p2: i32,
    kon_delay: u8,
    env: i32,
    hidden_env: i32,
    mode: Env,
    /// This voice's output last sample, which pitch-modulates the next voice.
    out: i32,
    /// Not keyed on since the snapshot: an SPC file does not say where a
    /// voice was in its sample, so it waits silent (not decoding, not
    /// setting ENDX from whatever RAM holds) until the driver keys it on.
    parked: bool,
}

pub struct Dsp {
    pub regs: [u8; 128],
    voices: [Voice; 8],
    counter: u32,
    every_other: bool,
    /// KON as the CPU last wrote it, until the next poll.
    new_kon: u8,
    noise: i32,
    echo_offset: u32,
    echo_length: u32,
    fir: [[i32; 2]; 8],
    fir_pos: usize,
    /// The mixed output, when kept: interleaved left, right.
    pub audio: Option<Vec<i16>>,
    /// Voices left out of the mixed output and the echo (bit n, voice n),
    /// still running: to hear one voice alone.
    pub mute: u8,
    /// Voices whose own output (after the envelope, before the volumes) is
    /// kept in `tapped`, one sample each per sample, in voice order: what
    /// pitch modulation made of a voice, for a converter to keep as it was.
    pub taps: u8,
    pub tapped: Vec<i16>,
    /// Samples run so far.
    pub samples: u64,
    /// Every key-on as the SNES chip acted on it, with the directory entry it
    /// read then: many drivers write a voice's entry just before keying it, so
    /// the snapshot's directory need not hold what a note plays.
    pub keyons: Vec<KeyOn>,
}

/// A key-on as it took effect.
#[derive(Clone, Copy, Debug)]
pub struct KeyOn {
    pub sample: u64,
    pub voice: u8,
    pub srcn: u8,
    pub start: u16,
    pub loop_addr: u16,
}

#[inline(always)]
fn clamp16(v: i32) -> i32 {
    v.clamp(-32768, 32767)
}

impl Dsp {
    /// The SNES chip with its registers as a snapshot left them. Its inner
    /// state (where each voice is in its sample) is not in an SPC file, so
    /// the voices start silent until the driver keys them on.
    pub fn new(regs: [u8; 128]) -> Dsp {
        let mut voices: [Voice; 8] = Default::default();
        for v in voices.iter_mut() {
            v.parked = true;
        }
        let d = Dsp {
            regs,
            voices,
            counter: 0,
            every_other: false,
            new_kon: 0,
            noise: 0x4000,
            echo_offset: 0,
            echo_length: 0,
            fir: [[0; 2]; 8],
            fir_pos: 0,
            audio: None,
            mute: 0,
            taps: 0,
            tapped: Vec::new(),
            samples: 0,
            keyons: Vec::new(),
        };
        // The snapshot's KON is what the driver last wrote, long since acted on:
        // it reads back as written but keys nothing on.
        d
    }

    /// The CPU wrote a register.
    pub fn write(&mut self, reg: usize, v: u8) {
        match reg {
            KON => {
                self.new_kon = v;
                self.regs[KON] = v;
            }
            ENDX => self.regs[ENDX] = 0, // any write clears it
            _ => self.regs[reg] = v,
        }
    }

    #[inline(always)]
    fn steps(&self, rate: usize) -> bool {
        (self.counter + RATE_PHASE[rate]) % RATE_PERIOD[rate] == 0
    }

    /// One 32 kHz sample.
    pub fn sample(&mut self, ram: &mut [u8]) {
        self.samples += 1;
        self.counter = if self.counter == 0 { COUNTER_RANGE - 1 } else { self.counter - 1 };
        let flg = self.regs[FLG];
        if self.steps((flg & 0x1F) as usize) {
            let n = self.noise;
            self.noise = (n >> 1) | (((n << 14) ^ (n << 13)) & 0x4000);
        }
        // KON and KOFF are polled every other sample.
        self.every_other = !self.every_other;
        let (kon, koff) = if self.every_other {
            let k = self.new_kon;
            self.new_kon = 0;
            self.regs[ENDX] &= !k;
            (k, self.regs[KOFF])
        } else {
            (0, 0)
        };
        let (pmon, non, eon) = (self.regs[PMON], self.regs[NON], self.regs[EON]);
        let dir = (self.regs[DIR] as u16) << 8;
        let (mut main_l, mut main_r, mut echo_l, mut echo_r) = (0i32, 0i32, 0i32, 0i32);
        let mut prev_out = 0;
        let mut outs = [0i32; 8];
        let mute = self.mute;
        for vi in 0..8 {
            let base = vi * 0x10;
            let bit = 1u8 << vi;
            let r = |reg: usize| self.regs[base + reg];
            let mut pitch = ((r(V_PITCHH) as u32 & 0x3F) << 8 | r(V_PITCHL) as u32) as i32;
            if pmon & bit != 0 && vi > 0 {
                pitch += ((prev_out >> 5) * pitch) >> 10;
            }
            let (voll, volr) = (r(V_VOLL) as i8 as i32, r(V_VOLR) as i8 as i32);
            let (adsr1, adsr2, gain, srcn) = (r(V_ADSR1), r(V_ADSR2), r(V_GAIN), r(V_SRCN));
            let v = &mut self.voices[vi];

            // Key off (or the soft reset), then key on.
            if self.every_other && (koff & bit != 0 || flg & 0x80 != 0) {
                v.mode = Env::Release;
            }
            if flg & 0x80 != 0 {
                v.env = 0;
            }
            if kon & bit != 0 {
                v.kon_delay = 5;
                v.mode = Env::Attack;
                v.parked = false;
            }
            if v.parked {
                v.out = 0;
                prev_out = 0;
                self.regs[base + V_ENVX] = 0;
                self.regs[base + V_OUTX] = 0;
                continue;
            }

            // The key-on delay: five silent samples, three of them decoding.
            if v.kon_delay > 0 {
                if v.kon_delay == 5 {
                    let e = (dir + 4 * srcn as u16) as usize;
                    v.brr_addr = ram[e & 0xFFFF] as u16 | (ram[(e + 1) & 0xFFFF] as u16) << 8;
                    let loop_addr = ram[(e + 2) & 0xFFFF] as u16 | (ram[(e + 3) & 0xFFFF] as u16) << 8;
                    self.keyons.push(KeyOn { sample: self.samples, voice: vi as u8, srcn, start: v.brr_addr, loop_addr });
                    v.brr_offset = 1;
                    v.pos = 0;
                    v.p1 = 0;
                    v.p2 = 0;
                    v.buf = [0; 12];
                    Self::enter_block(v, ram);
                }
                v.env = 0;
                v.hidden_env = 0;
                v.interp = 0;
                v.kon_delay -= 1;
                if v.kon_delay & 3 != 0 {
                    v.interp = 0x4000;
                }
                pitch = 0;
            }

            // The output: Gaussian interpolation of four samples, or noise.
            let mut out = if non & bit != 0 {
                ((self.noise << 17) >> 16) & !1
            } else {
                let i = ((v.interp >> 4) & 0xFF) as usize;
                let at = |k: u32| v.buf[(v.pos + (v.interp >> 12) as usize + k as usize) % 12];
                let mut o = (GAUSS[255 - i] * at(0)) >> 11;
                o += (GAUSS[511 - i] * at(1)) >> 11;
                o += (GAUSS[256 + i] * at(2)) >> 11;
                o = o as i16 as i32;
                o += (GAUSS[i] * at(3)) >> 11;
                clamp16(o) & !1
            };
            out = ((out * v.env) >> 11) & !1;
            v.out = out;
            prev_out = out;
            outs[vi] = out;

            // The envelope.
            if v.kon_delay == 0 {
                Self::envelope(v, adsr1, adsr2, gain, |rate| {
                    (self.counter + RATE_PHASE[rate]) % RATE_PERIOD[rate] == 0
                });
            }

            // The pitch counter, and a decode whenever four samples are used.
            if v.interp >= 0x4000 {
                Self::decode4(v, ram, dir, srcn, &mut self.regs[ENDX], bit);
            }
            v.interp = ((v.interp & 0x3FFF) as i32 + pitch).min(0x7FFF) as u32;

            // Into the mix.
            let al = (out * voll) >> 7;
            let ar = (out * volr) >> 7;
            if mute & bit == 0 {
                main_l = clamp16(main_l + al);
                main_r = clamp16(main_r + ar);
                if eon & bit != 0 {
                    echo_l = clamp16(echo_l + al);
                    echo_r = clamp16(echo_r + ar);
                }
            }
            self.regs[base + V_ENVX] = (v.env >> 4) as u8;
            self.regs[base + V_OUTX] = (out >> 8) as u8;
        }

        if self.taps != 0 {
            for (vi, out) in outs.iter().enumerate() {
                if self.taps >> vi & 1 != 0 {
                    self.tapped.push(*out as i16);
                }
            }
        }

        // The echo: read the oldest entry, filter, feed back, write.
        let esa = (self.regs[ESA] as u32) << 8;
        let addr = ((esa + self.echo_offset) & 0xFFFF) as usize;
        let rd16 = |a: usize| (ram[a & 0xFFFF] as u16 | (ram[(a + 1) & 0xFFFF] as u16) << 8) as i16 as i32;
        self.fir_pos = (self.fir_pos + 1) & 7;
        self.fir[self.fir_pos] = [rd16(addr) >> 1, rd16(addr + 2) >> 1];
        let mut fir_out = [0i32; 2];
        for (ch, out) in fir_out.iter_mut().enumerate() {
            let mut s = 0i32;
            for k in 0..7 {
                let tap = self.regs[0x0F + 0x10 * k] as i8 as i32;
                s += (self.fir[(self.fir_pos + 1 + k) & 7][ch] * tap) >> 6;
            }
            s = s as i16 as i32;
            s += (self.fir[self.fir_pos][ch] * self.regs[0x7F] as i8 as i32) >> 6;
            *out = clamp16(s) & !1;
        }
        let efb = self.regs[EFB] as i8 as i32;
        let in_l = clamp16(echo_l + ((fir_out[0] * efb) >> 7)) & !1;
        let in_r = clamp16(echo_r + ((fir_out[1] * efb) >> 7)) & !1;
        if flg & 0x20 == 0 {
            for (k, v) in [in_l, in_r].iter().enumerate() {
                let a = addr + 2 * k;
                ram[a & 0xFFFF] = *v as u8;
                ram[(a + 1) & 0xFFFF] = (*v >> 8) as u8;
            }
        }
        if self.echo_offset == 0 {
            self.echo_length = (self.regs[EDL] as u32 & 0x0F) << 11;
        }
        self.echo_offset += 4;
        if self.echo_offset >= self.echo_length {
            self.echo_offset = 0;
        }

        // The main output.
        if let Some(audio) = self.audio.as_mut() {
            let mix = |m: i32, mv: usize, f: i32, ev: usize, regs: &[u8; 128]| {
                let v = clamp16(((m * regs[mv] as i8 as i32) >> 7) + ((f * regs[ev] as i8 as i32) >> 7));
                if regs[FLG] & 0x40 != 0 { 0 } else { v }
            };
            audio.push(mix(main_l, MVOLL, fir_out[0], EVOLL, &self.regs) as i16);
            audio.push(mix(main_r, MVOLR, fir_out[1], EVOLR, &self.regs) as i16);
        }
    }

    /// Entering a BRR block: its header and its 16 samples.
    fn enter_block(v: &mut Voice, ram: &[u8]) {
        let hdr = ram[v.brr_addr as usize];
        let shift = (hdr >> 4) as i32;
        let filt = (hdr >> 2) & 3;
        for k in 0..16 {
            let byte = ram[(v.brr_addr as usize + 1 + k / 2) & 0xFFFF];
            let nib = if k % 2 == 0 { byte >> 4 } else { byte & 0x0F } as i32;
            let mut s = if nib & 8 != 0 { nib - 16 } else { nib };
            s = if shift <= 12 { (s << shift) >> 1 } else if s < 0 { -2048 } else { 0 };
            let (p1, p2) = (v.p1, v.p2);
            s += match filt {
                1 => p1 + ((-p1) >> 4),
                2 => (p1 << 1) + ((-3 * p1) >> 5) - p2 + (p2 >> 4),
                3 => (p1 << 1) + ((-13 * p1) >> 6) - p2 + ((3 * p2) >> 4),
                _ => 0,
            };
            s = clamp16(s);
            s = ((s & 0x7FFF) ^ 0x4000) - 0x4000; // 15 bits: bit 15 is lost
            v.p2 = p1;
            v.p1 = s;
            v.block[k] = s * 2;
        }
    }

    /// Four more samples into the voice's buffer; at a block's end, the
    /// next block, or the loop (or, after an end-without-loop, release).
    fn decode4(v: &mut Voice, ram: &[u8], dir: u16, srcn: u8, endx: &mut u8, bit: u8) {
        let first = ((v.brr_offset - 1) * 2) as usize;
        if first == 0 && ram[v.brr_addr as usize] & 1 != 0 {
            *endx |= bit; // set as an end block starts decoding, not when it ends (fullsnes)
        }
        for k in 0..4 {
            v.buf[(v.pos + k) % 12] = v.block[first + k];
        }
        v.pos = (v.pos + 4) % 12;
        v.brr_offset += 2;
        if v.brr_offset >= 9 {
            let hdr = ram[v.brr_addr as usize];
            if hdr & 1 != 0 {
                let e = (dir + 4 * srcn as u16) as usize;
                v.brr_addr = ram[(e + 2) & 0xFFFF] as u16 | (ram[(e + 3) & 0xFFFF] as u16) << 8;
                if hdr & 2 == 0 {
                    v.mode = Env::Release;
                    v.env = 0;
                }
            } else {
                v.brr_addr = v.brr_addr.wrapping_add(9);
            }
            v.brr_offset = 1;
            Self::enter_block(v, ram);
        }
    }

    fn envelope(v: &mut Voice, adsr1: u8, adsr2: u8, gain: u8, steps: impl Fn(usize) -> bool) {
        let mut env = v.env;
        if v.mode == Env::Release {
            env -= 8;
            v.env = env.max(0);
            return;
        }
        let rate;
        let mut boundary = adsr2;
        if adsr1 & 0x80 != 0 {
            if v.mode == Env::Attack {
                rate = ((adsr1 & 0x0F) * 2 + 1) as usize;
                env += if rate < 31 { 0x20 } else { 0x400 };
            } else {
                env -= 1;
                env -= env >> 8;
                rate = if v.mode == Env::Decay { (((adsr1 >> 4) & 7) * 2 + 16) as usize } else { (adsr2 & 0x1F) as usize };
            }
        } else {
            boundary = gain; // the hardware reads its decay boundary from GAIN here
            if gain & 0x80 == 0 {
                env = (gain as i32 & 0x7F) << 4;
                rate = 31;
            } else {
                rate = (gain & 0x1F) as usize;
                match (gain >> 5) & 3 {
                    0 => env -= 0x20,
                    1 => {
                        env -= 1;
                        env -= env >> 8;
                    }
                    2 => env += 0x20,
                    _ => env += if (v.hidden_env as u32) < 0x600 { 0x20 } else { 8 },
                }
            }
        }
        if v.mode == Env::Decay && (env >> 8) == (boundary >> 5) as i32 {
            v.mode = Env::Sustain;
        }
        v.hidden_env = env;
        if !(0..=0x7FF).contains(&env) {
            env = if env < 0 { 0 } else { 0x7FF };
            if v.mode == Env::Attack {
                v.mode = Env::Decay;
            }
        }
        if steps(rate) {
            v.env = env;
        }
    }
}
