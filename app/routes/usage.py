"""Usage & Billing Routes"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.database import User, Execution, UsageLog, ExecutionStatus, PlanTier
from app.models.schemas import UsageStats, PlanInfo, SuccessResponse

router = APIRouter(prefix="/v1", tags=["Usage & Billing"])

PLANS = {
    "free": PlanInfo(
        plan="free", executions_per_month=100, rate_limit_per_minute=10,
        connectors_allowed=3, price_usd=0,
        features=["100 executions/month", "3 connectors", "Community support", "Basic analytics"],
    ),
    "starter": PlanInfo(
        plan="starter", executions_per_month=5000, rate_limit_per_minute=60,
        connectors_allowed=10, price_usd=29,
        features=["5,000 executions/month", "10 connectors", "Email support", "Full analytics", "Webhooks", "Priority parsing"],
    ),
    "pro": PlanInfo(
        plan="pro", executions_per_month=50000, rate_limit_per_minute=200,
        connectors_allowed=50, price_usd=149,
        features=["50,000 executions/month", "All connectors", "Priority support", "Advanced analytics", "Custom connectors", "Team access", "SLA 99.9%"],
    ),
    "enterprise": PlanInfo(
        plan="enterprise", executions_per_month=999999, rate_limit_per_minute=1000,
        connectors_allowed=999, price_usd=499,
        features=["Unlimited executions", "All connectors", "Dedicated support", "Custom SLA", "On-premise option", "SSO/SAML", "Audit logs", "Custom AI models"],
    ),
}


@router.get("/usage", response_model=SuccessResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get your usage statistics for the current month"""
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0)

    total = await db.execute(
        select(func.count(Execution.id)).where(
            Execution.user_id == user.id, Execution.created_at >= month_start
        )
    )
    successful = await db.execute(
        select(func.count(Execution.id)).where(
            Execution.user_id == user.id,
            Execution.created_at >= month_start,
            Execution.status == ExecutionStatus.COMPLETED,
        )
    )
    failed = await db.execute(
        select(func.count(Execution.id)).where(
            Execution.user_id == user.id,
            Execution.created_at >= month_start,
            Execution.status == ExecutionStatus.FAILED,
        )
    )
    tokens = await db.execute(
        select(func.coalesce(func.sum(UsageLog.tokens_used), 0)).where(
            UsageLog.user_id == user.id, UsageLog.created_at >= month_start
        )
    )
    cost = await db.execute(
        select(func.coalesce(func.sum(UsageLog.cost_usd), 0)).where(
            UsageLog.user_id == user.id, UsageLog.created_at >= month_start
        )
    )

    stats = UsageStats(
        total_executions=total.scalar() or 0,
        successful_executions=successful.scalar() or 0,
        failed_executions=failed.scalar() or 0,
        total_tokens=tokens.scalar() or 0,
        total_cost_usd=round(float(cost.scalar() or 0), 4),
        period=month_start.strftime("%Y-%m"),
    )

    return SuccessResponse(message="Current month usage", data=stats.model_dump())


@router.get("/plans", response_model=SuccessResponse)
async def get_plans():
    """List all available plans and pricing"""
    return SuccessResponse(
        message="Available plans",
        data=[p.model_dump() for p in PLANS.values()],
    )
