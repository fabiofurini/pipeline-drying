# Numerics

[← Documentation index](README.md) · source: [`numerics/`](../src/pipeline_drying/numerics/)

Kept separate from the physics so both engines share one implementation, and so
a numerical change can be reviewed without reading any thermodynamics.

## Why the systems are stiff

Evaporation is near-instantaneous; drying takes days. An explicit method would
need time steps set by the fastest process and run for the duration of the
slowest. Both engines therefore integrate with **BDF**
(`scipy.integrate.solve_ivp`), with dense output on.

Absolute tolerances are set per variable where scales differ by orders of
magnitude — the vacuum state vector mixes kilograms, kelvin and joules.

## `finite_volume.py`

`upwind_advection_rate` — the net advective rate of change per cell for a
scalar carried by a flow. First-order upwind: each cell looks only at its
upstream neighbour, the first looks at the inlet value. Adequate here because
the system has no shocks; verified grid-independent from 20 to 100 cells.

## `integration.py`

| Function | Purpose |
|---|---|
| `integrate` | one shot from t₀ to t₁ |
| `integrate_segment` | one operating segment, optionally stopping at a terminal event; `sol.status == 1` means the event fired |
| `sample_segment` | uniformly resample a segment's dense output |
| `first_hold_crossing_time` | earliest t₀ such that a scalar stays below a target for the whole hold window |

`integrate_segment` is what lets the vacuum engine stitch pumping and soak
phases together and know which one ended each segment. Because events are
located by root-finding on the dense solution, a pumping phase stops exactly
when its criterion is met, not at the nearest sampling point.

`first_hold_crossing_time` is the acceptance rule in code: touching the target
is not enough, it has to stay there. Evaluating it for several targets on the
same dense solution is why comparing −20 / −30 / −50 °C costs one solve.

## A dead end worth recording

A `jac_sparsity` hint was implemented and removed. The sparsity pattern was
correct — upwind advection couples each cell only to its upstream neighbour,
and inventories couple only to their own cell — and it did speed up small
cases.

It fails on large ones: for most of a campaign the evaporation rate barely
depends on the inventory feeding it, so ∂(rate)/∂(inventory) ≈ 0, and
grouped-column numerical differencing overflows searching for a non-zero
difference. The comment in `air_1d.py` says so, to stop it being re-added.

Comparing several acceptance targets costs one solve anyway, so the speed-up
was not needed.

**See also:** [Verification](verification.md)
