import base64
import binascii
from contextlib import closing
import hmac
import html
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

import uvicorn
from fasthtml.common import fast_app
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles


PRODUCT_NAME = "Owolot"
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
STATIC_DIR = BASE_DIR / "static"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
logger = logging.getLogger(__name__)

_fasthtml_app, _ = fast_app(
    static_path=str(STATIC_DIR),
    canonical=False,
    default_hdrs=False,
    htmx=False,
    surreal=False,
    sess_cls=None,
    secret_key="sessions-disabled",
)
app = _fasthtml_app
app.routes.insert(
    0,
    Mount("/assets", app=StaticFiles(directory=ASSETS_DIR), name="assets"),
)
app.routes.insert(
    1,
    Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
)

PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#fbfaff">
    <meta name="description" content="A local-first personal finance app for planning, understanding, and managing your money with more intention.">
    <meta property="og:type" content="website">
    <meta property="og:title" content="__PRODUCT_NAME__ — Your money, managed">
    <meta property="og:description" content="A local-first personal finance app for planning, understanding, and managing your money with more intention.">
    <link rel="icon" type="image/png" href="/assets/mascot/happy.png">
    <link rel="stylesheet" href="/static/site.css">
    <title>__PRODUCT_NAME__ — Your money, managed</title>
  </head>
  <body>
    <a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header">
      <div class="header-inner">
        <a class="brand" href="#top" aria-label="__PRODUCT_NAME__ home">
          <img src="/assets/mascot/happy.png" width="44" height="44" alt="">
          <span>__PRODUCT_NAME__</span>
        </a>
        <nav class="main-nav" aria-label="Main navigation">
          <a href="#features">What it does</a>
          <a href="#how-it-works">How it works</a>
          <a href="#privacy">Privacy</a>
          <a class="nav-cta" href="/beta">Request beta access</a>
        </nav>
      </div>
    </header>

    <main id="main">
      <section class="hero section-wrap" id="top" aria-labelledby="hero-title">
        <div class="hero-copy">
          <p class="eyebrow"><span class="eyebrow-dot" aria-hidden="true"></span> A calmer way to handle money</p>
          <h1 id="hero-title">Your money,<br><span>managed</span> — not just monitored.</h1>
          <p class="hero-description">Make a plan, keep your records in one place, and understand where your money is going. Start with a finance app designed to work locally.</p>
          <div class="hero-actions">
            <a class="button button-primary" href="#features">Explore what it does <span aria-hidden="true">→</span></a>
            <span class="availability-note">iOS and Android · Store links coming soon</span>
          </div>
          <div class="hero-trust">
            <span class="trust-icon" aria-hidden="true">✦</span>
            <span>Core features are designed to work on your device</span>
          </div>
        </div>
        <div class="hero-visual">
          <div class="visual-orbit orbit-one" aria-hidden="true"></div>
          <div class="visual-orbit orbit-two" aria-hidden="true"></div>
          <div class="mascot-halo" aria-hidden="true"></div>
          <img class="hero-mascot" src="/assets/mascot/happy.png" width="351" height="351" alt="__PRODUCT_NAME__'s friendly violet owl mascot">
          <div class="float-card float-card-top" aria-hidden="true">
            <span class="float-icon float-icon-lilac">↗</span>
            <span><strong>Plan with purpose</strong><small>One step at a time</small></span>
          </div>
          <div class="float-card float-card-bottom" aria-hidden="true">
            <span class="float-icon float-icon-gold">✦</span>
            <span><strong>Your money, your call</strong><small>Changes need your approval</small></span>
          </div>
          <span class="visual-spark spark-one" aria-hidden="true">✦</span>
          <span class="visual-spark spark-two" aria-hidden="true">✧</span>
        </div>
      </section>

      <section class="intro-band" aria-label="__PRODUCT_NAME__ approach">
        <div class="intro-inner">
          <p>Less guesswork.</p><span aria-hidden="true">✦</span>
          <p>More intention.</p><span aria-hidden="true">✦</span>
          <p>Money on your terms.</p>
        </div>
      </section>

      <section class="section-wrap features-section" id="features" aria-labelledby="features-title">
        <div class="section-heading">
          <p class="eyebrow">A clearer picture</p>
          <h2 id="features-title">From everyday entries<br>to a plan that feels like yours.</h2>
          <p>Bring the moving parts of personal finance into one thoughtful place, without turning your life into a spreadsheet.</p>
        </div>
        <div class="feature-grid">
          <article class="feature-card feature-card-ledger">
            <div class="card-topline"><span class="feature-number">01</span><span class="feature-mark mark-blue" aria-hidden="true">≋</span></div>
            <h3>A ledger you can make sense of</h3>
            <p>Keep track of accounts, income, expenses, and transfers in a local-first ledger.</p>
            <span class="feature-caption">ACCOUNTS · INCOME · EXPENSES</span>
          </article>
          <article class="feature-card feature-card-planning">
            <div class="card-topline"><span class="feature-number">02</span><span class="feature-mark mark-gold" aria-hidden="true">◎</span></div>
            <h3>Plans for real life</h3>
            <p>Organize budgets, envelopes, bills, savings goals, and loans around what matters to you.</p>
            <span class="feature-caption">BUDGETS · BILLS · GOALS</span>
          </article>
          <article class="feature-card feature-card-insights">
            <div class="card-topline"><span class="feature-number">03</span><span class="feature-mark mark-violet" aria-hidden="true">⌁</span></div>
            <h3>Patterns, not just numbers</h3>
            <p>Explore spending and cash-flow insights, with forecasts to help you look ahead.</p>
            <span class="feature-caption">SPENDING · CASH FLOW · FORECASTS</span>
          </article>
          <article class="feature-card feature-card-agent">
            <div class="card-topline"><span class="feature-number">04</span><span class="feature-mark mark-peach" aria-hidden="true">✳</span></div>
            <h3>A helpful assistant, on your terms</h3>
            <p>When online AI is enabled, ask questions about the financial context you choose to share. Review proposed changes and approve them yourself.</p>
            <span class="feature-caption">OPTIONAL ONLINE AI · YOU APPROVE CHANGES</span>
          </article>
        </div>
      </section>

      <section class="how-section" id="how-it-works" aria-labelledby="how-title">
        <div class="section-wrap how-layout">
          <div class="how-copy">
            <p class="eyebrow">Designed around your choices</p>
            <h2 id="how-title">Local by default.<br>Online only by choice.</h2>
            <p class="how-lead">__PRODUCT_NAME__'s core finance tools are designed to work locally. Optional account sign-in, cloud sync, and online AI are separate choices—not one bundled switch.</p>
            <a class="text-link" href="#privacy">See how the choices work <span aria-hidden="true">→</span></a>
          </div>
          <ol class="steps-list">
            <li>
              <span class="step-index">01</span>
              <div><h3>Keep your finances close</h3><p>Use the core features locally on your device.</p></div>
              <span class="step-status">CORE EXPERIENCE</span>
            </li>
            <li>
              <span class="step-index">02</span>
              <div><h3>Sign in if you choose</h3><p>Signing in does not, by itself, turn on cloud sync.</p></div>
              <span class="step-status">OPTIONAL</span>
            </li>
            <li>
              <span class="step-index">03</span>
              <div><h3>Choose sync or online AI separately</h3><p>Each is an optional online feature you can choose to enable.</p></div>
              <span class="step-status">OPTIONAL</span>
            </li>
          </ol>
        </div>
      </section>

      <section class="privacy-section section-wrap" id="privacy" aria-labelledby="privacy-title">
        <div class="privacy-art" aria-hidden="true">
          <div class="privacy-ring ring-outer"></div>
          <div class="privacy-ring ring-inner"></div>
          <div class="privacy-lock"><span>✓</span></div>
          <span class="privacy-star star-a">✦</span><span class="privacy-star star-b">✧</span>
        </div>
        <div class="privacy-copy">
          <p class="eyebrow">Privacy, without the fine-print fog</p>
          <h2 id="privacy-title">You choose what<br>goes online.</h2>
          <p>__PRODUCT_NAME__ is designed so its core features work locally. Optional online features have distinct roles:</p>
          <ul class="privacy-points">
            <li><span class="check" aria-hidden="true">✓</span><span><strong>Sign-in is not sync.</strong> Signing in alone does not enable cloud sync.</span></li>
            <li><span class="check" aria-hidden="true">✓</span><span><strong>Sync is optional.</strong> Encrypted cloud sync is a separate choice.</span></li>
            <li><span class="check" aria-hidden="true">✓</span><span><strong>AI is optional.</strong> If enabled, your question and the financial context you consent to share go through the app's configured Supabase gateway to Groq.</span></li>
            <li><span class="check" aria-hidden="true">✓</span><span><strong>You stay in control.</strong> Agent-proposed changes require your explicit approval before they are applied.</span></li>
          </ul>
          <p class="privacy-note">This is a product overview, not a published privacy policy. No provider retention or security guarantees are made here.</p>
        </div>
      </section>

      <section class="faq-section" id="faq" aria-labelledby="faq-title">
        <div class="section-wrap faq-layout">
          <div class="faq-heading">
            <p class="eyebrow">Good questions</p>
            <h2 id="faq-title">A little more clarity.</h2>
            <p>Here are the basics about how __PRODUCT_NAME__ is designed to work.</p>
          </div>
          <div class="faq-list">
            <details>
              <summary>Can I use __PRODUCT_NAME__ without being online?</summary>
              <p>Core features are designed to work locally on your device. Cloud sync and online AI are optional online features.</p>
            </details>
            <details>
              <summary>Does signing in turn on sync?</summary>
              <p>No. Signing in does not itself enable cloud sync; sync is a separate optional choice.</p>
            </details>
            <details>
              <summary>What happens when I use online AI?</summary>
              <p>When online AI is enabled, your question and the financial context you consent to share are sent through the app's configured Supabase gateway to Groq.</p>
            </details>
            <details>
              <summary>Can an AI suggestion change my finances automatically?</summary>
              <p>No. Agent-proposed changes require your explicit approval before they are applied.</p>
            </details>
            <details>
              <summary>Where can I download the app?</summary>
              <p>__PRODUCT_NAME__ is being made for iOS and Android. Official store links are not available yet.</p>
            </details>
          </div>
        </div>
      </section>

      <section class="download-section section-wrap" id="download" aria-labelledby="download-title">
        <div class="download-card">
          <div class="download-content">
            <p class="eyebrow">A more intentional money routine</p>
            <h2 id="download-title">Make room for<br>the bigger picture.</h2>
            <p>__PRODUCT_NAME__ is being made for iOS and Android. Official download links will appear here when they're ready.</p>
            <a class="button button-light" href="/beta">Request beta access</a>
          </div>
          <img class="download-mascot" src="/assets/mascot/celebrating.png" width="372" height="372" alt="" loading="lazy">
          <span class="download-spark download-spark-one" aria-hidden="true">✦</span>
          <span class="download-spark download-spark-two" aria-hidden="true">✧</span>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div class="footer-inner">
        <a class="brand footer-brand" href="#top" aria-label="__PRODUCT_NAME__ home">
          <img src="/assets/mascot/happy.png" width="36" height="36" alt="">
          <span>__PRODUCT_NAME__</span>
        </a>
        <p>Thoughtful money management, on your terms.</p>
        <nav aria-label="Footer navigation">
          <a href="#features">Features</a>
          <a href="#privacy">Privacy overview</a>
          <a href="#faq">FAQs</a>
          <a href="/beta">Beta access</a>
        </nav>
      </div>
      <div class="footer-bottom"><span>A clearer relationship with money.</span><span>iOS and Android · Official store links coming soon</span></div>
    </footer>
  </body>
