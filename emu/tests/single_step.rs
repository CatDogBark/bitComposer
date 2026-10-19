//! The SingleStepTests SPC700 suite: 1,000 cases for each instruction, each
//! with the registers and RAM before and after and every bus cycle. Not in
//! the repository (81 MB); point SPC700_TESTS at its spc700/v1 folder
//! (https://github.com/SingleStepTests/ProcessorTests). Without it the test
//! says so and passes.
use bitcomposer_emu::cpu::{Bus, Cpu};
use serde_json::Value;
use std::path::PathBuf;
use std::time::Instant;

struct Flat(Vec<u8>);

impl Bus for Flat {
    fn read(&mut self, a: u16, _: u64) -> u8 {
        self.0[a as usize]
    }
    fn write(&mut self, a: u16, v: u8, _: u64) {
        self.0[a as usize] = v
    }
}

fn byte(v: &Value) -> u8 {
    v.as_u64().unwrap() as u8
}

#[test]
fn every_instruction_matches_the_suite() {
    let Some(dir) = std::env::var_os("SPC700_TESTS").map(PathBuf::from) else {
        eprintln!("SPC700_TESTS not set: the instruction suite was skipped");
        return;
    };
    let mut bus = Flat(vec![0; 0x10000]);
    let mut cpu = Cpu::default();
    let (mut total, mut failed) = (0u64, Vec::new());
    let mut stepping = std::time::Duration::ZERO;
    for op in 0..=255u8 {
        if op == 0xEF || op == 0xFF {
            continue; // SLEEP, STOP: the suite expects the clock to run on
        }
        let text = std::fs::read_to_string(dir.join(format!("{op:02x}.json"))).unwrap();
        let cases: Value = serde_json::from_str(&text).unwrap();
        for case in cases.as_array().unwrap() {
            let (ini, fin) = (&case["initial"], &case["final"]);
            for e in ini["ram"].as_array().unwrap() {
                bus.0[e[0].as_u64().unwrap() as usize] = byte(&e[1]);
            }
            cpu.a = byte(&ini["a"]);
            cpu.x = byte(&ini["x"]);
            cpu.y = byte(&ini["y"]);
            cpu.sp = byte(&ini["sp"]);
            cpu.pc = ini["pc"].as_u64().unwrap() as u16;
            cpu.set_psw(byte(&ini["psw"]));
            cpu.cycles = 0;
            cpu.halted = false;
            let t = Instant::now();
            cpu.step(&mut bus);
            stepping += t.elapsed();
            total += 1;
            let mut ok = cpu.a == byte(&fin["a"]) && cpu.x == byte(&fin["x"]) && cpu.y == byte(&fin["y"])
                && cpu.sp == byte(&fin["sp"]) && cpu.pc as u64 == fin["pc"].as_u64().unwrap()
                && cpu.psw() == byte(&fin["psw"])
                && cpu.cycles == case["cycles"].as_array().unwrap().len() as u64;
            for e in fin["ram"].as_array().unwrap() {
                ok &= bus.0[e[0].as_u64().unwrap() as usize] == byte(&e[1]);
            }
            if !ok {
                failed.push(case["name"].as_str().unwrap().to_string());
            }
            for e in ini["ram"].as_array().unwrap().iter().chain(fin["ram"].as_array().unwrap()) {
                bus.0[e[0].as_u64().unwrap() as usize] = 0;
            }
        }
    }
    eprintln!("{} of {total} cases pass; {:.1} ns a step", total - failed.len() as u64,
              stepping.as_nanos() as f64 / total as f64);
    assert!(failed.is_empty(), "{} cases fail, first: {:?}", failed.len(), &failed[..failed.len().min(10)]);
}
