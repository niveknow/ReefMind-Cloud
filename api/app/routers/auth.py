from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth import hash_password, verify_password, create_access_token, create_api_key
from app.services.influx import ensure_tenant_bucket

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create tenant
    import uuid
    tenant = Tenant(
        name=req.tenant_name,
        slug=req.email.split("@")[0] + "-" + str(uuid.uuid4())[:8],
    )
    db.add(tenant)
    await db.flush()

    # Create tenant config with API key
    api_key = create_api_key()
    config = TenantConfig(
        tenant_id=tenant.id,
        agent_api_key=api_key,
    )
    db.add(config)

    # Create user
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.email.split("@")[0],
    )
    db.add(user)
    await db.commit()

    # Create InfluxDB bucket
    try:
        ensure_tenant_bucket(str(tenant.id))
    except Exception as e:
        pass  # Non-fatal if Influx not ready yet

    # Generate JWT
    token = create_access_token({
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "email": req.email,
    })

    return TokenResponse(
        access_token=token,
        tenant_id=str(tenant.id),
        user_id=str(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": req.email,
    })

    return TokenResponse(
        access_token=token,
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
    )
