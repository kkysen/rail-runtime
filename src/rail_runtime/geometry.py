"""Build an ordered track centerline between two LIRR stations from OSM and measure curvature."""

import heapq
import json
import math
import sys
from collections.abc import Iterable
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from rail_runtime.model import Arr, Geometry, read_csv

type State = tuple[int, int | None]  # (node, previous node)


def third_rail(w: dict[str, Any]) -> bool:
    """Whether an OSM way is LIRR third-rail running track: not a yard, spur, siding or crossover.

    OSM's `electrified` tags are patchy, tagging some third-rail track through Sunnyside as overhead only,
    so this leaves out only what plainly isn't: unelectrified track, Metro-North's,
    and the Northeast Corridor, Amtrak's overhead-only Hell Gate Line through Harold.
    """
    t = w["tags"]
    return (
        t.get("railway") == "rail"
        and t.get("service") not in ("yard", "spur", "siding", "crossover")
        and t.get("electrified") != "no"
        and t.get("name") != "Northeast Corridor"
        and "Metro-North" not in t.get("operator", "")
    )


def catenary(w: dict[str, Any]) -> bool:
    """Whether an OSM way is overhead-wire running track, which AC substations feed.

    Not a yard, spur, siding or crossover.

    Track with both, like Penn's tunnels, counts here and in `third_rail()`.
    """
    t = w["tags"]
    return (
        t.get("railway") == "rail"
        and t.get("service") not in ("yard", "spur", "siding", "crossover")
        and "contact_line" in t.get("electrified", "").split(";")
    )


def count_tracks(xy: Arr, ways: list[dict[str, Any]], k_xy: Arr) -> npt.NDArray[np.int_]:
    """Through tracks at each sample of path `xy` (m), from OSM `ways` scaled to metres by `k_xy`.

    Every 50 m, a cut across the path counts the tracks crossing it within 60 degrees of the path's heading:
    the traced track's corridor, stepping outward while the next track is within 40 m,
    so it takes in all of Harold's fan but not a separate line beyond.
    Only through tracks count, at least 300 m from a dead end either way, so not stubs or leads,
    with tracks told apart by crossings 2.5 m or more apart (track centres are about 4 m).
    A 500 m running median smooths over interlockings.
    """
    coord: dict[int, Arr] = {}
    adj: dict[int, set[int]] = {}
    segs: list[tuple[int, int]] = []
    for w in ways:
        for n, p in zip(w["nodes"], w["geometry"], strict=True):
            coord[n] = np.array([p["lon"], p["lat"]]) * k_xy
        for a, b in pairwise(w["nodes"]):
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
            segs.append((a, b))
    # Distance along the track from every node to the nearest dead end.
    dead = {n: 0.0 for n, v in adj.items() if len(v) == 1}
    pq = [(0.0, n) for n in dead]
    heapq.heapify(pq)
    while pq:
        du, u = heapq.heappop(pq)
        if du > dead[u]:
            continue
        for v in adj[u]:
            dv = du + float(np.hypot(*(coord[u] - coord[v])))
            if dv < dead.get(v, math.inf):
                dead[v] = dv
                heapq.heappush(pq, (dv, v))
    segs = [(a, b) for a, b in segs if min(dead.get(a, math.inf), dead.get(b, math.inf)) >= 300]
    if not segs:
        return np.zeros(len(xy), dtype=int)
    a = np.array([coord[x] for x, _ in segs])
    d = np.array([coord[y] for _, y in segs]) - a
    lo, hi = np.minimum(a, a + d), np.maximum(a, a + d)  # segment bounding boxes
    reach = 500.0
    every = 10  # samples: 50 m
    counts = []
    for i in range(0, len(xy), every):
        p = xy[i]
        h = xy[min(i + 4, len(xy) - 1)] - xy[max(i - 4, 0)]
        h = h / np.hypot(*h)
        nrm = np.array([-h[1], h[0]])
        near = ((lo <= p + reach + 1) & (hi >= p - reach - 1)).all(1)
        an, dn = a[near], d[near]
        # Where each segment crosses the cut p + t * nrm.
        den = dn[:, 0] * nrm[1] - dn[:, 1] * nrm[0]
        ok = np.abs(den) > 1e-9
        den = np.where(ok, den, 1)
        r = p - an
        u = (r[:, 0] * nrm[1] - r[:, 1] * nrm[0]) / den
        t = (r[:, 0] * dn[:, 1] - r[:, 1] * dn[:, 0]) / den
        par = np.abs((dn / np.hypot(*dn.T)[:, None]) @ h) > math.cos(math.radians(60))
        offs = np.sort(t[ok & (u >= 0) & (u <= 1) & (np.abs(t) <= reach) & par])
        if len(offs) == 0:
            counts.append(0)
            continue
        j0 = j1 = int(np.argmin(np.abs(offs)))
        if abs(offs[j0]) > 40:  # none on the traced track's own corridor
            counts.append(0)
            continue
        while j0 > 0 and offs[j0] - offs[j0 - 1] <= 40:
            j0 -= 1
        while j1 < len(offs) - 1 and offs[j1 + 1] - offs[j1] <= 40:
            j1 += 1
        counts.append(1 + int((np.diff(offs[j0 : j1 + 1]) > 2.5).sum()))
    w = 5  # cuts either side: 500 m in all
    padded = np.pad(np.array(counts), w, mode="edge")
    smooth = [int(np.median(padded[i : i + 2 * w + 1])) for i in range(len(counts))]
    return np.repeat(smooth, every)[: len(xy)]


