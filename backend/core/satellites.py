from . import state
from config import CONFIG
from events import emit_event
import math, time

def _daylight_factor(lat, lon, now_s):
    """
    Toy daylight model:
    local solar time ≈ UTC hours + lon/15.
    Daylight 06:00–18:00; cosine ramp to 0 at night.
    """
    hrs = (now_s/3600.0 + lon/15.0) % 24.0
    if 6.0 <= hrs <= 18.0:
        # map 6->0, 12->1, 18->0 via cosine
        x = (hrs - 12.0) / 6.0   # -1..+1
        return max(0.0, math.cos(x * math.pi/2.0))  # 0..1
    return 0.0

def advance_tick(socketio):
    now = time.time()
    with state.LOCK:
        for s in state.SATELLITES.values():
            # 1) Solar generation
            lat, lon = s.position["lat"], s.position["lon"]
            k = _daylight_factor(lat, lon, now)
            gen = s.solar_gen_rate 
            if gen > 0:
                s.energy_amount = min(s.max_energy, s.energy_amount + gen)

            # 2) Process tasks: consume only while working
            completed = []
            for t in s.current_tasks:
                # energy burn per task this tick
                need = min(CONFIG.TASK_ENERGY_RATE, t["remaining_energy"])
                # if no energy to burn, the task stalls (very slow crawl)
                if s.energy_amount >= need and need > 0:
                    s.energy_amount -= need
                    t["remaining_energy"] -= need
                    eff = 1.0
                else:
                    eff = 0.2  # starved, crawl

                # progress update
                t["progress"] = min(1.0, t["progress"] + CONFIG.TASK_PROGRESS_RATE * eff)

                if t["progress"] >= 1.0 or t["remaining_energy"] <= 0.0:
                    completed.append(t)

            for t in completed:
                s.current_tasks.remove(t)
                tid = t["task_id"]
                state.ASSIGNED.pop(tid, None)
                emit_event(socketio, "task.completed",
                           {"task_id": tid, "satellite_id": s.satellite_id})

            # 3) Alerts
            if s.energy_amount < 10.0:
                emit_event(socketio, "alert.low_energy",
                           {"satellite_id": s.satellite_id, "energy": s.energy_amount})
