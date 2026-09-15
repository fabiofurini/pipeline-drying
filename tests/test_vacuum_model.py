import numpy as np
import pytest

from pipeline_drying import psychrometrics as psy
from pipeline_drying.equipment import VacuumPumpCurve, VacuumPumpSystem
from pipeline_drying.io_schema import VacuumDryingCaseConfig, VacuumSimulationConfig
from pipeline_drying.models.vacuum_lumped import run_vacuum_drying, schrage_factor

from conftest import make_small_vacuum_case

def _first_soak_bounds(phase: np.ndarray) -> tuple[int, int]:
    """Index of the first and last sample of the first contiguous soak block."""
    soak = np.flatnonzero(phase == "soak")
    assert soak.size, "no soak phase was recorded"
    gaps = np.flatnonzero(np.diff(soak) > 1)
    end = soak[gaps[0]] if gaps.size else soak[-1]
    return int(soak[0]), int(end)


FLAT_CURVE = VacuumPumpCurve(
    pressure_mbar=(0.1, 1.0, 10.0, 1013.0),
    capacity_m3_h=(500.0, 500.0, 500.0, 500.0),
)


# --------------------------------------------------------------------------
# Pump-curve interpolation
# --------------------------------------------------------------------------


def test_pump_curve_reproduces_its_own_tabulated_points():
    curve = VacuumPumpCurve(pressure_mbar=(0.1, 1.0, 10.0), capacity_m3_h=(50.0, 300.0, 600.0))
    for p_mbar, s_m3_h in zip(curve.pressure_mbar, curve.capacity_m3_h):
        assert curve.capacity_m3_s(p_mbar * 100.0) == pytest.approx(s_m3_h / 3600.0, rel=1e-9)


def test_pump_curve_interpolates_linearly_in_log_pressure():
    curve = VacuumPumpCurve(pressure_mbar=(1.0, 100.0), capacity_m3_h=(0.0, 200.0))
    # 10 mbar is the geometric midpoint of 1 and 100 mbar.
    assert curve.capacity_m3_s(10.0 * 100.0) == pytest.approx(100.0 / 3600.0, rel=1e-9)


def test_pump_curve_is_flat_outside_the_tabulated_range():
    curve = VacuumPumpCurve(pressure_mbar=(1.0, 100.0), capacity_m3_h=(80.0, 200.0))
    assert curve.capacity_m3_s(0.01 * 100.0) == pytest.approx(80.0 / 3600.0, rel=1e-9)
    assert curve.capacity_m3_s(5000.0 * 100.0) == pytest.approx(200.0 / 3600.0, rel=1e-9)


def test_pump_curve_capacity_vanishes_at_the_ultimate_pressure():
    curve = VacuumPumpCurve(
        pressure_mbar=(0.05, 1.0, 1013.0),
        capacity_m3_h=(100.0, 100.0, 100.0),
        ultimate_pressure_mbar=0.05,
    )
    assert curve.capacity_m3_s(0.05 * 100.0) == pytest.approx(0.0, abs=1e-12)
    assert curve.capacity_m3_s(0.04 * 100.0) == pytest.approx(0.0, abs=1e-12)
    # ...and recovers the full tabulated value far above it.
    assert curve.capacity_m3_s(100.0 * 100.0) == pytest.approx(100.0 / 3600.0, rel=1e-3)


def test_pump_curve_derating_is_monotonic_in_pressure():
    curve = VacuumPumpCurve(
        pressure_mbar=(0.05, 1013.0), capacity_m3_h=(100.0, 100.0), ultimate_pressure_mbar=0.05
    )
    p_pa = np.geomspace(0.05, 100.0, 60) * 100.0
    s = np.array([curve.capacity_m3_s(p) for p in p_pa])
    assert np.all(np.diff(s) >= -1e-15)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(pressure_mbar=(1.0, 10.0), capacity_m3_h=(1.0,)),
        dict(pressure_mbar=(10.0, 1.0), capacity_m3_h=(1.0, 2.0)),
        dict(pressure_mbar=(0.0, 1.0), capacity_m3_h=(1.0, 2.0)),
        dict(pressure_mbar=(1.0,), capacity_m3_h=(1.0,)),
        dict(pressure_mbar=(1.0, 10.0), capacity_m3_h=(1.0, -2.0)),
    ],
)
def test_pump_curve_rejects_malformed_tables(kwargs):
    with pytest.raises(ValueError):
        VacuumPumpCurve(**kwargs)


