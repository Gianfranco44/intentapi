"""
IntentEngine - The Brain of IntentAPI

Parses natural language intents into structured action graphs.
Supports OpenAI (primary) and Anthropic Claude (fallback).
"""
import json
import time
from typing import Any, Optional

import httpx
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
        self.provider = None
        self.api_key = None

        if settings.OPENAI_API_KEY:
            self.provider = "openai"
            self.api_key = settings.OPENAI_API_KEY
        elif settings.ANTHROPIC_API_KEY:
            self.provider = "anthropic"
            self.api_key = settings.ANTHROPIC_API_KEY

    async def parse_intent(
        self, intent: str, context: Optional[dict] = None, user_connectors: list[str] = []
    ) -> tuple[IntentParsed, int]:
        """
        Parse a natural language intent into a structured action plan.
        Returns (parsed_intent, tokens_used)
        """
        if not self.provider:
            return self._fallback_parse(intent, context)

        user_message = f"User intent: {intent}"
        if context:
            user_message += f"\n\nAdditional context: {json.dumps(context)}"
        if user_connectors:
            user_message += f"\n\nUser has these connectors configured: {', '.join(user_connectors)}"

        try:
            if self.provider == "openai":
                return await self._parse_openai(user_message)
            elif self.provider == "anthropic":
                return await self._parse_anthropic(user_message)
            else:
                return self._fallback_parse(intent, context)
        except json.JSONDecodeError:
            return self._fallback_parse(intent, context)
        except Exception as e:
            raise RuntimeError(f"Intent parsing failed: {str(e)}")

    async def _parse_openai(self, user_message: str) -> tuple[IntentParsed, int]:
        """Parse using OpenAI GPT-4o-mini"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                },
            )

            data = response.json()

            if "error" in data:
                raise RuntimeError(f"OpenAI error: {data['error'].get('message', str(data['error']))}")

            raw_text = data["choices"][0]["message"]["content"].strip()

            # Clean markdown wrapping
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            intent_parsed = IntentParsed(
                summary=parsed.get("summary", ""),
                confidence=parsed.get("confidence", 0.5),
                steps=[ActionStep(**step) for step in parsed.get("steps", [])],
                warnings=parsed.get("warnings", []),
                estimated_cost_usd=parsed.get("estimated_cost_usd", 0.001),
            )

            return intent_parsed, tokens_used

    async def _parse_anthropic(self, user_message: str) -> tuple[IntentParsed, int]:
        """Parse using Anthropic Claude"""
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()
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

    def _fallback_parse(self, intent: str, context: Optional[dict] = None) -> tuple[IntentParsed, int]:
        """Smart rule-based fallback when AI is unavailable"""
        import re
        intent_lower = intent.lower()
        steps = []

        # Extract useful data from the intent text
        urls = re.findall(r'https?://[^\s,\'"]+', intent)
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', intent)
        
        # Detect HTTP method
        method = "GET"
        for m in ["POST", "PUT", "DELETE", "PATCH"]:
            if m.lower() in intent_lower or m in intent:
                method = m
                break

        # Multi-step detection: split on "y", "then", "después", "luego", "and"
        has_multi = any(w in intent_lower for w in [" y ", " then ", " después ", " luego ", " and ", " además "])

        # Build steps based on keywords
        step_num = 1

        # Email detection
        if any(w in intent_lower for w in ["email", "mail", "correo", "enviar email", "manda un email", "envía"]):
            to = emails[0] if emails else "{{recipient}}"
            # Try to extract subject and body from intent
            body = intent
            subject = "Notification"
            if "subject" in intent_lower or "asunto" in intent_lower:
                subject_match = re.search(r'(?:subject|asunto)[:\s]+["\']?([^"\']+)["\']?', intent, re.IGNORECASE)
                if subject_match:
                    subject = subject_match.group(1).strip()
            if "saying" in intent_lower or "diciendo" in intent_lower:
                body_match = re.search(r'(?:saying|diciendo|que diga)[:\s]+(.+?)(?:\s+(?:y|and|then)\s|$)', intent, re.IGNORECASE)
                if body_match:
                    body = body_match.group(1).strip()
                    subject = body[:50]

            steps.append(ActionStep(
                step=step_num, connector="email", action="send_email",
                description=f"Send email to {to}",
                parameters={"to": to, "subject": subject, "body": body},
            ))
            step_num += 1

        # Slack detection
        if any(w in intent_lower for w in ["slack", "canal", "channel"]) or (has_multi and "slack" in intent_lower):
            channel_match = re.search(r'#(\w+)', intent)
            channel = f"#{channel_match.group(1)}" if channel_match else "#general"
            message = intent[:200]

            if not steps or has_multi:
                steps.append(ActionStep(
                    step=step_num, connector="slack", action="send_message",
                    description=f"Send Slack message to {channel}",
                    parameters={"channel": channel, "message": message},
                    depends_on=[s.step for s in steps],
                ))
                step_num += 1

        # WhatsApp detection
        if any(w in intent_lower for w in ["whatsapp", "wpp", "wa"]):
            to = emails[0].replace("@", "") if emails else (context or {}).get("phone", "{{phone}}")
            phone_match = re.search(r'[\+]?[\d\s\-]{8,15}', intent)
            if phone_match:
                to = phone_match.group(0).strip()

            steps.append(ActionStep(
                step=step_num, connector="whatsapp", action="send_message",
                description=f"Send WhatsApp message to {to}",
                parameters={"to": to, "message": intent[:500]},
                depends_on=[s.step for s in steps[:-1]] if steps else [],
            ))
            step_num += 1

        # HTTP/Webhook detection
        if any(w in intent_lower for w in ["http", "request", "api", "fetch", "webhook", "get a", "get to"]) or urls:
            url = urls[0] if urls else "{{url}}"
            if not steps or has_multi:
                steps.append(ActionStep(
                    step=step_num, connector="webhook", action="http_request",
                    description=f"{method} request to {url}",
                    parameters={"url": url, "method": method},
                    depends_on=[s.step for s in steps[:-1]] if steps else [],
                ))
                step_num += 1

        # Sheets detection
        if any(w in intent_lower for w in ["sheet", "planilla", "spreadsheet", "google sheet", "hoja de cálculo"]):
            spreadsheet_id = (context or {}).get("spreadsheet_id", "{{spreadsheet_id}}")
            steps.append(ActionStep(
                step=step_num, connector="sheets", action="append_row",
                description="Add data to Google Sheets",
                parameters={"spreadsheet_id": spreadsheet_id, "range": "Sheet1!A1", "values": ["{{data}}"]},
                depends_on=[s.step for s in steps[:-1]] if steps else [],
            ))
            step_num += 1

        # If nothing matched, use transform
        if not steps:
            steps.append(ActionStep(
                step=1, connector="transform", action="format_text",
                description="Process the intent (AI unavailable - fallback mode)",
                parameters={"input_data": intent, "transformation": "analyze"},
            ))

        confidence = 0.5 if len(steps) == 1 else 0.4
        if urls or emails:
            confidence += 0.15

        return IntentParsed(
            summary=f"Parsed {len(steps)} action(s): {intent[:80]}",
            confidence=min(confidence, 0.75),
            steps=steps,
            warnings=["AI engine unavailable — used smart fallback. Add ANTHROPIC_API_KEY for full intelligence."],
            estimated_cost_usd=len(steps) * 0.003,
        ), 0


# Singleton
intent_engine = IntentEngine()
