"""Psychrometric kernel: saturation pressures, dew/frost point, humidity conversions.

All functions use SI units at the module boundary (Pa, K) except where a
function name explicitly says `_c` (degrees Celsius), matching the
convention used throughout this package: pure SI internally, human units
only at input/output edges.

Reference correlations: WMO/Magnus-type formulas for saturation vapour
pressure over liquid water and over ice (see e.g. WMO-No. 8, Annex 4.B).
"""
from __future__ import annotations

import numpy as np

R_GAS = 8.31446  # J/(mol K)
M_WATER = 0.0180153  # kg/mol
M_AIR = 0.0289647  # kg/mol
MOLAR_MASS_RATIO = M_WATER / M_AIR  # ~0.6220, i.e. the "0.622" constant


def p_sat_water_pa(t_c: np.ndarray | float) -> np.ndarray | float:
    """Saturation vapour pressure over liquid water (Pa) from temperature (deg C).

    WMO/Magnus form, valid for t_c >= 0 (extrapolates smoothly below).
    """
    t_c = np.asarray(t_c, dtype=float)
    return 611.21 * np.exp(17.502 * t_c / (240.97 + t_c))


def p_sat_ice_pa(t_c: np.ndarray | float) -> np.ndarray | float:
    """Saturation vapour pressure over ice (Pa) from temperature (deg C).

    WMO/Magnus form, valid for t_c <= 0.
    Reference values: ~103 Pa at -20 C, ~38 Pa at -30 C.
    """
    t_c = np.asarray(t_c, dtype=float)
    return 611.15 * np.exp(22.452 * t_c / (272.55 + t_c))


def dew_point_c(pw_pa: np.ndarray | float) -> np.ndarray | float:
    """Dew point (deg C) from water-vapour partial pressure (Pa), liquid-water convention."""
    pw_pa = np.asarray(pw_pa, dtype=float)
    pw_pa = np.clip(pw_pa, 1e-6, None)
    ln_ratio = np.log(pw_pa / 611.21)
    return 240.97 * ln_ratio / (17.502 - ln_ratio)


def frost_point_c(pw_pa: np.ndarray | float) -> np.ndarray | float:
    """Frost point (deg C) from water-vapour partial pressure (Pa), ice convention."""
    pw_pa = np.asarray(pw_pa, dtype=float)
    pw_pa = np.clip(pw_pa, 1e-6, None)
    ln_ratio = np.log(pw_pa / 611.15)
    return 272.55 * ln_ratio / (22.452 - ln_ratio)


def dew_or_frost_point_c(pw_pa: np.ndarray | float) -> dict:
    """Return both conventions plus the physically-relevant one for the given pressure.

    Below 0 deg C the ice (frost point) convention is the correct equilibrium
    reference; the liquid-water dew point is still reported alongside it
    because field instruments and client specifications do not always state
    which convention was used.
    """
    t_dew = dew_point_c(pw_pa)
    t_frost = frost_point_c(pw_pa)
    primary = np.where(t_frost <= 0.0, t_frost, t_dew)
    return {"dew_point_c": t_dew, "frost_point_c": t_frost, "primary_c": primary}


def target_saturation_pressure_pa(target_c: float, convention: str = "auto") -> float:
    """Saturation pressure (Pa) corresponding to an acceptance target temperature.

    convention: "water" (dew point), "ice" (frost point), or "auto" (ice below
    0 deg C, water otherwise -- the standard meteorological practice).
    """
    if convention == "water":
        return float(p_sat_water_pa(target_c))
    if convention == "ice":
        return float(p_sat_ice_pa(target_c))
    if convention == "auto":
        return float(p_sat_ice_pa(target_c) if target_c <= 0.0 else p_sat_water_pa(target_c))
    raise ValueError(f"Unknown convention: {convention!r}")


def humidity_ratio_from_pw(pw_pa: np.ndarray | float, p_total_pa: np.ndarray | float) -> np.ndarray | float:
    """Humidity ratio w = mass water vapour / mass dry air."""
    pw_pa = np.asarray(pw_pa, dtype=float)
    p_total_pa = np.asarray(p_total_pa, dtype=float)
    denom = np.clip(p_total_pa - pw_pa, 1e-6, None)
    return MOLAR_MASS_RATIO * pw_pa / denom


def pw_from_humidity_ratio(w: np.ndarray | float, p_total_pa: np.ndarray | float) -> np.ndarray | float:
    """Inverse of humidity_ratio_from_pw."""
    w = np.asarray(w, dtype=float)
    p_total_pa = np.asarray(p_total_pa, dtype=float)
    return p_total_pa * w / (MOLAR_MASS_RATIO + w)


def mass_fraction_from_w(w: np.ndarray | float) -> np.ndarray | float:
    """Vapour mass fraction Y = mv / (mv + ma) from humidity ratio w = mv/ma."""
    w = np.asarray(w, dtype=float)
    return w / (1.0 + w)


