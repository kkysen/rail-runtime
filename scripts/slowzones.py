"""Rank posted slow zones by the time they cost, raising one zone at a time to its curve limit (80 mph cap)."""
import sys

import numpy as np

import model as m
from multitrain import JAM_STOPS, PW_EXPRESS, PW_STOPS

data = sys.argv[1]
m7 = m.TRAINS[0]
cases = {
    "Port Washington": ("pw_geom.json", PW_STOPS, {"local": PW_STOPS[::-1], "express": PW_EXPRESS[::-1]}),
    "Jamaica": ("jam_geom.json", JAM_STOPS, {"local": JAM_STOPS[::-1], "nonstop": ["Jamaica", "Penn Station"]}),
}
for name, (gf, stops, pats) in cases.items():
    line = m.Line(f"{data}/{gf}", f"{data}/substations.json", stops, terminal=name != "Jamaica")
    posted = line.limits("posted", 80)
    better = np.maximum(posted, line.limits("80", 80))
    # Zones: runs of constant posted speed below 80 mph, where the geometry allows more.
    zones = []
    i = 0
    while i < len(posted):
        j = i
        while j + 1 < len(posted) and posted[j + 1] == posted[i]:
            j += 1
        if posted[i] < 80 and better[i:j + 1].max() > posted[i] + 1:
            zones.append((i, j))
        i = j + 1
    base = {k: line.trip(m7, "posted", p) for k, p in pats.items()}
    rows = []
    for i, j in zones:
        lim = posted.copy()
        lim[i:j + 1] = better[i:j + 1]
        line_lim = lambda kind, vmax, _l=lim: _l
        orig = line.limits
        line.limits = line_lim
        saved = {k: base[k] - line.trip(m7, "posted", p) for k, p in pats.items()}
        line.limits = orig
        near = min(line.st, key=lambda n: abs(line.st[n] - line.s[i]))
        rows.append((max(saved.values()), line.s[i] / m.MILE, line.s[j] / m.MILE, posted[i],
                     better[i:j + 1].min(), near, saved))
    print(f"=== {name} (M7, base {', '.join(f'{k} {v:.1f}' for k, v in base.items())} min) ===")
    for r in sorted(rows, reverse=True)[:12]:
        if r[0] < 0.05:
            break
        print(f"  {r[1]:5.2f}-{r[2]:5.2f} mi  near {r[5]:22} posted {r[3]:3.0f} -> {r[4]:3.0f}  "
              + "  ".join(f"{k} {v * 60:4.0f}s" for k, v in r[6].items()))
