"""Pipeline drying simulator -- dry-air convection and vacuum engines (MVP)."""

from .economics import CampaignCost, CostModel, air_campaign_cost, vacuum_campaign_cost
from .io_schema import AirDryingCaseConfig, VacuumDryingCaseConfig
from .models.air_1d import AirDryingResult, run_air_drying
from .models.vacuum_lumped import VacuumDryingResult, run_vacuum_drying

__all__ = [
    "CampaignCost",
    "CostModel",
    "air_campaign_cost",
    "vacuum_campaign_cost",
    "AirDryingCaseConfig",
    "AirDryingResult",
    "run_air_drying",
    "VacuumDryingCaseConfig",
    "VacuumDryingResult",
    "run_vacuum_drying",
]
