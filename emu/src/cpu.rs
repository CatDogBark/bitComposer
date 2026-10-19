//! The SNES sound CPU (SPC700): every instruction, cycle-counted.
//!
//! Ported from the Python prototype that passes all of the SingleStepTests
//! cases (docs/SPC-IMPORT.md); the same cases check this core in
//! `tests/single_step.rs`. Written from the published descriptions of the
//! instruction set (Nocash's fullsnes, the SNESdev wiki); the hardware's odd
//! corners (DIV past a 9-bit quotient, DAA, DAS, the 16-bit flags) follow
//! them.

/// What the CPU is wired to. `now` is the cycle count at the start of the
/// instruction, for devices (the timers) that keep time.
pub trait Bus {
    fn read(&mut self, addr: u16, now: u64) -> u8;
    fn write(&mut self, addr: u16, value: u8, now: u64);
}

/// Cycles per instruction, branches not taken (a taken branch adds 2;
/// BRA's count already includes its jump). Read off the SingleStepTests
/// cases, one entry per opcode.
pub const CYCLES: [u8; 256] = [
    2,  8,  4,  5,  3,  4,  3,  6,  2,  6,  5,  4,  5,  4,  6,  8,  // 0x
    2,  8,  4,  5,  4,  5,  5,  6,  5,  5,  6,  5,  2,  2,  4,  6,  // 1x
    2,  8,  4,  5,  3,  4,  3,  6,  2,  6,  5,  4,  5,  4,  5,  4,  // 2x
    2,  8,  4,  5,  4,  5,  5,  6,  5,  5,  6,  5,  2,  2,  3,  8,  // 3x
    2,  8,  4,  5,  3,  4,  3,  6,  2,  6,  4,  4,  5,  4,  6,  6,  // 4x
    2,  8,  4,  5,  4,  5,  5,  6,  5,  5,  4,  5,  2,  2,  4,  3,  // 5x
    2,  8,  4,  5,  3,  4,  3,  6,  2,  6,  4,  4,  5,  4,  5,  5,  // 6x
    2,  8,  4,  5,  4,  5,  5,  6,  5,  5,  5,  5,  2,  2,  3,  6,  // 7x
    2,  8,  4,  5,  3,  4,  3,  6,  2,  6,  5,  4,  5,  2,  4,  5,  // 8x
    2,  8,  4,  5,  4,  5,  5,  6,  5,  5,  5,  5,  2,  2, 12,  5,  // 9x
    3,  8,  4,  5,  3,  4,  3,  6,  2,  6,  4,  4,  5,  2,  4,  4,  // Ax
    2,  8,  4,  5,  4,  5,  5,  6,  5,  5,  5,  5,  2,  2,  3,  4,  // Bx
    3,  8,  4,  5,  4,  5,  4,  7,  2,  5,  6,  4,  5,  2,  4,  9,  // Cx
    2,  8,  4,  5,  5,  6,  6,  7,  4,  5,  5,  5,  2,  2,  6,  3,  // Dx
    2,  8,  4,  5,  3,  4,  3,  6,  2,  4,  5,  3,  4,  3,  4,  7,  // Ex
    2,  8,  4,  5,  4,  5,  5,  6,  3,  4,  5,  4,  2,  2,  4,  7,  // Fx
];

#[derive(Clone, Debug, Default)]
pub struct Cpu {
    pub a: u8,
    pub x: u8,
    pub y: u8,
    pub sp: u8,
    pub pc: u16,
    pub c: bool,
    pub z: bool,
    pub i: bool,
    pub h: bool,
    pub b: bool,
    /// The direct page: page 1 when set, page 0 when clear.
    pub p: bool,
    pub v: bool,
    pub n: bool,
    /// Cycles run since the start.
    pub cycles: u64,
    /// SLEEP or STOP ran: the CPU waits for a reset that never comes.
    pub halted: bool,
}

/// ALU operations, by the top three bits of their opcodes (0x00-0xBF).
#[derive(Clone, Copy)]
enum Alu {
    Or,
    And,
    Eor,
    Cmp,
    Adc,
    Sbc,
}

const ALU: [Alu; 6] = [Alu::Or, Alu::And, Alu::Eor, Alu::Cmp, Alu::Adc, Alu::Sbc];

