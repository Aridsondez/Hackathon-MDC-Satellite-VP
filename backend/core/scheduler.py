from . import delegator, satellites, orchestrator_batteries
from config import CONFIG
from events import emit_event
import threading, time

_running = False
_thread  = None

def _loop(socketio):
    tick_s = CONFIG.TICK_MS / 1000.0
    while _running:
        try:
            delegator.assign_pending(socketio)
            satellites.advance_tick(socketio)
            orchestrator_batteries.route(socketio)
            emit_event(socketio, "tick", {})
        except Exception as e:
            # keep sim alive on transient errors
            print("[scheduler] tick error:", e)
        time.sleep(tick_s)

def start(socketio):
    global _running, _thread
    if _running: return
    _running = True
    _thread = threading.Thread(target=_loop, args=(socketio,), daemon=True)
    _thread.start()
