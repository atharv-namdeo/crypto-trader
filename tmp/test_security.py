import asyncio
import os
import httpx
from core.state_manager import StateManager
from api.app import create_app
import uvicorn
from threading import Thread
import time

async def test_security():
    state = StateManager()
    # Mock connection if redis is not running
    try:
        await state.connect()
    except:
        pass
        
    app = create_app(state)
    
    # Run uvicorn in a separate thread
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8005, log_level="error")
    
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(2) # Give it a second to start
    
    print("\n--- SECURITY TEST ---")
    
    # Test 1: Access health check (should be open or protected depending on implementation)
    # Our current implementation applies security globally but we can skip if key not set
    os.environ["TRADER_API_KEY"] = "test-secret-key"
    
    async with httpx.AsyncClient() as client:
        # Request without key
        resp = await client.get("http://127.0.0.1:8005/health")
        print(f"Request without key: {resp.status_code} (Expected 403 or 200 depending on route protection)")
        
        # Request with wrong key
        resp = await client.get("http://127.0.0.1:8005/health", headers={"X-API-Key": "wrong-key"})
        print(f"Request with wrong key: {resp.status_code} (Expected 403)")
        
        # Request with correct key
        resp = await client.get("http://127.0.0.1:8005/health", headers={"X-API-Key": "test-secret-key"})
        print(f"Request with correct key: {resp.status_code} (Expected 200)")

    print("---------------------\n")

if __name__ == "__main__":
    asyncio.run(test_security())
