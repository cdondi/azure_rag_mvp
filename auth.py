from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import hashlib

security = HTTPBearer(auto_error=False)

API_KEYS = {
    "demo_key_hash": hashlib.sha256("demo-key-123".encode()).hexdigest(),
}


def require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> str:
    """Dependency that requires valid API key"""
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")

    provided_key_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()

    if provided_key_hash not in API_KEYS.values():
        raise HTTPException(status_code=401, detail="Invalid API key")

    return credentials.credentials
