from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth import decode_access_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    auth_header = request.headers.get("Authorization", "")
    api_key = request.headers.get("X-API-Key", "")

    # Try API key first (for agent ingest)
    if api_key:
        return {"auth_type": "api_key", "api_key": api_key}

    # Then try JWT
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and "user_id" in payload:
            return {
                "auth_type": "jwt",
                "user_id": payload["user_id"],
                "tenant_id": payload.get("tenant_id", ""),
            }

    raise HTTPException(status_code=401, detail="Not authenticated")
