"""
Economics Engine - Handles energy pricing, transactions, and financial metrics
"""

from collections import deque
from datetime import datetime
from typing import Dict, List
from . import state
from .models import Transaction
from events import emit_event
import time

class EconomicsEngine:
    def __init__(self):
        self.transactions: deque = deque(maxlen=1000)  # Last 1000 transactions
        self.total_volume_sol: float = 0.0
        
    def calculate_dynamic_price(self, satellite) -> float:
        """
        Dynamic pricing based on satellite energy level
        Low energy = higher price (scarcity)
        High energy = lower price (abundance)
        """
        base_price = 0.05  # Base SOL per energy unit
        utilization = satellite.energy_amount / satellite.max_energy
        
        # Price increases as energy gets scarce
        if utilization < 0.2:
            multiplier = 2.5
        elif utilization < 0.4:
            multiplier = 1.8
        elif utilization < 0.6:
            multiplier = 1.3
        elif utilization < 0.8:
            multiplier = 1.0
        else:
            multiplier = 0.7  # Discount for abundant energy
        
        return base_price * multiplier
    
    def process_energy_transfer(self, from_sat, to_drone, amount: float, 
                                transfer_type: str, socketio) -> Transaction:
        """
        Create and record a transaction for energy transfer
        from_sat can be None for Earth (free energy)
        """
        # Earth energy is FREE
        if from_sat is None:
            txn = Transaction(
                from_entity_id="earth",
                from_company="Earth Energy Authority",
                from_wallet="earth-central",
                to_entity_id=to_drone.battery_id,
                to_company=to_drone.company_name,
                to_wallet=to_drone.owner_wallet,
                energy_amount=amount,
                price_per_unit=0.0,
                total_cost=0.0,
                transaction_type="earth_recharge"
            )
        else:
            # Satellite energy has dynamic pricing
            price = self.calculate_dynamic_price(from_sat)
            total = amount * price
            
            txn = Transaction(
                from_entity_id=from_sat.satellite_id,
                from_company=from_sat.company_name,
                from_wallet=from_sat.owner_wallet,
                to_entity_id=to_drone.battery_id,
                to_company=to_drone.company_name,
                to_wallet=to_drone.owner_wallet,
                energy_amount=amount,
                price_per_unit=price,
                total_cost=total,
                transaction_type=transfer_type
            )
            
            # Update financial records
            from_sat.total_revenue += total
            from_sat.total_energy_sold += amount
            to_drone.total_spent += total
            to_drone.total_energy_bought += amount
            self.total_volume_sol += total
        
        # Record transaction
        self.transactions.append(txn)
        
        # Emit event
        emit_event(socketio, "transaction.completed", {
            "transaction_id": txn.transaction_id,
            "from": txn.from_company,
            "to": txn.to_company,
            "amount": amount,
            "cost_sol": txn.total_cost,
            "type": transfer_type
        })
        
        return txn
    
    def get_metrics(self) -> Dict:
        """Calculate system-wide economic metrics"""
        with state.LOCK:
            # Satellite metrics
            sat_revenues = [(s.company_name, s.satellite_id, s.total_revenue, s.total_energy_sold) 
                           for s in state.SATELLITES.values()]
            sat_revenues.sort(key=lambda x: x[2], reverse=True)
            
            # Drone spending
            drone_spending = [(d.company_name, d.battery_id, d.total_spent, d.total_energy_bought)
                            for d in state.BATTERIES.values()]
            drone_spending.sort(key=lambda x: x[2], reverse=True)
            
            # Calculate efficiency (energy sold per revenue)
            most_efficient_sat = None
            best_efficiency = 0
            for s in state.SATELLITES.values():
                if s.total_revenue > 0:
                    efficiency = s.total_energy_sold / s.total_revenue
                    if efficiency > best_efficiency:
                        best_efficiency = efficiency
                        most_efficient_sat = s
            
            least_efficient_sat = None
            worst_efficiency = float('inf')
            for s in state.SATELLITES.values():
                if s.total_revenue > 0:
                    efficiency = s.total_energy_sold / s.total_revenue
                    if efficiency < worst_efficiency:
                        worst_efficiency = efficiency
                        least_efficient_sat = s
            
            return {
                "total_volume_sol": self.total_volume_sol,
                "total_transactions": len(self.transactions),
                "top_earning_satellites": [
                    {"company": c, "id": sid, "revenue": r, "energy_sold": e}
                    for c, sid, r, e in sat_revenues[:3]
                ],
                "top_spending_drones": [
                    {"company": c, "id": did, "spent": s, "energy_bought": e}
                    for c, did, s, e in drone_spending[:3]
                ],
                "most_efficient_satellite": {
                    "company": most_efficient_sat.company_name if most_efficient_sat else None,
                    "id": most_efficient_sat.satellite_id if most_efficient_sat else None,
                    "efficiency": best_efficiency,
                    "revenue": most_efficient_sat.total_revenue if most_efficient_sat else 0
                } if most_efficient_sat else None,
                "least_efficient_satellite": {
                    "company": least_efficient_sat.company_name if least_efficient_sat else None,
                    "id": least_efficient_sat.satellite_id if least_efficient_sat else None,
                    "efficiency": worst_efficiency,
                    "revenue": least_efficient_sat.total_revenue if least_efficient_sat else 0
                } if least_efficient_sat else None,
                "recent_transactions": [
                    {
                        "id": t.transaction_id,
                        "from": t.from_company,
                        "to": t.to_company,
                        "amount": t.energy_amount,
                        "cost": t.total_cost,
                        "timestamp": t.timestamp
                    }
                    for t in list(self.transactions)[-10:]
                ]
            }

# Global economics engine
ECONOMICS = EconomicsEngine()