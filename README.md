# rail-runtime

Minimum train runtimes from track geometry and train performance,
compared with what timetables schedule.

So far this covers four LIRR services into Manhattan and Brooklyn:
into Penn Station, the Port Washington Branch (all stops, and expresses nonstop from Great Neck)
and the Main Line from Jamaica,
into Grand Central Madison (GCM), the Main Line from Jamaica through the 63rd Street Tunnel,
and into Atlantic Terminal, the Atlantic Branch from Jamaica.
Beyond Jamaica, it covers the electrified branches into Jamaica from Hempstead, Babylon, Long Beach, Far Rockaway, West Hempstead, Huntington and Ronkonkoma.
On Metro-North, it covers the electric lines into Grand Central (GCT): the Harlem Line to Southeast, the Hudson Line to Croton-Harmon, the New Haven Line to New Haven, and into Stamford, its New Canaan Branch.

## Method

- **Track:** `rail_runtime.geometry` traces the route from Penn, GCM, Atlantic Terminal or Jamaica over OpenStreetMap rail ways
  (the OSM route relation where there is one, otherwise `usage=main` tracks),
  with a shortest-path search that can't reverse through a switch.
  It resamples the path every 5 m and measures curve radius
  from a circle through points 40 m either side, after smoothing.
- **Speed limits:** four cases.
  - "Posted" uses OSM `maxspeed`.
  - "60", "80" and "100 mph" use curve speed only,
    with 6 in of superelevation and 3 in of unbalance,
    capped at that speed, which also replaces each train's own top speed.
    Where the posted speed is higher, up to the train's top speed, the posted speed holds instead,
    so no case is slower than posted anywhere:
    a 60 mph cap doesn't slow track already posted at 80,
    and posted speeds above what the curve estimate allows are kept.
    They assume every switch is rebuilt to curve speed:
    through interlockings, curvature is measured on a path smoothed over 200 m
    so crossover kinks don't count as curves.
  - A restriction holds until the whole train has cleared it,
    and a bumper terminal like Port Washington or Atlantic Terminal is approached at 15 mph.
- **Trains:** tractive effort up to the rated acceleration,
  then constant power, minus Davis resistance,
  with 8% rotating mass and a 2 mph/s service brake unless noted.
  Dwells are 30 s and runs are flat, with no schedule padding.
- **Third rail:** 750 V substations from OSM,
  with gaps filled at the usual spacing, as near as whole substations allow,
  and continued at it past the outermost mapped ones to the first at or beyond each end of the line,
  rather than assuming one at the terminals.
  That spacing, 1.42 mi, is the mean gap between known LIRR substations from just west of Douglaston to Port Washington,
  the one stretch OSM seems to map continuously;
  elsewhere a long gap likely hides ones OSM doesn't map, and how many is anyone's guess.
  With an M7 at full current on every track, it leaves 453 V midway between two,
  below the 500 V cutoff, so they aren't spaced for every train drawing full current at once.
  Known means tagged as the LIRR's in OSM, or untagged there but identified elsewhere:
  the Jamaica and Winfield substations, from MTA contracts to replace them.
  Untagged substations within 50 m of the track count too,
  but only at least half that spacing from the others, where there's room for one.
  Amtrak's, the subway's and the utilities' substations don't count,
  and are kept for when those lines are modeled.
  A substation has a rectifier unit for every two LIRR third-rail through tracks beside it, counted from OSM,
  rounded up, each with 0.01 Ω source resistance,
  so one on the four-track Main Line has two and Winfield, feeding six, has three.
  No ratings for LIRR substations turned up to calibrate this.
  Each track has 0.02 Ω per mile of steel contact rail, fed from both sides,
  and 0.02 Ω per mile of running-rail return, whose rails are bonded across every parallel track,
  so a train alone on four tracks returns through a quarter of that.
  Trains draw up to their rated current and shed load below 500 V.
  25 kV trains get rated power everywhere.
  The "full power" M7 is the same train on a third rail with no voltage drop,
  so it also gets rated power everywhere: the gap to the plain M7 is what voltage drop costs.
- **Busy service:** the `sim` crate steps every train on the line every 0.5 s,
  solving the DC network each step with diode rectifier substations.
  With regenerative braking, braking trains feed other trains at 80% efficiency,
  up to 900 V.
  Each service has its own track, with no signals or terminal turnbacks,
  so a headway loads the power network but isn't checked against track capacity.
  A branch beyond Jamaica runs one service each way,
  as often as its busiest hour of AM arrivals into Jamaica.
  That service is a local stopping everywhere, on purpose,
  even on branches like Huntington and Ronkonkoma where no AM train does.
  Every line is assumed double-track, one track each way, for now,
  even where it isn't, like the mostly single-track West Hempstead Branch.
  Each line is its own power network, even where lines share track,
  like Babylon and Long Beach from Jamaica to Lynbrook, so neither loads the other's.
  Babylon is two lines, one per route its trains take from Jamaica to Valley Stream:
  the Atlantic Branch, which Long Beach and Far Rockaway share,
  or the Babylon Branch through St. Albans.
  Each runs all of the busiest hour's trains, not its share,
  so the stretch they share east of Valley Stream carries the full load either way.
  Shared networks are still to come.
- **Metro-North:** traced, timed and simulated the same way, from Metro-North's GTFS feed and OSM route relations.
  - Its under-running third rail is 700 V, as OSM tags it,
    with the LIRR's rail and substation resistances, since no figures for Metro-North's turned up either.
    Trains still shed load below 500 V and regen above 900 V,
    and a train's current limit is its rated draw at 700 V, so with no voltage drop it still gets rated power.
  - Substations are Metro-North's from OSM, which maps all of the Harlem Line's, from 110th St to Putnam Junction.
    Their gaps thin out past North White Plains, where most Harlem trains turn,
    so gaps elsewhere are filled at their mean spacing from Grand Central through North White Plains, 1.29 mi,
    which is as busy as the Hudson Line to Croton-Harmon and the New Haven Line to Pelham, whose gaps it fills.
    Past Mott Haven, OSM maps none of the Hudson Line's, and past Woodlawn, none of the New Haven Line's.
  - The M7A is an M7 on that third rail; the M8 is an M8 on 12.5 kV AC throughout, like the LIRR's 25 kV one.
  - Busy service runs one local each way, as on the branches beyond Jamaica,
    as often as the busiest hour of AM arrivals into GCT from trips that start on the line: 16 an hour on the Harlem.
    Each line is its own power network,
    though Harlem and New Haven trains share the third rail to Woodlawn, and all three share Park Avenue's.
  - The Hudson Line's busy service runs 7 an hour: not its trains from Poughkeepsie,
    whose dual-mode locomotives take the third rail only within Grand Central.
    Their replacements will take it throughout, and they wait to be modeled with the diesel trains.
  - On the New Haven Line, the M8 runs on the third rail to just west of Pelham, mile 14.7,
    where Metro-North's trains change over, and on 12.5 kV catenary beyond, at rated power.
    The third rail's substations stop where it does.
    Its timetable trips start no farther out than New Haven's Union Station, where the trace ends,
    so not at New Haven-State St, and its busy service runs 15 an hour.
  - The New Canaan Branch is all catenary, and like the branches beyond Jamaica,
    it's timed into Stamford from trips that start on it, with busy service 2 an hour.
- **Timetable:** AM inbound trips from the LIRR's and Metro-North's GTFS feeds.
  A branch beyond Jamaica is timed into Jamaica, from trips that start on it.
  Babylon's trips are timed on the route their GTFS shape follows.

## Running

`mise install` sets up `uv` and `pre-commit`;
`uv` manages Python 3.15 and the dependencies,
and builds the Rust simulation core in `sim/` with `maturin`, so `cargo` must be installed.
Regenerating every result takes about 10 s.

