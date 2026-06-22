from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProbeQuery(BaseModel):
    probe_name: str
    duration: str = "24h"
    aggregate: str = "mean"


class SummaryReading(BaseModel):
    probe_name: str
    probe_type: str
    value: float
    unit: str
    timestamp: datetime


class DashboardSummary(BaseModel):
    readings: list[SummaryReading]
    outlets: list[dict]
    power: dict