</html>
"""

PAGE = PAGE.replace("__PRODUCT_NAME__", PRODUCT_NAME)

SITE_HEADER = """<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/" aria-label="Owolot home">
      <img src="/assets/mascot/happy.png" width="44" height="44" alt="">
      <span>Owolot</span>
    </a>
    <nav class="main-nav" aria-label="Main navigation">
      <a href="/#features">What it does</a>
      <a href="/#how-it-works">How it works</a>
      <a href="/#privacy">Privacy</a>
      <a class="nav-cta" href="/beta">Request beta access</a>
    </nav>
  </div>
</header>"""

SITE_FOOTER = """<footer class="site-footer">
  <div class="footer-inner">
    <a class="brand footer-brand" href="/" aria-label="Owolot home">
      <img src="/assets/mascot/happy.png" width="36" height="36" alt="">
      <span>Owolot</span>
    </a>
    <p>Thoughtful money management, on your terms.</p>
    <nav aria-label="Footer navigation">
      <a href="/">Home</a>
      <a href="/#privacy">Privacy overview</a>
      <a href="/beta">Beta access</a>
    </nav>
  </div>
  <div class="footer-bottom"><span>A clearer relationship with money.</span><span>iOS and Android</span></div>
</footer>"""

BETA_FORM = """<form class="beta-form" method="post" action="/beta" aria-label="Request beta access">
  <label for="beta-email">Email address</label>
  <input id="beta-email" name="email" type="email" autocomplete="email" maxlength="254"
         placeholder="you@example.com" value="__EMAIL__" required>
  <fieldset class="platform-options">
    <legend>Which phone will you use?</legend>
    <label class="platform-option">
      <input type="radio" name="platform" value="ios"__IOS_CHECKED__ required>
      <span class="platform-icon" aria-hidden="true">●</span>
      <span><strong>iPhone or iPad</strong><small>iOS · TestFlight</small></span>
    </label>
    <label class="platform-option">
      <input type="radio" name="platform" value="android"__ANDROID_CHECKED__ required>
      <span class="platform-icon platform-icon-android" aria-hidden="true">●</span>
      <span><strong>Android phone or tablet</strong><small>Google Play testing</small></span>
    </label>
  </fieldset>
  <label class="consent-option">
    <input type="checkbox" name="consent" value="yes"__CONSENT_CHECKED__ required>
    <span>I agree that Owolot may use my email and device type to review this beta request and email me installation instructions.</span>
  </label>
  <button class="button button-primary beta-submit" type="submit">Request beta access <span aria-hidden="true">→</span></button>
  <p class="form-privacy">Only your email address and selected device type are requested. Your request is stored so the team can review it and send installation instructions.</p>
