# Hackathon MDC — Satellite VPP (Virtual Power Plant) with Solana Economics

A simulated satellite virtual power plant with blockchain-based energy trading: satellites receive tasks, consume energy, and can beam energy to one another (simulated), while battery drones (launched from Earth) shuttle charge to satellites and/or recharge from them. The system features a **Solana-based marketplace** where satellite operators earn SOL from selling energy and drone operators pay for energy transfers.

Backend streams real-time updates over WebSockets. Frontend displays a Three.js 3D globe visualization with economic metrics.

## 🌟 Key Features

- **Energy Marketplace**: Satellites owned by different companies sell energy; drones purchase energy using Solana (SOL)
- **Dynamic Pricing**: Energy prices fluctuate based on satellite energy levels (scarcity = higher prices)
- **Free Earth Energy**: Drones recharge at Earth for free; only satellite-to-drone transfers cost SOL
- **Real-time Economics**: Track total transaction volume, top earners, top spenders, and efficiency metrics
- **Equilibrium Monitoring**: Automatic drone dispatch to maintain system energy balance
- **3D Visualization**: Interactive Three.js globe with satellite and drone models, economic overlays

## System Architecture

### Entities

#### Task
```json
{
  "task_id": "uuid",
  "energy_need": 10,
  "processing_power_needed": 1000,
  "priority": "low|medium|high",
  "created_at": "ISO8601"
}
```

#### Satellite (with Economic Fields)
```json
{
  "satellite_id": "sat-001",
  "energy_amount": 90,
  "max_energy": 120,
  "consumption_rate": 2,
  "processing_capacity": 2000,
  "current_tasks": [...],
  "position": {"lat": 18.3, "lon": -72.3},
  "solar_gen_rate": 0.45,
  
  "owner_wallet": "wallet-abc123",
  "company_name": "OrbitPower Inc",
  "energy_price_per_unit": 0.05,
  "total_revenue": 125.50,
  "total_energy_sold": 2500
}
```

#### Battery Drone (with Economic Fields)
```json
{
  "battery_id": "bat-001",
  "reserve_battery": 500,
  "battery": 100,
  "position": {"lat": 0, "lon": 0, "alt": 0},
  "status": "charging|enroute|standby|at_earth|harvesting|returning",
  "target": {"satellite_id": "sat-001"},
  "speed_km_per_tick": 4000,
  
  "owner_wallet": "wallet-xyz789",
  "company_name": "DroneFleet Co",
  "total_spent": 45.25,
  "total_energy_bought": 900
}
```

#### Transaction
```json
{
  "transaction_id": "txn-uuid",
  "timestamp": 1234567890,
  "from_entity_id": "sat-001",
  "from_company": "OrbitPower Inc",
  "to_entity_id": "bat-001",
  "to_company": "DroneFleet Co",
  "energy_amount": 10.5,
  "price_per_unit": 0.06,
  "total_cost": 0.63,
  "transaction_type": "harvest|charge|earth_recharge",
  "status": "completed"
}
```

## Services & Loops

1. **SmokeConsumer**: Generates high-rate stream of tasks (configurable QPS/burst)
2. **TaskDelegator**: Load balancer assigning tasks to best satellite (sub-500ms target)
3. **Satellites**: Execute tasks, consume energy, generate solar power, handle transactions
4. **JobOrchestrator**: Manages satellite-to-satellite energy beaming (future feature)
5. **BatteryOrchestrator**: Routes drones, handles charging/harvesting with SOL payments
6. **EconomicsEngine**: Processes transactions, calculates metrics, tracks marketplace

## Drone Behavior (Economic Model)

### Auto-Dispatch
- Drones automatically deploy from Earth when satellites drop below 25 energy units
- System maintains equilibrium by balancing energy supply and demand
- Up to 2 drones can charge the same satellite simultaneously

### Energy Acquisition
1. **Earth Recharge (FREE)**: Drones return to Earth for full payload refill at 0 SOL cost
2. **Satellite Harvesting (PAID)**: Drones extract energy from high-capacity satellites
   - Only harvest from satellites with >80 energy units
   - Never harvest from satellites being charged by other drones
   - Pay dynamic price based on satellite energy level

### Energy Distribution
- Drones charge low-energy satellites (pay 0 SOL since drone already owns the energy)
- Satellite owners earn SOL when drones harvest from them
- Dynamic pricing: Low energy satellites charge premium rates (up to 2.5x base price)

### Reserve Management
- Movement consumes reserve battery (0.001 per km)
- Timeout recovery: Drones stuck >8 ticks return to Earth
- Instant travel mode enabled for stability

## Economic Metrics

### Real-time Tracking
- **Total Volume**: Cumulative SOL transacted across all energy transfers
- **Transaction Count**: Number of energy trades executed
- **Average Price**: Mean SOL per energy unit across recent transactions
- **Energy Traded**: Total energy units bought/sold

