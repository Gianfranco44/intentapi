"""Intent Routes - Core API Endpoints"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.engine import intent_engine
from app.core.executor import ExecutionEngine
from app.models.database import (
    User, Execution, ExecutionStatus, UserConnector,
    PlanTier, UsageLog
)
from app.models.schemas import (
    IntentRequest, ExecutionResponse, SuccessResponse, ErrorResponse
)

router = APIRouter(prefix="/v1", tags=["Intent API"])

# Plan limits
PLAN_LIMITS = {
    PlanTier.FREE: {"executions_per_month": 100, "rate_per_minute": 10},
    PlanTier.STARTER: {"executions_per_month": 5000, "rate_per_minute": 60},
    PlanTier.PRO: {"executions_per_month": 50000, "rate_per_minute": 200},
    PlanTier.ENTERPRISE: {"executions_per_month": 999999, "rate_per_minute": 1000},
}


@router.post("/intent", response_model=ExecutionResponse)
async def execute_intent(
    req: IntentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    🧠 Execute a natural language intent

    Send a plain English (or Spanish, or any language) description of what you
    want to do, and IntentAPI will parse it into an action plan and execute it.

    **Example:**
    ```json
    {
      "intent": "Send an email to hello@example.com saying 'Your order has shipped'",
      "dry_run": false
    }
    ```
    """
    start_time = time.time()

    # Check plan limits
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[PlanTier.FREE])
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0)
    result = await db.execute(
        select(func.count(Execution.id)).where(
            Execution.user_id == user.id,
            Execution.created_at >= month_start,
        )
    )
    monthly_count = result.scalar() or 0

    if monthly_count >= limits["executions_per_month"]:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly execution limit reached ({limits['executions_per_month']}). Upgrade your plan at /pricing",
        )

    # Load user's connector configs
    conn_result = await db.execute(
        select(UserConnector).where(
            UserConnector.user_id == user.id, UserConnector.is_active == True
        )
    )
    user_connectors_db = conn_result.scalars().all()
    user_connector_types = [c.connector_type for c in user_connectors_db]
    user_connector_configs = {}
    for c in user_connectors_db:
        try:
            import json
            user_connector_configs[c.connector_type] = json.loads(c.config_encrypted or "{}")
        except Exception:
            user_connector_configs[c.connector_type] = {}

    # Create execution record
    execution = Execution(
        user_id=user.id,
        intent_raw=req.intent,
        status=ExecutionStatus.PARSING,
        require_approval=req.require_approval,
    )
    db.add(execution)
    await db.flush()

    try:
        # Step 1: Parse intent with AI
        parsed, tokens_used = await intent_engine.parse_intent(
            intent=req.intent,
            context=req.context,
            user_connectors=user_connector_types,
        )

        execution.intent_parsed = {
            "summary": parsed.summary,
            "confidence": parsed.confidence,
            "steps": [s.model_dump() for s in parsed.steps],
            "warnings": parsed.warnings,
            "estimated_cost_usd": parsed.estimated_cost_usd,
        }
        execution.tokens_used = tokens_used

        # Dry run: return the plan without executing
        if req.dry_run:
            execution.status = ExecutionStatus.COMPLETED
            total_ms = int((time.time() - start_time) * 1000)
            execution.execution_time_ms = total_ms
            await db.flush()

            return ExecutionResponse(
                execution_id=execution.id,
                status="dry_run",
                intent_raw=req.intent,
                intent_parsed=parsed,
                results=[],
                total_duration_ms=total_ms,
                tokens_used=tokens_used,
                cost_usd=parsed.estimated_cost_usd,
                created_at=execution.created_at,
            )

        # Awaiting approval mode
        if req.require_approval:
            execution.status = ExecutionStatus.AWAITING_APPROVAL
            total_ms = int((time.time() - start_time) * 1000)
            execution.execution_time_ms = total_ms
            await db.flush()

            return ExecutionResponse(
                execution_id=execution.id,
                status="awaiting_approval",
                intent_raw=req.intent,
                intent_parsed=parsed,
                results=[],
                total_duration_ms=total_ms,
                tokens_used=tokens_used,
                cost_usd=parsed.estimated_cost_usd,
                created_at=execution.created_at,
            )

        # Step 2: Execute the action graph
        executor = ExecutionEngine(db, user_connector_configs)
        results = await executor.execute(execution, parsed)

        total_ms = int((time.time() - start_time) * 1000)
        execution.execution_time_ms = total_ms
        execution.cost_usd = parsed.estimated_cost_usd

        # Log usage
        usage = UsageLog(
            user_id=user.id,
            endpoint="/v1/intent",
            tokens_used=tokens_used,
            cost_usd=parsed.estimated_cost_usd,
        )
        db.add(usage)
        await db.flush()

        return ExecutionResponse(
            execution_id=execution.id,
            status=execution.status.value,
            intent_raw=req.intent,
            intent_parsed=parsed,
            results=results,
            total_duration_ms=total_ms,
            tokens_used=tokens_used,
            cost_usd=parsed.estimated_cost_usd,
            created_at=execution.created_at,
        )

    except Exception as e:
        execution.status = ExecutionStatus.FAILED
        execution.error = str(e)
        execution.execution_time_ms = int((time.time() - start_time) * 1000)
        await db.flush()

        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/intent/{execution_id}/approve", response_model=ExecutionResponse)
