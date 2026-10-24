"""List Port Washington Branch AM inbound trips to Penn from the LIRR GTFS feed."""
import csv
import sys
from collections import defaultdict

gtfs, date = sys.argv[1], sys.argv[2]
rd = lambda f: list(csv.DictReader(open(f"{gtfs}/{f}")))
stops = {s["stop_id"]: s["stop_name"] for s in rd("stops.txt")}
svc = {c["service_id"] for c in rd("calendar_dates.txt") if c["date"] == date and c["exception_type"] == "1"}
trips = {t["trip_id"]: t for t in rd("trips.txt") if t["route_id"] == "9" and t["service_id"] in svc}
st = defaultdict(list)
for r in rd("stop_times.txt"):
    if r["trip_id"] in trips:
        st[r["trip_id"]].append(r)


def mins(t):
    h, m, s = map(int, t.split(":"))
    return h * 60 + m + s / 60


rows = []
for tid, ss in st.items():
    ss.sort(key=lambda r: int(r["stop_sequence"]))
    names = [stops[r["stop_id"]] for r in ss]
    if names[-1] != "Penn Station":
        continue
    arr = mins(ss[-1]["arrival_time"])
    if not 6 * 60 <= arr <= 10 * 60:
        continue
    t = {stops[r["stop_id"]]: r for r in ss}
    pw = mins(ss[-1]["arrival_time"]) - mins(t["Port Washington"]["departure_time"]) if "Port Washington" in t else None
    gn = mins(ss[-1]["arrival_time"]) - mins(t["Great Neck"]["departure_time"]) if "Great Neck" in t else None
    rows.append((ss[-1]["arrival_time"], trips[tid]["trip_short_name"], ss[0]["departure_time"][:5], len(ss), pw, gn, " > ".join(n[:10] for n in names)))
for r in sorted(rows):
    print(f"arr {r[0][:5]} #{r[1]:>5} dep {r[2]} stops={r[3]:2} PW-Penn={r[4] if r[4] is None else round(r[4])} GN-Penn={r[5] if r[5] is None else round(r[5])}\n    {r[6]}")
