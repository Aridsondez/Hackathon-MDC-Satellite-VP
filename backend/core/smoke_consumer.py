import random, threading, time
from .models import Task
from . import state

_running = False
_thread  = None

def _loop(qps, burst):
    global _running
    period = 1.0 / max(qps, 1)
    while _running:
        n = random.randint(1, max(burst,1))
        with state.LOCK:
            for _ in range(n):
                t = Task(
                    energy_need=random.randint(5,15),
                    processing_power_needed=random.randint(500,2000),
                    priority=random.choice(["low","medium","high"])
                )
                state.TASK_QUEUE.append(t)
        time.sleep(period)

def start_smoke(qps=30, burst=10):
    global _running, _thread
    if _running: return
    _running = True
    _thread = threading.Thread(target=_loop, args=(qps, burst), daemon=True)
    _thread.start()

def stop_smoke():
    global _running
    _running = False
