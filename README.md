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
  - The M7A is an M7 on that third rail; the M8 is an M8 on 25 kV AC throughout, like the LIRR's,
    since these lines have no catenary yet to keep at 12.5 kV, unlike the New Haven Line.
  - Each line runs two patterns, each way, each on its own track:
    locals, and expresses that run local beyond where the locals turn,
    then stop only at Harlem-125 St, as nearly all do.
    On the Hudson, locals run all stops from Croton-Harmon, and expresses run nonstop from there,
    as only its diesel trains from Poughkeepsie do today, whose scheduled time they show, marked so.
    Harlem locals turn at North White Plains, and expresses stop there and at White Plains,
    but not at Mt Pleasant, which few trains serve.
    New Haven locals turn at Stamford, where expresses stop too,
    and stop in the Bronx at Mt Vernon East, Fordham and Harlem-125 St, as most do.
  - Busy service runs them as often as the busiest 60 minutes of AM arrivals into GCT,
    counting every electric trip along the line, not the clock hour the LIRR's lines count:
    on the Hudson, 6 locals and 3 expresses an hour,
    on the Harlem, 10 from North White Plains or nearer and 7 from beyond,
    and on the New Haven, 9 from Stamford or nearer and 9 from beyond.
    Each line is its own power network,
    though Harlem and New Haven trains share the third rail to Woodlawn, and all three share Park Avenue's.
  - The Hudson Line's busy service leaves out its trains from Poughkeepsie,
    nor the New Haven Line's from Danbury,
    whose dual-mode locomotives take the third rail only within Grand Central.
    Their replacements will take it throughout, and they wait to be modeled with the diesel trains.
  - On the New Haven Line, the M8 runs on the third rail to mile 14.5, and on 12.5 kV catenary beyond, at rated power.
    The two overlap from there to Pelham, mile 14.9, where trains change over:
    OSM counts neither there, so a gap between the two is taken as overlap,
    run on catenary, with the third rail and its substations reaching through it.
    A gap with the same supply either side, like a moveable bridge, takes that supply.
    The third rail's substations stop where it does.
    Its timetable trips start no farther out than New Haven's Union Station, where the trace ends,
    so not at New Haven-State St,
    but its busy service counts those, and New Canaan's through trains.
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

AM inbound trips arriving at Penn, GCM or Atlantic, or Jamaica from beyond it, or on Metro-North at GCT, or Stamford from New Canaan, 6-10 AM on 2026-10-27, grouped by stopping pattern: median scheduled time vs. one train running flat out with 30 s dwells: an M7 on the LIRR's 750 V third rail, an M7A on Metro-North's 700 V, or on the New Haven Line, an M8 on that third rail to Pelham and 12.5 kV catenary beyond.

#### Port Washington - Penn

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Great Neck, skips Mets | 2 | 39:00 | 26:12 | 24:55 | 23:28 | 23:13 |
| Port Washington to Great Neck local; Great Neck to Penn express | 2 | 38:30 | 25:32 | 23:42 | 21:09 | 20:46 |
| Great Neck, all stops | 1 | 38:00 | 27:16 | 25:59 | 24:42 | 24:30 |
| Port Washington to Great Neck local; Great Neck to Penn express, stops at Bayside | 1 | 40:00 | 26:36 | 24:46 | 22:26 | 22:09 |
| Port Washington, all stops | 1 | 49:00 | 34:57 | 33:17 | 31:55 | 31:44 |
| Port Washington, skips Auburndale, Broadway, Murray Hill, Flushing | 1 | 45:00 | 30:44 | 29:02 | 27:13 | 26:59 |
| Port Washington to Bayside local; Bayside to Penn express, stops at Woodside | 1 | 44:00 | 29:40 | 27:58 | 25:58 | 25:41 |

#### Jamaica - Penn

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jamaica, nonstop | 38 | 19:00 | 13:22 | 10:45 | 9:33 | 9:03 |
| Jamaica, stops at Woodside | 6 | 19:30 | 14:26 | 11:49 | 10:47 | 10:17 |
| Jamaica, stops at Forest Hills | 4 | 19:00 | 14:42 | 12:06 | 10:53 | 10:37 |
| Jamaica, stops at Kew Gardens | 4 | 19:00 | 14:38 | 12:04 | 10:53 | 10:31 |
| Jamaica, skips Woodside | 2 | 21:30 | 15:56 | 13:21 | 12:11 | 11:55 |
| Jamaica, all stops | 1 | 22:00 | 16:59 | 14:25 | 13:25 | 13:10 |

#### Jamaica - GCM

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jamaica, nonstop | 22 | 19:00 | 12:54 | 10:21 | 9:41 | 9:15 |
| Jamaica, stops at Woodside | 8 | 19:00 | 13:57 | 11:25 | 10:55 | 10:29 |
| Jamaica, stops at Forest Hills | 4 | 19:30 | 14:14 | 11:41 | 11:01 | 10:49 |
| Jamaica, stops at Kew Gardens | 4 | 19:00 | 14:09 | 11:39 | 11:01 | 10:43 |
| Jamaica, skips Woodside | 2 | 21:00 | 15:27 | 12:57 | 12:18 | 12:08 |

#### Jamaica - Atlantic

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jamaica, all stops | 26 | 20:00 | 13:56 | 11:34 | 10:45 | 10:23 |
| Jamaica, express | 1 | 19:00 | 12:07 | 9:24 | 8:20 | 7:50 |

#### Hempstead - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hempstead, all stops | 7 | 31:00 | 22:23 | 20:14 | 20:13 | 20:13 |
| Hempstead, express | 2 | 29:30 | 18:43 | 16:34 | 16:32 | 16:11 |

#### Babylon via Atlantic Branch - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Wantagh, skips Lynbrook | 4 | 29:30 | 22:32 | 21:54 | 20:36 | 20:25 |
| Babylon to Wantagh local; Wantagh to Jamaica express | 3 | 47:00 | 32:46 | 32:09 | 30:39 | 29:41 |
| Babylon, skips Lynbrook | 2 | 51:30 | 39:30 | 38:52 | 37:23 | 37:11 |
| Babylon, stops at Amityville, Massapequa, Bellmore, Freeport | 1 | 39:00 | 28:53 | 28:15 | 26:46 | 25:44 |
| Babylon, skips Bellmore, Merrick, Freeport, Lynbrook | 1 | 49:00 | 35:29 | 34:52 | 33:23 | 32:46 |
| Babylon to Merrick local; Merrick to Jamaica express | 1 | 49:00 | 35:27 | 34:49 | 33:20 | 32:41 |
| Babylon to Wantagh local; Wantagh to Jamaica express, stops at Lynbrook | 1 | 49:00 | 33:52 | 33:15 | 31:59 | 31:03 |
| Babylon, stops at Wantagh, Bellmore, Merrick, Freeport | 1 | 47:00 | 28:47 | 28:09 | 26:40 | 25:15 |
| Wantagh, all stops | 1 | 32:00 | 23:37 | 23:00 | 21:56 | 21:46 |

#### Babylon via Babylon Branch - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Babylon to Wantagh local; Wantagh to Jamaica express | 5 | 46:00 | 33:49 | 32:51 | 31:16 | 30:10 |
| Wantagh, skips Lynbrook, St. Albans | 2 | 30:30 | 23:35 | 22:37 | 21:13 | 20:53 |
| Babylon, all stops | 1 | 53:00 | 42:39 | 41:46 | 40:38 | 40:24 |
| Babylon to Wantagh express; Wantagh to Jamaica local, skips Lynbrook, St. Albans | 1 | 46:00 | 32:32 | 31:34 | 29:59 | 28:43 |
| Freeport, skips Lynbrook | 1 | 24:00 | 17:33 | 16:41 | 15:31 | 15:14 |
| Wantagh, skips St. Albans | 1 | 33:00 | 24:40 | 23:43 | 22:32 | 22:17 |
| Wantagh, skips Lynbrook | 1 | 32:00 | 24:35 | 23:42 | 22:32 | 22:15 |