```sh
./fetch.sh  # LIRR and Metro-North GTFS and OSM extracts into data/
# Optional: retrace the geometry, which is committed in data/.
uv run rail-runtime geometry data/rail_bbox.json data/pw_route.json data/gtfs "Penn Station" "Port Washington" data/pw_geometry.json
uv run rail-runtime geometry data/rail_bbox2.json - data/gtfs "Penn Station" Jamaica data/jam_geometry.json
uv run rail-runtime geometry data/rail_bbox2.json data/gcm_route.json data/gtfs "Grand Central" Jamaica data/gcm_geometry.json
uv run rail-runtime geometry data/rail_bbox_atl.json data/atl_route.json data/gtfs "Atlantic Terminal" Jamaica data/atl_geometry.json
uv run rail-runtime geometry data/rail_bbox_li.json data/hem_route.json data/gtfs Jamaica Hempstead data/hem_geometry.json
uv run rail-runtime geometry data/rail_bbox_li.json data/bab_route.json data/gtfs Jamaica Babylon data/bab_geometry.json
uv run rail-runtime geometry data/rail_bbox_li.json data/bab_branch_route.json data/gtfs Jamaica Babylon data/bab_branch_geometry.json
uv run rail-runtime geometry --yard data/rail_bbox_li.json data/lb_route.json data/gtfs Jamaica "Long Beach" data/lb_geometry.json
uv run rail-runtime geometry --yard data/rail_bbox_li.json data/frk_route.json data/gtfs Jamaica "Far Rockaway" data/frk_geometry.json
uv run rail-runtime geometry data/rail_bbox_li.json data/wh_route.json data/gtfs Jamaica "West Hempstead" data/wh_geometry.json
uv run rail-runtime geometry data/rail_bbox_li.json data/hun_route.json data/gtfs Jamaica Huntington data/hun_geometry.json
uv run rail-runtime geometry data/rail_bbox_li.json data/ronk_route.json data/gtfs Jamaica Ronkonkoma data/ronk_geometry.json
uv run rail-runtime geometry --railroad Metro-North data/rail_mnr.json data/hud_route.json data/gtfsmnr "Grand Central" Croton-Harmon data/hud_geometry.json
uv run rail-runtime geometry --railroad Metro-North data/rail_mnr.json data/har_route.json data/gtfsmnr "Grand Central" Southeast data/har_geometry.json
uv run rail-runtime geometry --railroad Metro-North data/rail_mnr.json data/nh_route.json data/gtfsmnr "Grand Central" "New Haven" data/nh_geometry.json
uv run rail-runtime geometry --railroad Metro-North data/rail_mnr.json data/nc_route.json data/gtfsmnr Stamford "New Canaan" data/nc_geometry.json
# Regenerate the results below.
uv run rail-runtime results
```

`rail-runtime report`, `multitrain`, `slowzones` and `curves`
print the same results as plain text.
The results cover the LIRR's own M7 and M8, and Metro-North's M7A and M8;
`--every-train` on `results` or `report` adds the other trains to the LIRR's lines, for comparison.
Rerun `rail-runtime results` in any commit that changes results,
so the tables below change with it.

## Development

```sh
pre-commit install  # ruff, ty, pyrefly, pytest, and cargo fmt, clippy and test, on every commit
uv run pytest       # well under a second, on the committed data; no fetch.sh needed
cargo test --manifest-path sim/Cargo.toml
```

## Results

<!-- BEGIN results: generated by rail_runtime.results, do not edit by hand -->

### Timetable vs. model

AM inbound trips arriving at Penn, GCM or Atlantic, or Jamaica from beyond it, or on Metro-North at GCT, or Stamford from New Canaan, 6-10 AM on 2026-10-27, grouped by stopping pattern: median scheduled minutes vs. one train running flat out with 30 s dwells: an M7 on the LIRR's 750 V third rail, an M7A on Metro-North's 700 V, or on the New Haven Line, an M8 on that third rail to Pelham and 12.5 kV catenary beyond.

#### Port Washington - Penn

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Great Neck, skips Mets | 2 | 39 | 26.2 | 24.9 | 23.5 | 23.2 |
| Port Washington, stops at Plandome, Manhasset, Great Neck | 2 | 38 | 25.5 | 23.7 | 21.1 | 20.8 |
| Great Neck, all stops | 1 | 38 | 27.3 | 26.0 | 24.7 | 24.5 |
| Port Washington, stops at Plandome, Manhasset, Great Neck, Bayside | 1 | 40 | 26.6 | 24.8 | 22.4 | 22.2 |
| Port Washington, all stops | 1 | 49 | 35.0 | 33.3 | 31.9 | 31.7 |
| Port Washington, skips Auburndale, Broadway, Murray Hill, Flushing | 1 | 45 | 30.7 | 29.0 | 27.2 | 27.0 |
| Port Washington, skips Auburndale, Broadway, Murray Hill, Flushing, Mets | 1 | 44 | 29.7 | 28.0 | 26.0 | 25.7 |

#### Jamaica - Penn

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jamaica, nonstop | 38 | 19 | 13.4 | 10.8 | 9.6 | 9.1 |
| Jamaica, stops at Woodside | 6 | 20 | 14.4 | 11.8 | 10.8 | 10.3 |
| Jamaica, stops at Forest Hills | 4 | 19 | 14.7 | 12.1 | 10.9 | 10.6 |
| Jamaica, stops at Kew Gardens | 4 | 19 | 14.6 | 12.1 | 10.9 | 10.5 |
| Jamaica, skips Woodside | 2 | 22 | 15.9 | 13.4 | 12.2 | 11.9 |
| Jamaica, all stops | 1 | 22 | 17.0 | 14.4 | 13.4 | 13.2 |

#### Jamaica - GCM

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jamaica, nonstop | 22 | 19 | 12.9 | 10.4 | 9.7 | 9.2 |
| Jamaica, stops at Woodside | 8 | 19 | 14.0 | 11.4 | 10.9 | 10.5 |
| Jamaica, stops at Forest Hills | 4 | 20 | 14.2 | 11.7 | 11.0 | 10.8 |
| Jamaica, stops at Kew Gardens | 4 | 19 | 14.1 | 11.7 | 11.0 | 10.7 |
| Jamaica, skips Woodside | 2 | 21 | 15.4 | 13.0 | 12.3 | 12.1 |

#### Jamaica - Atlantic

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jamaica, all stops | 26 | 20 | 13.9 | 11.6 | 10.8 | 10.4 |
| Jamaica, express | 1 | 19 | 12.1 | 9.4 | 8.3 | 7.8 |

#### Hempstead - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hempstead, all stops | 7 | 31 | 22.4 | 20.2 | 20.2 | 20.2 |
| Hempstead, express | 2 | 30 | 18.7 | 16.6 | 16.5 | 16.2 |

#### Babylon via Atlantic Branch - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Wantagh, skips Lynbrook | 4 | 30 | 22.5 | 21.9 | 20.6 | 20.4 |
| Babylon, skips Bellmore, Merrick, Freeport, Baldwin, Rockville Centre, Lynbrook | 3 | 47 | 32.8 | 32.1 | 30.7 | 29.7 |
| Babylon, skips Lynbrook | 2 | 52 | 39.5 | 38.9 | 37.4 | 37.2 |
| Babylon, stops at Amityville, Massapequa, Bellmore, Freeport | 1 | 39 | 28.9 | 28.3 | 26.8 | 25.7 |
| Babylon, skips Bellmore, Merrick, Freeport, Lynbrook | 1 | 49 | 35.5 | 34.9 | 33.4 | 32.8 |
| Babylon, skips Freeport, Baldwin, Rockville Centre, Lynbrook | 1 | 49 | 35.4 | 34.8 | 33.3 | 32.7 |
| Babylon, skips Bellmore, Merrick, Freeport, Baldwin, Rockville Centre | 1 | 49 | 33.9 | 33.2 | 32.0 | 31.0 |
| Babylon, stops at Wantagh, Bellmore, Merrick, Freeport | 1 | 47 | 28.8 | 28.2 | 26.7 | 25.2 |
| Wantagh, all stops | 1 | 32 | 23.6 | 23.0 | 21.9 | 21.8 |

#### Babylon via Babylon Branch - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Babylon, skips Bellmore, Merrick, Freeport, Baldwin, Rockville Centre, Lynbrook, St. Albans | 5 | 46 | 33.8 | 32.9 | 31.3 | 30.2 |
| Wantagh, skips Lynbrook, St. Albans | 2 | 30 | 23.6 | 22.6 | 21.2 | 20.9 |
| Babylon, all stops | 1 | 53 | 42.6 | 41.8 | 40.6 | 40.4 |
| Babylon, stops at Wantagh, Bellmore, Merrick, Freeport, Baldwin, Rockville Centre | 1 | 46 | 32.5 | 31.6 | 30.0 | 28.7 |
| Freeport, skips Lynbrook | 1 | 24 | 17.6 | 16.7 | 15.5 | 15.2 |
| Wantagh, skips St. Albans | 1 | 33 | 24.7 | 23.7 | 22.5 | 22.3 |
| Wantagh, skips Lynbrook | 1 | 32 | 24.6 | 23.7 | 22.5 | 22.3 |

