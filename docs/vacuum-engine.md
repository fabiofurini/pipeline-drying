# Vacuum engine

[← Documentation index](README.md) · source: [`models/vacuum_lumped.py`](../src/pipeline_drying/models/vacuum_lumped.py)

The line is isolated and evacuated. As pressure falls, residual water boils off
and the pumps remove the vapour. Unlike dry-air drying, this is inseparable
from heat: evaporation cools the line, and cooling shuts evaporation down.

One control volume, four physical states plus cumulative diagnostics.

## Governing equations

```
dm_a/dt = −m_a · S(p)/V                                              (1)
dm_v/dt = E − m_v · S(p)/V                                           (2)
dm_w/dt = −E                                                         (3)
C · dT/dt = −E · h_lat(T) + U·A_ext·(T_ext − T)                      (4)

p   = [m_a/M_air + m_v/M_water] · R·T / V                            (5)
p_v = (m_v/M_water) · R·T / V
```

A volumetric pump removes the mixture *at its own composition*, which is why
each species leaves in proportion to its own inventory — the `m·S(p)/V` form in
(1) and (2).

## Pump capacity

`S(p)` is tabulated from the manufacturer curve and interpolated **linearly in
log p** — the way such a curve is read off a log-scaled datasheet plot — and
held flat outside the tabulated range.

Near the blank-off pressure a smooth derating takes capacity to zero:

```
φ = ξ²/(1 + ξ²),    ξ = max(p − p_ult, 0)/p_ult
```

A hard cut-off would put a discontinuity in the right-hand side. For the same
reason a booster train, which replaces the backing pumps below its activation
pressure, is blended in with a sigmoid in log p rather than switched.

## Evaporation closures

```
equilibrium      E = k_m · A · [ρ_sat(T) − ρ_v],   k_m = 3.66·D(T,p)/d     (6)
Hertz–Knudsen    E = (2f/(2−f)) · A · √[M_w/(2πRT)] · [p_sat(T) − p_v]     (7)
```

(6) uses the laminar Sherwood plateau: gas in an isolated line is nearly
stagnant. (7) is the Schrage form used by He & Li (2020), with evaporation
coefficient f = 0.02–0.04 (Paul, 1962); the default is 0.03.

**They agree to within 1%** whenever pumping is the bottleneck, which is the
normal regime — 2.22 h against 2.20 h on the reference case. The closure only
matters if f is starved four orders of magnitude below the published range.
Practically: f need not be calibrated while the campaign is pump-limited, which
removes an uncertain parameter from the calibration problem.

## The energy balance is the limiter

No heuristic cap is placed on E. Runaway evaporation cools the line, collapses
p_sat(T), and shuts its own driving force down. That self-limiting behaviour is
the physical heart of vacuum drying, and it is why (4) is mandatory here while
the dry-air engine can defer an energy balance.

`C` is dominated by the steel wall:

```
C = coupling · ρ_steel · (π/4)·(d_out² − d²) · L · c_steel  +  m_w(0)·c_water
```

Below 0 °C the ice curve and the sublimation enthalpy take over automatically,
so freezing is represented rather than extrapolated. With a heavy residual film
and no external heat, the film reaches −3.6 °C and the campaign takes 49%
longer: heat supply, not pump size, is the binding constraint in that regime.

## Acceptance sequence

Completion is the operational procedure, not a pressure reading:

1. **draw down** until `p ≤ γ·p_target` *and* `p_v ≤ γ·p_sat(T_frost target)`,
   where γ = `drawdown_factor` < 1;
2. **isolate** the line (S = 0) for the soak duration;
3. **accept** if the pressure rebound ≤ `max_pressure_rise_mbar` and both
   targets still hold; otherwise pump again and repeat.

The margin γ exists because drawing down to exactly the target always fails the
check that follows — real procedures over-pump for the same reason. Cycles that
stop improving terminate with a warning instead of looping.

## Reporting conventions

Backfilling with dry gas adds moles but no water, so `p_v` is unchanged and only
its mole fraction falls:

```
ppmv at p_ref            = p_v / p_ref · 1e6
atmospheric frost point  = frost_point(p_v · p_atm / p_ref)
```

On the reference case the same residual water reads **−32.1 °C in the line** and
**−46.3 °C atmospheric-equivalent** after backfill to 5 bar. Both are correct; a
specification has to say which it means.

## Assumptions

| # | Assumption | Consequence if wrong |
|---|---|---|
| V1 | **Single control volume — no axial pressure gradient** | the dominant limitation on long lines is absent; do not extrapolate beyond short pipelines |
| V2 | One effective temperature for liquid, wall and gas | no radial or axial thermal gradient |
| V3 | `C` from the initial water mass, held constant | liquid is < 1% of C for realistic films |
| V4 | Gas-phase sensible heat neglected | negligible against steel |
| V5 | Enthalpy leaving with pumped gas neglected | small against latent heat |
| V6 | Heat of fusion on freezing not modelled | cooling below 0 °C predicted conservatively (too fast) |
| V7 | Ice heat capacity not substituted | small, same direction as V6 |
| V8 | Pump power independent of suction pressure | fine for positive-displacement machines; affects cost only |
| V9 | Booster replaces rather than compounds backing pumps | matches how vendors quote combined trains |
| V10 | Liquid volume ignored in V | < 0.1% for realistic films |

> **V1 is the one to remember.** A pump cannot make itself felt at the far end
> of a long line: the far end can sit orders of magnitude above the pump-end
> pressure, so the effective capacity seen by distant water is a fraction of
> the nameplate figure. Dry-air drying has no equivalent penalty. Until a 1-D
> vacuum engine exists, this prototype can compare the two processes on short
> lines and cannot rank them on long ones.

**See also:** [Assumptions, ranked](assumptions.md) · [Numerics](numerics.md)
