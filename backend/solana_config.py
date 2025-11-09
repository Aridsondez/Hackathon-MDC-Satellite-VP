from dataclasses import dataclass
import os

@dataclass
class SolanaConfig:
    # Feature flag - set to False to disable Solana entirely
    ENABLED: bool = os.getenv("SOLANA_ENABLED", "false").lower() == "true"
    
    # Devnet RPC endpoint
    RPC_ENDPOINT: str = "https://api.devnet.solana.com"
    
    # Keypair file path (will be auto-generated if missing)
    KEYPAIR_PATH: str = os.path.join(os.path.dirname(__file__), "solana_keypair.json")
    
    # Transaction settings
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 30
    
    # Rate limiting (to avoid spamming devnet)
    MIN_TRANSACTION_INTERVAL: float = 2.0  # seconds between transactions
    BATCH_TRANSACTIONS: bool = True  # Batch small transactions
    BATCH_THRESHOLD: float = 1.0  # Only send transactions >= 0.001 SOL

SOLANA_CONFIG = SolanaConfig()