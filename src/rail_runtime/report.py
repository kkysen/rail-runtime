"""Print scheduled vs simulated runtimes for every line in `multitrain.SPECS`."""

from collections.abc import Iterable
from statistics import median

from rail_runtime import model as m
from rail_runtime.multitrain import SPECS
from rail_runtime.results import heading

KINDS = ["posted", "60", "80", "100"]
# Patterns printed here beyond each line's own.
EXTRA = {
    "Port Washington": {"GN nonstop": ["Great Neck", "Penn Station"]},
    "Main Line to Penn": {"Woodside only": ["Jamaica", "Woodside", "Penn Station"]},
}


def fmt(xs: Iterable[float]) -> str:
    return " ".join(f"{x:6.1f}" for x in xs)


def report(data: str, date: str, every: bool = False) -> None:
    for name, spec in SPECS.items():
        line, stops, route = spec.line(data), spec.stops, spec.route
        m7 = spec.trains()[0]
        print(f"=== {heading(name, spec)} ===")
        print(
            "substations (mi):",
            " ".join(f"{x / m.MILE:.1f}{'*' if x in line.mapped else ''}" for x in line.subs),
            " (* mapped in OSM)",
        )
        p = [m7.power(x, line.v0) for x in line.r_eff[line.dc]] or [m7.p_shaft]
        print(
            f"{m7.name.split(',')[0]} 10-car power available on third rail: min {min(p) / 1e6:.1f} MW, "
            f"mean {sum(p) / len(p) / 1e6:.1f} MW of {m7.p_shaft / 1e6:.1f} MW rated"
        )
        order = list(reversed(stops))
        trips = m.am_inbound(
            spec.gtfs(data), date, None if route else stops[-1], set(stops), route, stops[0], via=spec.via
        )
        print(f"AM inbound, {m7.name:22} sched  posted     60     80    100")
        if route:
            for t in trips:
                sims = [line.trip(m7, k, [s for s in order if s in t.stops]) for k in KINDS]
                print(
                    f"  {t.num:>5} {int(t.arr // 60)}:{int(t.arr % 60):02d} {t.first[:12]:12} "
                    f"{len(t.stops):2} stops {t.sched:5.0f} {fmt(sims)}"
                )
        else:
            by = {}
            for t in trips:
                by.setdefault(tuple(s for s in order if s in t.stops), []).append(t.sched)
            only_express = sum(len(p) < len(stops) for p in by) == 1
            for pat, sch in sorted(by.items(), key=lambda kv: len(kv[0])):
                sims = [line.trip(m7, k, list(pat)) for k in KINDS]
                mid = " > ".join(p.split()[0] for p in pat[1:-1]) or ("express" if only_express else "nonstop")
                print(f"  {mid:28} n={len(sch):2} sched med {median(sch):4.0f} (min {min(sch):.0f}) {fmt(sims)}")
        for pname, p in (spec.patterns | EXTRA.get(name, {})).items():
            print(f"  {pname}: posted / 60 / 80 / 100")
            for tr in spec.trains(every):
                print(f"    {tr.name:34} {fmt(line.trip(tr, k, p) for k in KINDS)}")
        print()
