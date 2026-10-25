"""Build an ordered track centerline from Penn to a LIRR station from OSM and measure curvature.

usage: geom.py RAIL_JSON ROUTE_JSON|- GTFS DEST_STOP OUT
"""
import csv
import json
import math
import sys

import numpy as np

rail_json, route_json, gtfs, dest, out = sys.argv[1:6]
import heapq
d = json.load(open(rail_json))["elements"]
route_ways = set()
if route_json != "-":
    route_ways = {m["ref"] for e in json.load(open(route_json))["elements"] if e["type"] == "relation" for m in e["members"]}
coord = {}
adj = {}
for w in d:
    t = w["tags"]
    if t.get("service") in ("yard", "spur") or t.get("usage") in ("industrial", "military"):
        continue
    pen = 1.0 if w["id"] in route_ways or (not route_ways and t.get("usage") == "main") else 3.0
    if t.get("service") in ("crossover", "siding"):
        pen = 10.0
    for n, g in zip(w["nodes"], w["geometry"]):
        coord[n] = (g["lat"], g["lon"])
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        la, lo = coord[a]
        lb, lob = coord[b]
        L = math.hypot((la - lb) * 110540, (lo - lob) * 84000)
        adj.setdefault(a, []).append((b, L * pen, w["id"]))
        adj.setdefault(b, []).append((a, L * pen, w["id"]))
wtags = {w["id"]: w["tags"] for w in d}
stop = {r["stop_name"]: (float(r["stop_lat"]), float(r["stop_lon"])) for r in csv.DictReader(open(f"{gtfs}/stops.txt"))}
near = lambda ll: min(adj, key=lambda n: (coord[n][0] - ll[0]) ** 2 + ((coord[n][1] - ll[1]) * 0.76) ** 2)
src_n, dst_n = near(stop["Penn Station"]), near(stop[dest])
MAX_TURN = 30.0  # degrees between consecutive segments; more means reversing through a switch


def turn(a, b, c):
    (la, oa), (lb, ob), (lc, oc) = coord[a], coord[b], coord[c]
    h1 = math.atan2(la - lb, (oa - ob) * 0.76)
    h2 = math.atan2(lb - lc, (ob - oc) * 0.76)
    return abs((math.degrees(h2 - h1) + 180) % 360 - 180)


# Dijkstra over (node, previous node) states so the path can't double back through a switch.
start = (src_n, None)
dist = {start: 0.0}
prev = {}
pq = [(0.0, src_n, None)]
end = None
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
state = end
path = [dst_n]
wpath = []
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

lat0 = np.mean([p[0] for p in pts])
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
for r in csv.DictReader(open(f"{gtfs}/stops.txt")):
    p = np.array([float(r["stop_lon"]) * 111320 * math.cos(math.radians(lat0)), float(r["stop_lat"]) * 110540])
    dd = np.hypot(*(rs - p).T)
    i = int(np.argmin(dd))
    if dd[i] < 150:
        stations.append((r["stop_name"], float(ss[i])))
stations.sort(key=lambda t: t[1])

# Pretty-printed, one station or sample per line, so diffs line up with places on the track.
lonlat = rs / [111320 * math.cos(math.radians(lat0)), 110540]
with open(out, "w") as f:
    f.write('{\n  "stations": [\n')
    f.write(",\n".join(f"    {json.dumps([n, round(x, 1)])}" for n, x in stations))
    f.write('\n  ],\n  "samples": [\n')
    f.write(",\n".join(
        "    " + json.dumps({"s": round(float(x), 1), "R": None if math.isinf(r) else round(float(r), 1),
                            "maxspeed": None if math.isnan(v) else v,
                            "lon": round(float(lo), 7), "lat": round(float(la), 7)})
        for x, r, v, (lo, la) in zip(ss, R, maxspeed, lonlat)))
    f.write("\n  ]\n}\n")
print(f"length {s[-1] / 1609.34:.2f} mi, {len(ss)} samples")
for n, x in stations:
    print(f"  {x / 1609.34:6.2f} mi  {n}")
