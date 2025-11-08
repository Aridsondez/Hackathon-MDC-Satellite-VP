"""
Drone Orchestrator - Manages battery drone fleet for satellite energy equilibrium

Key behaviors:
- Auto-dispatch: Drones automatically deploy to low-energy satellites
- Charging: Multiple drones can charge one satellite (up to AUTO_MAX_DRONES_PER_SAT)
- No siphoning: Drones won't harvest from satellites being charged
- Mission completion: Drones leave after charging and find new targets
- Recharge: Drones return to Earth or harvest from high-energy satellites
- Reserve management: Drone movement consumes reserve battery
- Timeout recovery: Drones stuck enroute return to Earth
"""

from . import state
from config import CONFIG
from events import emit_event
from utils.geo import haversine_km

def _nearest_satellite(from_lat, from_lon, candidates):
    """Find nearest satellite from given position"""
    best, bestd = None, 1e18
    for s in candidates:
        d = haversine_km(from_lat, from_lon, s.position["lat"], s.position["lon"])
        if d < bestd: 
            best, bestd = s, d
    return best, bestd

def _reserve_cost_km(km):
    """Calculate reserve battery cost for distance"""
    return km * CONFIG.DRONE_RESERVE_PER_KM

def _can_reach(drone, lat, lon, reserve_min=None):
    """Check if drone has enough reserve to reach destination"""
    if reserve_min is None:
        reserve_min = CONFIG.DRONE_RESERVE_MIN_TO_CONTINUE
    dkm = haversine_km(drone.position["lat"], drone.position["lon"], lat, lon)
    need = _reserve_cost_km(dkm)
    return drone.reserve_battery >= need + reserve_min

def _set_course(drone, lat, lon, label=None):
    """Set drone course to destination"""
    drone.speed_km_per_tick = CONFIG.DRONE_SPEED_KM_PER_TICK
    
    # Calculate and pay reserve cost
    dkm = haversine_km(drone.position["lat"], drone.position["lon"], lat, lon)
    cost = _reserve_cost_km(dkm)
    drone.reserve_battery -= cost
    
    # Set travel mode
    if CONFIG.DRONE_TRAVEL_INSTANT:
        drone.eta_ticks = 0
    else:
        ticks = max(1, int(dkm / max(drone.speed_km_per_tick, 1)))
        drone.eta_ticks = ticks
    
    drone.dwell_ticks = 0
    drone._enroute_ticks = 0
    
    if label:
        emit_event(state.SOCKETIO, "drone.enroute", {
            "battery_id": drone.battery_id, 
            "eta": drone.eta_ticks, 
            "to": label
        })

def _arrive_at(drone, lat, lon):
    """Handle drone arrival at destination"""
    drone.position["lat"] = lat
    drone.position["lon"] = lon
    drone.eta_ticks = 0
    drone.dwell_ticks = 0
    drone._enroute_ticks = 0

def _release_current_claim(drone):
    """Release satellite claim when leaving"""
    if drone.target and "satellite_id" in drone.target:
        state.release_sat(drone.target["satellite_id"], drone.battery_id)

def _tick_travel(drone, dest_position):
    """Advance drone travel, return True if arrived, 'timeout' if stuck"""
    if CONFIG.DRONE_TRAVEL_INSTANT:
        _arrive_at(drone, dest_position["lat"], dest_position["lon"])
        return True
    
    if drone.eta_ticks > 0:
        drone.eta_ticks -= 1
        drone._enroute_ticks = getattr(drone, "_enroute_ticks", 0) + 1
        
        # Check for timeout
        if drone._enroute_ticks >= CONFIG.DRONE_ENROUTE_MAX_TICKS:
            return "timeout"
        
        if drone.eta_ticks == 0:
            _arrive_at(drone, dest_position["lat"], dest_position["lon"])
            return True
    
    return False