#### Long Beach - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Long Beach, skips Rosedale, Laurelton, Locust Manor | 8 | 33 | 23.0 | 20.0 | 18.9 | 18.8 |
| Long Beach, all stops | 2 | 37 | 26.3 | 23.3 | 22.8 | 22.8 |
| Island Park, all stops | 1 | 30 | 22.1 | 21.2 | 20.7 | 20.7 |
| Long Beach, skips Laurelton, Locust Manor | 1 | 36 | 24.1 | 21.0 | 20.3 | 20.2 |

#### Far Rockaway - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Far Rockaway, all stops | 10 | 36 | 24.9 | 22.7 | 22.5 | 22.4 |
| Far Rockaway, skips Rosedale, Laurelton, Locust Manor | 1 | 34 | 21.5 | 19.4 | 18.6 | 18.5 |
| Far Rockaway, skips Rosedale | 1 | 35 | 23.8 | 21.6 | 21.2 | 21.2 |
| Valley Stream, all stops | 1 | 16 | 10.4 | 10.0 | 9.7 | 9.7 |

#### West Hempstead - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| West Hempstead, all stops | 4 | 28 | 19.5 | 17.6 | 16.9 | 16.8 |

#### Huntington - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Huntington, skips Floral Park, Elmont-UBS Arena, Queens Village, Hollis | 6 | 48 | 34.8 | 31.6 | 31.2 | 30.3 |
| Huntington, skips Merillon Avenue, New Hyde Park, Floral Park, Elmont-UBS Arena, Queens Village, Hollis | 2 | 46 | 32.2 | 28.9 | 28.6 | 27.3 |
| Huntington, stops at Cold Spring Harbor, Syosset | 2 | 42 | 27.4 | 24.0 | 23.5 | 21.4 |
| Westbury, skips Floral Park | 2 | 25 | 20.1 | 19.2 | 19.1 | 19.1 |
| Hicksville, skips Elmont-UBS Arena, Queens Village, Hollis | 1 | 27 | 21.5 | 20.4 | 20.3 | 19.7 |
| Hicksville, skips Floral Park, Elmont-UBS Arena | 1 | 32 | 22.8 | 21.7 | 21.6 | 21.4 |
| Huntington, stops at Cold Spring Harbor, Syosset, Hicksville, Carle Place, Mineola | 1 | 43 | 30.9 | 27.7 | 27.3 | 25.9 |
| Huntington, stops at Cold Spring Harbor, Syosset, Hicksville | 1 | 39 | 28.2 | 25.0 | 24.6 | 22.5 |
| Huntington, skips Elmont-UBS Arena, Queens Village, Hollis | 1 | 48 | 36.2 | 32.9 | 32.6 | 31.8 |
| Huntington, skips Carle Place, Floral Park, Elmont-UBS Arena, Queens Village, Hollis | 1 | 44 | 33.5 | 30.3 | 29.9 | 28.9 |

#### Ronkonkoma - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park, Wyandanch, Farmingdale, Bethpage | 6 | 58 | 40.8 | 39.3 | 39.0 | 36.2 |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park, Wyandanch, Farmingdale, Bethpage, Hicksville | 3 | 60 | 41.6 | 40.3 | 40.0 | 37.3 |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park, Wyandanch, Farmingdale, Bethpage, Hicksville, Mineola | 2 | 59 | 42.9 | 41.6 | 41.4 | 39.0 |
| Farmingdale, skips Floral Park, Elmont-UBS Arena, Queens Village, Hollis | 1 | 38 | 27.6 | 26.3 | 26.0 | 25.2 |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park | 1 | 55 | 36.7 | 35.2 | 34.8 | 31.2 |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park, Wyandanch, Farmingdale, Bethpage, Floral Park | 1 | 61 | 42.1 | 40.7 | 40.3 | 37.9 |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park, Wyandanch, Farmingdale, Hicksville, Merillon Avenue, New Hyde Park | 1 | 61 | 42.9 | 41.6 | 41.3 | 38.9 |
| Ronkonkoma, stops at Central Islip, Brentwood, Deer Park, Wyandanch, Hicksville, Mineola | 1 | 61 | 40.2 | 38.9 | 38.6 | 35.8 |

#### Croton-Harmon - GCT

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Croton-Harmon, all stops | 6 | 71 | 56.9 | 51.4 | 50.2 | 49.9 |
| Croton-Harmon, skips Greystone, Glenwood, Ludlow, Riverdale, Spuyten Duyvil, University Heights, Morris Heights | 4 | 60 | 49.3 | 43.6 | 41.9 | 41.5 |
| Croton-Harmon, stops at Ossining, Scarborough, Philipse Manor, Tarrytown, Harlem-125 St | 3 | 55 | 42.1 | 36.3 | 34.5 | 33.6 |
| Greystone, all stops | 3 | 45 | 33.2 | 27.7 | 26.8 | 26.6 |
| Croton-Harmon, stops at Ossining, Scarborough, Philipse Manor, Tarrytown | 1 | 60 | 41.2 | 35.2 | 33.4 | 32.4 |
| Croton-Harmon, skips Greystone, Glenwood, Yonkers, Ludlow, Riverdale, Spuyten Duyvil, Marble Hill, University Heights, Morris Heights | 1 | 62 | 47.3 | 41.5 | 39.7 | 39.2 |
| Croton-Harmon, skips Greystone, Glenwood, Ludlow, Riverdale, Spuyten Duyvil, Marble Hill, University Heights, Morris Heights | 1 | 60 | 48.4 | 42.6 | 41.0 | 40.5 |
| Irvington, stops at Ardsley-on-Hudson, Dobbs Ferry, Hastings-on-Hudson, Greystone, Harlem-125 St | 1 | 46 | 33.6 | 27.9 | 26.5 | 26.1 |
| Irvington, stops at Ardsley-on-Hudson, Dobbs Ferry, Hastings-on-Hudson, Yonkers, Harlem-125 St | 1 | 49 | 33.4 | 27.8 | 26.3 | 25.9 |
| Tarrytown, stops at Irvington, Ardsley-on-Hudson, Dobbs Ferry, Hastings-on-Hudson, Greystone, Harlem-125 St | 1 | 51 | 36.9 | 31.2 | 29.7 | 29.3 |