#### Long Beach - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Long Beach to Valley Stream local; Valley Stream to Jamaica express | 8 | 33:00 | 23:01 | 19:58 | 18:56 | 18:48 |
| Long Beach, all stops | 2 | 37:00 | 26:20 | 23:17 | 22:47 | 22:46 |
| Island Park, all stops | 1 | 30:00 | 22:08 | 21:15 | 20:44 | 20:43 |
| Long Beach, skips Laurelton, Locust Manor | 1 | 36:00 | 24:05 | 21:01 | 20:15 | 20:10 |

#### Far Rockaway - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Far Rockaway, all stops | 10 | 36:00 | 24:52 | 22:42 | 22:28 | 22:27 |
| Far Rockaway to Valley Stream local; Valley Stream to Jamaica express | 1 | 34:00 | 21:32 | 19:23 | 18:37 | 18:29 |
| Far Rockaway, skips Rosedale | 1 | 35:00 | 23:48 | 21:39 | 21:12 | 21:10 |
| Valley Stream, all stops | 1 | 16:00 | 10:26 | 9:59 | 9:44 | 9:43 |

#### West Hempstead - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| West Hempstead, all stops | 4 | 28:00 | 19:29 | 17:37 | 16:53 | 16:50 |

#### Huntington - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Huntington to New Hyde Park local; New Hyde Park to Jamaica express | 6 | 47:30 | 34:47 | 31:34 | 31:12 | 30:16 |
| Huntington to Mineola local; Mineola to Jamaica express | 2 | 46:00 | 32:10 | 28:57 | 28:35 | 27:19 |
| Huntington, stops at Cold Spring Harbor, Syosset | 2 | 42:00 | 27:21 | 23:59 | 23:32 | 21:25 |
| Westbury, skips Floral Park | 2 | 25:00 | 20:04 | 19:10 | 19:07 | 19:04 |
| Hicksville to Floral Park local; Floral Park to Jamaica express | 1 | 27:00 | 21:30 | 20:25 | 20:20 | 19:44 |
| Hicksville, skips Floral Park, Elmont-UBS Arena | 1 | 32:00 | 22:48 | 21:43 | 21:37 | 21:24 |
| Huntington to Mineola local, skips Westbury; Mineola to Jamaica express | 1 | 43:00 | 30:53 | 27:40 | 27:18 | 25:54 |
| Huntington to Hicksville local; Hicksville to Jamaica express | 1 | 39:00 | 28:12 | 24:59 | 24:37 | 22:32 |
| Huntington to Floral Park local; Floral Park to Jamaica express | 1 | 48:00 | 36:09 | 32:56 | 32:34 | 31:51 |
| Huntington to New Hyde Park local, skips Carle Place; New Hyde Park to Jamaica express | 1 | 44:00 | 33:29 | 30:16 | 29:54 | 28:53 |

#### Ronkonkoma - Jamaica

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ronkonkoma to Bethpage local, skips Pinelawn; Bethpage to Jamaica express | 6 | 57:30 | 40:45 | 39:19 | 38:58 | 36:10 |
| Ronkonkoma to Hicksville local, skips Pinelawn; Hicksville to Jamaica express | 3 | 1:00:00 | 41:36 | 40:19 | 40:02 | 37:17 |
| Ronkonkoma to Hicksville local, skips Pinelawn; Hicksville to Jamaica express, stops at Mineola | 2 | 59:00 | 42:56 | 41:39 | 41:22 | 38:59 |
| Farmingdale to New Hyde Park local; New Hyde Park to Jamaica express | 1 | 38:00 | 27:34 | 26:17 | 26:00 | 25:10 |
| Ronkonkoma to Deer Park local; Deer Park to Jamaica express | 1 | 55:00 | 36:40 | 35:14 | 34:50 | 31:15 |
| Ronkonkoma to Bethpage local, skips Pinelawn; Bethpage to Jamaica express, stops at Floral Park | 1 | 1:01:00 | 42:08 | 40:42 | 40:21 | 37:56 |
| Ronkonkoma to Wyandanch local; Wyandanch to Jamaica express, stops at Farmingdale, Hicksville, Merillon Avenue, New Hyde Park | 1 | 1:01:00 | 42:54 | 41:37 | 41:18 | 38:55 |
| Ronkonkoma to Wyandanch local; Wyandanch to Jamaica express, stops at Hicksville, Mineola | 1 | 1:01:00 | 40:13 | 38:56 | 38:37 | 35:50 |

#### Croton-Harmon - GCT

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Croton-Harmon, all stops | 6 | 1:11:00 | 56:56 | 51:23 | 50:13 | 49:56 |
| Croton-Harmon to Hastings-on-Hudson local; Hastings-on-Hudson to GCT express, stops at Yonkers, Marble Hill, Harlem-125 St | 4 | 1:00:30 | 49:18 | 43:38 | 41:56 | 41:28 |
| Croton-Harmon to Tarrytown local; Tarrytown to GCT express, stops at Harlem-125 St | 3 | 55:00 | 42:05 | 36:16 | 34:28 | 33:36 |
| Greystone, all stops | 3 | 45:00 | 33:10 | 27:43 | 26:47 | 26:34 |
| Croton-Harmon to Tarrytown local; Tarrytown to GCT express | 1 | 1:00:00 | 41:14 | 35:15 | 33:21 | 32:26 |
| Croton-Harmon to Hastings-on-Hudson local; Hastings-on-Hudson to GCT express, stops at Harlem-125 St | 1 | 1:02:00 | 47:20 | 41:31 | 39:44 | 39:15 |
| Croton-Harmon to Hastings-on-Hudson local; Hastings-on-Hudson to GCT express, stops at Yonkers, Harlem-125 St | 1 | 1:00:00 | 48:22 | 42:39 | 40:57 | 40:30 |
| Irvington to Greystone local; Greystone to GCT express, stops at Harlem-125 St | 1 | 46:00 | 33:36 | 27:53 | 26:27 | 26:05 |
| Irvington to Hastings-on-Hudson local; Hastings-on-Hudson to GCT express, stops at Yonkers, Harlem-125 St | 1 | 49:00 | 33:25 | 27:48 | 26:20 | 25:56 |
| Tarrytown to Greystone local; Greystone to GCT express, stops at Harlem-125 St | 1 | 51:00 | 36:52 | 31:09 | 29:42 | 29:17 |

