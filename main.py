"""
╔══════════════════════════════════════════════════════════╗
║          IntentAPI - Universal Human Intent Interface     ║
║                                                          ║
║  Translate natural language → executable actions          ║
║  across any digital system.                              ║
╚══════════════════════════════════════════════════════════╝
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import structlog

from app.config import get_settings
from app.core.database import init_db
from app.middleware import RequestLoggingMiddleware
from app.routes import auth, intent, connectors, usage

settings = get_settings()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.APP_ENV == "development" else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_intentapi", version=settings.APP_VERSION, env=settings.APP_ENV)
    await init_db()
    logger.info("database_initialized")
    yield
    logger.info("shutting_down_intentapi")


app = FastAPI(
    title="IntentAPI",
    description=(
        "🧠 **Universal Human Intent Interface**\n\n"
        "Translate natural language into executable actions across any digital system.\n\n"
        "One API to orchestrate them all — email, Slack, webhooks, databases, "
        "and any service you connect.\n\n"
        "**How it works:**\n"
        "1. Send a natural language intent (e.g., *'Send an email to John about tomorrow's meeting'*)\n"
        "2. IntentAPI parses it into a structured action plan using AI\n"
        "3. Executes each step through connected services\n"
        "4. Returns results, logs, and cost tracking\n\n"
        "**Get started:** Register → Get API key → Send your first intent"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS - allow all origins for API usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(intent.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


# Health check
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": "IntentAPI",
    }


# Landing page
@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return LANDING_HTML


# API status
@app.get("/api", tags=["System"])
async def api_root():
    return {
        "service": "IntentAPI",
        "version": settings.APP_VERSION,
        "description": "Universal Human Intent Interface",
        "docs": "/docs",
        "endpoints": {
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login",
            "execute_intent": "POST /api/v1/intent",
            "connectors": "GET /api/v1/connectors/available",
            "usage": "GET /api/v1/usage",
            "plans": "GET /api/v1/plans",
        },
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc) if settings.APP_ENV == "development" else None},
    )


# ─── LANDING PAGE HTML ────────────────────────────────────────────
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IntentAPI — Universal Human Intent Interface</title>
<meta name="description" content="One API to translate natural language into executable actions across any digital system.">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#09090b;--surface:#18181b;--surface2:#27272a;--border:#3f3f46;
  --text:#fafafa;--text2:#a1a1aa;--text3:#71717a;
  --accent:#6d28d9;--accent2:#8b5cf6;--accent-glow:#7c3aed33;
  --green:#10b981;--blue:#3b82f6;--orange:#f59e0b;--red:#ef4444;
  --radius:12px;
}
html{scroll-behavior:smooth}
body{font-family:'Outfit',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;line-height:1.6}
code,pre,.mono{font-family:'JetBrains Mono',monospace}

/* HERO */
.hero{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:2rem;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle at 50% 50%,var(--accent-glow) 0%,transparent 50%);animation:pulse 8s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.3;transform:scale(1)}50%{opacity:.6;transform:scale(1.1)}}
.hero-badge{display:inline-flex;align-items:center;gap:.5rem;background:var(--surface);border:1px solid var(--border);border-radius:100px;padding:.4rem 1rem;font-size:.85rem;color:var(--text2);margin-bottom:2rem;position:relative;z-index:1}
.hero-badge .dot{width:8px;height:8px;background:var(--green);border-radius:50%;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
h1{font-size:clamp(2.5rem,7vw,5rem);font-weight:900;letter-spacing:-.03em;line-height:1.05;position:relative;z-index:1;max-width:900px}
h1 .gradient{background:linear-gradient(135deg,var(--accent2),var(--blue),var(--green));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:clamp(1.05rem,2vw,1.35rem);color:var(--text2);max-width:650px;margin:1.5rem auto 2.5rem;position:relative;z-index:1;font-weight:300}
.hero-buttons{display:flex;gap:1rem;flex-wrap:wrap;justify-content:center;position:relative;z-index:1}
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.85rem 2rem;border-radius:100px;font-size:1rem;font-weight:600;text-decoration:none;transition:all .2s;border:none;cursor:pointer;font-family:inherit}
.btn-primary{background:var(--accent2);color:#fff;box-shadow:0 0 30px var(--accent-glow)}
.btn-primary:hover{background:var(--accent);transform:translateY(-2px);box-shadow:0 0 50px var(--accent-glow)}
.btn-secondary{background:var(--surface);color:var(--text);border:1px solid var(--border)}
.btn-secondary:hover{border-color:var(--accent2);background:var(--surface2)}

/* CODE DEMO */
.demo{position:relative;z-index:1;margin-top:4rem;width:100%;max-width:750px}
.demo-window{background:#0d0d0f;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;box-shadow:0 25px 80px rgba(0,0,0,.5)}
.demo-bar{display:flex;align-items:center;gap:.5rem;padding:.75rem 1rem;background:var(--surface);border-bottom:1px solid var(--border)}
.demo-dot{width:12px;height:12px;border-radius:50%}
.demo-bar span{margin-left:auto;font-size:.75rem;color:var(--text3);font-family:'JetBrains Mono',monospace}
.demo-body{padding:1.5rem;font-size:.9rem;line-height:1.8;overflow-x:auto}
.demo-body pre{white-space:pre;color:var(--text2)}
.t-key{color:var(--accent2)}.t-str{color:var(--green)}.t-com{color:var(--text3);font-style:italic}
.t-url{color:var(--blue)}.t-num{color:var(--orange)}.t-bool{color:var(--orange)}

/* SECTIONS */
section{padding:6rem 2rem;max-width:1200px;margin:0 auto}
.section-label{font-size:.85rem;color:var(--accent2);text-transform:uppercase;letter-spacing:.15em;font-weight:600;margin-bottom:.5rem}
h2{font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;letter-spacing:-.02em;margin-bottom:1rem}
.section-sub{color:var(--text2);font-size:1.1rem;max-width:600px;margin-bottom:3rem}

/* FEATURES GRID */
.features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1.5rem}
.feature-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:2rem;transition:all .3s}
.feature-card:hover{border-color:var(--accent2);transform:translateY(-4px);box-shadow:0 12px 40px rgba(109,40,217,.15)}
.feature-icon{font-size:2rem;margin-bottom:1rem}
.feature-card h3{font-size:1.2rem;font-weight:700;margin-bottom:.5rem}
.feature-card p{color:var(--text2);font-size:.95rem}

/* HOW IT WORKS */
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:2rem;counter-reset:step}
.step{position:relative;padding:2rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);counter-increment:step}
.step::before{content:counter(step);position:absolute;top:-14px;left:20px;background:var(--accent2);color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.85rem;font-weight:700}
.step h3{margin-bottom:.5rem;font-weight:700;font-size:1.1rem}
.step p{color:var(--text2);font-size:.9rem}

/* PRICING */
.pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem}
.price-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:2rem;position:relative;transition:all .3s}
.price-card.popular{border-color:var(--accent2);box-shadow:0 0 40px var(--accent-glow)}
.price-card.popular::after{content:'MOST POPULAR';position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--accent2);color:#fff;font-size:.7rem;font-weight:700;padding:.3rem .8rem;border-radius:100px;letter-spacing:.05em}
.price-card h3{font-size:1.1rem;font-weight:700;margin-bottom:.25rem}
.price-amount{font-size:2.5rem;font-weight:900;margin:.75rem 0}
.price-amount span{font-size:.9rem;font-weight:400;color:var(--text3)}
.price-features{list-style:none;margin:1.25rem 0}
.price-features li{padding:.4rem 0;color:var(--text2);font-size:.9rem}
.price-features li::before{content:'✓ ';color:var(--green);font-weight:700}

/* CONNECTORS */
.conn-grid{display:flex;flex-wrap:wrap;gap:1rem;margin-top:2rem}
.conn-pill{display:inline-flex;align-items:center;gap:.5rem;background:var(--surface);border:1px solid var(--border);border-radius:100px;padding:.5rem 1.25rem;font-size:.9rem;transition:all .2s}
.conn-pill:hover{border-color:var(--accent2);background:var(--surface2)}

/* CTA */
.cta{text-align:center;padding:6rem 2rem;position:relative}
.cta::before{content:'';position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:80%;height:1px;background:linear-gradient(90deg,transparent,var(--accent2),transparent)}
.cta h2{margin-bottom:1rem}
.cta p{color:var(--text2);max-width:500px;margin:0 auto 2rem}

/* FOOTER */
footer{text-align:center;padding:3rem 2rem;color:var(--text3);font-size:.85rem;border-top:1px solid var(--border)}
footer a{color:var(--text2);text-decoration:none}
footer a:hover{color:var(--accent2)}

@media(max-width:640px){
  .hero{padding:1.5rem}
  .demo{margin-top:2rem}
  .hero-buttons{flex-direction:column;align-items:center}
  section{padding:4rem 1.25rem}
}
</style>
</head>
<body>

<!-- HERO -->
<div class="hero">
  <div class="hero-badge"><span class="dot"></span> v1.0 — Now Live</div>
  <h1>One API to <span class="gradient">execute your intent</span></h1>
  <p class="hero-sub">Translate natural language into real actions across any digital system. Email, Slack, APIs, databases — just say what you need.</p>
  <div class="hero-buttons">
    <a href="/docs" class="btn btn-primary">→ API Docs</a>
    <a href="#how" class="btn btn-secondary">How it works</a>
  </div>

  <div class="demo">
    <div class="demo-window">
      <div class="demo-bar">
        <div class="demo-dot" style="background:#ef4444"></div>
        <div class="demo-dot" style="background:#f59e0b"></div>
        <div class="demo-dot" style="background:#10b981"></div>
        <span>POST /api/v1/intent</span>
      </div>
      <div class="demo-body"><pre>
<span class="t-com">// Just tell it what you want. In any language.</span>
{
  <span class="t-key">"intent"</span>: <span class="t-str">"Send an email to sarah@acme.com saying</span>
            <span class="t-str">the Q3 report is ready, then post a</span>
            <span class="t-str">message to #sales on Slack with the link"</span>,
  <span class="t-key">"dry_run"</span>: <span class="t-bool">false</span>
}

<span class="t-com">// IntentAPI responds:</span>
{
  <span class="t-key">"status"</span>: <span class="t-str">"completed"</span>,
  <span class="t-key">"steps_executed"</span>: <span class="t-num">2</span>,
  <span class="t-key">"results"</span>: [
    { <span class="t-key">"connector"</span>: <span class="t-str">"email"</span>, <span class="t-key">"status"</span>: <span class="t-str">"sent"</span> },
    { <span class="t-key">"connector"</span>: <span class="t-str">"slack"</span>, <span class="t-key">"status"</span>: <span class="t-str">"posted"</span> }
  ],
  <span class="t-key">"cost_usd"</span>: <span class="t-num">0.003</span>
}</pre></div>
    </div>
  </div>
</div>

<!-- HOW IT WORKS -->
<section id="how">
  <div class="section-label">How it works</div>
  <h2>Three steps. Zero complexity.</h2>
  <p class="section-sub">From natural language to executed action in milliseconds.</p>
  <div class="steps">
    <div class="step">
      <h3>Describe your intent</h3>
      <p>Write what you want in plain English, Spanish, or any language. "Send a summary email every Friday" — that's it.</p>
    </div>
    <div class="step">
      <h3>AI parses & plans</h3>
      <p>Our engine decomposes your intent into an action graph: which connectors, what order, what parameters, what dependencies.</p>
    </div>
    <div class="step">
      <h3>Execute or approve</h3>
      <p>Run it instantly, do a dry-run first, or require manual approval. Full logs, rollback, and cost tracking included.</p>
    </div>
  </div>
</section>

<!-- FEATURES -->
<section>
  <div class="section-label">Capabilities</div>
  <h2>Built for real-world automation</h2>
  <p class="section-sub">Not another chatbot wrapper. A production execution engine.</p>
  <div class="features-grid">
    <div class="feature-card">
      <div class="feature-icon">🧠</div>
      <h3>AI-Powered Parsing</h3>
      <p>Claude-powered intent engine understands context, handles ambiguity, and supports any language.</p>
    </div>
    <div class="feature-card">
      <div class="feature-icon">🔌</div>
      <h3>Universal Connectors</h3>
      <p>Email, Slack, Webhooks, databases, SMS — connect once, orchestrate forever. Marketplace for community connectors.</p>
    </div>
    <div class="feature-card">
      <div class="feature-icon">🛡️</div>
      <h3>Safe Execution</h3>
      <p>Dry-run mode, human-in-the-loop approval, step-by-step logs, and automatic rollback on failure.</p>
    </div>
    <div class="feature-card">
      <div class="feature-icon">⚡</div>
      <h3>Sub-Second Latency</h3>
      <p>Async execution engine processes action graphs in parallel when possible. Median response under 800ms.</p>
    </div>
    <div class="feature-card">
      <div class="feature-icon">📊</div>
      <h3>Full Observability</h3>
      <p>Every execution logged with cost, duration, token usage, and step-by-step results. Built-in analytics.</p>
    </div>
    <div class="feature-card">
      <div class="feature-icon">🌍</div>
      <h3>Multi-Language</h3>
      <p>Send intents in English, Spanish, Portuguese, French, Japanese — any language your team speaks.</p>
    </div>
  </div>
</section>

<!-- CONNECTORS -->
<section>
  <div class="section-label">Ecosystem</div>
  <h2>Connect everything</h2>
  <p class="section-sub">Pre-built connectors for the tools you already use. Add your own via the marketplace.</p>
  <div class="conn-grid">
    <div class="conn-pill">📧 Email / SMTP</div>
    <div class="conn-pill">💬 Slack</div>
    <div class="conn-pill">🌐 Webhooks</div>
    <div class="conn-pill">📊 Google Sheets</div>
    <div class="conn-pill">🗄️ PostgreSQL</div>
    <div class="conn-pill">🔔 Twilio SMS</div>
    <div class="conn-pill">🛒 Stripe</div>
    <div class="conn-pill">📁 AWS S3</div>
    <div class="conn-pill">🔄 Data Transform</div>
    <div class="conn-pill">⏰ Scheduler</div>
    <div class="conn-pill">🤖 OpenAI</div>
    <div class="conn-pill">📝 Notion</div>
    <div class="conn-pill">🐙 GitHub</div>
    <div class="conn-pill">📦 Shopify</div>
    <div class="conn-pill">+ Build your own</div>
  </div>
</section>

<!-- PRICING -->
<section id="pricing">
  <div class="section-label">Pricing</div>
  <h2>Start free. Scale as you grow.</h2>
  <p class="section-sub">No hidden fees. Pay only for what you use.</p>
  <div class="pricing-grid">
    <div class="price-card">
      <h3>Free</h3>
      <p style="color:var(--text3)">For experimenting</p>
      <div class="price-amount">$0<span>/mo</span></div>
      <ul class="price-features">
        <li>100 executions/month</li>
        <li>3 connectors</li>
        <li>Community support</li>
        <li>Basic analytics</li>
      </ul>
      <a href="/docs" class="btn btn-secondary" style="width:100%;justify-content:center">Get Started</a>
    </div>
    <div class="price-card">
      <h3>Starter</h3>
      <p style="color:var(--text3)">For indie hackers & small teams</p>
      <div class="price-amount">$29<span>/mo</span></div>
      <ul class="price-features">
        <li>5,000 executions/month</li>
        <li>10 connectors</li>
        <li>Email support</li>
        <li>Full analytics</li>
        <li>Priority parsing</li>
      </ul>
      <a href="/docs" class="btn btn-secondary" style="width:100%;justify-content:center">Start Trial</a>
    </div>
    <div class="price-card popular">
      <h3>Pro</h3>
      <p style="color:var(--text3)">For growing businesses</p>
      <div class="price-amount">$149<span>/mo</span></div>
      <ul class="price-features">
        <li>50,000 executions/month</li>
        <li>All connectors</li>
        <li>Priority support</li>
        <li>Custom connectors</li>
        <li>Team access</li>
        <li>99.9% SLA</li>
      </ul>
      <a href="/docs" class="btn btn-primary" style="width:100%;justify-content:center">Start Trial</a>
    </div>
    <div class="price-card">
      <h3>Enterprise</h3>
      <p style="color:var(--text3)">For organizations at scale</p>
      <div class="price-amount">$499<span>/mo</span></div>
      <ul class="price-features">
        <li>Unlimited executions</li>
        <li>Dedicated support</li>
        <li>Custom SLA</li>
        <li>SSO / SAML</li>
        <li>Audit logs</li>
        <li>On-premise option</li>
      </ul>
      <a href="/docs" class="btn btn-secondary" style="width:100%;justify-content:center">Contact Sales</a>
    </div>
  </div>
</section>

<!-- CTA -->
<div class="cta">
  <h2>Ready to automate <span style="color:var(--accent2)">everything</span>?</h2>
  <p>Join developers and companies already using IntentAPI to eliminate integration complexity forever.</p>
  <div class="hero-buttons">
    <a href="/docs" class="btn btn-primary">→ Start Building</a>
    <a href="https://github.com/YOUR_USERNAME/intentapi" class="btn btn-secondary">⭐ GitHub</a>
  </div>
</div>

<footer>
  <p>IntentAPI &copy; 2026 &mdash; Built with ambition. Powered by AI.<br>
  <a href="/docs">Docs</a> · <a href="/redoc">API Reference</a> · <a href="https://github.com/YOUR_USERNAME/intentapi">GitHub</a></p>
</footer>

</body>
</html>"""