def trace(rail_json: str, route_json: str, gtfs: str, stop_a: str, stop_b: str, out: str, yard: bool = False) -> None:
    """Trace `stop_a` to `stop_b` and write the geometry to `out`.

    `route_json` is Overpass JSON whose relations' members and ways are the route, or `-` for main-line tracks.
    With `yard`, the route's own yard track counts as running track,
    for Far Rockaway and Long Beach, whose platform tracks OSM tags as yard.
    """
    d: list[dict[str, Any]] = json.loads(Path(rail_json).read_text())["elements"]
    route_ways: set[int] = set()
    if route_json != "-":
        for e in json.loads(Path(route_json).read_text())["elements"]:
            if e["type"] == "relation":
                route_ways |= {m["ref"] for m in e["members"]}
            elif e["type"] == "way":
                route_ways.add(e["id"])
    coord: dict[int, tuple[float, float]] = {}
    adj: dict[int, list[tuple[int, float, int]]] = {}
    for w in d:
        t = w["tags"]
        own_yard = yard and w["id"] in route_ways and t.get("service") == "yard"
        if not own_yard and (t.get("service") in ("yard", "spur") or t.get("usage") in ("industrial", "military")):
            continue
        pen = 1.0 if w["id"] in route_ways or (not route_ways and t.get("usage") == "main") else 3.0
        if t.get("service") in ("crossover", "siding"):
            pen = 10.0
        for n, g in zip(w["nodes"], w["geometry"], strict=True):
            coord[n] = (g["lat"], g["lon"])
        for a, b in pairwise(w["nodes"]):
            la, lo = coord[a]
            lb, lob = coord[b]
            L = math.hypot((la - lb) * 110540, (lo - lob) * 84000)
            adj.setdefault(a, []).append((b, L * pen, w["id"]))
            adj.setdefault(b, []).append((a, L * pen, w["id"]))
    wtags = {w["id"]: w["tags"] for w in d}
    stop = {r["stop_name"]: (float(r["stop_lat"]), float(r["stop_lon"])) for r in read_csv(f"{gtfs}/stops.txt")}

    def near(ll: tuple[float, float], nodes: Iterable[int] = adj) -> int:
        return min(nodes, key=lambda n: (coord[n][0] - ll[0]) ** 2 + ((coord[n][1] - ll[1]) * 0.76) ** 2)

    # Snap each end to the route's own tracks where they reach it, not to another line's platform there,
    # but to any track where the route stops short, as it does of Penn's platforms.
    on_route = {n for w in d if w["id"] in route_ways for n in w["nodes"] if n in adj}

    def snap(name: str) -> int:
        n = near(stop[name], on_route or adj)
        dy, dx = (coord[n][0] - stop[name][0]) * 110540, (coord[n][1] - stop[name][1]) * 84000
        return n if math.hypot(dx, dy) < 150 else near(stop[name])

    src_n, dst_n = snap(stop_a), snap(stop_b)
    MAX_TURN = 30.0  # degrees between consecutive segments; more means reversing through a switch

    def turn(a: int, b: int, c: int) -> float:
        (la, oa), (lb, ob), (lc, oc) = coord[a], coord[b], coord[c]
        h1 = math.atan2(la - lb, (oa - ob) * 0.76)
        h2 = math.atan2(lb - lc, (ob - oc) * 0.76)
        return abs((math.degrees(h2 - h1) + 180) % 360 - 180)

    # Dijkstra over (node, previous node) states so the path can't double back through a switch.
    start: State = (src_n, None)
    dist: dict[State, float] = {start: 0.0}
    prev: dict[State, tuple[State, int]] = {}
    pq: list[tuple[float, int, int | None]] = [(0.0, src_n, None)]
    end: State | None = None
    while pq:
        du, u, p = heapq.heappop(pq)
        if u == dst_n:
            end = (u, p)
            break
        if du > dist[(u, p)]:
            continue
        for v, c, wid in adj[u]:
            if v == p or (p is not None and turn(p, u, v) > MAX_TURN):
                continue
            if du + c < dist.get((v, u), 1e18):
                dist[(v, u)] = du + c
                prev[(v, u)] = ((u, p), wid)
                heapq.heappush(pq, (du + c, v, u))
    if end is None:
        raise SystemExit(f"no path from {stop_a} to {stop_b}")
    state = end
    path = [dst_n]
    wpath: list[int] = []
    while state != start:
        state, wid = prev[state]
        path.append(state[0])
        wpath.append(wid)
    path.reverse()
    wpath.reverse()
    pts = [coord[n] for n in path]
    tags = [wtags[w] for w in wpath] + [wtags[wpath[-1]]]
    off = sum(1 for w in set(wpath) if w not in route_ways)
    print(f"path uses {len(set(wpath))} ways, {off} not in route relation", file=sys.stderr)

    lat0 = float(np.mean([p[0] for p in pts]))
    xy = np.array([[(p[1]) * 111320 * math.cos(math.radians(lat0)), p[0] * 110540] for p in pts])
    seg = np.hypot(*np.diff(xy, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    # The first way's orientation may be wrong; fix by checking for a backtrack at the start.

    STEP = 5.0
    ss = np.arange(0, s[-1], STEP)
    rs = np.column_stack([np.interp(ss, s, xy[:, 0]), np.interp(ss, s, xy[:, 1])])
    idx = np.searchsorted(s, ss, side="right") - 1
    maxspeed = []
    for i in idx:
        v = tags[min(i, len(tags) - 1)].get("maxspeed", "")
        maxspeed.append(float(v.split()[0]) if v else math.nan)

    # Curvature from circle through points HALF metres either side, after smoothing.
    HALF = 40.0
    k = int(HALF / STEP)
    sm = np.copy(rs)
    w = 5
    for j in range(2):
        sm[:, j] = np.convolve(np.pad(rs[:, j], w, mode="edge"), np.ones(2 * w + 1) / (2 * w + 1), mode="valid")
    R = np.full(len(ss), np.inf)
    for i in range(k, len(ss) - k):
        a, b, c = sm[i - k], sm[i], sm[i + k]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        la, lb, lc = np.hypot(*(b - a)), np.hypot(*(c - b)), np.hypot(*(c - a))
        if abs(cross) > 1e-9:
            R[i] = la * lb * lc / (2 * abs(cross))

    # Station positions: GTFS stop coordinates projected onto the path.
    stations = []
    for r in read_csv(f"{gtfs}/stops.txt"):
        p = np.array([float(r["stop_lon"]) * 111320 * math.cos(math.radians(lat0)), float(r["stop_lat"]) * 110540])
        dd = np.hypot(*(rs - p).T)
        i = int(np.argmin(dd))
        if dd[i] < 150:
            stations.append((r["stop_name"], float(ss[i])))
    stations.sort(key=lambda t: t[1])

    lonlat = rs / [111320 * math.cos(math.radians(lat0)), 110540]
    k_xy = np.array([111320 * math.cos(math.radians(lat0)), 110540])
    third = count_tracks(rs, [w for w in d if third_rail(w)], k_xy)
    overhead = count_tracks(rs, [w for w in d if catenary(w)], k_xy)
    Geometry(ss, R, np.array(maxspeed), lonlat, stations, third, overhead).save(out)
    print(f"length {s[-1] / 1609.34:.2f} mi, {len(ss)} samples")
    for n, x in stations:
        print(f"  {x / 1609.34:6.2f} mi  {n}")
