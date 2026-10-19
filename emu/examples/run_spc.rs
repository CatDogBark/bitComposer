//! Run an SPC snapshot for N seconds of song and print what the driver did:
//!     cargo run --release --example run_spc -- song.spc [seconds] [--wav out.wav] [--cpu-only]
use bitcomposer_emu::spc::{self, CLOCK};
use std::time::Instant;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = &args[1];
    let seconds: f64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(10.0);
    let data = std::fs::read(path).expect("read the file");
    let (mut cpu, mut bus) = spc::load(&data).expect("an SPC file");
    let wav = args.iter().position(|a| a == "--wav").map(|i| args[i + 1].clone());
    if wav.is_some() {
        bus.dsp.audio = Some(Vec::new());
    }
    let t = Instant::now();
    let budget = (CLOCK as f64 * seconds) as u64;
    let n = if args.iter().any(|a| a == "--cpu-only") { cpu.run(&mut bus, budget) } else { spc::run(&mut cpu, &mut bus, budget) };
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
    let live: u64 = (0..8).map(|v| bus.dsp_reads[v * 0x10 + 8] + bus.dsp_reads[v * 0x10 + 9]).sum::<u64>() + bus.dsp_reads[0x7C];
    println!("  live SNES chip state read back {live} times");
    if let (Some(path), Some(pcm)) = (wav, bus.dsp.audio.as_ref()) {
        write_wav(&path, pcm);
        println!("  wrote {path} ({:.1} s)", pcm.len() as f64 / 64000.0);
    }
}

fn write_wav(path: &str, pcm: &[i16]) {
    let mut out = Vec::with_capacity(44 + pcm.len() * 2);
    let data = (pcm.len() * 2) as u32;
    out.extend_from_slice(b"RIFF");
    out.extend_from_slice(&(36 + data).to_le_bytes());
    out.extend_from_slice(b"WAVEfmt ");
    out.extend_from_slice(&16u32.to_le_bytes());
    out.extend_from_slice(&1u16.to_le_bytes());
    out.extend_from_slice(&2u16.to_le_bytes());
    out.extend_from_slice(&32000u32.to_le_bytes());
    out.extend_from_slice(&(32000u32 * 4).to_le_bytes());
    out.extend_from_slice(&4u16.to_le_bytes());
    out.extend_from_slice(&16u16.to_le_bytes());
    out.extend_from_slice(b"data");
    out.extend_from_slice(&data.to_le_bytes());
    for s in pcm {
        out.extend_from_slice(&s.to_le_bytes());
    }
    std::fs::write(path, out).expect("write the WAV");
}