def _find_charging_target(drone):
    """Find the best satellite to charge (lowest energy, not being charged by multiple drones)"""
    candidates = []
    
    for s in state.SATELLITES.values():
        # Skip if at full capacity
        if s.energy_amount >= s.max_energy - CONFIG.SAT_FULL_EPS:
            continue
        
        # Check if we can reach it
        if not _can_reach(drone, s.position["lat"], s.position["lon"]):
            continue
        
        # Count how many drones are already charging this satellite
        charging_count = 0
        for b in state.BATTERIES.values():
            if b.battery_id != drone.battery_id and b.status == "charging" and \
               b.target and b.target.get("satellite_id") == s.satellite_id:
                charging_count += 1
        
        # Skip if already at max concurrent chargers
        if charging_count >= CONFIG.AUTO_MAX_DRONES_PER_SAT:
            continue
        
        candidates.append((s, charging_count))
    
    if not candidates:
        return None
    
    # Sort by energy (lowest first), then by charging count (prefer less crowded)
    candidates.sort(key=lambda x: (x[0].energy_amount, x[1]))
    return candidates[0][0]

def _find_harvest_source(drone):
    """Find best satellite to harvest from (highest energy above threshold, not being siphoned)"""
    candidates = []
    
    for s in state.SATELLITES.values():
        # Must be above harvest start level
        if s.energy_amount < CONFIG.HARVEST_START_LEVEL:
            continue
        
        # Check if we can reach it
        if not _can_reach(drone, s.position["lat"], s.position["lon"]):
            continue
        
        # Don't harvest from satellites being charged
        being_charged = False
        for b in state.BATTERIES.values():
            if b.status == "charging" and b.target and \
               b.target.get("satellite_id") == s.satellite_id:
                being_charged = True
                break
        
        if being_charged:
            continue
        
        # Don't allow multiple drones to harvest from same satellite
        harvesting_count = 0
        for b in state.BATTERIES.values():
            if b.battery_id != drone.battery_id and b.status == "harvesting" and \
               b.target and b.target.get("satellite_id") == s.satellite_id:
                harvesting_count += 1
        
        if harvesting_count > 0:
            continue
        
        candidates.append(s)
    
    if not candidates:
        return None
    
    # Return highest energy satellite
    return max(candidates, key=lambda s: s.energy_amount)

def _should_go_to_earth(drone):
    """Determine if drone should return to Earth for recharge"""
    # Low payload and low reserve - must go to Earth
    if drone.battery < CONFIG.PAYLOAD_CHARGE_MIN and \
       drone.reserve_battery < CONFIG.DRONE_RESERVE_MIN_TO_CONTINUE * 2:
        return True
    
    # Payload is low - need to refill
    if drone.battery < CONFIG.PAYLOAD_CHARGE_MIN:
        # Check if any satellite can provide enough energy
        harvest_source = _find_harvest_source(drone)
        if harvest_source:
            return False  # Can harvest from satellite
        return True  # Must go to Earth
    
    return False

def _choose_next_mission(drone):
    """Decide drone's next mission: charge satellite, harvest, or return to Earth"""
    
    # First check if we need to go to Earth
    if _should_go_to_earth(drone):
        _release_current_claim(drone)
        drone.status = "returning"
        drone.target = {"earth": True}
        _set_course(drone, drone.home_base["lat"], drone.home_base["lon"], label="earth")
        return
    
    # If we have payload, prioritize charging
    if drone.battery >= CONFIG.PAYLOAD_CHARGE_MIN:
        target = _find_charging_target(drone)
        if target and state.try_claim_sat(target.satellite_id, drone.battery_id):
            drone.status = "enroute"
            drone.target = {"satellite_id": target.satellite_id}
            _set_course(drone, target.position["lat"], target.position["lon"], label=target.satellite_id)
            return
    
    # Otherwise, try to harvest
    target = _find_harvest_source(drone)
    if target and state.try_claim_sat(target.satellite_id, drone.battery_id):
        drone.status = "enroute"
        drone.target = {"satellite_id": target.satellite_id}
        _set_course(drone, target.position["lat"], target.position["lon"], label=target.satellite_id)
        return
    
    # No mission available, return to Earth
    _release_current_claim(drone)
    drone.status = "returning"
    drone.target = {"earth": True}
    _set_course(drone, drone.home_base["lat"], drone.home_base["lon"], label="earth")

