"""Connector Management Routes"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.connectors import registry
from app.models.database import User, UserConnector
from app.models.schemas import ConnectorConfigRequest, ConnectorInfo, SuccessResponse

router = APIRouter(prefix="/v1/connectors", tags=["Connectors"])


@router.get("/available", response_model=SuccessResponse)
async def list_available_connectors():
    """List all available connectors and their capabilities"""
    connectors = registry.list_all()
    return SuccessResponse(
        message=f"{len(connectors)} connectors available",
        data=connectors,
    )


@router.get("/mine", response_model=SuccessResponse)
async def list_my_connectors(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List your configured connectors"""
    result = await db.execute(
        select(UserConnector).where(UserConnector.user_id == user.id)
    )
    connectors = result.scalars().all()

    return SuccessResponse(
        message=f"{len(connectors)} connectors configured",
        data=[
            {
                "id": c.id,
                "type": c.connector_type,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in connectors
        ],
    )


@router.post("/configure", response_model=SuccessResponse, status_code=201)
async def configure_connector(
    req: ConnectorConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Configure a connector with your credentials"""
    # Check connector exists
    connector_cls = registry.get(req.connector_type)
    if not connector_cls:
        available = [c["type"] for c in registry.list_all()]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector: {req.connector_type}. Available: {available}",
        )

    # Check if already configured
    result = await db.execute(
        select(UserConnector).where(
            UserConnector.user_id == user.id,
            UserConnector.connector_type == req.connector_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.config_encrypted = json.dumps(req.config)
        existing.is_active = True
    else:
        connector = UserConnector(
            user_id=user.id,
            connector_type=req.connector_type,
            config_encrypted=json.dumps(req.config),
        )
        db.add(connector)

    await db.flush()

    return SuccessResponse(
        message=f"Connector '{req.connector_type}' configured successfully",
        data={"connector_type": req.connector_type, "status": "active"},
    )


@router.delete("/{connector_type}", response_model=SuccessResponse)
async def remove_connector(
    connector_type: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a connector"""
    result = await db.execute(
        select(UserConnector).where(
            UserConnector.user_id == user.id,
            UserConnector.connector_type == connector_type,
        )
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not configured")

    connector.is_active = False
    await db.flush()

    return SuccessResponse(message=f"Connector '{connector_type}' deactivated")
