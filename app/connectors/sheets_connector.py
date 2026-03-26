"""Google Sheets Connector - Read/Write spreadsheets"""
from typing import Any
import httpx

from app.connectors.base import BaseConnector, registry


@registry.register
class SheetsConnector(BaseConnector):
    connector_type = "sheets"
    name = "Google Sheets"
    description = "Read, write, and append data to Google Sheets spreadsheets"
    icon = "📊"
    actions = ["read_range", "write_range", "append_row", "create_spreadsheet"]
    required_config = ["service_account_json"]

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "read_range": self._read_range,
            "write_range": self._write_range,
            "append_row": self._append_row,
            "create_spreadsheet": self._create_spreadsheet,
        }
        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return await handler(parameters)

    async def _get_access_token(self) -> str:
        """Get OAuth2 token from service account JSON"""
        import json
        import time
        from jose import jwt as jose_jwt

        sa = json.loads(self.config.get("service_account_json", "{}"))
        if not sa.get("private_key"):
            raise ValueError("Service account JSON missing private_key")

        now = int(time.time())
        payload = {
            "iss": sa["client_email"],
            "scope": "https://www.googleapis.com/auth/spreadsheets",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        signed = jose_jwt.encode(payload, sa["private_key"], algorithm="RS256")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": signed},
            )
            return resp.json().get("access_token", "")

    async def _sheets_request(self, method: str, url: str, body: dict = None) -> dict:
        """Make authenticated request to Sheets API"""
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                resp = await client.put(url, headers=headers, json=body)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return resp.json()

    async def _read_range(self, params: dict) -> dict:
        spreadsheet_id = params.get("spreadsheet_id", "")
        range_name = params.get("range", "Sheet1!A1:Z100")

        if not spreadsheet_id:
            return {"success": False, "error": "Missing spreadsheet_id"}

        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
            data = await self._sheets_request("GET", url)
            values = data.get("values", [])
            return {"success": True, "range": range_name, "rows": len(values), "values": values}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _write_range(self, params: dict) -> dict:
        spreadsheet_id = params.get("spreadsheet_id", "")
        range_name = params.get("range", "Sheet1!A1")
        values = params.get("values", [])

        if not spreadsheet_id:
            return {"success": False, "error": "Missing spreadsheet_id"}

        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}?valueInputOption=USER_ENTERED"
            body = {"range": range_name, "majorDimension": "ROWS", "values": values}
            data = await self._sheets_request("PUT", url, body)
            return {
                "success": True,
                "updated_range": data.get("updatedRange", range_name),
                "updated_rows": data.get("updatedRows", 0),
                "updated_cells": data.get("updatedCells", 0),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _append_row(self, params: dict) -> dict:
        spreadsheet_id = params.get("spreadsheet_id", "")
        range_name = params.get("range", "Sheet1!A1")
        values = params.get("values", [])

        if not spreadsheet_id:
            return {"success": False, "error": "Missing spreadsheet_id"}

        if not isinstance(values[0], list):
            values = [values]

        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
            body = {"range": range_name, "majorDimension": "ROWS", "values": values}
            data = await self._sheets_request("POST", url, body)
            updates = data.get("updates", {})
            return {
                "success": True,
                "updated_range": updates.get("updatedRange", ""),
                "updated_rows": updates.get("updatedRows", 0),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_spreadsheet(self, params: dict) -> dict:
        title = params.get("title", "New Spreadsheet")
        try:
            url = "https://sheets.googleapis.com/v4/spreadsheets"
            body = {"properties": {"title": title}}
            data = await self._sheets_request("POST", url, body)
            return {
                "success": True,
                "spreadsheet_id": data.get("spreadsheetId", ""),
                "url": data.get("spreadsheetUrl", ""),
                "title": title,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