### Leaderboards
- **Top Earning Satellites**: Companies with highest revenue from energy sales
- **Top Spending Drones**: Companies with highest costs from energy purchases
- **Most Efficient Satellite**: Best energy-sold-to-revenue ratio
- **Least Efficient Satellite**: Worst energy-sold-to-revenue ratio

### Dynamic Pricing Algorithm
```python
base_price = 0.05 SOL per unit
utilization = satellite.energy / satellite.max_energy

if utilization < 0.2:    multiplier = 2.5  # Scarce
elif utilization < 0.4:  multiplier = 1.8  # Low
elif utilization < 0.6:  multiplier = 1.3  # Medium
elif utilization < 0.8:  multiplier = 1.0  # Normal
else:                    multiplier = 0.7  # Abundant (discount)

price = base_price * multiplier
```

## API Endpoints

### Control & State
- `POST /api/tasks` — Inject a task manually
- `GET /api/state` — Snapshot of satellites, drones, queues
- `POST /api/config` — Set weights, thresholds, beam rates
- `POST /api/reset` — Reset simulation to seed state

### Smoke Testing
- `POST /api/smoke/start` — Start task generation `{"qps": 50, "burst": 10}`
- `POST /api/smoke/stop` — Stop task generation

### Economics
- `GET /api/economics/metrics` — Comprehensive economic data
  - Total volume, transactions, leaderboards, efficiency metrics
- `GET /api/economics/transactions` — Recent transaction history (last 50)
- `GET /api/economics/leaderboard` — Top earners and spenders only

### Drone Control
- `POST /api/drones/launch` — Launch drones to specific satellite
  - `{"count": 1, "target_satellite_id": "sat-abc"}`

## WebSocket Events (namespace `/`)

### System Events
- `tick` — Simulation tick summary
- `task.created`, `task.assigned`, `task.completed`, `task.dropped`
- `alert.low_energy`, `alert.overloaded`, `alert.blackout_avoided`

### Drone Events
- `drone.launched`, `drone.arrived`, `drone.recalled`
- `drone.charged`, `drone.harvested`, `drone.recharged`
- `drone.charging_start`, `drone.charging_complete`
- `drone.harvesting_start`, `drone.harvesting_complete`
- `drone.auto_dispatched`, `drone.timeout_recovery`

### Economic Events
- `transaction.completed` — Energy transfer with SOL payment
  - Payload: `{from, to, amount, cost_sol, type}`
- `equilibrium.update` — System balance analysis
  - Payload: `{energy_trend, critical_satellites, recommendation}`

## File Structure

```
satellite-vpp/
├─ README.md
├─ backend/
│  ├─ app.py                         # Flask + SocketIO boot
│  ├─ config.py                      # System configuration
│  ├─ events.py                      # WebSocket emit helpers
│  ├─ routes/
│  │  ├─ control.py                  # Config, reset, drone launch
│  │  ├─ smoke.py                    # Smoke test start/stop
│  │  ├─ tasks.py                    # Task injection
│  │  ├─ state.py                    # State snapshot
│  │  └─ economics.py                # Economic metrics API
│  ├─ core/
│  │  ├─ models.py                   # Pydantic models (Task, Satellite, Battery, Transaction)
│  │  ├─ state.py                    # In-memory store + thread-safe ops
│  │  ├─ delegator.py                # Task delegation scoring
│  │  ├─ satellites.py               # Satellite tick + solar generation
│  │  ├─ orchestrator_batteries.py   # Drone routing with economics
│  │  ├─ economics.py                # Economic engine & transactions
│  │  ├─ equilibrium.py              # System balance monitoring
│  │  ├─ smoke_consumer.py           # Task generator
│  │  └─ scheduler.py                # Simulation clock
│  ├─ utils/
│  │  └─ geo.py                      # Haversine distance calculations
│  ├─ seeds/
│  │  └─ seed_state.py               # Initial satellites (4) & drones (2)
│  └─ requirements.txt
└─ frontend/
   ├─ package.json
   ├─ public/
   │  ├─ earth.glb                   # Earth 3D model
   │  └─ satellite/                  # Satellite 3D models
   │     ├─ satelliteobj.obj
   │     ├─ satellitemtl.mtl
   │     └─ satelliteimg.jpg
   └─ src/
      └─ pages/
         └─ index.jsx                # Three.js visualization + economics dashboard
```

## Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python app.py
# Server runs on http://localhost:5001
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# UI runs on http://localhost:5173 (or your Vite/Next port)
```

### Start Simulation
```bash
# Start task load
curl -X POST http://localhost:5001/api/smoke/start \
  -H "Content-Type: application/json" \
  -d '{"qps": 50, "burst": 10}'

# View state
curl http://localhost:5001/api/state

