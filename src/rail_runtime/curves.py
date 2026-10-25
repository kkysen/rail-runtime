"""Rank curves by the time they cost under curve-limited speeds (80 mph cap), one at a time."""
import sys

import numpy as np

from rail_runtime import model as m
from rail_runtime.multitrain import JAM_STOPS, PW_EXPRESS, PW_STOPS

CASES = {
    "Port Washington": ("pw_geom.json", PW_STOPS, {"local": PW_STOPS[::-1], "express": PW_EXPRESS[::-1]}),
    "Jamaica": ("jam_geom.json", JAM_STOPS, {"local": JAM_STOPS[::-1], "nonstop": ["Jamaica", "Penn Station"]}),
}


def rank(data, top=10):
    """Per line: (name, base runtimes, rows of (max saved, from mi, to mi, mph, near, saved by pattern))."""
    m7 = m.TRAINS[0]
    out = []
    for name, (gf, stops, pats) in CASES.items():
        line = m.Line(f"{data}/{gf}", f"{data}/substations.json", stops, terminal=name != "Jamaica")
        lim80 = line.limits("80", 80)
        slow = lim80 < 79.5
        edges = np.flatnonzero(np.diff(np.concatenate([[0], slow.astype(int), [0]])))
        orig = line.limits
        base = {k: line.trip(m7, "80", p) for k, p in pats.items()}
        rows = []
        for i, j in zip(edges[::2], edges[1::2]):
            lim = lim80.copy()
            lim[i:j] = 80
            line.limits = lambda kind, vmax, _l=lim: _l
            saved = {k: base[k] - line.trip(m7, "80", p) for k, p in pats.items()}
            line.limits = orig
            k = i + int(np.argmin(lim80[i:j]))
            near = min(line.st, key=lambda n: abs(line.st[n] - line.s[k]))
            rows.append((max(saved.values()), line.s[i] / m.MILE, line.s[j - 1] / m.MILE, lim80[k], near, saved))
        rows = [r for r in sorted(rows, reverse=True)[:top] if r[0] >= 0.05]
        out.append((name, base, rows))
    return out


if __name__ == "__main__":
    for name, base, rows in rank(sys.argv[1]):
        print(f"=== {name} (M7, 80 mph, base {', '.join(f'{k} {v:.1f}' for k, v in base.items())} min) ===")
        for r in rows:
            print(f"  {r[1]:5.2f}-{r[2]:5.2f} mi  near {r[4]:22} {r[3]:3.0f} mph  "
                  + "  ".join(f"{k} {v * 60:4.0f}s" for k, v in r[5].items()))
