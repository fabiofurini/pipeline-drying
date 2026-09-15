# `pipeline_drying` — package layout

What each file does, and why it exists as its own file.

| File | Role |
|---|---|
| [`psychrometrics.py`](psychrometrics.py) | Moist-air properties. Everything else depends on it; it depends on nothing. |
| [`geometry.py`](geometry.py) | Turns a length and a diameter into the per-cell areas and volumes the solvers need. |
| [`equipment.py`](equipment.py) | The two kinds of hardware: a dry-air supply, and vacuum pumps with their capacity curves. |
| [`io_schema.py`](io_schema.py) | Every input the user can set, validated, with human units converted to SI at the boundary. |
| [`models/`](models/) | The two solvers. See [`models/README.md`](models/README.md). |
| [`numerics/`](numerics/) | Discretisation and time integration, shared by both solvers. See [`numerics/README.md`](numerics/README.md). |
| [`economics.py`](economics.py) | Turns a simulated duration into energy and cost. |
| [`reporting.py`](reporting.py) | Results as a table or a text summary. |

## How a run flows through these

```
YAML or UI inputs
      │
      ▼
io_schema.py            validates, converts to SI
      │
      ▼
geometry.py             cell areas, volumes
equipment.py            air supply / pump curve
      │
      ▼
models/air_1d.py   or   models/vacuum_lumped.py
      │                       │
      │  calls psychrometrics.py for every saturation pressure and density
      │  calls numerics/ to advance in time
      ▼
result object  ──►  economics.py   (cost)
               └─►  reporting.py   (table, summary)
```

## `psychrometrics.py`

The one place that knows how water and air relate. Saturation pressure over
liquid water and over ice (Magnus form, WMO-No. 8), the inverse conversions to
dew and frost point, humidity ratio and mass fraction, vapour and mixture
density, binary diffusivity, and the latent heats of vaporisation and
sublimation.

Two things to know when reading it:

- Below 0 °C a vapour pressure has **two** names, one on each curve. Nothing
  here picks for you silently: `dew_or_frost_point_c` returns both plus the
  physically correct one, and `p_sat_pa(t, convention)` makes the choice
  explicit.
- `effective_latent_heat_j_kg` switches to sublimation below 0 °C. The vacuum
  engine relies on this; the dry-air engine never gets there.

## `geometry.py`

`PipelineGrid` is a frozen dataclass: length, diameter, number of cells. It
exposes cell centres, cell volume and wetted area per cell. The elevation field
is present but unused — it is where a low-point profile would go.

## `equipment.py`

`DryAirSupply` converts the dryer's quoted dew point into a vapour partial
pressure. It takes both a phase convention and an optional reference pressure,
because "−40 °C" on a datasheet is ambiguous on both counts and the difference
is worth several degrees.

`VacuumPumpCurve` interpolates a tabulated capacity curve linearly in
log(pressure) — the way such a curve is read off a log-scaled datasheet plot —
and derates smoothly to zero at the blank-off pressure. `VacuumPumpSystem`
combines identical pumps with an optional booster train that takes over below
its activation pressure, blended over a narrow band so the ODE right-hand side
stays smooth.

## `io_schema.py`

Pydantic models, one per input group, plus the two top-level case configs.
Human units (°C, bar, Nm³/h, mm) are accepted here and converted to SI
immediately; nothing downstream sees anything else.

The parameters worth understanding before changing anything:
`trapped_fraction` and `trapped_transfer_ratio` (where the drying tail comes
from), `reference_pressure_bar_a` on both the target and the dryer (the
dew-point convention), and `drawdown_factor` (why a vacuum campaign over-pumps).

## `economics.py`

Compressor shaft power from first principles with intercooled staging, dryer
regeneration energy from its datasheet, vacuum pump power from nameplate
figures. Tariffs are pure inputs. A campaign that never reaches its target
returns `reached_target=False` rather than a number: an unfinished campaign
cannot be priced.

## `reporting.py`

`result_to_dataframe` / `vacuum_result_to_dataframe` for the time series,
`summary_text` / `vacuum_summary_text` for the block shown under the charts and
written into exports.
