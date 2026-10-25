"""Minimum-runtime model for LIRR lines on OSM geometry, with a third-rail supply model.

Every run is flat (no grades), one train on the line, 30 s dwells, no schedule padding.
"""

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from rail_runtime import _sim

type Arr = npt.NDArray[np.float64]

MPH = 0.44704
MILE = 1609.34
DWELL = 30.0
EA, EU = 6.0, 3.0  # superelevation and unbalance, inches

# --- Third rail -------------------------------------------------------------
V0 = _sim.V0  # substation output, V (ORM tags the line 750 V)
R_SUB = 0.010  # source resistance of a substation feeding one track, ohm; one feeding n tracks has R_SUB / n
R_LOOP = 0.040  # contact rail plus running-rail return, ohm per mile
V_MIN = _sim.V_MIN  # train cuts traction below this


# --- Trains -----------------------------------------------------------------
class Train:
    def __init__(
        self,
        name: str,
        tare: float,
        load: float,
        p_shaft: float,
        a0: float,
        cars: int,
        vmax: float,
        supply: str,
        brake: float = 2.0 * MPH,
        aux_per_car: float = 30e3,
        sharing: float = 1.0,
    ) -> None:
        self.name = name
        self.m = (tare + load) * 1000
        self.m_eff = self.m * 1.08  # rotating mass
        self.p_shaft = p_shaft
        self.f_max = self.m_eff * a0
        self.cars = cars
        self.vmax = vmax
        self.supply = supply  # "third rail", "full power" (third rail with no voltage drop), or "25 kV"
        self.brake = brake
        self.aux = aux_per_car * cars
        # Trains drawing from the same substation section at once: scales the source resistance.
        self.sharing = sharing
        # Line current limit: what the propulsion draws at rated power and nominal voltage.
        self.i_max = (p_shaft / 0.90 + self.aux) / V0

    def resist(self, v: float) -> float:
        t = self.m / 1000
        return 21.7 * t + 0.35 * t * v + 3.0 * self.cars * v * v  # Davis, N

    def power(self, r_eff: float) -> float:
        """Shaft power available at a point fed through r_eff ohms."""
        return _sim.power(self, r_eff)


def m7_like(name: str, supply: str, sharing: float = 1.0) -> Train:
    return Train(name, 5 * 115.0, 10 * 105 * 0.080, 40 * 200e3, 2.0 * MPH, 10, 80, supply, sharing=sharing)


def c755(name: str, supply: str, sharing: float = 1.0, brake: float = 2.0 * MPH) -> Train:
    # Class 755/3 x4 in electric mode: 2600 kW per unit, 1.3 m/s^2, ~114 t per unit (unverified).
    return Train(name, 4 * 114.0, 4 * 144 * 0.080, 4 * 2600e3, 1.3, 12, 100, supply, brake=brake, sharing=sharing)


TRAINS = [
    m7_like("M7, 750 V third rail", "third rail"),
    m7_like("M7, 750 V third rail, full power", "full power"),
    Train("M8, 25 kV", 5 * 129.2, 10 * 105 * 0.080, 40 * 200e3, 2.0 * MPH, 10, 80, "25 kV"),
    Train("Class 700/1, 25 kV", 410.0, 666 * 0.080, 5000e3, 2.0 * MPH, 12, 100, "25 kV"),
    Train("Class 423 x4, AC", 4 * 105.0, 4 * 192 * 0.080, 4 * 2350e3, 1.0, 16, 87, "25 kV"),
    Train("FLIRT Sm5 x3, 25 kV", 3 * 132.0, 3 * 230 * 0.080, 3 * 2000e3, 1.2, 12, 100, "25 kV"),
    c755("755/3 x4, 750 V third rail", "third rail"),
    c755("755/3 x4, 25 kV", "25 kV"),
    c755("755/3 x4, 25 kV, 1.3 brake", "25 kV", brake=1.3),
]


def design_voltage(spacing: float, train: Train) -> float:
    """Volts midway between substations `spacing` miles apart, with `train` at full current on every track.

    Each substation is sized for its tracks, so the track count cancels out:
    each train draws half its current from either side, through `R_SUB` and half the gap of rail.
    """
    return V0 - train.i_max / 2 * (R_SUB + spacing / 2 * R_LOOP)


