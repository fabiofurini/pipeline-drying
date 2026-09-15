# `numerics` — discretisation and time stepping

Kept separate from the physics so both engines share one implementation, and so
a numerical change can be reviewed without reading any thermodynamics.

## `finite_volume.py`

`upwind_advection_rate` — net advective rate of change per cell for a scalar
carried by a flow. First-order upwind: each cell looks only at its upstream
neighbour, the first cell looks at the inlet. Enough for this problem, which has
no shocks.

## `integration.py`

Thin wrappers over `scipy.integrate.solve_ivp`, with defaults that suit these
systems.

- `integrate` — one shot from t0 to t1. BDF by default: the evaporation source
  term is stiff (evaporation is near-instant, drying takes days).
- `integrate_segment` — one operating segment, optionally stopping at a terminal
  event. This is what lets the vacuum engine stitch pumping and soak phases
  together and know which one ended it (`sol.status == 1` means the event
  fired).
- `sample_segment` — uniformly resample a segment's dense output.
- `first_hold_crossing_time` — the earliest t₀ such that a scalar stays below a
  target for the whole hold window. This is the acceptance rule: touching the
  target is not enough, it has to stay there.

Tolerances are per-variable where the scales differ by orders of magnitude —
the vacuum state mixes kilograms, kelvin and joules in one vector.
