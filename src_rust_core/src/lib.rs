# file: src_rust_core/src/lib.rs
// rust_core/src/lib.rs

mod dummy_points;

use pyo3::prelude::*;

#[pymodule]
fn src_rust_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<dummy_points::Sampler>()?;
    Ok(())
}