</form>"""


def beta_page(
    *,
    message: str = "",
    status: int = 200,
    email: str = "",
    platform: str = "",
    consent: bool = False,
    success: bool = False,
) -> HTMLResponse:
    feedback = (
        f'<p class="form-feedback" role="status">{html.escape(message)}</p>' if message else ""
    )
    form = (
        BETA_FORM.replace("__EMAIL__", html.escape(email, quote=True))
        .replace("__IOS_CHECKED__", " checked" if platform == "ios" else "")
        .replace("__ANDROID_CHECKED__", " checked" if platform == "android" else "")
        .replace("__CONSENT_CHECKED__", " checked" if consent else "")
    )
    document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#fbfaff">
    <meta name="description" content="Request access to the Owolot beta and learn how installation works on iOS and Android.">
    <link rel="icon" type="image/png" href="/assets/mascot/happy.png">
    <link rel="stylesheet" href="/static/site.css">
    <title>Request beta access — Owolot</title>
  </head>
  <body class="beta-page">
    <a class="skip-link" href="#main">Skip to content</a>
    {SITE_HEADER}
    <main id="main">
      <section class="beta-hero section-wrap" aria-labelledby="beta-title">
        <div class="beta-intro">
          <p class="eyebrow">Help shape what comes next</p>
          <h1 id="beta-title">Get early access<br>to <span>Owolot.</span></h1>
          <p>Tell us where you’d like to try Owolot. After we review your request, we’ll email the installation instructions for your device.</p>
          <div class="beta-availability"><span aria-hidden="true">✦</span> Request access for iOS or Android</div>
        </div>
        <div class="beta-form-card">
          <img class="beta-mascot" src="/assets/mascot/thinking.png" width="330" height="330" alt="" aria-hidden="true">
          <h2>Request beta access</h2>
          <p class="form-lead">Choose your phone and share the email where you’d like to receive your invite.</p>
          {feedback}
          {"" if success else form}
        </div>
      </section>

      <section class="beta-guide-section" aria-labelledby="guide-title">
        <div class="section-wrap">
          <div class="section-heading beta-guide-heading">
            <p class="eyebrow">What happens next</p>
            <h2 id="guide-title">Your install guide,<br>step by step.</h2>
            <p>We’ll send the right instructions after reviewing your request. Store invitations are shared by email when available.</p>
          </div>
          <div class="beta-guide-grid">
            <article class="beta-guide-card">
              <span class="guide-platform guide-ios" aria-hidden="true">iOS</span>
              <h3>For iPhone and iPad</h3>
              <ol>
                <li>Submit your email and choose iOS above.</li>
                <li>After review, look for the TestFlight invitation in that inbox.</li>
                <li>Open the invitation on your device. Install Apple’s TestFlight app if prompted, then accept the invite and install Owolot.</li>
              </ol>
            </article>
            <article class="beta-guide-card">
              <span class="guide-platform guide-android" aria-hidden="true">Android</span>
              <h3>For Android devices</h3>
              <ol>
                <li>Submit your email and choose Android above.</li>
                <li>After review, open the Google Play testing instructions we email you.</li>
                <li>Join the test with the invited Google account, then use Google Play to install Owolot.</li>
              </ol>
            </article>
          </div>
          <p class="beta-guide-note">Testing availability and store invitations are managed by the Owolot team. A request is not an installation link; we’ll email next steps after review.</p>
        </div>
      </section>
    </main>
    {SITE_FOOTER}
  </body>
</html>"""
    return HTMLResponse(document, status_code=status, headers={"Cache-Control": "no-store"})