# --------------------------------------------------------------------------
# Pump system: multiple pumps, booster hand-over, derating
# --------------------------------------------------------------------------


def test_capacity_scales_with_the_number_of_pumps():
    one = VacuumPumpSystem(main_curve=FLAT_CURVE, n_pumps=1)
    three = VacuumPumpSystem(main_curve=FLAT_CURVE, n_pumps=3)
    p = 10.0 * 100.0
    assert three.capacity_m3_s(p) == pytest.approx(3.0 * one.capacity_m3_s(p), rel=1e-12)


def test_derating_multiplies_the_whole_configuration():
    full = VacuumPumpSystem(main_curve=FLAT_CURVE, n_pumps=2)
    derated = VacuumPumpSystem(main_curve=FLAT_CURVE, n_pumps=2, derating=0.6)
    p = 10.0 * 100.0
    assert derated.capacity_m3_s(p) == pytest.approx(0.6 * full.capacity_m3_s(p), rel=1e-12)


def test_booster_takes_over_below_its_activation_pressure():
    booster = VacuumPumpCurve(pressure_mbar=(0.1, 50.0), capacity_m3_h=(4000.0, 4000.0))
    system = VacuumPumpSystem(
        main_curve=FLAT_CURVE, booster_curve=booster, booster_activation_mbar=20.0
    )
    well_above = system.capacity_m3_s(500.0 * 100.0)
    well_below = system.capacity_m3_s(1.0 * 100.0)
    assert well_above == pytest.approx(500.0 / 3600.0, rel=1e-2)
    assert well_below == pytest.approx(4000.0 / 3600.0, rel=1e-2)
    # The hand-over is centred on the activation pressure and is smooth.
    assert system.booster_fraction(20.0 * 100.0) == pytest.approx(0.5, rel=1e-9)


def test_booster_requires_an_activation_pressure():
    booster = VacuumPumpCurve(pressure_mbar=(0.1, 50.0), capacity_m3_h=(4000.0, 4000.0))
    with pytest.raises(ValueError):
        VacuumPumpSystem(main_curve=FLAT_CURVE, booster_curve=booster)


# --------------------------------------------------------------------------
# Conservation: the basic correctness check on the implementation
# --------------------------------------------------------------------------


def test_water_inventory_is_conserved():
    result = run_vacuum_drying(make_small_vacuum_case())
    assert result.mass_balance_relative_error < 1e-8


def test_energy_balance_is_closed():
    # Stored enthalpy must equal external heat in minus latent heat out.
    result = run_vacuum_drying(make_small_vacuum_case())
    assert result.energy_balance_relative_error < 1e-8


def test_liquid_water_never_goes_meaningfully_negative():
    result = run_vacuum_drying(make_small_vacuum_case())
    initial = float(result.liquid_water_kg[0])
    assert result.liquid_water_kg.min() > -1e-6 * initial


def test_pumped_water_accounts_for_the_evaporated_film():
    result = run_vacuum_drying(make_small_vacuum_case())
    removed = float(result.pumped_water_kg[-1])
    evaporated = float(result.liquid_water_kg[0] - result.liquid_water_kg[-1])
    # Everything that left the film either left the line or is still vapour.
    assert removed == pytest.approx(
        evaporated + float(result.vapor_mass_kg[0] - result.vapor_mass_kg[-1]), rel=1e-6
    )


# --------------------------------------------------------------------------
# Physics: pull-down, boil-off plateau, evaporative cooling
# --------------------------------------------------------------------------


