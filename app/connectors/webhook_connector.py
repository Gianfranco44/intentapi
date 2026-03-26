"""Webhook Connector - Make HTTP requests to any URL"""
from typing import Any
import httpx

from app.connectors.base import BaseConnector, registry


@registry.register
class WebhookConnector(BaseConnector):
    connector_type = "webhook"
    name = "Webhook / HTTP"
    description = "Make HTTP requests to any URL or API endpoint"
    icon = "🌐"
    actions = ["http_request"]
    required_config = []

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "http_request":
            return await self._http_request(parameters)
        raise ValueError(f"Unknown action: {action}")

    async def _http_request(self, params: dict) -> dict:
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body")
        query_params = params.get("query_params", {})
        timeout = params.get("timeout", 30)

        if not url:
            return {"success": False, "error": "Missing 'url' parameter"}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if body and isinstance(body, dict) else None,
                    content=body if body and isinstance(body, str) else None,
                    params=query_params,
                )

                try:
                    response_body = response.json()
                except Exception:
                    response_body = response.text[:5000]

                return {
                    "success": 200 <= response.status_code < 400,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_body,
                }
        except httpx.TimeoutException:
            return {"success": False, "error": f"Request to {url} timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
