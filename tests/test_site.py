import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from main import app


class LandingPageTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.data_dir = tempfile.TemporaryDirectory()
        self.env_patch = patch.dict(
            os.environ,
            {
                "DATABASE_PATH": str(Path(self.data_dir.name) / "requests.sqlite3"),
                "BETA_ADMIN_USERNAME": "test-admin",
                "BETA_ADMIN_PASSWORD": "test-password",
            },
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.addCleanup(self.data_dir.cleanup)

    def test_home_page_has_the_landing_page_sections_and_accessibility_landmarks(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("set-cookie", response.headers)
        self.assertIn('lang="en"', response.text)
        self.assertIn('href="#main">Skip to content</a>', response.text)
        self.assertIn('<main id="main">', response.text)
        self.assertIn('id="features"', response.text)
        self.assertIn('id="how-it-works"', response.text)
        self.assertIn('id="privacy"', response.text)
        self.assertIn('id="faq"', response.text)
        self.assertIn('id="download"', response.text)
        self.assertIn('href="/beta">Request beta access</a>', response.text)
        self.assertIn("<title>Owolot — Your money, managed</title>", response.text)

    def test_page_uses_verified_product_and_privacy_language_without_fake_store_links(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("accounts, income, expenses, and transfers", response.text)
        self.assertIn("budgets, envelopes, bills, savings goals, and loans", response.text)
        self.assertIn("Signing in does not itself enable cloud sync", response.text)
        self.assertIn("Encrypted cloud sync is a separate choice", response.text)
        self.assertIn("Supabase gateway to Groq", response.text)
        self.assertIn("Agent-proposed changes require your explicit approval", response.text)
        self.assertIn("Official store links are not available yet.", response.text)
        self.assertNotIn("play.google.com", response.text)
        self.assertNotIn("apps.apple.com", response.text)
        self.assertNotIn('rel="canonical"', response.text)

    def test_beta_page_has_consent_platform_choices_and_installation_guides(self):
        response = self.client.get("/beta")

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="email" type="email"', response.text)
        self.assertIn('name="platform" value="ios"', response.text)
        self.assertIn('name="platform" value="android"', response.text)
        self.assertIn('name="consent" value="yes" required', response.text)
        self.assertIn("TestFlight invitation", response.text)
        self.assertIn("Google Play testing instructions", response.text)
        self.assertNotIn("testflight.apple.com/join", response.text)
        self.assertNotIn("play.google.com/apps/testing", response.text)
        self.assertIn('href="/#features"', response.text)

    def test_beta_request_is_stored_and_shows_confirmation(self):
        response = self.client.post(
            "/beta",
            data={"email": "  Tester@Example.com ", "platform": "ios", "consent": "yes"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("Your request is in", response.text)
        self.assertIn("We’ll email installation instructions after review.", response.text)
        self.assertNotIn('name="email"', response.text)

        authorization = "Basic " + base64.b64encode(b"test-admin:test-password").decode()
        dashboard = self.client.get("/admin/beta", headers={"Authorization": authorization})
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("tester@example.com", dashboard.text)
        self.assertIn("<td>iOS</td>", dashboard.text)

    def test_beta_request_requires_valid_email_platform_and_consent(self):
        invalid_email = self.client.post(
            "/beta", data={"email": "not-an-email", "platform": "ios", "consent": "yes"}
        )
        no_consent = self.client.post(
            "/beta", data={"email": "test@example.com", "platform": "ios"}
        )
        invalid_platform = self.client.post(
            "/beta",
            data={"email": "test@example.com", "platform": "windows", "consent": "yes"},
        )

        self.assertEqual(invalid_email.status_code, 422)
        self.assertIn("Enter a valid email address.", invalid_email.text)
        self.assertIn('value="not-an-email"', invalid_email.text)
        self.assertEqual(no_consent.status_code, 422)
        self.assertIn("Please agree to the email use described above.", no_consent.text)
        self.assertIn('value="test@example.com"', no_consent.text)
        self.assertIn('value="ios" checked required', no_consent.text)
        self.assertEqual(invalid_platform.status_code, 422)
        self.assertIn("Choose iOS or Android.", invalid_platform.text)
        self.assertFalse(Path(os.environ["DATABASE_PATH"]).exists())

    def test_admin_dashboard_requires_configured_credentials(self):
        with patch.dict(os.environ, {"BETA_ADMIN_USERNAME": "", "BETA_ADMIN_PASSWORD": ""}):
            unconfigured = self.client.get("/admin/beta")
            submission = self.client.post(
                "/beta",
                data={
                    "email": "test@example.com",
                    "platform": "ios",
                    "consent": "yes",
                },
            )
        unauthorized = self.client.get("/admin/beta")
        wrong_password = "Basic " + base64.b64encode(b"test-admin:wrong").decode()
        denied = self.client.get(
            "/admin/beta", headers={"Authorization": wrong_password}
        )

        self.assertEqual(unconfigured.status_code, 503)
        self.assertEqual(submission.status_code, 503)
        self.assertIn("Beta requests are not available yet.", submission.text)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertIn("Basic realm=", unauthorized.headers["www-authenticate"])
        self.assertEqual(denied.status_code, 401)

    def test_storage_errors_are_reported_without_claiming_success(self):
        with patch.dict(os.environ, {"DATABASE_PATH": self.data_dir.name}):
            with self.assertLogs("main", level="ERROR") as captured:
                response = self.client.post(
                    "/beta",
                    data={
                        "email": "test@example.com",
                        "platform": "android",
                        "consent": "yes",
                    },
                )

        self.assertEqual(response.status_code, 503)
        self.assertIn("We couldn’t save your request right now.", response.text)
        self.assertNotIn("test@example.com", "\n".join(captured.output))

    def test_stylesheet_and_violet_mascot_are_served(self):
        stylesheet = self.client.get("/static/site.css")
        mascot = self.client.get("/assets/mascot/happy.png")

        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("prefers-reduced-motion", stylesheet.text)
        self.assertEqual(mascot.status_code, 200)
        self.assertEqual(mascot.headers["content-type"], "image/png")
        self.assertEqual(
            mascot.content,
            (Path(__file__).parents[1] / "assets/mascot/happy.png").read_bytes(),
        )