def test_dry_pull_down_matches_the_analytical_exponential():
    """With no water and a constant-capacity pump, p(t) = p0 exp(-S t / V)."""
    capacity_m3_h = 600.0
    data = dict(
        name="analytical_pulldown",
        pipeline=dict(
            length_m=500.0, diameter_m=0.2, n_cells=1, wall_thickness_mm=8.0,
            wall_temperature_c=15.0,
        ),
        initial_water=dict(water_mass_kg=0.0),
        initial_atmosphere=dict(dew_point_c=-40.0, pressure_bar_a=1.01325),
        equipment=dict(
            pump=dict(
                pressure_mbar=[0.001, 1013.0],
                capacity_m3_h=[capacity_m3_h, capacity_m3_h],
            )
        ),
        # No external heat exchange, so the isothermal analytical form holds.
        thermal=dict(external_temperature_c=15.0, u_value_w_m2_k=0.0),
        acceptance=dict(target_pressure_mbar=1e-6, soak_duration_s=0.0),
        simulation=dict(max_time_s=300.0),
    )
    result = run_vacuum_drying(VacuumDryingCaseConfig.model_validate(data))

    volume = np.pi * 0.2**2 / 4.0 * 500.0
    s_m3_s = capacity_m3_h / 3600.0
    expected = result.pressure_pa[0] * np.exp(-s_m3_s * result.t_s / volume)
    assert np.allclose(result.pressure_pa, expected, rtol=1e-4)


def test_pressure_plateaus_at_the_saturation_curve_during_boil_off():
    """Once the line is below the water vapour pressure, the pump can only
    remove vapour as fast as it is generated, so p tracks p_sat(T)."""
    result = run_vacuum_drying(make_small_vacuum_case())
    pumping = result.phase == "pumping"
    p_sat = psy.p_sat_pa(result.temperature_c, "auto")
    ratio = result.pressure_pa[pumping] / p_sat[pumping]
    # The line never sits meaningfully below the saturation curve while liquid
    # remains, and it spends most of the campaign pinned to it.
    assert np.mean(np.abs(ratio - 1.0) < 0.1) > 0.5


def test_evaporative_cooling_lowers_the_temperature():
    result = run_vacuum_drying(make_small_vacuum_case())
    assert result.min_temperature_c < result.temperature_c[0]


def test_a_large_heat_supply_keeps_the_line_isothermal():
    result = run_vacuum_drying(make_small_vacuum_case(u_value_w_m2_k=1e4))
    assert result.min_temperature_c == pytest.approx(15.0, abs=0.05)


def test_no_water_means_no_cooling_at_all():
    result = run_vacuum_drying(make_small_vacuum_case(water_mass_kg=0.0))
    assert result.min_temperature_c == pytest.approx(15.0, abs=1e-6)
    assert float(result.liquid_water_kg[-1]) == pytest.approx(0.0, abs=1e-12)


def test_adiabatic_line_with_a_heavy_film_freezes_and_warns():
    """The freezing risk of vacuum drying: with no heat supply, the
    latent heat can only come out of the steel's own thermal inertia."""
    result = run_vacuum_drying(
        make_small_vacuum_case(film_thickness_mm=1.0, u_value_w_m2_k=0.0,
                               max_time_s=200.0 * 3600.0)
    )
    assert result.min_temperature_c < 0.0
    assert any("ice forms" in w for w in result.warnings)


# --------------------------------------------------------------------------
# Qualitative trends
# --------------------------------------------------------------------------


def test_more_pumps_dry_faster():
    one = run_vacuum_drying(make_small_vacuum_case(n_pumps=1))
    four = run_vacuum_drying(make_small_vacuum_case(n_pumps=4))
    assert one.accepted and four.accepted
    assert four.time_to_acceptance_s < one.time_to_acceptance_s


def test_a_booster_dries_at_least_as_fast_as_the_bare_pumps():
    bare = run_vacuum_drying(make_small_vacuum_case())
    boosted = run_vacuum_drying(make_small_vacuum_case(with_booster=True))
    assert bare.accepted and boosted.accepted
    assert boosted.time_to_acceptance_s < bare.time_to_acceptance_s


