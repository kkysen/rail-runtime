"""Minimum-runtime model for LIRR lines on OSM geometry, with a third-rail supply model.

Every run is flat (no grades), one train on the line, 30 s dwells, no schedule padding.
"""
import csv
import json
import math
from collections import defaultdict

import numpy as np

MPH = 0.44704
MILE = 1609.34
DWELL = 30.0
EA, EU = 6.0, 3.0  # superelevation and unbalance, inches

# --- Third rail -------------------------------------------------------------
V0 = 750.0  # substation output, V (ORM tags the line 750 V)
R_SUB = 0.010  # substation source resistance, ohm
R_LOOP = 0.040  # contact rail plus running-rail return, ohm per mile
MAX_GAP = 2.0  # miles; gaps between mapped substations are filled at this spacing
V_MIN = 500.0  # train cuts traction below this


# --- Trains -----------------------------------------------------------------
class Train:
    def __init__(self, name, tare, load, p_shaft, a0, cars, vmax, supply, brake=2.0 * MPH, aux_per_car=30e3,
                 sharing=1.0):
        self.name = name
        self.m = (tare + load) * 1000
        self.m_eff = self.m * 1.08  # rotating mass
        self.p_shaft = p_shaft
        self.f_max = self.m_eff * a0
        self.cars = cars
        self.vmax = vmax
        self.supply = supply  # "third rail", "stiff" (rated power everywhere), or "25 kV"
        self.brake = brake
        self.aux = aux_per_car * cars
        # Trains drawing from the same substation section at once: scales the source resistance.
        self.sharing = sharing
        # Line current limit: what the propulsion draws at rated power and nominal voltage.
        self.i_max = (p_shaft / 0.90 + self.aux) / V0

    def resist(self, v):
        t = self.m / 1000
        return 21.7 * t + 0.35 * t * v + 3.0 * self.cars * v * v  # Davis, N

    def power(self, r_eff):
        """Shaft power available at a point fed through r_eff ohms."""
        if self.supply != "third rail":
            return self.p_shaft
        r_eff *= self.sharing
        demand = self.p_shaft / 0.90 + self.aux
        disc = V0 * V0 - 4 * r_eff * demand
        if disc >= 0:
            v = (V0 + math.sqrt(disc)) / 2
            i = demand / v
        else:  # network can't deliver the demand: maximum power transfer
            v, i = V0 / 2, V0 / (2 * r_eff)
        if i > self.i_max:
            i = self.i_max
            v = V0 - i * r_eff
        if v < V_MIN:
            # Shed current until the train voltage is back at the cutoff.
            i = (V0 - V_MIN) / r_eff
            v = V_MIN
        return max(v * i - self.aux, 0.0) * 0.90


def m7_like(name, supply, sharing=1.0):
    return Train(name, 5 * 115.0, 10 * 105 * 0.080, 40 * 200e3, 2.0 * MPH, 10, 80, supply, sharing=sharing)


def c755(name, supply, sharing=1.0, brake=2.0 * MPH):
    # Class 755/3 x4 in electric mode: 2600 kW per unit, 1.3 m/s^2, ~114 t per unit (unverified).
    return Train(name, 4 * 114.0, 4 * 144 * 0.080, 4 * 2600e3, 1.3, 12, 100, supply, brake=brake, sharing=sharing)


TRAINS = [
    m7_like("M7, 750 V third rail", "third rail"),
    m7_like("M7, third rail, 3 trains/section", "third rail", sharing=3.0),
    m7_like("M7, stiff supply (no sag)", "stiff"),
    Train("M8, 25 kV", 5 * 129.2, 10 * 105 * 0.080, 40 * 200e3, 2.0 * MPH, 10, 80, "25 kV"),
    Train("Class 700/1, 25 kV", 410.0, 666 * 0.080, 5000e3, 2.0 * MPH, 12, 100, "25 kV"),
    Train("Class 423 x4, AC", 4 * 105.0, 4 * 192 * 0.080, 4 * 2350e3, 1.0, 16, 87, "25 kV"),
    Train("FLIRT Sm5 x3, 25 kV", 3 * 132.0, 3 * 230 * 0.080, 3 * 2000e3, 1.2, 12, 100, "25 kV"),
    c755("755/3 x4, 750 V third rail", "third rail"),
    c755("755/3 x4, third rail, 3 trains/section", "third rail", sharing=3.0),
    c755("755/3 x4, 25 kV", "25 kV"),
    c755("755/3 x4, 25 kV, 1.3 brake", "25 kV", brake=1.3),
]


