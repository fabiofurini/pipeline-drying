import numpy as np
import pytest

from pipeline_drying import run_air_drying

from conftest import make_small_case


def test_global_mass_conservation():
    cfg = make_small_case()
    result = run_air_drying(cfg)
    assert result.mass_balance_relative_error < 1e-3


def test_liquid_water_never_goes_meaningfully_negative():
    cfg = make_small_case()
    result = run_air_drying(cfg)
    initial_total = result.liquid_water_kg[:, 0].sum()
    # A tiny negative numerical floor is acceptable (smooth ramp limiter);
    # anything more than a fraction of a percent of the initial mass is not.
    assert result.liquid_water_kg.min() > -1e-3 * initial_total


def test_no_mass_transfer_means_no_drying():
    cfg = make_small_case(mass_transfer_multiplier=0.0, max_time_s=3600.0)
    result = run_air_drying(cfg)
    liquid = result.liquid_water_kg
    assert np.allclose(liquid, liquid[:, [0]], rtol=1e-9, atol=1e-12)


def test_no_mass_transfer_outlet_flushes_to_inlet_humidity():
    cfg = make_small_case(mass_transfer_multiplier=0.0, max_time_s=3600.0)
    result = run_air_drying(cfg)
    # Residence time is a few minutes for this geometry/flow; after 1 h the
    # outlet should have flushed almost entirely to the dry-air supply value.
    assert result.outlet_dew_point_c[-1] == pytest.approx(
        cfg.equipment.inlet_dew_point_c, abs=0.5
    )