impl Cpu {
    pub fn psw(&self) -> u8 {
        (self.n as u8) << 7 | (self.v as u8) << 6 | (self.p as u8) << 5 | (self.b as u8) << 4
            | (self.h as u8) << 3 | (self.i as u8) << 2 | (self.z as u8) << 1 | self.c as u8
    }

    pub fn set_psw(&mut self, v: u8) {
        self.n = v & 0x80 != 0;
        self.v = v & 0x40 != 0;
        self.p = v & 0x20 != 0;
        self.b = v & 0x10 != 0;
        self.h = v & 0x08 != 0;
        self.i = v & 0x04 != 0;
        self.z = v & 0x02 != 0;
        self.c = v & 0x01 != 0;
    }

    /// Run until at least `cycles` more have passed (or the CPU halts).
    /// Returns the instructions run.
    pub fn run<B: Bus>(&mut self, bus: &mut B, cycles: u64) -> u64 {
        let end = self.cycles + cycles;
        let mut count = 0;
        while self.cycles < end && !self.halted {
            self.step(bus);
            count += 1;
        }
        count
    }

    // ── fetching and addressing ──

    #[inline(always)]
    fn fetch<B: Bus>(&mut self, bus: &mut B) -> u8 {
        let v = bus.read(self.pc, self.cycles);
        self.pc = self.pc.wrapping_add(1);
        v
    }

    #[inline(always)]
    fn fetch16<B: Bus>(&mut self, bus: &mut B) -> u16 {
        let lo = self.fetch(bus) as u16;
        let hi = self.fetch(bus) as u16;
        hi << 8 | lo
    }

    #[inline(always)]
    fn rd<B: Bus>(&self, bus: &mut B, a: u16) -> u8 {
        bus.read(a, self.cycles)
    }

    #[inline(always)]
    fn wr<B: Bus>(&self, bus: &mut B, a: u16, v: u8) {
        bus.write(a, v, self.cycles)
    }

    /// A direct-page address.
    #[inline(always)]
    fn dp(&self, off: u8) -> u16 {
        (self.p as u16) << 8 | off as u16
    }

    /// A word in the direct page; its high byte wraps within the page.
    #[inline(always)]
    fn rd_dp_word<B: Bus>(&self, bus: &mut B, off: u8) -> u16 {
        let lo = self.rd(bus, self.dp(off)) as u16;
        let hi = self.rd(bus, self.dp(off.wrapping_add(1))) as u16;
        hi << 8 | lo
    }

    #[inline(always)]
    fn m_dp<B: Bus>(&mut self, bus: &mut B) -> u16 {
        let o = self.fetch(bus);
        self.dp(o)
    }

    #[inline(always)]
    fn m_dpx<B: Bus>(&mut self, bus: &mut B) -> u16 {
        let o = self.fetch(bus);
        self.dp(o.wrapping_add(self.x))
    }

    #[inline(always)]
    fn m_dpy<B: Bus>(&mut self, bus: &mut B) -> u16 {
        let o = self.fetch(bus);
        self.dp(o.wrapping_add(self.y))
    }

    #[inline(always)]
    fn m_absx<B: Bus>(&mut self, bus: &mut B) -> u16 {
        self.fetch16(bus).wrapping_add(self.x as u16)
    }

    #[inline(always)]
    fn m_absy<B: Bus>(&mut self, bus: &mut B) -> u16 {
        self.fetch16(bus).wrapping_add(self.y as u16)
    }

    /// [dp+X]
    #[inline(always)]
    fn m_idx<B: Bus>(&mut self, bus: &mut B) -> u16 {
        let o = self.fetch(bus).wrapping_add(self.x);
        self.rd_dp_word(bus, o)
    }

    /// [dp]+Y
    #[inline(always)]
    fn m_idy<B: Bus>(&mut self, bus: &mut B) -> u16 {
        let o = self.fetch(bus);
        self.rd_dp_word(bus, o).wrapping_add(self.y as u16)
    }

    // ── flags and arithmetic ──

    #[inline(always)]
    fn nz(&mut self, v: u8) -> u8 {
        self.n = v & 0x80 != 0;
        self.z = v == 0;
        v
    }

    #[inline(always)]
    fn nz16(&mut self, v: u16) {
        self.n = v & 0x8000 != 0;
        self.z = v == 0;
    }

