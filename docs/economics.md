# Campaign economics

[← Documentation index](README.md) · source: [`economics.py`](../src/pipeline_drying/economics.py)

Turns a simulated duration into the numbers a campaign is judged on. This is
the evaluation function an optimisation layer would sit on top of, and it is
what lets a −20 / −30 / −50 °C comparison show *why* over-drying is expensive
rather than merely slower.

Everything here is deliberately simple and explicit: powers come from first
principles or from nameplate figures the user supplies, and tariffs are pure
inputs. Nothing is hidden in a correlation.

## Compressor power

Multi-stage compression with perfect intercooling back to inlet temperature:

```
P_comp = n · ṁ · L / η

  L = (k/(k−1)) · (R/M) · T · [ r^((k−1)/k) − 1 ]
  r = (p₂/p₁)^(1/n)                 pressure ratio per stage
```

k = 1.4 for air, η the combined isentropic and mechanical efficiency, n the
number of intercooled stages. Staging reduces the duty because each stage
returns to inlet temperature; the isothermal result is the floor it approaches.

Typical output: 0.1 kg/s (≈ 280 Nm³/h) to 5 bar in two stages ≈ 21.6 kW.

## Dryer and pumps

```
P_dryer = (Nm³/h)/1000 · e_dryer
P_vac   = n_pumps·P_pump + n_boosters·P_booster
```

`e_dryer` comes from the dryer datasheet and defaults to **zero** — it varies by
an order of magnitude between heatless, heated and blower-purge units, and a
silent guess would be worse than an obvious omission.

Vacuum pumps are charged at nameplate shaft power for the whole campaign: a fair
approximation for positive-displacement machines, whose power draw is dominated
by friction and varies far less with suction pressure than their capacity does.

## Cost

```
cost = energy · energy_price + hours · rental_rate
```

A campaign that never reaches its target returns `reached_target = False`
rather than a number. An unfinished campaign cannot be priced.

## A non-obvious consequence

Doubling the air flow halves the hours but doubles the power, so the **energy is
roughly unchanged** and only the rental bill falls. Whether more flow is worth
paying for depends entirely on the ratio of rental rate to energy tariff —
precisely the trade-off an optimisation layer would settle, and precisely the
input that is hardest to get.

## Assumptions

| # | Assumption | Consequence if wrong |
|---|---|---|
| E1 | Perfect intercooling between stages | power slightly optimistic |
| E2 | Single constant efficiency, no part-load curve | fine at a fixed operating point |
| E3 | Constant duty for the whole campaign | no ramp-up, no idle periods |
| E4 | Flat tariffs and rental | no time-of-day pricing, no mobilisation cost |

**See also:** [Assumptions, ranked](assumptions.md)