async def approve_execution(
    execution_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending execution (when require_approval=true)"""
    start_time = time.time()

    result = await db.execute(
        select(Execution).where(
            Execution.id == execution_id,
            Execution.user_id == user.id,
        )
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status != ExecutionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Execution is not awaiting approval (status: {execution.status.value})")

    from app.models.schemas import IntentParsed, ActionStep
    parsed_data = execution.intent_parsed
    parsed = IntentParsed(
        summary=parsed_data["summary"],
        confidence=parsed_data["confidence"],
        steps=[ActionStep(**s) for s in parsed_data["steps"]],
        warnings=parsed_data.get("warnings", []),
        estimated_cost_usd=parsed_data.get("estimated_cost_usd", 0),
    )

    # Load user connectors
    conn_result = await db.execute(
        select(UserConnector).where(
            UserConnector.user_id == user.id, UserConnector.is_active == True
        )
    )
    import json as json_mod
    user_connector_configs = {}
    for c in conn_result.scalars().all():
        try:
            user_connector_configs[c.connector_type] = json_mod.loads(c.config_encrypted or "{}")
        except Exception:
            user_connector_configs[c.connector_type] = {}

    executor = ExecutionEngine(db, user_connector_configs)
    results = await executor.execute(execution, parsed)

    total_ms = int((time.time() - start_time) * 1000)
    execution.execution_time_ms = total_ms

    return ExecutionResponse(
        execution_id=execution.id,
        status=execution.status.value,
        intent_raw=execution.intent_raw,
        intent_parsed=parsed,
        results=results,
        total_duration_ms=total_ms,
        tokens_used=execution.tokens_used or 0,
        cost_usd=execution.cost_usd or 0,
        created_at=execution.created_at,
    )


@router.get("/executions", response_model=SuccessResponse)
async def list_executions(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List your recent executions"""
    result = await db.execute(
        select(Execution)
        .where(Execution.user_id == user.id)
        .order_by(Execution.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    executions = result.scalars().all()

    return SuccessResponse(
        message=f"Found {len(executions)} executions",
        data=[
            {
                "id": e.id,
                "intent": e.intent_raw[:100],
                "status": e.status.value,
                "cost_usd": e.cost_usd,
                "tokens_used": e.tokens_used,
                "execution_time_ms": e.execution_time_ms,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in executions
        ],
    )


@router.get("/executions/{execution_id}", response_model=SuccessResponse)
async def get_execution(
    execution_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific execution"""
    result = await db.execute(
        select(Execution).where(
            Execution.id == execution_id, Execution.user_id == user.id
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return SuccessResponse(
        data={
            "id": execution.id,
            "intent_raw": execution.intent_raw,
            "intent_parsed": execution.intent_parsed,
            "status": execution.status.value,
            "result": execution.result,
            "error": execution.error,
            "cost_usd": execution.cost_usd,
            "tokens_used": execution.tokens_used,
            "execution_time_ms": execution.execution_time_ms,
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        },
    )
