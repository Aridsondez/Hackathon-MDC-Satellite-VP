from flask import Blueprint, jsonify
from core.economics import ECONOMICS

bp = Blueprint("economics", __name__)

@bp.get("/economics/metrics")
def get_metrics():
    """Get comprehensive economic metrics"""
    return jsonify(ECONOMICS.get_metrics())

@bp.get("/economics/transactions")
def get_transactions():
    """Get recent transactions"""
    return jsonify({
        "transactions": [
            {
                "id": t.transaction_id,
                "timestamp": t.timestamp,
                "from_company": t.from_company,
                "from_wallet": t.from_wallet,
                "to_company": t.to_company,
                "to_wallet": t.to_wallet,
                "energy": t.energy_amount,
                "price_per_unit": t.price_per_unit,
                "total_sol": t.total_cost,
                "type": t.transaction_type
            }
            for t in list(ECONOMICS.transactions)[-50:]
        ]
    })

@bp.get("/economics/leaderboard")
def get_leaderboard():
    """Get top earners and spenders"""
    metrics = ECONOMICS.get_metrics()
    return jsonify({
        "top_earners": metrics["top_earning_satellites"],
        "top_spenders": metrics["top_spending_drones"],
        "total_volume": metrics["total_volume_sol"]
    })