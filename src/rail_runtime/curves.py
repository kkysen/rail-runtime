"""Rank curves by the time they cost under curve-limited speeds (80 mph cap), one at a time."""

from dataclasses import dataclass

import numpy as np

from rail_runtime import model as m
from rail_runtime.multitrain import JAM_STOPS, PW_EXPRESS, PW_STOPS

CASES = {
    "Port Washington": ("pw_geom.json", PW_STOPS, {"local": PW_STOPS[::-1], "express": PW_EXPRESS[::-1]}),
    "Jamaica": ("jam_geom.json", JAM_STOPS, {"local": JAM_STOPS[::-1], "nonstop": ["Jamaica", "Penn Station"]}),
}


@dataclass
class Zone:
    """A stretch of track and the minutes saved on each pattern by raising its limit."""

    start: float  # mi from Penn
    end: float  # mi from Penn
    near: str  # nearest station
    posted: float | None  # mph; None for a curve ranking
    allows: float  # mph: what the geometry allows, or the curve's own limit
    saved: dict[str, float]

    @property
    def most(self) -> float:
        return max(self.saved.values())


type Ranking = list[tuple[str, dict[str, float], list[Zone]]]


def top_zones(zones: list[Zone], top: int) -> list[Zone]:
    """The `top` zones saving the most, dropping any saving under 3 s."""
    return [z for z in sorted(zones, key=lambda z: (z.most, z.start), reverse=True)[:top] if z.most >= 0.05]


def rank(data: str, top: int = 10) -> Ranking:
    """Per line: (name, base minutes by pattern, the curves costing the most)."""
    m7 = m.TRAINS[0]
    out: Ranking = []
    for name, (gf, stops, pats) in CASES.items():
        line = m.Line(f"{data}/{gf}", f"{data}/substations.json", stops, terminal=name != "Jamaica")
        lim80 = line.limits("80", 80)
        slow = lim80 < 79.5
        edges = np.flatnonzero(np.diff(np.concatenate([[0], slow.astype(int), [0]])))
        base = {k: line.trip(m7, "80", p) for k, p in pats.items()}
        rows: list[Zone] = []
        for i, j in zip(edges[::2], edges[1::2], strict=True):
            lim = lim80.copy()
            lim[i:j] = 80
            saved = {k: base[k] - line.trip(m7, "80", p, lim) for k, p in pats.items()}
            k = i + int(np.argmin(lim80[i:j]))
            near = min(line.st, key=lambda n: abs(line.st[n] - line.s[k]))
            rows.append(
                Zone(float(line.s[i]) / m.MILE, float(line.s[j - 1]) / m.MILE, near, None, float(lim80[k]), saved)
            )
        out.append((name, base, top_zones(rows, top)))
    return out


def show(data: str) -> None:
    for name, base, rows in rank(data):
        print(f"=== {name} (M7, 80 mph, base {', '.join(f'{k} {v:.1f}' for k, v in base.items())} min) ===")
        for z in rows:
            print(
                f"  {z.start:5.2f}-{z.end:5.2f} mi  near {z.near:22} {z.allows:3.0f} mph  "
                + "  ".join(f"{k} {v * 60:4.0f}s" for k, v in z.saved.items())
            )
