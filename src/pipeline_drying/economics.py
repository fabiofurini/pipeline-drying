"""Energy and cost of a drying campaign.

Turns a simulated duration into the numbers a campaign is actually judged on:
how much energy the equipment burns and what that costs. This is the
evaluation function a future optimisation layer would sit on top of, and it
is what lets a -20 / -30 / -50 C comparison show why over-drying is expensive
rather than merely slower.

Everything here is deliberately simple and explicit. Compressor and pump
powers come from first principles or from nameplate figures the user supplies;
nothing is hidden in a correlation. Tariffs and rental rates are pure inputs.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import psychrometrics as psy
from .io_schema import AirDryingCaseConfig, VacuumDryingCaseConfig
from .models.air_1d import AirDryingResult
from .models.vacuum_lumped import VacuumDryingResult

T0_K = 273.15
GAMMA_AIR = 1.4  # ratio of specific heats
P_ATM_PA = 101325.0
NORMAL_DENSITY = P_ATM_PA * psy.M_AIR / (psy.R_GAS * T0_K)  # kg per Nm3


@dataclass(frozen=True)
class CostModel:
    """Tariffs and equipment efficiencies. Every field is a user input."""

    energy_cost_per_kwh: float = 0.25
    rental_cost_per_hour: float = 0.0
    """All-in spread rental/crew rate, charged for the campaign duration."""

    compressor_isentropic_efficiency: float = 0.7
    """Isentropic efficiency times mechanical/motor efficiency."""
    compressor_stages: int = 2
    """Stages with intercooling back to inlet temperature. More stages move
    the duty towards isothermal compression and cut the power."""
    dryer_specific_energy_kwh_per_1000_nm3: float = 0.0
    """Regeneration energy of the air dryer, from its datasheet. Left at zero
    by default because it varies by an order of magnitude between heatless,
    heated and blower-purge units -- and a silent guess would be worse than
    an obvious omission."""

    vacuum_pump_power_kw: float = 0.0
    """Shaft power of one backing pump, from its datasheet."""
    vacuum_booster_power_kw: float = 0.0
    """Shaft power of one booster train."""


@dataclass(frozen=True)
class CampaignCost:
    duration_h: float
    energy_kwh: float
    mean_power_kw: float
    energy_cost: float
    rental_cost: float
    total_cost: float
    reached_target: bool


def compression_power_kw(mass_flow_kg_s: float, p_inlet_pa: float, p_outlet_pa: float,
                         inlet_temperature_k: float, efficiency: float,
                         stages: int = 1) -> float:
    """Shaft power (kW) to compress air, with perfect intercooling between stages.

    Each stage takes the same pressure ratio and returns to the inlet
    temperature, which is the standard idealisation for a multi-stage
    machine and is why staging reduces the duty.
    """
    if mass_flow_kg_s <= 0 or p_outlet_pa <= p_inlet_pa:
        return 0.0
    if efficiency <= 0:
        raise ValueError("compressor efficiency must be positive")
    stages = max(1, int(stages))
    ratio_per_stage = (p_outlet_pa / p_inlet_pa) ** (1.0 / stages)
    exponent = (GAMMA_AIR - 1.0) / GAMMA_AIR
    specific_work = (
        GAMMA_AIR / (GAMMA_AIR - 1.0)
        * psy.R_GAS / psy.M_AIR
        * inlet_temperature_k
        * (ratio_per_stage**exponent - 1.0)
    )
    return stages * mass_flow_kg_s * specific_work / efficiency / 1000.0


def air_campaign_cost(config: AirDryingCaseConfig, result: AirDryingResult,
                      model: CostModel, target_c: float | None = None) -> CampaignCost:
    """Energy and cost of a dry-air campaign run to a given acceptance target.

    `target_c` selects among the targets evaluated in the run; the primary
    target is used if omitted. An unreached target returns a zero-cost entry
    flagged `reached_target=False` -- a campaign that never finishes cannot
    be priced.
    """
    if target_c is None or target_c == config.acceptance.target_c:
        duration_s = result.time_to_target_s
    else:
        duration_s = result.additional_target_times_s.get(float(target_c))
    if duration_s is None:
        return CampaignCost(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False)

    hours = duration_s / 3600.0
    mass_flow = config.equipment.resolved_mass_flow_kg_s()
    power = compression_power_kw(
        mass_flow,
        P_ATM_PA,
        config.equipment.pressure_bar_a * 1e5,
        config.equipment.inlet_temperature_c + T0_K,
        model.compressor_isentropic_efficiency,
        model.compressor_stages,
    )
    nm3_per_hour = mass_flow / NORMAL_DENSITY * 3600.0
    power += nm3_per_hour / 1000.0 * model.dryer_specific_energy_kwh_per_1000_nm3

    energy = power * hours
    energy_cost = energy * model.energy_cost_per_kwh
    rental = hours * model.rental_cost_per_hour
    return CampaignCost(hours, energy, power, energy_cost, rental,
                        energy_cost + rental, True)


def vacuum_campaign_cost(config: VacuumDryingCaseConfig, result: VacuumDryingResult,
                         model: CostModel) -> CampaignCost:
    """Energy and cost of a vacuum campaign.

    Pumps are charged at nameplate shaft power for the whole campaign, which
    is a fair approximation for positive-displacement machines: their power
    draw is dominated by friction and varies far less with suction pressure
    than their capacity does. The booster is charged only while it is engaged.
    """
    if not result.accepted or result.time_to_acceptance_s is None:
        return CampaignCost(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False)

    hours = result.time_to_acceptance_s / 3600.0
    power = config.equipment.n_pumps * model.vacuum_pump_power_kw
    if config.equipment.booster is not None:
        power += config.equipment.n_boosters * model.vacuum_booster_power_kw

    energy = power * hours
    energy_cost = energy * model.energy_cost_per_kwh
    rental = hours * model.rental_cost_per_hour
    return CampaignCost(hours, energy, power, energy_cost, rental,
                        energy_cost + rental, True)
