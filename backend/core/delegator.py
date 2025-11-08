from . import state
from config import CONFIG
from events import emit_event

def _score(s, task):
    # Must have some energy and not be at cap
    if s.energy_amount < CONFIG.MIN_ENERGY_TO_ACCEPT: return -1e9
    if len(s.current_tasks) >= CONFIG.MAX_TASKS_PER_SAT: return -1e9

    e = s.energy_amount / max(s.max_energy, 1.0)
    spare = max(s.processing_capacity - task.processing_power_needed, 0) / max(s.processing_capacity, 1.0)
    qpen = len(s.current_tasks) * 0.15
    pr = {"low":0.0, "medium":0.5, "high":1.0}.get(task.priority, 0.0)
    W = CONFIG.WEIGHTS
    base = W["w1"]*e + W["w2"]*spare + W["w5"]*pr
    return base - qpen

def assign_pending(socketio):
    with state.LOCK:
        while state.TASK_QUEUE:
            task = state.TASK_QUEUE[0]
            best = None; bestScore = -1e9
            for s in state.SATELLITES.values():
                sc = _score(s, task)
                if sc > bestScore:
                    best = s; bestScore = sc
            if not best or bestScore < -1e8:
                # nobody can accept now; stop trying this tick
                break

            state.TASK_QUEUE.popleft()
            best.current_tasks.append({
                "task_id": task.task_id,
                "remaining_energy": float(task.energy_need),
                "progress": 0.0,
                "pp_need": float(task.processing_power_needed),
                "priority": task.priority
            })
            state.ASSIGNED[task.task_id] = best.satellite_id
            emit_event(socketio, "task.assigned",
                       {"task_id":task.task_id,"satellite_id":best.satellite_id})