#### Southeast - GCT

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| North White Plains, all stops | 6 | 56 | 46.2 | 41.2 | 40.1 | 39.9 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, Katonah, Bedford Hills, Mt Kisco, Chappaqua, Pleasantville, Hawthorne, Valhalla, North White Plains, White Plains, Harlem-125 St | 5 | 89 | 74.5 | 67.9 | 62.7 | 61.7 |
| Crestwood, stops at Tuckahoe, Bronxville, Fleetwood, Mt Vernon West, Harlem-125 St | 4 | 38 | 26.9 | 22.3 | 20.8 | 20.3 |
| North White Plains, stops at White Plains, Hartsdale, Scarsdale, Crestwood, Harlem-125 St | 3 | 46 | 34.2 | 29.2 | 26.8 | 26.3 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, White Plains, Harlem-125 St | 3 | 90 | 66.6 | 59.3 | 53.2 | 51.8 |
| Mt Kisco, stops at Chappaqua, Pleasantville, Hawthorne, Valhalla, North White Plains, White Plains, Harlem-125 St | 2 | 64 | 49.6 | 43.8 | 39.7 | 38.7 |
| North White Plains, stops at White Plains, Hartsdale, Scarsdale, Harlem-125 St | 2 | 42 | 33.1 | 28.1 | 25.5 | 24.8 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, Katonah, Bedford Hills, Mt Kisco, Chappaqua, White Plains, Harlem-125 St | 2 | 88 | 70.8 | 63.6 | 58.3 | 57.3 |
| Crestwood, stops at Tuckahoe, Bronxville, Fleetwood | 1 | 40 | 25.0 | 20.2 | 18.4 | 17.7 |
| Crestwood, stops at Tuckahoe, Bronxville, Fleetwood, Mt Vernon West | 1 | 35 | 26.1 | 21.3 | 19.7 | 19.2 |
| Crestwood, all stops | 1 | 43 | 34.7 | 30.1 | 29.3 | 29.0 |
| Crestwood, skips Botanical Garden, Fordham, Tremont, Melrose | 1 | 37 | 30.2 | 25.7 | 24.5 | 24.2 |
| Hartsdale, stops at Scarsdale | 1 | 38 | 26.6 | 21.8 | 19.2 | 18.5 |
| Hartsdale, stops at Scarsdale, Harlem-125 St | 1 | 39 | 27.4 | 22.8 | 20.3 | 19.6 |
| Mt Kisco, stops at Chappaqua, Pleasantville, Hawthorne, Valhalla, North White Plains, White Plains, Hartsdale, Scarsdale, Harlem-125 St | 1 | 68 | 51.8 | 46.0 | 42.4 | 41.5 |
| Mt Kisco, stops at Chappaqua, Pleasantville, Hawthorne, Valhalla, North White Plains, White Plains, Mt Vernon West, Fordham, Harlem-125 St | 1 | 67 | 51.7 | 45.9 | 42.3 | 41.4 |
| Mt Vernon West, all stops | 1 | 37 | 26.7 | 22.1 | 21.4 | 21.1 |
| North White Plains, stops at White Plains | 1 | 45 | 30.1 | 24.9 | 21.7 | 20.8 |
| North White Plains, stops at White Plains, Harlem-125 St | 1 | 45 | 30.9 | 25.9 | 22.8 | 22.0 |
| North White Plains, stops at White Plains, Hartsdale, Scarsdale, Crestwood | 1 | 43 | 33.3 | 28.2 | 25.7 | 25.1 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, Katonah, Bedford Hills, Mt Kisco, Chappaqua, North White Plains, Harlem-125 St | 1 | 90 | 70.9 | 63.6 | 58.3 | 57.3 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, Katonah, Bedford Hills, Mt Kisco, Chappaqua, North White Plains, White Plains, Harlem-125 St | 1 | 85 | 71.7 | 64.7 | 59.5 | 58.4 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, Katonah, Bedford Hills, Mt Kisco, Chappaqua, Pleasantville, Hawthorne, Valhalla, White Plains, Harlem-125 St | 1 | 87 | 73.6 | 66.8 | 61.6 | 60.6 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, North White Plains, White Plains, Harlem-125 St | 1 | 86 | 67.5 | 60.3 | 54.3 | 53.0 |
| Southeast, stops at Brewster, Croton Falls, Purdy's, Goldens Bridge, North White Plains, White Plains, Hartsdale, Scarsdale, Harlem-125 St | 1 | 89 | 69.7 | 62.5 | 57.0 | 55.8 |

#### New Haven - GCT

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stamford, all stops | 6 | 68 | 52.7 | 46.9 | 45.1 | 44.8 |
| New Haven, stops at Bridgeport, Stamford | 3 | 90 | 76.0 | 67.6 | 61.6 | 59.3 |
| New Rochelle, skips Fordham | 3 | 37 | 25.4 | 20.1 | 18.5 | 18.2 |
| Harrison, stops at Mamaroneck, Larchmont | 2 | 44 | 29.9 | 24.0 | 21.8 | 21.4 |
| Harrison, stops at Mamaroneck, Larchmont, Harlem-125 St | 2 | 44 | 30.7 | 25.0 | 23.0 | 22.6 |
| New Haven, skips Rowayton, Darien, Noroton Heights, Port Chester, Rye, Harrison, Mamaroneck, Larchmont, New Rochelle, Pelham, Mt Vernon East, Fordham | 2 | 128 | 92.6 | 84.8 | 80.2 | 78.7 |
| South Norwalk, stops at Rowayton, Darien, Noroton Heights, Stamford, Greenwich, Harlem-125 St | 2 | 72 | 51.7 | 45.1 | 41.9 | 41.1 |
| Stamford, skips Harrison, Mamaroneck, Larchmont, New Rochelle, Pelham, Mt Vernon East, Fordham | 2 | 64 | 44.9 | 38.8 | 36.3 | 35.6 |
| Bridgeport, stops at Fairfield-Black Rock, Fairfield, Southport, Green's Farms, Westport, East Norwalk | 1 | 93 | 65.8 | 58.2 | 53.9 | 52.9 |
| Bridgeport, stops at Fairfield-Black Rock, Fairfield, Southport, Green's Farms, Westport, East Norwalk, South Norwalk, Rowayton, Darien, Noroton Heights, Stamford, Harlem-125 St | 1 | 94 | 72.0 | 64.8 | 61.1 | 60.2 |
| Bridgeport, stops at Fairfield-Black Rock, Fairfield, Southport, Green's Farms, Westport, East Norwalk, South Norwalk, Stamford, Harlem-125 St | 1 | 95 | 68.5 | 61.3 | 57.3 | 56.3 |
| Fairfield-Black Rock, stops at Fairfield, Southport, Green's Farms, Westport, East Norwalk, South Norwalk, Stamford, Harlem-125 St | 1 | 83 | 63.8 | 57.0 | 53.2 | 52.3 |
| Greenwich, stops at Port Chester, Rye, Harlem-125 St | 1 | 52 | 36.1 | 30.1 | 27.6 | 26.9 |
| Harrison, all stops | 1 | 47 | 34.7 | 29.3 | 27.8 | 27.6 |
| Harrison, skips Fordham, Harlem-125 St | 1 | 45 | 32.8 | 27.2 | 25.5 | 25.1 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Fairfield-Black Rock, Fairfield | 1 | 110 | 81.0 | 72.5 | 66.7 | 64.7 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Fairfield-Black Rock, Fairfield, Harlem-125 St | 1 | 111 | 81.9 | 73.6 | 67.9 | 65.9 |
| New Haven, skips Rowayton, Noroton Heights, Old Greenwich, Riverside, Cos Cob, Port Chester, Rye, Harrison, Mamaroneck, Larchmont, New Rochelle, Pelham, Mt Vernon East, Fordham | 1 | 119 | 90.5 | 82.6 | 77.8 | 76.3 |
| New Haven, skips Old Greenwich, Riverside, Cos Cob, Greenwich, Port Chester, Rye, Harrison, Mamaroneck, Larchmont, New Rochelle, Pelham, Mt Vernon East, Fordham | 1 | 122 | 91.8 | 83.9 | 79.1 | 77.5 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Fairfield-Black Rock, Fairfield, Southport, Green's Farms, Westport, East Norwalk, South Norwalk, Stamford, Harlem-125 St | 1 | 116 | 88.3 | 80.3 | 75.3 | 73.6 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Fairfield-Black Rock, Fairfield, Stamford, Harlem-125 St | 1 | 116 | 82.8 | 74.6 | 69.1 | 67.1 |
| New Haven, skips Southport, Green's Farms, Rowayton, Noroton Heights, Harrison, Mamaroneck, Larchmont, Pelham, Mt Vernon East, Fordham | 1 | 128 | 94.1 | 86.7 | 82.4 | 80.8 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Fairfield-Black Rock, Fairfield, Westport, South Norwalk, Darien, Noroton Heights, Stamford, Harlem-125 St | 1 | 115 | 87.0 | 79.0 | 74.0 | 72.2 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Fairfield-Black Rock, Fairfield, Westport, Stamford, Harlem-125 St | 1 | 110 | 83.7 | 75.7 | 70.4 | 68.5 |
| New Haven, stops at West Haven, Milford, Stratford, Bridgeport, Stamford, Harlem-125 St | 1 | 110 | 80.3 | 72.1 | 66.5 | 64.4 |
| New Rochelle, skips Fordham, Harlem-125 St | 1 | 37 | 24.5 | 19.0 | 17.4 | 17.1 |
| South Norwalk, stops at Rowayton, Darien, Noroton Heights, Harlem-125 St | 1 | 71 | 49.7 | 43.0 | 39.4 | 38.6 |
| South Norwalk, stops at Rowayton, Darien, Noroton Heights, Stamford | 1 | 72 | 49.8 | 43.0 | 39.5 | 38.6 |
| Stamford, stops at Greenwich, Port Chester, Rye, Harrison, Fordham, Harlem-125 St | 1 | 63 | 44.0 | 37.7 | 35.2 | 34.4 |
| Stamford, skips Old Greenwich, Riverside, Cos Cob, New Rochelle, Pelham, Mt Vernon East, Fordham | 1 | 59 | 45.5 | 39.3 | 36.5 | 36.1 |
| Stamford, stops at Old Greenwich, Riverside, Cos Cob, Greenwich, Port Chester, Rye | 1 | 59 | 44.1 | 37.8 | 35.2 | 34.4 |

#### New Canaan - Stamford

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| New Canaan, all stops | 5 | 18 | 13.8 | 11.6 | 11.3 | 11.3 |

### Trains

One train alone, minutes.

