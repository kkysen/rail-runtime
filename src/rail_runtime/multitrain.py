"""Time-stepped multi-train runs with a DC third-rail network solve, in the `sim` crate (`sim/src/multi.rs`).

Each service runs on its own track at a fixed headway with one stopping pattern.
Braking trains regenerate into the third rail; substations are diode rectifiers and can't absorb it,
so regen only helps other trains, and a train sheds regen once its voltage reaches 900 V.
"""

from dataclasses import dataclass
from functools import cache
from typing import NamedTuple

import numpy as np

from rail_runtime import _sim
from rail_runtime import model as m
from rail_runtime.model import Arr, Line, Train


class Service(NamedTuple):
    """Trains on one stopping pattern in one direction, on their own track."""

    name: str
    stops: list[str]
    inbound: bool
    track: int
    headway: float  # s
    offset: float  # s, first departure


@dataclass
class Job:
    """One simulation, as `sim` reads it."""

    train: Train
    lim_mph: Arr  # by sample, in chainage order
    ds: float  # m
    s_end: float  # m
    subs: list[float]  # substation chainages, m
    r_subs: list[float]  # substation source resistances, ohm
    r_return: list[float]  # running-rail return from chainage 0 to each sample, ohm
    dc: list[bool]  # whether each sample is on the third rail, not under catenary
    v0: float  # substation output, V
    services: list[tuple[list[float], bool, int, float, float]]  # stop chainages, inbound, track, headway, offset
    horizon: float  # s
    regen: bool
    single: bool  # only the first train to depart, alone


@dataclass
class Finished:
    """A train that reached its last stop."""

    service: str
    inbound: bool
    t0: float  # departure, s
    done: float  # arrival, s


NONCONVERGED = [0]


def job(
    line: Line,
    train: Train,
    kind: str,
    services: list[Service],
    horizon: float,
    regen: bool = True,
    single: bool = False,
) -> Job:
    return Job(
        train=train,
        lim_mph=line.limits(kind, train.vmax),
        ds=line.ds,
        s_end=float(line.s[-1]),
        subs=[float(x) for x in line.subs],
        r_subs=[float(x) for x in line.r_subs],
        r_return=[float(x) for x in line.r_return],
        dc=[bool(x) for x in line.dc],
        v0=line.v0,
        services=[([line.st[n] for n in sv.stops], sv.inbound, sv.track, sv.headway, sv.offset) for sv in services],
        horizon=horizon,
        regen=regen,
        single=single,
    )


def outcome(services: list[Service], out: _sim.Outcome) -> tuple[list[Finished], float]:
    """The finished trains and the lowest train voltage (nan off third rail)."""
    NONCONVERGED[0] += out.nonconverged
    finished = [Finished(services[i].name, services[i].inbound, t0, done) for i, t0, done in out.finished]
    return finished, float("nan") if out.vmin is None else out.vmin


def simulate(
    line: Line,
    train: Train,
    kind: str,
    services: list[Service],
    horizon: float,
    regen: bool = True,
    single: bool = False,
) -> tuple[list[Finished], float]:
    """Run `services` for `horizon` s; returns the finished trains and the lowest train voltage (nan off third rail)."""
    [out] = _sim.simulate_many([job(line, train, kind, services, horizon, regen, single)])
    return outcome(services, out)


