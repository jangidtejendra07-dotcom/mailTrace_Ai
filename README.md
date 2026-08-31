# MailTrace AI

**SIH 26106 — Email Threat Detection, Geolocation & Forensic Intelligence**

An AI-assisted security and forensic layer with **user accounts** and a
**live Gmail inbox connection** — sign in, connect your Gmail, and every
message gets run through content/intent analysis, email-header forensics,
attachment risk scanning, URL/domain intelligence, IP geolocation, explainable
risk fusion, automated response (ALLOW / QUARANTINE / BLOCK), and forensic
case + evidence generation. Manual `.eml` upload is still available as a
fallback/demo path.

---

## What's new in this version

| Area | Before | Now |
|------|--------|-----|
| Access | Open, no accounts | Full user auth (JWT), register/login |
| Email source | Manual `.eml` upload only | **Live Gmail inbox connection** (OAuth2) + manual upload |
| Data | Shared, unscoped | Every case is scoped to the signed-in user |
| Frontend | Single dashboard | Login/Register + Inbox + Upload + Case Vault, all auth-gated |

---

## Architecture

```
                    ┌─────────────────┐
   Browser  ───────▶│  React frontend │
                    └───────┬─────────┘
                            │ JWT Bearer token
                            ▼
                    ┌─────────────────┐
                    │  FastAPI backend │
                    └───────┬─────────┘
              ┌─────────────┼─────────────────┐
              ▼             ▼                 ▼
        /api/v1/auth   /api/v1/gmail   /api/v1/analyze-email
        register/login  connect/sync    (manual .eml upload)
              │             │                 │
              │             ▼                 │
              │     Gmail API (OAuth2)        │
              │     fetch raw RFC822 msg      │
              │             │                 │
              └─────────────┴─────────────────┘
                            ▼
                    Core Detection Pipeline
                            │
      ┌─────────────────────┼───────────────────────┐
      ▼          ▼           ▼                       ▼
     AI      FORENSICS   ATTACHMENT           URL/Domain Intel
     NLP     SPF/DKIM/    Scanner              + IP Geolocation
             DMARC/Relay
      └─────────────────────┼───────────────────────┘
                            ▼
                      RISK FUSION
                            ▼
              ALLOW / QUARANTINE / BLOCK
                            │
                            ▼
          CASE (user-scoped, SHA-256 evidence) → PDF REPORT
```

## Stack

| Layer      | Tech |
|------------|------|
| Frontend   | React + Vite + Tailwind CSS, Leaflet map |
| Backend    | Python + FastAPI |
| Auth       | JWT (PyJWT) + bcrypt password hashing |
| Gmail      | Google OAuth2 (`google-auth-oauthlib`) + Gmail REST API |
| Database   | SQLite by default (zero setup) — swap to PostgreSQL via `DATABASE_URL` |
| AI/ML      | scikit-learn (TF-IDF + Logistic Regression) |
| Email      | Python `email`/MIME stdlib parsing |
| Evidence   | SHA-256 |
| Reports    | ReportLab (PDF) |
| Deploy     | Docker + docker-compose |

## Project layout

