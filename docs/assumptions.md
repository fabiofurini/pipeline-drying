# Assumptions

[← Documentation index](README.md)

Every assumption in the model, ranked by how much it would change an answer.
The per-topic pages carry the same entries in context.

## Ranked by impact

| Assumption | Where | Impact if wrong |
|---|---|---|
| **Nothing is calibrated against measured data** | everywhere | **largest** — residual-water quantity and split, `k_m` and `U` are all estimates |
| V1 — no axial pressure gradient in vacuum | [vacuum](vacuum-engine.md) | **large** on long lines: the dominant physical penalty is absent |
| A4 / A5 — trapped water uniform, same potential but slower | [dry air](dry-air-engine.md) | **large** — sets the length of the drying tail, hence the cost of a stricter target |
| A1 — fixed wall temperature | [dry air](dry-air-engine.md) | moderate — no evaporative cooling |
| A3 — uniform film over the perimeter | [dry air](dry-air-engine.md) | moderate — overestimates effective area |
| V6 / V7 — no fusion heat, no ice cₚ | [vacuum](vacuum-engine.md) | moderate below 0 °C, conservative direction |
| A7 — smooth-pipe Sherwood correlation | [dry air](dry-air-engine.md) | moderate — absorbed by `mass_transfer_multiplier` |
| A2 — uniform total pressure | [dry air](dry-air-engine.md) | small at usual flows |
| E1–E4 — cost idealisations | [economics](economics.md) | small on comparisons, larger on absolute cost |
| P1–P5 — ideal gas, correlation fits | [psychrometrics](psychrometrics.md) | small in this operating range |
| A6 — first-order upwind | [numerics](numerics.md) | small; grid-independent 20 → 100 cells |
| A9 / V10 — liquid volume ignored | both engines | negligible |

## The calibration gap

The model is physically consistent and its conservation properties hold to
round-off. But the quantities that most affect its answers are estimates, not
measurements:

- how much residual water remains after dewatering;
- how it is split between wall film and poorly-swept locations;
- how fast the trapped fraction gives itself up;
- the effective mass-transfer and heat-transfer coefficients.

Treat outputs as **physically consistent scenarios, not predictions**. Turning
this into a prediction tool needs one or two completed campaigns: geometry,
equipment, and a coarse time series of flow, pressure, temperature and measured
dew point. Calibrate on one subset, report errors on held-out cases.

## What is deliberately not modelled

| Not modelled | Why | Where it would go |
|---|---|---|
| Axial pressure gradient under vacuum | lumped model by design | a 1-D vacuum PDE |
| Elevation profile and localised low points | no bathymetry input | `geometry.py` has the field |
| Wall/gas/liquid energy balance for dry air | staged fidelity | second fidelity level of the dry-air engine |
| Hybrid dry-air → vacuum sequencing | both engines exist, orchestration does not | a hybrid engine |
| Trapped water in the vacuum engine | added to dry air first | same treatment, vacuum side |
| Heat of fusion on freezing | needs a frozen-fraction state | vacuum energy balance |

**See also:** [Verification](verification.md)