def _auto_dispatch():
    """Automatically dispatch idle drones to needy satellites"""
    if not CONFIG.AUTO_DISPATCH_ENABLED:
        return
    
    # Find satellites below threshold
    needy = [s for s in state.SATELLITES.values() 
             if s.energy_amount < CONFIG.AUTO_NEEDY_THRESH]
    
    if not needy:
        return
    
    # Sort by energy (lowest first)
    needy.sort(key=lambda s: s.energy_amount)
    
    # Find available drones
    available_drones = [b for b in state.BATTERIES.values() 
                       if b.status in ("at_earth", "standby") and 
                       b.battery >= CONFIG.PAYLOAD_CHARGE_MIN]
    
    # Dispatch drones to needy satellites
    for sat in needy:
        if not available_drones:
            break
        
        # Check how many drones already targeting this satellite
        targeting_count = sum(1 for b in state.BATTERIES.values() 
                            if b.target and b.target.get("satellite_id") == sat.satellite_id)
        
        if targeting_count >= CONFIG.AUTO_MAX_DRONES_PER_SAT:
            continue
        
        # Find closest available drone
        closest_drone = None
        closest_dist = 1e18
        
        for drone in available_drones:
            if not _can_reach(drone, sat.position["lat"], sat.position["lon"]):
                continue
            
            dist = haversine_km(drone.position["lat"], drone.position["lon"],
                              sat.position["lat"], sat.position["lon"])
            if dist < closest_dist:
                closest_drone = drone
                closest_dist = dist
        
        if closest_drone and state.try_claim_sat(sat.satellite_id, closest_drone.battery_id):
            closest_drone.status = "enroute"
            closest_drone.target = {"satellite_id": sat.satellite_id}
            _set_course(closest_drone, sat.position["lat"], sat.position["lon"], 
                       label=sat.satellite_id)
            available_drones.remove(closest_drone)
            
            emit_event(state.SOCKETIO, "drone.auto_dispatched", {
                "battery_id": closest_drone.battery_id,
                "satellite_id": sat.satellite_id,
                "reason": "low_energy"
            })