PW_STOPS = [
    "Penn Station",
    "Woodside",
    "Mets-Willets Point",
    "Flushing Main Street",
    "Murray Hill",
    "Broadway",
    "Auburndale",
    "Bayside",
    "Douglaston",
    "Little Neck",
    "Great Neck",
    "Manhasset",
    "Plandome",
    "Port Washington",
]
JAM_STOPS = ["Penn Station", "Woodside", "Forest Hills", "Kew Gardens", "Jamaica"]
PW_EXPRESS = ["Penn Station", "Great Neck", "Manhasset", "Plandome", "Port Washington"]
GCM_STOPS = ["Grand Central", "Woodside", "Forest Hills", "Kew Gardens", "Jamaica"]
ATL_STOPS = ["Atlantic Terminal", "Nostrand Avenue", "East New York", "Jamaica"]
# Branches beyond Jamaica, out to where the third rail ends, at the stations their AM trains into Jamaica serve.
HEM_STOPS = [
    "Jamaica",
    "Hollis",
    "Queens Village",
    "Elmont-UBS Arena",
    "Bellerose",
    "Floral Park",
    "Stewart Manor",
    "Nassau Boulevard",
    "Garden City",
    "Country Life Press",
    "Hempstead",
]
BAB_STOPS = [
    "Jamaica",
    "Lynbrook",
    "Rockville Centre",
    "Baldwin",
    "Freeport",
    "Merrick",
    "Bellmore",
    "Wantagh",
    "Seaford",
    "Massapequa",
    "Massapequa Park",
    "Amityville",
    "Copiague",
    "Lindenhurst",
    "Babylon",
]
# Via the Babylon Branch through St. Albans, the Montauk Branch's line to Valley Stream, instead of the Atlantic Branch.
BAB_BRANCH_STOPS = ["Jamaica", "St. Albans", *BAB_STOPS[1:]]
LB_STOPS = [
    "Jamaica",
    "Locust Manor",
    "Laurelton",
    "Rosedale",
    "Valley Stream",
    "Lynbrook",
    "Centre Avenue",
    "East Rockaway",
    "Oceanside",
    "Island Park",
    "Long Beach",
]
FRK_STOPS = [
    "Jamaica",
    "Locust Manor",
    "Laurelton",
    "Rosedale",
    "Valley Stream",
    "Gibson",
    "Hewlett",
    "Woodmere",
    "Cedarhurst",
    "Lawrence",
    "Inwood",
    "Far Rockaway",
]
WH_STOPS = [
    "Jamaica",
    "St. Albans",
    "Westwood",
    "Malverne",
    "Lakeview",
    "Hempstead Gardens",
    "West Hempstead",
]
HUN_STOPS = [
    "Jamaica",
    "Hollis",
    "Queens Village",
    "Elmont-UBS Arena",
    "Floral Park",
    "New Hyde Park",
    "Merillon Avenue",
    "Mineola",
    "Carle Place",
    "Westbury",
    "Hicksville",
    "Syosset",
    "Cold Spring Harbor",
    "Huntington",
]
RONK_STOPS = [
    "Jamaica",
    "Hollis",
    "Queens Village",
    "Elmont-UBS Arena",
    "Floral Park",
    "New Hyde Park",
    "Merillon Avenue",
    "Mineola",
    "Carle Place",
    "Westbury",
    "Hicksville",
    "Bethpage",
    "Farmingdale",
    "Pinelawn",
    "Wyandanch",
    "Deer Park",
    "Brentwood",
    "Central Islip",
    "Ronkonkoma",
]

# Metro-North, out of Grand Central to where the third rail ends, or on the New Haven Line, to New Haven.
# Not Yankees-E 153 St, which only game-day trains serve, nor Highbridge Yard or Springdale's shops.
HUD_STOPS = [
    "Grand Central",
    "Harlem-125 St",
    "Morris Heights",
    "University Heights",
    "Marble Hill",
    "Spuyten Duyvil",
    "Riverdale",
    "Ludlow",
    "Yonkers",
    "Glenwood",
    "Greystone",
    "Hastings-on-Hudson",
    "Dobbs Ferry",
    "Ardsley-on-Hudson",
    "Irvington",
    "Tarrytown",
    "Philipse Manor",
    "Scarborough",
    "Ossining",
    "Croton-Harmon",
]
HAR_STOPS = [
    "Grand Central",
    "Harlem-125 St",
    "Melrose",
    "Tremont",
    "Fordham",
    "Botanical Garden",
    "Williams Bridge",
    "Woodlawn",
    "Wakefield",
    "Mt Vernon West",
    "Fleetwood",
    "Bronxville",
    "Tuckahoe",
    "Crestwood",
    "Scarsdale",
    "Hartsdale",
    "White Plains",
    "North White Plains",
    "Valhalla",
    "Mt Pleasant",
    "Hawthorne",
    "Pleasantville",
    "Chappaqua",
    "Mt Kisco",
    "Bedford Hills",
    "Katonah",
    "Goldens Bridge",
    "Purdy's",
    "Croton Falls",
    "Brewster",
    "Southeast",
]
NH_STOPS = [
    *HAR_STOPS[:9],
    "Mt Vernon East ",  # sic: GTFS names it with a trailing space
    "Pelham",
    "New Rochelle",
    "Larchmont",
    "Mamaroneck",
    "Harrison",
    "Rye",
    "Port Chester",
    "Greenwich",
    "Cos Cob",
    "Riverside",
    "Old Greenwich",
    "Stamford",
    "Noroton Heights",
    "Darien",
    "Rowayton",
    "South Norwalk",
    "East Norwalk",
    "Westport",
    "Green's Farms",
    "Southport",
    "Fairfield",
    "Fairfield-Black Rock",
    "Bridgeport",
    "Stratford",
    "Milford",
    "West Haven",
    "New Haven",
]


