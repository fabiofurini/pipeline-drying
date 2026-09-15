# Psychrometric kernel

[← Documentation index](README.md) · source: [`psychrometrics.py`](../src/pipeline_drying/psychrometrics.py)

The one module that knows how water and air relate. Everything else depends on
it; it depends on nothing.

## Saturation pressure

Magnus form, as recommended in WMO-No. 8 Annex 4.B:

```
over liquid water    p_sat(T) = 611.21 · exp[ 17.502·T / (240.97 + T) ]
over ice             p_sat(T) = 611.15 · exp[ 22.452·T / (272.55 + T) ]
```

T in °C, p_sat in Pa. Inverting either gives dew point or frost point from a
vapour pressure.

## The ambiguity below 0 °C

Both curves are defined below freezing and they disagree. Air holding 18.76 Pa
of vapour is **−40 °C on the water curve** and **−36.6 °C on the ice curve** —
the same gas, two correct numbers.

The code never picks silently:

- `dew_or_frost_point_c(p_v)` returns both, plus the physically correct one
  (ice below 0 °C);
- `p_sat_pa(T, convention)` takes the choice as an argument;
- the dryer rating carries its own `inlet_convention`, because datasheets
  rarely say which curve they used.

This is not pedantry. An early result reading "−36.6 °C final outlet" from a
dryer rated −40 °C looked like a performance shortfall and was purely a
convention mismatch.

## Composition

```
w   = 0.622 · p_v / (p − p_v)          humidity ratio
Y   = w / (1 + w)                       mass fraction
ρ_v = p_v · M_water / (R·T)
ρ_g = p · M_mix / (R·T)                 M_mix from the vapour mole fraction
```

0.622 is the ratio of molar masses, M_water / M_air.

## Latent heat

```
vaporisation    h_fg(T) = 2.501e6 − 2369.2·T          J/kg, T in °C
sublimation     h_sg    = 2.501e6 + 0.3337e6          J/kg
effective       h_lat(T) = h_sg if T ≤ 0 °C else h_fg(T)
```

The switch at 0 °C is what lets the vacuum engine follow a film through
freezing instead of extrapolating past it.

## Diffusivity

Fuller-type scaling from 2.5e-5 m²/s at 298.15 K, 101325 Pa:

```
D(T, p) = 2.5e-5 · (T/298.15)^1.75 · (101325/p)
```

The `1/p` matters: as a line is evacuated, diffusion gets *faster*. Mass
transfer is therefore not the bottleneck at low pressure — the pump is.

## Assumptions

| # | Assumption | Why acceptable | When it breaks |
|---|---|---|---|
| P1 | Ideal gas for air and vapour | ≤ 0.1% below 10 bar here | well above 50 bar |
| P2 | Magnus fits exact | within 0.1% over −60…+60 °C | outside that range |
| P3 | Latent heat linear in T | within 0.5% over 0…100 °C | not used outside it |
| P4 | Sublimation enthalpy constant | residual T-dependence < 2% | very cold campaigns |
| P5 | Dalton's law | dilute vapour in air | near-saturated high-pressure gas |

**Next:** [Dry-air engine →](dry-air-engine.md) · [Vacuum engine →](vacuum-engine.md)
