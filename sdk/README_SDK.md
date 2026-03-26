# IntentAPI Python SDK

Official Python client for [IntentAPI](https://intentapi.onrender.com) — automate anything with natural language.

## Install

```bash
pip install httpx
```

Then copy `intentapi.py` to your project, or install from the repo:

```bash
pip install git+https://github.com/Gianfranco44/intentapi.git#subdirectory=sdk
```

## Quick Start

```python
from intentapi import IntentAPI

api = IntentAPI("intent_your_api_key")

# Execute an intent
result = api.run("Send an email to john@example.com saying Hello World")
print(result.status)       # "completed"
print(result.summary)      # "Send email to john@example.com"
print(result.cost_usd)     # 0.003

# Dry run (plan without executing)
plan = api.plan("When a sale comes in, notify the team on Slack and update the spreadsheet")
print(plan.confidence)     # 0.92
print(len(plan.steps))    # 2
for step in plan.steps:
    print(f"  Step {step.step}: {step.connector}.{step.action}")

# With approval required
result = api.run("Send mass email to all clients", require_approval=True)
print(result.status)       # "awaiting_approval"
# Review, then approve:
final = api.approve(result.execution_id)
```

## Configure Connectors

```python
# Connect Slack
api.configure_connector("slack", {
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
})

# Connect Email
api.configure_connector("email", {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_user": "you@gmail.com",
    "smtp_password": "your-app-password",
    "from_email": "you@gmail.com"
})

# Connect WhatsApp
api.configure_connector("whatsapp", {
    "access_token": "your-meta-access-token",
    "phone_number_id": "your-phone-number-id"
})

# See all available connectors
for c in api.list_connectors():
    print(f"{c.icon} {c.name}: {', '.join(c.actions)}")
```

## Usage Stats

```python
stats = api.usage()
print(f"Executions this month: {stats['total_executions']}")
print(f"Total cost: ${stats['total_cost_usd']}")
```

## One-Liner

```python
from intentapi import run
result = run("intent_your_key", "Make HTTP GET to https://api.example.com/data")
print(result.raw)
```

## Error Handling

```python
from intentapi import IntentAPI, AuthenticationError, RateLimitError

try:
    result = api.run("Do something")
except AuthenticationError:
    print("Bad API key")
except RateLimitError:
    print("Too many requests, upgrade your plan")
```

## Links

- **API Docs**: https://intentapi.onrender.com/docs
- **GitHub**: https://github.com/Gianfranco44/intentapi
- **Landing**: https://intentapi.onrender.com
