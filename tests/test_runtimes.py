"""Regression tests on the committed geometry: single-train runtimes, rankings, and one simulation."""

from functools import cache

import pytest

from rail_runtime import curves, slowzones
from rail_runtime import model as m
from rail_runtime import multitrain as mt

DATA = "data"
M7 = m.TRAINS[0]
M8 = next(t for t in m.TRAINS if t.name == "M8, 25 kV")


@cache
def pw() -> m.Line:
    return m.Line(f"{DATA}/pw_geom.json", f"{DATA}/substations.json", mt.PW_STOPS)


@cache
def jam() -> m.Line:
    return m.Line(f"{DATA}/jam_geom.json", f"{DATA}/substations.json", mt.JAM_STOPS, terminal=False)


@pytest.mark.parametrize(
    ("kind", "local", "express"),
    [("posted", 35.2, 25.6), ("60", 33.7, 23.9), ("80", 32.5, 21.6), ("100", 32.5, 21.4)],
)
def test_port_washington(kind: str, local: float, express: float) -> None:
    assert pw().trip(M7, kind, mt.PW_STOPS[::-1]) == pytest.approx(local, abs=0.05)
    assert pw().trip(M7, kind, mt.PW_EXPRESS[::-1]) == pytest.approx(express, abs=0.05)


@pytest.mark.parametrize(
    ("kind", "local", "nonstop"),
    [("posted", 17.2, 13.5), ("60", 15.1, 11.8), ("80", 13.7, 9.7), ("100", 13.6, 9.3)],
)
def test_jamaica(kind: str, local: float, nonstop: float) -> None:
    assert jam().trip(M7, kind, mt.JAM_STOPS[::-1]) == pytest.approx(local, abs=0.05)
    assert jam().trip(M7, kind, ["Jamaica", "Penn Station"]) == pytest.approx(nonstop, abs=0.05)


def test_third_rail_costs_time() -> None:
    """The same M7 with rated power everywhere runs the local faster than on sagging third rail."""
    stiff = next(t for t in m.TRAINS if t.supply == "stiff")
    assert pw().trip(stiff, "80", mt.PW_STOPS[::-1]) < pw().trip(M7, "80", mt.PW_STOPS[::-1]) - 0.5


def test_curve_ranking() -> None:
    name, base, zones = curves.rank(DATA)[0]
    assert name == "Port Washington"
    assert base["express"] == pytest.approx(21.6, abs=0.05)
    top = zones[0]
    assert (top.near, round(top.allows), round(top.saved["express"] * 60)) == ("Woodside", 48, 30)


def test_slow_zone_ranking() -> None:
    _, _, zones = slowzones.rank(DATA)[1]
    top = zones[0]
    assert (top.near, top.posted, round(top.allows)) == ("Kew Gardens", 20, 80)
    assert top.saved["nonstop"] * 60 == pytest.approx(60, abs=1)


def test_one_train_simulation_matches_model() -> None:
    """A lone train in the time-stepped simulation runs about as fast as the distance-stepped model.

    They differ by about 7 s on this run: 0.5 s time steps, and each approaches a stop its own way.
    """
    services = [mt.Service("x", mt.PW_EXPRESS, True, 0, 300, 0)]
    done, _ = mt.simulate(pw(), M8, "80", services, 3600, single=True)
    assert mt.runtime(done[0]) == pytest.approx(pw().trip(M8, "80", mt.PW_EXPRESS[::-1]), abs=0.2)