#### Southeast - GCT

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| North White Plains, all stops | 6 | 56:30 | 46:13 | 41:15 | 40:06 | 39:52 |
| Southeast to White Plains local, skips Mt Pleasant; White Plains to GCT express, stops at Harlem-125 St | 5 | 1:29:00 | 1:14:32 | 1:07:51 | 1:02:44 | 1:01:43 |
| Crestwood to Mt Vernon West local; Mt Vernon West to GCT express, stops at Harlem-125 St | 4 | 37:30 | 26:54 | 22:19 | 20:47 | 20:20 |
| North White Plains to Crestwood local; Crestwood to GCT express, stops at Harlem-125 St | 3 | 46:00 | 34:10 | 29:12 | 26:51 | 26:15 |
| Southeast to Goldens Bridge local; Goldens Bridge to GCT express, stops at White Plains, Harlem-125 St | 3 | 1:30:00 | 1:06:38 | 59:16 | 53:09 | 51:50 |
| Mt Kisco to White Plains local, skips Mt Pleasant; White Plains to GCT express, stops at Harlem-125 St | 2 | 1:04:30 | 49:34 | 43:46 | 39:43 | 38:43 |
| North White Plains to Scarsdale local; Scarsdale to GCT express, stops at Harlem-125 St | 2 | 42:00 | 33:06 | 28:07 | 25:30 | 24:50 |
| Southeast to Chappaqua local; Chappaqua to GCT express, stops at White Plains, Harlem-125 St | 2 | 1:28:30 | 1:10:47 | 1:03:38 | 58:17 | 57:16 |
| Crestwood to Fleetwood local; Fleetwood to GCT express | 1 | 40:00 | 25:00 | 20:14 | 18:22 | 17:45 |
| Crestwood to Mt Vernon West local; Mt Vernon West to GCT express | 1 | 35:00 | 26:03 | 21:18 | 19:40 | 19:10 |
| Crestwood, all stops | 1 | 43:00 | 34:41 | 30:06 | 29:16 | 29:03 |
| Crestwood to Williams Bridge local; Williams Bridge to GCT express, stops at Harlem-125 St | 1 | 37:00 | 30:15 | 25:39 | 24:29 | 24:11 |
| Hartsdale, stops at Scarsdale | 1 | 38:00 | 26:33 | 21:48 | 19:11 | 18:27 |
| Hartsdale, stops at Scarsdale, Harlem-125 St | 1 | 39:00 | 27:24 | 22:49 | 20:17 | 19:37 |
| Mt Kisco to Scarsdale local, skips Mt Pleasant; Scarsdale to GCT express, stops at Harlem-125 St | 1 | 1:08:00 | 51:46 | 45:57 | 42:26 | 41:33 |
| Mt Kisco to White Plains local, skips Mt Pleasant; White Plains to GCT express, stops at Mt Vernon West, Fordham, Harlem-125 St | 1 | 1:07:00 | 51:43 | 45:54 | 42:17 | 41:27 |
| Mt Vernon West, all stops | 1 | 37:00 | 26:44 | 22:09 | 21:22 | 21:09 |
| North White Plains, stops at White Plains | 1 | 45:00 | 30:04 | 24:55 | 21:40 | 20:50 |
| North White Plains, stops at White Plains, Harlem-125 St | 1 | 45:00 | 30:54 | 25:56 | 22:47 | 22:00 |
| North White Plains to Crestwood local; Crestwood to GCT express | 1 | 43:00 | 33:20 | 28:11 | 25:44 | 25:05 |
| Southeast to Chappaqua local; Chappaqua to GCT express, stops at North White Plains, Harlem-125 St | 1 | 1:30:00 | 1:10:54 | 1:03:37 | 58:17 | 57:17 |
| Southeast to Chappaqua local; Chappaqua to GCT express, stops at North White Plains, White Plains, Harlem-125 St | 1 | 1:25:00 | 1:11:42 | 1:04:43 | 59:27 | 58:26 |
| Southeast to Hawthorne local; Hawthorne to GCT express, stops at Valhalla, White Plains, Harlem-125 St | 1 | 1:27:00 | 1:13:38 | 1:06:47 | 1:01:34 | 1:00:33 |
| Southeast to Goldens Bridge local; Goldens Bridge to GCT express, stops at North White Plains, White Plains, Harlem-125 St | 1 | 1:26:00 | 1:07:33 | 1:00:20 | 54:19 | 53:00 |
| Southeast to Goldens Bridge local; Goldens Bridge to GCT express, stops at North White Plains, White Plains, Hartsdale, Scarsdale, Harlem-125 St | 1 | 1:29:00 | 1:09:44 | 1:02:31 | 57:02 | 55:50 |

#### New Haven - GCT

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stamford, all stops | 6 | 1:08:00 | 52:43 | 46:55 | 45:07 | 44:50 |
| New Haven, stops at Bridgeport, Stamford | 3 | 1:30:00 | 1:15:57 | 1:07:36 | 1:01:36 | 59:19 |
| New Rochelle, skips Fordham | 3 | 37:00 | 25:22 | 20:04 | 18:32 | 18:14 |
| Harrison, stops at Mamaroneck, Larchmont | 2 | 44:30 | 29:53 | 23:59 | 21:50 | 21:26 |
| Harrison, stops at Mamaroneck, Larchmont, Harlem-125 St | 2 | 44:30 | 30:44 | 25:00 | 22:57 | 22:37 |
| New Haven to Greenwich local, skips Rowayton, Darien, Noroton Heights; Greenwich to GCT express, stops at Harlem-125 St | 2 | 2:08:30 | 1:32:36 | 1:24:49 | 1:20:14 | 1:18:41 |
| South Norwalk to Stamford local; Stamford to GCT express, stops at Greenwich, Harlem-125 St | 2 | 1:12:00 | 51:43 | 45:08 | 41:54 | 41:05 |
| Stamford to Rye local; Rye to GCT express, stops at Harlem-125 St | 2 | 1:03:30 | 44:56 | 38:50 | 36:20 | 35:36 |
| Bridgeport to East Norwalk local; East Norwalk to GCT express | 1 | 1:33:00 | 1:05:51 | 58:12 | 53:56 | 52:52 |
| Bridgeport to Stamford local; Stamford to GCT express, stops at Harlem-125 St | 1 | 1:34:00 | 1:12:03 | 1:04:47 | 1:01:06 | 1:00:10 |
| Bridgeport to South Norwalk local; South Norwalk to GCT express, stops at Stamford, Harlem-125 St | 1 | 1:35:00 | 1:08:32 | 1:01:16 | 57:18 | 56:18 |
| Fairfield-Black Rock to South Norwalk local; South Norwalk to GCT express, stops at Stamford, Harlem-125 St | 1 | 1:23:00 | 1:03:46 | 57:02 | 53:13 | 52:16 |
| Greenwich, stops at Port Chester, Rye, Harlem-125 St | 1 | 52:00 | 36:05 | 30:04 | 27:38 | 26:55 |
| Harrison, all stops | 1 | 47:00 | 34:43 | 29:17 | 27:50 | 27:33 |
| Harrison, skips Fordham, Harlem-125 St | 1 | 45:00 | 32:47 | 27:10 | 25:28 | 25:05 |
| New Haven to Fairfield local; Fairfield to GCT express | 1 | 1:50:00 | 1:21:02 | 1:12:32 | 1:06:45 | 1:04:41 |
| New Haven to Fairfield local; Fairfield to GCT express, stops at Harlem-125 St | 1 | 1:51:00 | 1:21:53 | 1:13:33 | 1:07:52 | 1:05:52 |
| New Haven to South Norwalk local; South Norwalk to GCT express, stops at Darien, Stamford, Greenwich, Harlem-125 St | 1 | 1:59:00 | 1:30:33 | 1:22:37 | 1:17:50 | 1:16:18 |
| New Haven to Stamford local; Stamford to GCT express, stops at Harlem-125 St | 1 | 2:02:00 | 1:31:47 | 1:23:51 | 1:19:04 | 1:17:31 |
| New Haven to South Norwalk local; South Norwalk to GCT express, stops at Stamford, Harlem-125 St | 1 | 1:56:00 | 1:28:16 | 1:20:20 | 1:15:17 | 1:13:39 |
| New Haven to Fairfield local; Fairfield to GCT express, stops at Stamford, Harlem-125 St | 1 | 1:56:00 | 1:22:47 | 1:14:36 | 1:09:06 | 1:07:06 |
| New Haven to Rye local, skips Southport, Green's Farms, Rowayton, Noroton Heights; Rye to GCT express, stops at New Rochelle, Harlem-125 St | 1 | 2:08:00 | 1:34:09 | 1:26:43 | 1:22:24 | 1:20:48 |
| New Haven to Stamford local, skips Southport, Green's Farms, East Norwalk, Rowayton; Stamford to GCT express, stops at Harlem-125 St | 1 | 1:55:00 | 1:26:59 | 1:19:02 | 1:13:59 | 1:12:11 |
| New Haven to Fairfield local; Fairfield to GCT express, stops at Westport, Stamford, Harlem-125 St | 1 | 1:50:00 | 1:23:42 | 1:15:42 | 1:10:25 | 1:08:33 |
| New Haven to Bridgeport local; Bridgeport to GCT express, stops at Stamford, Harlem-125 St | 1 | 1:50:00 | 1:20:18 | 1:12:08 | 1:06:31 | 1:04:24 |
| New Rochelle, skips Fordham, Harlem-125 St | 1 | 37:00 | 24:31 | 19:02 | 17:24 | 17:03 |
| South Norwalk to Noroton Heights local; Noroton Heights to GCT express, stops at Harlem-125 St | 1 | 1:11:00 | 49:43 | 42:59 | 39:25 | 38:35 |
| South Norwalk to Stamford local; Stamford to GCT express | 1 | 1:12:00 | 49:46 | 43:00 | 39:31 | 38:38 |
| Stamford, stops at Greenwich, Port Chester, Rye, Harrison, Fordham, Harlem-125 St | 1 | 1:03:00 | 43:59 | 37:44 | 35:10 | 34:26 |
| Stamford to Greenwich express; Greenwich to Larchmont local; Larchmont to GCT express, stops at Harlem-125 St | 1 | 59:00 | 45:30 | 39:15 | 36:32 | 36:06 |
| Stamford to Rye local; Rye to GCT express | 1 | 59:00 | 44:05 | 37:49 | 35:13 | 34:26 |

