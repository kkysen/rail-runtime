"""The simulation's hot loops, from the `sim` crate (`sim/src/lib.rs`)."""

import numpy as np
import numpy.typing as npt

from rail_runtime.model import Train

MPH: float
V0: float
V_MIN: float

def power(t: Train, r_eff: float) -> float: ...
def run(t: Train, lim_mph: npt.NDArray[np.float64], r_eff: npt.NDArray[np.float64], ds: float) -> float: ...
