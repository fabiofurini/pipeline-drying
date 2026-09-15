# `examples` — ready-to-run configurations

```python
from pipeline_drying import AirDryingCaseConfig, run_air_drying

config = AirDryingCaseConfig.from_yaml("examples/literature_air.yaml")
result = run_air_drying(config)
```

| File | Case |
|---|---|
| [`demo_air.yaml`](demo_air.yaml) | 2 km × 300 mm at 600 Nm³/h — what the web interface opens with |
| [`literature_air.yaml`](literature_air.yaml) | 50 km × 600 mm at 2000 Nm³/h — the case used in the written studies |
| [`literature_vacuum.yaml`](literature_vacuum.yaml) | 2 km × 300 mm, two pumps plus a booster |

`demo_air.yaml` exists for one reason: a visitor's first click has to return a
real answer in a few seconds. The 50 km literature case needs far longer than
its own horizon to dry, so the first thing an unprepared visitor would see is
"not reached". A regression test keeps the demo honest — every comparison
target reached, at visibly different times, comfortably inside the horizon.

## What these numbers are, and are not

They are **plausible engineering values**, chosen to exercise the models and to
sit in the right order of magnitude. Their scale is informed by Ahmed et al.
(1998), Crivellini et al. (2013) and He & Li (2020).

They are **not** digitised from any paper, and not measurements from any asset.
The vacuum pump curve in particular is a generic two-stage rotary-vane shape
with a generic Roots booster — replace it with real manufacturer data before
drawing any operational conclusion.

## Writing your own

Every field is validated by `io_schema.py`, which rejects impossible
combinations with a readable message rather than producing a silently wrong
answer. Human units go here — °C, bar, Nm³/h, mm — and are converted to SI at
the boundary.

The fields worth understanding before changing them:

| Field | Why it matters |
|---|---|
| `initial_water.film_thickness_mm` | the most uncertain input of all |
| `initial_water.trapped_fraction` | at 0 every acceptance target costs the same time |
| `simulation.trapped_transfer_ratio` | sets the length of the drying tail; not monotonic |
| `acceptance.reference_pressure_bar_a` | the dew-point convention; worth a third of the campaign |
| `equipment.inlet_dew_point_c` | a target below it is unreachable at any flow |

See [`docs/assumptions.md`](../docs/assumptions.md) for what the model takes
for granted, and [`docs/dry-air-engine.md`](../docs/dry-air-engine.md) /
[`docs/vacuum-engine.md`](../docs/vacuum-engine.md) for the equations these
inputs feed.
