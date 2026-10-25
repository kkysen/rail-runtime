"""Time-stepped multi-train run on the Port Washington Branch with a DC third-rail network solve.

Each service runs on its own track at a fixed headway with one stopping pattern.
Braking trains regenerate into the third rail; substations are diode rectifiers and can't absorb it,
so regen only helps other trains, and a train sheds regen once its voltage reaches V_REGEN_MAX.
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import pairwise
from typing import NamedTuple

import numpy as np

from rail_runtime import model as m
from rail_runtime.model import Arr, Line, Train

DT = 0.5  # s
REGEN_EFF = 0.80  # wheel to line
V_REGEN_MAX = 900.0  # V


class Service(NamedTuple):
    """Trains on one stopping pattern in one direction, on their own track."""

    name: str
    stops: list[str]
    inbound: bool
    track: int
    headway: float  # s
    offset: float  # s, first departure


class Run:
    """One train's pattern in its own direction: limits and braking envelope by distance travelled."""

    def __init__(self, line: Line, train: Train, kind: str, stops: list[str], inbound: bool) -> None:
        lim = line.limits(kind, train.vmax) * m.MPH
        s = line.s
        if inbound:
            lim, pos = lim[::-1], s[-1] - s[::-1]
        else:
            pos = s
        stop_p = sorted(float(s[-1] - line.st[n]) if inbound else line.st[n] for n in stops)
        self.p0, self.p1 = stop_p[0], stop_p[-1]
        self.stops = stop_p
        self.ds = line.ds
        self.pos = pos
        env = lim.copy()
        for sp in stop_p:
            env[int(round(sp / self.ds))] = 0
        for i in range(len(env) - 2, -1, -1):
            env[i] = min(env[i], np.sqrt(env[i + 1] ** 2 + 2 * train.brake * self.ds))
        self.env = env
        self.lim = lim
        self.inbound = inbound
        self.s_end = float(s[-1])

    def chain(self, p: float) -> float:
        """Track chainage (from Penn) for distance travelled p."""
        return self.s_end - p if self.inbound else p


class Car:
    def __init__(self, run: Run, t0: float, track: int, service: str) -> None:
        self.run = run
        self.track = track
        self.service = service
        self.p = run.p0
        self.v = 0.0
        self.dwell = 0.0
        self.t0 = t0
        self.next_stop = 1
        self.done: float | None = None


def demand(train: Train, car: Car, regen: bool) -> float:
    """Electrical power the train wants this step (negative when regenerating)."""
    r = car.run
    if car.dwell > 0:
        return train.aux
    i = min(int(car.p / r.ds), len(r.env) - 1)
    j = min(int((car.p + car.v * DT) / r.ds), len(r.env) - 1)
    want = min(float(r.env[min(i + 1, len(r.env) - 1)]), float(r.lim[i]))
    v = max(car.v, 0.1)
    if car.v < want - 0.05:
        return min(train.f_max * v, train.p_shaft) / 0.90 + train.aux
    if float(r.env[j]) < car.v - 0.05:
        # Braking: electric brake recovers what it can, up to rated power.
        rec = min(train.m_eff * train.brake * car.v, train.p_shaft) * REGEN_EFF if regen else 0.0
        return train.aux - rec
    return train.resist(car.v) * car.v / 0.90 + train.aux  # cruise


NONCONVERGED = [0]


