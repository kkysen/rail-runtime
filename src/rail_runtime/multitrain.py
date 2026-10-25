"""Time-stepped multi-train runs with a DC third-rail network solve, in the `sim` crate (`sim/src/multi.rs`).

Each service runs on its own track at a fixed headway with one stopping pattern.
Braking trains regenerate into the third rail; substations are diode rectifiers and can't absorb it,
so regen only helps other trains, and a train sheds regen once its voltage reaches 900 V.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from rail_runtime import _sim
from rail_runtime import model as m
from rail_runtime.model import Arr, Line, Train


class Service(NamedTuple):
    """Trains on one stopping pattern in one direction, on their own track."""

    name: str
    stops: list[str]
    inbound: bool
    track: int
    headway: float  # s
    offset: float  # s, first departure


@dataclass
class Job:
    """One simulation, as `sim` reads it."""

    train: Train
    lim_mph: Arr  # by sample, in chainage order
    ds: float  # m
    s_end: float  # m
    subs: list[float]  # substation chainages, m
    services: list[tuple[list[float], bool, int, float, float]]  # stop chainages, inbound, track, headway, offset
    horizon: float  # s
    regen: bool
    single: bool  # only the first train to depart, alone


@dataclass
class Finished:
    """A train that reached its last stop."""

    service: str
    inbound: bool
    t0: float  # departure, s
    done: float  # arrival, s


NONCONVERGED = [0]


def simulate(
    line: Line,
    train: Train,
    kind: str,
    services: list[Service],
    horizon: float,
    regen: bool = True,
    single: bool = False,
) -> tuple[list[Finished], float]:
    """Run `services` for `horizon` s; returns the finished trains and the lowest train voltage (nan off third rail)."""
    job = Job(
        train=train,
        lim_mph=line.limits(kind, train.vmax),
        ds=line.ds,
        s_end=float(line.s[-1]),
        subs=[float(x) for x in line.subs],
        services=[([line.st[n] for n in sv.stops], sv.inbound, sv.track, sv.headway, sv.offset) for sv in services],
        horizon=horizon,
        regen=regen,
        single=single,
    )
    out = _sim.simulate(job)
    NONCONVERGED[0] += out.nonconverged
    finished = [Finished(services[i].name, services[i].inbound, t0, done) for i, t0, done in out.finished]
    return finished, float("nan") if out.vmin is None else out.vmin


PW_STOPS = [
    "Penn Station",
    "Woodside",
    "Mets-Willets Point",
    "Flushing Main Street",
    "Murray Hill",
    "Broadway",
    "Auburndale",
    "Bayside",
    "Douglaston",
    "Little Neck",
    "Great Neck",
    "Manhasset",
    "Plandome",
    "Port Washington",
]
JAM_STOPS = ["Penn Station", "Woodside", "Forest Hills", "Kew Gardens", "Jamaica"]
PW_EXPRESS = ["Penn Station", "Great Neck", "Manhasset", "Plandome", "Port Washington"]
TRAINS = ("M7, 750 V third rail", "M8, 25 kV")
KINDS = ("posted", "60", "80", "100")


@dataclass
class BusyRow:
    service: str
    train: Train
    kind: str
    one: float  # minutes per inbound trip with one train alone
    regen: float  # minutes per inbound trip in steady busy service
    no_regen: float  # nan unless on third rail
    vmin: float  # lowest train voltage, V; nan unless on third rail


class Setup(NamedTuple):
    title: str
    line: Line
    services: list[Service]
    horizon: float  # s
    window: tuple[float, float]  # departures counted as steady state, s


def busy(line: Line, cases: list[Service], horizon: float, window: tuple[float, float]) -> Iterator[BusyRow]:
    """Yield a row per inbound service, train and speed case."""
    for tr in [t for t in m.TRAINS if t.name in TRAINS]:
        for kind in KINDS:
            res: dict[bool, tuple[list[Finished], float]] = {}
            for regen in (True, False):
                if not regen and tr.supply != "third rail":
                    continue
                done, vmin = simulate(line, tr, kind, cases, horizon, regen)
                res[regen] = (done, vmin)
            for sv in cases:
                if not sv.inbound:
                    continue
                name = sv.name
                one, _ = simulate(line, tr, kind, [c for c in cases if c.name == name], horizon, single=True)
                row: dict[bool, float] = {}
                for regen in (True, False):
                    if regen not in res:
                        row[regen] = float("nan")
                        continue
                    xs = [
                        runtime(c)
                        for c in res[regen][0]
                        if c.service == name and c.inbound and window[0] <= c.t0 < window[1]
                    ]
                    row[regen] = float(np.mean(xs))
                yield BusyRow(
                    service=name,
                    train=tr,
                    kind=kind,
                    one=runtime(one[0]),
                    regen=row[True],
                    no_regen=row[False],
                    vmin=res[True][1],
                )


def runtime(c: Finished) -> float:
    """Minutes from departure to arrival."""
    return (c.done - c.t0) / 60


def lines(data: str) -> dict[str, Setup]:
    """The busy-service setups: Port Washington local, express, and Jamaica."""
    pw = m.Line(f"{data}/pw_geom.json", f"{data}/substations.json", PW_STOPS)
    jam = m.Line(f"{data}/jam_geom.json", f"{data}/substations.json", JAM_STOPS, terminal=False)
    nonstop = ["Penn Station", "Jamaica"]
    out: dict[str, Setup] = {}
    for name, stops in (("PW local", PW_STOPS), ("PW express", PW_EXPRESS)):
        out[name] = Setup(
            f"{name}, every 5 min each way",
            pw,
            [Service(name, stops, True, 0, 300, 0), Service(name, stops, False, 1, 300, 150)],
            3 * 3600,
            (3600, 7200),
        )
    out["Jamaica"] = Setup(
        "Jamaica: locals and nonstops each every 2.5 min per direction (1.25 min combined)",
        jam,
        [
            Service("Jamaica local", JAM_STOPS, True, 0, 150, 0),
            Service("Jamaica nonstop", nonstop, True, 1, 150, 75),
            Service("Jamaica local", JAM_STOPS, False, 2, 150, 40),
            Service("Jamaica nonstop", nonstop, False, 3, 150, 115),
        ],
        5400,
        (1800, 3600),
    )
    return out


def show(data: str, which: str) -> None:
    """Print busy-service runs for `which`: `pw` or `jam`."""
    for key, (title, line, cases, horizon, window) in lines(data).items():
        if (which == "pw") != key.startswith("PW"):
            continue
        print(f"--- {title} ---")
        print(f"{'service':16} {'train':28} {'kind':6} {'1 train':>8} {'busy':>6} {'busy no regen':>14} {'min V':>6}")
        for r in busy(line, cases, horizon, window):
            print(
                f"{r.service:16} {r.train.name:28} {r.kind:6} {r.one:8.1f} {r.regen:6.1f} "
                f"{r.no_regen:14.1f} {r.vmin:6.0f}  nonconv {NONCONVERGED[0]}",
                flush=True,
            )
