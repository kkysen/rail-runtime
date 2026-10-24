"""Minimum runtimes for AM inbound Port Washington trips on OSM geometry with an M7 power model."""
import csv
import json
import math
import sys
from collections import defaultdict

import numpy as np

MPH = 0.44704
geom_json, gtfs, date = sys.argv[1:4]
g = json.load(open(geom_json))
s = np.array(g["s"])
R = np.array([np.inf if r is None else r for r in g["R"]])
posted = np.array([np.nan if v is None else v for v in g["maxspeed"]])
DS = s[1] - s[0]

# Station chainage: only real PW branch stops; Port Washington is the end of track.
st = {n: x for n, x in g["stations"] if n not in ("Long Island City", "Hunterspoint Avenue")}
st["Port Washington"] = s[-1] - 60

# --- Track limits -----------------------------------------------------------
EA, EU = 6.0, 3.0  # superelevation and unbalance, inches
TRAIN_LEN = 10 * 85 * 0.3048  # 10-car M7 train, m
VMAX = 80.0  # M7/M9 service maximum, mph


def curve_limit(ea, eu):
    deg = 5729.58 / (R * 3.2808)  # degree of curve
    with np.errstate(divide="ignore"):
        return np.sqrt((ea + eu) / (0.0007 * deg))


def train_clear(lim):
    # A restriction holds until the rear of the train clears it (for both directions).
    n = int(TRAIN_LEN / DS)
    out = lim.copy()
    for k in range(1, n + 1):
        out[k:] = np.minimum(out[k:], lim[:-k])
        out[:-k] = np.minimum(out[:-k], lim[k:])
    return out


def terminal(lim):
    lim = lim.copy()
    lim[s > s[-1] - 150] = np.minimum(lim[s > s[-1] - 150], 15)  # bumper approach
    return lim


curve = curve_limit(EA, EU)
LIMITS = {
    "posted (OSM maxspeed)": terminal(np.fmin(np.nan_to_num(posted, nan=VMAX), VMAX)),
    "curves + 60 mph cap": terminal(train_clear(np.minimum(curve, 60))),
    "curves only (80 mph M7 max)": terminal(train_clear(np.minimum(curve, VMAX))),
}

# --- Train: M7 married pair under 750 V DC third rail ----------------------
EMPTY = 58.2 + 56.8  # t per pair
LOAD = 2 * 105 * 0.080  # seated load, t
M = (EMPTY + LOAD) * 1000
M_EFF = M * 1.08  # rotating mass
P_WHEEL = 8 * 200e3 * 0.97  # W: 8 x 200 kW motors at 750 V, gear losses
F_MAX = M_EFF * 2.0 * MPH  # tractive-effort cap giving the rated 2 mph/s
BRAKE = 2.0 * MPH  # planning service brake, m/s^2 (3 mph/s is the max)
DWELL = 30.0


def resist(v):
    return 2.5e3 + 40 * v + 6.0 * v * v  # Davis, N for a pair


def accel(v):
    f = min(F_MAX, P_WHEEL / max(v, 0.1))
    return (f - resist(v)) / M_EFF


def run(lim_mph, a, b):
    """Time from chainage a to b (stopping at both) with limits in mph."""
    i0, i1 = sorted((int(round(a / DS)), int(round(b / DS))))
    vl = lim_mph[i0 : i1 + 1] * MPH
    vl[0] = vl[-1] = 0  # stand at both stations
    v = vl.copy()
    for i in range(1, len(v)):
        v[i] = min(vl[i], math.sqrt(v[i - 1] ** 2 + 2 * accel(v[i - 1]) * DS))
    for i in range(len(v) - 2, -1, -1):
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * BRAKE * DS))
    vm = np.maximum((v[1:] + v[:-1]) / 2, 0.3)
    return float(np.sum(DS / vm)), v


def trip_time(lim, stops):
    xs = [st[n] for n in stops]
    t = sum(run(lim, a, b)[0] for a, b in zip(xs, xs[1:]))
    return (t + DWELL * (len(stops) - 2)) / 60


# --- AM inbound trips from GTFS --------------------------------------------
rd = lambda f: list(csv.DictReader(open(f"{gtfs}/{f}")))
names = {r["stop_id"]: r["stop_name"] for r in rd("stops.txt")}
svc = {c["service_id"] for c in rd("calendar_dates.txt") if c["date"] == date and c["exception_type"] == "1"}
trips = {t["trip_id"]: t for t in rd("trips.txt") if t["route_id"] == "9" and t["service_id"] in svc}
sts = defaultdict(list)
for r in rd("stop_times.txt"):
    if r["trip_id"] in trips:
        sts[r["trip_id"]].append(r)
hm = lambda t: int(t[:2]) * 60 + int(t[3:5]) + int(t[6:]) / 60

if __name__ == "__main__":
    print("Curves tighter than 60 mph (Ea 6 in + Eu 3 in):")
    tight = curve < 60
    edges = np.flatnonzero(np.diff(tight.astype(int)))
    for a, b in zip(edges[::2], edges[1::2]):
        i = a + 1 + int(np.argmin(R[a + 1 : b + 1]))
        print(f"  {s[a] / 1609.34:5.2f}-{s[b] / 1609.34:5.2f} mi  min R {R[i]:6.0f} m  "
              f"-> {curve[i]:4.0f} mph  (OSM posted {posted[i]:.0f})")
    print()
    print(f"{'train':>6} {'Penn arr':>8}  {'from':12} {'stops':>5} {'sched':>6}"
          + "".join(f"{k[:14]:>16}" for k in LIMITS))
    rows = []
    for tid, ss in sts.items():
        ss.sort(key=lambda r: int(r["stop_sequence"]))
        stops = [names[r["stop_id"]] for r in ss]
        arr = hm(ss[-1]["arrival_time"])
        if stops[-1] != "Penn Station" or not 360 <= arr <= 600:
            continue
        sched = arr - hm(ss[0]["departure_time"])
        sims = [trip_time(lim, stops) for lim in LIMITS.values()]
        rows.append((arr, trips[tid]["trip_short_name"], stops[0], len(stops), sched, sims))
    for arr, num, origin, n, sched, sims in sorted(rows):
        print(f"{num:>6} {int(arr // 60):02d}:{int(arr % 60):02d}     {origin[:12]:12} {n:5} {sched:6.0f}"
              + "".join(f"{x:16.1f}" for x in sims))
    print()
    print("Synthetic patterns:")
    order = sorted(st, key=st.get, reverse=True)
    pats = {"all-stops PW-Penn": order,
            "PW express (PW,PL,MH,GN,Penn)": ["Port Washington", "Plandome", "Manhasset", "Great Neck", "Penn Station"],
            "GN local": order[order.index("Great Neck"):],
            "GN-Penn nonstop": ["Great Neck", "Penn Station"]}
    for k, p in pats.items():
        print(f"  {k:32}" + "".join(f"{trip_time(lim, p):16.1f}" for lim in LIMITS.values()))
