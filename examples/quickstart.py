"""
IntentAPI - Quick Start Examples

These examples show how to use IntentAPI from Python.
"""

# ── Setup ─────────────────────────────────────────────────
# pip install httpx
# or copy intentapi_sdk.py to your project

from intentapi_sdk import IntentAPI, IntentAPIAuth

BASE_URL = "https://your-app.onrender.com"  # or http://localhost:8000


# ═══════════════════════════════════════════════════════════
# EXAMPLE 1: Quick Setup (register + get API key)
# ═══════════════════════════════════════════════════════════

auth = IntentAPIAuth(BASE_URL)
client = auth.quick_setup("you@example.com", "your-password-123", name="Your Name")
print(f"Ready! Client: {client}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 2: Send an email
# ═══════════════════════════════════════════════════════════

# First, configure email connector
client.configure_connector("email", {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_user": "you@gmail.com",
    "smtp_password": "your-app-password",
    "from_email": "you@gmail.com",
})

# Now just say what you want
result = client.run("Send an email to john@example.com with subject 'Hello' and body 'Hi John, this is automated!'")
print(result)


# ═══════════════════════════════════════════════════════════
# EXAMPLE 3: Dry Run (plan without executing)
# ═══════════════════════════════════════════════════════════

plan = client.plan("When a new payment arrives, send a Slack message to #sales and log it in a spreadsheet")
print(f"Confidence: {plan['intent_parsed']['confidence']}")
print(f"Steps: {len(plan['intent_parsed']['steps'])}")
for step in plan['intent_parsed']['steps']:
    print(f"  Step {step['step']}: [{step['connector']}] {step['description']}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 4: Webhook / HTTP Request
# ═══════════════════════════════════════════════════════════

result = client.run("Make a GET request to https://api.github.com/users/octocat")
print(result["results"][0]["output"])


# ═══════════════════════════════════════════════════════════
# EXAMPLE 5: Multi-step with approval
# ═══════════════════════════════════════════════════════════

pending = client.run(
    "Send an email to the team about the deployment, then post to #engineering on Slack",
    require_approval=True,
)
print(f"Status: {pending['status']}")  # "awaiting_approval"
print(f"Plan: {pending['intent_parsed']['summary']}")

# Review the plan, then approve:
# confirmed = client.approve(pending['execution_id'])


# ═══════════════════════════════════════════════════════════
# EXAMPLE 6: Slack notifications
# ═══════════════════════════════════════════════════════════

client.configure_connector("slack", {
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
})

result = client.run("Send a message to Slack saying 'Deployment v2.1 complete ✅'")
print(result)


# ═══════════════════════════════════════════════════════════
# EXAMPLE 7: Check usage
# ═══════════════════════════════════════════════════════════

usage = client.usage()
print(f"Executions this month: {usage['data']['total_executions']}")
print(f"Cost: ${usage['data']['total_cost_usd']}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 8: Multi-language (Spanish)
# ═══════════════════════════════════════════════════════════

result = client.plan("Enviá un email a pedro@ejemplo.com con asunto 'Reunión mañana' y cuerpo 'Hola Pedro, confirmamos la reunión de las 15hs'")
print(result)
