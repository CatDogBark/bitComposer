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

    /// run(data, seconds, audio=False) -> (writes, audio, cycles, instructions)
    ///
    /// Run an SPC snapshot's own driver for `seconds` of song. `writes` is
    /// every write it made to the SNES chip, 10 bytes each: the CPU cycle
    /// (u64), the register, the value, little-endian. `audio` is the mixed
    /// output (32 kHz, stereo, 16-bit) when asked for, else None.
    #[pyfunction]
    #[pyo3(signature = (data, seconds, audio = false))]
    #[allow(clippy::type_complexity)]
    fn run<'py>(py: Python<'py>, data: &[u8], seconds: f64, audio: bool)
        -> PyResult<(Bound<'py, PyBytes>, Option<Bound<'py, PyBytes>>, u64, u64)> {
        let (mut cpu, mut bus) = spc::load(data).map_err(PyValueError::new_err)?;
        if audio {
            bus.dsp.audio = Some(Vec::new());
        }
        let budget = (spc::CLOCK as f64 * seconds.max(0.0)) as u64;
        let n = py.allow_threads(|| spc::run(&mut cpu, &mut bus, budget));
        let mut out = Vec::with_capacity(bus.log.len() * 10);
        for w in &bus.log {
            out.extend_from_slice(&w.cycle.to_le_bytes());
            out.push(w.reg);
            out.push(w.value);
        }
        let pcm = bus.dsp.audio.as_ref().map(|a| {
            let mut b = Vec::with_capacity(a.len() * 2);
            for s in a {
                b.extend_from_slice(&s.to_le_bytes());
            }
            PyBytes::new(py, &b)
        });
        Ok((PyBytes::new(py, &out), pcm, cpu.cycles, n))
    }

    #[pymodule]
    fn bitcomposer_emu(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add("__version__", super::VERSION)?;
        m.add("CLOCK", spc::CLOCK)?;
        m.add_function(wrap_pyfunction!(run, m)?)?;
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
