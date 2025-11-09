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


    owner_wallet: str = Field(default_factory=lambda: f"wallet-{uuid.uuid4().hex[:12]}")
    company_name: str = Field(default_factory=lambda: random.choice([
        "OrbitPower Inc", "SkyGrid Energy", "SolarSat Systems", "NexGen Space"
    ]))
    energy_price_per_unit: float = Field(default=0.05)  
    total_revenue: float = 0.0
    total_energy_sold: float = 0.0
    total_energy_purchased: float = 0.0

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

    owner_wallet: str = Field(default_factory=lambda: f"wallet-{uuid.uuid4().hex[:12]}")
    company_name: str = Field(default_factory=lambda: random.choice([
        "DroneFleet Co", "PowerShuttle Ltd", "Orbital Logistics", "Battery Express"
    ]))
    total_spent: float = 0.0
    total_energy_bought: float = 0.0

class Transaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: uid("txn"))
    timestamp: float = Field(default_factory=time.time)
    
    # Transaction details
    from_entity_id: str  # satellite or "earth"
    from_company: str
    from_wallet: str
    
    to_entity_id: str  # drone battery_id
    to_company: str
    to_wallet: str
    
    energy_amount: float
    price_per_unit: float
    total_cost: float  # in SOL
    
    transaction_type: str  # "charge" or "harvest"
    status: str = "completed"  # "pending", "completed", "failed"