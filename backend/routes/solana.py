from flask import Blueprint, jsonify
from core.solana_integration import SOLANA
import asyncio

bp = Blueprint("solana", __name__)

@bp.get("/solana/status")
def get_status():
    """Check if Solana integration is enabled and connected"""
    if not SOLANA.enabled:
        return jsonify({
            "enabled": False,
            "message": "Solana integration disabled. Set SOLANA_ENABLED=true to enable."
        })
    
    # Get balance asynchronously
    try:
        balance = asyncio.run(SOLANA.get_balance())
        return jsonify({
            "enabled": True,
            "connected": SOLANA.client is not None,
            "wallet_address": str(SOLANA.keypair.pubkey()) if SOLANA.keypair else None,
            "balance_sol": balance,
            "network": "devnet",
            "faucet_url": "https://faucet.solana.com"
        })
    except Exception as e:
        return jsonify({
            "enabled": True,
            "connected": False,
            "error": str(e)
        }), 500

@bp.get("/solana/wallet")
def get_wallet():
    """Get wallet address for funding"""
    if not SOLANA.enabled or not SOLANA.keypair:
        return jsonify({"error": "Solana not enabled"}), 400
    
    return jsonify({
        "address": str(SOLANA.keypair.pubkey()),
        "faucet_url": f"https://faucet.solana.com/?address={SOLANA.keypair.pubkey()}",
        "explorer_url": f"https://explorer.solana.com/address/{SOLANA.keypair.pubkey()}?cluster=devnet"
    })