    fn adc(&mut self, a: u8, b: u8) -> u8 {
        let r = a as u16 + b as u16 + self.c as u16;
        let r8 = r as u8;
        self.v = !(a ^ b) & (a ^ r8) & 0x80 != 0;
        self.h = (a ^ b ^ r8) & 0x10 != 0;
        self.c = r > 0xFF;
        self.nz(r8)
    }

    fn cmp(&mut self, a: u8, b: u8) {
        self.c = a >= b;
        self.nz(a.wrapping_sub(b));
    }

    /// An ALU operation on a and b: Some(result) to store, None for CMP.
    #[inline(always)]
    fn alu(&mut self, op: Alu, a: u8, b: u8) -> Option<u8> {
        Some(match op {
            Alu::Or => self.nz(a | b),
            Alu::And => self.nz(a & b),
            Alu::Eor => self.nz(a ^ b),
            Alu::Adc => self.adc(a, b),
            Alu::Sbc => self.adc(a, !b),
            Alu::Cmp => {
                self.cmp(a, b);
                return None;
            }
        })
    }

    fn asl(&mut self, v: u8) -> u8 {
        self.c = v & 0x80 != 0;
        self.nz(v << 1)
    }

    fn lsr(&mut self, v: u8) -> u8 {
        self.c = v & 1 != 0;
        self.nz(v >> 1)
    }

    fn rol(&mut self, v: u8) -> u8 {
        let r = v << 1 | self.c as u8;
        self.c = v & 0x80 != 0;
        self.nz(r)
    }

    fn ror(&mut self, v: u8) -> u8 {
        let r = v >> 1 | (self.c as u8) << 7;
        self.c = v & 1 != 0;
        self.nz(r)
    }

    #[inline(always)]
    fn ya(&self) -> u16 {
        (self.y as u16) << 8 | self.a as u16
    }

    #[inline(always)]
    fn set_ya(&mut self, v: u16) {
        self.y = (v >> 8) as u8;
        self.a = v as u8;
    }

    // ── stack and branches ──

    #[inline(always)]
    fn push<B: Bus>(&mut self, bus: &mut B, v: u8) {
        self.wr(bus, 0x100 | self.sp as u16, v);
        self.sp = self.sp.wrapping_sub(1);
    }

    #[inline(always)]
    fn pop<B: Bus>(&mut self, bus: &mut B) -> u8 {
        self.sp = self.sp.wrapping_add(1);
        self.rd(bus, 0x100 | self.sp as u16)
    }

    fn push_pc<B: Bus>(&mut self, bus: &mut B) {
        self.push(bus, (self.pc >> 8) as u8);
        self.push(bus, self.pc as u8);
    }

    /// Fetch a branch offset and take it when `cond`: the extra cycles.
    #[inline(always)]
    fn branch<B: Bus>(&mut self, bus: &mut B, cond: bool) -> u32 {
        let r = self.fetch(bus) as i8;
        if cond {
            self.pc = self.pc.wrapping_add(r as i16 as u16);
            2
        } else {
            0
        }
    }

    /// A memory-bit operand: (address, bit).
    #[inline(always)]
    fn membit<B: Bus>(&mut self, bus: &mut B) -> (u16, u8) {
        let w = self.fetch16(bus);
        (w & 0x1FFF, (w >> 13) as u8)
    }

    fn rmw<B: Bus>(&mut self, bus: &mut B, a: u16, f: fn(&mut Self, u8) -> u8) {
        let v = self.rd(bus, a);
        let r = f(self, v);
        self.wr(bus, a, r);
    }

    /// A store: the hardware reads the target first.
    #[inline(always)]
    fn store<B: Bus>(&mut self, bus: &mut B, a: u16, v: u8) {
        self.rd(bus, a);
        self.wr(bus, a, v);
    }