# --- Lines ------------------------------------------------------------------
@dataclass
class Geometry:
    """A traced route: arrays by 5 m sample, and stations by distance from its origin (m)."""

    s: Arr
    R: Arr  # curve radius, m; inf on straight track
    maxspeed: Arr  # posted, mph; nan where OSM has none
    lonlat: Arr
    stations: list[tuple[str, float]]
    third_rail: npt.NDArray[np.int_]  # through third-rail tracks, which DC substations feed
    catenary: npt.NDArray[np.int_]  # through overhead-wire tracks, which AC substations feed

    def save(self, path: str) -> None:
        """Write pretty-printed, one station or sample per line, so diffs line up with places on the track."""
        samples = (
            {
                "s": round(float(x), 1),
                "R": None if math.isinf(r) else round(float(r), 1),
                "maxspeed": None if math.isnan(v) else float(v),
                "lon": round(float(lo), 7),
                "lat": round(float(la), 7),
                "third_rail": int(n3),
                "catenary": int(nc),
            }
            for x, r, v, lo, la, n3, nc in zip(
                self.s,
                self.R,
                self.maxspeed,
                self.lonlat[:, 0],
                self.lonlat[:, 1],
                self.third_rail,
                self.catenary,
                strict=True,
            )
        )
        with open(path, "w") as f:
            f.write('{\n  "stations": [\n')
            f.write(",\n".join(f"    {json.dumps([n, round(x, 1)])}" for n, x in self.stations))
            f.write('\n  ],\n  "samples": [\n')
            f.write(",\n".join(f"    {json.dumps(x)}" for x in samples))
            f.write("\n  ]\n}\n")


def load_geom(path: str) -> Geometry:
    """Read a `geom.py` file."""
    g = json.loads(Path(path).read_text())
    sm: list[dict[str, Any]] = g["samples"]
    return Geometry(
        s=np.array([x["s"] for x in sm], dtype=float),
        R=np.array([np.inf if x["R"] is None else x["R"] for x in sm], dtype=float),
        maxspeed=np.array([np.nan if x["maxspeed"] is None else x["maxspeed"] for x in sm], dtype=float),
        lonlat=np.array([[x["lon"], x["lat"]] for x in sm], dtype=float),
        stations=[(n, x) for n, x in g["stations"]],
        third_rail=np.array([x["third_rail"] for x in sm], dtype=int),
        catenary=np.array([x["catenary"] for x in sm], dtype=int),
    )


def system(tags: dict[str, str]) -> str | None:
    """Whose network an OSM substation feeds: LIRR, Amtrak, NYCT (the subway) or utility; None if untagged.

    Only LIRR substations feed LIRR lines, plus untagged ones beside the track;
    Amtrak and the subway are kept apart for when their lines are modeled.
    """
    who = tags.get("operator", "") + " " + tags.get("name", "")
    if "LIRR" in who or "Long Island Rail" in who:
        return "LIRR"
    if "Amtrak" in who:
        return "Amtrak"
    if "New York City Transit" in who or re.search(r"\b(IRT|BMT|IND)\b", who):
        return "NYCT"
    if tags.get("operator"):
        return "utility"
    return None


def lirr_substations(g: Geometry, substations_json: str) -> list[tuple[float, int]]:
    """(chainage, OSM id) of each LIRR-tagged substation within 400 m of the path, in order.

    One substation mapped twice, say as a building and its fence, counts once.
    """
    lat0 = float(np.mean(g.lonlat[:, 1]))
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
    out: list[tuple[float, int]] = []
    for e in json.loads(Path(substations_json).read_text())["elements"]:
        if system(e["tags"]) != "LIRR":
            continue
        c = e.get("center", e)
        d = np.hypot((g.lonlat[:, 0] - c["lon"]) * kx, (g.lonlat[:, 1] - c["lat"]) * ky)
        i = int(np.argmin(d))
        if d[i] < 400:
            out.append((float(g.s[i]), e["id"]))
    out.sort()
    return [x for k, x in enumerate(out) if k == 0 or x[0] - out[k - 1][0] > 200]


