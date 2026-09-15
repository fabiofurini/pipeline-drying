# Pipeline Drying Simulator

*[Italiano](README.it.md)*

A physics-based simulator for drying a pipeline after hydrostatic testing. It
covers both processes used industrially — **dry-air convection** and **vacuum**
— and answers the question a campaign is actually planned around: how long will
this take, and what will it cost?

> **Research prototype.** The conservation properties are verified to round-off
> and the trends behave sensibly, but **nothing here is calibrated against
> measured data**. Treat the outputs as physically consistent scenarios, not
> predictions. See [assumptions](docs/assumptions.md).

## Quick start

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                              # 106 tests, ~2 minutes
streamlit run app/streamlit_app.py  # interactive interface, English / Italian
```

From code:

```python
from pipeline_drying import (AirDryingCaseConfig, run_air_drying,
                             CostModel, air_campaign_cost)

cfg = AirDryingCaseConfig.from_yaml("examples/literature_air.yaml")
res = run_air_drying(cfg)

print(res.time_to_target_s / 3600)       # hours to the main target
print(res.additional_target_times_s)     # other targets, same single solve

cost = air_campaign_cost(cfg, res, CostModel(energy_cost_per_kwh=0.25,
                                             rental_cost_per_hour=150.0))
print(cost.total_cost, cost.energy_kwh)
```

## What it does

- **Dry-air engine** — 1-D finite volume, advection plus wall evaporation with a
  Sherwood closure, fixed wall temperature. Residual water is split between the
  wall film and water trapped in poorly-swept locations.
- **Vacuum engine** — lumped mass *and energy* balances, tabulated pump curves
  with boosters, latent heat and freezing, draw-down/soak acceptance.
- **Campaign economics** — compressor and pump power, energy and rental cost, so
  acceptance targets can be compared on cost and not only on duration.
- **Acceptance conventions made explicit** — the target's reference pressure,
  the dryer's reference pressure, and the water/ice phase convention. Each is
  worth more campaign time than most equipment choices.

## Three things the model says

**Where the water is matters more than how much there is.** Moving 15% of the
same residual water into poorly-swept locations lengthens a campaign from 71 to
112 hours without adding a gram.

**A line can pass its acceptance test while still wet.** Water that releases
slowly enough never lifts the outlet reading far enough to register. In one
simulated case −20 °C was met with 73% of the trapped inventory still present.
The engine warns when this happens.

**The definition is worth more than the equipment.** Reading the same −30 °C at
atmospheric pressure instead of line pressure changes a campaign from 130 to 87
hours — a third of the work, decided by how the specification is written.

## Documentation

| | |
|---|---|
| [Documentation index](docs/README.md) | Equations, closures, assumptions, one topic per page |
| [Package layout](src/pipeline_drying/README.md) | What each source file does and how a run flows through them |
| [Web interface](app/README.md) | The Streamlit page and how it is translated |
| [Tests](tests/README.md) | What is checked, and what the tests deliberately do not establish |
| [Examples](examples/README.md) | The two ready-to-run configurations |

Start with [assumptions](docs/assumptions.md) if you are deciding whether to
trust a number, and [verification](docs/verification.md) if you are deciding
whether to trust the code.

## Not implemented

Hybrid dry-air/vacuum sequencing; calibration against measured campaigns; an
optimisation layer over flow, pressure and equipment choice; and a 1-D vacuum
PDE with an axial pressure gradient — which is the main reason the vacuum
engine must not be extrapolated to long pipelines.

## References

- Crivellini et al. (2013), *Development and validation of a model for the
  simulation of the air drying phenomena in pipelines*, IJMMNO 4(4), 351-373.
  [doi:10.1504/IJMMNO.2013.059203](https://doi.org/10.1504/IJMMNO.2013.059203)
- He & Li (2020), *Modeling and simulation of the drying process of natural gas
  pipeline using vacuum drying method*, Drying Technology 38(8), 963-974.
  [doi:10.1080/07373937.2019.1604541](https://doi.org/10.1080/07373937.2019.1604541)
- Ahmed, Gandhidasan & Al-Farayedhi (1998), *Pipeline drying using dehumidified
  air with low dew point temperature*, Applied Thermal Engineering 18(5),
  231-244. [doi:10.1016/S1359-4311(97)00083-5](https://doi.org/10.1016/S1359-4311(97)00083-5)
- Paul (1962), *Compilation of Evaporation Coefficients*, ARS Journal 32(9),
  1321-1328. [doi:10.2514/8.6277](https://doi.org/10.2514/8.6277)
- Saturation-pressure correlations: WMO-No. 8, Annex 4.B.

## Licence

MIT — see [LICENSE](LICENSE).
