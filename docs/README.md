# Documentation

How the simulator works, one topic per page.

## Start here

| Page | What it covers |
|---|---|
| [Notation and units](notation.md) | Symbols, units, and the SI-inside convention |
| [Psychrometric kernel](psychrometrics.md) | How water and air relate; the dew-point / frost-point ambiguity |

## The two engines

| Page | What it covers |
|---|---|
| [Dry-air engine](dry-air-engine.md) | 1-D mass balance, Sherwood closure, the two water inventories, acceptance rule |
| [Vacuum engine](vacuum-engine.md) | Lumped mass and energy balances, pump curves, evaporation closures, soak test |

## Around the engines

| Page | What it covers |
|---|---|
| [Campaign economics](economics.md) | Compressor and pump power, energy and cost |
| [Numerics](numerics.md) | Discretisation, stiff integration, events |

## Before you trust a number

| Page | What it covers |
|---|---|
| [Assumptions](assumptions.md) | Every assumption, ranked by how much it would change an answer |
| [Verification](verification.md) | What the 106 tests actually pin down |

---

For the package layout and what each source file does, see
[`../src/pipeline_drying/README.md`](../src/pipeline_drying/README.md).