```
mailtrace-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI entrypoint (auth + gmail + analyze + cases routers)
│   │   ├── config.py                Env-driven settings (JWT secret, Google OAuth, etc.)
│   │   ├── pipeline.py              Core detection pipeline orchestration
│   │   ├── models.py                User, GmailAccount, Case (user-scoped)
│   │   ├── schemas.py               Pydantic request/response schemas
│   │   ├── auth/
│   │   │   ├── security.py          Password hashing + JWT create/decode
│   │   │   └── dependencies.py      get_current_user (+ query-token variant for PDF links)
│   │   ├── routers/
│   │   │   ├── auth.py              /api/v1/auth/register, /login, /me
│   │   │   ├── gmail.py             /api/v1/gmail/connect, /callback, /status, /sync, /disconnect
│   │   │   ├── analyze.py           POST /api/v1/analyze-email (auth required)
│   │   │   └── cases.py             GET cases list/detail, PDF report (auth required)
│   │   ├── services/
│   │   │   ├── ai_engine.py            AI/NLP intent engine
│   │   │   ├── forensics.py            Header forensics (SPF/DKIM/DMARC)
│   │   │   ├── attachment_scanner.py   Attachment risk scanning
│   │   │   ├── url_intel.py            URL/domain intelligence
│   │   │   ├── ip_geolocation.py       IP/geo intelligence
│   │   │   ├── risk_fusion.py          Weighted risk fusion + policy
│   │   │   ├── case_manager.py         Correlation graph + SHA-256 evidence
│   │   │   ├── report_generator.py     PDF report package
│   │   │   └── gmail_service.py        Gmail OAuth2 + message fetching
│   │   ├── ml/                      Training data + classifier + model.joblib
│   │   └── utils/email_parser.py    .eml / raw RFC822 → structured dict
│   ├── tests/test_pipeline.py      Automated MVP acceptance tests
│   ├── .env.example                Copy to .env and fill in
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── context/AuthContext.jsx     Login/register/logout + token persistence
│       ├── pages/
│       │   ├── LoginPage.jsx / RegisterPage.jsx   Auth screens
│       │   ├── InboxPage.jsx                       Connect Gmail + live sync
│       │   ├── UploadPage.jsx                      Manual .eml upload (fallback)
│       │   ├── CasesPage.jsx / CaseDetailPage.jsx  Case vault
│       └── components/                             Shared UI (risk gauge, panels, map...)
├── samples/eml/                    Sample .eml files for the 5 MVP acceptance tests
└── docker-compose.yml
```

---

## Quick start (VS Code, no Docker)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy the env template and fill in JWT_SECRET (Gmail vars optional at first)
cp .env.example .env             # Windows: copy .env.example .env

# Train the classifier (already included as model.joblib, but re-run any
# time you edit app/ml/dataset.py)
python -m app.ml.train_model

# Run the API
uvicorn app.main:app --reload --port 8000
```

Backend is now live at **http://localhost:8000** (interactive docs at `/docs`).

> ⚠️ If you're upgrading from the pre-auth version of this project, **delete
> the old `mailtrace.db`** before starting the server — the schema changed
> (new `users`, `gmail_accounts` tables, and `user_id` on `cases`).

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend is now live at **http://localhost:5173**.

### 3. Try it — sign up and analyze

Open http://localhost:5173, create an account, then either:
- **Manual Upload** tab → drop any file from `samples/eml/`, or
- **Live Gmail Inbox** tab → connect your Gmail (see setup below) and click "Sync Gmail"

---

## Gmail OAuth setup (required only for the live-inbox feature)

Manual upload works with zero configuration. To enable **Connect Gmail**:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. **APIs & Services → Library** → search for and enable the **Gmail API**.
3. **APIs & Services → OAuth consent screen** → configure it (choose "External" for testing, and add your own Gmail address under "Test users" so you can actually log in during development).
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Under **Authorized redirect URIs**, add exactly:
     ```
     http://localhost:8000/api/v1/gmail/callback
     ```
5. Copy the generated **Client ID** and **Client Secret**.
6. In `backend/.env`, set:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/gmail/callback
   FRONTEND_URL=http://localhost:5173
   ```
7. Restart the backend. Go to **Live Gmail Inbox → Connect Gmail** — you'll be sent to Google's consent screen, then redirected back automatically.
8. Click **Sync Gmail** to pull and analyze your most recent inbox messages.

MailTrace only requests **read-only** Gmail access (`gmail.readonly`) — it can never send, delete, or modify your mail.

---

## Quick start (Docker)

