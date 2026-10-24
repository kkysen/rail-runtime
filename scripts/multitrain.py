"""Time-stepped multi-train run on the Port Washington Branch with a DC third-rail network solve.

Trains run both directions at a fixed headway with one stopping pattern.
Only Port Washington trains draw from the network (no Main Line trains west of Woodside),
there is no regenerative braking, and the single track east of Great Neck is treated as double.
"""
import sys

import numpy as np

import model as m

DT = 0.5  # s


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
    def __init__(self, run, t0):
        self.run = run
        self.p = run.p0
        self.v = 0.0
        self.dwell = 0.0
        self.t0 = t0
        self.next_stop = 1
        self.done = None


def demand(train, car):
    """Electrical power the train wants this step."""
    r = car.run
    if car.dwell > 0:
        return train.aux
    i = min(int(car.p / r.ds), len(r.env) - 1)
    want = min(r.env[min(i + 1, len(r.env) - 1)], r.lim[i])
    v = max(car.v, 0.1)
    if car.v < want - 0.05:
        f = train.f_max
        mech = min(f * v, train.p_shaft)
    elif car.v > 0.5 and r.env[i] >= car.v - 0.05:
        mech = train.resist(car.v) * car.v  # cruise
    else:
        mech = 0.0  # braking or coasting into a restriction
    return mech / 0.90 + train.aux


def solve(line, subs, cars, track_of, dem, train):
    """Nodal solve of the DC network; returns power delivered to each train (W, electrical)."""
    n_sub = len(subs)
    n = n_sub + len(cars)
    if not cars:
        return [], []
    I = np.zeros(len(cars))
    V = np.full(n, m.V0)
    # Branch conductances only depend on positions.
    G0 = np.zeros((n, n))
    for track in (0, 1):
        nodes = [(subs[k], k) for k in range(n_sub)]
        nodes += [(c.run.chain(c.p), n_sub + j) for j, c in enumerate(cars) if track_of[j] == track]
        nodes.sort()
        for (xa, a), (xb, bb) in zip(nodes, nodes[1:]):
            g = 1 / max((xb - xa) / m.MILE * m.R_LOOP, 1e-6)
            G0[a, a] += g
            G0[bb, bb] += g
            G0[a, bb] -= g
            G0[bb, a] -= g
    for _ in range(30):
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
            I[j] = min(dem[j] / Vt, train.i_max)
            if Vt < m.V_MIN:
                I[j] *= max(Vt - 0.6 * m.V_MIN, 0) / (0.4 * m.V_MIN)  # shed load as voltage collapses
            b[k] -= I[j]
        # Nodes with no branches (lone train on an isolated stretch) can't happen: subs bound every track.
        V_new = np.linalg.solve(G, b)
        if np.max(np.abs(V_new - V)) < 0.5:
            V = V_new
            break
        V = 0.5 * V + 0.5 * V_new
    return [V[n_sub + j] * I[j] for j in range(len(cars))], V[n_sub:]


def simulate(line, train, kind, stops, headway, horizon):
    runs = {d: Run(line, train, kind, stops, d) for d in (True, False)}
    subs = list(line.subs)
    cars = []
    finished = []
    vmin = []
    t = 0.0
    next_dep = {True: 0.0, False: 0.0}
    while t < horizon:
        for d in (True, False):
            if headway and t >= next_dep[d] or (not headway and t == 0 and d):
                cars.append(Car(runs[d], t))
                next_dep[d] += headway or 1e18
        active = [c for c in cars if c.done is None]
        track_of = [0 if c.run.inbound else 1 for c in active]
        dem = [demand(train, c) for c in active]
        if train.supply == "third rail":
            pw, vt = solve(line, subs, active, track_of, dem, train)
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
            p_look = c.p + c.v * DT
            j = min(int(p_look / r.ds), len(r.env) - 1)
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
                    finished.append(c)
                else:
                    c.dwell = m.DWELL
                    c.next_stop += 1
        t += DT
    return finished, vmin


if __name__ == "__main__":
    data = sys.argv[1]
    PW_STOPS = ["Penn Station", "Woodside", "Mets-Willets Point", "Flushing Main Street", "Murray Hill",
                "Broadway", "Auburndale", "Bayside", "Douglaston", "Little Neck", "Great Neck", "Manhasset",
                "Plandome", "Port Washington"]
    line = m.Line(f"{data}/pw_geom.json", f"{data}/substations.json", PW_STOPS)
    pats = {"local": PW_STOPS,
            "express": ["Penn Station", "Great Neck", "Manhasset", "Plandome", "Port Washington"]}
    trains = [t for t in m.TRAINS if t.name in ("M7, 750 V third rail", "755/3 x4, 750 V third rail", "755/3 x4, 25 kV")]
    print(f"{'pattern':8} {'train':28} {'kind':7} {'1 train':>8} {'5 min':>8} {'min V':>6}")
    for pname, stops in pats.items():
        for tr in trains:
            for kind in ("posted", "60", "80", "100"):
                one, _ = simulate(line, tr, kind, stops, 0, 3600)
                many, vmin = simulate(line, tr, kind, stops, 300, 3 * 3600)
                steady = [c for c in many if 3600 <= c.t0 < 7200 and c.run.inbound]
                t1 = (one[0].done - one[0].t0) / 60
                t5 = np.mean([(c.done - c.t0) / 60 for c in steady])
                print(f"{pname:8} {tr.name:28} {kind:7} {t1:8.1f} {t5:8.1f} {min(vmin) if vmin else float('nan'):6.0f}",
                      flush=True)
