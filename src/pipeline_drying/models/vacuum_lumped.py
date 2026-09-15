"""Vacuum drying engine: lumped mass + energy model.

Governing model. The pipeline is treated as
a single control volume holding dry air, water vapour and residual liquid
water, with one effective temperature shared by the film and the steel wall:

    dm_a/dt = -m_a S(p) / V
    dm_v/dt = E - m_v S(p) / V
    dm_w/dt = -E
    C_eff dT/dt = -E h_lat(T) + U A_ext (T_ext - T)

    p = (m_a/M_air + m_v/M_water) R T / V        (Dalton, ideal gas)

A volumetric pump draws the mixture at its own composition, which is why
each species leaves at a rate proportional to its own inventory. S(p) comes
from the tabulated manufacturer curve in `equipment.VacuumPumpSystem`.

Two evaporation closures are available:

  "equilibrium"    E = k_m A_wet [rho_v,sat(T) - rho_v], with k_m from the
                   laminar Sherwood plateau (the gas is nearly stagnant in a
                   line under vacuum) and a diffusivity that scales as 1/p,
                   so mass transfer gets *faster* as the line is evacuated.
  "hertz_knudsen"  the Hertz-Knudsen-Schrage interfacial form used by
                   He & Li (2020),
                   E = [2f/(2-f)] A_wet sqrt(M_w / (2 pi R T)) [p_sat(T) - p_v],
                   with the Schrage correction factor 2f/(2-f) on the
                   evaporation coefficient f.

No explicit "heat-limited" cap is applied: the energy balance supplies that
limit by itself, because runaway evaporation cools the line, collapses
p_sat(T) and shuts the driving force down. Below 0 deg C the ice saturation
curve and the latent heat of sublimation are used, so the freezing regime is
represented rather than extrapolated.

Completion follows the operational sequence of section 3.3 -- draw down,
isolate, soak, check the pressure rebound -- and not the mere attainment of
a low absolute pressure.

MVP simplifications, all stated deliberately:
  - single control volume, so the axial pressure gradient of a long line
    (pump end much lower than far end) is not resolved; that is the 1-D
    upgrade of section 3.2.
  - C_eff is evaluated with the initial water mass and held constant; the
    liquid contributes well under 1% of it for realistic residual films.
  - the heat of fusion released when the film freezes is not modelled, so
    predicted cooling below 0 deg C is conservative (too fast).
  - the gas phase carries no sensible-heat balance of its own; its heat
    capacity is negligible against the steel wall.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import psychrometrics as psy
from ..equipment import VacuumPumpCurve, VacuumPumpSystem
from ..geometry import PipelineGrid
from ..io_schema import VacuumDryingCaseConfig
from ..numerics.integration import integrate_segment, sample_segment

T0_K = 273.15
P_ATM_PA = 101325.0
RHO_STEEL = 7850.0  # kg/m3
CP_STEEL = 490.0  # J/(kg K)

PHASE_PUMPING = "pumping"
PHASE_SOAK = "soak"

# State vector layout.
I_MA, I_MV, I_MW, I_T, I_REM_V, I_REM_A, I_Q_EXT, I_Q_LAT = range(8)
N_STATE = 8


@dataclass
class VacuumDryingResult:
    t_s: np.ndarray
    phase: np.ndarray  # per-sample label, PHASE_PUMPING or PHASE_SOAK
    pressure_pa: np.ndarray
    vapor_pressure_pa: np.ndarray
    temperature_c: np.ndarray
    liquid_water_kg: np.ndarray
    vapor_mass_kg: np.ndarray
    dry_air_mass_kg: np.ndarray
    frost_point_c: np.ndarray
    """In-line frost point of the residual vapour, i.e. at the current
    (sub-atmospheric) pressure."""
    atmospheric_frost_point_c: np.ndarray | None
    """Frost point the residual vapour would show if the line were
    repressurised to acceptance.reference_pressure_bar_a with perfectly dry
    gas and a sample then expanded to atmospheric pressure. Filling with dry
    gas leaves the vapour partial pressure unchanged, so this is strictly
    lower than the in-line value -- the dew-point convention ambiguity that a
    specification rarely resolves."""
    water_content_ppmv_at_reference: np.ndarray | None
    """Vapour mole fraction (ppmv) after the same repressurisation."""
    pumped_water_kg: np.ndarray
    time_to_acceptance_s: float | None
    accepted: bool
    soak_pressure_rise_mbar: float | None
    n_cycles: int
    min_temperature_c: float
    mass_balance_relative_error: float
    energy_balance_relative_error: float
    warnings: list[str] = field(default_factory=list)


def schrage_factor(evaporation_coefficient: float) -> float:
    """Schrage's correction 2f/(2-f) to the bare Hertz-Knudsen flux.

    Tends to f itself for the small coefficients measured on engineering
    surfaces, and to 2 at the kinetic limit f = 1.
    """
    f = float(evaporation_coefficient)
    if not 0.0 <= f <= 1.0:
        raise ValueError("evaporation coefficient must lie in [0, 1]")
    return 2.0 * f / (2.0 - f)


def wall_thermal_capacity_j_k(grid: PipelineGrid, wall_thickness_m: float,
                              coupling_fraction: float) -> float:
    """Heat capacity (J/K) of the steel wall that follows the film temperature."""
    d_out = grid.diameter_m + 2.0 * wall_thickness_m
    steel_area = np.pi / 4.0 * (d_out**2 - grid.diameter_m**2)
    mass = RHO_STEEL * steel_area * grid.length_m
    return coupling_fraction * mass * CP_STEEL


def external_surface_area_m2(grid: PipelineGrid, wall_thickness_m: float) -> float:
    return np.pi * (grid.diameter_m + 2.0 * wall_thickness_m) * grid.length_m


def _build_pump_system(config: VacuumDryingCaseConfig) -> VacuumPumpSystem:
    def curve(spec) -> VacuumPumpCurve:
        return VacuumPumpCurve(
            pressure_mbar=tuple(spec.pressure_mbar),
            capacity_m3_h=tuple(spec.capacity_m3_h),
            ultimate_pressure_mbar=spec.ultimate_pressure_mbar,
        )

    eq = config.equipment
    return VacuumPumpSystem(
        main_curve=curve(eq.pump),
        n_pumps=eq.n_pumps,
        booster_curve=curve(eq.booster) if eq.booster is not None else None,
        booster_activation_mbar=eq.booster_activation_mbar,
        n_boosters=eq.n_boosters,
        derating=eq.derating,
    )


def _pressures(m_a: float, m_v: float, t_k: float, volume_m3: float) -> tuple[float, float]:
    """Total and water-vapour partial pressure (Pa) from the gas inventory."""
    n_a = max(m_a, 0.0) / psy.M_AIR
    n_v = max(m_v, 0.0) / psy.M_WATER
    p_total = (n_a + n_v) * psy.R_GAS * t_k / volume_m3
    p_vapor = n_v * psy.R_GAS * t_k / volume_m3
    return p_total, p_vapor


def run_vacuum_drying(config: VacuumDryingCaseConfig) -> VacuumDryingResult:
    grid = PipelineGrid(
        length_m=config.pipeline.length_m,
        diameter_m=config.pipeline.diameter_m,
        n_cells=1,
    )
    pumps = _build_pump_system(config)

    volume = float(grid.area_m2 * grid.length_m)
    a_wet = float(grid.wetted_perimeter_m * grid.length_m)
    wall_thickness_m = config.pipeline.wall_thickness_mm * 1e-3
    a_ext = external_surface_area_m2(grid, wall_thickness_m)
    ua = config.thermal.u_value_w_m2_k * a_ext
    t_ext_k = config.thermal.external_temperature_c + T0_K

    water0 = config.initial_water.total_mass_kg(grid.wetted_perimeter_m, grid.length_m)
    c_eff = (
        wall_thermal_capacity_j_k(grid, wall_thickness_m,
                                  config.thermal.wall_coupling_fraction)
        + water0 * psy.CP_LIQUID_WATER
    )

    t_init_k = config.pipeline.wall_temperature_c + T0_K
    p_init = config.initial_atmosphere.pressure_bar_a * 1e5
    pw_init = min(
        float(psy.p_sat_water_pa(config.initial_atmosphere.dew_point_c)), 0.99 * p_init
    )
    m_v0 = pw_init * psy.M_WATER / (psy.R_GAS * t_init_k) * volume
    m_a0 = (p_init - pw_init) * psy.M_AIR / (psy.R_GAS * t_init_k) * volume

    mw_eps = max(1e-9, 1e-6 * water0)
    km_mult = config.simulation.mass_transfer_multiplier
    sigma = config.simulation.accommodation_coefficient
    sigma_schrage = schrage_factor(sigma)
    use_hk = config.simulation.evaporation_model == "hertz_knudsen"

    def evaporation_rate(m_w: float, t_k: float, p_total: float, p_vapor: float) -> float:
        """Net wall-film evaporation rate (kg/s); negative means condensation."""
        t_c = t_k - T0_K
        p_sat = float(psy.p_sat_pa(t_c, "auto"))
        if use_hk:
            kinetic = np.sqrt(psy.M_WATER / (2.0 * np.pi * psy.R_GAS * t_k))
            potential = sigma_schrage * a_wet * kinetic * (p_sat - p_vapor)
        else:
            d_ab = float(psy.water_vapor_diffusivity_m2_s(t_k, max(p_total, 1.0)))
            # Stagnant gas in an isolated line: laminar Sherwood plateau.
            k_m = 3.66 * d_ab / grid.diameter_m * km_mult
            rho_sat = float(psy.vapor_density_kg_m3(p_sat, t_k))
            rho_v = float(psy.vapor_density_kg_m3(p_vapor, t_k))
            potential = k_m * a_wet * (rho_sat - rho_v)
        if potential <= 0.0:
            return potential  # condensation is not limited by the film inventory
        m_pos = max(m_w, 0.0)
        return potential * m_pos / (m_pos + mw_eps)

    def make_rhs(pumping: bool):
        def rhs(_t: float, state: np.ndarray) -> np.ndarray:
            m_a = max(state[I_MA], 0.0)
            m_v = max(state[I_MV], 0.0)
            m_w = state[I_MW]
            t_k = state[I_T]

            p_total, p_vapor = _pressures(m_a, m_v, t_k, volume)
            evap = evaporation_rate(m_w, t_k, p_total, p_vapor)

            if pumping:
                s_v = float(pumps.capacity_m3_s(p_total)) / volume
            else:
                s_v = 0.0
            out_a = m_a * s_v
            out_v = m_v * s_v

            h_lat = float(psy.effective_latent_heat_j_kg(t_k - T0_K))
            q_ext = ua * (t_ext_k - t_k)
            q_lat = evap * h_lat

            d = np.zeros(N_STATE)
            d[I_MA] = -out_a
            d[I_MV] = evap - out_v
            d[I_MW] = -evap
            d[I_T] = (q_ext - q_lat) / c_eff
            d[I_REM_V] = out_v
            d[I_REM_A] = out_a
            d[I_Q_EXT] = q_ext
            d[I_Q_LAT] = q_lat
            return d

        return rhs

    rhs_pumping = make_rhs(True)
    rhs_soak = make_rhs(False)

    p_target = config.acceptance.target_pressure_mbar * 100.0
    # A frost-point target constrains the vapour partial pressure, which is a
    # strictly stronger requirement than a total-pressure target once the line
    # is evacuated (by then the gas is nearly pure vapour, so the two almost
    # coincide). Draw-down must satisfy whichever binds.
    if config.acceptance.target_frost_point_c is not None:
        pv_target = float(psy.p_sat_ice_pa(config.acceptance.target_frost_point_c))
    else:
        pv_target = np.inf

    def acceptance_margin(state: np.ndarray, factor: float = 1.0) -> float:
        """<= 0 once both the pressure and frost-point targets are met.

        `factor` < 1 tightens both targets, which is how the draw-down phase
        buys itself room for the soak rebound.
        """
        p_total, p_vapor = _pressures(state[I_MA], state[I_MV], state[I_T], volume)
        margin = p_total - factor * p_target
        if np.isfinite(pv_target):
            margin = max(margin, p_vapor - factor * pv_target)
        return margin

    drawdown_factor = config.acceptance.drawdown_factor

    def reached_target(_t: float, state: np.ndarray) -> float:
        return acceptance_margin(state, drawdown_factor)

    reached_target.terminal = True
    reached_target.direction = -1.0

    state = np.zeros(N_STATE)
    state[I_MA] = m_a0
    state[I_MV] = m_v0
    state[I_MW] = water0
    state[I_T] = t_init_k

    # Absolute tolerances per state variable: masses in kg, temperature in K,
    # cumulative heats in J -- these differ by many orders of magnitude.
    atol = np.array([1e-9, 1e-12, 1e-9, 1e-8, 1e-12, 1e-9, 1e-3, 1e-3])

    t_max = config.simulation.max_time_s
    samples_t: list[np.ndarray] = []
    samples_y: list[np.ndarray] = []
    samples_phase: list[np.ndarray] = []

    t_now = 0.0
    accepted = False
    time_to_acceptance: float | None = None
    soak_rise_mbar: float | None = None
    n_cycles = 0
    warnings: list[str] = []
    hit_horizon = False
    stalled = False
    last_soak_end_pa: float | None = None

    def record(sol, phase: str, n_points: int) -> np.ndarray:
        t_grid, y_grid = sample_segment(sol, n_points)
        samples_t.append(t_grid)
        samples_y.append(y_grid)
        samples_phase.append(np.full(t_grid.size, phase, dtype=object))
        return y_grid[:, -1]

    while t_now < t_max and n_cycles < config.simulation.max_cycles:
        n_cycles += 1

        if acceptance_margin(state, drawdown_factor) > 0.0:
            sol = integrate_segment(
                rhs_pumping, state, (t_now, t_max), events=[reached_target], atol=atol
            )
            state = record(sol, PHASE_PUMPING, 400)
            t_now = float(sol.t[-1])
            if sol.status != 1:
                hit_horizon = True
                break

        t_soak_end = min(t_now + config.acceptance.soak_duration_s, t_max)
        p_soak_start, _ = _pressures(state[I_MA], state[I_MV], state[I_T], volume)
        sol = integrate_segment(rhs_soak, state, (t_now, t_soak_end), atol=atol)
        state = record(sol, PHASE_SOAK, 200)
        t_now = float(sol.t[-1])

        p_soak_end, pw_soak_end = _pressures(state[I_MA], state[I_MV], state[I_T], volume)
        soak_rise_mbar = (p_soak_end - p_soak_start) / 100.0

        rise_ok = soak_rise_mbar <= config.acceptance.max_pressure_rise_mbar
        if rise_ok and acceptance_margin(state) <= 0.0:
            accepted = True
            time_to_acceptance = t_now
            break
        if t_now >= t_max:
            hit_horizon = True
            break
        # Guard against spinning through identical cycles: if a full draw-down
        # plus soak no longer improves the end-of-soak pressure, more cycles
        # cannot help and the campaign needs different equipment or more heat.
        if last_soak_end_pa is not None and p_soak_end > 0.99 * last_soak_end_pa:
            stalled = True
            break
        last_soak_end_pa = p_soak_end

    t_s = np.concatenate(samples_t)
    y = np.concatenate(samples_y, axis=1)
    phase = np.concatenate(samples_phase)

    m_a = np.maximum(y[I_MA], 0.0)
    m_v = np.maximum(y[I_MV], 0.0)
    m_w = y[I_MW]
    t_k = y[I_T]
    n_total = m_a / psy.M_AIR + m_v / psy.M_WATER
    pressure = n_total * psy.R_GAS * t_k / volume
    p_vapor = m_v / psy.M_WATER * psy.R_GAS * t_k / volume

    frost = psy.frost_point_c(p_vapor)
    atmospheric_frost = None
    ppmv_at_ref = None
    if config.acceptance.reference_pressure_bar_a is not None:
        p_ref = config.acceptance.reference_pressure_bar_a * 1e5
        # Backfilling with dry gas adds moles but no water: the vapour partial
        # pressure is unchanged, only its mole fraction falls.
        ppmv_at_ref = p_vapor / p_ref * 1e6
        atmospheric_frost = psy.frost_point_c(p_vapor * P_ATM_PA / p_ref)

    # The trapped air already carries vapour at t=0, so the conserved water
    # inventory is the liquid film plus that initial vapour holdup.
    water_inventory0 = water0 + m_v0
    water_total = m_w + m_v + y[I_REM_V]
    mass_error = float(
        np.max(np.abs(water_total - water_inventory0)) / max(water_inventory0, 1e-9)
    )

    stored = c_eff * (t_k - t_init_k)
    energy_residual = np.abs(stored - (y[I_Q_EXT] - y[I_Q_LAT]))
    energy_scale = max(float(np.max(np.abs(y[I_Q_LAT]))), 1.0)
    energy_error = float(np.max(energy_residual) / energy_scale)

    min_t_c = float(np.min(t_k) - T0_K)

    if not accepted:
        if stalled:
            warnings.append(
                "Draw-down/soak cycles stopped making progress: the end-of-soak "
                "pressure is no longer falling. The acceptance criterion is not "
                "reachable with this pumping configuration and heat input."
            )
        elif hit_horizon:
            warnings.append(
                "Acceptance sequence not completed within max_time_s; increase "
                "simulation.max_time_s or review pump sizing."
            )
        else:
            warnings.append(
                f"Acceptance not met after {n_cycles} draw-down/soak cycles "
                "(simulation.max_cycles reached); the pressure rebound stayed "
                "above acceptance.max_pressure_rise_mbar."
            )
    if min_t_c <= 0.0:
        warnings.append(
            f"Evaporative cooling drives the film to {min_t_c:.1f} C: ice forms and "
            "the model switches to sublimation. The heat of fusion is not modelled, "
            "so the predicted cooling rate below 0 C is conservative (too fast)."
        )
    if float(np.min(m_w)) > 1e-3 * water0 and accepted:
        warnings.append(
            "Accepted while a non-negligible liquid inventory remains: with a "
            "lumped volume this is plausible only if that water is effectively "
            "sealed off. Re-check once the 1-D vacuum engine resolves low points."
        )

    return VacuumDryingResult(
        t_s=t_s,
        phase=phase,
        pressure_pa=pressure,
        vapor_pressure_pa=p_vapor,
        temperature_c=t_k - T0_K,
        liquid_water_kg=m_w,
        vapor_mass_kg=m_v,
        dry_air_mass_kg=m_a,
        frost_point_c=frost,
        atmospheric_frost_point_c=atmospheric_frost,
        water_content_ppmv_at_reference=ppmv_at_ref,
        pumped_water_kg=y[I_REM_V],
        time_to_acceptance_s=time_to_acceptance,
        accepted=accepted,
        soak_pressure_rise_mbar=soak_rise_mbar,
        n_cycles=n_cycles,
        min_temperature_c=min_t_c,
        mass_balance_relative_error=mass_error,
        energy_balance_relative_error=energy_error,
        warnings=warnings,
    )