```bash
# Make sure backend/.env exists first (see Gmail setup above, or leave
# GOOGLE_CLIENT_ID/SECRET blank to skip Gmail and use manual upload only)
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/docs

To use PostgreSQL instead of SQLite, uncomment the `db` service and the
`DATABASE_URL` line in `docker-compose.yml`.

---

## Running the acceptance tests

The 5 MVP Acceptance Tests from the spec are automated in
`backend/tests/test_pipeline.py` and call the detection pipeline directly
(no auth needed to run these — they test the core engine):

```bash
cd backend
pytest -v
```

1. Safe email → low score → **DELIVER (ALLOW)**
2. Phishing URL + suspicious language → high score → **QUARANTINE**
3. `invoice.pdf.exe` → attachment CRITICAL → **BLOCK**
4. BEC / executive impersonation → AI + header anomaly → **QUARANTINE/BLOCK**
5. Blocked message → case + indicators + SHA-256 + report generated

---

## API contract

### Auth
```
POST /api/v1/auth/register   { email, password, full_name? }  -> { access_token, user }
POST /api/v1/auth/login      { email, password }               -> { access_token, user }
GET  /api/v1/auth/me         (Authorization: Bearer <token>)    -> user
```

### Gmail
```
GET  /api/v1/gmail/status       -> { connected, gmail_address?, last_synced_at? }
GET  /api/v1/gmail/connect      -> { authorization_url }   (frontend redirects browser here)
GET  /api/v1/gmail/callback     (Google redirects here after consent — not called by frontend directly)
POST /api/v1/gmail/sync         -> { fetched, new_cases, skipped_existing, cases }
POST /api/v1/gmail/disconnect   -> { disconnected: true }
```

### Analysis & cases (all require `Authorization: Bearer <token>`)
```
POST /api/v1/analyze-email      multipart file upload -> full analysis result
GET  /api/v1/cases              -> list of the current user's cases
GET  /api/v1/cases/{case_id}    -> full case detail
GET  /api/v1/cases/{case_id}/report   -> PDF (also accepts ?token=<jwt> for <a href> downloads)
```

Example analysis result shape:
```json
{
  "classification": "phishing",
  "risk_score": 94,
  "decision": "BLOCK",
  "ai": { "score": 86, "category": "bec", "reasons": [...] },
  "authentication": { "spf": "fail", "dkim": "pass", "dmarc": "fail" },
  "sender": {...},
  "urls": [...],
  "attachments": [...],
  "ip_intelligence": {...},
  "geolocation": {...},
  "correlation_graph": { "nodes": [...], "edges": [...] },
  "case_id": "MT-2026-XXXXXXXX",
  "evidence_hash": "<sha256>",
  "explanation": [...]
}
```

---

## Notes on scope & honesty

- **Gmail integration**: this connects to a real Gmail inbox via OAuth2 and
  analyzes real messages via `users.messages.get(format=raw)`. It currently
  works as **on-demand polling** ("Sync Gmail" button). True *pre-delivery*
  blocking before a message lands in the inbox requires a mail-routing /
  security-gateway deployment (e.g. a Google Workspace add-on with a
  pre-delivery hook) — not something a read-only OAuth API scope can do.
  Near-real-time push sync via Gmail's `users.watch` + Cloud Pub/Sub is a
  natural next step, but needs a publicly reachable HTTPS webhook, which is
  why it's documented here as an extension point rather than built in.
- **Read-only access**: MailTrace only requests `gmail.readonly` — it cannot
  send, delete, label, or modify mail in the connected account.
- **Geolocation** returns a *probable network origin* (country/city/ASN/ISP +
  confidence), never an exact physical attacker location.
- **Cybercrime reporting** generates a ready-to-review report package (PDF +
  evidence hash) for a human analyst to submit via the National Cyber Crime
  Reporting Portal's "Report Suspect" facility — it does not auto-file
  complaints.
- **Auth security note**: this MVP uses a simple JWT scheme suitable for a
  hackathon demo. For a production deployment, add refresh-token rotation,
  rate-limiting on `/auth/login`, and email verification before go-live.

## Extending this for the final round

- Swap the hand-crafted `app/ml/dataset.py` samples for a real corpus (Enron +
  Nazario phishing corpus, or your own labeled data) and retrain.
- Add Gmail push notifications (`users.watch` + Cloud Pub/Sub) for near-real-time
  sync instead of manual "Sync Gmail" clicks.
- Wire `PostgreSQL` in via `docker-compose.yml` and add Alembic migrations.
- Add Neo4j for the correlation graph instead of the in-memory node/edge
  structure, to support cross-case campaign detection at scale.
- Integrate a real threat-intel feed (VirusTotal, AbuseIPDB, URLhaus) into
  `url_intel.py` and `ip_geolocation.py` for production-grade reputation data.
- Add role-based access (admin vs analyst) and an audit log for case actions.
