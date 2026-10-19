//! The SNES sound CPU (SPC700) and SNES chip (S-DSP) emulator for bitComposer's
//! SPC import: step 3 of `docs/SPC-IMPORT.md`. It runs the game's own music
//! driver from an SPC snapshot and logs what the driver tells the SNES chip.
//!
//! The emulator is plain Rust; built with the `python` feature (as the wheel
//! is) it is also the Python module `bitcomposer_emu`.

pub mod cpu;
pub mod spc;

/// The crate's version, also the Python module's `__version__`.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(feature = "python")]
mod python {
    use pyo3::prelude::*;

    #[pymodule]
    fn bitcomposer_emu(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add("__version__", super::VERSION)?;
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
