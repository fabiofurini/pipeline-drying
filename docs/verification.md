# Verification

[← Documentation index](README.md)

106 automated tests. The ones that matter check against known truths — analytic
solutions, conservation laws, published values — not against previous outputs of
this same code.

```bash
pytest          # about two minutes
```

## Conservation

| Check | What it pins down | Result |
|---|---|---|
| Water inventory closes | nothing created or destroyed, across film, trapped, vapour and removed | < 3e-15 relative (vacuum) |
| Energy balance closes | stored enthalpy = external heat in − latent heat out | < 5e-13 relative |
| Liquid never meaningfully negative | the inventory limiter works | within numerical floor |

## Against analytic solutions

| Check | What it pins down | Result |
|---|---|---|
| Dry pull-down vs `p(t) = p₀·exp(−S·t/V)` | pump/volume coupling, independent of any water physics | within 1e-4 relative |
| Saturation pressures at −20 / −30 °C | psychrometric kernel against published values | 103 / 38 Pa |
| Dew and frost point round-trips | inverse conversions | exact to 1e-6 °C |
| Pump curve reproduces its own tabulated points | interpolation | exact |
| Schrage factor 2f/(2−f) | evaporation closure algebra | exact |

## Numerical independence

| Check | Result |
|---|---|
| Grid independence, 20 → 100 cells | 71.0 h in every case |
| Both evaporation closures, pump-limited regime | agree within 1% |

## Physical trends

All of these are asserted, not assumed:

- more dry-air flow dries faster; more pumps dry faster;
- more residual water takes longer;
- a stricter target is never reached sooner;
- throttling mass transfer slows the campaign;
- with no heat supply and a heavy film, the line freezes and warns;
- a large heat supply keeps the line isothermal;
- no water means no cooling at all;
- a soak started with liquid remaining shows a pressure rebound.

## Regression guards

- `trapped_fraction = 0` reproduces the single-film model exactly — the
  backwards-compatibility check for the second inventory;
- additional acceptance targets computed from one solve agree exactly with
  separate runs;
- a target below the dryer's dew point is reported as unreachable, not as a
  horizon that was too short;
- a stalled draw-down/soak cycle terminates instead of burning the horizon.

## What the tests do *not* establish

None of this is validation against field data. The tests establish that the
code solves the equations it claims to solve, and that those equations behave
sensibly. Whether the equations describe a real pipeline campaign is
[an open question](assumptions.md#the-calibration-gap).
