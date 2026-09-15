import numpy as np

from pipeline_drying import run_air_drying
from pipeline_drying.io_schema import AirDryingCaseConfig

from conftest import make_small_case


def test_liquid_water_is_monotonically_non_increasing():
    # Wall (15 C) is warmer than the initial ambient dew point (5 C), so
    # evaporation dominates from t=0 and the residual film should only ever
    # shrink (within numerical noise).
    cfg = make_small_case(max_time_s=45.0 * 3600.0)
    result = run_air_drying(cfg)
    total_liquid = result.liquid_water_kg.sum(axis=0)
    noise_floor = 1e-6 * total_liquid[0]
    assert np.all(np.diff(total_liquid) < noise_floor)


def test_outlet_eventually_reaches_supply_dew_point():
    cfg = make_small_case(max_time_s=60.0 * 3600.0)
    result = run_air_drying(cfg)
    assert result.outlet_dew_point_c[-1] < cfg.equipment.inlet_dew_point_c + 2.0


def test_time_to_target_found_for_an_easy_target():
    cfg = make_small_case(target_c=12.0, hold_duration_s=60.0, max_time_s=60.0 * 3600.0)
    result = run_air_drying(cfg)
    assert result.time_to_target_s is not None
    assert result.time_to_target_s > 0.0


def test_stricter_target_takes_at_least_as_long():
    easy = run_air_drying(
        make_small_case(target_c=12.0, hold_duration_s=60.0, max_time_s=60.0 * 3600.0)
    )
    strict = run_air_drying(
        make_small_case(target_c=8.0, hold_duration_s=60.0, max_time_s=60.0 * 3600.0)
    )
    assert easy.time_to_target_s is not None
    assert strict.time_to_target_s is not None
    assert strict.time_to_target_s >= easy.time_to_target_s


def test_higher_dry_air_flow_dries_faster():
    def case_with_flow(mass_flow_kg_s: float) -> AirDryingCaseConfig:
        data = dict(
            name="flow_sensitivity",
            pipeline=dict(length_m=200.0, diameter_m=0.2, n_cells=40, wall_temperature_c=15.0),
            initial_water=dict(film_thickness_mm=0.2),
            initial_atmosphere=dict(dew_point_c=5.0),
            equipment=dict(
                mass_flow_kg_s=mass_flow_kg_s,
                pressure_bar_a=3.0,
                inlet_temperature_c=15.0,
                inlet_dew_point_c=-50.0,
            ),
            acceptance=dict(target_c=12.0, convention="auto", hold_duration_s=60.0),
            simulation=dict(max_time_s=150.0 * 3600.0, mass_transfer_multiplier=1.0),
        )
        return AirDryingCaseConfig.model_validate(data)

    slow = run_air_drying(case_with_flow(0.03))
    fast = run_air_drying(case_with_flow(0.08))
    assert slow.time_to_target_s is not None
    assert fast.time_to_target_s is not None
    assert fast.time_to_target_s < slow.time_to_target_s


def test_not_reached_within_horizon_returns_none_and_warns():
    cfg = make_small_case(target_c=-45.0, hold_duration_s=3600.0, max_time_s=1.0 * 3600.0)
    result = run_air_drying(cfg)
    assert result.time_to_target_s is None
    assert any("not reached" in w for w in result.warnings)


def test_example_config_loads_and_runs():
    cfg = AirDryingCaseConfig.from_yaml("examples/literature_air.yaml")
    result = run_air_drying(cfg)
    assert result.mass_balance_relative_error < 1e-2
    assert result.mass_fraction.shape == (cfg.pipeline.n_cells, 500)
