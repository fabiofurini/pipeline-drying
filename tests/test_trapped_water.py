"""Trapped water, multi-target evaluation and acceptance conventions.

The single-film model dries to the supply dew point almost as soon as the
film is gone, which makes every acceptance target look equally cheap. These
tests pin down the behaviour that fixes it.
"""
import numpy as np
import pytest

from pipeline_drying import psychrometrics as psy
from pipeline_drying import run_air_drying
from pipeline_drying.io_schema import AirDryingCaseConfig

from conftest import make_small_case


def case(trapped_fraction=0.0, targets=(), inlet_dew_point_c=-60.0,
         max_time_s=40 * 3600.0, film_thickness_mm=0.05, **overrides):
    # A thinner film than the shared fixture: the tail physics is identical
    # but the campaign is over in tens of hours instead of hundreds, which
    # keeps this file's runtime sane.
    data = make_small_case(max_time_s=max_time_s,
                           film_thickness_mm=film_thickness_mm).model_dump()
    data["pipeline"]["n_cells"] = 20  # trends here do not need a fine grid
    data["initial_water"]["trapped_fraction"] = trapped_fraction
    data["equipment"]["inlet_dew_point_c"] = inlet_dew_point_c
    data["acceptance"].update(target_c=-20.0, additional_targets_c=list(targets),
                              hold_duration_s=3600.0)
    for section, values in overrides.items():
        data[section].update(values)
    return AirDryingCaseConfig.model_validate(data)


# --------------------------------------------------------------------------
# The inventory itself
# --------------------------------------------------------------------------


def test_zero_trapped_fraction_reproduces_the_single_film_model():
    """Backwards compatibility: the default must not change any prediction."""
    plain = run_air_drying(make_small_case(max_time_s=20 * 3600,
                                           film_thickness_mm=0.05))
    explicit = run_air_drying(
        AirDryingCaseConfig.model_validate(
            {**make_small_case(max_time_s=20 * 3600,
                               film_thickness_mm=0.05).model_dump(),
             "initial_water": dict(film_thickness_mm=0.05, trapped_fraction=0.0)}
        )
    )
    assert explicit.time_to_target_s == plain.time_to_target_s
    assert np.allclose(explicit.total_liquid_water_kg, plain.total_liquid_water_kg)
    assert np.all(explicit.trapped_water_kg == 0.0)


def test_water_is_split_between_the_two_inventories():
    result = run_air_drying(case(trapped_fraction=0.25))
    film0 = float(result.film_water_kg[:, 0].sum())
    trapped0 = float(result.trapped_water_kg[:, 0].sum())
    total0 = float(result.total_liquid_water_kg[0])
    assert trapped0 == pytest.approx(0.25 * total0, rel=1e-9)
    assert film0 == pytest.approx(0.75 * total0, rel=1e-9)


def test_mass_is_conserved_with_two_inventories():
    result = run_air_drying(case(trapped_fraction=0.2))
    # The diagnostic integrates the outlet flux over the 500 sampled points,
    # so its own quadrature error dominates once breakthrough is sharp; this
    # bounds the solver, not the trapezoid rule.
    assert result.mass_balance_relative_error < 5e-3
    assert result.trapped_water_kg.min() > -1e-3 * float(result.total_liquid_water_kg[0])


def test_trapped_water_drains_more_slowly_than_the_film():
    """The whole point: at the moment the film is exhausted, most trapped
    water is still there."""
    result = run_air_drying(case(trapped_fraction=0.3))
    film = result.film_water_kg.sum(axis=0)
    trapped = result.trapped_water_kg.sum(axis=0)
    exhausted = np.flatnonzero(film < 0.01 * film[0])
    assert exhausted.size, "the film should empty within the horizon"
    i = exhausted[0]
    assert trapped[i] > 0.5 * trapped[0]


def test_a_slower_release_ratio_leaves_more_water_behind():
    """Time to target is *not* monotonic in the release ratio, which is the
    uncomfortable part. A slow enough release never lifts the outlet dew point
    far enough to be seen, so the line passes sooner while still holding its
    water. What is monotonic is how much water is left at acceptance."""
    def left_at_acceptance(ratio):
        r = run_air_drying(case(trapped_fraction=0.15,
                                simulation=dict(trapped_transfer_ratio=ratio)))
        assert r.time_to_target_s is not None
        trapped = r.total_trapped_water_kg
        return float(np.interp(r.time_to_target_s, r.t_s, trapped)) / float(trapped[0])

    ratios = [0.05, 0.01, 0.002, 0.0005]
    left = [left_at_acceptance(r) for r in ratios]
    assert all(b >= a - 1e-9 for a, b in zip(left, left[1:])), left
    assert left[0] < 0.05 and left[-1] > 0.5


def test_passing_with_water_still_in_the_line_is_flagged():
    result = run_air_drying(case(trapped_fraction=0.15,
                                 simulation=dict(trapped_transfer_ratio=0.0005)))
    assert result.time_to_target_s is not None
    assert any("still in the line" in w for w in result.warnings)