def w_from_mass_fraction(y: np.ndarray | float) -> np.ndarray | float:
    """Inverse of mass_fraction_from_w."""
    y = np.asarray(y, dtype=float)
    y = np.clip(y, 0.0, 1.0 - 1e-12)
    return y / (1.0 - y)


def pw_from_mass_fraction(y: np.ndarray | float, p_total_pa: np.ndarray | float) -> np.ndarray | float:
    """Vapour partial pressure (Pa) from mass fraction Y and total pressure."""
    return pw_from_humidity_ratio(w_from_mass_fraction(y), p_total_pa)


def mass_fraction_from_pw(pw_pa: np.ndarray | float, p_total_pa: np.ndarray | float) -> np.ndarray | float:
    """Vapour mass fraction Y from partial pressure and total pressure."""
    return mass_fraction_from_w(humidity_ratio_from_pw(pw_pa, p_total_pa))


def vapor_density_kg_m3(pw_pa: np.ndarray | float, t_k: np.ndarray | float) -> np.ndarray | float:
    """Water-vapour partial density (kg/m3) via ideal gas law."""
    pw_pa = np.asarray(pw_pa, dtype=float)
    t_k = np.asarray(t_k, dtype=float)
    return pw_pa * M_WATER / (R_GAS * t_k)


def gas_density_kg_m3(p_total_pa: np.ndarray | float, t_k: np.ndarray | float,
                       y: np.ndarray | float = 0.0) -> np.ndarray | float:
    """Humid-air mixture density (kg/m3) via ideal gas law with an effective molar mass."""
    p_total_pa = np.asarray(p_total_pa, dtype=float)
    t_k = np.asarray(t_k, dtype=float)
    y = np.asarray(y, dtype=float)
    w = w_from_mass_fraction(y)
    x_v = w / MOLAR_MASS_RATIO / (1.0 + w / MOLAR_MASS_RATIO)  # mole fraction of vapour
    m_mix = x_v * M_WATER + (1.0 - x_v) * M_AIR
    return p_total_pa * m_mix / (R_GAS * t_k)


def water_vapor_diffusivity_m2_s(t_k: np.ndarray | float, p_total_pa: np.ndarray | float) -> np.ndarray | float:
    """Binary diffusivity of water vapour in air (m2/s).

    Fuller-type correlation, referenced to 298.15 K / 101325 Pa where
    D_ab ~ 2.5e-5 m2/s, scaled as D ~ T^1.75 / p.
    """
    t_k = np.asarray(t_k, dtype=float)
    p_total_pa = np.asarray(p_total_pa, dtype=float)
    d_ref = 2.5e-5
    return d_ref * (t_k / 298.15) ** 1.75 * (101325.0 / p_total_pa)


def p_sat_pa(t_c: np.ndarray | float, convention: str = "auto") -> np.ndarray | float:
    """Saturation vapour pressure (Pa) with an explicit phase convention.

    "auto" selects the ice curve at or below 0 deg C and the liquid-water
    curve above it, i.e. the physically correct equilibrium reference for a
    film that may freeze -- the situation the vacuum engine has to handle.
    """
    t_c = np.asarray(t_c, dtype=float)
    if convention == "water":
        return p_sat_water_pa(t_c)
    if convention == "ice":
        return p_sat_ice_pa(t_c)
    if convention == "auto":
        return np.where(t_c <= 0.0, p_sat_ice_pa(t_c), p_sat_water_pa(t_c))
    raise ValueError(f"Unknown convention: {convention!r}")


CP_LIQUID_WATER = 4182.0  # J/(kg K)
H_FUSION_J_KG = 0.3337e6  # J/kg, latent heat of fusion at 0 deg C


def latent_heat_vaporization_j_kg(t_c: np.ndarray | float) -> np.ndarray | float:
    """Latent heat of vaporisation of water (J/kg) from temperature (deg C).

    Linear fit to steam-table values, accurate to better than 0.5% between
    0 and 100 deg C.
    """
    t_c = np.asarray(t_c, dtype=float)
    return 2.501e6 - 2369.2 * t_c


def latent_heat_sublimation_j_kg(t_c: np.ndarray | float) -> np.ndarray | float:
    """Latent heat of sublimation of ice (J/kg).

    Taken as vaporisation at 0 deg C plus the heat of fusion; the residual
    temperature dependence below 0 deg C is under 2% and is neglected.
    """
    t_c = np.asarray(t_c, dtype=float)
    return np.full_like(t_c, 2.501e6 + H_FUSION_J_KG)


def effective_latent_heat_j_kg(t_c: np.ndarray | float) -> np.ndarray | float:
    """Latent heat for the phase actually present: sublimation below 0 deg C.

    This matters for vacuum drying, where evaporative cooling can drive the
    film through 0 deg C, which is a real freezing risk.
    """
    t_c = np.asarray(t_c, dtype=float)
    return np.where(t_c <= 0.0, latent_heat_sublimation_j_kg(t_c),
                    latent_heat_vaporization_j_kg(t_c))
