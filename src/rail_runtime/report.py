"""Print scheduled vs simulated runtimes for every line in `multitrain.SPECS`."""

from collections.abc import Iterable
from statistics import median

from rail_runtime import model as m
from rail_runtime.multitrain import SPECS

KINDS = ["posted", "60", "80", "100"]
# Patterns printed here beyond each line's own.
EXTRA = {
    "Port Washington": {"GN nonstop": ["Great Neck", "Penn Station"]},
    "Jamaica": {"Woodside only": ["Jamaica", "Woodside", "Penn Station"]},
}


def fmt(xs: Iterable[float]) -> str:
    return " ".join(f"{x:6.1f}" for x in xs)


def report(data: str, date: str) -> None:
    m7 = m.TRAINS[0]
    for name, spec in SPECS.items():
        line, stops, route = spec.line(data), spec.stops, spec.route
        print(f"=== {stops[-1]} -> {stops[0]} ===")
        print(
            "substations (mi):",
            " ".join(f"{x / m.MILE:.1f}{'*' if x in line.mapped else ''}" for x in line.subs),
            " (* mapped in OSM)",
        )
        r = line.r_eff
        print(
            f"M7 10-car power available: min {min(m7.power(x) for x in r) / 1e6:.1f} MW, "
            f"mean {sum(m7.power(x) for x in r) / len(r) / 1e6:.1f} MW of {m7.p_shaft / 1e6:.1f} MW rated"
        )
        order = list(reversed(stops))
        trips = m.am_inbound(f"{data}/gtfs", date, None if route else stops[-1], set(stops), route, stops[0])
        print("AM inbound, M7 750 V:   sched  posted     60     80    100")
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
            for pat, sch in sorted(by.items(), key=lambda kv: len(kv[0])):
                sims = [line.trip(m7, k, list(pat)) for k in KINDS]
                mid = " > ".join(p.split()[0] for p in pat[1:-1]) or "nonstop"
                print(f"  {mid:28} n={len(sch):2} sched med {median(sch):4.0f} (min {min(sch):.0f}) {fmt(sims)}")
        for pname, p in (spec.patterns | EXTRA.get(name, {})).items():
            print(f"  {pname}: posted / 60 / 80 / 100")
            for tr in m.TRAINS:
                print(f"    {tr.name:34} {fmt(line.trip(tr, k, p) for k in KINDS)}")
        print()
