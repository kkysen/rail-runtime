"""Rank posted slow zones by the time they cost, raising one zone at a time to its curve limit (80 mph cap)."""

import numpy as np

from rail_runtime import model as m
from rail_runtime.curves import CASES


def rank(data, top=12):
    """Per line: (name, base runtimes, rows).

    Each row is (max saved, from mi, to mi, posted, raised to, near, saved by pattern).
    """
    m7 = m.TRAINS[0]
    out = []
    for name, (gf, stops, pats) in CASES.items():
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
            if posted[i] < 80 and better[i : j + 1].max() > posted[i] + 1:
                zones.append((i, j))
            i = j + 1
        base = {k: line.trip(m7, "posted", p) for k, p in pats.items()}
        rows = []
        for i, j in zones:
            lim = posted.copy()
            lim[i : j + 1] = better[i : j + 1]
            saved = {k: base[k] - line.trip(m7, "posted", p, lim) for k, p in pats.items()}
            near = min(line.st, key=lambda n: abs(line.st[n] - line.s[i]))
            rows.append(
                (
                    max(saved.values()),
                    line.s[i] / m.MILE,
                    line.s[j] / m.MILE,
                    posted[i],
                    better[i : j + 1].max(),
                    near,
                    saved,
                )
            )
        rows = [r for r in sorted(rows, reverse=True)[:top] if r[0] >= 0.05]
        out.append((name, base, rows))
    return out


def show(data: str) -> None:
    for name, base, rows in rank(data):
        print(f"=== {name} (M7, base {', '.join(f'{k} {v:.1f}' for k, v in base.items())} min) ===")
        for r in rows:
            print(
                f"  {r[1]:5.2f}-{r[2]:5.2f} mi  near {r[5]:22} posted {r[3]:3.0f} -> {r[4]:3.0f}  "
                + "  ".join(f"{k} {v * 60:4.0f}s" for k, v in r[6].items())
            )
