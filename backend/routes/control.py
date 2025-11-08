from core import state
from core.models import Battery
from utils.geo import haversine_km
from events import emit_event
from flask import jsonify, request, Blueprint

bp = Blueprint("control", __name__)

@bp.post("/drones/launch")
def launch():
    """
    body: { "count": 1, "target_satellite_id": "sat-..." }
    Launches 'count' drones from Earth, aiming first at target_satellite_id.
    """
    data = request.get_json(force=True)
    count = int(data.get("count", 1))
    target = data.get("target_satellite_id")
    with state.LOCK:
        sat = state.SATELLITES.get(target)
        if not sat:
            return jsonify({"error":"target satellite not found"}), 404
        launched = []
        for _ in range(count):
            # pick an available or create a new drone at Earth
            drone = None
            for b in state.BATTERIES.values():
                if b.status == "at_earth":
                    drone = b; break
            if not drone:
                drone = Battery(
                    reserve_battery=state.CONFIG.DRONE_RESERVE_MAX if hasattr(state, "CONFIG") else 60.0,
                    battery=state.CONFIG.DRONE_PAYLOAD_MAX if hasattr(state, "CONFIG") else 100.0
                )
                state.BATTERIES[drone.battery_id] = drone
            # set departure
            drone.status = "enroute"
            drone.target = {"satellite_id": sat.satellite_id}
            drone.speed_km_per_tick = state.CONFIG.DRONE_SPEED_KM_PER_TICK
            # compute ETA crudely
            d_km = haversine_km(drone.position["lat"], drone.position["lon"], sat.position["lat"], sat.position["lon"])
            ticks = max(1, int(d_km / drone.speed_km_per_tick))
            drone.eta_ticks = ticks
            launched.append(drone.battery_id)
            emit_event(state.SOCKETIO, "drone.launched", {
                "battery_id": drone.battery_id, "target": drone.target, "eta": ticks
            })
    return jsonify({"ok": True, "launched": launched})
