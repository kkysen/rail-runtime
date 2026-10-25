"""Time-stepped multi-train run on the Port Washington Branch with a DC third-rail network solve.

Each service runs on its own track at a fixed headway with one stopping pattern.
Braking trains regenerate into the third rail; substations are diode rectifiers and can't absorb it,
so regen only helps other trains, and a train sheds regen once its voltage reaches V_REGEN_MAX.
"""

import numpy as np

from rail_runtime import model as m

DT = 0.5  # s
REGEN_EFF = 0.80  # wheel to line
V_REGEN_MAX = 900.0  # V


class Run:
    """One train's pattern in its own direction: limits and braking envelope by distance travelled."""

    def __init__(self, line, train, kind, stops, inbound):
        lim = line.limits(kind, train.vmax) * m.MPH
        s = line.s
        if inbound:
            lim, pos = lim[::-1], s[-1] - s[::-1]
        else:
            pos = s
        stop_p = sorted((s[-1] - line.st[n]) if inbound else line.st[n] for n in stops)
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
        self.s_end = s[-1]

    def chain(self, p):
        """Track chainage (from Penn) for distance travelled p."""
        return self.s_end - p if self.inbound else p


class Car:
    def __init__(self, run, t0, track, service):
        self.run = run
        self.track = track
        self.service = service
        self.p = run.p0
        self.v = 0.0
        self.dwell = 0.0
        self.t0 = t0
        self.next_stop = 1
        self.done = None


def demand(train, car, regen):
    """Electrical power the train wants this step (negative when regenerating)."""
    r = car.run
    if car.dwell > 0:
        return train.aux
    i = min(int(car.p / r.ds), len(r.env) - 1)
    j = min(int((car.p + car.v * DT) / r.ds), len(r.env) - 1)
    want = min(r.env[min(i + 1, len(r.env) - 1)], r.lim[i])
    v = max(car.v, 0.1)
    if car.v < want - 0.05:
        return min(train.f_max * v, train.p_shaft) / 0.90 + train.aux
    if r.env[j] < car.v - 0.05:
        # Braking: electric brake recovers what it can, up to rated power.
        rec = min(train.m_eff * train.brake * car.v, train.p_shaft) * REGEN_EFF if regen else 0.0
        return train.aux - rec
    return train.resist(car.v) * car.v / 0.90 + train.aux  # cruise


NONCONVERGED = [0]


def solve(subs, cars, dem, train, n_tracks):
    """Nodal solve of the DC network; returns (power to each train in W, train voltages)."""
    n_sub = len(subs)
    n = n_sub + len(cars)
    if not cars:
        return [], []
    I = np.zeros(len(cars))
    V = np.full(n, m.V0)
    # Branch conductances only depend on positions.
    G0 = np.zeros((n, n))
    for track in range(n_tracks):
        nodes = [(subs[k], k) for k in range(n_sub)]
        nodes += [(c.run.chain(c.p), n_sub + j) for j, c in enumerate(cars) if c.track == track]
        nodes.sort()
        for (xa, a), (xb, bb) in zip(nodes, nodes[1:]):
            g = 1 / max((xb - xa) / m.MILE * m.R_LOOP, 1e-6)
            G0[a, a] += g
            G0[bb, bb] += g
            G0[a, bb] -= g
            G0[bb, a] -= g
    shed = np.ones(len(cars))
    for it in range(200):
        G = G0.copy()
        b = np.zeros(n)
        for k in range(n_sub):
            # Diode rectifier: conducts only outward (a tiny leak keeps the network grounded).
            g = 1 / m.R_SUB if V[k] <= m.V0 + 1e-6 else 1e-6
            G[k, k] += g
            b[k] += m.V0 * g
        for j in range(len(cars)):
            k = n_sub + j
            Vt = max(V[k], 1.0)
            if dem[j] >= 0:
                I[j] = min(dem[j] / Vt, train.i_max)
                if Vt < m.V_MIN:
                    I[j] *= max(Vt - 0.6 * m.V_MIN, 0) / (0.4 * m.V_MIN)  # shed load as voltage collapses
            else:
                if Vt > V_REGEN_MAX:
                    shed[j] *= 0.8  # line not receptive: blend to friction brake
                I[j] = max(dem[j] * shed[j] / Vt, -train.i_max)
            b[k] -= I[j]
        # Nodes with no branches (lone train on an isolated stretch) can't happen: subs bound every track.
        # Clamp to the physical range: below 0.6 V_MIN trains draw nothing, above V_REGEN_MAX they shed regen.
        V_new = np.clip(np.linalg.solve(G, b), 0.6 * m.V_MIN, V_REGEN_MAX + 50)
        if np.max(np.abs(V_new - V)) < 0.2:
            V = V_new
            break
        V = 0.7 * V + 0.3 * V_new
    else:
        NONCONVERGED[0] += 1
    return [V[n_sub + j] * I[j] for j in range(len(cars))], V[n_sub:]


