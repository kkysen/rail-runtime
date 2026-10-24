"""Build the ordered Penn-Port Washington track centerline from OSM and measure curvature."""
import csv
import json
import math
import sys

import numpy as np

route_json, gtfs, out = sys.argv[1:4]
d = json.load(open(route_json))["elements"]
rel = next(e for e in d if e["type"] == "relation")
ways = {e["id"]: e for e in d if e["type"] == "way"}

# Chain ways in relation order, flipping each to continue from the previous end.
pts = []
tags = []
for m in rel["members"]:
    if m["type"] != "way":
        continue
    w = ways[m["ref"]]
    g = [(p["lat"], p["lon"]) for p in w["geometry"]]
    if pts:
        end = pts[-1]
        dist = lambda p: (p[0] - end[0]) ** 2 + (p[1] - end[1]) ** 2
        if dist(g[-1]) < dist(g[0]):
            g = g[::-1]
        gap = math.sqrt(dist(g[0])) * 111e3
        if gap > 30:
            print(f"warning: {gap:.0f} m gap before way {w['id']}", file=sys.stderr)
        g = g[1:]
    elif len(rel["members"]) > 1:
        pass
    pts += g
    tags += [w["tags"]] * len(g)

# Ensure the path starts at Penn (west end).
if pts[0][1] > pts[-1][1]:
    pts, tags = pts[::-1], tags[::-1]

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

json.dump({"s": ss.tolist(), "R": [None if math.isinf(x) else x for x in R],
           "maxspeed": [None if math.isnan(x) else x for x in maxspeed],
           "stations": stations, "lonlat": (rs / [111320 * math.cos(math.radians(lat0)), 110540]).tolist()},
          open(out, "w"))
print(f"length {s[-1] / 1609.34:.2f} mi, {len(ss)} samples")
for n, x in stations:
    print(f"  {x / 1609.34:6.2f} mi  {n}")
