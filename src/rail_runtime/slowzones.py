"""Rank posted slow zones by the time they cost, raising one zone at a time to its curve limit (80 mph cap)."""

import numpy as np

from rail_runtime import model as m
from rail_runtime.curves import CASES, Ranking, Zone, top_zones


def rank(data: str, top: int = 12) -> Ranking:
    """Per line: (name, base minutes by pattern, the posted zones costing the most)."""
    m7 = m.TRAINS[0]
    out: Ranking = []
    for name, (gf, stops, pats) in CASES.items():
        line = m.Line(f"{data}/{gf}", f"{data}/substations.json", stops, terminal=name != "Jamaica")
        posted = line.limits("posted", 80)
        better = np.maximum(posted, line.limits("80", 80))
        # Zones: runs of constant posted speed below 80 mph, where the geometry allows more.
        zones: list[tuple[int, int]] = []
        i = 0
        while i < len(posted):
            j = i
            while j + 1 < len(posted) and posted[j + 1] == posted[i]:
                j += 1
            if posted[i] < 80 and better[i : j + 1].max() > posted[i] + 1:
                zones.append((i, j))
            i = j + 1
        base = {k: line.trip(m7, "posted", p) for k, p in pats.items()}
        rows: list[Zone] = []
        for i, j in zones:
            lim = posted.copy()
            lim[i : j + 1] = better[i : j + 1]
            saved = {k: base[k] - line.trip(m7, "posted", p, lim) for k, p in pats.items()}
            near = min(line.st, key=lambda n: abs(line.st[n] - line.s[i]))
            rows.append(
                Zone(
                    float(line.s[i]) / m.MILE,
                    float(line.s[j]) / m.MILE,
                    near,
                    float(posted[i]),
                    float(better[i : j + 1].max()),
                    saved,
                )
            )
        out.append((name, base, top_zones(rows, top)))
    return out


def show(data: str) -> None:
    for name, base, rows in rank(data):
        print(f"=== {name} (M7, base {', '.join(f'{k} {v:.1f}' for k, v in base.items())} min) ===")
        for z in rows:
            print(
                f"  {z.start:5.2f}-{z.end:5.2f} mi  near {z.near:22} posted {z.posted:3.0f} -> {z.allows:3.0f}  "
                + "  ".join(f"{k} {v * 60:4.0f}s" for k, v in z.saved.items())
            )