def test_more_residual_water_takes_longer():
    light = run_vacuum_drying(make_small_vacuum_case(film_thickness_mm=0.05,
                                                     max_time_s=200.0 * 3600.0))
    heavy = run_vacuum_drying(make_small_vacuum_case(film_thickness_mm=0.5,
                                                     max_time_s=200.0 * 3600.0))
    assert light.accepted and heavy.accepted
    assert heavy.time_to_acceptance_s > light.time_to_acceptance_s


def test_stricter_frost_point_target_takes_at_least_as_long():
    easy = run_vacuum_drying(make_small_vacuum_case(target_frost_point_c=-20.0))
    strict = run_vacuum_drying(make_small_vacuum_case(target_frost_point_c=-30.0))
    assert easy.accepted and strict.accepted
    assert strict.time_to_acceptance_s >= easy.time_to_acceptance_s


def test_throttling_mass_transfer_slows_the_campaign():
    fast = run_vacuum_drying(make_small_vacuum_case())
    slow = run_vacuum_drying(make_small_vacuum_case(mass_transfer_multiplier=1e-3))
    assert fast.accepted and slow.accepted
    assert slow.time_to_acceptance_s > fast.time_to_acceptance_s


def test_the_two_evaporation_closures_agree_when_pumping_is_the_bottleneck():
    """Both closures are far faster than the pump can remove vapour, so the
    campaign duration is set by S(p) and not by the interfacial model -- the
    reason the lumped MVP can start from either."""
    equilibrium = run_vacuum_drying(make_small_vacuum_case())
    kinetic = run_vacuum_drying(make_small_vacuum_case(evaporation_model="hertz_knudsen"))
    assert equilibrium.accepted and kinetic.accepted
    assert kinetic.time_to_acceptance_s == pytest.approx(
        equilibrium.time_to_acceptance_s, rel=0.05
    )


def test_a_kinetically_starved_interface_does_change_the_answer():
    """...but only because the accommodation coefficient is large enough.
    Starve it and evaporation, not pumping, becomes the limiting step."""
    starved = run_vacuum_drying(
        make_small_vacuum_case(evaporation_model="hertz_knudsen",
                               accommodation_coefficient=1e-7)
    )
    assert not starved.accepted
    assert float(starved.liquid_water_kg[-1]) > 0.1 * float(starved.liquid_water_kg[0])


# --------------------------------------------------------------------------
# Acceptance sequence: draw down, isolate, soak, pressure-rise test
# --------------------------------------------------------------------------


def test_campaign_ends_with_an_isolated_soak():
    result = run_vacuum_drying(make_small_vacuum_case())
    assert result.accepted
    assert result.phase[-1] == "soak"
    assert result.phase[0] == "pumping"


def test_soak_rebounds_while_liquid_water_remains():
    """A soak started with the film still wet shows the pressure rebound that
    makes "we reached a low pressure" an insufficient completion criterion.

    Reaching that state needs mass transfer slow enough for the pump to
    outrun evaporation; with a fast interface the line simply sits on the
    saturation plateau instead and never gets below it while liquid remains.
    """
    result = run_vacuum_drying(
        make_small_vacuum_case(mass_transfer_multiplier=1e-5, target_pressure_mbar=1.0,
                               target_frost_point_c=None, soak_duration_s=3600.0,
                               max_time_s=3.0 * 3600.0)
    )
    assert not result.accepted
    assert float(result.liquid_water_kg[-1]) > 0.9 * float(result.liquid_water_kg[0])
    start, end = _first_soak_bounds(result.phase)
    assert result.pressure_pa[end] > 2.0 * result.pressure_pa[start]


def test_a_stalled_campaign_stops_instead_of_cycling_forever():
    """A rebound tolerance the configuration can never meet must terminate,
    not burn the whole horizon repeating an identical cycle."""
    result = run_vacuum_drying(
        make_small_vacuum_case(target_pressure_mbar=100.0, target_frost_point_c=None,
                               max_pressure_rise_mbar=0.01,
                               max_time_s=100.0 * 3600.0, max_cycles=10)
    )
    assert not result.accepted
    assert result.n_cycles < 10
    assert result.t_s[-1] < 100.0 * 3600.0
    assert any("no longer falling" in w for w in result.warnings)


