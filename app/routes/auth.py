"""Authentication Routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import (
    hash_password, verify_password, create_access_token,
    generate_api_key, get_current_user
)
from app.models.database import User, APIKey, PlanTier
from app.models.schemas import (
    RegisterRequest, LoginRequest, AuthResponse,
    APIKeyResponse, SuccessResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account"""
    # Check if email exists
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        name=req.name,
        company=req.company,
        plan=PlanTier.FREE,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id, user.email)

    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        plan=user.plan.value,
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get access token"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(user.id, user.email)

    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        plan=user.plan.value,
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    name: str = "Default Key",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key (shown only once!)"""
    full_key, prefix, key_hash = generate_api_key()

    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=prefix,
        name=name,
    )
    db.add(api_key)
    await db.flush()

    return APIKeyResponse(key=full_key, key_prefix=prefix, name=name, id=api_key.id)


@router.get("/me", response_model=SuccessResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info"""
    return SuccessResponse(
        message="User info",
        data={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company": user.company,
            "plan": user.plan.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    )


@router.delete("/api-keys/{key_id}", response_model=SuccessResponse)
async def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key"""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.flush()
    return SuccessResponse(message=f"API key {api_key.key_prefix}... revoked")
