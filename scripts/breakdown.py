"""Per-segment scheduled vs simulated times for one trip, plus low posted-speed zones."""
import sys

import numpy as np

trip_num = sys.argv.pop()
import sim  # noqa: E402

print("Posted limits under 50 mph (OSM):")
low = np.nan_to_num(sim.posted, nan=99) < 50
edges = np.flatnonzero(np.diff(np.concatenate([[0], low.astype(int), [0]])))
for a, b in zip(edges[::2], edges[1::2]):
    print(f"  {sim.s[a] / 1609.34:5.2f}-{sim.s[b - 1] / 1609.34:5.2f} mi  {np.nanmin(sim.posted[a:b]):.0f} mph"
          f"  (curve allows {np.min(sim.curve[a:b]):.0f})")
for tid, ss in sim.sts.items():
    if sim.trips[tid]["trip_short_name"] != trip_num:
        continue
    ss.sort(key=lambda r: int(r["stop_sequence"]))
    print(f"\nTrain {trip_num}: segment  sched(dep->arr)  " + "  ".join(k[:12] for k in sim.LIMITS))
    for r0, r1 in zip(ss, ss[1:]):
        a, b = sim.names[r0["stop_id"]], sim.names[r1["stop_id"]]
        sch = sim.hm(r1["arrival_time"]) - sim.hm(r0["departure_time"])
        runs = [sim.run(l, sim.st[a], sim.st[b])[0] / 60 for l in sim.LIMITS.values()]
        print(f"  {a[:14]:>14} > {b[:14]:14} {sch:5.1f}  " + "  ".join(f"{x:12.1f}" for x in runs))
