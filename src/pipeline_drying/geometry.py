"""Pipeline geometry: axial discretisation into finite-volume cells."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PipelineGrid:
    """1-D axial grid for a pipeline of constant diameter.

    Elevation/bathymetry and branches are not modelled in the MVP; the field
    is present so it can be wired in later without changing the interface.
    """

    length_m: float
    diameter_m: float
    n_cells: int
    elevation_m: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.length_m <= 0:
            raise ValueError("length_m must be positive")
        if self.diameter_m <= 0:
            raise ValueError("diameter_m must be positive")
        if self.n_cells < 1:
            raise ValueError("n_cells must be >= 1")

    @property
    def dx_m(self) -> float:
        return self.length_m / self.n_cells

    @property
    def area_m2(self) -> float:
        return np.pi * self.diameter_m**2 / 4.0

    @property
    def wetted_perimeter_m(self) -> float:
        return np.pi * self.diameter_m

    @property
    def cell_centers_m(self) -> np.ndarray:
        dx = self.dx_m
        return (np.arange(self.n_cells) + 0.5) * dx

    @property
    def cell_volume_m3(self) -> np.ndarray:
        return np.full(self.n_cells, self.area_m2 * self.dx_m)

    @property
    def cell_wetted_area_m2(self) -> np.ndarray:
        """Wall contact area per cell (perimeter x dx), used for mass transfer."""
        return np.full(self.n_cells, self.wetted_perimeter_m * self.dx_m)
