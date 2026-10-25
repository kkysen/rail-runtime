"""The simulation's hot loops, from the `sim` crate (`sim/src/lib.rs`)."""

from typing import final

import numpy as np
import numpy.typing as npt

from rail_runtime.model import Train
from rail_runtime.multitrain import Job

MPH: float
V0: float
V_MIN: float

def power(t: Train, r_eff: float) -> float: ...
def run(t: Train, lim_mph: npt.NDArray[np.float64], r_eff: npt.NDArray[np.float64], ds: float) -> float: ...

@final
class Outcome:
    """What a simulation produced."""

    finished: list[tuple[int, float, float]]  # service index, departure s, arrival s
    vmin: float | None  # lowest train voltage, V; None off third rail
    nonconverged: int  # steps whose network solve didn't converge

def simulate(j: Job) -> Outcome: ...
