# `tests` — what is checked and why

```bash
pytest          # 106 tests, about two minutes
```

| File | Covers |
|---|---|
| [`conftest.py`](conftest.py) | Shared fixtures: one small dry-air case, one small vacuum case |
| [`test_psychrometrics.py`](test_psychrometrics.py) | Saturation pressures, round-trip conversions, conventions |
| [`test_mass_balance.py`](test_mass_balance.py) | Global water conservation in the dry-air engine |
| [`test_air_model.py`](test_air_model.py) | Dry-air physical trends and the acceptance rule |
| [`test_trapped_water.py`](test_trapped_water.py) | The second water inventory, multi-target evaluation, reference pressures |
| [`test_vacuum_model.py`](test_vacuum_model.py) | Pump curves, conservation, energy balance, soak sequence |
| [`test_economics.py`](test_economics.py) | Compressor power, cost arithmetic, unpriceable campaigns |

## What these tests are for

They establish that the code **solves the equations it claims to solve**, and
that those equations behave sensibly. They do not establish that the equations
describe a real campaign — nothing here is validated against field data.

Three kinds of check, in descending order of value:

1. **Against known truths.** A dry pull-down must follow
   `p(t) = p₀·exp(−S·t/V)`; saturation pressure at −20 °C must be 103 Pa; a
   pump curve must reproduce its own tabulated points. These would catch a
   wrong implementation, not merely a changed one.
2. **Conservation.** Water in equals water out plus water stored, to
   round-off; stored enthalpy equals heat in minus latent heat out.
3. **Trends.** More flow dries faster, more water takes longer, a stricter
   target is never quicker. Weaker, but they catch sign errors and broken
   couplings.

There are deliberately **no golden-output tests** — no "this case took 71.0
hours last time". Such tests fail on every legitimate improvement and pass
through shared misconceptions.

## Fixtures

`make_small_case` and `make_small_vacuum_case` build short pipelines (200–500 m)
that dry in tens of hours of simulated time and a few seconds of real time.
Every parameter is overridable, so a test that cares about one effect changes
one argument.

`test_trapped_water.py` uses a coarser grid and a thinner film than the shared
fixture: the physics under test is identical and the file runs in a third of
the time.

## When a test fails

Check whether it is asserting a **truth** or a **trend**. A conservation or
analytic-solution failure is a real bug. A trend failure may mean the trend is
genuinely not monotonic — which is how the non-monotonic behaviour of the
trapped-water release rate was found: time to target is not monotonic in it,
and the test asserting otherwise was wrong, not the code.
