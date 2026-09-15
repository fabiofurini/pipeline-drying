# `models` — the two solvers

Both take a validated config and return a result object. They share the
psychrometric kernel and the time integrator, and nothing else: the physics of
blowing dry air through a pipe and of evacuating one have little in common.

| | [`air_1d.py`](air_1d.py) | [`vacuum_lumped.py`](vacuum_lumped.py) |
|---|---|---|
| Space | 1-D finite volume, N cells | one lumped volume |
| Temperature | fixed input | solved |
| Driver | advection of dry air | pump suction curve S(p) |
| Completion | outlet below target for a hold time | draw down, isolate, soak, pressure-rise test |
| Conserves | water mass | water mass **and** energy |
| Cost | seconds to minutes | under a second |

## `air_1d.py`

Per cell: a vapour mass fraction, a wall-film water inventory, and — when
`trapped_fraction > 0` — a second, slowly-draining inventory.

```
d(M_g,i · Y_i)/dt = ṁ · (Y_{i-1} − Y_i) + E_film,i + E_trap,i
dm_film,i/dt      = −E_film,i
dm_trap,i/dt      = −E_trap,i

E_film,i = k_m · A_i · [ρ_sat(T_wall) − ρ_v,i]
E_trap,i = f · k_m · A_i · [ρ_sat(T_wall) − ρ_v,i]        f ≪ 1
```

`k_m` comes from a Sherwood correlation (laminar plateau 3.66, or Colburn
analogy in turbulent flow). Both evaporation terms are throttled by
`_limited_by_inventory` as their inventory empties, which is what keeps water
from going negative.

**Why two inventories.** A uniform film empties everywhere at once, so the
outlet collapses to the supply dew point within minutes and every acceptance
target is crossed at the same instant — which made −20 °C and −50 °C look
equally cheap. Trapped water instead holds the outlet on a slowly falling
plateau. That plateau is the drying tail, and it is what makes a stricter
target cost real time.

Two warnings are raised here rather than left to the caller: a target below the
dryer's own dew point (unreachable at any flow or duration), and acceptance
reached while a significant trapped inventory remains (the line can pass its
test still wet).

Several acceptance targets are evaluated from one solve —
`additional_target_times_s` — because a target is a crossing of the outlet
curve, not a separate campaign.

A `jac_sparsity` hint was tried and removed: the pattern is correct, but for
most of a campaign the evaporation rate barely depends on the inventory feeding
it, and grouped-column numerical differencing then overflows. The comment in
the source says so, to stop anyone re-adding it.

## `vacuum_lumped.py`

State: dry-air mass, vapour mass, liquid water, one effective temperature, plus
cumulative counters used only as conservation diagnostics.

```
dm_a/dt = −m_a · S(p)/V
dm_v/dt = E − m_v · S(p)/V
dm_w/dt = −E
C · dT/dt = −E · h_lat(T) + U·A·(T_ext − T)

p = [m_a/M_air + m_v/M_water] · R·T/V
```

A volumetric pump draws the mixture at its own composition, which is why each
species leaves in proportion to its own inventory.

Two evaporation closures: an equilibrium/mass-transfer law, and
Hertz–Knudsen–Schrage with the Schrage factor `2f/(2−f)`. They agree whenever
pumping is the bottleneck, which is the normal regime.

**No heuristic cap on evaporation.** The energy balance supplies the limit by
itself: fast evaporation cools the line, collapses p_sat(T) and shuts the
driving force down. Below 0 °C the ice curve and the latent heat of sublimation
take over, so the freezing regime is represented rather than extrapolated.

Completion follows the operational sequence, not a pressure reading: draw down
past the target by `drawdown_factor`, isolate, soak, accept only if the rebound
stays inside tolerance. Failed cycles repeat; cycles that stop making progress
terminate with a warning instead of looping.
