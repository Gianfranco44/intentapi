"""
IntentAPI Python SDK
====================

Official Python client for IntentAPI — your digital employee that
automates business operations with natural language.

Installation:
    pip install intentapi

Quick start:
    from intentapi import IntentAPI

    api = IntentAPI("intent_your_api_key")
    result = api.run("Send an email to john@example.com saying hello")
    print(result.status)  # "completed"

Full docs: https://intentapi.onrender.com/docs
"""

import httpx
from typing import Optional, Any
from dataclasses import dataclass, field


__version__ = "1.0.0"
DEFAULT_BASE_URL = "https://intentapi.onrender.com"


@dataclass
class StepResult:
    """Result of a single execution step"""
    step: int
    connector: str
    action: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class IntentResult:
    """Result of an intent execution"""
    execution_id: str
    status: str
    intent: str
    summary: str = ""
    confidence: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_duration_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    raw: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status in ("completed", "dry_run")

    @property
    def failed(self) -> bool:
        return self.status == "failed"


@dataclass
class ConnectorInfo:
    """Information about an available connector"""
    type: str
    name: str
    description: str
    actions: list[str]
    required_config: list[str]
    icon: str = ""


class IntentAPIError(Exception):
    """Base exception for IntentAPI errors"""
    def __init__(self, message: str, status_code: int = 0, detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AuthenticationError(IntentAPIError):
    pass


class RateLimitError(IntentAPIError):
    pass


class IntentAPI:
    """
    IntentAPI Python Client

    Usage:
        api = IntentAPI("intent_your_api_key")

        # Execute an intent
        result = api.run("Send email to john@test.com saying Hello")

        # Dry run (plan without executing)
        plan = api.plan("Send email to john@test.com saying Hello")

        # With approval required
        result = api.run("Delete old records", require_approval=True)
        # Later: api.approve(result.execution_id)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        if not api_key:
            raise ValueError("API key is required. Get one at https://intentapi.onrender.com/docs")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"intentapi-python/{__version__}",
            },
            timeout=timeout,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request"""
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise IntentAPIError("Request timed out", status_code=408)
        except httpx.ConnectError:
            raise IntentAPIError(f"Could not connect to {self.base_url}")

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded. Upgrade your plan.", status_code=429)
        if response.status_code >= 400:
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            raise IntentAPIError(
                data.get("detail", f"HTTP {response.status_code}"),
                status_code=response.status_code,
            )

        return response.json()

    # ── Core Methods ──────────────────────────────────────────

    def run(
        self,
        intent: str,
        context: Optional[dict] = None,
        require_approval: bool = False,
    ) -> IntentResult:
        """
        Execute a natural language intent.

        Args:
            intent: What you want to do, in plain language.
            context: Extra variables or parameters.
            require_approval: If True, pauses for human approval.

        Returns:
            IntentResult with execution details.

        Example:
            result = api.run("Send an email to sarah@acme.com saying the report is ready")
            if result.success:
                print(f"Done in {result.total_duration_ms}ms")
        """
        body = {
            "intent": intent,
            "dry_run": False,
            "require_approval": require_approval,
        }
        if context:
            body["context"] = context

        data = self._request("POST", "/api/v1/intent", json=body)
        return self._parse_result(data)

    def plan(
        self,
        intent: str,
        context: Optional[dict] = None,
    ) -> IntentResult:
        """
        Plan an intent without executing it (dry run).

        Returns the parsed action plan so you can review before executing.

        Example:
            plan = api.plan("Delete all inactive users older than 1 year")
            print(f"Plan: {plan.summary}")
            print(f"Steps: {len(plan.steps)}")
            print(f"Confidence: {plan.confidence}")
        """
        body = {"intent": intent, "dry_run": True}
        if context:
            body["context"] = context

        data = self._request("POST", "/api/v1/intent", json=body)
        return self._parse_result(data)

    def approve(self, execution_id: str) -> IntentResult:
        """
        Approve a pending execution (when require_approval=True).

        Example:
            result = api.run("Send mass email to all clients", require_approval=True)
            # Review the plan...
            if looks_good:
                final = api.approve(result.execution_id)
        """
        data = self._request("POST", f"/api/v1/intent/{execution_id}/approve")
        return self._parse_result(data)

    # ── Execution History ─────────────────────────────────────

    def list_executions(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """List your recent executions."""
        data = self._request("GET", f"/api/v1/executions?limit={limit}&offset={offset}")
        return data.get("data", [])

    def get_execution(self, execution_id: str) -> dict:
        """Get details of a specific execution."""
        data = self._request("GET", f"/api/v1/executions/{execution_id}")
        return data.get("data", {})

    # ── Connectors ────────────────────────────────────────────

    def list_connectors(self) -> list[ConnectorInfo]:
        """List all available connectors."""
        data = self._request("GET", "/api/v1/connectors/available")
        return [ConnectorInfo(**c) for c in data.get("data", [])]

    def configure_connector(self, connector_type: str, config: dict) -> dict:
        """
        Configure a connector with your credentials.

        Example:
            api.configure_connector("slack", {
                "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK"
            })
        """
        data = self._request("POST", "/api/v1/connectors/configure", json={
            "connector_type": connector_type,
            "config": config,
        })
        return data

    def my_connectors(self) -> list[dict]:
        """List your configured connectors."""
        data = self._request("GET", "/api/v1/connectors/mine")
        return data.get("data", [])

    # ── Usage & Account ───────────────────────────────────────

    def usage(self) -> dict:
        """Get your usage stats for the current month."""
        data = self._request("GET", "/api/v1/usage")
        return data.get("data", {})

    def plans(self) -> list[dict]:
        """List available plans and pricing."""
        data = self._request("GET", "/api/v1/plans")
        return data.get("data", [])

    def me(self) -> dict:
        """Get your account info."""
        data = self._request("GET", "/api/auth/me")
        return data.get("data", {})

    # ── Helpers ────────────────────────────────────────────────

    def _parse_result(self, data: dict) -> IntentResult:
        parsed = data.get("intent_parsed") or {}
        steps = []
        for r in data.get("results", []):
            steps.append(StepResult(
                step=r.get("step", 0),
                connector=r.get("connector", ""),
                action=r.get("action", ""),
                status=r.get("status", ""),
                output=r.get("output"),
                error=r.get("error"),
                duration_ms=r.get("duration_ms", 0),
            ))

        return IntentResult(
            execution_id=data.get("execution_id", ""),
            status=data.get("status", ""),
            intent=data.get("intent_raw", ""),
            summary=parsed.get("summary", ""),
            confidence=parsed.get("confidence", 0),
            steps=steps,
            warnings=parsed.get("warnings", []),
            total_duration_ms=data.get("total_duration_ms", 0),
            tokens_used=data.get("tokens_used", 0),
            cost_usd=data.get("cost_usd", 0),
            raw=data,
        )

    def health(self) -> dict:
        """Check if the API is healthy."""
        return self._request("GET", "/health")

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self):
        prefix = self.api_key[:12] + "..."
        return f"IntentAPI(key={prefix}, url={self.base_url})"


# ── Convenience function ──────────────────────────────────────

def run(api_key: str, intent: str, **kwargs) -> IntentResult:
    """
    Quick one-liner to execute an intent.

    Example:
        from intentapi import run
        result = run("intent_your_key", "Send email to john@test.com saying hi")
    """
    with IntentAPI(api_key) as api:
        return api.run(intent, **kwargs)
