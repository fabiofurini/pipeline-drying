import numpy as np
import pytest

from pipeline_drying import psychrometrics as psy


def test_ice_saturation_pressure_sanity_check():
    # Reference values: ~1.03 mbar at -20 C, ~0.38 mbar at -30 C (103 / 38 Pa).
    p20 = psy.p_sat_ice_pa(-20.0)
    p30 = psy.p_sat_ice_pa(-30.0)
    assert p20 == pytest.approx(103.0, rel=0.01)
    assert p30 == pytest.approx(38.0, rel=0.03)


def test_minus_30_is_about_37_percent_of_minus_20():
    p20 = psy.p_sat_ice_pa(-20.0)
    p30 = psy.p_sat_ice_pa(-30.0)
    assert p30 / p20 == pytest.approx(0.37, abs=0.01)


def test_saturation_pressure_monotonic_increasing_in_temperature():
    t = np.linspace(-60.0, -1.0, 50)
    p = psy.p_sat_ice_pa(t)
    assert np.all(np.diff(p) > 0)

    t = np.linspace(1.0, 60.0, 50)
    p = psy.p_sat_water_pa(t)
    assert np.all(np.diff(p) > 0)


@pytest.mark.parametrize("t_c", [-40.0, -20.0, -5.0, -0.5])
def test_frost_point_round_trip(t_c):
    pw = psy.p_sat_ice_pa(t_c)
    assert psy.frost_point_c(pw) == pytest.approx(t_c, abs=1e-6)


@pytest.mark.parametrize("t_c", [0.5, 10.0, 25.0, 40.0])
def test_dew_point_round_trip(t_c):
    pw = psy.p_sat_water_pa(t_c)
    assert psy.dew_point_c(pw) == pytest.approx(t_c, abs=1e-6)


def test_dew_or_frost_point_picks_ice_below_zero():
    pw = psy.p_sat_ice_pa(-25.0)
    result = psy.dew_or_frost_point_c(pw)
    assert result["primary_c"] == pytest.approx(result["frost_point_c"], abs=1e-9)
    assert result["primary_c"] < 0.0


def test_dew_or_frost_point_picks_water_above_zero():
    pw = psy.p_sat_water_pa(20.0)
    result = psy.dew_or_frost_point_c(pw)
    assert result["primary_c"] == pytest.approx(result["dew_point_c"], abs=1e-9)
    assert result["primary_c"] > 0.0


def test_target_saturation_pressure_auto_convention():
    assert psy.target_saturation_pressure_pa(-20.0, "auto") == pytest.approx(
        psy.p_sat_ice_pa(-20.0)
    )
    assert psy.target_saturation_pressure_pa(20.0, "auto") == pytest.approx(
        psy.p_sat_water_pa(20.0)
    )


@pytest.mark.parametrize("w", [1e-5, 1e-3, 1e-2, 0.1])
def test_humidity_ratio_round_trip(w):
    p_total = 3.0e5
    pw = psy.pw_from_humidity_ratio(w, p_total)
    w_back = psy.humidity_ratio_from_pw(pw, p_total)
    assert w_back == pytest.approx(w, rel=1e-9)


@pytest.mark.parametrize("y", [1e-6, 1e-4, 1e-2, 0.05])
def test_mass_fraction_round_trip(y):
    p_total = 5.0e5
    pw = psy.pw_from_mass_fraction(y, p_total)
    y_back = psy.mass_fraction_from_pw(pw, p_total)
    assert y_back == pytest.approx(y, rel=1e-9)


def test_vapor_density_scales_with_pressure():
    t_k = 293.15
    rho_low = psy.vapor_density_kg_m3(500.0, t_k)
    rho_high = psy.vapor_density_kg_m3(1000.0, t_k)
    assert rho_high == pytest.approx(2.0 * rho_low, rel=1e-9)


def test_gas_density_close_to_dry_air_ideal_gas_law():
    p_total, t_k = 101325.0, 288.15
    rho = psy.gas_density_kg_m3(p_total, t_k, y=0.0)
    expected = p_total * psy.M_AIR / (psy.R_GAS * t_k)
    assert rho == pytest.approx(expected, rel=1e-9)
