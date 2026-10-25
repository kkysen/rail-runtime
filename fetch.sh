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

# Port Washington Branch route relation, with its ways and stops.
overpass '[out:json][timeout:90];rel(1834644);out body;way(r);out tags geom;node(r);out;' data/pw_route.json

# Every rail way around western Queens and northern Nassau.
overpass '[out:json][timeout:160];way["railway"="rail"](40.735,-74.0,40.835,-73.68);out body geom;' data/rail_bbox.json

# A wider box reaching Jamaica.
overpass '[out:json][timeout:160];way["railway"="rail"](40.695,-74.0,40.835,-73.68);out body geom;' data/rail_bbox2.json

# Far Rockaway Branch route relation, for its Atlantic Branch ways from Atlantic Terminal to Jamaica.
overpass '[out:json][timeout:90];rel(8712205);out body;way(r);out tags geom;node(r);out;' data/atl_route.json

# Every rail way across Brooklyn to Jamaica.
overpass '[out:json][timeout:160];way["railway"="rail"](40.66,-73.99,40.71,-73.78);out body geom;' data/rail_bbox_atl.json

# Substations, to place LIRR traction substations along each line.
overpass '[out:json][timeout:160];nwr["power"="substation"](40.69,-74.0,40.835,-73.68);out center tags;' data/substations.json
# The Atlantic Branch's own, kept apart so the other lines' substations don't change.
overpass '[out:json][timeout:160];nwr["power"="substation"](40.66,-73.99,40.71,-73.78);out center tags;' data/substations_atl.json
# Committed, so rewritten one element per line for diffs that line up with substations.
python3 - data/substations.json data/substations_atl.json <<'PY'
import json, sys
for path in sys.argv[1:]:
    with open(path) as f:
        d = json.load(f)
    lines = ["{"]
    lines += [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}," for k, v in d.items() if k != "elements"]
    lines += ['  "elements": [', ",\n".join("    " + json.dumps(e, ensure_ascii=False) for e in d["elements"]), "  ]", "}"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
PY
