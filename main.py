"""
IntentAPI - Tu empleado digital para automatizar
ventas, emails y operaciones. Sin codigo.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
        "Tu empleado digital para PyMEs.\n\n"
        "Automatiza ventas, emails, notificaciones y operaciones con una sola frase.\n\n"
        "Sin codigo. En espanol. Conectado a las herramientas que ya usas.\n\n"
        "**Como funciona:**\n"
        "1. Describi lo que queres hacer en lenguaje natural\n"
        "2. IntentAPI lo entiende y arma un plan de ejecucion con IA\n"
        "3. Ejecuta cada paso: email, Slack, webhooks, SMS\n"
        "4. Te devuelve resultados, logs y costos\n\n"
        "**Empeza:** Registrate -> Crea tu API key -> Manda tu primer intent"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(intent.router, prefix="/api")
app.include_router(connectors.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION, "service": "IntentAPI"}


@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return LANDING_HTML


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return DASHBOARD_HTML


@app.get("/api", tags=["System"])
async def api_root():
    return {
        "service": "IntentAPI",
        "version": settings.APP_VERSION,
        "description": "Automatizacion inteligente para PyMEs",
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal server error", "detail": str(exc) if settings.APP_ENV == "development" else None})


LANDING_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IntentAPI — Tu empleado digital que automatiza tu negocio</title>
<meta name="description" content="Automatiza ventas, emails, notificaciones y mas con una sola frase. Sin codigo. En espanol.">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#09090b;--surface:#18181b;--surface2:#27272a;--border:#3f3f46;--text:#fafafa;--text2:#a1a1aa;--text3:#71717a;--accent:#059669;--accent2:#10b981;--accent-glow:#05966933;--purple:#8b5cf6;--blue:#3b82f6;--orange:#f59e0b;--red:#ef4444;--radius:12px}
html{scroll-behavior:smooth}
body{font-family:'Outfit',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;line-height:1.6}
code,pre,.mono{font-family:'JetBrains Mono',monospace}
.hero{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:2rem;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle at 50% 50%,var(--accent-glow) 0%,transparent 50%);animation:pulse 8s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.3;transform:scale(1)}50%{opacity:.6;transform:scale(1.1)}}
.hero-badge{display:inline-flex;align-items:center;gap:.5rem;background:var(--surface);border:1px solid var(--border);border-radius:100px;padding:.4rem 1rem;font-size:.85rem;color:var(--text2);margin-bottom:2rem;position:relative;z-index:1}
.hero-badge .dot{width:8px;height:8px;background:var(--accent2);border-radius:50%;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
h1{font-size:clamp(2.5rem,7vw,4.5rem);font-weight:900;letter-spacing:-.03em;line-height:1.05;position:relative;z-index:1;max-width:900px}
h1 .gradient{background:linear-gradient(135deg,var(--accent2),#34d399,var(--blue));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:clamp(1.05rem,2vw,1.35rem);color:var(--text2);max-width:650px;margin:1.5rem auto 2.5rem;position:relative;z-index:1;font-weight:300}
.hero-buttons{display:flex;gap:1rem;flex-wrap:wrap;justify-content:center;position:relative;z-index:1}
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.85rem 2rem;border-radius:100px;font-size:1rem;font-weight:600;text-decoration:none;transition:all .2s;border:none;cursor:pointer;font-family:inherit}
.btn-primary{background:var(--accent2);color:#fff;box-shadow:0 0 30px var(--accent-glow)}
.btn-primary:hover{background:var(--accent);transform:translateY(-2px);box-shadow:0 0 50px var(--accent-glow)}
.btn-secondary{background:var(--surface);color:var(--text);border:1px solid var(--border)}
.btn-secondary:hover{border-color:var(--accent2);background:var(--surface2)}
.demo{position:relative;z-index:1;margin-top:4rem;width:100%;max-width:750px}
.demo-window{background:#0d0d0f;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;box-shadow:0 25px 80px rgba(0,0,0,.5)}
.demo-bar{display:flex;align-items:center;gap:.5rem;padding:.75rem 1rem;background:var(--surface);border-bottom:1px solid var(--border)}
.demo-dot{width:12px;height:12px;border-radius:50%}
.demo-bar span{margin-left:auto;font-size:.75rem;color:var(--text3);font-family:'JetBrains Mono',monospace}
.demo-body{padding:1.5rem;font-size:.9rem;line-height:1.8;overflow-x:auto}
.demo-body pre{white-space:pre;color:var(--text2)}
.t-key{color:var(--accent2)}.t-str{color:#34d399}.t-com{color:var(--text3);font-style:italic}.t-num{color:var(--orange)}
section{padding:6rem 2rem;max-width:1200px;margin:0 auto}
.section-label{font-size:.85rem;color:var(--accent2);text-transform:uppercase;letter-spacing:.15em;font-weight:600;margin-bottom:.5rem}
h2{font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;letter-spacing:-.02em;margin-bottom:1rem}
.section-sub{color:var(--text2);font-size:1.1rem;max-width:600px;margin-bottom:3rem}
.pain-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.5rem;margin-bottom:1.5rem}
.pain-card{background:var(--surface);border:1px solid #ef44441a;border-left:3px solid var(--red);border-radius:var(--radius);padding:1.5rem}
.pain-card h3{font-size:1rem;font-weight:700;margin-bottom:.4rem;color:#fca5a5}
.pain-card p{color:var(--text2);font-size:.9rem}
.solution-card{background:var(--surface);border:1px solid #10b9811a;border-left:3px solid var(--accent2);border-radius:var(--radius);padding:1.5rem}
.solution-card h3{font-size:1rem;font-weight:700;margin-bottom:.4rem;color:#6ee7b7}
.solution-card p{color:var(--text2);font-size:.9rem}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:2rem;counter-reset:step}
.step{position:relative;padding:2rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);counter-increment:step}
.step::before{content:counter(step);position:absolute;top:-14px;left:20px;background:var(--accent2);color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.85rem;font-weight:700}
.step h3{margin-bottom:.5rem;font-weight:700;font-size:1.1rem}
.step p{color:var(--text2);font-size:.9rem}
.use-cases{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem}
.use-case{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem 2rem;transition:all .3s}
.use-case:hover{border-color:var(--accent2)}
.use-case .tag{display:inline-block;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;padding:.2rem .6rem;border-radius:100px;margin-bottom:.75rem}
.use-case .intent{font-size:.95rem;color:var(--accent2);font-family:'JetBrains Mono',monospace;margin-bottom:.5rem;line-height:1.5}
.use-case .result{font-size:.85rem;color:var(--text3)}
.features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1.5rem}
.feature-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:2rem;transition:all .3s}
.feature-card:hover{border-color:var(--accent2);transform:translateY(-4px);box-shadow:0 12px 40px rgba(16,185,129,.12)}
.feature-icon{font-size:2rem;margin-bottom:1rem}
.feature-card h3{font-size:1.2rem;font-weight:700;margin-bottom:.5rem}
.feature-card p{color:var(--text2);font-size:.95rem}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:2rem;margin-top:2rem}
.compare-col h3{font-size:1.1rem;font-weight:700;margin-bottom:1rem;padding-bottom:.5rem;border-bottom:2px solid}
.compare-col ul{list-style:none}
.compare-col ul li{padding:.5rem 0;color:var(--text2);font-size:.9rem}
.compare-old h3{border-color:var(--red);color:#fca5a5}
.compare-old li::before{content:'\\2717  ';color:var(--red)}
.compare-new h3{border-color:var(--accent2);color:#6ee7b7}
.compare-new li::before{content:'\\2713  ';color:var(--accent2)}
.conn-grid{display:flex;flex-wrap:wrap;gap:1rem;margin-top:2rem}
.conn-pill{display:inline-flex;align-items:center;gap:.5rem;background:var(--surface);border:1px solid var(--border);border-radius:100px;padding:.5rem 1.25rem;font-size:.9rem;transition:all .2s}
.conn-pill:hover{border-color:var(--accent2);background:var(--surface2)}
.pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1.5rem}
.price-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:2rem;position:relative;transition:all .3s}
.price-card.popular{border-color:var(--accent2);box-shadow:0 0 40px var(--accent-glow)}
.price-card.popular::after{content:'MAS ELEGIDO';position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--accent2);color:#fff;font-size:.7rem;font-weight:700;padding:.3rem .8rem;border-radius:100px;letter-spacing:.05em}
.price-card h3{font-size:1.1rem;font-weight:700;margin-bottom:.25rem}
.price-amount{font-size:2.5rem;font-weight:900;margin:.75rem 0}
.price-amount span{font-size:.9rem;font-weight:400;color:var(--text3)}
.price-features{list-style:none;margin:1.25rem 0}
.price-features li{padding:.4rem 0;color:var(--text2);font-size:.9rem}
.price-features li::before{content:'\\2713  ';color:var(--accent2);font-weight:700}
.price-save{font-size:.8rem;color:var(--accent2);margin-bottom:1rem;font-weight:600}
.cta{text-align:center;padding:6rem 2rem;position:relative}
.cta::before{content:'';position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:80%;height:1px;background:linear-gradient(90deg,transparent,var(--accent2),transparent)}
footer{text-align:center;padding:3rem 2rem;color:var(--text3);font-size:.85rem;border-top:1px solid var(--border)}
footer a{color:var(--text2);text-decoration:none}footer a:hover{color:var(--accent2)}
@media(max-width:640px){.hero{padding:1.5rem}.demo{margin-top:2rem}.hero-buttons{flex-direction:column;align-items:center}section{padding:4rem 1.25rem}.compare{grid-template-columns:1fr}}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-badge"><span class="dot"></span> v1.0 &mdash; En vivo</div>
  <h1>Tu negocio en <span class="gradient">piloto automatico</span></h1>
  <p class="hero-sub">Escribi lo que necesitas en espanol y tu empleado digital lo ejecuta: emails, notificaciones, datos, integraciones. Sin codigo, sin programador.</p>
  <div class="hero-buttons">
    <a href="/docs" class="btn btn-primary">Empezar gratis</a>
    <a href="#dolor" class="btn btn-secondary">Ver como funciona</a>
  </div>
  <div class="demo">
    <div class="demo-window">
      <div class="demo-bar">
        <div class="demo-dot" style="background:#ef4444"></div>
        <div class="demo-dot" style="background:#f59e0b"></div>
        <div class="demo-dot" style="background:#10b981"></div>
        <span>POST /api/v1/intent</span>
      </div>
      <div class="demo-body"><pre><span class="t-com">// Escribi lo que queres. En espanol.</span>
{
  <span class="t-key">"intent"</span>: <span class="t-str">"Cuando entre una venta nueva, manda</span>
            <span class="t-str">un email al cliente confirmando el</span>
            <span class="t-str">pedido y avisale al equipo por Slack"</span>
}

<span class="t-com">// IntentAPI responde:</span>
{
  <span class="t-key">"status"</span>: <span class="t-str">"completed"</span>,
  <span class="t-key">"pasos_ejecutados"</span>: <span class="t-num">2</span>,
  <span class="t-key">"results"</span>: [
    { <span class="t-key">"connector"</span>: <span class="t-str">"email"</span>, <span class="t-key">"status"</span>: <span class="t-str">"enviado"</span> },
    { <span class="t-key">"connector"</span>: <span class="t-str">"slack"</span>, <span class="t-key">"status"</span>: <span class="t-str">"notificado"</span> }
  ],
  <span class="t-key">"costo"</span>: <span class="t-str">"$0.003 USD"</span>
}</pre></div></div></div>
</div>

<section id="dolor">
  <div class="section-label">El problema</div>
  <h2>Tu negocio pierde plata todos los dias</h2>
  <p class="section-sub">Porque tus herramientas no se hablan entre si y todo depende de que alguien lo haga a mano.</p>
  <div class="pain-grid">
    <div class="pain-card"><h3>Ventas que se pierden</h3><p>Un cliente compra y nadie le avisa. El equipo se entera tarde. El stock no se actualiza.</p></div>
    <div class="pain-card"><h3>Horas en tareas repetitivas</h3><p>Copiar datos de un sistema a otro, mandar los mismos emails, actualizar planillas a mano.</p></div>
    <div class="pain-card"><h3>Contratar un dev es carisimo</h3><p>Para conectar 3 herramientas necesitas un programador que cobra $2.000+/mes. Y tarda semanas.</p></div>
  </div>
  <div class="pain-grid">
    <div class="solution-card"><h3>Con IntentAPI</h3><p>Le decis "cuando entre una venta, avisale al cliente y actualiza el stock" y pasa. Sin codigo. En segundos.</p></div>
    <div class="solution-card"><h3>Ahorras 15+ horas/semana</h3><p>Todo lo que hoy haces a mano se automatiza con una frase. Tu equipo se enfoca en vender.</p></div>
    <div class="solution-card"><h3>Cuesta menos que un cafe por dia</h3><p>Desde $29/mes tenes 5.000 acciones automaticas. Menos que un almuerzo y te ahorra un empleado.</p></div>
  </div>
</section>

<section>
  <div class="section-label">Asi de simple</div>
  <h2>Tres pasos. Cero complicacion.</h2>
  <p class="section-sub">No necesitas saber programar. Solo saber escribir.</p>
  <div class="steps">
    <div class="step"><h3>Escribi lo que queres</h3><p>"Manda un email de bienvenida a cada cliente nuevo" o "Todos los viernes mandame un resumen de ventas por Slack".</p></div>
    <div class="step"><h3>La IA entiende y planifica</h3><p>Nuestro motor descompone tu frase en acciones concretas: que conectores usar, en que orden, con que datos.</p></div>
    <div class="step"><h3>Se ejecuta (o vos aprobas)</h3><p>Podes ejecutar al instante, hacer una prueba sin riesgo, o pedir aprobacion manual antes de cada accion.</p></div>
  </div>
</section>

<section>
  <div class="section-label">Casos reales</div>
  <h2>Lo que tus competidores todavia hacen a mano</h2>
  <p class="section-sub">Cada frase es un flujo completo que se ejecuta automaticamente.</p>
  <div class="use-cases">
    <div class="use-case"><div class="tag" style="background:#10b98120;color:#6ee7b7">E-commerce</div><div class="intent">"Cuando entre un pedido, confirma por email, actualiza el stock y avisale a logistica por Slack"</div><div class="result">3 acciones | 0.8 seg | $0.005</div></div>
    <div class="use-case"><div class="tag" style="background:#3b82f620;color:#93c5fd">Agencia</div><div class="intent">"Todos los lunes a las 9am, manda a cada cliente un reporte con las metricas de la semana"</div><div class="result">2 acciones x N clientes | programado | $0.01/cliente</div></div>
    <div class="use-case"><div class="tag" style="background:#f59e0b20;color:#fcd34d">Ventas</div><div class="intent">"Cuando un lead complete el formulario, agregalo al CRM, manda un email de bienvenida y asigna un vendedor"</div><div class="result">3 acciones | 1.2 seg | $0.008</div></div>
    <div class="use-case"><div class="tag" style="background:#8b5cf620;color:#c4b5fd">Admin</div><div class="intent">"Cuando se pague una factura en Stripe, registra el ingreso, avisa al contador por email y archiva el comprobante"</div><div class="result">3 acciones | 0.9 seg | $0.006</div></div>
  </div>
</section>

<section>
  <div class="section-label">Comparacion honesta</div>
  <h2>IntentAPI vs. lo que existe</h2>
  <p class="section-sub">No somos un Zapier mas. Somos la capa que elimina la complejidad.</p>
  <div class="compare">
    <div class="compare-col compare-old"><h3>Zapier / Make / n8n</h3><ul>
      <li>Tenes que armar flujos visuales a mano</li>
      <li>Interfaz en ingles, soporte en ingles</li>
      <li>Necesitas entender triggers y actions</li>
      <li>Si el flujo falla, debuggeas vos</li>
      <li>Precios altos para PyMEs</li>
    </ul></div>
    <div class="compare-col compare-new"><h3>IntentAPI</h3><ul>
      <li>Escribis una frase y se ejecuta</li>
      <li>Funciona en espanol (y cualquier idioma)</li>
      <li>No necesitas saber nada tecnico</li>
      <li>La IA re-intenta y te avisa si falla</li>
      <li>Desde $0/mes (100 acciones gratis)</li>
    </ul></div>
  </div>
</section>

<section>
  <div class="section-label">Conectores</div>
  <h2>Se conecta con lo que ya usas</h2>
  <p class="section-sub">Conectores listos para usar. Y podes agregar cualquier API con webhooks.</p>
  <div class="conn-grid">
    <div class="conn-pill">&#128231; Email / Gmail</div>
    <div class="conn-pill">&#128172; Slack</div>
    <div class="conn-pill">&#127760; Cualquier API</div>
    <div class="conn-pill">&#128276; SMS (Twilio)</div>
    <div class="conn-pill">&#128260; Transformar datos</div>
    <div class="conn-pill">&#128256; Logica condicional</div>
    <div class="conn-pill">&#128179; Stripe</div>
    <div class="conn-pill">&#128202; Google Sheets</div>
    <div class="conn-pill">&#128722; Shopify</div>
    <div class="conn-pill">&#128221; Notion</div>
    <div class="conn-pill" style="border-color:var(--accent2);color:var(--accent2)">+ Proximamente mas</div>
  </div>
</section>

<section>
  <div class="section-label">Por que nos eligen</div>
  <h2>Hecho para negocios reales</h2>
  <div class="features-grid">
    <div class="feature-card"><div class="feature-icon">&#129504;</div><h3>IA que entiende tu negocio</h3><p>Motor de IA avanzado que entiende contexto, maneja ambiguedad y funciona en cualquier idioma.</p></div>
    <div class="feature-card"><div class="feature-icon">&#128737;</div><h3>Seguro y controlable</h3><p>Modo prueba, aprobacion manual, logs paso a paso y rollback automatico si algo falla.</p></div>
    <div class="feature-card"><div class="feature-icon">&#9889;</div><h3>Rapido como un rayo</h3><p>Ejecucion en menos de 1 segundo. Motor asincrono que paraleliza acciones cuando es posible.</p></div>
    <div class="feature-card"><div class="feature-icon">&#128202;</div><h3>Todo medido</h3><p>Cada accion queda registrada con costo, duracion, resultado. Dashboard de uso incluido.</p></div>
    <div class="feature-card"><div class="feature-icon">&#127757;</div><h3>Multi-idioma</h3><p>Manda instrucciones en espanol, portugues, ingles. El idioma que hable tu equipo.</p></div>
    <div class="feature-card"><div class="feature-icon">&#128268;</div><h3>Se conecta a todo</h3><p>Conectores pre-armados + webhooks para cualquier API. Si tiene una URL, lo conectamos.</p></div>
  </div>
</section>

<section id="pricing">
  <div class="section-label">Precios</div>
  <h2>Arranca gratis. Escala cuando quieras.</h2>
  <p class="section-sub">Sin letra chica. Pagas solo por lo que usas.</p>
  <div class="pricing-grid">
    <div class="price-card"><h3>Gratis</h3><p style="color:var(--text3)">Para probar</p><div class="price-amount">$0<span>/mes</span></div><ul class="price-features"><li>100 acciones/mes</li><li>3 conectores</li><li>Soporte comunidad</li><li>Analytics basico</li></ul><a href="/docs" class="btn btn-secondary" style="width:100%;justify-content:center">Empezar gratis</a></div>
    <div class="price-card"><h3>Starter</h3><p style="color:var(--text3)">Para emprendedores</p><div class="price-amount">$29<span>/mes</span></div><div class="price-save">Ahorras +$500/mes vs. hacerlo manual</div><ul class="price-features"><li>5.000 acciones/mes</li><li>10 conectores</li><li>Soporte por email</li><li>Analytics completo</li><li>IA avanzada</li></ul><a href="/docs" class="btn btn-secondary" style="width:100%;justify-content:center">Probar 14 dias</a></div>
    <div class="price-card popular"><h3>Pro</h3><p style="color:var(--text3)">Para negocios en crecimiento</p><div class="price-amount">$149<span>/mes</span></div><div class="price-save">Ahorras +$2.000/mes vs. contratar un dev</div><ul class="price-features"><li>50.000 acciones/mes</li><li>Todos los conectores</li><li>Soporte prioritario</li><li>Conectores custom</li><li>Acceso para equipo</li><li>SLA 99.9%</li></ul><a href="/docs" class="btn btn-primary" style="width:100%;justify-content:center">Probar 14 dias</a></div>
    <div class="price-card"><h3>Enterprise</h3><p style="color:var(--text3)">Para empresas</p><div class="price-amount">$499<span>/mes</span></div><div class="price-save">Reemplaza equipos enteros de integracion</div><ul class="price-features"><li>Acciones ilimitadas</li><li>Soporte dedicado</li><li>SLA personalizado</li><li>SSO / SAML</li><li>Auditoria</li><li>On-premise</li></ul><a href="/docs" class="btn btn-secondary" style="width:100%;justify-content:center">Contactar ventas</a></div>
  </div>
</section>

<div class="cta">
  <h2>Tu competencia ya esta <span style="color:var(--accent2)">automatizando</span></h2>
  <p style="color:var(--text2);max-width:550px;margin:0 auto 2rem">Cada dia que seguis haciendo las cosas a mano, perdes ventas, tiempo y plata. Empeza hoy.</p>
  <div class="hero-buttons">
    <a href="/docs" class="btn btn-primary">Empezar gratis</a>
    <a href="https://github.com/Gianfranco44/intentapi" class="btn btn-secondary">Ver en GitHub</a>
  </div>
</div>

<footer>
  <p>IntentAPI &copy; 2026 &mdash; Hecho en Argentina. Automatizacion inteligente para LATAM.<br>
  <a href="/docs">Documentacion</a> &middot; <a href="/redoc">API Reference</a> &middot; <a href="https://github.com/Gianfranco44/intentapi">GitHub</a></p>
</footer>
</body>
</html>"""


# Read dashboard HTML
with open("dashboard.html", "r") as f:
    DASHBOARD_HTML = f.read()
