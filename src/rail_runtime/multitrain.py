"""Time-stepped multi-train runs with a DC third-rail network solve, in the `sim` crate (`sim/src/multi.rs`).

Each service runs on its own track at a fixed headway with one stopping pattern.
Braking trains regenerate into the third rail; substations are diode rectifiers and can't absorb it,
so regen only helps other trains, and a train sheds regen once its voltage reaches 900 V.
"""

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


def job(
    line: Line,
    train: Train,
    kind: str,
    services: list[Service],
    horizon: float,
    regen: bool = True,
    single: bool = False,
) -> Job:
    return Job(
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


def outcome(services: list[Service], out: _sim.Outcome) -> tuple[list[Finished], float]:
    """The finished trains and the lowest train voltage (nan off third rail)."""
    NONCONVERGED[0] += out.nonconverged
    finished = [Finished(services[i].name, services[i].inbound, t0, done) for i, t0, done in out.finished]
    return finished, float("nan") if out.vmin is None else out.vmin


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
    [out] = _sim.simulate_many([job(line, train, kind, services, horizon, regen, single)])
    return outcome(services, out)


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
ATL_STOPS = ["Atlantic Terminal", "Nostrand Avenue", "East New York", "Jamaica"]


class Spec(NamedTuple):
    """A line: its traced geometry, its stops in path order, and the inbound patterns to compare."""

    geom: str
    substations: str
    stops: list[str]
    patterns: dict[str, list[str]]
    bumpers: tuple[bool, bool]  # whether the start and end of the path are bumpers
    route: str | None  # GTFS route_id of its timetable trips; None for every trip through the last stop

    def line(self, data: str) -> Line:
        return m.Line(
            f"{data}/{self.geom}",
            f"{data}/{self.substations}",
            self.stops,
            self.bumpers,
        )


SPECS = {
    "Port Washington": Spec(
        "pw_geom.json",
        "substations.json",
        PW_STOPS,
        {"local": PW_STOPS[::-1], "express": PW_EXPRESS[::-1]},
        (False, True),
        "9",
    ),
    "Jamaica": Spec(
        "jam_geom.json",
        "substations.json",
        JAM_STOPS,
        {"local": JAM_STOPS[::-1], "nonstop": ["Jamaica", "Penn Station"]},
        (False, False),
        None,
    ),
    "Atlantic": Spec(
        "atl_geom.json",
        "substations.json",
        ATL_STOPS,
        {"local": ATL_STOPS[::-1]},
        (True, False),
        None,
    ),
}
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


def busy(setups: list[Setup]) -> list[list[BusyRow]]:
    """For each setup, a row per inbound service, train and speed case.

    Every simulation for every setup goes to `sim` in one batch, which runs them in parallel.
    """
    trains = [t for t in m.TRAINS if t.name in TRAINS]
    # (setup, train, kind, regen, the service run alone or None for all of them busy)
    keys: list[tuple[int, str, str, bool, str | None]] = []
    jobs: list[Job] = []
    services: list[list[Service]] = []
    for si, st in enumerate(setups):
        for tr in trains:
            for kind in KINDS:
                for regen in (True, False):
                    if regen or tr.supply == "third rail":
                        keys.append((si, tr.name, kind, regen, None))
                        services.append(st.services)
                for sv in st.services:
                    if sv.inbound:
                        keys.append((si, tr.name, kind, True, sv.name))
                        services.append([c for c in st.services if c.name == sv.name])
    for (si, name, kind, regen, alone), svcs in zip(keys, services, strict=True):
        tr = next(t for t in trains if t.name == name)
        st = setups[si]
        jobs.append(job(st.line, tr, kind, svcs, st.horizon, regen, single=alone is not None))
    res = {k: outcome(svcs, out) for k, svcs, out in zip(keys, services, _sim.simulate_many(jobs), strict=True)}
    out: list[list[BusyRow]] = []
    for si, st in enumerate(setups):
        lo, hi = st.window
        rows: list[BusyRow] = []
        for tr in trains:
            for kind in KINDS:
                for sv in st.services:
                    if not sv.inbound:
                        continue
                    busy_mean = {}
                    for regen in (True, False):
                        if (si, tr.name, kind, regen, None) not in res:
                            busy_mean[regen] = float("nan")
                            continue
                        done, _ = res[(si, tr.name, kind, regen, None)]
                        xs = [runtime(c) for c in done if c.service == sv.name and c.inbound and lo <= c.t0 < hi]
                        busy_mean[regen] = float(np.mean(xs))
                    one, _ = res[(si, tr.name, kind, True, sv.name)]
                    rows.append(
                        BusyRow(
                            service=sv.name,
                            train=tr,
                            kind=kind,
                            one=runtime(one[0]),
                            regen=busy_mean[True],
                            no_regen=busy_mean[False],
                            vmin=res[(si, tr.name, kind, True, None)][1],
                        )
                    )
        out.append(rows)
    return out


def runtime(c: Finished) -> float:
    """Minutes from departure to arrival."""
    return (c.done - c.t0) / 60


def lines(data: str) -> dict[str, Setup]:
    """The busy-service setups: Port Washington local, express, Jamaica, and Atlantic."""
    pw = SPECS["Port Washington"].line(data)
    jam = SPECS["Jamaica"].line(data)
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
    # Two tracks, so one service each way, at the most Atlantic Terminal has scheduled:
    # 11 trains an hour out in the PM peak in the 2015 and 2016 GTFS feeds, 10 in in the AM.
    # Each train runs on its own track, with no signals or turnbacks at Atlantic Terminal's stub tracks,
    # so the headway only loads the power network.
    atl_headway = 3600 / 11
    out["Atlantic"] = Setup(
        "Atlantic: locals 11 an hour each way",
        SPECS["Atlantic"].line(data),
        [
            Service("Atlantic local", ATL_STOPS, True, 0, atl_headway, 0),
            Service("Atlantic local", ATL_STOPS, False, 1, atl_headway, atl_headway / 2),
        ],
        3 * 3600,
        (3600, 7200),
    )
    return out


def show(data: str, which: str) -> None:
    """Print busy-service runs for `which`: `pw`, `jam` or `atl`."""
    prefix = {"pw": "PW", "jam": "Jamaica", "atl": "Atlantic"}[which]
    setups = [st for key, st in lines(data).items() if key.startswith(prefix)]
    for st, rows in zip(setups, busy(setups), strict=True):
        print(f"--- {st.title} ---")
        print(f"{'service':16} {'train':28} {'kind':6} {'1 train':>8} {'busy':>6} {'busy no regen':>14} {'min V':>6}")
        for r in rows:
            print(
                f"{r.service:16} {r.train.name:28} {r.kind:6} {r.one:8.1f} {r.regen:6.1f} "
                f"{r.no_regen:14.1f} {r.vmin:6.0f}"
            )
    print(f"non-converged network solves: {NONCONVERGED[0]}")
