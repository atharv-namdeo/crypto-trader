from enum import Enum
from typing import List, Dict

class CryptoTier(Enum):
    TIER_1 = "tier_1"      # BTC, ETH only (high conviction)
    TIER_2 = "tier_2"      # Top 10 (liquid, stable)
    TIER_3 = "tier_3"      # Top 25 (good liquidity)
    TIER_4 = "tier_4"      # 26-50 (lower liquidity)

SYMBOL_CONFIG = {
    CryptoTier.TIER_1: [
        'BTC/USDT', 'ETH/USDT'
    ],
    CryptoTier.TIER_2: [
        'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT',
        'SHIB/USDT', 'POL/USDT', 'AVAX/USDT', 'LINK/USDT'
    ],
    CryptoTier.TIER_3: [
        'UNI/USDT', 'DOT/USDT', 'BCH/USDT', 'NEAR/USDT',
        'LTC/USDT', 'XLM/USDT', 'ATOM/USDT', 'HBAR/USDT',
        'ARB/USDT', 'OP/USDT', 'PEPE/USDT', 'TON/USDT',
        'ALGO/USDT', 'FIL/USDT', 'CRO/USDT'
    ],
    CryptoTier.TIER_4: [
        'ICP/USDT', 'MANTA/USDT', 'RENDER/USDT', 'SEI/USDT',
        'XEC/USDT', 'JUP/USDT', 'ONDO/USDT', 'AAVE/USDT',
        'STX/USDT', 'IOTX/USDT', 'VET/USDT', 'ETC/USDT',
        'MNT/USDT', 'FLR/USDT', 'BLUR/USDT', 'TRUMP/USDT',
        'CYBER/USDT', 'SONIC/USDT', 'TAO/USDT', 'SUI/USDT',
        'APT/USDT', 'MOVE/USDT', 'BONK/USDT'
    ]
}

# Strategy allocation by tier
STRATEGY_TIER_ALLOCATION = {
    CryptoTier.TIER_1: {
        'scalper': 0.20,      # High activity on BTC/ETH
        'swing': 0.40,
        'position': 0.40
    },
    CryptoTier.TIER_2: {
        'scalper': 0.15,
        'swing': 0.35,
        'position': 0.40,
        'ai_ensemble': 0.10
    },
    CryptoTier.TIER_3: {
        'scalper': 0.10,      # Lower liquidity, less scalping
        'swing': 0.30,
        'position': 0.40,
        'ai_ensemble': 0.20
    },
    CryptoTier.TIER_4: {
        'scalper': 0.0,       # Skip scalping (low liquidity)
        'swing': 0.20,
        'position': 0.50,
        'ai_ensemble': 0.30
    }
}

# Risk limits by tier
RISK_TIER_CONFIG = {
    CryptoTier.TIER_1: {
        'max_position_size': 0.15,     # Can take 15% of capital
        'leverage': 3.0,
        'stop_loss_distance': '1.5x'
    },
    CryptoTier.TIER_2: {
        'max_position_size': 0.10,
        'leverage': 2.0,
        'stop_loss_distance': '2.0x'
    },
    CryptoTier.TIER_3: {
        'max_position_size': 0.08,
        'leverage': 1.5,
        'stop_loss_distance': '2.5x'
    },
    CryptoTier.TIER_4: {
        'max_position_size': 0.05,
        'leverage': 1.0,
        'stop_loss_distance': '3.0x'
    }
}
