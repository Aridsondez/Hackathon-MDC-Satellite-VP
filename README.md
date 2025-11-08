# Hackathon MDC — Satellite VPP (Virtual Power Plant)


A simulated satellite virtual power plant: satellites receive tasks, consume energy, and can beam energy to one another (simulated), while battery drones (launched from Earth) shuttle charge to satellites and/or recharge from them.
Backend streams real-time updates over WebSockets for a Three.js globe UI.

## Backend: Python

(Flask + Flask-SocketIO), in-memory store (swap to Redis later), event-loop workers

Transport: REST for control, WebSockets for live telemetry/events

Core loops: SmokeConsumer → TaskDelegator → Satellites + JobOrchestrator → BatteryOrchestrator

Goal tonight: get all backend services running with a fast simulation tick + websocket feed

System Architecture
Entities

Task

{
  "task_id": "uuid",
  "energy_need": 10,
  "processing_power_needed": 1000,
  "priority": "low|medium|high",
  "created_at": "ISO8601"
}


Satellite

{
  "satellite_id": "sat-001",
  "energy_amount": 90,
  "consumption_rate": 2,
  "processing_capacity": 2000,
  "current_tasks": [
    {"task_id": "uuid", "energy_need": 10, "started_at": "ISO8601"}
  ],
  "position": {"x": 18.3, "y": -72.3},
  "giving_energy": "active|idle|blocked"
}


Battery Drone

{
  "battery_id": "bat-001",
  "reserve_battery": 50,         // mobility/ferry
  "battery": 100,                // payload charge
  "position": {"lat": 0, "lon": 0, "alt": 0}, // earth=alt 0
  "status": "charging|enroute|standby|out_of_service|docking",
  "target": {"satellite_id": "sat-001"}      // optional
}

Services & Loops

SmokeConsumer: generates a high-rate stream of tasks (configurable QPS/burst).

TaskDelegator: load balancer that assigns each incoming task to the “best” satellite (sub-500ms target).

Satellites (workers): execute tasks, decrement energy per tick, optionally request energy top-ups when predicted to fall below thresholds.

JobOrchestrator: handles satellite-to-satellite beaming (simulated transfer). Simple v1 rule: if sat.energy < lowWatermark and peer is > highWatermark, initiate transfer if “distance” cost acceptable.

BatteryOrchestrator: routes drones to where they’re most valuable; controls launch/recall; balances reserve (mobility) vs payload (charge).

Scoring / Decisions (v1 heuristic)

Delegator score for satellite s:

score(s) = w1 * available_energy_norm
         + w2 * spare_processing_norm
         + w3 * (1 - task_queue_norm)
         - w4 * distance_cost_norm
         + w5 * priority_boost


Defaults: w1=0.35, w2=0.25, w3=0.2, w4=0.15, w5=0.05

Energy beam decision (JobOrchestrator):

If s_low.energy < 25% and s_high.energy > 70% and distance < Dmax, transfer min(beam_rate, s_high.energy - 60%).

Drone routing (BatteryOrchestrator):

Prioritize satellites with predicted_energy(t+Δ) < 20%, weighted by priority of tasks on board.

Ensure drone has reserve_battery >= reserve_min_to_target + reserve_min_to_return.

All “distances” are simulated geodesic distances; rates & thresholds configurable.

API Contracts
REST (control/config)

POST /api/tasks — inject a task (manual)

body: Task minus task_id and created_at.

POST /api/smoke/start — { "qps": 50, "burst": 10 }

POST /api/smoke/stop

GET /api/state — snapshot of satellites, drones, queues

POST /api/config — set weights, thresholds, beam rates, tick interval

POST /api/reset — reset sim to seed state

WebSocket (telemetry/events) — namespace /ws

Emits JSON events:

tick — per simulation tick summary

task.created, task.assigned, task.completed, task.dropped

sat.energy_transfer_started/ended

drone.launched, drone.arrived, drone.charged, drone.recalled

alert.low_energy, alert.overloaded, alert.blackout_avoided

File Structure
satellite-vpp/
├─ README.md
├─ .env.example
├─ docker-compose.yml                # (optional: add Redis later)
├─ backend/
│  ├─ app.py                         # Flask + SocketIO boot
│  ├─ config.py
│  ├─ events.py                      # websocket emit helpers
│  ├─ routes/
│  │  ├─ __init__.py
│  │  ├─ control.py                  # /api/config, /api/reset
│  │  ├─ smoke.py                    # /api/smoke/start|stop
│  │  ├─ tasks.py                    # /api/tasks
│  │  └─ state.py                    # /api/state
│  ├─ core/
│  │  ├─ models.py                   # dataclasses: Task, Satellite, Battery
│  │  ├─ state.py                    # in-memory store + thread-safe ops
│  │  ├─ delegator.py                # TaskDelegator scoring
│  │  ├─ satellites.py               # worker tick + exec
│  │  ├─ orchestrator_jobs.py        # sat-to-sat beaming
│  │  ├─ orchestrator_batteries.py   # drone routing/logic
│  │  ├─ smoke_consumer.py           # task generator
│  │  └─ scheduler.py                # simulation clock/tickers
│  ├─ utils/
│  │  ├─ geo.py                      # distance/azimuth helpers
│  │  ├─ ids.py                      # uuid helpers
│  │  └─ time.py                     # monotonic, isoformat
│  ├─ seeds/
│  │  └─ seed_state.py               # initial satellites & drones
│  ├─ requirements.txt
│  └─ run_dev.sh
└─ frontend/
   ├─ README.md
   ├─ package.json
   ├─ src/
   │  ├─ main.jsx
   │  ├─ App.jsx
   │  ├─ components/
   │  │  ├─ Globe.jsx
   │  │  ├─ Satellite.jsx
   │  │  ├─ Drone.jsx
   │  │  ├─ Labels.jsx
   │  │  └─ HUDStats.jsx
   │  ├─ api/socket.js
   │  └─ api/http.js
   └─ vite.config.js
