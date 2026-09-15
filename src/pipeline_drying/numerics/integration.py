"""Thin wrapper around scipy.integrate.solve_ivp with consistent defaults.

The mass-transfer source term can make the ODE system stiff for fine grids
(many cells, fast mass transfer), so an implicit method is the default per
the decision to start from solve_ivp and add CFL-controlled explicit
stepping only if it turns out to be needed.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp


def integrate(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    y0: np.ndarray,
    t_span: tuple[float, float],
    method: str = "BDF",
    rtol: float = 1e-6,
    atol: float = 1e-9,
    max_step: float | None = None,
):
    kwargs = dict(method=method, rtol=rtol, atol=atol, dense_output=True)
    if max_step is not None:
        kwargs["max_step"] = max_step
    sol = solve_ivp(rhs, t_span, y0, **kwargs)
    if not sol.success:
        raise RuntimeError(f"Integration failed: {sol.message}")
    return sol


def first_hold_crossing_time(
    sol,
    scalar_of_state: Callable[[np.ndarray], float],
    target: float,
    hold_duration_s: float,
    n_eval: int = 2000,
) -> float | None:
    """Earliest t0 such that scalar_of_state(y(t)) <= target for all t in [t0, t0+hold].

    Returns None if the criterion is never satisfied within the simulated
    horizon (including the hold window). Evaluates the dense ODE solution on
    a fine uniform grid, which is adequate because the underlying fields are
    smooth (no shocks in this advection-source system).
    """
    t0, t1 = sol.t[0], sol.t[-1]
    t_grid = np.linspace(t0, t1, n_eval)
    y_grid = sol.sol(t_grid)
    values = np.array([scalar_of_state(y_grid[:, i]) for i in range(t_grid.size)])
    below = values <= target

    for i, t_candidate in enumerate(t_grid):
        if not below[i]:
            continue
        t_end = t_candidate + hold_duration_s
        if t_end > t1:
            return None
        j = np.searchsorted(t_grid, t_end)
        if j >= t_grid.size:
            return None
        if np.all(below[i : j + 1]):
            return float(t_candidate)
    return None


def integrate_segment(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    y0: np.ndarray,
    t_span: tuple[float, float],
    events: list | None = None,
    method: str = "BDF",
    rtol: float = 1e-7,
    atol: float | np.ndarray = 1e-9,
    max_step: float | None = None,
):
    """Integrate one operating segment, optionally stopping at a terminal event.

    Unlike `integrate`, this is meant for piecewise campaigns (pump on, pump
    off, ...) where the caller stitches segments together and needs to know
    whether the segment ended because an event fired or because it ran to the
    end of its window. Returns the solve_ivp object; `sol.status == 1` means
    an event terminated it.
    """
    kwargs = dict(method=method, rtol=rtol, atol=atol, dense_output=True)
    if events is not None:
        kwargs["events"] = events
    if max_step is not None:
        kwargs["max_step"] = max_step
    sol = solve_ivp(rhs, t_span, y0, **kwargs)
    if not sol.success and sol.status != 1:
        raise RuntimeError(f"Integration failed: {sol.message}")
    return sol


def sample_segment(sol, n_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Uniformly resample a segment's dense output over its realised span."""
    t0, t1 = float(sol.t[0]), float(sol.t[-1])
    if t1 <= t0:
        t_grid = np.array([t0])
    else:
        t_grid = np.linspace(t0, t1, max(2, n_points))
    return t_grid, sol.sol(t_grid)
