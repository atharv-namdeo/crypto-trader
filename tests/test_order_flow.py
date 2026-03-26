import asyncio
import os
import json
from core.state_manager import StateManager

async def test_order_flow():
    print("🧪 Starting Order Flow Verification Test...")
    state = StateManager()
    await state.connect()
    
    symbol = "BTC/USDT"
    queue_key = f"order_request:{symbol}"
    
    # 1. Clear existing requests
    await state.redis.delete(queue_key)
    print(f"🧹 Cleared {queue_key}")
    
    # 2. Simulate a strategy setting an order request
    req = {
        'action': 'OPEN',
        'side': 'LONG',
        'qty': 0.001,
        'price': 60000.0,
        'strategy': 'TEST_STRATEGY'
    }
    await state.set(queue_key, req)
    print(f"📡 Set {queue_key} with {req}")
    
    # 3. Verify it's in Redis
    val = await state.get(queue_key)
    if val and val['strategy'] == 'TEST_STRATEGY':
        print("✅ SUCCESS: Order request correctly stored in Redis.")
    else:
        print(f"❌ FAILURE: Order request not found or incorrect. Found: {val}")

if __name__ == "__main__":
    asyncio.run(test_order_flow())