#### New Canaan - Stamford

| Pattern | Trips | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| New Canaan, all stops | 5 | 18:00 | 13:48 | 11:36 | 11:20 | 11:20 |

### Trains

One train alone, next to the median scheduled for trips with that stopping pattern, if any.

#### Port Washington local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 49:00 | 34:57 | 33:17 | 31:55 | 31:44 |
| M7, 750 V third rail, full power |  | 34:37 | 32:56 | 31:27 | 31:10 |
| M8, 25 kV |  | 34:45 | 33:05 | 31:39 | 31:25 |

#### Port Washington express

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 38:30 | 25:32 | 23:42 | 21:09 | 20:46 |
| M7, 750 V third rail, full power |  | 25:26 | 23:37 | 20:55 | 20:24 |
| M8, 25 kV |  | 25:28 | 23:39 | 21:00 | 20:33 |

#### Main Line to Penn local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 22:00 | 16:59 | 14:25 | 13:25 | 13:10 |
| M7, 750 V third rail, full power |  | 16:51 | 14:17 | 13:13 | 12:54 |
| M8, 25 kV |  | 16:55 | 14:21 | 13:19 | 13:01 |

#### Main Line to Penn express

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 19:00 | 13:22 | 10:45 | 9:33 | 9:03 |
| M7, 750 V third rail, full power |  | 13:20 | 10:43 | 9:29 | 8:54 |
| M8, 25 kV |  | 13:21 | 10:45 | 9:31 | 8:58 |

#### Main Line to GCM local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail |  | 16:30 | 14:01 | 13:33 | 13:22 |
| M7, 750 V third rail, full power |  | 16:23 | 13:53 | 13:21 | 13:07 |
| M8, 25 kV |  | 16:27 | 13:57 | 13:26 | 13:14 |

#### Main Line to GCM express

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 19:00 | 12:54 | 10:21 | 9:41 | 9:15 |
| M7, 750 V third rail, full power |  | 12:52 | 10:19 | 9:36 | 9:06 |
| M8, 25 kV |  | 12:53 | 10:20 | 9:38 | 9:09 |

#### Atlantic local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 20:00 | 13:56 | 11:34 | 10:45 | 10:23 |
| M7, 750 V third rail, full power |  | 13:52 | 11:26 | 10:31 | 10:00 |
| M8, 25 kV |  | 13:53 | 11:29 | 10:36 | 10:08 |

#### Hempstead local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 31:00 | 22:23 | 20:14 | 20:13 | 20:13 |
| M7, 750 V third rail, full power |  | 22:05 | 19:54 | 19:52 | 19:51 |
| M8, 25 kV |  | 22:13 | 20:02 | 20:01 | 20:00 |

#### Babylon via Atlantic Branch local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail |  | 40:36 | 39:58 | 38:43 | 38:32 |
| M7, 750 V third rail, full power |  | 39:37 | 39:00 | 37:45 | 37:27 |
| M8, 25 kV |  | 39:58 | 39:21 | 38:06 | 37:51 |

#### Babylon via Babylon Branch local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 53:00 | 42:39 | 41:46 | 40:38 | 40:24 |
| M7, 750 V third rail, full power |  | 41:41 | 40:48 | 39:36 | 39:15 |
| M8, 25 kV |  | 42:01 | 41:09 | 39:59 | 39:41 |

#### Long Beach local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 37:00 | 26:20 | 23:17 | 22:47 | 22:46 |
| M7, 750 V third rail, full power |  | 26:05 | 23:00 | 22:22 | 22:20 |
| M8, 25 kV |  | 26:11 | 23:07 | 22:33 | 22:31 |

#### Far Rockaway local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 36:00 | 24:52 | 22:42 | 22:28 | 22:27 |
| M7, 750 V third rail, full power |  | 24:39 | 22:20 | 22:02 | 22:00 |
| M8, 25 kV |  | 24:43 | 22:27 | 22:11 | 22:10 |

#### West Hempstead local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail | 28:00 | 19:29 | 17:37 | 16:53 | 16:50 |
| M7, 750 V third rail, full power |  | 19:11 | 17:21 | 16:30 | 16:25 |
| M8, 25 kV |  | 19:16 | 17:26 | 16:38 | 16:34 |

#### Huntington local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail |  | 39:58 | 36:45 | 36:23 | 36:07 |
| M7, 750 V third rail, full power |  | 39:22 | 36:10 | 35:44 | 35:16 |
| M8, 25 kV |  | 39:40 | 36:27 | 36:02 | 35:40 |

#### Ronkonkoma local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7, 750 V third rail |  | 54:45 | 53:28 | 53:11 | 52:29 |
| M7, 750 V third rail, full power |  | 53:37 | 52:21 | 52:03 | 50:51 |
| M8, 25 kV |  | 54:05 | 52:48 | 52:30 | 51:30 |

#### Hudson local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7A, 700 V third rail | 1:11:00 | 56:56 | 51:23 | 50:13 | 49:56 |
| M7A, 700 V third rail, full power |  | 56:15 | 50:42 | 49:21 | 48:57 |
| M8, 25 kV |  | 56:36 | 51:02 | 49:47 | 49:26 |

#### Hudson express

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7A, 700 V third rail | 50:00 (diesel) | 37:19 | 31:31 | 29:20 | 28:16 |
| M7A, 700 V third rail, full power |  | 37:13 | 31:25 | 29:08 | 27:53 |
| M8, 25 kV |  | 37:16 | 31:28 | 29:13 | 28:03 |

#### Harlem local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7A, 700 V third rail | 56:30 | 46:13 | 41:15 | 40:06 | 39:52 |
| M7A, 700 V third rail, full power |  | 45:43 | 40:41 | 39:11 | 38:51 |
| M8, 25 kV |  | 45:56 | 40:54 | 39:30 | 39:13 |

#### Harlem express

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M7A, 700 V third rail | 1:29:00 | 1:14:32 | 1:07:51 | 1:02:44 | 1:01:43 |
| M7A, 700 V third rail, full power |  | 1:14:02 | 1:07:14 | 1:01:32 | 1:00:05 |
| M8, 25 kV |  | 1:14:12 | 1:07:25 | 1:01:54 | 1:00:35 |

#### New Haven local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M8, 700 V third rail and 12.5 kV | 1:08:00 | 52:43 | 46:55 | 45:07 | 44:50 |
| M8, 12.5 kV |  | 52:34 | 46:46 | 44:52 | 44:25 |

#### New Haven express

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M8, 700 V third rail and 12.5 kV | 2:02:00 | 1:31:47 | 1:23:51 | 1:19:04 | 1:17:31 |
| M8, 12.5 kV |  | 1:31:42 | 1:23:46 | 1:18:53 | 1:17:11 |

#### New Canaan local

| Train | Scheduled | Posted | 60 mph | 80 mph | 100 mph |
| --- | ---: | ---: | ---: | ---: | ---: |
| M8, 700 V third rail and 12.5 kV | 18:00 | 13:48 | 11:36 | 11:20 | 11:20 |
| M8, 12.5 kV |  | 13:48 | 11:36 | 11:20 | 11:20 |

### Busy service

Time per inbound trip in steady service, from the time-stepped multi-train simulation. "Busy" is with the other trains on the line; "+ regen" adds regenerative braking. "Scheduled" is the median for trips with that stopping pattern, if any.

#### PW local: 5:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PW local | 49:00 | posted | 35:06 | 35:11 | 35:09 | 35:00 | 521 |
|  |  | 60 mph | 33:30 | 33:35 | 33:31 | 33:23 | 486 |
|  |  | 80 mph | 32:06 | 32:13 | 32:10 | 31:58 | 502 |
|  |  | 100 mph | 31:59 | 32:07 | 32:05 | 31:50 | 495 |