def simulate(line, train, kind, services, horizon, regen=True, single=False):
    """services: list of (name, stops, inbound, track, headway s, offset s)."""
    runs = {(nm, d): Run(line, train, kind, st, d) for nm, st, d, *_ in services}
    subs = list(line.subs)
    n_tracks = max(sv[3] for sv in services) + 1
    cars = []
    vmin = []
    t = 0.0
    next_dep = {i: sv[5] for i, sv in enumerate(services)}
    while t < horizon:
        for i, (nm, st, d, track, hw, off) in enumerate(services):
            if t >= next_dep[i] and not (single and cars):
                cars.append(Car(runs[(nm, d)], t, track, nm))
                next_dep[i] += hw
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
        for c, pe in zip(active, pw):
            r = c.run
            if c.dwell > 0:
                c.dwell -= DT
                continue
            i = min(int(c.p / r.ds), len(r.env) - 1)
            u = max(c.v, 0.1)
            mech = max(pe - train.aux, 0) * 0.90
            acc = (min(train.f_max, mech / u) - train.resist(c.v)) / train.m_eff
            v_new = max(c.v + acc * DT, 0)
            j = min(int((c.p + c.v * DT) / r.ds), len(r.env) - 1)
            v_new = min(v_new, r.env[j], r.lim[i])
            stop = r.stops[c.next_stop]
            if stop - c.p > 1.0:
                v_new = max(v_new, min(1.0, np.sqrt(2 * train.brake * max(stop - c.p, 0))))
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


PW_STOPS = ["Penn Station", "Woodside", "Mets-Willets Point", "Flushing Main Street", "Murray Hill",
            "Broadway", "Auburndale", "Bayside", "Douglaston", "Little Neck", "Great Neck", "Manhasset",
            "Plandome", "Port Washington"]
JAM_STOPS = ["Penn Station", "Woodside", "Forest Hills", "Kew Gardens", "Jamaica"]
PW_EXPRESS = ["Penn Station", "Great Neck", "Manhasset", "Plandome", "Port Washington"]
TRAINS = ("M7, 750 V third rail", "M8, 25 kV")
KINDS = ("posted", "60", "80", "100")


def busy(line, cases, horizon, window):
    """Yield dicts of service, train, kind, one-train and busy runtimes (min), and the lowest train voltage."""
    for tr in [t for t in m.TRAINS if t.name in TRAINS]:
        for kind in KINDS:
            res = {}
            for regen in (True, False):
                if not regen and tr.supply != "third rail":
                    continue
                done, vmin = simulate(line, tr, kind, cases, horizon, regen)
                res[regen] = (done, vmin)
            for name, stops, inbound, *_ in cases:
                if not inbound:
                    continue
                one, _ = simulate(line, tr, kind, [c for c in cases if c[0] == name], horizon, single=True)
                row = {}
                for regen in (True, False):
                    if regen not in res:
                        row[regen] = float("nan")
                        continue
                    xs = [(c.done - c.t0) / 60 for c in res[regen][0]
                          if c.service == name and c.run.inbound and window[0] <= c.t0 < window[1]]
                    row[regen] = np.mean(xs)
                yield dict(service=name, train=tr, kind=kind, one=(one[0].done - one[0].t0) / 60,
                           regen=row[True], no_regen=row[False],
                           vmin=min(res[True][1]) if res[True][1] else float("nan"))


def lines(data):
    """Per line: (title, Line, cases, horizon s, steady-state departure window s)."""
    pw = m.Line(f"{data}/pw_geom.json", f"{data}/substations.json", PW_STOPS)
    jam = m.Line(f"{data}/jam_geom.json", f"{data}/substations.json", JAM_STOPS, terminal=False)
    nonstop = ["Penn Station", "Jamaica"]
    out = {}
    for name, stops in (("PW local", PW_STOPS), ("PW express", PW_EXPRESS)):
        out[name] = (f"{name}, every 5 min each way", pw,
                     [(name, stops, True, 0, 300, 0), (name, stops, False, 1, 300, 150)], 3 * 3600, (3600, 7200))
    out["Jamaica"] = ("Jamaica: locals and nonstops each every 2.5 min per direction (1.25 min combined)", jam,
                      [("Jamaica local", JAM_STOPS, True, 0, 150, 0), ("Jamaica nonstop", nonstop, True, 1, 150, 75),
                       ("Jamaica local", JAM_STOPS, False, 2, 150, 40),
                       ("Jamaica nonstop", nonstop, False, 3, 150, 115)],
                      5400, (1800, 3600))
    return out


def show(data: str, which: str) -> None:
    """Print busy-service runs for `which`: `pw` or `jam`."""
    for key, (title, line, cases, horizon, window) in lines(data).items():
        if (which == "pw") != key.startswith("PW"):
            continue
        print(f"--- {title} ---")
        print(f"{'service':16} {'train':28} {'kind':6} {'1 train':>8} {'busy':>6} {'busy no regen':>14} {'min V':>6}")
        for r in busy(line, cases, horizon, window):
            print(f"{r['service']:16} {r['train'].name:28} {r['kind']:6} {r['one']:8.1f} {r['regen']:6.1f} "
                  f"{r['no_regen']:14.1f} {r['vmin']:6.0f}  nonconv {NONCONVERGED[0]}", flush=True)
