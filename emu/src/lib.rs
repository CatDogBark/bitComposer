//! The SNES sound CPU (SPC700) and SNES chip (S-DSP) emulator for bitComposer's
//! SPC import: step 3 of `docs/SPC-IMPORT.md`. It runs the game's own music
//! driver from an SPC snapshot and logs what the driver tells the SNES chip.
//!
//! The emulator is plain Rust; built with the `python` feature (as the wheel
//! is) it is also the Python module `bitcomposer_emu`.

pub mod cpu;
pub mod dsp;
pub mod spc;

/// The crate's version, also the Python module's `__version__`.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(feature = "python")]
mod python {
    use crate::spc;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::PyBytes;

    /// run(data, seconds, audio=False, mute=0, taps=0) -> (writes, keyons, audio, tapped, cycles, instructions)
    ///
    /// Run an SPC snapshot's own driver for `seconds` of song. `writes` is
    /// every write it made to the SNES chip, 10 bytes each: the CPU cycle
    /// (u64), the register, the value. `keyons` is every key-on as the SNES
    /// chip acted on it, 14 bytes each: the sample count (u64), the voice,
    /// the directory entry, and the start and loop addresses it read (u16).
    /// All little-endian. `audio` is the mixed output (32 kHz, stereo,
    /// 16-bit) when asked for, else None; `mute` leaves voices out of it
    /// (bit n, voice n). `tapped` is, for the voices in `taps`, each one's
    /// own output (after its envelope, before its volumes), 16-bit, the
    /// tapped voices interleaved in voice order; None when `taps` is 0.
    #[pyfunction]
    #[pyo3(signature = (data, seconds, audio = false, mute = 0, taps = 0))]
    #[allow(clippy::type_complexity)]
    fn run<'py>(py: Python<'py>, data: &[u8], seconds: f64, audio: bool, mute: u8, taps: u8)
        -> PyResult<(Bound<'py, PyBytes>, Bound<'py, PyBytes>, Option<Bound<'py, PyBytes>>, Option<Bound<'py, PyBytes>>, u64, u64)> {
        let (mut cpu, mut bus) = spc::load(data).map_err(PyValueError::new_err)?;
        if audio {
            bus.dsp.audio = Some(Vec::new());
        }
        bus.dsp.mute = mute;
        bus.dsp.taps = taps;
        let budget = (spc::CLOCK as f64 * seconds.max(0.0)) as u64;
        let n = py.allow_threads(|| spc::run(&mut cpu, &mut bus, budget));
        let mut out = Vec::with_capacity(bus.log.len() * 10);
        for w in &bus.log {
            out.extend_from_slice(&w.cycle.to_le_bytes());
            out.push(w.reg);
            out.push(w.value);
        }
        let mut kons = Vec::with_capacity(bus.dsp.keyons.len() * 14);
        for k in &bus.dsp.keyons {
            kons.extend_from_slice(&k.sample.to_le_bytes());
            kons.push(k.voice);
            kons.push(k.srcn);
            kons.extend_from_slice(&k.start.to_le_bytes());
            kons.extend_from_slice(&k.loop_addr.to_le_bytes());
        }
        let bytes = |a: &[i16]| {
            let mut b = Vec::with_capacity(a.len() * 2);
            for s in a {
                b.extend_from_slice(&s.to_le_bytes());
            }
            PyBytes::new(py, &b)
        };
        let pcm = bus.dsp.audio.as_deref().map(bytes);
        let tapped = (taps != 0).then(|| bytes(&bus.dsp.tapped));
        Ok((PyBytes::new(py, &out), PyBytes::new(py, &kons), pcm, tapped, cpu.cycles, n))
    }

    /// solos(data, seconds) -> (voices, frames)
    ///
    /// Each voice alone, as `run` with the other seven muted gives it, from
    /// one run: `voices` is eight streams one after another (voice 0 first),
    /// each `frames` stereo frames of 16-bit little-endian, left then right.
    #[pyfunction]
    fn solos<'py>(py: Python<'py>, data: &[u8], seconds: f64) -> PyResult<(Bound<'py, PyBytes>, u64)> {
        let (mut cpu, mut bus) = spc::load(data).map_err(PyValueError::new_err)?;
        bus.dsp.solos = Some(Box::new(crate::dsp::Solos::new(&bus.ram)));
        let budget = (spc::CLOCK as f64 * seconds.max(0.0)) as u64;
        py.allow_threads(|| spc::run(&mut cpu, &mut bus, budget));
        let solos = bus.dsp.solos.take().expect("solos kept");
        let frames = solos.out[0].len() / 2;
        let mut b = Vec::with_capacity(8 * frames * 4);
        for out in &solos.out {
            for s in out {
                b.extend_from_slice(&s.to_le_bytes());
            }
        }
        Ok((PyBytes::new(py, &b), frames as u64))
    }

    #[pymodule]
    fn bitcomposer_emu(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add("__version__", super::VERSION)?;
        m.add("CLOCK", spc::CLOCK)?;
        m.add_function(wrap_pyfunction!(run, m)?)?;
        m.add_function(wrap_pyfunction!(solos, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn has_a_version() {
        assert!(!super::VERSION.is_empty());
    }
}