#### PW express: 5:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PW express | 38:30 | posted | 25:36 | 25:37 | 25:36 | 25:33 | 541 |
|  |  | 60 mph | 23:48 | 23:50 | 23:50 | 23:46 | 476 |
|  |  | 80 mph | 21:12 | 21:15 | 21:15 | 21:08 | 479 |
|  |  | 100 mph | 20:52 | 20:56 | 20:55 | 20:45 | 500 |

#### Main Line to Penn: locals and expresses each at 2:30 headways each way (1:15 combined)

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Penn local | 22:00 | posted | 17:08 | 17:15 | 17:14 | 17:02 | 487 |
|  |  | 60 mph | 14:30 | 14:36 | 14:34 | 14:26 | 518 |
|  |  | 80 mph | 13:24 | 13:34 | 13:32 | 13:19 | 478 |
|  |  | 100 mph | 13:14 | 13:28 | 13:26 | 13:07 | 483 |
| Penn express | 19:00 | posted | 13:28 | 13:30 | 13:30 | 13:26 | 487 |
|  |  | 60 mph | 10:46 | 10:46 | 10:46 | 10:45 | 518 |
|  |  | 80 mph | 9:30 | 9:30 | 9:30 | 9:29 | 478 |
|  |  | 100 mph | 9:01 | 9:06 | 9:05 | 8:59 | 483 |

#### Main Line to GCM: 2:30 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GCM express | 19:00 | posted | 13:00 | 13:01 | 13:01 | 12:58 | 580 |
|  |  | 60 mph | 10:22 | 10:22 | 10:22 | 10:21 | 532 |
|  |  | 80 mph | 9:43 | 9:43 | 9:43 | 9:41 | 529 |
|  |  | 100 mph | 9:17 | 9:19 | 9:18 | 9:14 | 523 |

#### Atlantic: 5:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Atlantic local | 20:00 | posted | 13:56 | 13:56 | 13:57 | 13:55 | 556 |
|  |  | 60 mph | 11:32 | 11:32 | 11:32 | 11:30 | 557 |
|  |  | 80 mph | 10:41 | 10:42 | 10:42 | 10:36 | 512 |
|  |  | 100 mph | 10:15 | 10:18 | 10:18 | 10:06 | 494 |

#### Hempstead: 20:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hempstead local | 31:00 | posted | 22:33 | 22:34 | 22:34 | 22:26 | 477 |
|  |  | 60 mph | 20:26 | 20:28 | 20:27 | 20:20 | 483 |
|  |  | 80 mph | 20:26 | 20:28 | 20:26 | 20:18 | 484 |
|  |  | 100 mph | 20:25 | 20:27 | 20:25 | 20:18 | 485 |

#### Babylon via Atlantic Branch: 7:30 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Babylon via Atlantic Branch local |  | posted | 40:36 | 40:41 | 40:39 | 40:14 | 497 |
|  |  | 60 mph | 39:58 | 40:06 | 40:03 | 39:36 | 504 |
|  |  | 80 mph | 38:52 | 39:02 | 38:59 | 38:26 | 514 |
|  |  | 100 mph | 38:40 | 38:52 | 38:49 | 38:13 | 520 |

#### Babylon via Babylon Branch: 7:30 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Babylon via Babylon Branch local | 53:00 | posted | 42:44 | 42:50 | 42:47 | 42:20 | 499 |
|  |  | 60 mph | 41:52 | 42:03 | 41:59 | 41:28 | 499 |
|  |  | 80 mph | 40:47 | 40:57 | 40:53 | 40:20 | 489 |
|  |  | 100 mph | 40:36 | 40:47 | 40:44 | 40:06 | 493 |

#### Long Beach: 12:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Long Beach local | 37:00 | posted | 26:32 | 26:34 | 26:33 | 26:25 | 523 |
|  |  | 60 mph | 23:34 | 23:35 | 23:34 | 23:24 | 531 |
|  |  | 80 mph | 23:00 | 23:04 | 23:01 | 22:48 | 527 |
|  |  | 100 mph | 22:59 | 23:04 | 23:00 | 22:46 | 526 |

#### Far Rockaway: 15:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Far Rockaway local | 36:00 | posted | 25:07 | 25:07 | 25:06 | 25:00 | 497 |
|  |  | 60 mph | 22:57 | 22:59 | 22:58 | 22:45 | 495 |
|  |  | 80 mph | 22:44 | 22:46 | 22:46 | 22:30 | 494 |
|  |  | 100 mph | 22:44 | 22:46 | 22:46 | 22:28 | 494 |

#### West Hempstead: 1:00:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| West Hempstead local | 28:00 | posted | 19:33 | 19:33 | 19:33 | 19:24 | 528 |
|  |  | 60 mph | 17:44 | 17:44 | 17:44 | 17:34 | 528 |
|  |  | 80 mph | 17:00 | 17:00 | 17:00 | 16:47 | 528 |
|  |  | 100 mph | 16:56 | 16:56 | 16:56 | 16:43 | 528 |

#### Huntington: 10:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Huntington local |  | posted | 40:05 | 40:08 | 40:06 | 39:52 | 531 |
|  |  | 60 mph | 36:54 | 36:57 | 36:58 | 36:41 | 542 |
|  |  | 80 mph | 36:30 | 36:34 | 36:34 | 36:16 | 543 |
|  |  | 100 mph | 36:06 | 36:10 | 36:09 | 35:47 | 534 |

#### Ronkonkoma: 10:00 headways each way

| Service | Scheduled | Speeds | M7, 1 train | M7, busy | M7, busy + regen | M8 25 kV | Lowest V (M7) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ronkonkoma local |  | posted | 54:58 | 55:05 | 55:03 | 54:28 | 505 |
|  |  | 60 mph | 53:42 | 53:47 | 53:44 | 53:14 | 497 |
|  |  | 80 mph | 53:23 | 53:25 | 53:23 | 52:56 | 512 |
|  |  | 100 mph | 52:34 | 52:42 | 52:36 | 51:52 | 520 |

#### Hudson: locals at 10:00 and expresses at 20:00 headways each way

| Service | Scheduled | Speeds | M7A, 1 train | M7A, busy | M7A, busy + regen | M8 25 kV | Lowest V (M7A) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hudson local | 1:11:00 | posted | 57:06 | 57:09 | 57:07 | 56:56 | 513 |
|  |  | 60 mph | 51:36 | 51:39 | 51:37 | 51:26 | 504 |
|  |  | 80 mph | 50:24 | 50:28 | 50:26 | 50:08 | 490 |
|  |  | 100 mph | 50:06 | 50:12 | 50:11 | 49:48 | 495 |
| Hudson express | 50:00 (diesel) | posted | 37:18 | 37:20 | 37:20 | 37:16 | 513 |
|  |  | 60 mph | 31:30 | 31:32 | 31:32 | 31:30 | 504 |
|  |  | 80 mph | 29:18 | 29:20 | 29:20 | 29:14 | 490 |
|  |  | 100 mph | 28:11 | 28:14 | 28:14 | 28:04 | 495 |

#### Harlem: locals at 6:00 and expresses at 8:34 headways each way

| Service | Scheduled | Speeds | M7A, 1 train | M7A, busy | M7A, busy + regen | M8 25 kV | Lowest V (M7A) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Harlem local | 56:30 | posted | 46:34 | 46:44 | 46:41 | 46:22 | 438 |
|  |  | 60 mph | 41:35 | 41:41 | 41:37 | 41:22 | 441 |
|  |  | 80 mph | 40:18 | 40:31 | 40:27 | 39:54 | 425 |
|  |  | 100 mph | 40:02 | 40:22 | 40:17 | 39:36 | 424 |
| Harlem express | 1:29:00 | posted | 1:14:35 | 1:14:40 | 1:14:39 | 1:14:27 | 438 |
|  |  | 60 mph | 1:07:53 | 1:07:59 | 1:07:57 | 1:07:46 | 441 |
|  |  | 80 mph | 1:02:38 | 1:02:55 | 1:02:50 | 1:02:18 | 425 |
|  |  | 100 mph | 1:01:27 | 1:01:54 | 1:01:46 | 1:00:57 | 424 |

