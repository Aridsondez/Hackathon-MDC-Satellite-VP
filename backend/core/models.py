from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid, random, time

def uid(prefix): return f"{prefix}-{uuid.uuid4().hex[:8]}"

class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: uid("task"))
    energy_need: float
    processing_power_needed: float
    priority: str
    created_at: float = Field(default_factory=time.time)

class Satellite(BaseModel):
    satellite_id: str = Field(default_factory=lambda: uid("sat"))
    energy_amount: float                                 # current energy (0..max_energy)
    max_energy: float = 120.0                            # battery capacity cap
    # processing
    processing_capacity: float
    current_tasks: List[Dict] = Field(default_factory=list)
    # solar
    solar_gen_rate: float = 0.35                         # energy units per tick at full sun
    # misc
    position: Dict[str, float] = Field(default_factory=lambda: {
        "lat": random.uniform(-60, 60), "lon": random.uniform(-180, 180)
    })
    giving_energy: str = "idle"

class Battery(BaseModel):
    battery_id: str = Field(default_factory=lambda: uid("bat"))
    reserve_battery: float
    battery: float
    position: Dict[str, float] = Field(default_factory=lambda: {"lat":0,"lon":0,"alt":0})
    status: str = "standby"
    speed_km_per_tick: float = 4000
    target: Optional[Dict[str, str]] = None
    eta_ticks: int = 0
    route: List[str] = Field(default_factory=list) 
    home_base: Dict[str, float] = Field(default_factory=lambda: {"lat":0.0,"lon":0.0,"alt":0.0})
    dwell_ticks: int = 0   