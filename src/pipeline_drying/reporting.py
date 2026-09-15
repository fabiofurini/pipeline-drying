"""Minimal run export: tabular time series + a text summary.

PDF export and the calibration/optimisation reporting hooks are later
build-plan items (section 8, tasks 4 and 8) and are intentionally out of
scope for this first prototype.
"""
from __future__ import annotations

import pandas as pd

from .io_schema import AirDryingCaseConfig, VacuumDryingCaseConfig
from .models.air_1d import AirDryingResult
from .models.vacuum_lumped import VacuumDryingResult


def result_to_dataframe(result: AirDryingResult) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "t_s": result.t_s,
            "outlet_dew_point_c": result.outlet_dew_point_c,
            "outlet_frost_point_c": result.outlet_frost_point_c,
            "outlet_primary_c": result.outlet_primary_c,
            "total_liquid_water_kg": result.total_liquid_water_kg,
        }
    )


def summary_text(config: AirDryingCaseConfig, result: AirDryingResult) -> str:
    lines = [
        f"Case: {config.name}",
        f"Acceptance target: {config.acceptance.target_c} C "
        f"({config.acceptance.convention} convention), "
        f"hold {config.acceptance.hold_duration_s / 3600:.2f} h",
        f"Time to target: "
        + (
            f"{result.time_to_target_s / 3600:.2f} h"
            if result.time_to_target_s is not None
            else "not reached within max_time_s"
        ),
        f"Mass-balance relative error: {result.mass_balance_relative_error:.2e}",
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in result.warnings)
    return "\n".join(lines)


def vacuum_result_to_dataframe(result: VacuumDryingResult) -> pd.DataFrame:
    data = {
        "t_s": result.t_s,
        "phase": result.phase,
        "pressure_mbar": result.pressure_pa / 100.0,
        "vapor_pressure_mbar": result.vapor_pressure_pa / 100.0,
        "temperature_c": result.temperature_c,
        "frost_point_c": result.frost_point_c,
        "liquid_water_kg": result.liquid_water_kg,
        "pumped_water_kg": result.pumped_water_kg,
    }
    if result.atmospheric_frost_point_c is not None:
        data["atmospheric_frost_point_c"] = result.atmospheric_frost_point_c
        data["water_content_ppmv_at_reference"] = result.water_content_ppmv_at_reference
    return pd.DataFrame(data)


def vacuum_summary_text(config: VacuumDryingCaseConfig, result: VacuumDryingResult) -> str:
    acc = config.acceptance
    criterion = f"p <= {acc.target_pressure_mbar} mbar"
    if acc.target_frost_point_c is not None:
        criterion += f" and frost point <= {acc.target_frost_point_c} C"
    lines = [
        f"Case: {config.name}",
        f"Acceptance: {criterion}, soak {acc.soak_duration_s / 3600:.2f} h, "
        f"rebound <= {acc.max_pressure_rise_mbar} mbar",
        "Time to acceptance: "
        + (
            f"{result.time_to_acceptance_s / 3600:.2f} h "
            f"({result.n_cycles} draw-down/soak cycle(s))"
            if result.accepted
            else "not accepted within max_time_s"
        ),
        f"Final pressure: {result.pressure_pa[-1] / 100:.4g} mbar "
        f"(vapour {result.vapor_pressure_pa[-1] / 100:.4g} mbar)",
        f"Final in-line frost point: {result.frost_point_c[-1]:.1f} C",
    ]
    if result.atmospheric_frost_point_c is not None:
        lines.append(
            f"After backfill to {acc.reference_pressure_bar_a} bar a with dry gas: "
            f"{result.water_content_ppmv_at_reference[-1]:.0f} ppmv, atmospheric "
            f"frost point {result.atmospheric_frost_point_c[-1]:.1f} C"
        )
    lines += [
        f"Soak pressure rise: "
        + (
            f"{result.soak_pressure_rise_mbar:.4g} mbar"
            if result.soak_pressure_rise_mbar is not None
            else "no soak performed"
        ),
        f"Residual liquid water: {max(result.liquid_water_kg[-1], 0.0):.4g} kg "
        f"of {result.liquid_water_kg[0]:.4g} kg initial",
        f"Minimum film temperature: {result.min_temperature_c:.1f} C",
        f"Water mass-balance relative error: {result.mass_balance_relative_error:.2e}",
        f"Energy-balance relative error: {result.energy_balance_relative_error:.2e}",
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in result.warnings)
    return "\n".join(lines)
