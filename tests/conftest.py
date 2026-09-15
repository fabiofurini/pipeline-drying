"""Shared fixtures: a small, fast dry-air case used across the test suite.

Parameters are chosen so the whole pipeline (200 m, 0.2 m ID, 40 cells) is
flushed in minutes and dries out in tens of hours, keeping tests fast while
still exercising the full advection + evaporation + conservation behaviour.
"""
from __future__ import annotations

from pipeline_drying.io_schema import AirDryingCaseConfig, VacuumDryingCaseConfig


def make_small_case(
    target_c: float = -20.0,
    hold_duration_s: float = 60.0,
    max_time_s: float = 60.0 * 3600.0,
    film_thickness_mm: float = 0.2,
    mass_transfer_multiplier: float = 1.0,
) -> AirDryingCaseConfig:
    data = dict(
        name="small_test_case",
        pipeline=dict(length_m=200.0, diameter_m=0.2, n_cells=40, wall_temperature_c=15.0),
        initial_water=dict(film_thickness_mm=film_thickness_mm),
        initial_atmosphere=dict(dew_point_c=5.0),
        equipment=dict(
            mass_flow_kg_s=0.05,
            pressure_bar_a=3.0,
            inlet_temperature_c=15.0,
            inlet_dew_point_c=-50.0,
        ),
        acceptance=dict(target_c=target_c, convention="auto", hold_duration_s=hold_duration_s),
        simulation=dict(max_time_s=max_time_s, mass_transfer_multiplier=mass_transfer_multiplier),
    )
    return AirDryingCaseConfig.model_validate(data)


def make_small_vacuum_case(
    film_thickness_mm: float | None = 0.05,
    water_mass_kg: float | None = None,
    n_pumps: int = 1,
    capacity_m3_h: float = 300.0,
    ultimate_pressure_mbar: float = 0.05,
    with_booster: bool = False,
    u_value_w_m2_k: float = 5.0,
    external_temperature_c: float = 15.0,
    target_pressure_mbar: float = 1.0,
    target_frost_point_c: float | None = None,
    drawdown_factor: float = 0.8,
    soak_duration_s: float = 1800.0,
    max_pressure_rise_mbar: float = 0.2,
    max_time_s: float = 24.0 * 3600.0,
    evaporation_model: str = "equilibrium",
    reference_pressure_bar_a: float | None = 5.0,
    **simulation_overrides,
):
    """A small vacuum case (500 m, 0.2 m ID) that draws down in minutes."""
    water = (
        dict(film_thickness_mm=film_thickness_mm)
        if water_mass_kg is None
        else dict(water_mass_kg=water_mass_kg)
    )
    equipment = dict(
        n_pumps=n_pumps,
        pump=dict(
            pressure_mbar=[0.05, 1.0, 10.0, 1013.0],
            capacity_m3_h=[0.0, 0.7 * capacity_m3_h, capacity_m3_h, capacity_m3_h],
            ultimate_pressure_mbar=ultimate_pressure_mbar,
        ),
    )
    if with_booster:
        equipment.update(
            booster=dict(
                pressure_mbar=[0.05, 1.0, 50.0],
                capacity_m3_h=[0.0, 5.0 * capacity_m3_h, 6.0 * capacity_m3_h],
                ultimate_pressure_mbar=ultimate_pressure_mbar,
            ),
            booster_activation_mbar=20.0,
        )
    data = dict(
        name="small_vacuum_test_case",
        pipeline=dict(
            length_m=500.0,
            diameter_m=0.2,
            n_cells=1,
            wall_thickness_mm=8.0,
            wall_temperature_c=15.0,
        ),
        initial_water=water,
        initial_atmosphere=dict(dew_point_c=5.0, pressure_bar_a=1.01325),
        equipment=equipment,
        thermal=dict(
            external_temperature_c=external_temperature_c,
            u_value_w_m2_k=u_value_w_m2_k,
            wall_coupling_fraction=1.0,
        ),
        acceptance=dict(
            target_pressure_mbar=target_pressure_mbar,
            drawdown_factor=drawdown_factor,
            soak_duration_s=soak_duration_s,
            max_pressure_rise_mbar=max_pressure_rise_mbar,
            target_frost_point_c=target_frost_point_c,
            reference_pressure_bar_a=reference_pressure_bar_a,
        ),
        simulation=dict(
            max_time_s=max_time_s,
            evaporation_model=evaporation_model,
            **simulation_overrides,
        ),
    )
    return VacuumDryingCaseConfig.model_validate(data)
