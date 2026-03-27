"""MercadoPago Connector - Payments and notifications for LATAM"""
from typing import Any
import httpx

from app.connectors.base import BaseConnector, registry


@registry.register
class MercadoPagoConnector(BaseConnector):
    connector_type = "mercadopago"
    name = "MercadoPago"
    description = "Procesa pagos, crea links de pago y recibe notificaciones con MercadoPago"
    icon = "💳"
    actions = ["create_payment_link", "check_payment", "search_payments", "create_preference"]
    required_config = ["access_token"]

    API_BASE = "https://api.mercadopago.com"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "create_payment_link": self._create_payment_link,
            "check_payment": self._check_payment,
            "search_payments": self._search_payments,
            "create_preference": self._create_preference,
        }
        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return await handler(parameters)

    async def _create_payment_link(self, params: dict) -> dict:
        """Create a payment link (checkout pro)"""
        title = params.get("title", "Pago")
        amount = params.get("amount", 0)
        currency = params.get("currency", "ARS")
        description = params.get("description", "")
        payer_email = params.get("payer_email", "")

        if not amount:
            return {"success": False, "error": "Missing 'amount' parameter"}

        body = {
            "items": [{
                "title": title,
                "quantity": 1,
                "unit_price": float(amount),
                "currency_id": currency,
                "description": description,
            }],
            "back_urls": {
                "success": params.get("success_url", "https://intentapi.onrender.com"),
                "failure": params.get("failure_url", "https://intentapi.onrender.com"),
            },
            "auto_return": "approved",
        }

        if payer_email:
            body["payer"] = {"email": payer_email}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.API_BASE}/checkout/preferences",
                    headers=self._headers(),
                    json=body,
                )
                data = resp.json()

                if resp.status_code in (200, 201):
                    return {
                        "success": True,
                        "preference_id": data.get("id", ""),
                        "payment_url": data.get("init_point", ""),
                        "sandbox_url": data.get("sandbox_init_point", ""),
                        "title": title,
                        "amount": amount,
                    }
                else:
                    return {"success": False, "error": data.get("message", f"HTTP {resp.status_code}"), "details": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_payment(self, params: dict) -> dict:
        """Check status of a payment by ID"""
        payment_id = params.get("payment_id", "")
        if not payment_id:
            return {"success": False, "error": "Missing 'payment_id'"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.API_BASE}/v1/payments/{payment_id}",
                    headers=self._headers(),
                )
                data = resp.json()

                if resp.status_code == 200:
                    return {
                        "success": True,
                        "payment_id": data.get("id"),
                        "status": data.get("status"),
                        "status_detail": data.get("status_detail"),
                        "amount": data.get("transaction_amount"),
                        "currency": data.get("currency_id"),
                        "payer_email": data.get("payer", {}).get("email"),
                        "date_approved": data.get("date_approved"),
                        "payment_method": data.get("payment_method_id"),
                    }
                else:
                    return {"success": False, "error": data.get("message", f"HTTP {resp.status_code}")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _search_payments(self, params: dict) -> dict:
        """Search recent payments"""
        status = params.get("status", "")
        limit = params.get("limit", 10)
        email = params.get("payer_email", "")

        query_params = {"sort": "date_created", "criteria": "desc", "limit": limit}
        if status:
            query_params["status"] = status
        if email:
            query_params["payer.email"] = email

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.API_BASE}/v1/payments/search",
                    headers=self._headers(),
                    params=query_params,
                )
                data = resp.json()
                results = data.get("results", [])

                return {
                    "success": True,
                    "total": data.get("paging", {}).get("total", 0),
                    "payments": [
                        {
                            "id": p.get("id"),
                            "status": p.get("status"),
                            "amount": p.get("transaction_amount"),
                            "description": p.get("description", ""),
                            "payer_email": p.get("payer", {}).get("email"),
                            "date": p.get("date_created"),
                        }
                        for p in results[:limit]
                    ],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_preference(self, params: dict) -> dict:
        """Alias for create_payment_link"""
        return await self._create_payment_link(params)
