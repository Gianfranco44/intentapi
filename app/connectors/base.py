"""
Connector System - Universal Adapter Layer

Each connector wraps an external service and exposes
a standard interface for the execution engine.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
import structlog

logger = structlog.get_logger()


class BaseConnector(ABC):
    """Base class for all connectors"""

    connector_type: str = ""
    name: str = ""
    description: str = ""
    icon: str = ""
    actions: list[str] = []
    required_config: list[str] = []

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    @abstractmethod
    async def execute(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute an action with given parameters. Returns result dict."""
        pass

    async def validate_config(self) -> bool:
        """Validate that all required config keys are present"""
        for key in self.required_config:
            if key not in self.config:
                return False
        return True

    def get_info(self) -> dict:
        return {
            "type": self.connector_type,
            "name": self.name,
            "description": self.description,
            "actions": self.actions,
            "required_config": self.required_config,
            "icon": self.icon,
        }


class ConnectorRegistry:
    """Registry of all available connectors"""

    def __init__(self):
        self._connectors: dict[str, type[BaseConnector]] = {}

    def register(self, connector_class: type[BaseConnector]):
        self._connectors[connector_class.connector_type] = connector_class
        return connector_class

    def get(self, connector_type: str) -> Optional[type[BaseConnector]]:
        return self._connectors.get(connector_type)

    def list_all(self) -> list[dict]:
        return [cls({}).get_info() for cls in self._connectors.values()]

    def get_instance(self, connector_type: str, config: dict = None) -> Optional[BaseConnector]:
        cls = self._connectors.get(connector_type)
        if cls:
            return cls(config)
        return None


# Global registry
registry = ConnectorRegistry()
