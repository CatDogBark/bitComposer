//! Run an SPC snapshot for N seconds of song and print what the driver did:
//!     cargo run --release --example run_spc -- song.spc [seconds]
use bitcomposer_emu::spc::{self, CLOCK};
use std::time::Instant;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = &args[1];
    let seconds: f64 = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(10.0);
    let data = std::fs::read(path).expect("read the file");
    let (mut cpu, mut bus) = spc::load(&data).expect("an SPC file");
    let t = Instant::now();
    let n = cpu.run(&mut bus, (CLOCK as f64 * seconds) as u64);
    let dt = t.elapsed().as_secs_f64();
    let song = cpu.cycles as f64 / CLOCK as f64;
    let kon: Vec<_> = bus.log.iter().filter(|w| w.reg == 0x4C && w.value != 0).collect();
    let notes: u32 = kon.iter().map(|w| w.value.count_ones()).sum();
    println!("{}", path.rsplit('/').next().unwrap());
    println!("  {song:.1} s of song in {dt:.4} s wall: {:.0}x real time; {:.0} M instructions/s",
             song / dt, n as f64 / dt / 1e6);
    println!("  {} SNES chip writes, {} key-on writes ({notes} notes); halted={}", bus.log.len(), kon.len(), cpu.halted);
    let first: Vec<String> = kon.iter().take(6).map(|w| format!("{:.2}", w.cycle as f64 / CLOCK as f64)).collect();
    println!("  first notes at {} s", first.join(", "));
}
