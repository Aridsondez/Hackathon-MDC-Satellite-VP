from core.models import Satellite, Battery
from core import state
from config import CONFIG
import random

def seed_state():
    """Initialize simulation with satellites and 2 standby drones"""
    
    # Create satellites with varied energy levels
    sats = [
        Satellite(
            energy_amount=90, 
            max_energy=120,
            processing_capacity=2500, 
            solar_gen_rate=0.45
        ),
        Satellite(
            energy_amount=65, 
            max_energy=120,
            processing_capacity=1800, 
            solar_gen_rate=0.35
        ),
        Satellite(
            energy_amount=40, 
            max_energy=120,
            processing_capacity=2200, 
            solar_gen_rate=0.40
        ),
        Satellite(
            energy_amount=75, 
            max_energy=120,
            processing_capacity=2000, 
            solar_gen_rate=0.38
        ),
    ]
    
    # Randomize satellite positions
    for s in sats:
        s.position["lon"] = random.uniform(-180, 180)
        s.position["lat"] = random.uniform(-60, 60)
        # Set varied base pricing
        s.energy_price_per_unit = random.uniform(0.03, 0.08)
    
    # Create 2 standby drones at Earth (ready for auto-dispatch)
    bats = [
        Battery(
            reserve_battery=CONFIG.DRONE_RESERVE_MAX,
            battery=CONFIG.DRONE_PAYLOAD_MAX,
            speed_km_per_tick=CONFIG.DRONE_SPEED_KM_PER_TICK,
            status="at_earth",
            position={"lat": 0.0, "lon": 0.0, "alt": 0.0},
            home_base={"lat": 0.0, "lon": 0.0, "alt": 0.0}
        ),
        Battery(
            reserve_battery=CONFIG.DRONE_RESERVE_MAX,
            battery=CONFIG.DRONE_PAYLOAD_MAX,
            speed_km_per_tick=CONFIG.DRONE_SPEED_KM_PER_TICK,
            status="at_earth",
            position={"lat": 0.0, "lon": 0.0, "alt": 0.0},
            home_base={"lat": 0.0, "lon": 0.0, "alt": 0.0}
        ),
    ]
    
    # Clear and populate state
    with state.LOCK:
        state.SATELLITES.clear()
        state.BATTERIES.clear()
        state.TASK_QUEUE.clear()
        state.ASSIGNED.clear()
        state.SAT_CLAIM.clear()
        
        for s in sats:
            state.SATELLITES[s.satellite_id] = s
        
        for b in bats:
            state.BATTERIES[b.battery_id] = b
    
    print(f"✓ Seeded {len(sats)} satellites and {len(bats)} standby drones")