#### New Haven: locals at 6:40 and expresses at 6:40 headways each way

| Service | Scheduled | Speeds | M8, 1 train | M8, busy | M8, busy + regen | M8 12.5 kV | Lowest V (M8) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| New Haven local | 1:08:00 | posted | 53:04 | 53:06 | 53:05 | 52:57 | 485 |
|  |  | 60 mph | 47:19 | 47:19 | 47:19 | 47:12 | 478 |
|  |  | 80 mph | 45:24 | 45:26 | 45:25 | 45:12 | 475 |
|  |  | 100 mph | 45:03 | 45:09 | 45:08 | 44:46 | 460 |
| New Haven express | 2:02:00 | posted | 1:32:08 | 1:32:09 | 1:32:08 | 1:32:06 | 485 |
|  |  | 60 mph | 1:24:13 | 1:24:13 | 1:24:13 | 1:24:11 | 478 |
|  |  | 80 mph | 1:19:28 | 1:19:29 | 1:19:29 | 1:19:24 | 475 |
|  |  | 100 mph | 1:17:48 | 1:17:52 | 1:17:52 | 1:17:37 | 460 |

#### New Canaan: 30:00 headways each way

| Service | Scheduled | Speeds | M8, 1 train | M8, busy | M8, busy + regen | M8 12.5 kV | Lowest V (M8) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| New Canaan local | 18:00 | posted | 13:54 | 13:54 | 13:54 | 13:54 |  |
|  |  | 60 mph | 11:42 | 11:42 | 11:42 | 11:42 |  |
|  |  | 80 mph | 11:26 | 11:26 | 11:26 | 11:26 |  |
|  |  | 100 mph | 11:26 | 11:26 | 11:26 | 11:26 |  |

### Posted slow zones

One train, the timetable's, raising one posted zone at a time to what the curves allow (80 mph cap).

#### Port Washington (base: local 34:57, express 25:32)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 2.67 | 4.38 | Woodside | 50 mph | 80 mph | 0:41 | 0:41 |
| 9.64 | 13.45 | Auburndale | 60 mph | 80 mph | 0:01 | 0:41 |
| 0.00 | 0.25 | Penn Station | 15 mph | 73 mph | 0:39 | 0:39 |
| 6.08 | 9.55 | Mets-Willets Point | 60 mph | 80 mph | 0:24 | 0:36 |
| 0.26 | 2.67 | Penn Station | 60 mph | 80 mph | 0:19 | 0:19 |
| 15.89 | 18.38 | Manhasset | 50 mph | 80 mph | 0:19 | 0:19 |
| 13.46 | 13.81 | Douglaston | 40 mph | 77 mph | 0:09 | 0:14 |
| 13.81 | 15.89 | Little Neck | 60 mph | 80 mph | 0:01 | 0:09 |
| 18.39 | 19.40 | Port Washington | 40 mph | 65 mph | 0:08 | 0:08 |
| 5.84 | 6.07 | Woodside | 40 mph | 49 mph | 0:07 | 0:07 |

#### Main Line to Penn (base: local 16:59, express 13:22)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 10.49 | 10.88 | Jamaica | 20 mph | 80 mph | 0:55 | 1:00 |
| 0.00 | 0.30 | Penn Station | 15 mph | 80 mph | 0:48 | 0:48 |
| 2.55 | 3.98 | Woodside | 50 mph | 80 mph | 0:32 | 0:32 |
| 10.98 | 11.27 | Jamaica | 20 mph | 80 mph | 0:20 | 0:20 |
| 0.30 | 2.55 | Penn Station | 60 mph | 80 mph | 0:18 | 0:18 |
| 4.45 | 5.98 | Woodside | 60 mph | 80 mph | 0:06 | 0:17 |
| 3.99 | 4.45 | Woodside | 50 mph | 80 mph | 0:06 | 0:06 |

#### Main Line to GCM (base: local 16:30, express 12:54)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 9.77 | 10.22 | Jamaica | 20 mph | 80 mph | 1:00 | 1:05 |
| 0.00 | 0.22 | Grand Central | 15 mph | 73 mph | 0:28 | 0:28 |
| 10.27 | 10.56 | Jamaica | 20 mph | 80 mph | 0:19 | 0:19 |
| 3.76 | 5.27 | Woodside | 60 mph | 80 mph | 0:06 | 0:16 |
| 2.59 | 3.38 | Woodside | 45 mph | 80 mph | 0:12 | 0:12 |
| 1.09 | 2.59 | Grand Central | 60 mph | 80 mph | 0:10 | 0:10 |
| 0.46 | 1.09 | Grand Central | 45 mph | 80 mph | 0:09 | 0:09 |
| 0.22 | 0.45 | Grand Central | 30 mph | 46 mph | 0:07 | 0:07 |
| 3.38 | 3.76 | Woodside | 50 mph | 80 mph | 0:04 | 0:04 |

#### Atlantic (base: local 13:56)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1.41 | 3.98 | East New York | 45 mph | 80 mph | 0:55 |
| 8.77 | 9.19 | Jamaica | 20 mph | 80 mph | 0:37 |
| 0.00 | 0.07 | Atlantic Terminal | 5 mph | 15 mph | 0:31 |
| 4.03 | 8.27 | East New York | 70 mph | 80 mph | 0:20 |
| 0.09 | 1.25 | Atlantic Terminal | 45 mph | 80 mph | 0:16 |
| 8.27 | 8.77 | Jamaica | 45 mph | 80 mph | 0:11 |
| 1.25 | 1.40 | Nostrand Avenue | 30 mph | 53 mph | 0:07 |

#### Hempstead (base: local 22:23)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 9.37 | 9.60 | Country Life Press | 15 mph | 38 mph | 0:41 |
| 10.17 | 10.33 | Hempstead | 10 mph | 80 mph | 0:25 |
| 0.23 | 0.69 | Jamaica | 35 mph | 80 mph | 0:22 |
| 0.00 | 0.22 | Jamaica | 20 mph | 80 mph | 0:17 |
| 9.61 | 10.17 | Country Life Press | 30 mph | 62 mph | 0:08 |
| 5.70 | 5.75 | Floral Park | 25 mph | 45 mph | 0:07 |

#### Babylon via Atlantic Branch (base: local 40:36)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 3.84 | 6.20 | Lynbrook | 60 mph | 80 mph | 0:30 |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 0:13 |
| 25.68 | 26.73 | Babylon | 60 mph | 80 mph | 0:11 |
| 0.37 | 0.60 | Jamaica | 35 mph | 62 mph | 0:09 |
| 6.20 | 6.46 | Lynbrook | 45 mph | 80 mph | 0:07 |
| 6.61 | 8.25 | Lynbrook | 60 mph | 80 mph | 0:07 |
| 3.04 | 3.11 | Jamaica | 60 mph | 80 mph | 0:05 |
| 0.98 | 1.28 | Jamaica | 60 mph | 77 mph | 0:04 |
| 0.25 | 0.37 | Jamaica | 30 mph | 39 mph | 0:03 |

#### Babylon via Babylon Branch (base: local 42:39)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 6.36 | 8.93 | Lynbrook | 60 mph | 80 mph | 0:27 |
| 0.19 | 0.64 | Jamaica | 35 mph | 80 mph | 0:14 |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 0:13 |
| 26.35 | 27.41 | Babylon | 60 mph | 80 mph | 0:11 |
| 0.65 | 1.69 | Jamaica | 50 mph | 80 mph | 0:11 |
| 3.15 | 3.68 | St. Albans | 50 mph | 80 mph | 0:10 |
| 3.68 | 5.17 | St. Albans | 60 mph | 80 mph | 0:07 |
| 5.32 | 6.35 | Lynbrook | 70 mph | 80 mph | 0:03 |