class Spec(NamedTuple):
    """A line: its traced geometry, its stops in path order, and the inbound patterns to compare."""

    geometry: str
    substations: str
    stops: list[str]
    patterns: dict[str, list[str]]
    bumpers: tuple[bool, bool]  # whether the start and end of the path are bumpers
    route: str | None  # GTFS route_id of its timetable trips; None for every trip through the last stop
    via: str | None = None  # a station its timetable trips' shapes pass, to tell apart a branch's routes
    railroad: str = "LIRR"  # or "Metro-North"
    fleet: str = "LIRR"  # a key of `model.FLEETS`

    def line(self, data: str) -> Line:
        return m.Line(
            f"{data}/{self.geometry}",
            f"{data}/{self.substations}",
            self.stops,
            self.bumpers,
            spacing(data, self.railroad),
            m.V0 if self.railroad == "LIRR" else m.V0_MNR,
            self.railroad,
        )

    def gtfs(self, data: str) -> str:
        """Its railroad's GTFS feed."""
        return f"{data}/{GTFS[self.railroad]}"

    def trains(self, every: bool = False) -> list[Train]:
        """The trains it runs, the first on third rail; with `every`, the others to compare."""
        return m.trains(every, self.fleet)


GTFS = {"LIRR": "gtfs", "Metro-North": "gtfsmnr"}


SPECS = {
    "Port Washington": Spec(
        "pw_geometry.json",
        "substations.json",
        PW_STOPS,
        {"local": PW_STOPS[::-1], "express": PW_EXPRESS[::-1]},
        (False, True),
        "9",
    ),
    "Main Line to Penn": Spec(
        "jam_geometry.json",
        "substations.json",
        JAM_STOPS,
        {"local": JAM_STOPS[::-1], "express": ["Jamaica", "Penn Station"]},
        (False, False),
        None,
    ),
    "Main Line to GCM": Spec(
        "gcm_geometry.json",
        "substations.json",
        GCM_STOPS,
        {"local": GCM_STOPS[::-1], "express": ["Jamaica", "Grand Central"]},
        (False, False),
        None,
    ),
    "Atlantic": Spec(
        "atl_geometry.json",
        "substations.json",
        ATL_STOPS,
        {"local": ATL_STOPS[::-1]},
        (True, False),
        None,
    ),
    "Hempstead": Spec(
        "hem_geometry.json",
        "substations.json",
        HEM_STOPS,
        {"local": HEM_STOPS[::-1]},
        (False, True),
        "2",
    ),
    "Babylon via Atlantic Branch": Spec(
        "bab_geometry.json",
        "substations.json",
        BAB_STOPS,
        {"local": BAB_STOPS[::-1]},
        (False, False),
        "1",
        "Locust Manor",
    ),
    "Babylon via Babylon Branch": Spec(
        "bab_branch_geometry.json",
        "substations.json",
        BAB_BRANCH_STOPS,
        {"local": BAB_BRANCH_STOPS[::-1]},
        (False, False),
        "1",
        "St. Albans",
    ),
    "Long Beach": Spec(
        "lb_geometry.json",
        "substations.json",
        LB_STOPS,
        {"local": LB_STOPS[::-1]},
        (False, True),
        "6",
    ),
    "Far Rockaway": Spec(
        "frk_geometry.json",
        "substations.json",
        FRK_STOPS,
        {"local": FRK_STOPS[::-1]},
        (False, True),
        "7",
    ),
    "West Hempstead": Spec(
        "wh_geometry.json",
        "substations.json",
        WH_STOPS,
        {"local": WH_STOPS[::-1]},
        (False, True),
        "8",
    ),
    "Huntington": Spec(
        "hun_geometry.json",
        "substations.json",
        HUN_STOPS,
        {"local": HUN_STOPS[::-1]},
        (False, False),
        "10",
    ),
    "Ronkonkoma": Spec(
        "ronk_geometry.json",
        "substations.json",
        RONK_STOPS,
        {"local": RONK_STOPS[::-1]},
        (False, False),
        "4",
    ),
    "Hudson": Spec(
        "hud_geometry.json",
        "substations_mnr.json",
        HUD_STOPS,
        {"local": HUD_STOPS[::-1]},
        (True, False),
        "1",
        railroad="Metro-North",
        fleet="Metro-North",
    ),
    "Harlem": Spec(
        "har_geometry.json",
        "substations_mnr.json",
        HAR_STOPS,
        {"local": HAR_STOPS[::-1]},
        (True, False),
        "2",
        railroad="Metro-North",
        fleet="Metro-North",
    ),
    "New Haven": Spec(
        "nh_geometry.json",
        "substations_mnr.json",
        NH_STOPS,
        {"local": NH_STOPS[::-1]},
        (True, False),
        "3",
        railroad="Metro-North",
        fleet="New Haven",
    ),
}


