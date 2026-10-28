"""The `rail-runtime` command line."""

from pathlib import Path
from typing import Annotated

import typer

from rail_runtime import curves as curves_
from rail_runtime import geom as geom_
from rail_runtime import multitrain as multitrain_
from rail_runtime import report as report_
from rail_runtime import results as results_
from rail_runtime import slowzones as slowzones_

app = typer.Typer(no_args_is_help=True)

DataDir = Annotated[Path, typer.Option(help="Downloaded and generated data, from `fetch.sh`.")]
Date = Annotated[str, typer.Option(help="Timetable service date, YYYYMMDD.")]


@app.command()
def geom(
    rail_json: Path,
    route_json: Annotated[str, typer.Argument(help="OSM route relation JSON, or `-` to prefer main-line tracks.")],
    gtfs: Path,
    a: Annotated[str, typer.Argument(help="GTFS stop name at one end; distances run from here.")],
    b: Annotated[str, typer.Argument(help="GTFS stop name at the other end.")],
    out: Path,
    yard: Annotated[bool, typer.Option(help="Count the route's own yard track as running track.")] = False,
) -> None:
    """Trace a route between two stops over OSM rail and write its geometry."""
    geom_.trace(str(rail_json), route_json, str(gtfs), a, b, str(out), yard)


@app.command()
def report(data: DataDir = Path("data"), date: Date = "20261027") -> None:
    """Print AM inbound timetable runtimes next to the model, and every train type."""
    report_.report(str(data), date)


@app.command()
def multitrain(
    which: Annotated[
        str,
        typer.Argument(
            help="`pw` for Port Washington, `penn` or `gcm` for the Main Line to Penn or GCM, `atl` for Atlantic, "
            "or a branch beyond Jamaica: `hem`, `bab`, `lb`, `frk`, `wh`, `hun`."
        ),
    ],
    data: DataDir = Path("data"),
) -> None:
    """Print busy-service runs from the time-stepped multi-train simulation."""
    multitrain_.show(str(data), which)


@app.command()
def slowzones(data: DataDir = Path("data")) -> None:
    """Rank posted slow zones by the time they cost."""
    slowzones_.show(str(data))


@app.command()
def curves(data: DataDir = Path("data")) -> None:
    """Rank curves by the time they cost at an 80 mph cap."""
    curves_.show(str(data))


@app.command()
def results(data: DataDir = Path("data"), date: Date = "20261027") -> None:
    """Regenerate the results tables in `README.md`."""
    results_.main(str(data), date)
