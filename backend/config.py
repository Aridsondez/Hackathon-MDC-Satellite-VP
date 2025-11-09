from dataclasses import dataclass

@dataclass
class Config:
    # Simulation timing
    TICK_MS: int = 500
    
    # Task delegation weights
    LOW_WATERMARK: float = 0.25
    HIGH_WATERMARK: float = 0.70
    WEIGHTS: dict = None
    DEFAULT_QPS: int = 30
    
    # Satellite task limits
    MAX_TASKS_PER_SAT: int = 30
    MIN_ENERGY_TO_ACCEPT: float = 10
    TASK_ENERGY_RATE: float = 0.10              
    TASK_PROGRESS_RATE: float = 0.02        
    
    # Drone movement & battery
    DRONE_SPEED_KM_PER_TICK: float = 4000.0
    DRONE_RESERVE_PER_KM: float = 0.001          # Reserve cost per km traveled
    DRONE_RESERVE_MIN_TO_CONTINUE: float = 10.0  # Minimum reserve to continue operations
    DRONE_RESERVE_MAX: float = 3000.0            # Maximum reserve capacity
    DRONE_TRAVEL_INSTANT: bool = True            # Instant teleport for stability
    DRONE_ENROUTE_MAX_TICKS: int = 8             # Max ticks before timeout recovery
    
    # Drone payload (charging capacity)
    DRONE_PAYLOAD_CHARGE_RATE: float = 8.0       # Energy units transferred per tick
    DRONE_PAYLOAD_MIN_TO_CHARGE: float = 6.0     # Minimum payload to start/continue charging
    DRONE_PAYLOAD_MAX: float = 120.0             # Maximum payload capacity
    PAYLOAD_CHARGE_MIN: float = 15.0        
    # Drone harvesting (collecting from satellites)
    DRONE_HARVEST_RATE: float = 10.0             # Energy units harvested per tick
    HARVEST_FLOOR: float = 70.0                  # Don't harvest below this sat energy
    HARVEST_START_LEVEL: float = 80.0            # Prefer sources above this to start
    
    # Satellite charging thresholds
    SAT_FULL_EPS: float = 0.5                    # Stop charging when within eps of full
    NEEDY_THRESH: float = 30.0                   # Satellite considered "needy" below this
    
    # Drone behavior limits
    DRONE_MAX_DWELL_TICKS: int = 60              # Max ticks at one satellite before moving
    LOOP_GUARD_MIN_PROGRESS_TICKS: int = 3       # Ticks without progress before bailout
    
    # Auto-dispatch settings (for equilibrium)
    AUTO_DISPATCH_ENABLED: bool = True
    AUTO_NEEDY_THRESH: float = 25.0              # Auto-dispatch when sat below this
    AUTO_MAX_DRONES_PER_SAT: int = 2             # Max concurrent drones per satellite
    
    # Equilibrium calculation
    EQUILIBRIUM_CHECK_INTERVAL: int = 10         # Ticks between equilibrium checks
    EQUILIBRIUM_WINDOW_TICKS: int = 50           # Rolling window for energy trend
    EQUILIBRIUM_DISPATCH_THRESHOLD: float = -5.0 # Net energy loss triggering dispatch
    
    def __post_init__(self):
        if self.WEIGHTS is None:
            self.WEIGHTS = dict(w1=0.35, w2=0.25, w3=0.20, w4=0.15, w5=0.05)

CONFIG = Config()