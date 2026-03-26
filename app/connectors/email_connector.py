"""Email Connector - Send emails via SMTP"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from app.connectors.base import BaseConnector, registry


@registry.register
class EmailConnector(BaseConnector):
    connector_type = "email"
    name = "Email"
    description = "Send emails via SMTP (Gmail, Outlook, custom SMTP)"
    icon = "📧"
    actions = ["send_email", "send_template"]
    required_config = ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email"]

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "send_email":
            return await self._send_email(parameters)
        elif action == "send_template":
            return await self._send_template(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _send_email(self, params: dict) -> dict:
        to = params.get("to", "")
        subject = params.get("subject", "(No subject)")
        body = params.get("body", "")
        html_body = params.get("html_body")

        if not to:
            return {"success": False, "error": "Missing 'to' parameter"}

        msg = MIMEMultipart("alternative")
        msg["From"] = self.config.get("from_email", self.config.get("smtp_user", ""))
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.config["smtp_host"], int(self.config["smtp_port"])) as server:
                server.starttls()
                server.login(self.config["smtp_user"], self.config["smtp_password"])
                server.send_message(msg)

            return {"success": True, "message": f"Email sent to {to}", "to": to, "subject": subject}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_template(self, params: dict) -> dict:
        template = params.get("template", "")
        variables = params.get("variables", {})
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        params["body"] = template
        return await self._send_email(params)
