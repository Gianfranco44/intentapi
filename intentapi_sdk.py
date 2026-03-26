"""
IntentAPI Python SDK

Install: pip install intentapi (or copy this file)

Usage:
    from intentapi_sdk import IntentAPI

    client = IntentAPI("intent_your_api_key", base_url="https://your-app.onrender.com")

    # Execute an intent
    result = client.run("Send an email to john@example.com saying hello")
    print(result)

    # Dry run
    plan = client.plan("When Stripe gets a payment, notify #sales on Slack")
    print(plan)

    # With approval workflow
    pending = client.run("Delete all inactive users", require_approval=True)
    # Review the plan...
    confirmed = client.approve(pending["execution_id"])
"""
import httpx
from typing import Optional, Any


class IntentAPIError(Exception):
    def __init__(self, status_code: int, message: str, detail: str = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f"[{status_code}] {message}")


class IntentAPI:
    """IntentAPI Python SDK Client"""

    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "IntentAPI-Python-SDK/1.0",
        }

    def _request(self, method: str, path: str, json: dict = None, params: dict = None) -> dict:
        with httpx.Client(timeout=120) as client:
            response = client.request(
                method, f"{self.base_url}{path}",
                headers=self._headers, json=json, params=params,
            )
        if response.status_code >= 400:
            try:
                body = response.json()
                raise IntentAPIError(response.status_code, body.get("detail", body.get("error", "Unknown error")))
            except (ValueError, KeyError):
                raise IntentAPIError(response.status_code, response.text)
        return response.json()

    # ── Core Methods ─────────────────────────────────────────

    def run(
        self,
        intent: str,
        context: Optional[dict] = None,
        require_approval: bool = False,
    ) -> dict:
        """
        Execute a natural language intent.

        Args:
            intent: What you want to do, in plain language
            context: Optional additional context (variables, params)
            require_approval: If True, pauses for human approval

        Returns:
            Execution result with status, steps, and outputs
        """
        payload = {
            "intent": intent,
            "dry_run": False,
            "require_approval": require_approval,
        }
        if context:
            payload["context"] = context
        return self._request("POST", "/api/v1/intent", json=payload)

    def plan(self, intent: str, context: Optional[dict] = None) -> dict:
        """
        Dry-run: parse the intent and return the action plan
        WITHOUT executing anything.

        Args:
            intent: What you want to do
            context: Optional context

        Returns:
            Parsed action plan with steps, confidence, warnings
        """
        payload = {"intent": intent, "dry_run": True}
        if context:
            payload["context"] = context
        return self._request("POST", "/api/v1/intent", json=payload)

    def approve(self, execution_id: str) -> dict:
        """Approve a pending execution."""
        return self._request("POST", f"/api/v1/intent/{execution_id}/approve")

    # ── Execution History ────────────────────────────────────

    def executions(self, limit: int = 20, offset: int = 0) -> dict:
        """List your recent executions."""
        return self._request("GET", "/api/v1/executions", params={"limit": limit, "offset": offset})

    def execution(self, execution_id: str) -> dict:
        """Get details of a specific execution."""
        return self._request("GET", f"/api/v1/executions/{execution_id}")

    # ── Connectors ───────────────────────────────────────────

    def connectors(self) -> dict:
        """List all available connectors."""
        return self._request("GET", "/api/v1/connectors/available")

    def my_connectors(self) -> dict:
        """List your configured connectors."""
        return self._request("GET", "/api/v1/connectors/mine")

    def configure_connector(self, connector_type: str, config: dict) -> dict:
        """
        Configure a connector with your credentials.

        Args:
            connector_type: e.g., "email", "slack", "webhook"
            config: Credentials dict (e.g., {"webhook_url": "https://..."})
        """
        return self._request("POST", "/api/v1/connectors/configure", json={
            "connector_type": connector_type, "config": config,
        })

    # ── Account ──────────────────────────────────────────────

    def me(self) -> dict:
        """Get your account info."""
        return self._request("GET", "/api/auth/me")

    def usage(self) -> dict:
        """Get your usage stats for the current month."""
        return self._request("GET", "/api/v1/usage")

    def plans(self) -> dict:
        """List available pricing plans."""
        return self._request("GET", "/api/v1/plans")

    # ── Convenience ──────────────────────────────────────────

    def __repr__(self):
        prefix = self.api_key[:12] + "..." if len(self.api_key) > 12 else self.api_key
        return f"IntentAPI(key={prefix}, url={self.base_url})"


# ── Auth Helper (for initial setup) ─────────────────────────

class IntentAPIAuth:
    """Helper for registration and login (before you have an API key)"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def register(self, email: str, password: str, name: str = None) -> dict:
        """Register a new account. Returns access token."""
        payload = {"email": email, "password": password}
        if name:
            payload["name"] = name
        with httpx.Client() as client:
            r = client.post(f"{self.base_url}/api/auth/register", json=payload)
        return r.json()

    def login(self, email: str, password: str) -> dict:
        """Login and get access token."""
        with httpx.Client() as client:
            r = client.post(f"{self.base_url}/api/auth/login", json={"email": email, "password": password})
        return r.json()

    def create_api_key(self, access_token: str, name: str = "SDK Key") -> dict:
        """Create an API key using an access token."""
        with httpx.Client() as client:
            r = client.post(
                f"{self.base_url}/api/auth/api-keys",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"name": name},
            )
        return r.json()

    def quick_setup(self, email: str, password: str, name: str = None) -> IntentAPI:
        """Register (or login), create API key, and return a ready-to-use client."""
        try:
            auth = self.register(email, password, name)
        except Exception:
            auth = self.login(email, password)

        token = auth.get("access_token")
        if not token:
            raise IntentAPIError(401, "Failed to get access token")

        key_data = self.create_api_key(token)
        api_key = key_data.get("key")
        if not api_key:
            raise IntentAPIError(500, "Failed to create API key")

        return IntentAPI(api_key, self.base_url)
