"""Import all connectors to trigger registration"""
from app.connectors.base import registry
from app.connectors.email_connector import EmailConnector
from app.connectors.webhook_connector import WebhookConnector
from app.connectors.slack_connector import SlackConnector
from app.connectors.transform_connector import TransformConnector
from app.connectors.notification_connector import NotificationConnector, ConditionalConnector
from app.connectors.sheets_connector import SheetsConnector
from app.connectors.whatsapp_connector import WhatsAppConnector

__all__ = ["registry"]
