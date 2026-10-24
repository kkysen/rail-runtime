"""Compare rolling stock on curve-limited geometry, with and without a 60 mph cap."""
import numpy as np

import sim

order = sorted(sim.st, key=sim.st.get, reverse=True)
pats = {"PW local": order,
        "PW express": ["Port Washington", "Plandome", "Manhasset", "Great Neck", "Penn Station"],
        "GN local": order[order.index("Great Neck"):],
        "GN-Penn nonstop": ["Great Neck", "Penn Station"]}
for name in sim.TRAINS:
    vmax = sim.set_train(name)
    kw_t = sim.P_WHEEL / 1e3 / sim.M_T
    posted = sim.LIMITS["posted (OSM maxspeed)"]
    cap60 = sim.LIMITS["curves + 60 mph cap"]
    nocap = sim.terminal(sim.train_clear(np.minimum(sim.curve, vmax)))
    print(f"{name}  ({sim.M_T:.0f} t, {kw_t:.1f} kW/t)")
    for k, p in pats.items():
        print(f"  {k:16} posted {sim.trip_time(posted, p):5.1f}   60cap {sim.trip_time(cap60, p):5.1f}   nocap {sim.trip_time(nocap, p):5.1f}")
