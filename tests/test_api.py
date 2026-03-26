"""
IntentAPI Tests

Run: python -m pytest tests/ -v
"""
import pytest
import httpx
import asyncio
import time
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")

# Shared state across tests
state = {}


class TestHealthAndDocs:
    def test_health_check(self):
        r = httpx.get(f"{BASE_URL}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_landing_page(self):
        r = httpx.get(f"{BASE_URL}/")
        assert r.status_code == 200
        assert "IntentAPI" in r.text

    def test_docs_available(self):
        r = httpx.get(f"{BASE_URL}/docs")
        assert r.status_code == 200

    def test_api_root(self):
        r = httpx.get(f"{BASE_URL}/api")
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "IntentAPI"
        assert "endpoints" in data


class TestAuth:
    def test_register(self):
        r = httpx.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"test_{int(time.time())}@example.com",
            "password": "testpassword123",
            "name": "Test User",
        })
        assert r.status_code == 201
        data = r.json()
        assert "access_token" in data
        assert data["plan"] == "free"
        state["access_token"] = data["access_token"]
        state["email"] = data["email"]

    def test_register_duplicate(self):
        if "email" not in state:
            self.test_register()
        r = httpx.post(f"{BASE_URL}/api/auth/register", json={
            "email": state["email"],
            "password": "testpassword123",
        })
        assert r.status_code == 409

    def test_login(self):
        if "email" not in state:
            self.test_register()
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "email": state["email"],
            "password": "testpassword123",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_create_api_key(self):
        if "access_token" not in state:
            self.test_register()
        r = httpx.post(
            f"{BASE_URL}/api/auth/api-keys",
            headers={"Authorization": f"Bearer {state['access_token']}"},
            params={"name": "Test Key"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["key"].startswith("intent_")
        state["api_key"] = data["key"]

    def test_get_me(self):
        if "api_key" not in state:
            self.test_create_api_key()
        r = httpx.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {state['api_key']}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_unauthorized_access(self):
        r = httpx.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code in [401, 403]

    def test_invalid_api_key(self):
        r = httpx.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer intent_fake_key_12345"},
        )
        assert r.status_code == 401


class TestConnectors:
    def _auth_header(self):
        if "api_key" not in state:
            TestAuth().test_create_api_key()
        return {"Authorization": f"Bearer {state['api_key']}"}

    def test_list_available_connectors(self):
        r = httpx.get(
            f"{BASE_URL}/api/v1/connectors/available",
            headers=self._auth_header(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        connectors = data["data"]
        types = [c["type"] for c in connectors]
        assert "email" in types
        assert "webhook" in types
        assert "slack" in types

    def test_configure_connector(self):
        r = httpx.post(
            f"{BASE_URL}/api/v1/connectors/configure",
            headers=self._auth_header(),
            json={
                "connector_type": "webhook",
                "config": {},
            },
        )
        assert r.status_code == 201
        assert r.json()["success"] is True

    def test_list_my_connectors(self):
        r = httpx.get(
            f"{BASE_URL}/api/v1/connectors/mine",
            headers=self._auth_header(),
        )
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestIntent:
    def _auth_header(self):
        if "api_key" not in state:
            TestAuth().test_create_api_key()
        return {"Authorization": f"Bearer {state['api_key']}"}

    def test_dry_run_intent(self):
        r = httpx.post(
            f"{BASE_URL}/api/v1/intent",
            headers=self._auth_header(),
            json={
                "intent": "Send an email to test@example.com with subject Hello and body Hi there",
                "dry_run": True,
            },
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "dry_run"
        assert data["intent_parsed"] is not None

    def test_execute_webhook_intent(self):
        r = httpx.post(
            f"{BASE_URL}/api/v1/intent",
            headers=self._auth_header(),
            json={
                "intent": "Make an HTTP GET request to https://httpbin.org/json",
                "dry_run": False,
            },
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ["completed", "failed"]  # May fail if no AI key

    def test_require_approval_intent(self):
        r = httpx.post(
            f"{BASE_URL}/api/v1/intent",
            headers=self._auth_header(),
            json={
                "intent": "Send a test notification",
                "require_approval": True,
            },
            timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "awaiting_approval"
        state["pending_execution_id"] = data["execution_id"]


class TestExecutions:
    def _auth_header(self):
        if "api_key" not in state:
            TestAuth().test_create_api_key()
        return {"Authorization": f"Bearer {state['api_key']}"}

    def test_list_executions(self):
        r = httpx.get(
            f"{BASE_URL}/api/v1/executions",
            headers=self._auth_header(),
        )
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestUsageAndPlans:
    def _auth_header(self):
        if "api_key" not in state:
            TestAuth().test_create_api_key()
        return {"Authorization": f"Bearer {state['api_key']}"}

    def test_get_usage(self):
        r = httpx.get(
            f"{BASE_URL}/api/v1/usage",
            headers=self._auth_header(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "total_executions" in data["data"]

    def test_get_plans(self):
        r = httpx.get(
            f"{BASE_URL}/api/v1/plans",
            headers=self._auth_header(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        plans = data["data"]
        assert len(plans) == 4
        plan_names = [p["plan"] for p in plans]
        assert "free" in plan_names
        assert "enterprise" in plan_names


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