#### Long Beach (base: local 26:20)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 12.92 | 13.15 | Long Beach | 5 mph | 55 mph | 1:48 |
| 11.41 | 11.74 | Island Park | 40 mph | 61 mph | 0:16 |
| 12.58 | 12.92 | Long Beach | 30 mph | 80 mph | 0:14 |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 0:13 |
| 3.84 | 6.20 | Rosedale | 60 mph | 80 mph | 0:09 |
| 0.37 | 0.60 | Jamaica | 35 mph | 62 mph | 0:09 |
| 9.69 | 11.41 | Oceanside | 60 mph | 80 mph | 0:07 |
| 0.98 | 1.28 | Jamaica | 60 mph | 77 mph | 0:04 |
| 6.93 | 8.08 | Lynbrook | 60 mph | 80 mph | 0:04 |
| 8.09 | 8.89 | Centre Avenue | 45 mph | 80 mph | 0:04 |
| 6.20 | 6.70 | Valley Stream | 45 mph | 80 mph | 0:04 |
| 0.25 | 0.37 | Jamaica | 30 mph | 39 mph | 0:03 |

#### Far Rockaway (base: local 24:52)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 6.41 | 6.61 | Valley Stream | 15 mph | 39 mph | 0:36 |
| 8.11 | 11.09 | Cedarhurst | 40 mph | 80 mph | 0:26 |
| 11.09 | 11.24 | Far Rockaway | 10 mph | 67 mph | 0:21 |
| 0.00 | 0.18 | Jamaica | 20 mph | 80 mph | 0:13 |
| 6.61 | 7.89 | Gibson | 40 mph | 80 mph | 0:12 |
| 3.84 | 6.20 | Rosedale | 60 mph | 80 mph | 0:09 |
| 0.37 | 0.60 | Jamaica | 35 mph | 62 mph | 0:09 |
| 7.89 | 8.10 | Hewlett | 30 mph | 36 mph | 0:05 |
| 0.98 | 1.28 | Jamaica | 60 mph | 77 mph | 0:04 |
| 0.25 | 0.37 | Jamaica | 30 mph | 39 mph | 0:03 |

#### West Hempstead (base: local 19:29)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 7.41 | 7.59 | Westwood | 15 mph | 44 mph | 0:47 |
| 0.00 | 0.23 | Jamaica | 20 mph | 80 mph | 0:17 |
| 0.23 | 0.69 | Jamaica | 35 mph | 80 mph | 0:14 |
| 0.80 | 1.73 | Jamaica | 50 mph | 80 mph | 0:12 |
| 11.56 | 11.66 | West Hempstead | 10 mph | 80 mph | 0:10 |
| 3.73 | 5.41 | St. Albans | 60 mph | 80 mph | 0:09 |
| 3.47 | 3.73 | St. Albans | 50 mph | 80 mph | 0:06 |
| 5.41 | 6.76 | Westwood | 70 mph | 80 mph | 0:05 |
| 6.76 | 7.41 | Westwood | 60 mph | 80 mph | 0:04 |
| 1.74 | 3.47 | St. Albans | 60 mph | 80 mph | 0:04 |

#### Huntington (base: local 39:58)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 24.28 | 25.30 | Huntington | 30 mph | 80 mph | 0:59 |
| 21.40 | 24.28 | Cold Spring Harbor | 45 mph | 80 mph | 0:47 |
| 14.96 | 16.12 | Hicksville | 40 mph | 80 mph | 0:36 |
| 0.00 | 0.32 | Jamaica | 20 mph | 80 mph | 0:26 |
| 0.32 | 0.71 | Jamaica | 35 mph | 80 mph | 0:18 |
| 19.41 | 19.79 | Syosset | 50 mph | 61 mph | 0:04 |

#### Ronkonkoma (base: local 54:45)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0.00 | 0.32 | Jamaica | 20 mph | 80 mph | 0:26 |
| 14.97 | 15.95 | Hicksville | 40 mph | 80 mph | 0:26 |
| 0.32 | 0.71 | Jamaica | 35 mph | 80 mph | 0:18 |
| 19.31 | 19.96 | Bethpage | 60 mph | 80 mph | 0:11 |

#### Hudson (base: local 56:56, express 37:19)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 0.00 | 0.88 | Grand Central | 10 mph | 80 mph | 4:09 | 4:09 |
| 9.82 | 10.72 | Spuyten Duyvil | 30 mph | 80 mph | 0:36 | 0:43 |
| 23.69 | 31.75 | Scarborough | 70 mph | 80 mph | 0:10 | 0:33 |
| 14.43 | 17.81 | Glenwood | 70 mph | 80 mph | 0:01 | 0:16 |
| 6.33 | 9.16 | Morris Heights | 60 mph | 80 mph | 0:08 | 0:15 |
| 10.72 | 14.13 | Riverdale | 70 mph | 80 mph | 0:01 | 0:12 |
| 5.40 | 6.33 | Harlem-125 St | 45 mph | 80 mph | 0:11 | 0:11 |
| 4.46 | 4.93 | Harlem-125 St | 35 mph | 52 mph | 0:11 | 0:11 |
| 14.14 | 14.43 | Yonkers | 50 mph | 70 mph | 0:01 | 0:11 |
| 2.69 | 3.95 | Harlem-125 St | 60 mph | 80 mph | 0:07 | 0:07 |
| 31.75 | 32.04 | Croton-Harmon | 50 mph | 80 mph | 0:05 | 0:05 |
| 2.63 | 2.69 | Harlem-125 St | 45 mph | 80 mph | 0:04 | 0:04 |

#### Harlem (base: local 46:13, express 1:14:32)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 0.00 | 0.88 | Grand Central | 10 mph | 80 mph | 4:09 | 4:09 |
| 11.39 | 14.55 | Mt Vernon West | 60 mph | 80 mph | 0:03 | 0:45 |
| 18.58 | 21.95 | Hartsdale | 60 mph | 80 mph | 0:09 | 0:38 |
| 38.97 | 45.45 | Goldens Bridge | 60 mph | 80 mph | 0:00 | 0:34 |
| 0.89 | 3.94 | Harlem-125 St | 60 mph | 80 mph | 0:31 | 0:31 |
| 51.51 | 52.76 | Brewster | 40 mph | 80 mph | 0:00 | 0:25 |
| 25.14 | 25.99 | Valhalla | 40 mph | 80 mph | 0:00 | 0:22 |
| 14.66 | 17.21 | Tuckahoe | 60 mph | 80 mph | 0:00 | 0:19 |
| 21.95 | 22.58 | White Plains | 35 mph | 80 mph | 0:17 | 0:17 |
| 25.99 | 30.05 | Hawthorne | 60 mph | 80 mph | 0:00 | 0:15 |
| 32.22 | 35.65 | Chappaqua | 70 mph | 80 mph | 0:00 | 0:15 |
| 4.46 | 4.92 | Harlem-125 St | 35 mph | 54 mph | 0:12 | 0:12 |

#### New Haven (base: local 52:43, express 1:31:47)

| From mi | To mi | Near | Posted | Raised to | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 0.00 | 0.88 | Grand Central | 10 mph | 80 mph | 4:09 | 4:09 |
| 15.87 | 16.55 | New Rochelle | 30 mph | 68 mph | 0:30 | 0:43 |
| 11.39 | 15.69 | Mt Vernon East  | 60 mph | 80 mph | 0:21 | 0:41 |
| 54.48 | 55.16 | Bridgeport | 30 mph | 80 mph | 0:00 | 0:32 |
| 33.02 | 34.30 | Stamford | 50 mph | 80 mph | 0:00 | 0:26 |
| 29.53 | 30.00 | Cos Cob | 50 mph | 80 mph | 0:00 | 0:16 |
| 63.59 | 70.73 | West Haven | 75 mph | 80 mph | 0:00 | 0:13 |
| 23.00 | 23.35 | Rye | 50 mph | 80 mph | 0:13 | 0:13 |
| 4.46 | 4.92 | Harlem-125 St | 35 mph | 50 mph | 0:12 | 0:12 |
| 71.53 | 71.83 | New Haven | 30 mph | 80 mph | 0:00 | 0:10 |
| 55.17 | 56.22 | Bridgeport | 45 mph | 80 mph | 0:00 | 0:10 |
| 8.70 | 9.89 | Fordham | 60 mph | 80 mph | 0:01 | 0:10 |

#### New Canaan (base: local 13:48)

