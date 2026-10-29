#!/usr/bin/env bash
# Download the LIRR GTFS feed and the OSM extracts into `data/`.
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p data

overpass() {
    local query="$1"
    local out="$2"
    local wait=10
    local url
    for _ in 1 2 3 4 5 6; do
        for url in https://overpass-api.de/api/interpreter https://overpass.private.coffee/api/interpreter; do
            if curl -sf -m 170 -A "rail-runtime/0.1" --data-urlencode "data=$query" "$url" -o "$out.tmp" \
                && python3 -c 'import json, sys; json.load(open(sys.argv[1]))' "$out.tmp"; then
                mv "$out.tmp" "$out"
                echo "fetched $out"
                return 0
            fi
        done
        sleep "$wait"
        wait=$((wait * 2))
    done
    echo "failed to fetch $out" >&2
    return 1
}

# LIRR GTFS schedule.
curl -sfL -m 60 https://rrgtfsfeeds.s3.amazonaws.com/gtfslirr.zip -o data/gtfslirr.zip
rm -rf data/gtfs
mkdir data/gtfs
unzip -q data/gtfslirr.zip -d data/gtfs

# Metro-North GTFS schedule.
curl -sfL -m 60 https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip -o data/gtfsmnr.zip
rm -rf data/gtfsmnr
mkdir data/gtfsmnr
unzip -q data/gtfsmnr.zip -d data/gtfsmnr

# Port Washington Branch route relation, with its ways and stops.
overpass '[out:json][timeout:90];rel(1834644);out body;way(r);out tags geom;node(r);out;' data/pw_route.json

# Every rail way around western Queens and northern Nassau.
overpass '[out:json][timeout:160];way["railway"="rail"](40.735,-74.0,40.835,-73.68);out body geom;' data/rail_bbox.json

# A wider box reaching Jamaica.
overpass '[out:json][timeout:160];way["railway"="rail"](40.695,-74.0,40.835,-73.68);out body geom;' data/rail_bbox2.json

# Far Rockaway Branch route relation, for its Atlantic Branch ways from Atlantic Terminal to Jamaica.
overpass '[out:json][timeout:90];rel(8712205);out body;way(r);out tags geom;node(r);out;' data/atl_route.json

# The Grand Central Branch, from Grand Central Madison through the 63rd Street Tunnel to the Main Line;
# it has no route relation, and Metro-North's tracks lie closer to the stop than its own.
overpass '[out:json][timeout:90];way["railway"="rail"]["name"="Grand Central Branch"](40.695,-74.0,40.835,-73.68);out ids;' data/gcm_route.json

# Every rail way across Brooklyn to Jamaica.
overpass '[out:json][timeout:160];way["railway"="rail"](40.66,-73.99,40.71,-73.78);out body geom;' data/rail_bbox_atl.json

# Every rail way across Queens, Nassau and western Suffolk, out to Far Rockaway, Long Beach, Huntington and Ronkonkoma.
overpass '[out:json][timeout:280];way["railway"="rail"](40.57,-73.84,40.89,-73.07);out body geom;' data/rail_bbox_li.json

# Route relations for the electrified branches beyond Jamaica.
overpass '[out:json][timeout:90];rel(4600806);out body;way(r);out tags geom;' data/hem_route.json
overpass '[out:json][timeout:90];rel(8712205);out body;way(r);out tags geom;' data/frk_route.json
overpass '[out:json][timeout:90];rel(8712202);out body;way(r);out tags geom;' data/lb_route.json
overpass '[out:json][timeout:90];rel(3917588);out body;way(r);out tags geom;' data/wh_route.json
overpass '[out:json][timeout:90];rel(1255264);out body;way(r);out tags geom;' data/hun_route.json
# Ronkonkoma's relation misses much of the Main Line, so take Port Jefferson's for that.
overpass '[out:json][timeout:90];rel(id:8325874,1255264);out body;way(r);out tags geom;' data/ronk_route.json
# Babylon's relation runs Jamaica to Valley Stream on the Montauk Branch through St. Albans,
# which some of its trains take, but most run the Atlantic Branch there,
# so that route takes Long Beach's ways for that stretch.
overpass '[out:json][timeout:90];rel(4509484);out body;way(r);out tags geom;' data/bab_branch_route.json
python3 - data/bab_branch_route.json data/lb_route.json data/bab_route.json <<'PY'
import json, sys
bab, lb = (json.load(open(p))["elements"] for p in sys.argv[1:3])
# East of Valley Stream, about 73.71 W, where the two branches meet.
ways = [e for e in bab if e["type"] == "way" and min(g["lon"] for g in e["geometry"]) > -73.71]
ways += [e for e in lb if e["type"] == "way" and e["tags"].get("name") != "Long Beach Branch"]
with open(sys.argv[3], "w") as f:
    json.dump({"elements": ways}, f)
PY

# Committed substation extracts are rewritten one element per line, for diffs that line up with substations.
one_per_line() {
    python3 - "$1" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    d = json.load(f)
lines = ["{"]
lines += [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}," for k, v in d.items() if k != "elements"]
lines += ['  "elements": [', ",\n".join("    " + json.dumps(e, ensure_ascii=False) for e in d["elements"]), "  ]", "}"]
with open(path, "w") as f:
    f.write("\n".join(lines) + "\n")
PY
}

# Substations, to place LIRR traction substations along each line.
overpass '[out:json][timeout:160];nwr["power"="substation"](40.57,-74.0,40.89,-73.07);out center tags;' data/substations.json
one_per_line data/substations.json

# Metro-North's Hudson, Harlem and New Haven Line route relations, and the New Canaan Branch's.
overpass '[out:json][timeout:90];rel(1186686);out body;way(r);out tags geom;' data/hud_route.json
overpass '[out:json][timeout:90];rel(1158719);out body;way(r);out tags geom;' data/har_route.json
overpass '[out:json][timeout:90];rel(1260624);out body;way(r);out tags geom;' data/nh_route.json
overpass '[out:json][timeout:90];rel(1910690);out body;way(r);out tags geom;' data/nc_route.json
# Every rail way and substation near them: the lines reach New Haven, too far for one box.
mnr='rel(id:1186686,1158719,1260624,1910690);way(r)->.r;'
overpass "[out:json][timeout:280];${mnr}way(around.r:120)[\"railway\"=\"rail\"];out body geom;" data/rail_mnr.json
overpass "[out:json][timeout:280];${mnr}nwr(around.r:600)[\"power\"=\"substation\"];out center tags;" data/substations_mnr.json
one_per_line data/substations_mnr.json