# View economics
curl http://localhost:5001/api/economics/metrics
```

## Configuration Parameters

### Economic Settings
```python
# Drone payload
DRONE_PAYLOAD_MAX: 120.0              # Maximum payload capacity
DRONE_PAYLOAD_CHARGE_RATE: 8.0       # Energy units per tick
PAYLOAD_CHARGE_MIN: 15.0             # Minimum to start charging

# Harvesting
DRONE_HARVEST_RATE: 10.0             # Units harvested per tick
HARVEST_FLOOR: 70.0                  # Don't drain satellites below this
HARVEST_START_LEVEL: 80.0            # Prefer sources above this

# Movement
DRONE_RESERVE_PER_KM: 0.001          # Reserve cost per km
DRONE_TRAVEL_INSTANT: True           # Teleport mode for stability

# Auto-dispatch
AUTO_DISPATCH_ENABLED: True
AUTO_NEEDY_THRESH: 25.0              # Deploy when satellite < 25 energy
AUTO_MAX_DRONES_PER_SAT: 2           # Max concurrent chargers

# Equilibrium monitoring
EQUILIBRIUM_CHECK_INTERVAL: 10       # Ticks between checks
EQUILIBRIUM_WINDOW_TICKS: 50         # Rolling window size
EQUILIBRIUM_DISPATCH_THRESHOLD: -5.0 # Net energy loss trigger
```

## Frontend Features

### 3D Visualization
- **Interactive Globe**: Rotate, zoom, auto-rotate enabled
- **Satellite Models**: Custom OBJ/MTL models with energy status rings
- **Drone Indicators**: Color-coded status spheres with trail effects
- **Target Lines**: Visual connections between drones and target satellites
- **Real-time Labels**: Company names, energy levels, SOL amounts

### Economic Dashboard
- **Total Volume**: Cumulative SOL traded
- **Top Earners**: Satellites with highest revenue
- **Top Spenders**: Drones with highest costs
- **Efficiency Metrics**: Best/worst energy-to-revenue ratios
- **Transaction Feed**: Live scrolling transaction log
- **System Stats**: Satellite/drone tables with economic data

### Color Coding
- 🟢 **Green**: High energy (>70%), charging status, earning
- 🟡 **Yellow**: Medium energy (30-70%), harvesting
- 🔴 **Red**: Low energy (<30%), critical status
- 🔵 **Blue**: Charging operations
- 🟣 **Purple**: Enroute/returning
- 🔷 **Cyan**: Earth/standby

## Economic Simulation Flow

```
1. Simulation starts with 4 satellites (different companies) and 2 drones
   ↓
2. Tasks arrive → Satellites consume energy processing tasks
   ↓
3. Satellite energy drops below 25 → Auto-dispatch triggers
   ↓
4. Drone at Earth deploys (FREE recharge) → Travels to needy satellite
   ↓
5. Drone charges satellite (NO COST - drone owns this energy)
   ↓
6. Drone payload depleted → Seeks energy source
   ↓
7a. High-energy satellite available (>80 units)?
    → Drone harvests energy (PAYS satellite owner in SOL)
    → Transaction recorded with dynamic pricing
    ↓
7b. No suitable satellite?
    → Drone returns to Earth (FREE recharge)
    ↓
8. Repeat: Maintain equilibrium between energy consumption and supply
   ↓
9. Economic metrics update: Revenue, spending, efficiency tracked
```

## Testing & Demo

### View Live Data
Open `backend/viewer.html` in browser for HTML dashboard, or use the React Three.js frontend for 3D visualization.

### Generate Load
```bash
# Heavy load
POST /api/smoke/start {"qps": 100, "burst": 20}

# Moderate load  
POST /api/smoke/start {"qps": 50, "burst": 10}

# Stop
POST /api/smoke/stop
```

### Watch Economics
```bash
# Monitor transactions
watch -n 1 'curl -s http://localhost:5001/api/economics/metrics | jq'

# View leaderboard
curl http://localhost:5001/api/economics/leaderboard | jq
```

## Future Enhancements

- [ ] Actual Solana integration (currently simulated)
- [ ] Wallet connection (Phantom, Solflare)
- [ ] On-chain transaction recording
- [ ] NFT satellite ownership
- [ ] Governance token for system parameters
- [ ] Satellite-to-satellite beaming (peer energy transfers)
- [ ] Energy futures market (pre-purchase energy contracts)
- [ ] Staking mechanism for satellite operators
- [ ] Real orbital mechanics (Kepler elements)
- [ ] Multiple Earth stations with different pricing

## Tech Stack

**Backend**: Python 3.11+, Flask, Flask-SocketIO, Pydantic  
**Frontend**: React, Three.js, @react-three/fiber, @react-three/drei  
**Models**: GLB (Earth), OBJ/MTL (Satellites)  
**Protocol**: REST API + WebSocket for real-time updates  
**Blockchain**: Solana (simulated - ready for web3.js integration)

## License

MIT License - Hackathon Project

---

Built for MDC Hackathon 🚀 Demonstrating decentralized energy marketplaces in space.