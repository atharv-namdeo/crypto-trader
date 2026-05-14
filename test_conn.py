import asyncio
import ccxt.async_support as ccxt
import logging

# logging.basicConfig(level=logging.DEBUG)

async def test():
    ex = ccxt.binance({
        "enableRateLimit": True,
        "timeout": 20000,
        "options": {"defaultType": "spot"}
    })
    try:
        print("Testing connection...")
        markets = await ex.load_markets()
        print(f"Success! Loaded {len(markets)} markets.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await ex.close()

if __name__ == "__main__":
    asyncio.run(test())
