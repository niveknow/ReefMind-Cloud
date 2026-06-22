from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class TelemetryReading(BaseModel):
    probe_name: str
    probe_type: str
    value: float
    unit: str
    timestamp: Optional[datetime] = None


class TelemetryBatch(BaseModel):
    readings: list[TelemetryReading]


class OutletState(BaseModel):
    outlet_name: str
    state: int
    state_display: str
    timestamp: Optional[datetime] = None


class OutletBatch(BaseModel):
    outlets: list[OutletState]


class PowerReading(BaseModel):
    outlet_name: str
    watts: float
    amps: float = 0.0
    channel: str = "main"
    timestamp: Optional[datetime] = None


class PowerBatch(BaseModel):
    readings: list[PowerReading]


class WaterTest(BaseModel):
    parameter: str
    value: float
    unit: str
    timestamp: Optional[datetime] = None
