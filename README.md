# Owolot landing page

The public landing page for Owolot, a local-first personal finance app for iOS
and Android. The site uses FastHTML with Starlette/ASGI, Uvicorn, server-rendered
HTML, and custom CSS. Brand artwork is served from `assets/`.

## Local development

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --extra test
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. Run the tests with:

```sh
uv run pytest
```

## Deployment

Deploy the included `Dockerfile` to Railway. The app binds to `0.0.0.0` and
uses the `PORT` environment variable supplied by the platform (defaulting to
`8000` locally). Set the following variables in the deployment environment:

| Variable | Purpose | Secret? |
| --- | --- | --- |
| `PORT` | HTTP port supplied by the host; defaults to `8000`. | No |
| `DATABASE_PATH` | SQLite file path; defaults to `data/beta_requests.sqlite3`. | No |
| `BETA_ADMIN_USERNAME` | Username for `/admin/beta`. | No |
| `BETA_ADMIN_PASSWORD` | Strong password for `/admin/beta`; there is no default. | **Yes** |

Attach persistent storage to the service and set `DATABASE_PATH` to a file
inside its mount (for example, `/data/beta_requests.sqlite3`). Without a
persistent volume, request data can be lost when a deployment is replaced.
Set a unique, strong dashboard password in Railway's secret environment
settings. The dashboard uses HTTP Basic authentication and must only be used
over HTTPS; Railway's public HTTPS endpoint provides transport encryption.

## Content and launch checklist

- The page describes product behavior based on the current product brief; update
  `main.py` when verified app behavior changes.
- `/beta` accepts an email address and iOS/Android selection after explicit
  consent. Requests are stored in SQLite; `/admin/beta` lists the latest 500
  requests for a manually authenticated admin. It does not send email or grant
  store access automatically. Both admin credential variables must be set
  before a beta request can be accepted; otherwise the form shows that requests
  are unavailable.
- Decide and document a retention/deletion schedule for beta request emails
  before launch. The admin page is read-only and does not delete requests;
  until a deletion workflow is added, an operator must manage retention in the
  SQLite database directly.
- Configure and verify the iOS TestFlight and Android Google Play testing
  tracks before sending installation instructions. No invite links are
  published on the site.
- To create an iOS invite: in App Store Connect, open the app's TestFlight
  page, add a tester group and build for external testing, then enable a public
  link for that group after completing Apple's required review steps. You can
  also invite testers by email. Send the resulting invite to approved
  applicants yourself.
- To create an Android invite: in Google Play Console, configure a closed or
  internal testing track, add the tester email/group or enable its opt-in
  link, and publish the test release. Send approved applicants the appropriate
  opt-in and Play installation instructions yourself.
- No production domain is confirmed, so the page intentionally has no canonical
  URL.
- A publisher-approved privacy policy, support contact, publisher identity, and
  any legal terms have not been provided. The page labels its privacy section
  as an overview and does not invent those destinations or details.
- `PRODUCT_NAME` in `main.py` is the single source for the displayed product
  name.
