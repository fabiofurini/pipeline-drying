"""Dry-air convection drying engine: 1-D finite-volume mass-balance MVP.

Governing model:
    d(M_g,i Y_i)/dt = m_dot_g (Y_{i-1} - Y_i) + E_i
    dm_w,i/dt = -E_i
    E_i = k_m,i A_wet,i [rho_v,sat(T_w,i) - rho_v,i], smoothly limited as m_w,i -> 0

Residual water is held in two inventories per cell: the wall film, and water
trapped where the gas stream barely reaches (low-point pools, valve cavities,
dead legs). Both see the same driving potential, but trapped water evaporates
through a much smaller effective coefficient. This matters because the film
empties all at once, so a single-film model dries to the supply dew point
almost as soon as the film is gone and makes every acceptance target look
equally cheap. Trapped water instead holds the outlet at a slowly-falling
plateau -- the long tail that makes -30 C materially harder than -20 C.

Staged fidelity: wall and gas temperature are fixed, uniform inputs for this
first version (no wall/gas/liquid energy balance yet), as recommended so the
mass-balance model can be benchmarked before adding energy coupling.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import psychrometrics as psy
from ..equipment import DryAirSupply
from ..geometry import PipelineGrid
from ..io_schema import AirDryingCaseConfig
from ..numerics.finite_volume import upwind_advection_rate
from ..numerics.integration import first_hold_crossing_time, integrate

T0_K = 273.15


def sutherland_air_viscosity_pa_s(t_k: float) -> float:
    """Dynamic viscosity of air (Pa s) via Sutherland's law."""
    mu_ref, t_ref, s_suth = 1.716e-5, 273.15, 110.4
    return mu_ref * (t_k / t_ref) ** 1.5 * (t_ref + s_suth) / (t_k + s_suth)


def wall_saturation_vapor_density(t_wall_c: float, t_wall_k: float) -> float:
    """Equilibrium vapour density (kg/m3) at the wet-wall/film surface.

    Uses the ice saturation curve below 0 deg C (frost/equilibrium with a
    frozen or near-frozen film) and the liquid-water curve above, matching
    the convention used for the acceptance target elsewhere in the package.
    """
    p_sat = psy.p_sat_ice_pa(t_wall_c) if t_wall_c <= 0.0 else psy.p_sat_water_pa(t_wall_c)
    return float(psy.vapor_density_kg_m3(p_sat, t_wall_k))


def sherwood_number(re: np.ndarray, sc: np.ndarray) -> np.ndarray:
    """Sherwood number for internal pipe flow: laminar plateau or turbulent (Colburn analogy)."""
    turbulent = 0.023 * re**0.83 * sc ** (1.0 / 3.0)
    laminar = np.full_like(re, 3.66)
    return np.where(re > 2300.0, turbulent, laminar)


def _limited_by_inventory(potential: np.ndarray, inventory: np.ndarray,
                          eps: float) -> np.ndarray:
    """Evaporation rate, smoothly throttled as an inventory runs dry.

    Condensation (a negative potential) is not limited: a cell can always
    take water back out of the gas.
    """
    available = np.maximum(inventory, 0.0)
    ramp = available / (available + eps)
    return np.where(potential > 0.0, potential * ramp, potential)


@dataclass
class AirDryingResult:
    x_m: np.ndarray
    t_s: np.ndarray
    mass_fraction: np.ndarray  # shape (n_cells, n_t)
    liquid_water_kg: np.ndarray  # film + trapped, shape (n_cells, n_t)
    film_water_kg: np.ndarray
    trapped_water_kg: np.ndarray
    outlet_dew_point_c: np.ndarray
    outlet_frost_point_c: np.ndarray
    outlet_primary_c: np.ndarray
    total_liquid_water_kg: np.ndarray
    total_trapped_water_kg: np.ndarray
    outlet_referenced_c: np.ndarray | None
    """Outlet dryness expressed at acceptance.reference_pressure_bar_a, when
    one is given; this is what a client specification quoted "at atmospheric
    pressure" actually asks for."""
    time_to_target_s: float | None
    additional_target_times_s: dict[float, float | None]
    mass_balance_relative_error: float
    warnings: list[str] = field(default_factory=list)


def _build_case(config: AirDryingCaseConfig):
    grid = PipelineGrid(
        length_m=config.pipeline.length_m,
        diameter_m=config.pipeline.diameter_m,
        n_cells=config.pipeline.n_cells,
    )
    supply = DryAirSupply(
        mass_flow_kg_s=config.equipment.resolved_mass_flow_kg_s(),
        pressure_pa=config.equipment.pressure_bar_a * 1e5,
        inlet_temperature_k=config.equipment.inlet_temperature_c + T0_K,
        inlet_dew_point_c=config.equipment.inlet_dew_point_c,
        inlet_convention=config.equipment.inlet_convention,
        inlet_reference_pressure_pa=(
            None if config.equipment.inlet_reference_pressure_bar_a is None
            else config.equipment.inlet_reference_pressure_bar_a * 1e5
        ),
    )
    return grid, supply