#### Port Washington local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 35.0 | 33.3 | 31.9 | 31.7 |
| M7, 750 V third rail, full power | 34.6 | 32.9 | 31.4 | 31.2 |
| M8, 25 kV | 34.8 | 33.1 | 31.6 | 31.4 |

#### Port Washington express

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 25.5 | 23.7 | 21.1 | 20.8 |
| M7, 750 V third rail, full power | 25.4 | 23.6 | 20.9 | 20.4 |
| M8, 25 kV | 25.5 | 23.6 | 21.0 | 20.6 |

#### Main Line to Penn local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 17.0 | 14.4 | 13.4 | 13.2 |
| M7, 750 V third rail, full power | 16.9 | 14.3 | 13.2 | 12.9 |
| M8, 25 kV | 16.9 | 14.4 | 13.3 | 13.0 |

#### Main Line to Penn express

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 13.4 | 10.8 | 9.6 | 9.1 |
| M7, 750 V third rail, full power | 13.3 | 10.7 | 9.5 | 8.9 |
| M8, 25 kV | 13.4 | 10.7 | 9.5 | 9.0 |

#### Main Line to GCM local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 16.5 | 14.0 | 13.5 | 13.4 |
| M7, 750 V third rail, full power | 16.4 | 13.9 | 13.4 | 13.1 |
| M8, 25 kV | 16.4 | 13.9 | 13.4 | 13.2 |

#### Main Line to GCM express

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 12.9 | 10.4 | 9.7 | 9.2 |
| M7, 750 V third rail, full power | 12.9 | 10.3 | 9.6 | 9.1 |
| M8, 25 kV | 12.9 | 10.3 | 9.6 | 9.2 |

#### Atlantic local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 13.9 | 11.6 | 10.8 | 10.4 |
| M7, 750 V third rail, full power | 13.9 | 11.4 | 10.5 | 10.0 |
| M8, 25 kV | 13.9 | 11.5 | 10.6 | 10.1 |

#### Hempstead local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 22.4 | 20.2 | 20.2 | 20.2 |
| M7, 750 V third rail, full power | 22.1 | 19.9 | 19.9 | 19.8 |
| M8, 25 kV | 22.2 | 20.0 | 20.0 | 20.0 |

#### Babylon via Atlantic Branch local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 40.6 | 40.0 | 38.7 | 38.5 |
| M7, 750 V third rail, full power | 39.6 | 39.0 | 37.7 | 37.5 |
| M8, 25 kV | 40.0 | 39.3 | 38.1 | 37.9 |

#### Babylon via Babylon Branch local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 42.6 | 41.8 | 40.6 | 40.4 |
| M7, 750 V third rail, full power | 41.7 | 40.8 | 39.6 | 39.2 |
| M8, 25 kV | 42.0 | 41.2 | 40.0 | 39.7 |

#### Long Beach local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 26.3 | 23.3 | 22.8 | 22.8 |
| M7, 750 V third rail, full power | 26.1 | 23.0 | 22.4 | 22.3 |
| M8, 25 kV | 26.2 | 23.1 | 22.6 | 22.5 |

#### Far Rockaway local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 24.9 | 22.7 | 22.5 | 22.4 |
| M7, 750 V third rail, full power | 24.6 | 22.3 | 22.0 | 22.0 |
| M8, 25 kV | 24.7 | 22.4 | 22.2 | 22.2 |

#### West Hempstead local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 19.5 | 17.6 | 16.9 | 16.8 |
| M7, 750 V third rail, full power | 19.2 | 17.3 | 16.5 | 16.4 |
| M8, 25 kV | 19.3 | 17.4 | 16.6 | 16.6 |

#### Huntington local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 40.0 | 36.8 | 36.4 | 36.1 |
| M7, 750 V third rail, full power | 39.4 | 36.2 | 35.7 | 35.3 |
| M8, 25 kV | 39.7 | 36.5 | 36.0 | 35.7 |

#### Ronkonkoma local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 54.7 | 53.5 | 53.2 | 52.5 |
| M7, 750 V third rail, full power | 53.6 | 52.4 | 52.0 | 50.8 |
| M8, 25 kV | 54.1 | 52.8 | 52.5 | 51.5 |

#### Hudson local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7A, 700 V third rail | 56.9 | 51.4 | 50.2 | 49.9 |
| M7A, 700 V third rail, full power | 56.3 | 50.7 | 49.4 | 48.9 |
| M8, 12.5 kV | 56.6 | 51.0 | 49.8 | 49.4 |

#### Harlem local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M7A, 700 V third rail | 90.9 | 84.3 | 81.3 | 80.8 |
| M7A, 700 V third rail, full power | 90.0 | 83.2 | 79.4 | 78.7 |
| M8, 12.5 kV | 90.3 | 83.5 | 80.0 | 79.4 |

#### New Haven local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M8, 700 V third rail and 12.5 kV | 106.0 | 98.6 | 95.1 | 94.1 |
| M8, 12.5 kV | 105.9 | 98.4 | 94.8 | 93.7 |

#### New Canaan local

| Train | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: |
| M8, 700 V third rail and 12.5 kV | 13.8 | 11.6 | 11.3 | 11.3 |
| M8, 12.5 kV | 13.8 | 11.6 | 11.3 | 11.3 |

### Busy service

Minutes per inbound trip in steady service, from the time-stepped multi-train simulation. "Busy" is with the other trains on the line; "+ regen" adds regenerative braking.

#### PW local: 5 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PW local | posted | 35.1 | 35.2 | 35.1 | 35.0 | 521 |
|  | 60 mph | 33.5 | 33.6 | 33.5 | 33.4 | 486 |
|  | 80 mph | 32.1 | 32.2 | 32.2 | 32.0 | 502 |
|  | 100 mph | 32.0 | 32.1 | 32.1 | 31.8 | 495 |

#### PW express: 5 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PW express | posted | 25.6 | 25.6 | 25.6 | 25.6 | 541 |
|  | 60 mph | 23.8 | 23.8 | 23.8 | 23.8 | 476 |
|  | 80 mph | 21.2 | 21.3 | 21.2 | 21.1 | 479 |
|  | 100 mph | 20.9 | 20.9 | 20.9 | 20.7 | 500 |

#### Main Line to Penn: locals and expresses each at 2.5 min headways each way (1.25 min combined)

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Penn local | posted | 17.1 | 17.2 | 17.2 | 17.0 | 487 |
|  | 60 mph | 14.5 | 14.6 | 14.6 | 14.4 | 518 |
|  | 80 mph | 13.4 | 13.6 | 13.5 | 13.3 | 478 |
|  | 100 mph | 13.2 | 13.5 | 13.4 | 13.1 | 483 |
| Penn express | posted | 13.5 | 13.5 | 13.5 | 13.4 | 487 |
|  | 60 mph | 10.8 | 10.8 | 10.8 | 10.8 | 518 |
|  | 80 mph | 9.5 | 9.5 | 9.5 | 9.5 | 478 |
|  | 100 mph | 9.0 | 9.1 | 9.1 | 9.0 | 483 |

#### Main Line to GCM: 2.5 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GCM express | posted | 13.0 | 13.0 | 13.0 | 13.0 | 580 |
|  | 60 mph | 10.4 | 10.4 | 10.4 | 10.3 | 532 |
|  | 80 mph | 9.7 | 9.7 | 9.7 | 9.7 | 529 |
|  | 100 mph | 9.3 | 9.3 | 9.3 | 9.2 | 523 |

#### Atlantic: 5 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Atlantic local | posted | 13.9 | 13.9 | 13.9 | 13.9 | 556 |
|  | 60 mph | 11.5 | 11.5 | 11.5 | 11.5 | 557 |
|  | 80 mph | 10.7 | 10.7 | 10.7 | 10.6 | 512 |
|  | 100 mph | 10.2 | 10.3 | 10.3 | 10.1 | 494 |

#### Hempstead: 20 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hempstead local | posted | 22.6 | 22.6 | 22.6 | 22.4 | 477 |
|  | 60 mph | 20.4 | 20.5 | 20.4 | 20.3 | 483 |
|  | 80 mph | 20.4 | 20.5 | 20.4 | 20.3 | 484 |
|  | 100 mph | 20.4 | 20.4 | 20.4 | 20.3 | 485 |

#### Babylon via Atlantic Branch: 7.5 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Babylon via Atlantic Branch local | posted | 40.6 | 40.7 | 40.6 | 40.2 | 497 |
|  | 60 mph | 40.0 | 40.1 | 40.1 | 39.6 | 504 |
|  | 80 mph | 38.9 | 39.0 | 39.0 | 38.4 | 514 |
|  | 100 mph | 38.7 | 38.9 | 38.8 | 38.2 | 520 |

