//! The `rail_runtime._sim` module.

use numpy::PyReadonlyArray1;
use pyo3::exceptions::PyValueError;
use pyo3::pyclass;
use pyo3::types::{PyAnyMethods, PyModule, PyModuleMethods};
use pyo3::{Bound, PyAny, PyResult, pyfunction, pymodule, wrap_pyfunction};
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};

use crate::multi::{self, Job, Outcome, Service};
use crate::train::{Supply, Train, V_MIN, V0};

/// Read a `rail_runtime.model.Train`, running on third rail fed at `v0` volts.
fn train(t: &Bound<'_, PyAny>, v0: f64) -> PyResult<Train> {
    let f = |name: &str| -> PyResult<f64> { t.getattr(name)?.extract() };
    let supply: String = t.getattr("supply")?.extract()?;
    // Line current limit: what the propulsion draws at rated power and the line's nominal voltage.
    let i_max = (f("p_shaft")? / 0.90 + f("aux")?) / v0;
    Ok(Train {
        m: f("m")?,
        m_eff: f("m_eff")?,
        p_shaft: f("p_shaft")?,
        f_max: f("f_max")?,
        cars: f("cars")?,
        supply: match supply.as_str() {
            "third rail" => Supply::ThirdRail,
            "full power" => Supply::FullPower,
            "AC" => Supply::Ac,
            _ => return Err(PyValueError::new_err(format!("unknown supply {supply:?}"))),
        },
        brake: f("brake")?,
        aux: f("aux")?,
        i_max,
        v0,
        sharing: f("sharing")?,
    })
}

/// Shaft power, W, available to `t` fed through `r_eff` ohms (NaN under catenary) from a `v0` V third rail.
#[pyfunction]
fn power(t: &Bound<'_, PyAny>, r_eff: f64, v0: f64) -> PyResult<f64> {
    Ok(train(t, v0)?.power(r_eff))
}

/// Seconds from standing at the first sample to standing at the last.
#[pyfunction]
fn run(
    t: &Bound<'_, PyAny>,
    lim_mph: PyReadonlyArray1<'_, f64>,
    r_eff: PyReadonlyArray1<'_, f64>,
    ds: f64,
    v0: f64,
) -> PyResult<f64> {
    let (lim_mph, r_eff) = (lim_mph.as_slice()?, r_eff.as_slice()?);
    if lim_mph.len() != r_eff.len() || lim_mph.len() < 2 {
        return Err(PyValueError::new_err(
            "need matching limits and resistances, at least 2 samples",
        ));
    }
    Ok(crate::single::run(&train(t, v0)?, lim_mph, r_eff, ds))
}

/// Read a `rail_runtime.multitrain.Job`.
fn job(j: &Bound<'_, PyAny>) -> PyResult<Job> {
    let services: Vec<(Vec<f64>, bool, usize, f64, f64)> = j.getattr("services")?.extract()?;
    let lim: PyReadonlyArray1<'_, f64> = j.getattr("lim_mph")?.extract()?;
    Ok(Job {
        train: train(&j.getattr("train")?, j.getattr("v0")?.extract()?)?,
        lim_mph: lim.as_slice()?.to_vec(),
        ds: j.getattr("ds")?.extract()?,
        s_end: j.getattr("s_end")?.extract()?,
        subs: j.getattr("subs")?.extract()?,
        r_subs: j.getattr("r_subs")?.extract()?,
        r_return: j.getattr("r_return")?.extract()?,
        dc: j.getattr("dc")?.extract()?,
        services: services
            .into_iter()
            .map(|(stops, inbound, track, headway, offset)| Service {
                stops,
                inbound,
                track,
                headway,
                offset,
            })
            .collect(),
        horizon: j.getattr("horizon")?.extract()?,
        regen: j.getattr("regen")?.extract()?,
        single: j.getattr("single")?.extract()?,
    })
}

/// What a simulation produced.
#[pyclass(frozen, get_all, name = "Outcome")]
struct PyOutcome {
    /// (service index, departure s, arrival s) for each train that finished, in departure order.
    finished: Vec<(usize, f64, f64)>,
    /// Lowest train voltage, V; `None` off third rail.
    vmin: Option<f64>,
    /// Steps whose network solve didn't converge.
    nonconverged: u32,
}

impl From<Outcome> for PyOutcome {
    fn from(o: Outcome) -> Self {
        PyOutcome {
            finished: o
                .finished
                .into_iter()
                .map(|f| (f.service, f.t0, f.done))
                .collect(),
            vmin: o.vmin,
            nonconverged: o.nonconverged,
        }
    }
}

/// Run time-stepped multi-train simulations, in parallel, without holding the GIL.
#[pyfunction]
fn simulate_many(py: pyo3::Python<'_>, jobs: Vec<Bound<'_, PyAny>>) -> PyResult<Vec<PyOutcome>> {
    let jobs = jobs.iter().map(job).collect::<PyResult<Vec<_>>>()?;
    let outcomes: Vec<Outcome> = py.detach(|| jobs.par_iter().map(multi::simulate).collect());
    Ok(outcomes.into_iter().map(PyOutcome::from).collect())
}

#[pymodule]
#[pyo3(name = "_sim")]
fn sim_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("MPH", crate::MPH)?;
    m.add("V0", V0)?;
    m.add("V_MIN", V_MIN)?;
    m.add_function(wrap_pyfunction!(power, m)?)?;
    m.add_function(wrap_pyfunction!(run, m)?)?;
    m.add_function(wrap_pyfunction!(simulate_many, m)?)?;
    m.add_class::<PyOutcome>()?;
    Ok(())
}
