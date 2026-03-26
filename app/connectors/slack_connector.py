"""Slack Connector - Send messages to Slack"""
from typing import Any
import httpx

from app.connectors.base import BaseConnector, registry


@registry.register
class SlackConnector(BaseConnector):
    connector_type = "slack"
    name = "Slack"
    description = "Send messages and manage channels in Slack"
    icon = "💬"
    actions = ["send_message", "send_webhook"]
    required_config = ["webhook_url"]  # Simplest: incoming webhook. Or "bot_token" for full API.

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "send_message":
            return await self._send_message(parameters)
        elif action == "send_webhook":
            return await self._send_webhook(parameters)
        raise ValueError(f"Unknown action: {action}")

    async def _send_message(self, params: dict) -> dict:
        """Send via Bot Token + API"""
        bot_token = self.config.get("bot_token")
        if bot_token:
            channel = params.get("channel", "#general")
            message = params.get("message", "")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {bot_token}", "Content-Type": "application/json"},
                    json={"channel": channel, "text": message},
                )
                data = response.json()
                return {
                    "success": data.get("ok", False),
                    "channel": channel,
                    "ts": data.get("ts"),
                    "error": data.get("error"),
                }

        # Fallback to webhook
        return await self._send_webhook(params)

    async def _send_webhook(self, params: dict) -> dict:
        """Send via Incoming Webhook URL"""
        webhook_url = self.config.get("webhook_url", "")
        message = params.get("message", "")

        if not webhook_url:
            return {"success": False, "error": "No webhook_url or bot_token configured"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json={"text": message})
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "message": message[:100],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
