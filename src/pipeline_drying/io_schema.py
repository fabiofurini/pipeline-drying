"""Pydantic input schemas for the dry-air and vacuum drying cases (MVP).

Human-facing units (deg C, bar, Nm3/h, mm) are accepted at this boundary and
converted to pure SI immediately; every solver module downstream works in SI
only: human units at the boundary, SI everywhere inside.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

RHO_WATER = 1000.0  # kg/m3, MVP constant (liquid film density)


class PipelineConfig(BaseModel):
    length_m: float = Field(..., gt=0)
    diameter_m: float = Field(..., gt=0)
    n_cells: int = Field(200, ge=1, le=5000)
    """Axial cells for the 1-D engines; ignored by the lumped vacuum engine."""
    wall_thickness_mm: float = Field(10.0, gt=0)
    """Steel wall thickness -- sets the thermal inertia the vacuum engine
    balances latent heat against; unused by the isothermal dry-air MVP."""
    wall_temperature_c: float
    gas_temperature_c: Optional[float] = None
    """If omitted, gas temperature is assumed equal to wall_temperature_c (thermal equilibrium, MVP)."""

    @model_validator(mode="after")
    def _default_gas_temperature(self) -> "PipelineConfig":
        if self.gas_temperature_c is None:
            self.gas_temperature_c = self.wall_temperature_c
        return self


class InitialWaterConfig(BaseModel):
    film_thickness_mm: Optional[float] = Field(None, gt=0)
    water_mass_kg: Optional[float] = Field(None, ge=0)
    trapped_fraction: float = Field(0.0, ge=0, lt=1)
    """Fraction of the residual water held somewhere the gas stream barely
    reaches -- low-point pools, valve cavities, dead legs, flanges. It is
    modelled as a second, slowly-draining inventory (see
    `SimulationConfig.trapped_transfer_ratio`) rather than as part of the wall
    film, because it is what produces the long tail of a drying campaign: the
    film empties all at once, trapped water does not. 0.0 reproduces the
    single-film behaviour of the first prototype."""

    @model_validator(mode="after")
    def _exactly_one(self) -> "InitialWaterConfig":
        provided = [v is not None for v in (self.film_thickness_mm, self.water_mass_kg)]
        if sum(provided) != 1:
            raise ValueError("Specify exactly one of film_thickness_mm or water_mass_kg")
        return self

    def total_mass_kg(self, wetted_perimeter_m: float, length_m: float) -> float:
        if self.water_mass_kg is not None:
            return self.water_mass_kg
        film_m = self.film_thickness_mm * 1e-3
        return RHO_WATER * wetted_perimeter_m * length_m * film_m


class InitialAtmosphereConfig(BaseModel):
    dew_point_c: float
    pressure_bar_a: float = Field(1.01325, gt=0)
    """Absolute pressure of the air trapped in the line at t=0. Only the
    vacuum engine uses it; the dry-air engine runs at the equipment pressure."""


class DryAirEquipmentConfig(BaseModel):
    mass_flow_kg_s: Optional[float] = Field(None, gt=0)
    volumetric_flow_nm3_h: Optional[float] = Field(None, gt=0)
    pressure_bar_a: float = Field(..., gt=0)
    inlet_temperature_c: float
    inlet_dew_point_c: float
    inlet_convention: Literal["auto", "water", "ice"] = "water"
    """Phase convention behind the dryer's quoted outlet dew point. Below 0 C
    a given vapour pressure has two names: air quoted at -40 C over liquid
    water is the same gas as air quoted at -36.6 C over ice. Dryer datasheets
    rarely say which they mean, so it is an explicit input. "water" keeps the
    reading a datasheet -40 C most often denotes; set "auto"/"ice" to match an
    acceptance target stated on the ice curve."""
    inlet_reference_pressure_bar_a: Optional[float] = Field(None, gt=0)
    """Pressure at which the dryer's outlet dew point is quoted. Leave unset to
    read it at the operating pressure. Set 1.01325 for a datasheet stating
    e.g. "-40 C at atmospheric pressure" (as the TAP specification does):
    that same air is far wetter once compressed, so the distinction changes
    what the dryer can actually deliver."""

    @model_validator(mode="after")
    def _exactly_one_flow(self) -> "DryAirEquipmentConfig":
        provided = [v is not None for v in (self.mass_flow_kg_s, self.volumetric_flow_nm3_h)]
        if sum(provided) != 1:
            raise ValueError("Specify exactly one of mass_flow_kg_s or volumetric_flow_nm3_h")
        return self

    def resolved_mass_flow_kg_s(self) -> float:
        if self.mass_flow_kg_s is not None:
            return self.mass_flow_kg_s
        # Normal conditions reference: 0 deg C, 1.01325 bar a.
        rho_n = 101325.0 * 0.0289647 / (8.31446 * 273.15)
        return self.volumetric_flow_nm3_h / 3600.0 * rho_n


class AcceptanceConfig(BaseModel):
    target_c: float
    convention: Literal["auto", "water", "ice"] = "auto"
    hold_duration_s: float = Field(3600.0, ge=0)
    measurement_location: Literal["outlet"] = "outlet"
    additional_targets_c: list[float] = Field(default_factory=list)
    """Further acceptance targets to evaluate on the same run. Comparing
    -20 / -30 / -50 C does not need three simulations: they are three
    crossings of one outlet curve, so they cost one solve."""
    reference_pressure_bar_a: Optional[float] = Field(None, gt=0)
    """Pressure at which the target is specified. Leave unset to interpret the
    target at pipeline pressure (a pressure dew point). Set 1.01325 for a
    target quoted "at atmospheric pressure", as e.g. the TAP specification
    does -- the same vapour reads many degrees apart under the two
    conventions, so this is not a cosmetic setting."""


class SimulationConfig(BaseModel):
    max_time_s: float = Field(..., gt=0)
    mass_transfer_multiplier: float = Field(1.0, ge=0)
    """Tunable k_m multiplier -- the hook a calibration step would fit."""
    trapped_transfer_ratio: float = Field(0.01, gt=0, le=1)
    """How much slower trapped water evaporates than the wall film, as a
    fraction of the film's mass-transfer coefficient. A pool in a low point
    presents far less interfacial area per kilogram than a film and sits in
    poorly swept gas, so the effective rate is orders of magnitude lower.
    This and `InitialWaterConfig.trapped_fraction` are the two parameters that
    set the length of the drying tail; both are calibration targets."""


class AirDryingCaseConfig(BaseModel):
    name: str = "unnamed_case"
    pipeline: PipelineConfig
    initial_water: InitialWaterConfig
    initial_atmosphere: InitialAtmosphereConfig
    equipment: DryAirEquipmentConfig
    acceptance: AcceptanceConfig
    simulation: SimulationConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AirDryingCaseConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


class VacuumPumpCurveConfig(BaseModel):
    """A manufacturer suction-capacity curve, in vendor units."""

    pressure_mbar: list[float] = Field(..., min_length=2)
    capacity_m3_h: list[float] = Field(..., min_length=2)
    ultimate_pressure_mbar: float = Field(0.0, ge=0)

    @model_validator(mode="after")
    def _consistent_curve(self) -> "VacuumPumpCurveConfig":
        if len(self.pressure_mbar) != len(self.capacity_m3_h):
            raise ValueError("pressure_mbar and capacity_m3_h must have the same length")
        if any(p <= 0 for p in self.pressure_mbar):
            raise ValueError("pressure_mbar entries must be positive")
        if any(b <= a for a, b in zip(self.pressure_mbar, self.pressure_mbar[1:])):
            raise ValueError("pressure_mbar must be strictly increasing")
        if any(c < 0 for c in self.capacity_m3_h):
            raise ValueError("capacity_m3_h entries must be non-negative")
        return self


class VacuumEquipmentConfig(BaseModel):
    pump: VacuumPumpCurveConfig
    n_pumps: int = Field(1, ge=1)
    booster: Optional[VacuumPumpCurveConfig] = None
    booster_activation_mbar: Optional[float] = Field(None, gt=0)
    """Suction pressure at which the booster train takes over."""
    n_boosters: int = Field(1, ge=1)
    derating: float = Field(1.0, ge=0)

    @model_validator(mode="after")
    def _booster_pair(self) -> "VacuumEquipmentConfig":
        if (self.booster is None) != (self.booster_activation_mbar is None):
            raise ValueError(
                "Specify booster and booster_activation_mbar together, or neither"
            )
        return self


class ThermalConfig(BaseModel):
    """External heat supply, which is what ultimately feeds the latent heat."""

    external_temperature_c: float
    u_value_w_m2_k: float = Field(5.0, ge=0)
    """Overall heat-transfer coefficient on the external pipe surface."""
    wall_coupling_fraction: float = Field(1.0, ge=0, le=1)
    """Fraction of the steel wall mass that follows the film temperature on
    campaign time scales. 1.0 is appropriate for a bare wall (conduction
    through ~10 mm of steel equilibrates in seconds); lower it to represent
    a wall that stays partly decoupled, e.g. under thick coating."""


class VacuumAcceptanceConfig(BaseModel):
    """Operational completion rule, not merely "a low pressure was reached".

    Follows the usual operational sequence: draw down to
    `target_pressure_mbar`, isolate for `soak_duration_s`, and accept only if
    the pressure rebound stays within `max_pressure_rise_mbar` (the classic
    pressure-rise test) and, optionally, the in-line frost point is below
    `target_frost_point_c`.
    """

    target_pressure_mbar: float = Field(..., gt=0)
    drawdown_factor: float = Field(0.8, gt=0, le=1)
    """Draw down to this fraction of the acceptance target before isolating,
    so the soak rebound still lands inside the criterion. Pumping to exactly
    the target always fails the post-soak check by a hair, which is why real
    procedures over-pump."""
    soak_duration_s: float = Field(3600.0, ge=0)
    max_pressure_rise_mbar: float = Field(1.0, gt=0)
    target_frost_point_c: Optional[float] = None
    reference_pressure_bar_a: Optional[float] = Field(None, gt=0)
    """If set, also report the frost point the residual vapour would show if
    the line were recompressed to this pressure without condensation -- the
    "pressure dew point" ambiguity that a specification rarely resolves."""


class VacuumSimulationConfig(BaseModel):
    max_time_s: float = Field(..., gt=0)
    evaporation_model: Literal["equilibrium", "hertz_knudsen"] = "equilibrium"
    mass_transfer_multiplier: float = Field(1.0, ge=0)
    """Calibration hook on k_m for the `equilibrium` closure."""
    accommodation_coefficient: float = Field(0.03, ge=0, le=1)
    """Evaporation coefficient f of the Hertz-Knudsen-Schrage closure. The
    default is the midpoint of the 0.02-0.04 range He & Li (2020) use for
    pipeline vacuum drying, after Paul (1962). The kinetic limit (f = 1)
    exceeds any achievable pumping rate by orders of magnitude, so this stays
    a calibration parameter rather than a physical constant -- though section
    5.4 of the vacuum note shows the answer barely depends on it while the
    campaign is pump-limited."""
    max_cycles: int = Field(5, ge=1)
    """Maximum number of draw-down/soak attempts before giving up."""


class VacuumDryingCaseConfig(BaseModel):
    name: str = "unnamed_vacuum_case"
    pipeline: PipelineConfig
    initial_water: InitialWaterConfig
    initial_atmosphere: InitialAtmosphereConfig
    equipment: VacuumEquipmentConfig
    thermal: ThermalConfig
    acceptance: VacuumAcceptanceConfig
    simulation: VacuumSimulationConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> "VacuumDryingCaseConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
