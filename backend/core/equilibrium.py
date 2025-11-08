"""
Equilibrium Monitor - Tracks system energy balance and recommends drone fleet size

Monitors:
- Total satellite energy trends
- Energy consumption vs generation rates
- Drone utilization and efficiency
- Recommends optimal drone count for equilibrium
"""

from collections import deque
from . import state
from config import CONFIG
from events import emit_event

class EquilibriumMonitor:
    def __init__(self):
        self.energy_history = deque(maxlen=CONFIG.EQUILIBRIUM_WINDOW_TICKS)
        self.tick_count = 0
        self.last_recommendation = None
    
    def record_tick(self, socketio):
        """Record current system state"""
        with state.LOCK:
            # Calculate total system energy
            total_energy = sum(s.energy_amount for s in state.SATELLITES.values())
            total_capacity = sum(s.max_energy for s in state.SATELLITES.values())
            
            # Count active drones
            active_drones = sum(1 for d in state.BATTERIES.values() 
                              if d.status in ("charging", "enroute", "harvesting"))
            idle_drones = sum(1 for d in state.BATTERIES.values() 
                            if d.status in ("at_earth", "standby"))
            
            # Record state
            self.energy_history.append({
                "tick": self.tick_count,
                "total_energy": total_energy,
                "capacity": total_capacity,
                "utilization": total_energy / max(total_capacity, 1),
                "active_drones": active_drones,
                "idle_drones": idle_drones
            })
            
            self.tick_count += 1
            
            # Check equilibrium periodically
            if self.tick_count % CONFIG.EQUILIBRIUM_CHECK_INTERVAL == 0:
                self._check_equilibrium(socketio)
    
    def _check_equilibrium(self, socketio):
        """Analyze trends and emit recommendations"""
        if len(self.energy_history) < 10:
            return  # Need more data
        
        with state.LOCK:
            # Calculate energy trend
            recent = list(self.energy_history)[-10:]
            oldest = recent[0]["total_energy"]
            newest = recent[-1]["total_energy"]
            trend = newest - oldest
            
            # Calculate average utilization
            avg_util = sum(r["utilization"] for r in recent) / len(recent)
            
            # Count satellites below threshold
            critical_sats = sum(1 for s in state.SATELLITES.values() 
                              if s.energy_amount < CONFIG.AUTO_NEEDY_THRESH)
            
            # Current drone count
            total_drones = len(state.BATTERIES)
            active = recent[-1]["active_drones"]
            idle = recent[-1]["idle_drones"]
            
            # Determine recommendation
            recommendation = self._calculate_drone_need(
                trend, avg_util, critical_sats, total_drones, active, idle
            )
            
            if recommendation != self.last_recommendation:
                self.last_recommendation = recommendation
                emit_event(socketio, "equilibrium.update", {
                    "tick": self.tick_count,
                    "energy_trend": trend,
                    "avg_utilization": avg_util,
                    "critical_satellites": critical_sats,
                    "active_drones": active,
                    "idle_drones": idle,
                    "total_drones": total_drones,
                    "recommendation": recommendation,
                    "status": self._get_status(trend, avg_util, critical_sats)
                })
    
    def _calculate_drone_need(self, trend, avg_util, critical_sats, total, active, idle):
        """Calculate recommended drone count for equilibrium"""
        
        # Severe energy loss - need more drones
        if trend < CONFIG.EQUILIBRIUM_DISPATCH_THRESHOLD * 2:
            needed = total + 2
            return {
                "action": "add_drones",
                "count": 2,
                "total_needed": needed,
                "reason": "severe_energy_loss"
            }
        
        # Moderate energy loss - need 1 more drone
        if trend < CONFIG.EQUILIBRIUM_DISPATCH_THRESHOLD:
            needed = total + 1
            return {
                "action": "add_drones",
                "count": 1,
                "total_needed": needed,
                "reason": "moderate_energy_loss"
            }
        
        # Critical satellites exist but drones are idle - deployment issue
        if critical_sats > 0 and idle > 0:
            return {
                "action": "dispatch_idle",
                "reason": "critical_satellites_with_idle_drones"
            }
        
        # System stable, high utilization - maintain current
        if 0.4 <= avg_util <= 0.7 and abs(trend) < 5:
            return {
                "action": "maintain",
                "reason": "equilibrium_achieved"
            }
        
        # Excess drones (all idle, energy rising)
        if idle > 1 and trend > 10 and avg_util > 0.8:
            return {
                "action": "reduce_drones",
                "count": 1,
                "reason": "excess_capacity"
            }
        
        # Default: maintain current
        return {
            "action": "maintain",
            "reason": "monitoring"
        }
    
    def _get_status(self, trend, avg_util, critical_sats):
        """Get overall system status"""
        if critical_sats > 2 or trend < -10:
            return "critical"
        elif critical_sats > 0 or trend < -5:
            return "warning"
        elif abs(trend) < 3 and 0.4 <= avg_util <= 0.7:
            return "equilibrium"
        else:
            return "stable"

# Global monitor instance
MONITOR = EquilibriumMonitor()