def database_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "beta_requests.sqlite3")))


def open_database() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS beta_requests (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                platform TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
                requested_at TEXT NOT NULL
            )"""
        )
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def mongodb_config() -> tuple[str, str] | None:
    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        return None
    if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        raise RuntimeError("MONGODB_URI must start with mongodb:// or mongodb+srv://.")
    database_name = os.environ.get("MONGODB_DATABASE", "owolot").strip() or "owolot"
    return uri, database_name


def open_mongodb_client(uri: str):
    from pymongo import MongoClient

    return MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
    )


def supabase_config() -> tuple[str, str] | None:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url and not key:
        return None
    if not url or not key:
        raise RuntimeError(
            "Both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set when configuring Supabase."
        )
    parsed = urllib_parse.urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise RuntimeError("SUPABASE_URL must be a valid HTTP or HTTPS URL.")
    return url, key


def save_beta_request(email: str, platform: str, requested_at: str) -> None:
    mongodb = mongodb_config()
    supabase = supabase_config()
    if mongodb is not None and supabase is not None:
        raise RuntimeError("Configure either MONGODB_URI or SUPABASE_URL, not both.")

    if mongodb is not None:
        uri, database_name = mongodb
        try:
            with closing(open_mongodb_client(uri)) as client:
                client[database_name]["beta_requests"].insert_one(
                    {
                        "email": email,
                        "platform": platform,
                        "requested_at": requested_at,
                    }
                )
        except Exception as exc:
            raise RuntimeError("MongoDB request failed") from exc
        return

    if supabase is not None:
        base_url, api_key = supabase
        endpoint = f"{base_url}/rest/v1/beta_requests"
        payload = json.dumps(
            {
                "email": email,
                "platform": platform,
                "requested_at": requested_at,
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=5) as response:
                if not (200 <= response.status < 300):
                    raise RuntimeError(f"Supabase returned HTTP {response.status}")
        except urllib_error.URLError as exc:
            raise RuntimeError("Supabase request failed") from exc
        return

    with closing(open_database()) as connection, connection:
        connection.execute(
            "INSERT INTO beta_requests (email, platform, requested_at) VALUES (?, ?, ?)",
            (email, platform, requested_at),
        )


def load_beta_requests() -> list[dict[str, str]]:
    mongodb = mongodb_config()
    supabase = supabase_config()
    if mongodb is not None and supabase is not None:
        raise RuntimeError("Configure either MONGODB_URI or SUPABASE_URL, not both.")

    if mongodb is not None:
        uri, database_name = mongodb
        try:
            with closing(open_mongodb_client(uri)) as client:
                cursor = (
                    client[database_name]["beta_requests"]
                    .find({}, {"_id": 0, "email": 1, "platform": 1, "requested_at": 1})
                    .sort("_id", -1)
                    .limit(500)
                )
                items = list(cursor)
        except Exception as exc:
            raise RuntimeError("MongoDB request failed") from exc

        return [
            {
                "email": str(item["email"]),
                "platform": str(item["platform"]),
                "requested_at": str(item["requested_at"]),
            }
            for item in items
        ]

    if supabase is not None:
        base_url, api_key = supabase
        query = urllib_parse.urlencode(
            {
                "select": "email,platform,requested_at",
                "order": "id.desc",
                "limit": "500",
            }
        )
        endpoint = f"{base_url}/rest/v1/beta_requests?{query}"
        req = urllib_request.Request(
            endpoint,
            method="GET",
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=5) as response:
                if not (200 <= response.status < 300):
                    raise RuntimeError(f"Supabase returned HTTP {response.status}")
                body = json.loads(response.read().decode("utf-8"))
        except (urllib_error.URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Supabase request failed") from exc

        if not isinstance(body, list):
            raise RuntimeError("Unexpected Supabase response payload")

        records: list[dict[str, str]] = []
        for item in body:
            if not isinstance(item, dict):
                raise RuntimeError("Unexpected Supabase row format")
            records.append(
                {
                    "email": str(item["email"]),
                    "platform": str(item["platform"]),
                    "requested_at": str(item["requested_at"]),
                }
            )
        return records

    with closing(open_database()) as connection, connection:
        rows = connection.execute(
            "SELECT email, platform, requested_at FROM beta_requests ORDER BY id DESC LIMIT 500"
        ).fetchall()
    return [
        {
            "email": str(row["email"]),
            "platform": str(row["platform"]),
            "requested_at": str(row["requested_at"]),
        }
        for row in rows
    ]


def admin_is_authenticated(request: Request) -> bool:
    expected_username = os.environ.get("BETA_ADMIN_USERNAME")
    expected_password = os.environ.get("BETA_ADMIN_PASSWORD")
    if not expected_username or not expected_password:
        return False

    authorization = request.headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "basic" or not credentials:
        return False

    try:
        username, password = base64.b64decode(credentials, validate=True).decode("utf-8").split(":", 1)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False

    username_matches = hmac.compare_digest(username, expected_username)
    password_matches = hmac.compare_digest(password, expected_password)
    return username_matches and password_matches


def admin_unauthorized() -> Response:
    configured = bool(
        os.environ.get("BETA_ADMIN_USERNAME") and os.environ.get("BETA_ADMIN_PASSWORD")
    )
    if not configured:
        return HTMLResponse(
            "Beta request dashboard is not configured.",
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )
    return HTMLResponse(
        "Sign in is required to view beta requests.",
        status_code=401,
        headers={
            "WWW-Authenticate": 'Basic realm="Owolot beta requests"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/")
def home() -> HTMLResponse:
    return HTMLResponse(PAGE)


@app.get("/beta")
def beta() -> HTMLResponse:
    return beta_page()


@app.post("/beta")
async def submit_beta_request(request: Request) -> Response:
    try:
        form = await request.form()
    except (ValueError, UnicodeDecodeError):
        return beta_page(message="Please complete the request form and try again.", status=400)

    email = str(form.get("email", "")).strip().lower()
    platform = str(form.get("platform", ""))
    consent = form.get("consent") == "yes"

    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        return beta_page(message="Enter a valid email address.", status=422, email=email)
    if platform not in {"ios", "android"}:
        return beta_page(
            message="Choose iOS or Android.",
            status=422,
            email=email,
            consent=consent,
        )
    if not consent:
        return beta_page(
            message="Please agree to the email use described above.",
            status=422,
            email=email,
            platform=platform,
        )
    if not os.environ.get("BETA_ADMIN_USERNAME") or not os.environ.get("BETA_ADMIN_PASSWORD"):
        return beta_page(
            message="Beta requests are not available yet. Please try again later.",
            status=503,
            email=email,
            platform=platform,
            consent=consent,
        )

    try:
        save_beta_request(email, platform, datetime.now(timezone.utc).isoformat())
    except (sqlite3.Error, RuntimeError):
        logger.exception("Could not save beta access request")
        return beta_page(
            message="We couldn’t save your request right now. Please try again later.",
            email=email,
            platform=platform,
            consent=consent,
            status=503,
        )
    except OSError:
        logger.exception("Could not open beta request storage")
        return beta_page(
            message="We couldn’t save your request right now. Please try again later.",
            email=email,
            platform=platform,
            consent=consent,
            status=503,
        )

    return beta_page(
        message="Your request is in. We’ll email installation instructions after review.",
        status=201,
        success=True,
    )


@app.get("/admin/beta")
def beta_admin(request: Request) -> Response:
    if not admin_is_authenticated(request):
        return admin_unauthorized()

    try:
        requests = load_beta_requests()
    except (sqlite3.Error, OSError, RuntimeError, KeyError):
        logger.exception("Could not load beta access requests")
        return HTMLResponse(
            "Beta requests could not be loaded. Check server configuration.",
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )

    rows = "".join(
        "<tr>"
        f"<td>{html.escape(row['email'])}</td>"
        f"<td>{'iOS' if row['platform'] == 'ios' else 'Android'}</td>"
        f"<td>{html.escape(row['requested_at'])}</td>"
        "</tr>"
        for row in requests
    )
    if not rows:
        rows = '<tr><td class="empty-requests" colspan="3">No beta requests yet.</td></tr>'

    document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <title>Beta requests — Owolot admin</title>
    <link rel="stylesheet" href="/static/site.css">
  </head>
  <body class="admin-page">
    {SITE_HEADER}
    <main class="section-wrap admin-main">
      <p class="eyebrow">Private admin</p>
      <h1>Beta access requests</h1>
      <p class="admin-intro">Review the email and device type, then send installation instructions yourself.</p>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <caption class="sr-only">Beta access requests, newest first</caption>
          <thead><tr><th scope="col">Email</th><th scope="col">Device</th><th scope="col">Requested (UTC)</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <p class="admin-note">This page does not send email or share store invitations automatically.</p>
    </main>
    {SITE_FOOTER}
  </body>
</html>"""
    return HTMLResponse(document, headers={"Cache-Control": "no-store"})


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