class Line:
    def __init__(
        self,
        geom_json: str,
        substations_json: str,
        stations: list[str],
        bumpers: tuple[bool, bool],
        spacing: float,
    ) -> None:
        """`spacing` is the usual miles between substations, to fill gaps where OSM maps none."""
        self.bumpers = bumpers  # whether the start and end of the path are bumpers, not through stations
        g = load_geom(geom_json)
        self.s = g.s
        self.ds = float(self.s[1] - self.s[0])
        R = g.R
        self.posted = g.maxspeed
        # Interlockings (posted 20 mph or less): the traced path zig-zags through crossovers, whose kinks
        # read as tiny radii. With switches rebuilt to geometry, measure curvature on a smoothed path instead.
        R = np.where(self.posted <= 20, np.maximum(R, self._long_chord_radius(g.lonlat, 100.0)), R)
        deg = 5729.58 / (R * 3.2808)
        with np.errstate(divide="ignore"):
            self.curve = np.sqrt((EA + EU) / (0.0007 * deg))
        st = dict(g.stations)
        self.st = {n: st[n] for n in stations if n in st}
        self.st[stations[-1]] = float(self.s[-1]) - 60  # the last station is at the end of the path
        self.lonlat = g.lonlat
        self.third_rail = g.third_rail
        self.spacing = spacing
        self.lirr = [x for x, _ in lirr_substations(g, substations_json)]
        self._substations(substations_json)

    def _long_chord_radius(self, lonlat: Arr, half: float) -> Arr:
        lat0 = float(np.mean(lonlat[:, 1]))
        xy = lonlat * np.array([111320 * math.cos(math.radians(lat0)), 110540])
        # Smooth over 2 * half first: a rebuilt crossover ladder is a gentle S, not a chain of kinks.
        w = int(half / self.ds)
        for c in range(2):
            xy[:, c] = np.convolve(np.pad(xy[:, c], w, mode="edge"), np.ones(2 * w + 1) / (2 * w + 1), mode="valid")
        k = int(half / 2 / self.ds)
        R = np.full(len(xy), np.inf)
        a, b, c = xy[: -2 * k], xy[k:-k], xy[2 * k :]
        cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        with np.errstate(divide="ignore"):
            R[k:-k] = (np.hypot(*(b - a).T) * np.hypot(*(c - b).T) * np.hypot(*(c - a).T)) / (2 * np.abs(cross))
        return R

    def _substations(self, path: str) -> None:
        lat0 = float(np.mean(self.lonlat[:, 1]))
        kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
        untagged: list[float] = []
        for e in json.loads(Path(path).read_text())["elements"]:
            if system(e["tags"]) is not None:
                continue
            c = e.get("center", e)
            d = np.hypot((self.lonlat[:, 0] - c["lon"]) * kx, (self.lonlat[:, 1] - c["lat"]) * ky)
            i = int(np.argmin(d))
            if d[i] < 50:
                untagged.append(float(self.s[i]))
        mapped = list(self.lirr)
        # An untagged substation right beside the track counts only where the spacing leaves room for one,
        # at least half the usual spacing from every substation counted so far; that also drops its duplicates.
        for x in sorted(untagged):
            if all(abs(x - y) >= self.spacing / 2 * MILE for y in mapped):
                mapped.append(x)
        mapped.sort()
        # Fill gaps at the usual spacing, as near as whole substations allow.
        # No substation is assumed at either end of the path: past the outermost mapped ones,
        # they continue at the usual spacing to the first at or beyond each end.
        sp = self.spacing * MILE
        pts = sorted(mapped) or [float(self.s[-1]) / 2]
        while pts[0] > 0:
            pts.insert(0, pts[0] - sp)
        while pts[-1] < self.s[-1]:
            pts.append(pts[-1] + sp)
        subs: list[float] = []
        for a, b in pairwise(pts):
            n = max(1, round((b - a) / sp))
            subs += [a + (b - a) * k / n for k in range(n)]
        subs.append(pts[-1])
        self.mapped = sorted(mapped)
        self.subs = np.array(subs)
        # A substation is sized for the third-rail tracks it feeds, so its source resistance falls as they multiply.
        n = self.third_rail[np.clip(np.round(self.subs / self.ds).astype(int), 0, len(self.s) - 1)]
        self.r_subs = R_SUB / np.maximum(n, 1)
        # Effective source resistance at each point: fed from both neighbouring substations.
        j = np.clip(np.searchsorted(self.subs, self.s), 1, len(self.subs) - 1)
        d1 = (self.s - self.subs[j - 1]) / MILE * R_LOOP + self.r_subs[j - 1]
        d2 = (self.subs[j] - self.s) / MILE * R_LOOP + self.r_subs[j]
        self.r_eff = d1 * d2 / (d1 + d2)

    def limits(self, kind: str, vmax: float, train_len: float = 260.0) -> Arr:
        if kind == "posted":
            lim = np.fmin(np.nan_to_num(self.posted, nan=vmax), vmax)
        else:
            lim = np.minimum(self.curve, float(kind))  # kind is the line speed cap in mph
            # A restriction holds until the whole train has cleared it.
            n = int(train_len / self.ds)
            out = lim.copy()
            for k in range(1, n + 1):
                out[k:] = np.minimum(out[k:], lim[:-k])
                out[:-k] = np.minimum(out[:-k], lim[k:])
            lim = out
        # The geometry cases assume every switch is rebuilt to curve speed; only the bumper stays slow.
        # Bumper approaches.
        for bumper, near in zip(self.bumpers, (self.s < 150, self.s > self.s[-1] - 150), strict=True):
            if bumper:
                lim[near] = np.minimum(lim[near], 15)
        return lim

    def run(self, train: Train, lim_mph: Arr, a: float, b: float) -> float:
        """Seconds from standing at chainage `a` to standing at `b`."""
        i0, i1 = sorted((round(a / self.ds), round(b / self.ds)))
        return _sim.run(train, lim_mph[i0 : i1 + 1], self.r_eff[i0 : i1 + 1], self.ds)

    def trip(self, train: Train, kind: str, stops: list[str], lim: Arr | None = None) -> float:
        """Minutes from the first stop to the last; `lim` (mph by sample) overrides `kind`'s limits."""
        if lim is None:
            lim = self.limits(kind, train.vmax)
        xs = [self.st[n] for n in stops]
        t = sum(self.run(train, lim, a, b) for a, b in pairwise(xs))
        return (t + DWELL * (len(stops) - 2)) / 60


