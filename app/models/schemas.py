"""API Request/Response Schemas"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


# ── Auth Schemas ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    name: Optional[str] = None
    company: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    plan: str


class APIKeyResponse(BaseModel):
    key: str = Field(..., description="Full API key (shown only once)")
    key_prefix: str
    name: str
    id: str


# ── Intent Schemas ────────────────────────────────────────────
class IntentRequest(BaseModel):
    intent: str = Field(
        ...,
        description="Natural language description of what you want to do",
        examples=[
            "When a new order comes in on Stripe, send a Slack message to #sales and log it in Google Sheets",
            "Send an email to john@example.com with subject 'Meeting Tomorrow' and body 'Hi John, confirming our 3pm meeting.'",
            "Every day at 9am, fetch the weather for Buenos Aires and post it to #general on Slack",
        ]
    )
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context: variables, credentials references, or parameters"
    )
    dry_run: bool = Field(
        default=False,
        description="If true, parse and plan the intent but don't execute"
    )
    require_approval: bool = Field(
        default=False,
        description="If true, pause before execution for human approval"
    )


class ActionStep(BaseModel):
    step: int
    connector: str
    action: str
    description: str
    parameters: dict[str, Any]
    depends_on: list[int] = []


class IntentParsed(BaseModel):
    summary: str
    confidence: float = Field(..., ge=0, le=1)
    steps: list[ActionStep]
    warnings: list[str] = []
    estimated_cost_usd: float = 0.0


class StepResult(BaseModel):
    step: int
    connector: str
    action: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0


class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    intent_raw: str
    intent_parsed: Optional[IntentParsed] = None
    results: list[StepResult] = []
    total_duration_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    created_at: datetime


# ── Connector Schemas ─────────────────────────────────────────
class ConnectorInfo(BaseModel):
    type: str
    name: str
    description: str
    actions: list[str]
    required_config: list[str]
    icon: str = ""


class ConnectorConfigRequest(BaseModel):
    connector_type: str
    config: dict[str, str]


# ── Usage & Billing ───────────────────────────────────────────
class UsageStats(BaseModel):
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_tokens: int
    total_cost_usd: float
    period: str


class PlanInfo(BaseModel):
    plan: str
    executions_per_month: int
    rate_limit_per_minute: int
    connectors_allowed: int
    price_usd: float
    features: list[str]


# ── Generic ───────────────────────────────────────────────────
class SuccessResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