    /// Run one instruction. Returns its cycles.
    pub fn step<B: Bus>(&mut self, bus: &mut B) -> u32 {
        let op = self.fetch(bus);
        let mut extra = 0;
        match op {
            // The ALU block: OR AND EOR CMP ADC SBC by the top three bits,
            // the addressing mode by the low five.
            _ if op < 0xC0 && (4..=9).contains(&(op & 0x0F)) => {
                let kind = ALU[(op >> 5) as usize];
                match op & 0x1F {
                    0x04 | 0x05 | 0x06 | 0x07 | 0x08 | 0x14 | 0x15 | 0x16 | 0x17 => {
                        let v = match op & 0x1F {
                            0x04 => { let a = self.m_dp(bus); self.rd(bus, a) }
                            0x05 => { let a = self.fetch16(bus); self.rd(bus, a) }
                            0x06 => { let a = self.dp(self.x); self.rd(bus, a) }
                            0x07 => { let a = self.m_idx(bus); self.rd(bus, a) }
                            0x08 => self.fetch(bus),
                            0x14 => { let a = self.m_dpx(bus); self.rd(bus, a) }
                            0x15 => { let a = self.m_absx(bus); self.rd(bus, a) }
                            0x16 => { let a = self.m_absy(bus); self.rd(bus, a) }
                            _ => { let a = self.m_idy(bus); self.rd(bus, a) }
                        };
                        if let Some(r) = self.alu(kind, self.a, v) {
                            self.a = r;
                        }
                    }
                    0x09 => {
                        // op dd, ss (encoded ss dd)
                        let sa = self.m_dp(bus);
                        let src = self.rd(bus, sa);
                        let d = self.m_dp(bus);
                        let dv = self.rd(bus, d);
                        if let Some(r) = self.alu(kind, dv, src) {
                            self.wr(bus, d, r);
                        }
                    }
                    0x18 => {
                        // op dd, #ii (encoded ii dd)
                        let v = self.fetch(bus);
                        let d = self.m_dp(bus);
                        let dv = self.rd(bus, d);
                        if let Some(r) = self.alu(kind, dv, v) {
                            self.wr(bus, d, r);
                        }
                    }
                    _ => {
                        // op (X), (Y)
                        let src = self.rd(bus, self.dp(self.y));
                        let d = self.dp(self.x);
                        let dv = self.rd(bus, d);
                        if let Some(r) = self.alu(kind, dv, src) {
                            self.wr(bus, d, r);
                        }
                    }
                }
            }

            // CMP X, CMP Y
            0x1E => { let a = self.fetch16(bus); let v = self.rd(bus, a); self.cmp(self.x, v) }
            0x3E => { let a = self.m_dp(bus); let v = self.rd(bus, a); self.cmp(self.x, v) }
            0xC8 => { let v = self.fetch(bus); self.cmp(self.x, v) }
            0x5E => { let a = self.fetch16(bus); let v = self.rd(bus, a); self.cmp(self.y, v) }
            0x7E => { let a = self.m_dp(bus); let v = self.rd(bus, a); self.cmp(self.y, v) }
            0xAD => { let v = self.fetch(bus); self.cmp(self.y, v) }

            // shifts, rotates, INC and DEC: dp, abs, dp+X, A
            0x0B | 0x2B | 0x4B | 0x6B | 0x8B | 0xAB
            | 0x0C | 0x2C | 0x4C | 0x6C | 0x8C | 0xAC
            | 0x1B | 0x3B | 0x5B | 0x7B | 0x9B | 0xBB => {
                let f: fn(&mut Self, u8) -> u8 = match op & 0xE0 {
                    0x00 => Self::asl,
                    0x20 => Self::rol,
                    0x40 => Self::lsr,
                    0x60 => Self::ror,
                    0x80 => |s, v| s.nz(v.wrapping_sub(1)),
                    _ => |s, v| s.nz(v.wrapping_add(1)),
                };
                let a = match op & 0x1F {
                    0x0B => self.m_dp(bus),
                    0x0C => self.fetch16(bus),
                    _ => self.m_dpx(bus),
                };
                self.rmw(bus, a, f);
            }
            0x1C => { self.a = self.asl(self.a) }
            0x3C => { self.a = self.rol(self.a) }
            0x5C => { self.a = self.lsr(self.a) }
            0x7C => { self.a = self.ror(self.a) }
            0x9C => { self.a = self.nz(self.a.wrapping_sub(1)) }
            0xBC => { self.a = self.nz(self.a.wrapping_add(1)) }
            0x3D => { self.x = self.nz(self.x.wrapping_add(1)) }
            0x1D => { self.x = self.nz(self.x.wrapping_sub(1)) }
            0xFC => { self.y = self.nz(self.y.wrapping_add(1)) }
            0xDC => { self.y = self.nz(self.y.wrapping_sub(1)) }

            // loads (N, Z)
            0xE4 => { let a = self.m_dp(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xE5 => { let a = self.fetch16(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xE6 => { let v = self.rd(bus, self.dp(self.x)); self.a = self.nz(v) }
            0xE7 => { let a = self.m_idx(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xE8 => { let v = self.fetch(bus); self.a = self.nz(v) }
            0xF4 => { let a = self.m_dpx(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xF5 => { let a = self.m_absx(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xF6 => { let a = self.m_absy(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xF7 => { let a = self.m_idy(bus); let v = self.rd(bus, a); self.a = self.nz(v) }
            0xF8 => { let a = self.m_dp(bus); let v = self.rd(bus, a); self.x = self.nz(v) }
            0xF9 => { let a = self.m_dpy(bus); let v = self.rd(bus, a); self.x = self.nz(v) }
            0xE9 => { let a = self.fetch16(bus); let v = self.rd(bus, a); self.x = self.nz(v) }
            0xCD => { let v = self.fetch(bus); self.x = self.nz(v) }
            0xEB => { let a = self.m_dp(bus); let v = self.rd(bus, a); self.y = self.nz(v) }
            0xFB => { let a = self.m_dpx(bus); let v = self.rd(bus, a); self.y = self.nz(v) }
            0xEC => { let a = self.fetch16(bus); let v = self.rd(bus, a); self.y = self.nz(v) }
            0x8D => { let v = self.fetch(bus); self.y = self.nz(v) }
            0xBF => {
                // MOV A, (X)+
                let v = self.rd(bus, self.dp(self.x));
                self.a = self.nz(v);
                self.x = self.x.wrapping_add(1);
            }

            // stores (no flags)
            0xC4 => { let a = self.m_dp(bus); self.store(bus, a, self.a) }
            0xC5 => { let a = self.fetch16(bus); self.store(bus, a, self.a) }
            0xC6 => { let a = self.dp(self.x); self.store(bus, a, self.a) }
            0xC7 => { let a = self.m_idx(bus); self.store(bus, a, self.a) }
            0xD4 => { let a = self.m_dpx(bus); self.store(bus, a, self.a) }
            0xD5 => { let a = self.m_absx(bus); self.store(bus, a, self.a) }
            0xD6 => { let a = self.m_absy(bus); self.store(bus, a, self.a) }
            0xD7 => { let a = self.m_idy(bus); self.store(bus, a, self.a) }
            0xD8 => { let a = self.m_dp(bus); self.store(bus, a, self.x) }
            0xD9 => { let a = self.m_dpy(bus); self.store(bus, a, self.x) }
            0xC9 => { let a = self.fetch16(bus); self.store(bus, a, self.x) }
            0xCB => { let a = self.m_dp(bus); self.store(bus, a, self.y) }
            0xDB => { let a = self.m_dpx(bus); self.store(bus, a, self.y) }
            0xCC => { let a = self.fetch16(bus); self.store(bus, a, self.y) }
            0xAF => {
                // MOV (X)+, A
                self.wr(bus, self.dp(self.x), self.a);
                self.x = self.x.wrapping_add(1);
            }
            0x8F => {
                // MOV dd, #ii
                let v = self.fetch(bus);
                let d = self.m_dp(bus);
                self.store(bus, d, v);
            }
            0xFA => {
                // MOV dd, ss (encoded ss dd)
                let s = self.m_dp(bus);
                let v = self.rd(bus, s);
                let d = self.m_dp(bus);
                self.wr(bus, d, v);
            }

            // register transfers
            0x7D => { self.a = self.nz(self.x) }
            0xDD => { self.a = self.nz(self.y) }
            0x5D => { self.x = self.nz(self.a) }
            0xFD => { self.y = self.nz(self.a) }
            0x9D => { self.x = self.nz(self.sp) }
            0xBD => { self.sp = self.x }

            // stack
            0x0D => { let v = self.psw(); self.push(bus, v) }
            0x2D => { self.push(bus, self.a) }
            0x4D => { self.push(bus, self.x) }
            0x6D => { self.push(bus, self.y) }
            0x8E => { let v = self.pop(bus); self.set_psw(v) }
            0xAE => { self.a = self.pop(bus) }
            0xCE => { self.x = self.pop(bus) }
            0xEE => { self.y = self.pop(bus) }

            // branches
            0x2F => { self.branch(bus, true); }     // BRA: its count includes the jump
            0x10 => { extra = self.branch(bus, !self.n) }
            0x30 => { extra = self.branch(bus, self.n) }
            0x50 => { extra = self.branch(bus, !self.v) }
            0x70 => { extra = self.branch(bus, self.v) }
            0x90 => { extra = self.branch(bus, !self.c) }
            0xB0 => { extra = self.branch(bus, self.c) }
            0xD0 => { extra = self.branch(bus, !self.z) }
            0xF0 => { extra = self.branch(bus, self.z) }
            _ if op & 0x0F == 0x03 => {
                // BBS dp.bit / BBC dp.bit, rel (bit by the top three bits; BBC on odd rows)
                let a = self.m_dp(bus);
                let v = self.rd(bus, a);
                let set = v >> (op >> 5) & 1 != 0;
                extra = self.branch(bus, set == (op & 0x10 == 0));
            }
            0x2E => {
                // CBNE dp, rel
                let a = self.m_dp(bus);
                let v = self.rd(bus, a);
                extra = self.branch(bus, v != self.a);
            }
            0xDE => {
                // CBNE dp+X, rel
                let a = self.m_dpx(bus);
                let v = self.rd(bus, a);
                extra = self.branch(bus, v != self.a);
            }
            0xFE => {
                // DBNZ Y, rel
                self.y = self.y.wrapping_sub(1);
                extra = self.branch(bus, self.y != 0);
            }
            0x6E => {
                // DBNZ dp, rel
                let a = self.m_dp(bus);
                let v = self.rd(bus, a).wrapping_sub(1);
                self.wr(bus, a, v);
                extra = self.branch(bus, v != 0);
            }

            // jumps and calls
            0x5F => { self.pc = self.fetch16(bus) }
            0x1F => {
                // JMP [abs+X]
                let a = self.m_absx(bus);
                let lo = self.rd(bus, a) as u16;
                let hi = self.rd(bus, a.wrapping_add(1)) as u16;
                self.pc = hi << 8 | lo;
            }
            0x3F => {
                let t = self.fetch16(bus);
                self.push_pc(bus);
                self.pc = t;
            }
            0x4F => {
                // PCALL u
                let t = 0xFF00 | self.fetch(bus) as u16;
                self.push_pc(bus);
                self.pc = t;
            }
            _ if op & 0x0F == 0x01 => {
                // TCALL n
                self.push_pc(bus);
                let v = 0xFFDE - 2 * (op >> 4) as u16;
                let lo = self.rd(bus, v) as u16;
                let hi = self.rd(bus, v + 1) as u16;
                self.pc = hi << 8 | lo;
            }
            0x0F => {
                // BRK
                self.push_pc(bus);
                let v = self.psw();
                self.push(bus, v);
                self.b = true;
                self.i = false;
                let lo = self.rd(bus, 0xFFDE) as u16;
                let hi = self.rd(bus, 0xFFDF) as u16;
                self.pc = hi << 8 | lo;
            }
            0x6F => {
                let lo = self.pop(bus) as u16;
                let hi = self.pop(bus) as u16;
                self.pc = hi << 8 | lo;
            }
            0x7F => {
                let v = self.pop(bus);
                self.set_psw(v);
                let lo = self.pop(bus) as u16;
                let hi = self.pop(bus) as u16;
                self.pc = hi << 8 | lo;
            }

            // bits
            _ if op & 0x0F == 0x02 => {
                // SET1 dp.bit (even rows) / CLR1 dp.bit (odd rows)
                let a = self.m_dp(bus);
                let v = self.rd(bus, a);
                let m = 1u8 << (op >> 5);
                self.wr(bus, a, if op & 0x10 == 0 { v | m } else { v & !m });
            }
            0x0E | 0x4E => {
                // TSET1 / TCLR1 abs
                let a = self.fetch16(bus);
                let v = self.rd(bus, a);
                self.nz(self.a.wrapping_sub(v));
                self.wr(bus, a, if op == 0x0E { v | self.a } else { v & !self.a });
            }
            0x0A | 0x2A | 0x4A | 0x6A | 0x8A | 0xAA => {
                let (a, bit) = self.membit(bus);
                let m = self.rd(bus, a) >> bit & 1 != 0;
                match op {
                    0x0A => self.c |= m,
                    0x2A => self.c |= !m,
                    0x4A => self.c &= m,
                    0x6A => self.c &= !m,
                    0x8A => self.c ^= m,
                    _ => self.c = m,
                }
            }
            0xCA => {
                // MOV1 mem.bit, C
                let (a, bit) = self.membit(bus);
                let v = self.rd(bus, a);
                self.wr(bus, a, (v & !(1 << bit)) | (self.c as u8) << bit);
            }
            0xEA => {
                // NOT1 mem.bit
                let (a, bit) = self.membit(bus);
                let v = self.rd(bus, a);
                self.wr(bus, a, v ^ (1 << bit));
            }

            // flags
            0x60 => { self.c = false }
            0x80 => { self.c = true }
            0x20 => { self.p = false }
            0x40 => { self.p = true }
            0xA0 => { self.i = true }
            0xC0 => { self.i = false }
            0xED => { self.c = !self.c }
            0xE0 => { self.v = false; self.h = false }

            // 16-bit
            0xBA => {
                let o = self.fetch(bus);
                let v = self.rd_dp_word(bus, o);
                self.set_ya(v);
                self.nz16(v);
            }
            0xDA => {
                let o = self.fetch(bus);
                self.rd(bus, self.dp(o));
                self.wr(bus, self.dp(o), self.a);
                self.wr(bus, self.dp(o.wrapping_add(1)), self.y);
            }
            0x3A | 0x1A => {
                // INCW / DECW dp
                let o = self.fetch(bus);
                let w = self.rd_dp_word(bus, o);
                let v = if op == 0x3A { w.wrapping_add(1) } else { w.wrapping_sub(1) };
                self.wr(bus, self.dp(o), v as u8);
                self.wr(bus, self.dp(o.wrapping_add(1)), (v >> 8) as u8);
                self.nz16(v);
            }
            0x7A => {
                // ADDW YA, dp
                let o = self.fetch(bus);
                let w = self.rd_dp_word(bus, o);
                let a = self.ya();
                let r = a as u32 + w as u32;
                self.c = r > 0xFFFF;
                let r = r as u16;
                self.v = !(a ^ w) & (a ^ r) & 0x8000 != 0;
                self.h = (a ^ w ^ r) & 0x1000 != 0;
                self.set_ya(r);
                self.nz16(r);
            }
            0x9A => {
                // SUBW YA, dp
                let o = self.fetch(bus);
                let w = self.rd_dp_word(bus, o);
                let a = self.ya();
                self.c = a >= w;
                let r = a.wrapping_sub(w);
                self.v = (a ^ w) & (a ^ r) & 0x8000 != 0;
                self.h = (a ^ w ^ r) & 0x1000 == 0;
                self.set_ya(r);
                self.nz16(r);
            }
            0x5A => {
                // CMPW YA, dp
                let o = self.fetch(bus);
                let w = self.rd_dp_word(bus, o);
                let a = self.ya();
                self.c = a >= w;
                self.nz16(a.wrapping_sub(w));
            }
            0xCF => {
                // MUL YA
                let r = self.y as u16 * self.a as u16;
                self.set_ya(r);
                self.nz(self.y);
            }
            0x9E => {
                // DIV YA, X, with the hardware's answer past a 9-bit quotient
                let ya = self.ya() as u32;
                let x = self.x as u32;
                self.v = self.y as u32 >= x;
                self.h = (self.y & 15) >= (self.x & 15);
                let (q, r) = if (self.y as u32) < (x << 1) {
                    (ya / x, ya % x)
                } else {
                    let d = ya - (x << 9);
                    (255 - d / (256 - x), x + d % (256 - x))
                };
                self.a = q as u8;
                self.y = r as u8;
                self.nz(self.a);
            }
            0xDF => {
                // DAA
                if self.c || self.a > 0x99 {
                    self.a = self.a.wrapping_add(0x60);
                    self.c = true;
                }
                if self.h || (self.a & 15) > 9 {
                    self.a = self.a.wrapping_add(6);
                }
                self.nz(self.a);
            }
            0xBE => {
                // DAS
                if !self.c || self.a > 0x99 {
                    self.a = self.a.wrapping_sub(0x60);
                    self.c = false;
                }
                if !self.h || (self.a & 15) > 9 {
                    self.a = self.a.wrapping_sub(6);
                }
                self.nz(self.a);
            }
            0x9F => { self.a = self.nz(self.a.rotate_left(4)) }

            0x00 => {}
            0xEF | 0xFF => { self.halted = true }

            _ => unreachable!("opcode {op:#04x}"),
        }
        let n = CYCLES[op as usize] as u32 + extra;
        self.cycles += n as u64;
        n
    }
}
