# 🧠 IntentAPI — Universal Human Intent Interface

> One API to translate natural language into executable actions across any digital system.

[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)

---

## What is IntentAPI?

IntentAPI is a **meta-orchestration layer** that takes plain English (or any language) and converts it into real actions across connected services — email, Slack, webhooks, databases, SMS, and more.

**Not a chatbot. Not a wrapper. A production execution engine.**

```bash
curl -X POST https://your-app.onrender.com/api/v1/intent \
  -H "Authorization: Bearer intent_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Send an email to john@example.com with subject Meeting Tomorrow and body Hi John, confirming our 3pm meeting.",
    "dry_run": false
  }'
```

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/intentapi.git
cd intentapi
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your keys:
# - ANTHROPIC_API_KEY (required for AI parsing)
# - STRIPE_SECRET_KEY (optional, for billing)
```

### 3. Run Locally

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 for the landing page, or http://localhost:8000/docs for interactive API docs.

### 4. First API Call

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password-123"}'

# Get API key (use the access_token from registration)
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Execute an intent
curl -X POST http://localhost:8000/api/v1/intent \
  -H "Authorization: Bearer intent_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Make an HTTP GET request to https://httpbin.org/json", "dry_run": false}'
```

---

## Deploy to Render (Free Tier)

### Option A: One-Click Deploy

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml`
5. Add environment variable: `ANTHROPIC_API_KEY`
6. Deploy!

### Option B: Manual Setup

1. New Web Service → Connect repo
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment:** Python 3
5. Add env vars from `.env.example`
6. Deploy

Your API will be live at `https://your-app.onrender.com`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get access token |
| POST | `/api/auth/api-keys` | Generate API key |
| GET | `/api/auth/me` | Current user info |
| **POST** | **`/api/v1/intent`** | **Execute a natural language intent** |
| POST | `/api/v1/intent/{id}/approve` | Approve pending execution |
| GET | `/api/v1/executions` | List your executions |
| GET | `/api/v1/executions/{id}` | Get execution details |
| GET | `/api/v1/connectors/available` | List available connectors |
| POST | `/api/v1/connectors/configure` | Configure a connector |
| GET | `/api/v1/usage` | Your usage stats |
| GET | `/api/v1/plans` | Pricing plans |

Full interactive docs at `/docs` (Swagger UI) or `/redoc` (ReDoc).

---

## Connectors

| Connector | Actions | Config Required |
|-----------|---------|----------------|
| 📧 Email | send_email, send_template | SMTP credentials |
| 💬 Slack | send_message, send_webhook | Webhook URL or Bot Token |
| 🌐 Webhook | http_request | None |
| 🔄 Transform | map, filter, format_text, parse_json | None |
| 🔔 Notification | send_sms, send_push | Twilio credentials |
| 🔀 Conditional | if_then, switch | None |

### Configure a Connector

```bash
curl -X POST http://localhost:8000/api/v1/connectors/configure \
  -H "Authorization: Bearer intent_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type": "slack",
    "config": {
      "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    }
  }'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   IntentAPI                          │
│                                                     │
│  ┌─────────┐   ┌──────────┐   ┌─────────────────┐  │
│  │  REST   │──▶│  Intent  │──▶│   Execution     │  │
│  │  API    │   │  Engine  │   │   Engine         │  │
│  │         │   │  (Claude)│   │                  │  │
│  └─────────┘   └──────────┘   └──────┬──────────┘  │
│                                       │              │
│                    ┌──────────────────┼───────┐      │
│                    │                  │       │      │
│                ┌───▼──┐ ┌────▼──┐ ┌──▼───┐   │      │
│                │Email │ │Slack │ │HTTP  │ ...│      │
│                └──────┘ └──────┘ └──────┘   │      │
│                    Connector Bus             │      │
│                    └─────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

---

## Pricing Model

| Plan | Price | Executions | Connectors |
|------|-------|-----------|------------|
| Free | $0/mo | 100/mo | 3 |
| Starter | $29/mo | 5,000/mo | 10 |
| Pro | $149/mo | 50,000/mo | All |
| Enterprise | $499/mo | Unlimited | All + Custom |

---

## Tech Stack

- **Runtime:** Python 3.12 + FastAPI + Uvicorn
- **AI Engine:** Anthropic Claude (Sonnet)
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT + API Keys (bcrypt + SHA-256)
- **Deploy:** Render / Docker / Any cloud

---

## License

MIT — Build whatever you want.

---

**Built with ambition. Powered by AI.**
