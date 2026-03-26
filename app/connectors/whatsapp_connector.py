"""WhatsApp Business Connector - Send messages via Meta Cloud API"""
from typing import Any
import httpx

from app.connectors.base import BaseConnector, registry


@registry.register
class WhatsAppConnector(BaseConnector):
    connector_type = "whatsapp"
    name = "WhatsApp Business"
    description = "Send messages, templates, and media via WhatsApp Business Cloud API"
    icon = "💬"
    actions = ["send_message", "send_template", "send_media"]
    required_config = ["access_token", "phone_number_id"]

    API_BASE = "https://graph.facebook.com/v19.0"

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "send_message": self._send_message,
            "send_template": self._send_template,
            "send_media": self._send_media,
        }
        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return await handler(parameters)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config['access_token']}",
            "Content-Type": "application/json",
        }

    async def _send_message(self, params: dict) -> dict:
        """Send a text message to a WhatsApp number"""
        to = params.get("to", "")
        message = params.get("message", "")

        if not to or not message:
            return {"success": False, "error": "Missing 'to' or 'message' parameter"}

        # Clean phone number (remove +, spaces, dashes)
        to_clean = to.replace("+", "").replace(" ", "").replace("-", "")

        phone_id = self.config["phone_number_id"]
        url = f"{self.API_BASE}/{phone_id}/messages"

        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_clean,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=self._headers(), json=body)
                data = resp.json()

                if resp.status_code == 200 and data.get("messages"):
                    return {
                        "success": True,
                        "message_id": data["messages"][0].get("id", ""),
                        "to": to_clean,
                        "status": "sent",
                    }
                else:
                    error = data.get("error", {})
                    return {
                        "success": False,
                        "error": error.get("message", f"HTTP {resp.status_code}"),
                        "code": error.get("code"),
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_template(self, params: dict) -> dict:
        """Send a pre-approved template message"""
        to = params.get("to", "")
        template_name = params.get("template_name", "")
        language = params.get("language", "es")
        components = params.get("components", [])

        if not to or not template_name:
            return {"success": False, "error": "Missing 'to' or 'template_name'"}

        to_clean = to.replace("+", "").replace(" ", "").replace("-", "")
        phone_id = self.config["phone_number_id"]
        url = f"{self.API_BASE}/{phone_id}/messages"

        body = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }

        if components:
            body["template"]["components"] = components

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=self._headers(), json=body)
                data = resp.json()

                if resp.status_code == 200 and data.get("messages"):
                    return {
                        "success": True,
                        "message_id": data["messages"][0].get("id", ""),
                        "to": to_clean,
                        "template": template_name,
                        "status": "sent",
                    }
                else:
                    error = data.get("error", {})
                    return {"success": False, "error": error.get("message", f"HTTP {resp.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_media(self, params: dict) -> dict:
        """Send media (image, document, video) via URL"""
        to = params.get("to", "")
        media_type = params.get("media_type", "image")  # image, document, video, audio
        media_url = params.get("media_url", "")
        caption = params.get("caption", "")

        if not to or not media_url:
            return {"success": False, "error": "Missing 'to' or 'media_url'"}

        to_clean = to.replace("+", "").replace(" ", "").replace("-", "")
        phone_id = self.config["phone_number_id"]
        url = f"{self.API_BASE}/{phone_id}/messages"

        media_object = {"link": media_url}
        if caption and media_type in ("image", "video", "document"):
            media_object["caption"] = caption
        if media_type == "document":
            media_object["filename"] = params.get("filename", "document")

        body = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": media_type,
            media_type: media_object,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=self._headers(), json=body)
                data = resp.json()

                if resp.status_code == 200 and data.get("messages"):
                    return {
                        "success": True,
                        "message_id": data["messages"][0].get("id", ""),
                        "to": to_clean,
                        "media_type": media_type,
                        "status": "sent",
                    }
                else:
                    error = data.get("error", {})
                    return {"success": False, "error": error.get("message", f"HTTP {resp.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}
