//! The `rail_runtime._sim` module.

use numpy::PyReadonlyArray1;
use pyo3::exceptions::PyValueError;
use pyo3::types::{PyAnyMethods, PyModule, PyModuleMethods};
use pyo3::{Bound, PyAny, PyResult, pyfunction, pymodule, wrap_pyfunction};

use crate::train::{Supply, Train, V_MIN, V0};

/// Read a `rail_runtime.model.Train`.
fn train(t: &Bound<'_, PyAny>) -> PyResult<Train> {
    let f = |name: &str| -> PyResult<f64> { t.getattr(name)?.extract() };
    let supply: String = t.getattr("supply")?.extract()?;
    Ok(Train {
        m: f("m")?,
        m_eff: f("m_eff")?,
        p_shaft: f("p_shaft")?,
        f_max: f("f_max")?,
        cars: f("cars")?,
        supply: match supply.as_str() {
            "third rail" => Supply::ThirdRail,
            "stiff" => Supply::Stiff,
            "25 kV" => Supply::Ac,
            _ => return Err(PyValueError::new_err(format!("unknown supply {supply:?}"))),
        },
        brake: f("brake")?,
        aux: f("aux")?,
        i_max: f("i_max")?,
        sharing: f("sharing")?,
    })
}

/// Shaft power, W, available to `t` fed through `r_eff` ohms.
#[pyfunction]
fn power(t: &Bound<'_, PyAny>, r_eff: f64) -> PyResult<f64> {
    Ok(train(t)?.power(r_eff))
}

/// Seconds from standing at the first sample to standing at the last.
#[pyfunction]
fn run(
    t: &Bound<'_, PyAny>,
    lim_mph: PyReadonlyArray1<'_, f64>,
    r_eff: PyReadonlyArray1<'_, f64>,
    ds: f64,
) -> PyResult<f64> {
    let (lim_mph, r_eff) = (lim_mph.as_slice()?, r_eff.as_slice()?);
    if lim_mph.len() != r_eff.len() || lim_mph.len() < 2 {
        return Err(PyValueError::new_err(
            "need matching limits and resistances, at least 2 samples",
        ));
    }
    Ok(crate::single::run(&train(t)?, lim_mph, r_eff, ds))
}

#[pymodule]
#[pyo3(name = "_sim")]
fn sim_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("MPH", crate::MPH)?;
    m.add("V0", V0)?;
    m.add("V_MIN", V_MIN)?;
    m.add_function(wrap_pyfunction!(power, m)?)?;
    m.add_function(wrap_pyfunction!(run, m)?)?;
    Ok(())
}
