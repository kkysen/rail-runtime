//! The `rail_runtime._sim` module.

use pyo3::types::{PyModule, PyModuleMethods};
use pyo3::{Bound, PyResult, pymodule};

#[pymodule]
#[pyo3(name = "_sim")]
fn sim_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("MPH", crate::MPH)?;
    Ok(())
}
