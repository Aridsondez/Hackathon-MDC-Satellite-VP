"""
Solana Devnet Integration - Records energy transactions on blockchain

This module is OPTIONAL and isolated. If SOLANA_ENABLED=false, all methods are no-ops.
"""

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey
from solders.message import Message
import json
import os
import time
import asyncio
from typing import Optional
from solana_config import SOLANA_CONFIG
from events import emit_event

class SolanaIntegrator:
    def __init__(self):
        self.enabled = SOLANA_CONFIG.ENABLED
        self.keypair: Optional[Keypair] = None
        self.client: Optional[AsyncClient] = None
        self.last_transaction_time = 0
        self.pending_transactions = []
        
        if self.enabled:
            self._initialize()
    
    def _initialize(self):
        """Initialize Solana connection and keypair"""
        try:
            # Load or create keypair
            if os.path.exists(SOLANA_CONFIG.KEYPAIR_PATH):
                with open(SOLANA_CONFIG.KEYPAIR_PATH, 'r') as f:
                    secret_key = json.load(f)
                    self.keypair = Keypair.from_bytes(bytes(secret_key))
                print(f"✓ Loaded Solana keypair: {self.keypair.pubkey()}")
            else:
                self.keypair = Keypair()
                with open(SOLANA_CONFIG.KEYPAIR_PATH, 'w') as f:
                    json.dump(list(self.keypair.secret()), f)
                print(f"✓ Created new Solana keypair: {self.keypair.pubkey()}")
                print(f"⚠️  Fund this address on Devnet: https://faucet.solana.com")
            
            # Initialize async client
            self.client = AsyncClient(SOLANA_CONFIG.RPC_ENDPOINT)
            print(f"✓ Connected to Solana Devnet")
            
        except Exception as e:
            print(f"❌ Solana initialization failed: {e}")
            self.enabled = False
    
    async def record_transaction(self, transaction_data: dict, socketio) -> Optional[str]:
        """
        Record an energy transaction on Solana Devnet
        Returns transaction signature if successful, None otherwise
        """
        if not self.enabled or not self.client or not self.keypair:
            return None
        
        # Rate limiting
        now = time.time()
        if now - self.last_transaction_time < SOLANA_CONFIG.MIN_TRANSACTION_INTERVAL:
            return None
        
        # Only record transactions above threshold
        if transaction_data.get("total_cost", 0) < SOLANA_CONFIG.BATCH_THRESHOLD:
            return None
        
        try:
            # Convert SOL amount to lamports (1 SOL = 1e9 lamports)
            amount_lamports = int(transaction_data["total_cost"] * 1_000_000_000)
            
            # Minimum transaction is 1 lamport
            if amount_lamports < 1:
                return None
            
            # Create transfer instruction (sending to self as a record)
            # In production, you'd send to the actual recipient's wallet
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=self.keypair.pubkey(),
                    to_pubkey=self.keypair.pubkey(),  # Sending to self for demo
                    lamports=amount_lamports
                )
            )
            
            # Get recent blockhash
            recent_blockhash_resp = await self.client.get_latest_blockhash(Confirmed)
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            # Create transaction
            msg = Message.new_with_blockhash(
                [transfer_ix],
                self.keypair.pubkey(),
                recent_blockhash
            )
            txn = Transaction.new_unsigned(msg)
            txn.sign([self.keypair], recent_blockhash)
            
            # Send transaction
            response = await self.client.send_transaction(txn)
            signature = str(response.value)
            
            self.last_transaction_time = now
            
            # Emit Solana event
            emit_event(socketio, "solana.transaction", {
                "signature": signature,
                "transaction_id": transaction_data.get("transaction_id"),
                "amount_sol": transaction_data.get("total_cost"),
                "explorer_url": f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
            })
            
            print(f"✓ Solana TX: {signature[:16]}... ({transaction_data.get('total_cost', 0):.6f} SOL)")
            return signature
            
        except Exception as e:
            print(f"⚠️  Solana transaction failed: {e}")
            return None
    
    async def get_balance(self) -> Optional[float]:
        """Get wallet balance in SOL"""
        if not self.enabled or not self.client or not self.keypair:
            return None
        
        try:
            balance_resp = await self.client.get_balance(self.keypair.pubkey())
            lamports = balance_resp.value
            return lamports / 1_000_000_000
        except Exception as e:
            print(f"⚠️  Failed to get balance: {e}")
            return None
    
    async def close(self):
        """Close async client connection"""
        if self.client:
            await self.client.close()

# Global Solana integrator instance
SOLANA = SolanaIntegrator()