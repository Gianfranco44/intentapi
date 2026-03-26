"""Transform Connector - Data transformation and processing"""
import json
from typing import Any

from app.connectors.base import BaseConnector, registry


@registry.register
class TransformConnector(BaseConnector):
    connector_type = "transform"
    name = "Transform"
    description = "Transform, filter, map, and format data between steps"
    icon = "🔄"
    actions = ["map", "filter", "aggregate", "format_text", "parse_json", "convert", "merge"]
    required_config = []

    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "format_text": self._format_text,
            "parse_json": self._parse_json,
            "map": self._map_data,
            "filter": self._filter_data,
            "merge": self._merge_data,
            "convert": self._convert,
            "aggregate": self._aggregate,
        }
        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return await handler(parameters)

    async def _format_text(self, params: dict) -> dict:
        template = params.get("template", params.get("input_data", ""))
        variables = params.get("variables", {})
        result = str(template)
        for key, val in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(val))
        return {"success": True, "output": result}

    async def _parse_json(self, params: dict) -> dict:
        try:
            data = json.loads(params.get("input_data", "{}"))
            path = params.get("path", "")
            if path:
                for key in path.split("."):
                    if isinstance(data, dict):
                        data = data.get(key)
                    elif isinstance(data, list) and key.isdigit():
                        data = data[int(key)]
            return {"success": True, "output": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _map_data(self, params: dict) -> dict:
        items = params.get("input_data", [])
        field = params.get("field", None)
        if field and isinstance(items, list):
            return {"success": True, "output": [item.get(field) if isinstance(item, dict) else item for item in items]}
        return {"success": True, "output": items}

    async def _filter_data(self, params: dict) -> dict:
        items = params.get("input_data", [])
        field = params.get("field", "")
        value = params.get("value", "")
        if isinstance(items, list) and field:
            filtered = [i for i in items if isinstance(i, dict) and str(i.get(field)) == str(value)]
            return {"success": True, "output": filtered, "count": len(filtered)}
        return {"success": True, "output": items}

    async def _merge_data(self, params: dict) -> dict:
        sources = params.get("sources", [])
        if isinstance(sources, list):
            merged = {}
            for src in sources:
                if isinstance(src, dict):
                    merged.update(src)
            return {"success": True, "output": merged}
        return {"success": False, "error": "sources must be a list of dicts"}

    async def _convert(self, params: dict) -> dict:
        data = params.get("input_data")
        to_type = params.get("to", "string")
        try:
            if to_type == "string":
                return {"success": True, "output": str(data)}
            elif to_type == "json":
                return {"success": True, "output": json.loads(data) if isinstance(data, str) else data}
            elif to_type == "number":
                return {"success": True, "output": float(data)}
            elif to_type == "boolean":
                return {"success": True, "output": bool(data)}
            return {"success": True, "output": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _aggregate(self, params: dict) -> dict:
        items = params.get("input_data", [])
        op = params.get("operation", "count")
        field = params.get("field")

        if not isinstance(items, list):
            return {"success": False, "error": "input_data must be a list"}

        values = items
        if field:
            values = [i.get(field, 0) for i in items if isinstance(i, dict)]

        if op == "count":
            return {"success": True, "output": len(values)}
        elif op == "sum":
            return {"success": True, "output": sum(float(v) for v in values if v is not None)}
        elif op == "avg":
            nums = [float(v) for v in values if v is not None]
            return {"success": True, "output": sum(nums) / len(nums) if nums else 0}
        return {"success": False, "error": f"Unknown operation: {op}"}