def route(socketio):
    """Main drone orchestration loop"""
    with state.LOCK:
        # Auto-dispatch idle drones first
        _auto_dispatch()
        
        for drone in state.BATTERIES.values():
            if drone.status == "out_of_service":
                continue
            
            # Handle travel states
            if drone.status in ("enroute", "returning"):
                if drone.target and drone.target.get("earth"):
                    # Traveling to Earth
                    result = _tick_travel(drone, drone.home_base)
                    if result == True:
                        # Arrived at Earth - full recharge
                        drone.status = "at_earth"
                        drone.battery = CONFIG.DRONE_PAYLOAD_MAX
                        drone.reserve_battery = CONFIG.DRONE_RESERVE_MAX
                        drone.target = None
                        emit_event(socketio, "drone.recharged", {
                            "battery_id": drone.battery_id
                        })
                        # Immediately look for next mission
                        _choose_next_mission(drone)
                    elif result == "timeout":
                        # Stuck enroute - force return to Earth
                        _release_current_claim(drone)
                        drone.status = "returning"
                        drone.target = {"earth": True}
                        drone.position = drone.home_base.copy()  # Teleport to Earth
                        drone.battery = CONFIG.DRONE_PAYLOAD_MAX
                        drone.reserve_battery = CONFIG.DRONE_RESERVE_MAX
                        emit_event(socketio, "drone.timeout_recovery", {
                            "battery_id": drone.battery_id
                        })
                    continue
                
                elif drone.target and "satellite_id" in drone.target:
                    # Traveling to satellite
                    sat = state.SATELLITES.get(drone.target["satellite_id"])
                    if not sat:
                        _release_current_claim(drone)
                        _choose_next_mission(drone)
                        continue
                    
                    result = _tick_travel(drone, sat.position)
                    if result == True:
                        # Arrived at satellite - determine mode
                        if drone.battery >= CONFIG.PAYLOAD_CHARGE_MIN and \
                           sat.energy_amount < sat.max_energy - CONFIG.SAT_FULL_EPS:
                            drone.status = "charging"
                            drone.dwell_ticks = 0
                            emit_event(socketio, "drone.charging_start", {
                                "battery_id": drone.battery_id,
                                "satellite_id": sat.satellite_id
                            })
                        elif sat.energy_amount >= CONFIG.HARVEST_START_LEVEL:
                            drone.status = "harvesting"
                            drone.dwell_ticks = 0
                            emit_event(socketio, "drone.harvesting_start", {
                                "battery_id": drone.battery_id,
                                "satellite_id": sat.satellite_id
                            })
                        else:
                            # Satellite not suitable - find new mission
                            _release_current_claim(drone)
                            _choose_next_mission(drone)
                    elif result == "timeout":
                        # Stuck enroute - return to Earth
                        _release_current_claim(drone)
                        drone.status = "returning"
                        drone.target = {"earth": True}
                        drone.position = drone.home_base.copy()  # Teleport to Earth
                        drone.battery = CONFIG.DRONE_PAYLOAD_MAX
                        drone.reserve_battery = CONFIG.DRONE_RESERVE_MAX
                        emit_event(socketio, "drone.timeout_recovery", {
                            "battery_id": drone.battery_id
                        })
                    continue
            
            # Handle charging mode
            if drone.status == "charging":
                if not drone.target or "satellite_id" not in drone.target:
                    _choose_next_mission(drone)
                    continue
                
                sat = state.SATELLITES.get(drone.target["satellite_id"])
                if not sat:
                    _release_current_claim(drone)
                    _choose_next_mission(drone)
                    continue
                
                drone.dwell_ticks += 1
                
                # Check if we should stop charging
                sat_full = sat.energy_amount >= sat.max_energy - CONFIG.SAT_FULL_EPS
                payload_empty = drone.battery < CONFIG.PAYLOAD_CHARGE_MIN
                max_dwell = drone.dwell_ticks >= CONFIG.DRONE_MAX_DWELL_TICKS
                
                if sat_full or payload_empty or max_dwell:
                    # Done charging - release and find new mission
                    emit_event(socketio, "drone.charging_complete", {
                        "battery_id": drone.battery_id,
                        "satellite_id": sat.satellite_id,
                        "reason": "full" if sat_full else "empty" if payload_empty else "max_dwell"
                    })
                    _release_current_claim(drone)
                    _choose_next_mission(drone)
                    continue
                
                # Transfer energy
                deficit = sat.max_energy - sat.energy_amount
                give = min(CONFIG.DRONE_PAYLOAD_CHARGE_RATE, drone.battery, deficit)
                
                if give > 0:
                    drone.battery -= give
                    sat.energy_amount += give
                    emit_event(socketio, "drone.charged", {
                        "battery_id": drone.battery_id,
                        "satellite_id": sat.satellite_id,
                        "amount": give
                    })
            
            # Handle harvesting mode
            if drone.status == "harvesting":
                if not drone.target or "satellite_id" not in drone.target:
                    _choose_next_mission(drone)
                    continue
                
                sat = state.SATELLITES.get(drone.target["satellite_id"])
                if not sat:
                    _release_current_claim(drone)
                    _choose_next_mission(drone)
                    continue
                
                drone.dwell_ticks += 1
                
                # Check if we should stop harvesting
                sat_low = sat.energy_amount <= CONFIG.HARVEST_FLOOR
                payload_full = drone.battery >= CONFIG.DRONE_PAYLOAD_MAX - 1
                max_dwell = drone.dwell_ticks >= CONFIG.DRONE_MAX_DWELL_TICKS
                
                if sat_low or payload_full or max_dwell:
                    # Done harvesting - release and find new mission
                    emit_event(socketio, "drone.harvesting_complete", {
                        "battery_id": drone.battery_id,
                        "satellite_id": sat.satellite_id,
                        "reason": "low" if sat_low else "full" if payload_full else "max_dwell"
                    })
                    _release_current_claim(drone)
                    _choose_next_mission(drone)
                    continue
                
                # Extract energy
                available = max(0.0, sat.energy_amount - CONFIG.HARVEST_FLOOR)
                take = min(CONFIG.DRONE_HARVEST_RATE,
                          CONFIG.DRONE_PAYLOAD_MAX - drone.battery,
                          available)
                
                if take > 0:
                    drone.battery += take
                    sat.energy_amount -= take
                    emit_event(socketio, "drone.harvested", {
                        "battery_id": drone.battery_id,
                        "satellite_id": sat.satellite_id,
                        "amount": take
                    })
            
            # Handle idle drones
            if drone.status in ("standby", "at_earth") and not drone.target:
                _choose_next_mission(drone)