@cache
def spacing(data: str, railroad: str = "LIRR") -> float:
    """The usual miles between `railroad`'s substations, from a stretch OSM seems to map continuously.

    On the LIRR, that's the mean gap between known ones from Douglaston to Port Washington,
    from the last one west of Douglaston.
    On Metro-North, OSM maps the whole Harlem Line's, but they thin out past North White Plains,
    where most trains turn, so it's the mean gap from Grand Central to there,
    as busy as the Hudson Line to Croton-Harmon and the New Haven Line to Pelham, whose gaps it fills.
    Elsewhere a gap might hide any number of them, and fitting the gaps as whole numbers of intervals
    favors ever tighter spacings, down to whatever floor the fit is given.
    """
    if railroad == "LIRR":
        spec, start, end = SPECS["Port Washington"], "Douglaston", None
    else:
        spec, start, end = SPECS["Harlem"], "Grand Central", "North White Plains"
    geometry = m.load_geometry(f"{data}/{spec.geometry}")
    at = dict(geometry.stations)
    xs = [x for x, _ in m.own_substations(geometry, f"{data}/{spec.substations}", railroad)]
    xs = xs[max(i for i, x in enumerate(xs) if x <= at[start]) if xs[0] <= at[start] else 0 :]
    if end:
        xs = [x for x in xs if x <= at[end] + 800]  # both North White Plains substations
    return (xs[-1] - xs[0]) / (len(xs) - 1) / m.MILE


KINDS = ("posted", "60", "80", "100")


@dataclass
class BusyRow:
    service: str
    train: Train
    kind: str
    one: float  # minutes per inbound trip with one train alone
    regen: float  # minutes per inbound trip in steady busy service
    no_regen: float  # nan unless on third rail
    vmin: float  # lowest train voltage, V; nan unless on third rail


class Setup(NamedTuple):
    title: str
    line: Line
    services: list[Service]
    horizon: float  # s
    window: tuple[float, float]  # departures counted as steady state, s
    trains: list[Train]  # one on third rail, one on AC


def busy_trains(spec: Spec) -> list[Train]:
    """The line's first third-rail train and its first AC train, for busy service."""
    trains = spec.trains()
    return [next(t for t in trains if t.supply == s) for s in ("third rail", "AC")]