def solve(subs: list[float], cars: list[Car], dem: list[float], train: Train, n_tracks: int) -> tuple[list[float], Arr]:
    """Nodal solve of the DC network; returns (power to each train in W, train voltages)."""
    n_sub = len(subs)
    n = n_sub + len(cars)
    if not cars:
        return [], np.zeros(0)
    cur = np.zeros(len(cars))
    V = np.full(n, m.V0)
    # Branch conductances only depend on positions.
    G0 = np.zeros((n, n))
    for track in range(n_tracks):
        nodes: list[tuple[float, int]] = [(subs[k], k) for k in range(n_sub)]
        nodes += [(c.run.chain(c.p), n_sub + j) for j, c in enumerate(cars) if c.track == track]
        nodes.sort()
        for (xa, a), (xb, bb) in pairwise(nodes):
            g = 1 / max((xb - xa) / m.MILE * m.R_LOOP, 1e-6)
            G0[a, a] += g
            G0[bb, bb] += g
            G0[a, bb] -= g
            G0[bb, a] -= g
    shed = np.ones(len(cars))
    for _ in range(200):
        G = G0.copy()
        b = np.zeros(n)
        for k in range(n_sub):
            # Diode rectifier: conducts only outward (a tiny leak keeps the network grounded).
            g = 1 / m.R_SUB if V[k] <= m.V0 + 1e-6 else 1e-6
            G[k, k] += g
            b[k] += m.V0 * g
        for j in range(len(cars)):
            k = n_sub + j
            Vt = max(float(V[k]), 1.0)
            if dem[j] >= 0:
                cur[j] = min(dem[j] / Vt, train.i_max)
                if Vt < m.V_MIN:
                    cur[j] *= max(Vt - 0.6 * m.V_MIN, 0) / (0.4 * m.V_MIN)  # shed load as voltage collapses
            else:
                if Vt > V_REGEN_MAX:
                    shed[j] *= 0.8  # line not receptive: blend to friction brake
                cur[j] = max(dem[j] * shed[j] / Vt, -train.i_max)
            b[k] -= cur[j]
        # Nodes with no branches (lone train on an isolated stretch) can't happen: subs bound every track.
        # Clamp to the physical range: below 0.6 V_MIN trains draw nothing, above V_REGEN_MAX they shed regen.
        V_new = np.clip(np.linalg.solve(G, b), 0.6 * m.V_MIN, V_REGEN_MAX + 50)
        if np.max(np.abs(V_new - V)) < 0.2:
            V = V_new
            break
        V = 0.7 * V + 0.3 * V_new
    else:
        NONCONVERGED[0] += 1
    return [float(V[n_sub + j] * cur[j]) for j in range(len(cars))], V[n_sub:]


def simulate(
    line: Line,
    train: Train,
    kind: str,
    services: list[Service],
    horizon: float,
    regen: bool = True,
    single: bool = False,
) -> tuple[list[Car], list[float]]:
    """Run `services` for `horizon` s; returns the finished trains and each step's lowest train voltage."""
    runs = {(sv.name, sv.inbound): Run(line, train, kind, sv.stops, sv.inbound) for sv in services}
    subs = [float(x) for x in line.subs]
    n_tracks = max(sv.track for sv in services) + 1
    cars: list[Car] = []
    vmin: list[float] = []
    t = 0.0
    next_dep = {i: sv.offset for i, sv in enumerate(services)}
    while t < horizon:
        for i, sv in enumerate(services):
            if t >= next_dep[i] and not (single and cars):
                cars.append(Car(runs[(sv.name, sv.inbound)], t, sv.track, sv.name))
                next_dep[i] += sv.headway
        active = [c for c in cars if c.done is None]
        if single and cars and not active:
            break
        dem = [demand(train, c, regen) for c in active]
        if train.supply == "third rail":
            pw, vt = solve(subs, active, dem, train, n_tracks)
            if len(vt):
                vmin.append(float(np.min(vt)))
        else:
            pw = dem
        for c, pe in zip(active, pw, strict=True):
            r = c.run
            if c.dwell > 0:
                c.dwell -= DT
                continue
            i = min(int(c.p / r.ds), len(r.env) - 1)
            u = max(c.v, 0.1)
            mech = max(pe - train.aux, 0.0) * 0.90
            acc = (min(train.f_max, mech / u) - train.resist(c.v)) / train.m_eff
            v_new = max(c.v + acc * DT, 0.0)
            j = min(int((c.p + c.v * DT) / r.ds), len(r.env) - 1)
            v_new = min(v_new, float(r.env[j]), float(r.lim[i]))
            stop = r.stops[c.next_stop]
            if stop - c.p > 1.0:
                v_new = max(v_new, min(1.0, math.sqrt(2 * train.brake * max(stop - c.p, 0.0))))
            c.p += (c.v + v_new) / 2 * DT
            c.v = v_new
            if c.p >= stop - 1.0:
                c.p, c.v = stop, 0.0
                if c.next_stop == len(r.stops) - 1:
                    c.done = t
                else:
                    c.dwell = m.DWELL
                    c.next_stop += 1
        t += DT
    return [c for c in cars if c.done is not None], vmin


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
            res: dict[bool, tuple[list[Car], list[float]]] = {}
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
                        if c.service == name and c.run.inbound and window[0] <= c.t0 < window[1]
                    ]
                    row[regen] = float(np.mean(xs))
                yield BusyRow(
                    service=name,
                    train=tr,
                    kind=kind,
                    one=runtime(one[0]),
                    regen=row[True],
                    no_regen=row[False],
                    vmin=min(res[True][1]) if res[True][1] else float("nan"),
                )


def runtime(c: Car) -> float:
    """Minutes from departure to arrival of a finished train."""
    assert c.done is not None
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
