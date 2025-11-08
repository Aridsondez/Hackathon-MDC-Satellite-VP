from collections import deque
from threading import RLock
from typing import Dict
from .models import Satellite, Battery, Task

LOCK = RLock()
SATELLITES: Dict[str, Satellite] = {}
BATTERIES: Dict[str, Battery] = {}
TASK_QUEUE = deque()
ASSIGNED: Dict[str, str] = {}
CONFIG = None
SOCKETIO = None
SAT_CLAIM: dict[str, str] = {}  

def snapshot():
    with LOCK:
        return dict(
            satellites=[s.model_dump() for s in SATELLITES.values()],
            batteries=[b.model_dump() for b in BATTERIES.values()],
            queue=[t.model_dump() for t in list(TASK_QUEUE)],
            assigned=ASSIGNED.copy()
        )
def init_globals(config, socketio):
    global CONFIG, SOCKETIO
    CONFIG = config
    SOCKETIO = socketio

def try_claim_sat(sat_id: str, battery_id: str) -> bool:
    owner = SAT_CLAIM.get(sat_id)
    if owner is None or owner == battery_id:
        SAT_CLAIM[sat_id] = battery_id
        return True
    return False

def release_sat(sat_id: str, battery_id: str) -> None:
    if SAT_CLAIM.get(sat_id) == battery_id:
        del SAT_CLAIM[sat_id]