#### Babylon via Babylon Branch: 7.5 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Babylon via Babylon Branch local | posted | 42.7 | 42.8 | 42.8 | 42.3 | 499 |
|  | 60 mph | 41.9 | 42.1 | 42.0 | 41.5 | 499 |
|  | 80 mph | 40.8 | 40.9 | 40.9 | 40.3 | 489 |
|  | 100 mph | 40.6 | 40.8 | 40.7 | 40.1 | 493 |

#### Long Beach: 12 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Long Beach local | posted | 26.5 | 26.6 | 26.6 | 26.4 | 523 |
|  | 60 mph | 23.6 | 23.6 | 23.6 | 23.4 | 531 |
|  | 80 mph | 23.0 | 23.1 | 23.0 | 22.8 | 527 |
|  | 100 mph | 23.0 | 23.1 | 23.0 | 22.8 | 526 |

#### Far Rockaway: 15 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Far Rockaway local | posted | 25.1 | 25.1 | 25.1 | 25.0 | 497 |
|  | 60 mph | 22.9 | 23.0 | 23.0 | 22.8 | 495 |
|  | 80 mph | 22.7 | 22.8 | 22.8 | 22.5 | 494 |
|  | 100 mph | 22.7 | 22.8 | 22.8 | 22.5 | 494 |

#### West Hempstead: 60 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| West Hempstead local | posted | 19.6 | 19.6 | 19.6 | 19.4 | 528 |
|  | 60 mph | 17.7 | 17.7 | 17.7 | 17.6 | 528 |
|  | 80 mph | 17.0 | 17.0 | 17.0 | 16.8 | 528 |
|  | 100 mph | 16.9 | 16.9 | 16.9 | 16.7 | 528 |

#### Huntington: 10 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Huntington local | posted | 40.1 | 40.1 | 40.1 | 39.9 | 531 |
|  | 60 mph | 36.9 | 36.9 | 37.0 | 36.7 | 542 |
|  | 80 mph | 36.5 | 36.6 | 36.6 | 36.3 | 543 |
|  | 100 mph | 36.1 | 36.2 | 36.1 | 35.8 | 534 |

#### Ronkonkoma: 10 min headways each way

| Service | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ronkonkoma local | posted | 55.0 | 55.1 | 55.1 | 54.5 | 505 |
|  | 60 mph | 53.7 | 53.8 | 53.7 | 53.2 | 497 |
|  | 80 mph | 53.4 | 53.4 | 53.4 | 52.9 | 512 |
|  | 100 mph | 52.6 | 52.7 | 52.6 | 51.9 | 520 |

#### Hudson: 8.57 min headways each way

| Service | Speeds | M7A, 1 train | M7A, busy | M7A, busy + regen | M8 12.5 kV | Lowest V (M7A) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hudson local | posted | 57.1 | 57.2 | 57.1 | 56.9 | 526 |
|  | 60 mph | 51.6 | 51.6 | 51.6 | 51.4 | 501 |
|  | 80 mph | 50.4 | 50.5 | 50.4 | 50.1 | 521 |
|  | 100 mph | 50.1 | 50.2 | 50.2 | 49.8 | 529 |

#### Harlem: 3.75 min headways each way

| Service | Speeds | M7A, 1 train | M7A, busy | M7A, busy + regen | M8 12.5 kV | Lowest V (M7A) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Harlem local | posted | 91.3 | 91.7 | 91.6 | 91.0 | 456 |
|  | 60 mph | 84.7 | 85.0 | 84.9 | 84.3 | 458 |
|  | 80 mph | 81.5 | 82.3 | 82.0 | 80.8 | 449 |
|  | 100 mph | 81.0 | 81.9 | 81.6 | 80.2 | 446 |

#### New Haven: 4 min headways each way

| Service | Speeds | M8, 1 train | M8, busy | M8, busy + regen | M8 12.5 kV | Lowest V (M8) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| New Haven local | posted | 106.7 | 106.7 | 106.7 | 106.6 | 504 |
|  | 60 mph | 99.3 | 99.4 | 99.4 | 99.2 | 500 |
|  | 80 mph | 95.8 | 95.8 | 95.8 | 95.6 | 517 |
|  | 100 mph | 94.7 | 94.8 | 94.8 | 94.4 | 500 |

#### New Canaan: 30 min headways each way

| Service | Speeds | M8, 1 train | M8, busy | M8, busy + regen | M8 12.5 kV | Lowest V (M8) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| New Canaan local | posted | 13.9 | 13.9 | 13.9 | 13.9 |  |
|  | 60 mph | 11.7 | 11.7 | 11.7 | 11.7 |  |
|  | 80 mph | 11.4 | 11.4 | 11.4 | 11.4 |  |
|  | 100 mph | 11.4 | 11.4 | 11.4 | 11.4 |  |

### Posted slow zones

One train, the timetable's, raising one posted zone at a time to what the curves allow (80 mph cap).

#### Port Washington (base: local 35.0 min, express 25.5 min)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 2.67 | 4.38 | Woodside | 50 mph | 80 mph | 41 s | 41 s |
| 9.64 | 13.45 | Auburndale | 60 mph | 80 mph | 1 s | 41 s |
| 0.00 | 0.25 | Penn Station | 15 mph | 73 mph | 39 s | 39 s |
| 6.08 | 9.55 | Mets-Willets Point | 60 mph | 80 mph | 24 s | 36 s |
| 0.26 | 2.67 | Penn Station | 60 mph | 80 mph | 19 s | 19 s |
| 15.89 | 18.38 | Manhasset | 50 mph | 80 mph | 19 s | 19 s |
| 13.46 | 13.81 | Douglaston | 40 mph | 77 mph | 9 s | 14 s |
| 13.81 | 15.89 | Little Neck | 60 mph | 80 mph | 1 s | 9 s |
| 18.39 | 19.40 | Port Washington | 40 mph | 65 mph | 8 s | 8 s |
| 5.84 | 6.07 | Woodside | 40 mph | 49 mph | 7 s | 7 s |

#### Main Line to Penn (base: local 17.0 min, express 13.4 min)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 10.49 | 10.88 | Jamaica | 20 mph | 80 mph | 55 s | 60 s |
| 0.00 | 0.30 | Penn Station | 15 mph | 80 mph | 48 s | 48 s |
| 2.55 | 3.98 | Woodside | 50 mph | 80 mph | 32 s | 32 s |
| 10.98 | 11.27 | Jamaica | 20 mph | 80 mph | 20 s | 20 s |
| 0.30 | 2.55 | Penn Station | 60 mph | 80 mph | 18 s | 18 s |
| 4.45 | 5.98 | Woodside | 60 mph | 80 mph | 6 s | 17 s |
| 3.99 | 4.45 | Woodside | 50 mph | 80 mph | 6 s | 6 s |

#### Main Line to GCM (base: local 16.5 min, express 12.9 min)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 9.77 | 10.22 | Jamaica | 20 mph | 80 mph | 60 s | 65 s |
| 0.00 | 0.22 | Grand Central | 15 mph | 73 mph | 28 s | 28 s |
| 10.27 | 10.56 | Jamaica | 20 mph | 80 mph | 19 s | 19 s |
| 3.76 | 5.27 | Woodside | 60 mph | 80 mph | 6 s | 16 s |
| 2.59 | 3.38 | Woodside | 45 mph | 80 mph | 12 s | 12 s |
| 1.09 | 2.59 | Grand Central | 60 mph | 80 mph | 10 s | 10 s |
| 0.46 | 1.09 | Grand Central | 45 mph | 80 mph | 9 s | 9 s |
| 0.22 | 0.45 | Grand Central | 30 mph | 46 mph | 7 s | 7 s |
| 3.38 | 3.76 | Woodside | 50 mph | 80 mph | 4 s | 4 s |

#### Atlantic (base: local 13.9 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1.41 | 3.98 | East New York | 45 mph | 80 mph | 55 s |
| 8.77 | 9.19 | Jamaica | 20 mph | 80 mph | 37 s |
| 0.00 | 0.07 | Atlantic Terminal | 5 mph | 15 mph | 31 s |
| 4.03 | 8.27 | East New York | 70 mph | 80 mph | 20 s |
| 0.09 | 1.25 | Atlantic Terminal | 45 mph | 80 mph | 16 s |
| 8.27 | 8.77 | Jamaica | 45 mph | 80 mph | 11 s |
| 1.25 | 1.40 | Nostrand Avenue | 30 mph | 53 mph | 7 s |