def test_more_trapped_water_takes_longer():
    little = run_air_drying(case(trapped_fraction=0.02))
    lots = run_air_drying(case(trapped_fraction=0.20))
    assert little.time_to_target_s is not None and lots.time_to_target_s is not None
    assert lots.time_to_target_s > little.time_to_target_s


# --------------------------------------------------------------------------
# What it buys: acceptance targets that actually differ
# --------------------------------------------------------------------------


def test_without_trapped_water_all_targets_cost_the_same():
    """Documents the limitation that motivated the second inventory."""
    result = run_air_drying(case(trapped_fraction=0.0, targets=(-30.0, -50.0)))
    times = [result.time_to_target_s, *result.additional_target_times_s.values()]
    assert all(t is not None for t in times)
    assert max(times) - min(times) < 0.05 * min(times)


def test_trapped_water_separates_the_targets():
    result = run_air_drying(case(trapped_fraction=0.15, targets=(-30.0, -50.0)))
    t20 = result.time_to_target_s
    t30 = result.additional_target_times_s[-30.0]
    t50 = result.additional_target_times_s[-50.0]
    assert t20 is not None and t30 is not None and t50 is not None
    assert t30 > t20 and t50 > t30
    assert t50 > 1.1 * t20


def test_additional_targets_agree_with_separate_runs():
    """They must be exactly the same answer, just computed from one solve."""
    combined = run_air_drying(case(trapped_fraction=0.15, targets=(-30.0,)))
    separate = run_air_drying(case(trapped_fraction=0.15,
                                   acceptance=dict(target_c=-30.0)))
    assert combined.additional_target_times_s[-30.0] == pytest.approx(
        separate.time_to_target_s, rel=1e-12
    )


def test_additional_target_times_are_monotonic_in_strictness():
    result = run_air_drying(
        case(trapped_fraction=0.15, targets=(-25.0, -30.0, -35.0, -40.0))
    )
    times = [result.time_to_target_s] + [
        result.additional_target_times_s[t] for t in (-25.0, -30.0, -35.0, -40.0)
    ]
    assert all(t is not None for t in times)
    assert all(b >= a for a, b in zip(times, times[1:]))


# --------------------------------------------------------------------------
# Targets the equipment cannot reach, and the convention they are quoted in
# --------------------------------------------------------------------------


def test_target_below_the_dryer_dew_point_is_flagged_as_unreachable():
    result = run_air_drying(
        case(trapped_fraction=0.0, targets=(-50.0,), inlet_dew_point_c=-40.0)
    )
    assert result.additional_target_times_s[-50.0] is None
    assert any("unreachable at any flow" in w for w in result.warnings)
    # ...and it is reported as such, not as a horizon that was too short.
    assert not any("not reached within max_time_s" in w for w in result.warnings)


def test_a_reachable_target_produces_no_unreachability_warning():
    result = run_air_drying(case(trapped_fraction=0.0, inlet_dew_point_c=-60.0))
    assert not any("unreachable" in w for w in result.warnings)


def test_the_same_number_is_a_looser_target_when_quoted_atmospheric():
    """-20 C "at atmospheric pressure" is a weaker requirement than -20 C read
    at line pressure: expanding the gas lowers its partial pressure, so more
    water is allowed in the line. Which one the client means is worth several
    hours of campaign, in the direction most people guess wrong."""
    at_line = run_air_drying(case(trapped_fraction=0.1))
    atmospheric = run_air_drying(
        case(trapped_fraction=0.1, acceptance=dict(reference_pressure_bar_a=1.01325))
    )
    assert at_line.time_to_target_s is not None
    assert atmospheric.time_to_target_s is not None
    assert atmospheric.time_to_target_s < at_line.time_to_target_s


def test_a_dryer_rated_at_atmospheric_pressure_delivers_wetter_air():
    """The mirror image on the supply side: "-40 C at atmospheric pressure"
    from a datasheet is much wetter air once compressed into the line."""
    generous = run_air_drying(case(trapped_fraction=0.0, inlet_dew_point_c=-40.0))
    honest = run_air_drying(
        case(trapped_fraction=0.0, inlet_dew_point_c=-40.0,
             equipment=dict(inlet_reference_pressure_bar_a=1.01325))
    )
    assert generous.outlet_dew_point_c[-1] < honest.outlet_dew_point_c[-1]


def test_referenced_outlet_series_is_drier_than_the_in_line_reading():
    result = run_air_drying(
        case(trapped_fraction=0.1, acceptance=dict(reference_pressure_bar_a=1.01325))
    )
    assert result.outlet_referenced_c is not None
    # Expanding to atmospheric pressure lowers the partial pressure, hence the
    # dew point. The line runs at 3 bar in this fixture.
    assert np.all(result.outlet_referenced_c < result.outlet_primary_c + 1e-9)


def test_no_reference_pressure_means_no_referenced_series():
    assert run_air_drying(case()).outlet_referenced_c is None
