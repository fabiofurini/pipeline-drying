"""Shared finite-volume building blocks (upwind advection along a 1-D grid).

Kept separate from any single physics engine so the vacuum and hybrid
engines can reuse it later without duplicating the discretisation logic.
"""
from __future__ import annotations

import numpy as np


def upwind_advection_rate(field: np.ndarray, inlet_value: float, mass_flow_kg_s: float) -> np.ndarray:
    """Net advective rate of change (per cell) for a scalar carried by a flow.

    `field` holds the transported quantity per unit mass flow (e.g. a mass
    fraction) in each cell, ordered from inlet (index 0) to outlet.
    Returns d/dt contribution in the same units as `field` per second, i.e.
    (flow_in * field_upstream - flow_out * field_i); the caller divides by
    the cell's holdup (e.g. gas mass) to get an actual time derivative.
    """
    upstream = np.empty_like(field)
    upstream[0] = inlet_value
    upstream[1:] = field[:-1]
    return mass_flow_kg_s * (upstream - field)
