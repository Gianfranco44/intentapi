"""
IntentEngine - The Brain of IntentAPI

Parses natural language intents into structured action graphs
using Claude as the reasoning backbone.
"""
import json
import time
from typing import Any, Optional

import anthropic
from app.config import get_settings
from app.models.schemas import IntentParsed, ActionStep

settings = get_settings()

SYSTEM_PROMPT = """You are IntentEngine, the core reasoning module of IntentAPI — a Universal Human Intent Interface.

Your job: take a natural language intent from a user and decompose it into a precise, executable action graph.

## Available Connectors and Actions

1. **email** — Send emails
   - Actions: send_email, send_template
   - Params: to, cc, bcc, subject, body, html_body, attachments

2. **slack** — Slack messaging
   - Actions: send_message, create_channel, list_channels
   - Params: channel, message, username

3. **webhook** — HTTP requests to any URL
   - Actions: http_request
   - Params: url, method, headers, body, query_params

4. **sheets** — Google Sheets operations
   - Actions: read_range, write_range, append_row, create_spreadsheet
   - Params: spreadsheet_id, range, values

5. **database** — SQL database operations
   - Actions: query, insert, update, delete
   - Params: connection_string, query, params

6. **scheduler** — Cron/scheduled tasks
   - Actions: create_schedule, delete_schedule
   - Params: cron_expression, intent_to_run

7. **storage** — File storage (S3-compatible)
   - Actions: upload, download, list, delete
   - Params: bucket, key, file_data

8. **transform** — Data transformation
   - Actions: map, filter, aggregate, format_text, parse_json, convert
   - Params: input_data, transformation, template

9. **conditional** — Logic branching
   - Actions: if_then, switch
   - Params: condition, then_steps, else_steps

10. **notification** — Push notifications / SMS
    - Actions: send_sms, send_push
    - Params: to, message, provider

## Output Format

Respond with ONLY valid JSON (no markdown, no explanation) in this exact format:
{
  "summary": "Brief description of what will happen",
  "confidence": 0.0-1.0,
  "steps": [
    {
      "step": 1,
      "connector": "connector_name",
      "action": "action_name",
      "description": "What this step does",
      "parameters": { ... },
      "depends_on": []
    }
  ],
  "warnings": ["Any concerns or ambiguities"],
  "estimated_cost_usd": 0.001
}

## Rules
- Break complex intents into atomic steps
- Use depends_on to define execution order (step numbers that must complete first)
- If the intent is ambiguous, set confidence < 0.7 and add warnings
- If a connector isn't available for the task, use "webhook" with a descriptive URL placeholder
- Estimate cost based on: $0.001 per simple action, $0.005 per API call, $0.01 per AI-processed step
- Be precise with parameters — use placeholders like {{user.email}} for dynamic values
- For scheduled/recurring intents, wrap the actions inside a scheduler step
"""


class IntentEngine:
    """Parses natural language intents into executable action graphs"""

    def __init__(self):
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def parse_intent(
        self, intent: str, context: Optional[dict] = None, user_connectors: list[str] = []
    ) -> tuple[IntentParsed, int]:
        """
        Parse a natural language intent into a structured action plan.
        Returns (parsed_intent, tokens_used)
        """
        if not self.client:
            return self._fallback_parse(intent, context)

        user_message = f"User intent: {intent}"
        if context:
            user_message += f"\n\nAdditional context: {json.dumps(context)}"
        if user_connectors:
            user_message += f"\n\nUser has these connectors configured: {', '.join(user_connectors)}"

        start = time.time()

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            raw_text = response.content[0].text.strip()
            # Clean potential markdown wrapping
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            intent_parsed = IntentParsed(
                summary=parsed.get("summary", ""),
                confidence=parsed.get("confidence", 0.5),
                steps=[ActionStep(**step) for step in parsed.get("steps", [])],
                warnings=parsed.get("warnings", []),
                estimated_cost_usd=parsed.get("estimated_cost_usd", 0.001),
            )

            return intent_parsed, tokens_used

        except json.JSONDecodeError:
            return self._fallback_parse(intent, context)
        except Exception as e:
            raise RuntimeError(f"Intent parsing failed: {str(e)}")

    def _fallback_parse(self, intent: str, context: Optional[dict] = None) -> tuple[IntentParsed, int]:
        """Simple rule-based fallback when AI is unavailable"""
        intent_lower = intent.lower()
        steps = []

        if any(w in intent_lower for w in ["email", "mail", "send", "enviar", "correo"]):
            steps.append(ActionStep(
                step=1,
                connector="email",
                action="send_email",
                description="Send an email based on the intent",
                parameters={"to": "{{recipient}}", "subject": "{{subject}}", "body": "{{body}}"},
            ))
        elif any(w in intent_lower for w in ["slack", "message", "notify", "canal", "mensaje"]):
            steps.append(ActionStep(
                step=1,
                connector="slack",
                action="send_message",
                description="Send a Slack message",
                parameters={"channel": "{{channel}}", "message": "{{message}}"},
            ))
        elif any(w in intent_lower for w in ["http", "request", "api", "fetch", "webhook"]):
            steps.append(ActionStep(
                step=1,
                connector="webhook",
                action="http_request",
                description="Make an HTTP request",
                parameters={"url": "{{url}}", "method": "GET"},
            ))
        else:
            steps.append(ActionStep(
                step=1,
                connector="transform",
                action="format_text",
                description="Process the intent (AI unavailable - fallback mode)",
                parameters={"input_data": intent, "transformation": "analyze"},
            ))

        return IntentParsed(
            summary=f"Fallback parsing for: {intent[:100]}",
            confidence=0.3,
            steps=steps,
            warnings=["AI engine unavailable — used rule-based fallback. Results may be imprecise."],
            estimated_cost_usd=0.0,
        ), 0


# Singleton
intent_engine = IntentEngine()
