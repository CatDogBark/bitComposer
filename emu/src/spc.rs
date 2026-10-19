//! The SNES sound unit around the CPU: 64 KB of RAM, the I/O registers at
//! 0xF0-0xFF (the three timers, the SNES chip's address and data ports, the
//! ports to the main CPU), the boot ROM, and a log of every write the
//! driver makes to the SNES chip. Loaded from an SPC snapshot.
//!
//! The SNES chip (dsp.rs) runs alongside, one sample every 32 CPU cycles
//! (`run`), so what the driver reads back from it (envelope levels, end
//! flags, the echo in RAM) is live.

use crate::cpu::{Bus, Cpu};
use crate::dsp::Dsp;

/// The SNES sound unit's 64-byte boot ROM, mapped over 0xFFC0-0xFFFF while
/// CONTROL bit 7 is set.
const IPL: [u8; 64] = [
    0xCD, 0xEF, 0xBD, 0xE8, 0x00, 0xC6, 0x1D, 0xD0, 0xFC, 0x8F, 0xAA, 0xF4, 0x8F, 0xBB, 0xF5, 0x78,
    0xCC, 0xF4, 0xD0, 0xFB, 0x2F, 0x19, 0xEB, 0xF4, 0xD0, 0xFC, 0x7E, 0xF4, 0xD0, 0x0B, 0xE4, 0xF5,
    0xCB, 0xF4, 0xD7, 0x00, 0xFC, 0xD0, 0xF3, 0xAB, 0x01, 0x10, 0xEF, 0x7E, 0xF4, 0x10, 0xEB, 0xBA,
    0xF6, 0xDA, 0x00, 0xBA, 0xF4, 0xC4, 0xF4, 0xDD, 0x5D, 0xD0, 0xDB, 0x1F, 0x00, 0x00, 0xC0, 0xFF,
];

/// The CPU clock: cycles per second.
pub const CLOCK: u64 = 1_024_000;
const MAGIC: &[u8] = b"SNES-SPC700 Sound File Data";
const SIZE: usize = 0x10200;

/// One write the driver made to an SNES chip register.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DspWrite {
    pub cycle: u64,
    pub reg: u8,
    pub value: u8,
}

pub struct SpcBus {
    pub ram: Vec<u8>,
    pub dsp: Dsp,
    next_sample: u64,
    control: u8,
    dspaddr: u8,
    ports_in: [u8; 4],
    pub ports_out: [u8; 4],
    target: [u32; 3],
    out: [u8; 3],
    stage: [u32; 3],
    last: [u64; 3],
    pub log: Vec<DspWrite>,
    pub dsp_reads: [u64; 128],
    pub rom_reads: u64,
}

impl SpcBus {
    /// Bring timer t up to `now` (lazily: only when it is read or set).
    fn timer(&mut self, t: usize, now: u64) {
        let period = if t == 2 { 16 } else { 128 };
        let ticks = (now - self.last[t]) / period;
        self.last[t] += ticks * period;
        if ticks > 0 && self.control >> t & 1 != 0 {
            let total = self.stage[t] as u64 + ticks;
            let target = self.target[t] as u64;
            self.out[t] = ((self.out[t] as u64 + total / target) & 15) as u8;
            self.stage[t] = (total % target) as u32;
        }
    }
}

impl Bus for SpcBus {
    #[inline(always)]
    fn read(&mut self, a: u16, now: u64) -> u8 {
        if (0xF0..=0xFF).contains(&a) {
            return match a {
                0xF2 => self.dspaddr,
                0xF3 => {
                    let reg = (self.dspaddr & 0x7F) as usize;
                    self.dsp_reads[reg] += 1;
                    self.dsp.regs[reg]
                }
                0xF4..=0xF7 => self.ports_in[(a - 0xF4) as usize],
                0xF8 | 0xF9 => self.ram[a as usize],
                0xFD..=0xFF => {
                    let t = (a - 0xFD) as usize;
                    self.timer(t, now);
                    let v = self.out[t];
                    self.out[t] = 0;
                    v
                }
                _ => 0,
            };
        }
        if a >= 0xFFC0 && self.control & 0x80 != 0 {
            self.rom_reads += 1;
            return IPL[(a - 0xFFC0) as usize];
        }
        self.ram[a as usize]
    }

