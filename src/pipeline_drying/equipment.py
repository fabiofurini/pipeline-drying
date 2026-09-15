"""Equipment models: dry-air supply and vacuum pumping systems."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import psychrometrics as psy


@dataclass(frozen=True)
class DryAirSupply:
    """Dry-air unit operating point, held constant over the campaign (MVP).

    A time-varying schedule (flow/pressure steps) is a natural later
    extension behind the same interface, and is what an optimisation layer
    would vary.
    """

    mass_flow_kg_s: float
    pressure_pa: float
    inlet_temperature_k: float
    inlet_dew_point_c: float
    inlet_convention: str = "water"
    inlet_reference_pressure_pa: float | None = None

    @property
    def inlet_pw_pa(self) -> float:
        """Inlet vapour partial pressure at the operating pressure.

        A dew point quoted at a lower reference pressure describes a gas whose
        vapour partial pressure scales up with compression, so the same
        datasheet figure means much wetter air inside a pressurised line.
        """
        pw = float(psy.p_sat_pa(self.inlet_dew_point_c, self.inlet_convention))
        if self.inlet_reference_pressure_pa is None:
            return pw
        return pw * self.pressure_pa / self.inlet_reference_pressure_pa

    @property
    def inlet_mass_fraction(self) -> float:
        return float(psy.mass_fraction_from_pw(self.inlet_pw_pa, self.pressure_pa))


@dataclass(frozen=True)
class VacuumPumpCurve:
    """Tabulated suction capacity S(p) of a vacuum pump or pumping group.

    Manufacturer curves are published as volumetric capacity against suction
    pressure, so the table is stored in the vendor's own units (mbar, m3/h)
    and converted to SI on use. Capacity is interpolated linearly in
    log(pressure), which is how these curves are normally read off a
    log-scaled datasheet plot, and held flat outside the tabulated range.
    """

    pressure_mbar: tuple[float, ...]
    capacity_m3_h: tuple[float, ...]
    ultimate_pressure_mbar: float = 0.0
    """Blank-off pressure. Capacity is smoothly derated to zero as p -> p_ult;
    leave at 0 if the tabulated curve already falls to zero on its own."""

    def __post_init__(self) -> None:
        if len(self.pressure_mbar) != len(self.capacity_m3_h):
            raise ValueError("pressure_mbar and capacity_m3_h must have the same length")
        if len(self.pressure_mbar) < 2:
            raise ValueError("A pump curve needs at least two points")
        p = np.asarray(self.pressure_mbar, dtype=float)
        if np.any(p <= 0.0):
            raise ValueError("Pump-curve pressures must be positive")
        if np.any(np.diff(p) <= 0.0):
            raise ValueError("pressure_mbar must be strictly increasing")
        if np.any(np.asarray(self.capacity_m3_h, dtype=float) < 0.0):
            raise ValueError("Pump-curve capacities must be non-negative")
        if self.ultimate_pressure_mbar < 0.0:
            raise ValueError("ultimate_pressure_mbar must be non-negative")

    def capacity_m3_s(self, p_pa: np.ndarray | float) -> np.ndarray | float:
        """Suction capacity (m3/s) at absolute suction pressure p_pa (Pa)."""
        p_mbar = np.asarray(p_pa, dtype=float) / 100.0
        p_mbar = np.clip(p_mbar, 1e-12, None)
        s_m3_h = np.interp(
            np.log(p_mbar),
            np.log(np.asarray(self.pressure_mbar, dtype=float)),
            np.asarray(self.capacity_m3_h, dtype=float),
        )
        return s_m3_h * self._ultimate_derating(p_mbar) / 3600.0

    def _ultimate_derating(self, p_mbar: np.ndarray) -> np.ndarray:
        """Smooth 0->1 factor that kills capacity at the blank-off pressure.

        A hard cut-off would put a discontinuity in the ODE right-hand side;
        the rational ramp below is continuous and also reproduces the real
        loss of capacity that pumps show within a factor of a few of their
        ultimate pressure.
        """
        p_ult = self.ultimate_pressure_mbar
        if p_ult <= 0.0:
            return np.ones_like(p_mbar)
        excess = np.clip(p_mbar - p_ult, 0.0, None) / p_ult
        return excess**2 / (1.0 + excess**2)


@dataclass(frozen=True)
class VacuumPumpSystem:
    """A pumping configuration: n identical pumps, optionally a booster group.

    The booster is represented the way vendors quote combined systems: its
    curve is the capacity of the whole booster + backing-pump train, and it
    replaces (rather than adds to) the bare backing pumps once its activation
    pressure is reached. The hand-over is blended over a narrow pressure band
    so the right-hand side stays smooth for the implicit integrator.
    """

    main_curve: VacuumPumpCurve
    n_pumps: int = 1
    booster_curve: VacuumPumpCurve | None = None
    booster_activation_mbar: float | None = None
    n_boosters: int = 1
    activation_sharpness: float = 8.0
    derating: float = 1.0
    """Overall capacity multiplier -- the "pump derating factor" listed as a
    calibration parameter, since real pumps rarely meet their datasheet."""

    def __post_init__(self) -> None:
        if self.n_pumps < 1:
            raise ValueError("n_pumps must be >= 1")
        if self.derating < 0.0:
            raise ValueError("derating must be non-negative")
        if (self.booster_curve is None) != (self.booster_activation_mbar is None):
            raise ValueError(
                "booster_curve and booster_activation_mbar must be given together"
            )

    def booster_fraction(self, p_pa: np.ndarray | float) -> np.ndarray | float:
        """Weight in [0,1] of the booster train at suction pressure p_pa."""
        if self.booster_curve is None:
            return np.zeros_like(np.asarray(p_pa, dtype=float))
        p_mbar = np.clip(np.asarray(p_pa, dtype=float) / 100.0, 1e-12, None)
        ratio = p_mbar / self.booster_activation_mbar
        return 1.0 / (1.0 + ratio**self.activation_sharpness)

    def capacity_m3_s(self, p_pa: np.ndarray | float) -> np.ndarray | float:
        """Total suction capacity (m3/s) of the configuration at pressure p_pa."""
        main = self.n_pumps * self.main_curve.capacity_m3_s(p_pa)
        if self.booster_curve is None:
            return self.derating * main
        boost = self.n_boosters * self.booster_curve.capacity_m3_s(p_pa)
        w = self.booster_fraction(p_pa)
        return self.derating * ((1.0 - w) * main + w * boost)