def busy(setups: list[Setup]) -> list[list[BusyRow]]:
    """For each setup, a row per inbound service, train and speed case.

    Every simulation for every setup goes to `sim` in one batch, which runs them in parallel.
    """
    # (setup, train, kind, regen, the service run alone or None for all of them busy)
    keys: list[tuple[int, str, str, bool, str | None]] = []
    jobs: list[Job] = []
    services: list[list[Service]] = []
    for si, st in enumerate(setups):
        for tr in st.trains:
            for kind in KINDS:
                for regen in (True, False):
                    if regen or tr.supply == "third rail":
                        keys.append((si, tr.name, kind, regen, None))
                        services.append(st.services)
                for sv in st.services:
                    if sv.inbound:
                        keys.append((si, tr.name, kind, True, sv.name))
                        services.append([c for c in st.services if c.name == sv.name])
    for (si, name, kind, regen, alone), svcs in zip(keys, services, strict=True):
        st = setups[si]
        tr = next(t for t in st.trains if t.name == name)
        jobs.append(job(st.line, tr, kind, svcs, st.horizon, regen, single=alone is not None))
    res = {k: outcome(svcs, out) for k, svcs, out in zip(keys, services, _sim.simulate_many(jobs), strict=True)}
    out: list[list[BusyRow]] = []
    for si, st in enumerate(setups):
        lo, hi = st.window
        rows: list[BusyRow] = []
        for tr in st.trains:
            for kind in KINDS:
                for sv in st.services:
                    if not sv.inbound:
                        continue
                    busy_mean = {}
                    for regen in (True, False):
                        if (si, tr.name, kind, regen, None) not in res:
                            busy_mean[regen] = float("nan")
                            continue
                        done, _ = res[(si, tr.name, kind, regen, None)]
                        xs = [runtime(c) for c in done if c.service == sv.name and c.inbound and lo <= c.t0 < hi]
                        busy_mean[regen] = float(np.mean(xs))
                    one, _ = res[(si, tr.name, kind, True, sv.name)]
                    rows.append(
                        BusyRow(
                            service=sv.name,
                            train=tr,
                            kind=kind,
                            one=runtime(one[0]),
                            regen=busy_mean[True],
                            no_regen=busy_mean[False],
                            vmin=res[(si, tr.name, kind, True, None)][1],
                        )
                    )
        out.append(rows)
    return out


def runtime(c: Finished) -> float:
    """Minutes from departure to arrival."""
    return (c.done - c.t0) / 60


def lines(data: str) -> dict[str, Setup]:
    """The busy-service setups.

    Port Washington local and express, the Main Line to Penn and to GCM, Atlantic, and the branches beyond Jamaica.
    """
    pw = SPECS["Port Washington"].line(data)
    penn = SPECS["Main Line to Penn"].line(data)
    penn_express = ["Penn Station", "Jamaica"]
    out: dict[str, Setup] = {}
    for name, stops in (("PW local", PW_STOPS), ("PW express", PW_EXPRESS)):
        out[name] = Setup(
            f"{name}: 5 min headways each way",
            pw,
            [Service(name, stops, True, 0, 300, 0), Service(name, stops, False, 1, 300, 150)],
            3 * 3600,
            (3600, 7200),
            busy_trains(SPECS["Port Washington"]),
        )
    out["Main Line to Penn"] = Setup(
        "Main Line to Penn: locals and expresses each at 2.5 min headways each way (1.25 min combined)",
        penn,
        [
            Service("Penn local", JAM_STOPS, True, 0, 150, 0),
            Service("Penn express", penn_express, True, 1, 150, 75),
            Service("Penn local", JAM_STOPS, False, 2, 150, 40),
            Service("Penn express", penn_express, False, 3, 150, 115),
        ],
        5400,
        (1800, 3600),
        busy_trains(SPECS["Main Line to Penn"]),
    )
    # Two tracks through the 63rd Street Tunnel, so one service each way: the express, most of GCM's AM trips.
    # 2.5 min headways, as per track to Penn, against about 3.5 min scheduled at the peak (17 to 18 in an hour).
    gcm_express = ["Grand Central", "Jamaica"]
    out["Main Line to GCM"] = Setup(
        "Main Line to GCM: 2.5 min headways each way",
        SPECS["Main Line to GCM"].line(data),
        [
            Service("GCM express", gcm_express, True, 0, 150, 0),
            Service("GCM express", gcm_express, False, 1, 150, 75),
        ],
        5400,
        (1800, 3600),
        busy_trains(SPECS["Main Line to GCM"]),
    )
    # Two tracks, so one service each way, at 5 min headways,
    # a little tighter than the most Atlantic Terminal has scheduled:
    # about 5.5 min out in the PM peak in the 2015 and 2016 GTFS feeds (11 in the busiest hour),
    # and 6 min in in the AM (10).
    # Each train runs on its own track, with no signals or turnbacks at Atlantic Terminal's stub tracks,
    # so the headway only loads the power network.
    atl_headway = 300
    out["Atlantic"] = Setup(
        "Atlantic: 5 min headways each way",
        SPECS["Atlantic"].line(data),
        [
            Service("Atlantic local", ATL_STOPS, True, 0, atl_headway, 0),
            Service("Atlantic local", ATL_STOPS, False, 1, atl_headway, atl_headway / 2),
        ],
        3 * 3600,
        (3600, 7200),
        busy_trains(SPECS["Atlantic"]),
    )
    # The branches beyond Jamaica: one service each way at the busiest hour's scheduled AM arrivals into Jamaica.
    # Branches sharing track toward Jamaica each get their own network, as Penn and GCM do.
    for name, headway in BRANCH_HEADWAYS.items():
        spec = SPECS[name]
        out[name] = Setup(
            f"{name}: {headway / 60:.3g} min headways each way",
            spec.line(data),
            [
                Service(f"{name} local", spec.stops, True, 0, headway, 0),
                Service(f"{name} local", spec.stops, False, 1, headway, headway / 2),
            ],
            3 * 3600,
            (3600, 7200),
            busy_trains(spec),
        )
    return out