    #[inline(always)]
    fn write(&mut self, a: u16, v: u8, now: u64) {
        if !(0xF0..=0xFF).contains(&a) {
            self.ram[a as usize] = v;
            return;
        }
        match a {
            0xF1 => {
                for t in 0..3 {
                    self.timer(t, now);
                    if v >> t & 1 != 0 && self.control >> t & 1 == 0 {
                        self.stage[t] = 0;
                        self.out[t] = 0;
                    }
                }
                if v & 0x10 != 0 {
                    self.ports_in[0] = 0;
                    self.ports_in[1] = 0;
                }
                if v & 0x20 != 0 {
                    self.ports_in[2] = 0;
                    self.ports_in[3] = 0;
                }
                self.control = v;
            }
            0xF2 => self.dspaddr = v,
            0xF3 => {
                let reg = self.dspaddr;
                if reg < 0x80 {
                    self.dsp.write(reg as usize, v);
                    self.log.push(DspWrite { cycle: now, reg, value: v });
                }
            }
            0xF4..=0xF7 => self.ports_out[(a - 0xF4) as usize] = v,
            0xF8 | 0xF9 => self.ram[a as usize] = v,
            0xFA..=0xFC => {
                let t = (a - 0xFA) as usize;
                self.timer(t, now);
                self.target[t] = if v == 0 { 256 } else { v as u32 };
            }
            _ => {}
        }
    }
}

/// An SPC snapshot loaded and ready to run: the CPU at its saved state, the
/// sound unit around it.
pub fn load(data: &[u8]) -> Result<(Cpu, SpcBus), String> {
    if !data.starts_with(MAGIC) {
        return Err("not an SPC file".into());
    }
    if data.len() < SIZE {
        return Err(format!("{} bytes; an SPC file is at least {SIZE}", data.len()));
    }
    let ram = data[0x100..0x10100].to_vec();
    let mut regs = [0u8; 128];
    regs.copy_from_slice(&data[0x10100..0x10180]);
    let r = |a: usize| ram[a];
    let target = |a: usize| if r(a) == 0 { 256 } else { r(a) as u32 };
    let bus = SpcBus {
        control: r(0xF1),
        dspaddr: r(0xF2),
        ports_in: [r(0xF4), r(0xF5), r(0xF6), r(0xF7)],
        ports_out: [0; 4],
        target: [target(0xFA), target(0xFB), target(0xFC)],
        out: [r(0xFD) & 15, r(0xFE) & 15, r(0xFF) & 15],
        stage: [0; 3],
        last: [0; 3],
        log: Vec::new(),
        dsp_reads: [0; 128],
        rom_reads: 0,
        ram,
        dsp: Dsp::new(regs),
        next_sample: 32,
    };
    let mut cpu = Cpu {
        pc: data[0x25] as u16 | (data[0x26] as u16) << 8,
        a: data[0x27],
        x: data[0x28],
        y: data[0x29],
        sp: data[0x2B],
        ..Cpu::default()
    };
    cpu.set_psw(data[0x2A]);
    Ok((cpu, bus))
}

/// Run the sound unit for at least `cycles` CPU cycles: the CPU, with the
/// SNES chip stepping a sample every 32 cycles. Returns the instructions run.
pub fn run(cpu: &mut Cpu, bus: &mut SpcBus, cycles: u64) -> u64 {
    let end = cpu.cycles + cycles;
    let mut n = 0;
    while cpu.cycles < end && !cpu.halted {
        cpu.step(bus);
        n += 1;
        while bus.next_sample <= cpu.cycles {
            bus.dsp.sample(&mut bus.ram);
            bus.next_sample += 32;
        }
    }
    n
}
