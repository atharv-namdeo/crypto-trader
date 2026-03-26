import asyncio
import os
from core.state_manager import StateManager

async def inspect():
    state = StateManager()
    await state.connect()
    if state.redis:
        keys = await state.redis.keys("*")
        print(f"Total keys: {len(keys)}")
        for key in keys[:50]:
            val = await state.redis.get(key)
            print(f"{key}: {val[:100] if val else 'None'}")
    else:
        print("Could not connect to Redis")

if __name__ == "__main__":
    asyncio.run(inspect())
