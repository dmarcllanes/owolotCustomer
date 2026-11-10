import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib import error as urllib_error

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
                "SUPABASE_URL": "",
                "SUPABASE_SERVICE_ROLE_KEY": "",
                "MONGODB_URI": "",
                "MONGODB_DATABASE": "",
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

    def test_supabase_storage_is_used_when_explicitly_configured(self):
        captured_requests = []

        class FakeHttpResponse:
            def __init__(self, status: int, body: bytes = b""):
                self.status = status
                self._body = body

            def read(self) -> bytes:
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req, timeout=5):
            captured_requests.append((req, timeout))
            if req.get_method() == "POST":
                return FakeHttpResponse(201)
            payload = json.dumps(
                [
                    {
                        "email": "supabase@example.com",
                        "platform": "android",
                        "requested_at": "2026-11-10T00:00:00+00:00",
                    }
                ]
            ).encode("utf-8")
            return FakeHttpResponse(200, payload)

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
            },
        ), patch("main.urllib_request.urlopen", side_effect=fake_urlopen):
            submit = self.client.post(
                "/beta",
                data={"email": "Supabase@Example.com", "platform": "android", "consent": "yes"},
            )
            authorization = "Basic " + base64.b64encode(b"test-admin:test-password").decode()
            dashboard = self.client.get(
                "/admin/beta", headers={"Authorization": authorization}
            )

        self.assertEqual(submit.status_code, 201)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("supabase@example.com", dashboard.text)
        self.assertIn("<td>Android</td>", dashboard.text)
        self.assertFalse(Path(os.environ["DATABASE_PATH"]).exists())
        self.assertEqual(len(captured_requests), 2)
        post_req, _ = captured_requests[0]
        self.assertEqual(post_req.full_url, "https://example.supabase.co/rest/v1/beta_requests")
        self.assertEqual(json.loads(post_req.data.decode("utf-8"))["email"], "supabase@example.com")

    def test_partial_or_failing_supabase_configuration_fails_visibly(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "",
            },
        ):
            with self.assertLogs("main", level="ERROR") as partial_logs:
                partial = self.client.post(
                    "/beta",
                    data={"email": "user@example.com", "platform": "ios", "consent": "yes"},
                )

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "secret-service-key",
            },
        ), patch(
            "main.urllib_request.urlopen",
            side_effect=urllib_error.URLError("connection refused"),
        ):
            with self.assertLogs("main", level="ERROR") as error_logs:
                failed = self.client.post(
                    "/beta",
                    data={"email": "user@example.com", "platform": "ios", "consent": "yes"},
                )

        self.assertEqual(partial.status_code, 503)
        self.assertEqual(failed.status_code, 503)
        self.assertIn("We couldn’t save your request right now.", failed.text)
        combined_logs = "\n".join(partial_logs.output + error_logs.output)
        self.assertNotIn("user@example.com", combined_logs)
        self.assertNotIn("secret-service-key", combined_logs)

    def test_mongodb_storage_is_used_when_explicitly_configured(self):
        stored_docs = []

        class FakeCursor(list):
            def sort(self, key, direction):
                return self

            def limit(self, count):
                return self

        class FakeCollection:
            def insert_one(self, doc):
                stored_docs.append(dict(doc))

            def find(self, filt, projection):
                return FakeCursor(stored_docs)

        class FakeClient:
            def __init__(self):
                self.db_names = []

            def __getitem__(self, db_name):
                self.db_names.append(db_name)
                return {"beta_requests": FakeCollection()}

            def close(self):
                pass

        fake_client = FakeClient()

        with patch.dict(
            os.environ,
            {
                "MONGODB_URI": "mongodb+srv://user:secret@cluster.example.mongodb.net/",
                "MONGODB_DATABASE": "owolot_customer",
            },
        ), patch("main.open_mongodb_client", return_value=fake_client):
            submit = self.client.post(
                "/beta",
                data={"email": "Mongo@Example.com", "platform": "ios", "consent": "yes"},
            )
            authorization = "Basic " + base64.b64encode(b"test-admin:test-password").decode()
            dashboard = self.client.get(
                "/admin/beta", headers={"Authorization": authorization}
            )

        self.assertEqual(submit.status_code, 201)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("mongo@example.com", dashboard.text)
        self.assertIn("<td>iOS</td>", dashboard.text)
        self.assertEqual(fake_client.db_names, ["owolot_customer", "owolot_customer"])
        self.assertFalse(Path(os.environ["DATABASE_PATH"]).exists())

    def test_admin_login_endpoint_authenticates_and_redirects_to_dashboard(self):
        login_page = self.client.get("/admin/login")
        self.assertEqual(login_page.status_code, 200)
        self.assertIn('action="/admin/login"', login_page.text)
        self.assertNotIn("www-authenticate", login_page.headers)

        bad_login = self.client.post(
            "/admin/login",
            data={"username": "test-admin", "password": "wrong-password"},
        )
        self.assertEqual(bad_login.status_code, 401)
        self.assertIn("Invalid username or password.", bad_login.text)

        good_login = self.client.post(
            "/admin/login",
            data={"username": "test-admin", "password": "test-password"},
            follow_redirects=True,
        )
        self.assertEqual(good_login.status_code, 200)
        self.assertIn("<h1>Beta access requests</h1>", good_login.text)
        self.assertIn('action="/admin/logout"', good_login.text)



