# Dry-air engine

[← Documentation index](README.md) · source: [`models/air_1d.py`](../src/pipeline_drying/models/air_1d.py)

Very dry air is blown through the line. Its low vapour partial pressure pulls
water off the wall, and the stream carries it out.

The pipe is divided into N equal cells. Each carries a gas vapour fraction and
two liquid inventories.

## Governing equations

```
d(M_g,i · Y_i)/dt = ṁ · (Y_{i−1} − Y_i) + E_film,i + E_trap,i        (1)
dm_film,i/dt      = −E_film,i                                        (2)
dm_trap,i/dt      = −E_trap,i                                        (3)
```

`M_g,i = ρ_g(Y_i)·V_i` is the gas held in cell i. `Y_0`, upstream of the first
cell, is the dryer outlet. The advective term is first-order upwind: each cell
sees only its upstream neighbour.

## Evaporation closure

```
E_film,i = k_m · A_i · [ρ_sat(T_wall) − ρ_v,i] · λ(m_film,i)          (4)
E_trap,i = f · k_m · A_i · [ρ_sat(T_wall) − ρ_v,i] · λ(m_trap,i)      (5)
```

with `f = trapped_transfer_ratio ≪ 1`, and the limiter

```
λ(m) = m⁺/(m⁺ + ε),    m⁺ = max(m, 0),    ε = 1e-6 · m(0)
```

which throttles evaporation smoothly as an inventory empties. Condensation — a
negative driving potential — is deliberately **not** limited: a cell can always
take water back out of the gas.

## Mass-transfer coefficient

```
Re = ρ_g·u·d/μ,    Sc = μ/(ρ_g·D),    u = ṁ/(ρ_g·A)

Sh = 0.023 · Re^0.83 · Sc^(1/3)      Re > 2300   (Colburn analogy)
Sh = 3.66                            otherwise   (laminar plateau)

k_m = Sh · D / d
```

μ from Sutherland's law. In words: the faster the air runs, the more
effectively it strips moisture off the wall.

## Why two liquid inventories

This is the part that changed the model's conclusions.

A **uniform film empties everywhere at once**. The outlet stays flat while it
lasts, then collapses to the supply dew point within minutes. Every acceptance
target is crossed during that collapse, so −20 °C and −50 °C come out costing
the same time — which is not what happens on site.

Water in low points, valve cavities and dead legs offers far less interfacial
area per kilogram and sits in poorly-swept gas. Equation (5) gives it the same
driving potential and a much smaller coefficient. It holds the outlet on a
slowly falling plateau: **the drying tail**, and the reason a stricter target
costs real time.

Two parameters control it, and both are calibration targets:
`trapped_fraction` (how much) and `trapped_transfer_ratio` (how slowly).

> **A counter-intuitive consequence.** Time to target is *not* monotonic in the
> release rate. Water slow enough to go unnoticed at the outlet lets a loose
> target be reached *sooner* — while the water is still in the line. In one
> simulated case −20 °C was met with 73% of the trapped inventory remaining.
> The engine raises a warning when this happens.

`trapped_fraction = 0` removes equation (3) from the state vector entirely,
rather than setting it to zero: an identically-constant block sends the
solver's numerical Jacobian estimate into overflow.

## Acceptance

Not "the outlet touched the value" but "it stayed there":

```
find the earliest t₀ with  T_dew(t) ≤ T_target  for all t ∈ [t₀, t₀ + hold]
```

A target quoted at a reference pressure is first referred to line pressure:

```
p_v,target(line) = p_sat(T_target) · p_line / p_reference             (6)
```

At 5 bar that factor is nearly 5 — which is why the reference pressure is worth
more campaign time than most equipment choices.

Several targets are evaluated from **one** solve (`additional_target_times_s`):
a target is a crossing of the outlet curve, not a separate campaign.

## Warnings raised here

- **target below the dryer's own dew point** — unreachable at any flow and any
  duration; only a drier dryer fixes it;
- **accepted with trapped water still in the line** — the line can pass its test
  while still wet.

## Assumptions

| # | Assumption | Consequence if wrong |
|---|---|---|
| A1 | Wall and gas temperature fixed and uniform | no evaporative cooling; times optimistic where gas is cold |
| A2 | Total pressure uniform along the line | no pressure-drop effect on density or residence time |
| A3 | Film uniform over the wetted perimeter | real films drain downward; effective area overestimated |
| A4 | Trapped water uniformly distributed axially | real low points are localised; changes the axial picture, not the trend |
| A5 | Trapped water sees the same potential, only slower | a pool in dead gas may be limited differently |
| A6 | First-order upwind advection | numerical diffusion; verified grid-independent 20 → 100 cells |
| A7 | Smooth-pipe Sherwood correlation | roughness and fittings absorbed into `mass_transfer_multiplier` |
| A8 | No axial dispersion or back-diffusion | fine at these velocities |
| A9 | Liquid volume ignored in gas volume | < 0.1% for realistic films |

**See also:** [Assumptions, ranked](assumptions.md) · [Numerics](numerics.md)