# --- Lines ------------------------------------------------------------------
class Line:
    def __init__(self, geom_json, substations_json, stations):
        g = json.load(open(geom_json))
        self.s = np.array(g["s"])
        self.ds = self.s[1] - self.s[0]
        R = np.array([np.inf if r is None else r for r in g["R"]])
        self.posted = np.array([np.nan if v is None else v for v in g["maxspeed"]])
        deg = 5729.58 / (R * 3.2808)
        with np.errstate(divide="ignore"):
            self.curve = np.sqrt((EA + EU) / (0.0007 * deg))
        st = dict(g["stations"])
        self.st = {n: st[n] for n in stations if n in st}
        self.st[stations[-1]] = self.s[-1] - 60  # end of the path is the outer terminal
        self.lonlat = np.array(g["lonlat"])
        self._substations(substations_json)

    def _substations(self, path):
        lat0 = np.mean(self.lonlat[:, 1])
        kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
        mapped = []
        for e in json.load(open(path))["elements"]:
            t = e["tags"]
            if "LIRR" not in (t.get("operator", "") + t.get("name", "")) and t.get("operator") != "Long Island Rail Road":
                continue
            c = e.get("center", e)
            d = np.hypot((self.lonlat[:, 0] - c["lon"]) * kx, (self.lonlat[:, 1] - c["lat"]) * ky)
            i = int(np.argmin(d))
            if d[i] < 400:
                mapped.append(self.s[i])
        pts = sorted(set([0.0] + mapped + [self.s[-1]]))
        subs = []
        for a, b in zip(pts, pts[1:]):
            n = max(1, math.ceil((b - a) / (MAX_GAP * MILE)))
            subs += [a + (b - a) * k / n for k in range(n)]
        subs.append(pts[-1])
        self.mapped = sorted(mapped)
        self.subs = np.array(subs)
        # Effective source resistance at each point: fed from both neighbouring substations.
        j = np.clip(np.searchsorted(self.subs, self.s), 1, len(self.subs) - 1)
        d1 = (self.s - self.subs[j - 1]) / MILE * R_LOOP + R_SUB
        d2 = (self.subs[j] - self.s) / MILE * R_LOOP + R_SUB
        self.r_eff = d1 * d2 / (d1 + d2)

    def limits(self, kind, vmax, train_len=260.0):
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
        # Turnout limits the geometry can't see: keep posted 15 mph or less (Penn interlocking).
        lim = np.where(self.posted <= 15, np.minimum(lim, self.posted), lim)
        end = self.s > self.s[-1] - 150
        lim[end] = np.minimum(lim[end], 15)  # bumper approach at the outer terminal
        return lim

    def run(self, train, lim_mph, a, b):
        i0, i1 = sorted((int(round(a / self.ds)), int(round(b / self.ds))))
        vl = lim_mph[i0 : i1 + 1] * MPH
        vl[0] = vl[-1] = 0  # stand at both stations
        p = [train.power(r) for r in self.r_eff[i0 : i1 + 1]]
        v = vl.copy()
        for i in range(1, len(v)):
            u = max(v[i - 1], 0.1)
            f = min(train.f_max, p[i - 1] / u)
            acc = (f - train.resist(u)) / train.m_eff
            v[i] = min(vl[i], math.sqrt(max(v[i - 1] ** 2 + 2 * acc * self.ds, 0)))
        for i in range(len(v) - 2, -1, -1):
            v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * train.brake * self.ds))
        vm = np.maximum((v[1:] + v[:-1]) / 2, 0.3)
        return float(np.sum(self.ds / vm)), v

    def trip(self, train, kind, stops):
        lim = self.limits(kind, train.vmax)
        xs = [self.st[n] for n in stops]
        t = sum(self.run(train, lim, a, b)[0] for a, b in zip(xs, xs[1:]))
        return (t + DWELL * (len(stops) - 2)) / 60


# --- Timetable --------------------------------------------------------------
def hm(t):
    h, m, s = map(int, t.split(":"))
    return h * 60 + m + s / 60


def am_inbound(gtfs, date, origin, line_stops, route_id=None, arr_window=(360, 600)):
    """Scheduled origin->Penn times for AM trips, with their stops on this line."""
    rd = lambda f: list(csv.DictReader(open(f"{gtfs}/{f}")))
    names = {r["stop_id"]: r["stop_name"] for r in rd("stops.txt")}
    svc = {c["service_id"] for c in rd("calendar_dates.txt") if c["date"] == date and c["exception_type"] == "1"}
    trips = {t["trip_id"]: t for t in rd("trips.txt")
             if t["service_id"] in svc and (route_id is None or t["route_id"] == route_id)}
    sts = defaultdict(list)
    for r in rd("stop_times.txt"):
        if r["trip_id"] in trips:
            sts[r["trip_id"]].append(r)
    out = []
    for tid, ss in sts.items():
        ss.sort(key=lambda r: int(r["stop_sequence"]))
        stops = [names[r["stop_id"]] for r in ss]
        on = [i for i, n in enumerate(stops) if n in line_stops]
        if stops[-1] != "Penn Station" or (origin and origin not in stops) or len(on) < 2:
            continue
        k = stops.index(origin) if origin else on[0]
        arr = hm(ss[-1]["arrival_time"])
        if not arr_window[0] <= arr <= arr_window[1]:
            continue
        on_line = [n for n in stops[k:] if n in line_stops]
        out.append(dict(num=trips[tid]["trip_short_name"], arr=arr, first=stops[0],
                        sched=arr - hm(ss[k]["departure_time"]), stops=on_line))
    return sorted(out, key=lambda r: r["arr"])
