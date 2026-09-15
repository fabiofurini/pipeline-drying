import pytest

from pipeline_drying import run_air_drying, run_vacuum_drying
from pipeline_drying.economics import (
    P_ATM_PA,
    CostModel,
    air_campaign_cost,
    compression_power_kw,
    vacuum_campaign_cost,
)
from pipeline_drying.io_schema import AirDryingCaseConfig, VacuumDryingCaseConfig

from conftest import make_small_case, make_small_vacuum_case


def test_compression_power_rises_with_discharge_pressure():
    p = [compression_power_kw(0.1, P_ATM_PA, bar * 1e5, 293.15, 0.7) for bar in (2, 5, 10, 20)]
    assert all(b > a for a, b in zip(p, p[1:]))


def test_intercooled_staging_reduces_the_duty():
    one = compression_power_kw(0.1, P_ATM_PA, 10e5, 293.15, 0.7, stages=1)
    three = compression_power_kw(0.1, P_ATM_PA, 10e5, 293.15, 0.7, stages=3)
    assert three < one
    # ...but never below the isothermal limit m R T ln(r) / M / eta.
    import numpy as np

    from pipeline_drying import psychrometrics as psy

    isothermal = 0.1 * psy.R_GAS / psy.M_AIR * 293.15 * np.log(10e5 / P_ATM_PA) / 0.7 / 1000
    assert three > isothermal


def test_compression_power_scales_linearly_with_flow():
    a = compression_power_kw(0.05, P_ATM_PA, 5e5, 293.15, 0.7)
    b = compression_power_kw(0.10, P_ATM_PA, 5e5, 293.15, 0.7)
    assert b == pytest.approx(2 * a, rel=1e-12)


def test_no_compression_no_power():
    assert compression_power_kw(0.1, P_ATM_PA, P_ATM_PA, 293.15, 0.7) == 0.0
    assert compression_power_kw(0.0, P_ATM_PA, 5e5, 293.15, 0.7) == 0.0


def test_invalid_efficiency_is_rejected():
    with pytest.raises(ValueError):
        compression_power_kw(0.1, P_ATM_PA, 5e5, 293.15, 0.0)


def test_air_cost_is_energy_plus_rental():
    cfg = make_small_case(target_c=12.0, hold_duration_s=60.0, max_time_s=60 * 3600)
    result = run_air_drying(cfg)
    model = CostModel(energy_cost_per_kwh=0.30, rental_cost_per_hour=50.0)
    cost = air_campaign_cost(cfg, result, model)
    assert cost.reached_target
    assert cost.energy_kwh == pytest.approx(cost.mean_power_kw * cost.duration_h, rel=1e-12)
    assert cost.energy_cost == pytest.approx(cost.energy_kwh * 0.30, rel=1e-12)
    assert cost.rental_cost == pytest.approx(cost.duration_h * 50.0, rel=1e-12)
    assert cost.total_cost == pytest.approx(cost.energy_cost + cost.rental_cost, rel=1e-12)


def test_dryer_regeneration_energy_adds_to_the_bill():
    cfg = make_small_case(target_c=12.0, hold_duration_s=60.0, max_time_s=60 * 3600)
    result = run_air_drying(cfg)
    bare = air_campaign_cost(cfg, result, CostModel())
    with_dryer = air_campaign_cost(
        cfg, result, CostModel(dryer_specific_energy_kwh_per_1000_nm3=5.0)
    )
    assert with_dryer.mean_power_kw > bare.mean_power_kw
    assert with_dryer.duration_h == pytest.approx(bare.duration_h, rel=1e-12)


def test_an_unreached_target_cannot_be_priced():
    cfg = make_small_case(target_c=-45.0, hold_duration_s=3600.0, max_time_s=3600.0)
    result = run_air_drying(cfg)
    cost = air_campaign_cost(cfg, result, CostModel())
    assert not cost.reached_target
    assert cost.total_cost == 0.0


def test_cost_can_be_taken_for_a_secondary_target():
    data = make_small_case(max_time_s=150 * 3600).model_dump()
    data["initial_water"]["trapped_fraction"] = 0.15
    data["equipment"]["inlet_dew_point_c"] = -60.0
    data["acceptance"].update(target_c=-20.0, additional_targets_c=[-30.0],
                              hold_duration_s=3600.0)
    cfg = AirDryingCaseConfig.model_validate(data)
    result = run_air_drying(cfg)
    loose = air_campaign_cost(cfg, result, CostModel(), target_c=-20.0)
    strict = air_campaign_cost(cfg, result, CostModel(), target_c=-30.0)
    assert loose.reached_target and strict.reached_target
    # Same equipment, so the stricter target costs more only through time.
    assert strict.mean_power_kw == pytest.approx(loose.mean_power_kw, rel=1e-12)
    assert strict.total_cost > loose.total_cost


def test_vacuum_cost_counts_pumps_and_booster():
    cfg = make_small_vacuum_case(n_pumps=2, with_booster=True)
    result = run_vacuum_drying(cfg)
    model = CostModel(vacuum_pump_power_kw=7.5, vacuum_booster_power_kw=15.0)
    cost = vacuum_campaign_cost(cfg, result, model)
    assert cost.reached_target
    assert cost.mean_power_kw == pytest.approx(2 * 7.5 + 15.0, rel=1e-12)


def test_vacuum_cost_without_booster_is_lower():
    model = CostModel(vacuum_pump_power_kw=7.5, vacuum_booster_power_kw=15.0)
    bare = make_small_vacuum_case(n_pumps=2, with_booster=False)
    boosted = make_small_vacuum_case(n_pumps=2, with_booster=True)
    c_bare = vacuum_campaign_cost(bare, run_vacuum_drying(bare), model)
    c_boost = vacuum_campaign_cost(boosted, run_vacuum_drying(boosted), model)
    assert c_bare.mean_power_kw < c_boost.mean_power_kw
    # The booster draws more power but finishes sooner -- which one wins is
    # exactly the trade-off the optimisation layer is meant to resolve.
    assert c_boost.duration_h < c_bare.duration_h


def test_unaccepted_vacuum_campaign_cannot_be_priced():
    cfg = make_small_vacuum_case(max_time_s=600.0)
    result = run_vacuum_drying(cfg)
    assert not result.accepted
    assert not vacuum_campaign_cost(cfg, result, CostModel()).reached_target
