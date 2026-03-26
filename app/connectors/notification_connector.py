"""Notification Connector - SMS, Push, alerts"""
from typing import Any
import httpx

from app.connectors.base import BaseConnector, registry


@registry.register
class NotificationConnector(BaseConnector):
    connector_type = "notification"
    name = "Notification"
    description = "Send SMS, push notifications, and alerts"
    icon = "🔔"
    actions = ["send_sms", "send_push"]
    required_config = []  # Varies: twilio_sid, twilio_token, twilio_from for SMS

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "send_sms":
            return await self._send_sms(parameters)
        elif action == "send_push":
            return await self._send_push(parameters)
        raise ValueError(f"Unknown action: {action}")

    async def _send_sms(self, params: dict) -> dict:
        """Send SMS via Twilio"""
        sid = self.config.get("twilio_sid")
        token = self.config.get("twilio_token")
        from_number = self.config.get("twilio_from")
        to = params.get("to", "")
        message = params.get("message", "")

        if not all([sid, token, from_number]):
            return {"success": False, "error": "Twilio credentials not configured (twilio_sid, twilio_token, twilio_from)"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                    auth=(sid, token),
                    data={"From": from_number, "To": to, "Body": message},
                )
                data = response.json()
                return {
                    "success": response.status_code == 201,
                    "sid": data.get("sid"),
                    "to": to,
                    "error": data.get("message") if response.status_code != 201 else None,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_push(self, params: dict) -> dict:
        """Send push notification (placeholder — users integrate their provider)"""
        return {
            "success": True,
            "message": "Push notification queued",
            "note": "Configure your push provider (Firebase, OneSignal, etc.) via webhook connector for full integration",
            "params": params,
        }


@registry.register
class ConditionalConnector(BaseConnector):
    connector_type = "conditional"
    name = "Conditional Logic"
    description = "If/then/else branching and switch statements"
    icon = "🔀"
    actions = ["if_then", "switch"]
    required_config = []

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "if_then":
            condition = parameters.get("condition", False)
            if condition:
                return {"success": True, "branch": "then", "execute_steps": parameters.get("then_steps", [])}
            else:
                return {"success": True, "branch": "else", "execute_steps": parameters.get("else_steps", [])}
        elif action == "switch":
            value = str(parameters.get("value", ""))
            cases = parameters.get("cases", {})
            matched = cases.get(value, cases.get("default", []))
            return {"success": True, "matched_case": value, "execute_steps": matched}
        raise ValueError(f"Unknown action: {action}")
