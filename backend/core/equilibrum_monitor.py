from . import delegator, satellites, orchestrator_batteries
from .equilibrium import MONITOR
from config import CONFIG
from events import emit_event
import threading, time

_running = False
_thread  = None

def _loop(socketio):
    """Main simulation loop with equilibrium monitoring"""
    tick_s = CONFIG.TICK_MS / 1000.0
    tick_num = 0
    
    while _running:
        try:
            # Core simulation steps
            delegator.assign_pending(socketio)
            satellites.advance_tick(socketio)
            orchestrator_batteries.route(socketio)
            
            # Monitor equilibrium
            MONITOR.record_tick(socketio)
            
            # Emit tick event with basic stats
            emit_event(socketio, "tick", {
                "tick": tick_num,
                "timestamp": time.time()
            })
            
            tick_num += 1
            
        except Exception as e:
            # Keep sim alive on transient errors
            print(f"[scheduler] tick {tick_num} error:", e)
            import traceback
            traceback.print_exc()
        
        time.sleep(tick_s)

def start(socketio):
    """Start the simulation scheduler"""
    global _running, _thread
    if _running:
        print("[scheduler] Already running")
        return
    
    print("[scheduler] Starting simulation loop...")
    _running = True
    _thread = threading.Thread(target=_loop, args=(socketio,), daemon=True)
    _thread.start()
    print("[scheduler] ✓ Simulation started")

def stop():
    """Stop the simulation scheduler"""
    global _running
    if not _running:
        return
    
    print("[scheduler] Stopping simulation loop...")
    _running = False
    if _thread:
        _thread.join(timeout=2.0)
    print("[scheduler] ✓ Simulation stopped")