| From mi | To mi | Near | Posted | Raised to | local saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 2.47 | 7.49 | Talmadge Hill | 40 mph | 80 mph | 1:53 |
| 0.23 | 1.73 | Stamford | 50 mph | 80 mph | 0:25 |
| 2.20 | 2.32 | Glenbrook | 20 mph | 67 mph | 0:06 |

### Limiting curves

One train, the timetable's, at an 80 mph cap, easing one curve-limited zone at a time to 80 mph.

#### Port Washington (base: local 31:55, express 21:09)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 17.31 | 19.49 | Port Washington | 15 mph | 0:22 | 0:22 |
| 5.53 | 6.21 | Woodside | 48 mph | 0:16 | 0:21 |
| 13.30 | 13.94 | Douglaston | 55 mph | 0:03 | 0:15 |
| 4.29 | 5.06 | Woodside | 57 mph | 0:09 | 0:14 |
| 9.41 | 9.81 | Flushing Main Street | 57 mph | 0:00 | 0:09 |
| 10.13 | 10.61 | Murray Hill | 65 mph | 0:00 | 0:06 |
| 8.87 | 9.23 | Mets-Willets Point | 69 mph | 0:00 | 0:03 |

#### Main Line to Penn (base: local 13:25, express 9:33)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 4.32 | 5.07 | Woodside | 65 mph | 0:04 | 0:07 |
| 10.57 | 11.17 | Jamaica | 57 mph | 0:04 | 0:05 |

#### Main Line to GCM (base: local 13:33, express 9:41)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 2.58 | 3.11 | Woodside | 53 mph | 0:19 | 0:19 |
| 0.00 | 1.08 | Grand Central | 44 mph | 0:17 | 0:17 |
| 9.86 | 10.45 | Jamaica | 47 mph | 0:08 | 0:09 |
| 3.54 | 4.22 | Woodside | 65 mph | 0:03 | 0:06 |
| 4.92 | 5.27 | Woodside | 70 mph | 0:00 | 0:03 |

#### Atlantic (base: local 10:45)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.00 | 0.31 | Atlantic Terminal | 15 mph | 0:13 |
| 1.09 | 1.45 | Nostrand Avenue | 53 mph | 0:03 |

#### Hempstead (base: local 20:13)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 9.27 | 10.23 | Garden City | 38 mph | 0:08 |
| 10.24 | 10.33 | Hempstead | 15 mph | 0:06 |
| 0.12 | 0.58 | Jamaica | 54 mph | 0:04 |

#### Babylon via Atlantic Branch (base: local 38:43)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.02 | 0.72 | Jamaica | 39 mph | 0:11 |

#### Babylon via Babylon Branch (base: local 40:38)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 1.09 | 1.81 | St. Albans | 58 mph | 0:13 |
| 4.31 | 5.10 | St. Albans | 60 mph | 0:11 |
| 0.08 | 0.53 | Jamaica | 55 mph | 0:03 |

#### Long Beach (base: local 22:47)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.02 | 0.72 | Jamaica | 39 mph | 0:11 |
| 11.31 | 11.87 | Island Park | 60 mph | 0:09 |
| 12.81 | 13.15 | Long Beach | 15 mph | 0:07 |
| 7.81 | 8.44 | Lynbrook | 47 mph | 0:04 |

#### Far Rockaway (base: local 22:28)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 0.02 | 0.72 | Jamaica | 39 mph | 0:11 |
| 7.74 | 8.22 | Hewlett | 36 mph | 0:11 |
| 6.24 | 6.73 | Valley Stream | 39 mph | 0:07 |
| 10.90 | 11.24 | Far Rockaway | 15 mph | 0:06 |

#### West Hempstead (base: local 16:53)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 7.24 | 7.74 | Westwood | 44 mph | 0:21 |
| 1.13 | 1.86 | St. Albans | 62 mph | 0:11 |
| 4.35 | 5.10 | St. Albans | 60 mph | 0:11 |
| 11.57 | 11.66 | West Hempstead | 15 mph | 0:06 |
| 0.12 | 0.58 | Jamaica | 55 mph | 0:04 |

#### Huntington (base: local 36:23)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 22.59 | 23.96 | Cold Spring Harbor | 48 mph | 0:18 |
| 21.54 | 22.56 | Cold Spring Harbor | 56 mph | 0:10 |
| 15.46 | 16.12 | Hicksville | 50 mph | 0:04 |

#### Ronkonkoma (base: local 53:11)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 15.37 | 15.95 | Hicksville | 49 mph | 0:07 |

#### Hudson (base: local 50:13, express 29:20)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 7.93 | 10.64 | Marble Hill | 42 mph | 0:13 | 1:10 |
| 4.29 | 5.56 | Harlem-125 St | 42 mph | 0:38 | 0:38 |
| 0.00 | 0.09 | Grand Central | 15 mph | 0:14 | 0:14 |
| 5.89 | 6.37 | Harlem-125 St | 52 mph | 0:14 | 0:14 |
| 14.03 | 15.01 | Yonkers | 69 mph | 0:00 | 0:07 |
| 28.30 | 29.06 | Scarborough | 70 mph | 0:00 | 0:06 |
| 7.21 | 7.59 | Morris Heights | 67 mph | 0:04 | 0:05 |
| 26.92 | 27.33 | Philipse Manor | 70 mph | 0:04 | 0:04 |
| 13.38 | 13.85 | Ludlow | 71 mph | 0:00 | 0:03 |

#### Harlem (base: local 40:06, express 1:02:44)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 4.29 | 5.09 | Harlem-125 St | 44 mph | 0:19 | 0:20 |
| 0.00 | 0.09 | Grand Central | 15 mph | 0:14 | 0:14 |
| 14.40 | 14.82 | Fleetwood | 55 mph | 0:01 | 0:11 |
| 6.14 | 6.60 | Melrose | 60 mph | 0:00 | 0:10 |
| 28.76 | 29.67 | Hawthorne | 60 mph | 0:00 | 0:10 |
| 9.57 | 10.01 | Botanical Garden | 60 mph | 0:00 | 0:10 |
| 50.11 | 51.72 | Brewster | 61 mph | 0:00 | 0:10 |
| 37.52 | 38.00 | Bedford Hills | 63 mph | 0:00 | 0:09 |
| 48.87 | 49.44 | Croton Falls | 61 mph | 0:00 | 0:09 |
| 18.79 | 19.17 | Scarsdale | 65 mph | 0:00 | 0:08 |

#### New Haven (base: local 45:07, express 1:19:04)

| From mi | To mi | Near | Allows | local saves | express saves |
| ---: | ---: | --- | ---: | ---: | ---: |
| 54.38 | 55.10 | Bridgeport | 40 mph | 0:00 | 0:23 |
| 4.28 | 5.09 | Harlem-125 St | 45 mph | 0:18 | 0:18 |
| 12.36 | 13.89 | Mt Vernon East  | 64 mph | 0:10 | 0:16 |
| 15.54 | 16.60 | New Rochelle | 61 mph | 0:04 | 0:15 |
| 0.00 | 0.09 | Grand Central | 15 mph | 0:14 | 0:14 |
| 25.41 | 26.27 | Port Chester | 57 mph | 0:02 | 0:13 |
| 6.14 | 6.60 | Harlem-125 St | 60 mph | 0:11 | 0:11 |
| 55.23 | 56.03 | Bridgeport | 49 mph | 0:00 | 0:10 |
| 9.58 | 10.01 | Fordham | 60 mph | 0:07 | 0:10 |
| 23.57 | 24.60 | Rye | 66 mph | 0:00 | 0:09 |

#### New Canaan (base: local 11:20)

| From mi | To mi | Near | Allows | local saves |
| ---: | ---: | --- | ---: | ---: |
| 3.40 | 5.61 | Springdale | 48 mph | 0:21 |
| 5.83 | 7.49 | New Canaan | 40 mph | 0:18 |
| 0.97 | 1.54 | Stamford | 60 mph | 0:09 |
| 7.52 | 7.61 | New Canaan | 15 mph | 0:06 |

<!-- END results -->

## License

The code is under the [MIT License](LICENSE).
The traced track geometry and substations in `data/` are derived from OpenStreetMap,
© OpenStreetMap contributors, and are under the ODbL; see [`data/LICENSE`](data/LICENSE).