def test_accepting_above_the_saturation_pressure_is_flagged():
    """Drawing down only to 80 mbar leaves the vapour saturated, so the
    rebound is tiny and the pressure-rise test passes while the line is still
    wet. The engine accepts but says so loudly -- this is the case where a
    lumped volume is genuinely not enough."""
    result = run_vacuum_drying(
        make_small_vacuum_case(target_pressure_mbar=100.0, target_frost_point_c=None,
                               max_time_s=6.0 * 3600.0)
    )
    assert result.accepted
    assert float(result.liquid_water_kg[-1]) > 0.9 * float(result.liquid_water_kg[0])
    assert any("non-negligible liquid inventory" in w for w in result.warnings)


def test_not_reached_within_horizon_returns_none_and_warns():
    result = run_vacuum_drying(make_small_vacuum_case(max_time_s=600.0))
    assert result.time_to_acceptance_s is None
    assert not result.accepted
    assert any("not completed within max_time_s" in w for w in result.warnings)


# --------------------------------------------------------------------------
# Dew-point convention reporting
# --------------------------------------------------------------------------


def test_backfilling_with_dry_gas_lowers_the_reported_frost_point():
    """Same residual water, two legitimate ways to quote it. Which one a
    specification means is exactly the ambiguity worth resolving up front."""
    result = run_vacuum_drying(make_small_vacuum_case(reference_pressure_bar_a=5.0))
    assert result.atmospheric_frost_point_c is not None
    assert result.atmospheric_frost_point_c[-1] < result.frost_point_c[-1]
    # Consistency: ppmv and partial pressure must describe the same gas.
    p_ref = 5.0e5
    assert result.water_content_ppmv_at_reference[-1] == pytest.approx(
        result.vapor_pressure_pa[-1] / p_ref * 1e6, rel=1e-9
    )


def test_reference_metrics_are_absent_when_no_reference_pressure_is_given():
    result = run_vacuum_drying(make_small_vacuum_case(reference_pressure_bar_a=None))
    assert result.atmospheric_frost_point_c is None
    assert result.water_content_ppmv_at_reference is None


# --------------------------------------------------------------------------
# Example configuration
# --------------------------------------------------------------------------


def test_example_vacuum_config_loads_and_runs():
    config = VacuumDryingCaseConfig.from_yaml("examples/literature_vacuum.yaml")
    result = run_vacuum_drying(config)
    assert result.accepted
    assert result.mass_balance_relative_error < 1e-8
    assert result.energy_balance_relative_error < 1e-8
    assert result.t_s.size == result.pressure_pa.size == result.phase.size


def test_example_vacuum_config_rejects_a_lone_booster():
    with pytest.raises(ValueError):
        VacuumDryingCaseConfig.model_validate(
            {
                **VacuumDryingCaseConfig.from_yaml(
                    "examples/literature_vacuum.yaml"
                ).model_dump(),
                "equipment": {
                    "pump": dict(pressure_mbar=[1.0, 10.0], capacity_m3_h=[10.0, 20.0]),
                    "booster": dict(pressure_mbar=[1.0, 10.0], capacity_m3_h=[10.0, 20.0]),
                },
            }
        )


def test_schrage_factor_matches_its_definition():
    assert schrage_factor(1.0) == pytest.approx(2.0, rel=1e-12)
    assert schrage_factor(0.03) == pytest.approx(2 * 0.03 / (2 - 0.03), rel=1e-12)
    # For the small coefficients measured on real surfaces it reduces to f.
    assert schrage_factor(1e-4) == pytest.approx(1e-4, rel=1e-3)
    assert schrage_factor(0.0) == 0.0
    with pytest.raises(ValueError):
        schrage_factor(1.5)


def test_default_evaporation_coefficient_matches_the_published_range():
    """He & Li (2020) use f = 0.02-0.04 for pipeline vacuum drying."""
    default = VacuumSimulationConfig(max_time_s=1.0).accommodation_coefficient
    assert 0.02 <= default <= 0.04
