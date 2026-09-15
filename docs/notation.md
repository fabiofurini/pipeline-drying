# Notation and units

[← Documentation index](README.md)

| Symbol | Meaning | Unit |
|---|---|---|
| `p`, `p_v` | total pressure, water-vapour partial pressure | Pa |
| `T` | temperature | K (°C where stated) |
| `Y` | vapour mass fraction, m_vapour / m_mixture | – |
| `w` | humidity ratio, m_vapour / m_dry air | – |
| `ρ_v`, `ρ_g` | vapour density, gas mixture density | kg/m³ |
| `ṁ` | dry-air mass flow | kg/s |
| `E` | evaporation rate | kg/s |
| `m_film`, `m_trap` | wall-film and trapped liquid inventories | kg |
| `k_m` | mass-transfer coefficient | m/s |
| `S(p)` | pump volumetric suction capacity | m³/s |
| `A_i`, `V_i` | wetted area, volume of cell i | m², m³ |
| `h_lat` | latent heat | J/kg |
| `C` | effective heat capacity | J/K |
| `Re`, `Sc`, `Sh` | Reynolds, Schmidt, Sherwood numbers | – |

## The unit convention

SI everywhere inside the solvers. Human units — °C, bar, Nm³/h, mm, micron —
are accepted only in `io_schema.py` and converted at the boundary. Nothing
downstream of validation sees anything but SI.

This is deliberate: unit errors in a mixed-unit codebase are silent and
expensive, and the input schema is the one place they can be caught.

**Next:** [Psychrometric kernel →](psychrometrics.md)
