"""Minimum-runtime (flat-out, no padding) sim for LIRR Port Washington Branch and PATCO.

Miles are from Penn Station (PW) or from Lindenwold (PATCO).
Speed limits are assumed approximations, not official timetable values.
"""
import numpy as np

DX = 0.001  # miles


def accel(v, a0, v_corner):
    # constant tractive effort to v_corner, then constant power; mph/s
    return a0 if v <= v_corner else a0 * v_corner / v


def run(stations, limits, stops, a0, v_corner, brake, dwell):
    end = stations[-1][1]
    x = np.arange(0, end + DX, DX)
    vlim = np.full_like(x, 200.0)
    for a, b, lim in limits:
        vlim[(x >= a) & (x <= b)] = np.minimum(vlim[(x >= a) & (x <= b)], lim)
    for name, mi in stations:
        if name in stops:
            vlim[np.abs(x - mi) < DX / 2] = 0
    vlim[0] = vlim[-1] = 0
    # forward pass (accel), mph -> mi/s: v/3600
    v = vlim.copy()
    for i in range(1, len(x)):
        vp = v[i - 1]
        a = accel(max(vp, 1), a0, v_corner)
        # v dv = a dx -> v^2 increases by 2*a*dx*3600 (mph^2 with dx in miles)
        v[i] = min(vlim[i], np.sqrt(vp**2 + 2 * a * DX * 3600))
    for i in range(len(x) - 2, -1, -1):
        v[i] = min(v[i], np.sqrt(v[i + 1] ** 2 + 2 * brake * DX * 3600))
    vm = (v[1:] + v[:-1]) / 2
    t = np.sum(DX / np.maximum(vm, 0.5)) * 3600
    t += dwell * (len(stops) - 2)
    return t / 60


PW_STATIONS = [("Penn", 0.0), ("Woodside", 5.0), ("Mets", 8.6), ("Flushing", 9.4),
               ("Murray Hill", 10.3), ("Broadway", 11.1), ("Auburndale", 11.8),
               ("Bayside", 12.7), ("Douglaston", 14.0), ("Little Neck", 14.6),
               ("Great Neck", 15.7), ("Manhasset", 17.3), ("Plandome", 18.4),
               ("Port Washington", 20.0)]

# Assumed current speed restrictions.
PW_CURRENT = [(0, 0.5, 15), (0.5, 1.2, 30), (1.2, 3.3, 60), (3.3, 4.3, 40),
              (4.3, 5.3, 60), (5.3, 5.8, 40), (5.8, 8.8, 65), (8.8, 9.6, 45),
              (9.6, 13.6, 65), (13.6, 14.2, 50), (14.2, 15.9, 65),
              (15.9, 17.0, 45), (17.0, 19.7, 55), (19.7, 20.0, 15)]
# "Could be": modern interlockings / signals, 80 mph tangents, curves at
# higher cant deficiency, faster terminal approaches.
PW_UPGRADED = [(0, 0.4, 30), (0.4, 3.3, 60), (3.3, 4.3, 60), (4.3, 5.3, 70),
               (5.3, 5.8, 45), (5.8, 8.8, 80), (8.8, 9.6, 55), (9.6, 13.6, 80),
               (13.6, 14.2, 60), (14.2, 15.9, 80), (15.9, 17.0, 50),
               (17.0, 19.8, 65), (19.8, 20.0, 25)]

ALL = [s for s, _ in PW_STATIONS]
EXP = ["Penn", "Great Neck", "Manhasset", "Plandome", "Port Washington"]

# PATCO, Lindenwold (0) to 15-16th & Locust (14.2).
PATCO_STATIONS = [("Lindenwold", 0.0), ("Ashland", 1.8), ("Woodcrest", 3.0),
                  ("Haddonfield", 4.6), ("Westmont", 5.6), ("Collingswood", 6.5),
                  ("Ferry Ave", 7.5), ("Broadway", 9.6), ("City Hall", 10.0),
                  ("Franklin Sq", 11.9), ("8th-Market", 12.6), ("9-10th Locust", 13.4),
                  ("12-13th Locust", 13.8), ("15-16th Locust", 14.2)]
PATCO_LIM = [(0, 8.8, 65), (8.8, 10.4, 30), (10.4, 11.5, 40), (11.5, 14.2, 30)]
P_ALL = [s for s, _ in PATCO_STATIONS]
P_EXP = ["Lindenwold", "Ferry Ave", "Broadway", "City Hall", "Franklin Sq",
         "8th-Market", "9-10th Locust", "12-13th Locust", "15-16th Locust"]


def to(st, name):
    return st[: [s for s, _ in st].index(name) + 1]


if __name__ == "__main__":
    m7 = dict(a0=2.0, v_corner=35, brake=1.8)
    m7_hot = dict(a0=2.5, v_corner=45, brake=2.2)  # EMU-class perf (e.g. M9 tuned/modern EMU)
    patco = dict(a0=3.0, v_corner=30, brake=3.0)
    gn = to(PW_STATIONS, "Great Neck")
    gn_all = [s for s, _ in gn]
    rows = [
        ("PW local, Penn-PW", PW_STATIONS, ALL),
        ("PW express, Penn-PW", PW_STATIONS, EXP),
        ("Local, Penn-Great Neck", gn, gn_all),
        ("Nonstop, Penn-Great Neck", gn, ["Penn", "Great Neck"]),
    ]
    print(f"{'run':28}{'cur PSR/M7':>12}{'upg/M7':>9}{'upg/fast':>10}  (dwell 45s / 30s)")
    for name, st, stops in rows:
        a = run(st, PW_CURRENT, stops, dwell=45, **m7)
        b = run(st, PW_UPGRADED, stops, dwell=45, **m7)
        c = run(st, PW_UPGRADED, stops, dwell=30, **m7_hot)
        print(f"{name:28}{a:12.1f}{b:9.1f}{c:10.1f}")
    for name, stops in [("PATCO local", P_ALL), ("PATCO express (skip 5)", P_EXP)]:
        t = run(PATCO_STATIONS, PATCO_LIM, stops, dwell=25, **patco)
        print(f"{name:28}{t:12.1f}")