#### Hempstead (base: local 22.4 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 9.37 | 9.60 | Country Life Press | 15 mph | 38 mph | 41 s |
| 10.17 | 10.33 | Hempstead | 10 mph | 80 mph | 25 s |
| 0.23 | 0.69 | Jamaica | 35 mph | 80 mph | 22 s |
| 0.00 | 0.22 | Jamaica | 20 mph | 80 mph | 17 s |
| 9.61 | 10.17 | Country Life Press | 30 mph | 62 mph | 8 s |
| 5.70 | 5.75 | Floral Park | 25 mph | 45 mph | 7 s |

#### Babylon via Atlantic Branch (base: local 40.6 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 3.84 | 6.20 | Lynbrook | 60 mph | 80 mph | 30 s |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 13 s |
| 25.68 | 26.73 | Babylon | 60 mph | 80 mph | 11 s |
| 0.37 | 0.60 | Jamaica | 35 mph | 62 mph | 9 s |
| 6.20 | 6.46 | Lynbrook | 45 mph | 80 mph | 7 s |
| 6.61 | 8.25 | Lynbrook | 60 mph | 80 mph | 7 s |
| 3.04 | 3.11 | Jamaica | 60 mph | 80 mph | 5 s |
| 0.98 | 1.28 | Jamaica | 60 mph | 77 mph | 4 s |
| 0.25 | 0.37 | Jamaica | 30 mph | 39 mph | 3 s |

#### Babylon via Babylon Branch (base: local 42.6 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 6.36 | 8.93 | Lynbrook | 60 mph | 80 mph | 27 s |
| 0.19 | 0.64 | Jamaica | 35 mph | 80 mph | 14 s |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 13 s |
| 26.35 | 27.41 | Babylon | 60 mph | 80 mph | 11 s |
| 0.65 | 1.69 | Jamaica | 50 mph | 80 mph | 11 s |
| 3.15 | 3.68 | St. Albans | 50 mph | 80 mph | 10 s |
| 3.68 | 5.17 | St. Albans | 60 mph | 80 mph | 7 s |
| 5.32 | 6.35 | Lynbrook | 70 mph | 80 mph | 3 s |

#### Long Beach (base: local 26.3 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 12.92 | 13.15 | Long Beach | 5 mph | 55 mph | 108 s |
| 11.41 | 11.74 | Island Park | 40 mph | 61 mph | 16 s |
| 12.58 | 12.92 | Long Beach | 30 mph | 80 mph | 14 s |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 13 s |
| 3.84 | 6.20 | Rosedale | 60 mph | 80 mph | 9 s |
| 0.37 | 0.60 | Jamaica | 35 mph | 62 mph | 9 s |
| 9.69 | 11.41 | Oceanside | 60 mph | 80 mph | 7 s |
| 0.98 | 1.28 | Jamaica | 60 mph | 77 mph | 4 s |
| 6.93 | 8.08 | Lynbrook | 60 mph | 80 mph | 4 s |
| 8.09 | 8.89 | Centre Avenue | 45 mph | 80 mph | 4 s |
| 6.20 | 6.70 | Valley Stream | 45 mph | 80 mph | 4 s |
| 0.25 | 0.37 | Jamaica | 30 mph | 39 mph | 3 s |

#### Far Rockaway (base: local 24.9 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 6.41 | 6.61 | Valley Stream | 15 mph | 39 mph | 36 s |
| 8.11 | 11.09 | Cedarhurst | 40 mph | 80 mph | 26 s |
| 11.09 | 11.24 | Far Rockaway | 10 mph | 67 mph | 21 s |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 13 s |
| 6.61 | 7.89 | Gibson | 40 mph | 80 mph | 12 s |
| 3.84 | 6.20 | Rosedale | 60 mph | 80 mph | 9 s |
| 0.37 | 0.60 | Jamaica | 35 mph | 62 mph | 9 s |
| 7.89 | 8.10 | Hewlett | 30 mph | 36 mph | 5 s |
| 0.98 | 1.28 | Jamaica | 60 mph | 77 mph | 4 s |
| 0.25 | 0.37 | Jamaica | 30 mph | 39 mph | 3 s |

#### West Hempstead (base: local 19.5 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 7.41 | 7.59 | Westwood | 15 mph | 44 mph | 47 s |
| 0.00 | 0.23 | Jamaica | 20 mph | 80 mph | 17 s |
| 0.23 | 0.69 | Jamaica | 35 mph | 80 mph | 14 s |
| 0.80 | 1.73 | Jamaica | 50 mph | 80 mph | 12 s |
| 11.56 | 11.66 | West Hempstead | 10 mph | 80 mph | 10 s |
| 3.73 | 5.41 | St. Albans | 60 mph | 80 mph | 9 s |
| 3.47 | 3.73 | St. Albans | 50 mph | 80 mph | 6 s |
| 5.41 | 6.76 | Westwood | 70 mph | 80 mph | 5 s |
| 6.76 | 7.41 | Westwood | 60 mph | 80 mph | 4 s |
| 1.74 | 3.47 | St. Albans | 60 mph | 80 mph | 4 s |

#### Huntington (base: local 40.0 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 24.28 | 25.30 | Huntington | 30 mph | 80 mph | 59 s |
| 21.40 | 24.28 | Cold Spring Harbor | 45 mph | 80 mph | 47 s |
| 14.96 | 16.12 | Hicksville | 40 mph | 80 mph | 36 s |
| 0.00 | 0.32 | Jamaica | 20 mph | 80 mph | 26 s |
| 0.32 | 0.71 | Jamaica | 35 mph | 80 mph | 18 s |
| 19.41 | 19.79 | Syosset | 50 mph | 61 mph | 4 s |

#### Ronkonkoma (base: local 54.7 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0.00 | 0.32 | Jamaica | 20 mph | 80 mph | 26 s |
| 14.97 | 15.95 | Hicksville | 40 mph | 80 mph | 26 s |
| 0.32 | 0.71 | Jamaica | 35 mph | 80 mph | 18 s |
| 19.31 | 19.96 | Bethpage | 60 mph | 80 mph | 11 s |

#### Hudson (base: local 56.9 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0.00 | 0.88 | Grand Central | 10 mph | 80 mph | 249 s |
| 9.82 | 10.72 | Spuyten Duyvil | 30 mph | 80 mph | 36 s |
| 5.40 | 6.33 | Harlem-125 St | 45 mph | 80 mph | 11 s |
| 4.46 | 4.93 | Harlem-125 St | 35 mph | 52 mph | 11 s |
| 23.69 | 31.75 | Scarborough | 70 mph | 80 mph | 10 s |
| 6.33 | 9.16 | Morris Heights | 60 mph | 80 mph | 8 s |
| 2.69 | 3.95 | Harlem-125 St | 60 mph | 80 mph | 7 s |
| 31.75 | 32.04 | Croton-Harmon | 50 mph | 80 mph | 5 s |
| 2.63 | 2.69 | Harlem-125 St | 45 mph | 80 mph | 4 s |
| 0.89 | 2.13 | Grand Central | 60 mph | 80 mph | 4 s |
| 2.13 | 2.18 | Harlem-125 St | 45 mph | 80 mph | 4 s |
| 4.93 | 5.40 | Harlem-125 St | 40 mph | 56 mph | 3 s |

#### Harlem (base: local 90.9 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0.00 | 0.88 | Grand Central | 10 mph | 80 mph | 249 s |
| 38.97 | 45.45 | Goldens Bridge | 60 mph | 80 mph | 34 s |
| 0.89 | 3.94 | Harlem-125 St | 60 mph | 80 mph | 31 s |
| 51.51 | 52.76 | Brewster | 40 mph | 80 mph | 25 s |
| 25.14 | 25.99 | Valhalla | 40 mph | 80 mph | 22 s |
| 21.95 | 22.58 | White Plains | 35 mph | 80 mph | 17 s |
| 32.22 | 35.65 | Chappaqua | 70 mph | 80 mph | 15 s |
| 4.46 | 4.92 | Harlem-125 St | 35 mph | 54 mph | 12 s |
| 23.73 | 25.14 | Valhalla | 50 mph | 69 mph | 11 s |
| 48.16 | 50.68 | Croton Falls | 60 mph | 80 mph | 11 s |
| 50.68 | 51.51 | Brewster | 50 mph | 65 mph | 10 s |
| 36.68 | 38.79 | Bedford Hills | 60 mph | 80 mph | 10 s |

