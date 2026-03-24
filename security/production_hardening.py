import os
import logging
from fastapi import Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

log = logging.getLogger("Security")

async def verify_api_key(x_api_key: str = Header(None)):
    """Simple API Key validation"""
    expected_key = os.getenv("TRADER_API_KEY")
    if not expected_key:
        return # Skip if not configured
        
    if x_api_key != expected_key:
        log.warning(f"🚫 Unauthorized API Access attempt")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

class ProductionSecurityHardening:
    """Enterprise-grade security for production"""
    
    def __init__(self, app):
        self.app = app
        self.limiter = Limiter(key_func=get_remote_address)
        self.app.state.limiter = self.limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    def apply_cors(self):
        """Restrict CORS origins"""
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        log.info(f"🛡️ CORS Applied: {allowed_origins}")

def setup_production_security(app):
    """Utility to apply all hardening to a FastAPI app"""
    security = ProductionSecurityHardening(app)
    security.apply_cors()
    log.info("✅ Production Security Hardening Initialized")
    return security