# --- Timetable --------------------------------------------------------------
def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def hm(t: str) -> float:
    h, m, s = map(int, t.split(":"))
    return h * 60 + m + s / 60


@dataclass
class Trip:
    num: str  # train number
    arr: float  # arrival at the terminus, minutes after midnight
    first: str  # first stop, on or off this line
    sched: float  # scheduled minutes from the first stop on this line to the terminus
    stops: list[str]  # stops on this line


def am_inbound(
    gtfs: str,
    date: str,
    origin: str | None,
    line_stops: set[str],
    route_id: str | None = None,
    terminus: str = "Penn Station",
    arr_window: tuple[float, float] = (360, 600),
) -> list[Trip]:
    """Scheduled origin->`terminus` times for AM trips, with their stops on this line."""
    names = {r["stop_id"]: r["stop_name"] for r in read_csv(f"{gtfs}/stops.txt")}
    svc = {
        c["service_id"]
        for c in read_csv(f"{gtfs}/calendar_dates.txt")
        if c["date"] == date and c["exception_type"] == "1"
    }
    trips = {
        t["trip_id"]: t
        for t in read_csv(f"{gtfs}/trips.txt")
        if t["service_id"] in svc and (route_id is None or t["route_id"] == route_id)
    }
    sts: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for r in read_csv(f"{gtfs}/stop_times.txt"):
        if r["trip_id"] in trips:
            sts[r["trip_id"]].append(r)
    out: list[Trip] = []
    for tid, ss in sts.items():
        ss.sort(key=lambda r: int(r["stop_sequence"]))
        stops = [names[r["stop_id"]] for r in ss]
        on = [i for i, n in enumerate(stops) if n in line_stops]
        if stops[-1] != terminus or (origin and origin not in stops) or len(on) < 2:
            continue
        k = stops.index(origin) if origin else on[0]
        arr = hm(ss[-1]["arrival_time"])
        if not arr_window[0] <= arr <= arr_window[1]:
            continue
        on_line = [n for n in stops[k:] if n in line_stops]
        out.append(
            Trip(
                num=trips[tid]["trip_short_name"],
                arr=arr,
                first=stops[0],
                sched=arr - hm(ss[k]["departure_time"]),
                stops=on_line,
            )
        )
    return sorted(out, key=lambda r: r.arr)