BRANCH_KEYS = {
    "hem": "Hempstead",
    "bab": "Babylon",
    "lb": "Long Beach",
    "frk": "Far Rockaway",
    "wh": "West Hempstead",
    "hun": "Huntington",
    "ronk": "Ronkonkoma",
    "hud": "Hudson",
    "har": "Harlem",
    "nh": "New Haven",
}

# Seconds between trains, from the busiest hour of AM arrivals into Jamaica on 2026-10-27.
BRANCH_HEADWAYS = {
    "Hempstead": 1200,  # 3 an hour
    # 8 an hour in all, split between the two routes, but each runs all 8,
    # so the track and third rail they share east of Valley Stream carry the full load.
    "Babylon via Atlantic Branch": 450,
    "Babylon via Babylon Branch": 450,
    "Long Beach": 720,  # 5 an hour
    "Far Rockaway": 900,  # 4 an hour
    # 1 an hour, on mostly single track past Valley Stream, which the simulation doesn't model:
    # each direction still gets its own track.
    "West Hempstead": 3600,
    "Huntington": 600,  # 6 an hour
    "Ronkonkoma": 600,  # 6 an hour
    # Metro-North, from the busiest hour of AM arrivals into Grand Central, or Stamford from New Canaan,
    # counting only trips that start on the electrified line.
    # So not the Hudson's trains from Poughkeepsie, whose dual-mode locomotives take the third rail
    # only within Grand Central, until their replacements, which will take it throughout,
    # and which wait to be modeled with the diesel trains.
    # Each line runs on its own network, though Harlem and New Haven trains share the third rail to Woodlawn,
    # and all three lines share Park Avenue's into Grand Central.
    "Hudson": 3600 / 7,
    "Harlem": 3600 / 16,
    "New Haven": 3600 / 15,
}


def show(data: str, which: str) -> None:
    """Print busy-service runs for `which`: `pw`, `penn`, `gcm`, `atl`, or a key of `BRANCH_KEYS`."""
    prefix = {"pw": "PW", "penn": "Main Line to Penn", "gcm": "Main Line to GCM", "atl": "Atlantic"} | BRANCH_KEYS
    prefix = prefix[which]
    setups = [st for key, st in lines(data).items() if key.startswith(prefix)]
    for st, rows in zip(setups, busy(setups), strict=True):
        print(f"--- {st.title} ---")
        print(f"{'service':16} {'train':28} {'kind':6} {'1 train':>8} {'busy':>6} {'busy no regen':>14} {'min V':>6}")
        for r in rows:
            print(
                f"{r.service:16} {r.train.name:28} {r.kind:6} {r.one:8.1f} {r.regen:6.1f} "
                f"{r.no_regen:14.1f} {r.vmin:6.0f}"
            )
    print(f"non-converged network solves: {NONCONVERGED[0]}")