#### New Haven (base: local 106.0 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0.00 | 0.88 | Grand Central | 10 mph | 80 mph | 249 s |
| 54.48 | 55.16 | Bridgeport | 30 mph | 80 mph | 32 s |
| 15.87 | 16.55 | New Rochelle | 30 mph | 68 mph | 30 s |
| 33.02 | 34.30 | Stamford | 50 mph | 80 mph | 26 s |
| 11.39 | 15.69 | Mt Vernon East  | 60 mph | 80 mph | 21 s |
| 63.59 | 70.73 | West Haven | 75 mph | 80 mph | 13 s |
| 23.00 | 23.35 | Rye | 50 mph | 80 mph | 13 s |
| 4.46 | 4.92 | Harlem-125 St | 35 mph | 50 mph | 12 s |
| 71.53 | 71.83 | New Haven | 30 mph | 80 mph | 10 s |
| 55.17 | 56.22 | Bridgeport | 45 mph | 80 mph | 10 s |
| 16.69 | 17.11 | New Rochelle | 50 mph | 80 mph | 9 s |
| 4.93 | 5.27 | Harlem-125 St | 40 mph | 80 mph | 9 s |

#### New Canaan (base: local 13.8 min)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 2.47 | 7.49 | Talmadge Hill | 40 mph | 80 mph | 113 s |
| 0.23 | 1.73 | Stamford | 50 mph | 80 mph | 25 s |
| 2.20 | 2.32 | Glenbrook | 20 mph | 67 mph | 6 s |

### Limiting curves

One train, the timetable's, at an 80 mph cap, easing one curve-limited zone at a time to 80 mph.

#### Port Washington (base: local 31.9 min, express 21.1 min)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 17.31 | 19.49 | Port Washington | 15 mph | 22 s | 22 s |
| 5.53 | 6.21 | Woodside | 48 mph | 16 s | 21 s |
| 13.30 | 13.94 | Douglaston | 55 mph | 3 s | 15 s |
| 4.29 | 5.06 | Woodside | 57 mph | 9 s | 14 s |
| 9.41 | 9.81 | Flushing Main Street | 57 mph | 0 s | 9 s |
| 10.13 | 10.61 | Murray Hill | 65 mph | 0 s | 6 s |
| 8.87 | 9.23 | Mets-Willets Point | 69 mph | 0 s | 3 s |

#### Main Line to Penn (base: local 13.4 min, express 9.6 min)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 4.32 | 5.07 | Woodside | 65 mph | 4 s | 7 s |
| 10.57 | 11.17 | Jamaica | 57 mph | 4 s | 5 s |

#### Main Line to GCM (base: local 13.5 min, express 9.7 min)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 2.58 | 3.11 | Woodside | 53 mph | 19 s | 19 s |
| 0.00 | 1.08 | Grand Central | 44 mph | 17 s | 17 s |
| 9.86 | 10.45 | Jamaica | 47 mph | 8 s | 9 s |
| 3.54 | 4.22 | Woodside | 65 mph | 3 s | 6 s |
| 4.92 | 5.27 | Woodside | 70 mph | 0 s | 3 s |

#### Atlantic (base: local 10.8 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.00 | 0.31 | Atlantic Terminal | 15 mph | 13 s |
| 1.09 | 1.45 | Nostrand Avenue | 53 mph | 3 s |

#### Hempstead (base: local 20.2 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 9.27 | 10.23 | Garden City | 38 mph | 8 s |
| 10.24 | 10.33 | Hempstead | 15 mph | 6 s |
| 0.12 | 0.58 | Jamaica | 54 mph | 4 s |

#### Babylon via Atlantic Branch (base: local 38.7 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.02 | 0.72 | Jamaica | 39 mph | 11 s |

#### Babylon via Babylon Branch (base: local 40.6 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 1.09 | 1.81 | St. Albans | 58 mph | 13 s |
| 4.31 | 5.10 | St. Albans | 60 mph | 11 s |
| 0.08 | 0.53 | Jamaica | 55 mph | 3 s |

#### Long Beach (base: local 22.8 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.02 | 0.72 | Jamaica | 39 mph | 11 s |
| 11.31 | 11.87 | Island Park | 60 mph | 9 s |
| 12.81 | 13.15 | Long Beach | 15 mph | 7 s |
| 7.81 | 8.44 | Lynbrook | 47 mph | 4 s |

#### Far Rockaway (base: local 22.5 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.02 | 0.72 | Jamaica | 39 mph | 11 s |
| 7.74 | 8.22 | Hewlett | 36 mph | 11 s |
| 6.24 | 6.73 | Valley Stream | 39 mph | 7 s |
| 10.90 | 11.24 | Far Rockaway | 15 mph | 6 s |

#### West Hempstead (base: local 16.9 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 7.24 | 7.74 | Westwood | 44 mph | 21 s |
| 1.13 | 1.86 | St. Albans | 62 mph | 11 s |
| 4.35 | 5.10 | St. Albans | 60 mph | 11 s |
| 11.57 | 11.66 | West Hempstead | 15 mph | 6 s |
| 0.12 | 0.58 | Jamaica | 55 mph | 4 s |

#### Huntington (base: local 36.4 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 22.59 | 23.96 | Cold Spring Harbor | 48 mph | 18 s |
| 21.54 | 22.56 | Cold Spring Harbor | 56 mph | 10 s |
| 15.46 | 16.12 | Hicksville | 50 mph | 4 s |

#### Ronkonkoma (base: local 53.2 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 15.37 | 15.95 | Hicksville | 49 mph | 7 s |

#### Hudson (base: local 50.2 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 4.29 | 5.56 | Harlem-125 St | 42 mph | 38 s |
| 0.00 | 0.09 | Grand Central | 15 mph | 14 s |
| 5.89 | 6.37 | Harlem-125 St | 52 mph | 14 s |
| 7.93 | 10.64 | Marble Hill | 42 mph | 13 s |
| 7.21 | 7.59 | Morris Heights | 67 mph | 4 s |
| 26.92 | 27.33 | Philipse Manor | 70 mph | 4 s |

#### Harlem (base: local 81.3 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 4.29 | 5.09 | Harlem-125 St | 44 mph | 19 s |
| 0.00 | 0.09 | Grand Central | 15 mph | 14 s |
| 28.76 | 29.67 | Hawthorne | 60 mph | 10 s |
| 50.11 | 51.72 | Brewster | 61 mph | 10 s |
| 37.52 | 38.00 | Bedford Hills | 63 mph | 9 s |
| 48.87 | 49.44 | Croton Falls | 61 mph | 9 s |
| 23.62 | 25.63 | Valhalla | 57 mph | 7 s |
| 39.58 | 40.54 | Bedford Hills | 63 mph | 6 s |
| 43.38 | 44.60 | Goldens Bridge | 64 mph | 5 s |
| 46.07 | 46.97 | Purdy's | 60 mph | 4 s |

#### New Haven (base: local 95.1 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 54.38 | 55.10 | Bridgeport | 40 mph | 23 s |
| 4.28 | 5.09 | Harlem-125 St | 45 mph | 18 s |
| 0.00 | 0.09 | Grand Central | 15 mph | 14 s |
| 6.14 | 6.60 | Harlem-125 St | 60 mph | 11 s |
| 55.23 | 56.03 | Bridgeport | 49 mph | 10 s |
| 12.36 | 13.89 | Mt Vernon East  | 64 mph | 10 s |
| 9.58 | 10.01 | Fordham | 60 mph | 7 s |
| 34.50 | 35.49 | Noroton Heights | 70 mph | 6 s |
| 57.42 | 58.16 | Stratford | 70 mph | 4 s |
| 15.54 | 16.60 | New Rochelle | 61 mph | 4 s |

#### New Canaan (base: local 11.3 min)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 3.40 | 5.61 | Springdale | 48 mph | 21 s |
| 5.83 | 7.49 | New Canaan | 40 mph | 18 s |
| 0.97 | 1.54 | Stamford | 60 mph | 9 s |
| 7.52 | 7.61 | New Canaan | 15 mph | 6 s |

<!-- END results -->

## License

The code is under the [MIT License](LICENSE).
The traced track geometry and substations in `data/` are derived from OpenStreetMap,
© OpenStreetMap contributors, and are under the ODbL; see [`data/LICENSE`](data/LICENSE).