def run_air_drying(config: AirDryingCaseConfig) -> AirDryingResult:
    grid, supply = _build_case(config)
    n = grid.n_cells
    p = supply.pressure_pa
    t_gas_k = config.pipeline.gas_temperature_c + T0_K
    t_wall_c = config.pipeline.wall_temperature_c
    t_wall_k = t_wall_c + T0_K

    mu_g = sutherland_air_viscosity_pa_s(t_gas_k)
    d_ab = float(psy.water_vapor_diffusivity_m2_s(t_gas_k, p))
    rho_v_sat_wall = wall_saturation_vapor_density(t_wall_c, t_wall_k)
    a_wet = grid.cell_wetted_area_m2  # (n,)
    volume = grid.cell_volume_m3  # (n,)
    area = grid.area_m2

    y_in = supply.inlet_mass_fraction
    m_dot = supply.mass_flow_kg_s
    km_mult = config.simulation.mass_transfer_multiplier

    total_water0 = config.initial_water.total_mass_kg(grid.wetted_perimeter_m, grid.length_m)
    trapped_frac = config.initial_water.trapped_fraction
    trapped_ratio = config.simulation.trapped_transfer_ratio
    film0_per_cell = total_water0 * (1.0 - trapped_frac) / n
    trap0_per_cell = total_water0 * trapped_frac / n
    film_eps = max(1e-9, 1e-6 * film0_per_cell)
    trap_eps = max(1e-9, 1e-6 * trap0_per_cell)

    pw0 = float(psy.p_sat_water_pa(config.initial_atmosphere.dew_point_c))
    y0_scalar = float(psy.mass_fraction_from_pw(pw0, p))

    # A zero trapped inventory would contribute a block whose derivatives are
    # identically zero, which sends the solver's numerical Jacobian estimate
    # into overflow. Integrate it only when there is water in it.
    has_trapped = trap0_per_cell > 0.0

    y0 = np.full(n, y0_scalar)
    blocks0 = [y0, np.full(n, film0_per_cell)]
    if has_trapped:
        blocks0.append(np.full(n, trap0_per_cell))
    state0 = np.concatenate(blocks0)

    def rhs(_t: float, state: np.ndarray) -> np.ndarray:
        y = state[:n]
        m_film = state[n : 2 * n]

        rho_g = psy.gas_density_kg_m3(p, t_gas_k, y)
        m_g = rho_g * volume
        u = m_dot / (rho_g * area)
        re = rho_g * u * grid.diameter_m / mu_g
        sc = mu_g / (rho_g * d_ab)
        sh = sherwood_number(re, sc)
        k_m = sh * d_ab / grid.diameter_m * km_mult

        pw = psy.pw_from_mass_fraction(y, p)
        rho_v = psy.vapor_density_kg_m3(pw, t_gas_k)
        driving = rho_v_sat_wall - rho_v

        film_potential = k_m * a_wet * driving
        film_rate = _limited_by_inventory(film_potential, m_film, film_eps)

        if has_trapped:
            trap_rate = _limited_by_inventory(
                trapped_ratio * film_potential, state[2 * n :], trap_eps
            )
        else:
            trap_rate = 0.0

        dy_dt = (upwind_advection_rate(y, y_in, m_dot) + film_rate + trap_rate) / m_g
        blocks = [dy_dt, -film_rate]
        if has_trapped:
            blocks.append(-trap_rate)
        return np.concatenate(blocks)

    t_span = (0.0, config.simulation.max_time_s)
    # A jac_sparsity hint was tried here and removed: the pattern is correct
    # and it does speed up small cases, but for most of a campaign the
    # evaporation rate barely depends on the inventory that feeds it
    # (d(rate)/d(mass) ~ 0 while water is plentiful), and grouped-column
    # numerical differencing then overflows looking for a non-zero difference.
    # Comparing several acceptance targets costs one solve anyway -- see
    # `acceptance.additional_targets_c` -- so the speed-up was not needed.
    sol = integrate(rhs, state0, t_span)

    n_out = 500
    t_out = np.linspace(t_span[0], t_span[1], n_out)
    state_out = sol.sol(t_out)
    y_out = state_out[:n, :]
    film_out = state_out[n : 2 * n, :]
    trap_out = state_out[2 * n :, :] if has_trapped else np.zeros_like(film_out)
    mw_out = film_out + trap_out

    pw_outlet = psy.pw_from_mass_fraction(y_out[-1, :], p)
    dew_outlet = psy.dew_point_c(pw_outlet)
    frost_outlet = psy.frost_point_c(pw_outlet)
    conv = config.acceptance.convention
    if conv == "water":
        primary_outlet = dew_outlet
    elif conv == "ice":
        primary_outlet = frost_outlet
    else:
        primary_outlet = np.where(frost_outlet <= 0.0, frost_outlet, dew_outlet)

    # A target quoted at a reference pressure constrains the vapour partial
    # pressure the line would show *there*, so scale it back to line pressure.
    p_ref = config.acceptance.reference_pressure_bar_a
    pressure_scale = 1.0 if p_ref is None else p / (p_ref * 1e5)

    def target_pw_at_line(target_c: float) -> float:
        return psy.target_saturation_pressure_pa(target_c, conv) * pressure_scale

    def outlet_pw_of_state(state: np.ndarray) -> float:
        y_last = state[n - 1]
        return float(psy.pw_from_mass_fraction(y_last, p))

    hold = config.acceptance.hold_duration_s
    time_to_target = first_hold_crossing_time(
        sol, outlet_pw_of_state, target_pw_at_line(config.acceptance.target_c), hold
    )
    # Extra targets are extra crossings of the same curve, not extra solves.
    additional_times = {
        float(t): first_hold_crossing_time(
            sol, outlet_pw_of_state, target_pw_at_line(t), hold
        )
        for t in config.acceptance.additional_targets_c
    }

    outlet_referenced = None
    if p_ref is not None:
        pw_ref = pw_outlet / pressure_scale
        outlet_referenced = np.where(
            psy.frost_point_c(pw_ref) <= 0.0,
            psy.frost_point_c(pw_ref),
            psy.dew_point_c(pw_ref),
        )

    total_liquid = mw_out.sum(axis=0)
    total_trapped = trap_out.sum(axis=0)

    warnings: list[str] = []

    # The outlet can never be drier than the air entering it, so a target
    # below the dryer's own outlet dew point is not slow or expensive: it is
    # unreachable at any flow rate and any duration, and only a drier dryer
    # fixes it. Worth saying plainly rather than reporting "not reached".
    inlet_pw = supply.inlet_pw_pa
    unreachable = [
        t for t in [config.acceptance.target_c, *config.acceptance.additional_targets_c]
        if target_pw_at_line(t) <= inlet_pw
    ]
    if unreachable:
        as_target = psy.dew_or_frost_point_c(inlet_pw)
        warnings.append(
            "Target(s) "
            + ", ".join(f"{t:g} C" for t in sorted(unreachable, reverse=True))
            + " lie below the dryer's own outlet dew point "
            f"({config.equipment.inlet_dew_point_c:g} C, "
            f"{config.equipment.inlet_convention} convention = "
            f"{float(as_target['primary_c']):.1f} C on the auto convention). "
            "They are unreachable at any flow or duration: the supply air "
            "itself is not that dry. Specify a drier dryer."
        )

    if time_to_target is not None and has_trapped:
        trapped_left = float(np.interp(time_to_target, t_out, total_trapped))
        trapped_initial = float(total_trapped[0])
        if trapped_left > 0.05 * trapped_initial:
            warnings.append(
                f"Acceptance was met with {trapped_left:.3g} kg "
                f"({100 * trapped_left / trapped_initial:.0f}% of the trapped "
                "inventory) still in the line. Water this slow to release does "
                "not raise the outlet dew point enough to be seen at the "
                "measurement point, so the line can pass its test and give the "
                "water back later in service. A longer hold, or a measurement "
                "closer to the trapped water, is what discriminates."
            )

    if time_to_target is None and not unreachable:
        warnings.append(
            "Acceptance criterion not reached within max_time_s; "
            "increase simulation.max_time_s or review equipment sizing."
        )
    if t_wall_c < 0.0:
        warnings.append(
            "Wall temperature below 0 C: equilibrium computed against the ice "
            "(frost point) curve, which is the correct reference below 0 C."
        )

    gas_mass_per_cell = psy.gas_density_kg_m3(p, t_gas_k, y_out) * volume[:, None]  # (n, n_out)
    total_vapor_holdup = (y_out * gas_mass_per_cell).sum(axis=0)
    total_water = total_liquid + total_vapor_holdup

    outflow_y = y_out[-1, :]
    outflow_mass_rate = m_dot * outflow_y
    outflow_integrated = np.trapezoid(outflow_mass_rate, t_out)
    inflow_integrated = m_dot * y_in * t_out[-1]
    expected_final = total_water[0] + inflow_integrated - outflow_integrated
    mass_balance_error = abs(total_water[-1] - expected_final) / max(total_water[0], 1e-9)

    return AirDryingResult(
        x_m=grid.cell_centers_m,
        t_s=t_out,
        mass_fraction=y_out,
        liquid_water_kg=mw_out,
        film_water_kg=film_out,
        trapped_water_kg=trap_out,
        outlet_dew_point_c=dew_outlet,
        outlet_frost_point_c=frost_outlet,
        outlet_primary_c=primary_outlet,
        total_liquid_water_kg=total_liquid,
        total_trapped_water_kg=total_trapped,
        outlet_referenced_c=outlet_referenced,
        time_to_target_s=time_to_target,
        additional_target_times_s=additional_times,
        mass_balance_relative_error=float(mass_balance_error),
        warnings=warnings,
    )
