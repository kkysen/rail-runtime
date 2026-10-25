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
    return mt.SPECS["Port Washington"].line(DATA)


@cache
def jam() -> m.Line:
    return mt.SPECS["Jamaica"].line(DATA)


@pytest.mark.parametrize(
    ("kind", "local", "express"),
    [("posted", 35.0, 25.5), ("60", 33.5, 23.9), ("80", 32.2, 21.4), ("100", 32.1, 21.1)],
)
def test_port_washington(kind: str, local: float, express: float) -> None:
    assert pw().trip(M7, kind, mt.PW_STOPS[::-1]) == pytest.approx(local, abs=0.05)
    assert pw().trip(M7, kind, mt.PW_EXPRESS[::-1]) == pytest.approx(express, abs=0.05)


@pytest.mark.parametrize(("kind", "local"), [("posted", 14.0), ("60", 12.1), ("80", 10.8), ("100", 10.4)])
def test_atlantic(kind: str, local: float) -> None:
    atl = mt.SPECS["Atlantic"].line(DATA)
    assert atl.trip(M7, kind, mt.ATL_STOPS[::-1]) == pytest.approx(local, abs=0.05)


@pytest.mark.parametrize(
    ("kind", "local", "express"),
    [("posted", 17.0, 13.4), ("60", 15.0, 11.8), ("80", 13.5, 9.5), ("100", 13.2, 9.1)],
)
def test_jamaica(kind: str, local: float, express: float) -> None:
    assert jam().trip(M7, kind, mt.JAM_STOPS[::-1]) == pytest.approx(local, abs=0.05)
    assert jam().trip(M7, kind, ["Jamaica", "Penn Station"]) == pytest.approx(express, abs=0.05)


def test_third_rail_costs_time() -> None:
    """The same M7 with rated power everywhere runs the local faster than with voltage drop on third rail."""
    full = next(t for t in m.TRAINS if t.supply == "full power")
    assert pw().trip(full, "80", mt.PW_STOPS[::-1]) < pw().trip(M7, "80", mt.PW_STOPS[::-1]) - 0.3


def test_curve_ranking() -> None:
    name, base, zones = curves.rank(DATA)[0]
    assert name == "Port Washington"
    assert base["express"] == pytest.approx(21.4, abs=0.05)
    top = zones[0]
    assert (top.near, round(top.allows), round(top.saved["express"] * 60)) == ("Woodside", 48, 27)


def test_slow_zone_ranking() -> None:
    _, _, zones = slowzones.rank(DATA)[1]
    top = zones[0]
    assert (top.near, top.posted, round(top.allows)) == ("Jamaica", 20, 80)
    assert top.saved["express"] * 60 == pytest.approx(60, abs=1)


def test_one_train_simulation_matches_model() -> None:
    """A lone train in the time-stepped simulation runs about as fast as the distance-stepped model.

    They differ by about 7 s on this run: 0.5 s time steps, and each approaches a stop its own way.
    """
    services = [mt.Service("x", mt.PW_EXPRESS, True, 0, 300, 0)]
    done, _ = mt.simulate(pw(), M8, "80", services, 3600, single=True)
    assert mt.runtime(done[0]) == pytest.approx(pw().trip(M8, "80", mt.PW_EXPRESS[::-1]), abs=0.2)
