# MailTrace AI — Setup Guide (things you have to do yourself)

This covers everything that needs **your own accounts/credentials**, which I
can't do on your behalf. Follow these in order — each section says exactly
what to click and where to paste the result.

Total time: ~45–60 minutes the first time. Free the whole way through.

---

## 0. Install & run locally (do this first, sanity check)

```bash
# Backend
cd mailtrace-ai/backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # you'll fill this in as you go below
uvicorn app.main:app --reload

# Frontend (new terminal)
cd mailtrace-ai/frontend
npm install
npm run dev
```

Open http://localhost:5173 — register an account, try **Manual Upload**
with a sample `.eml` from `mailtrace-ai/samples/eml`. If this works, the
base project (as your friend built it) is healthy before you add anything else.

---

## 1. Get free AI API keys (5 minutes)

**Groq (primary — fastest):**
1. Go to https://console.groq.com → sign in with Google/GitHub (no card needed)
2. Left sidebar → **API Keys** → **Create API Key** → copy it
3. Paste into `backend/.env` → `GROQ_API_KEY=gsk_...`

**Gemini (fallback):**
1. Go to https://aistudio.google.com/apikey → sign in
2. **Create API key** → copy it
3. Paste into `backend/.env` → `GEMINI_API_KEY=AIza...`

Restart the backend (`Ctrl+C`, then `uvicorn app.main:app --reload` again).
Test it: upload any `.eml` file — the returned case JSON will now have
`"engine_used": "groq"` (or `"gemini"` / `"local-sklearn"` if both keys are
missing/rate-limited — it never fails outright).

---

## 2. Connect your real Gmail account (10 minutes)

You need a Google Cloud OAuth client (separate from the Pub/Sub project
below, but you can reuse the same Google Cloud project for both).

1. Go to https://console.cloud.google.com → create a project (or pick your
   existing one, since you said Cloud Console is already set up)
2. **APIs & Services → Library** → search "Gmail API" → **Enable**
3. **APIs & Services → OAuth consent screen** → External → fill app name
   "MailTrace AI", your email → **Save**. On the Scopes step, you don't need
   to add scopes manually here (the app requests them at runtime) — just
   save through to the end.
   - Because the app now requests `gmail.modify` (a "sensitive" scope, needed
     for auto-quarantine), Google will show an "unverified app" warning
     during login for hackathon demo purposes. Click **Advanced → Go to
     MailTrace AI (unsafe)** to proceed — this is completely normal for
     apps in testing mode and fine for a hackathon demo. Add your own Gmail
     address under **Test users** so you're allowed to log in.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   → Application type: **Web application**
   → Authorized redirect URI: `http://localhost:8000/api/v1/gmail/callback`
   (add your deployed backend's `/api/v1/gmail/callback` URL too, later,
   once you've deployed — step 5)
5. Copy the **Client ID** and **Client Secret** into `backend/.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```
6. Restart the backend, go to **Live Gmail Inbox** on the site, click
   **Connect Gmail**, approve access, then click **Sync Gmail**.

If this step works, manual sync is fully live. Real-time (next section) is
an upgrade on top of this — don't skip ahead if this part isn't working yet.

---

## 3. Turn on real-time detection (Cloud Pub/Sub) (15–20 minutes)

This is the part that makes detection run **automatically**, without
clicking Sync. It needs your backend to be reachable from the internet
(Google's servers push notifications to it), so do this AFTER step 5
(deployment) if you don't want to mess with ngrok.

### 3a. Create the Pub/Sub topic
```bash
gcloud pubsub topics create mailtrace-gmail-notifications
```
(Or via Console: **Pub/Sub → Topics → Create Topic**, ID:
`mailtrace-gmail-notifications`.)

### 3b. Let Gmail publish to your topic
Gmail's push service publishes as a special Google system account. Grant it
permission:
```bash
gcloud pubsub topics add-iam-policy-binding mailtrace-gmail-notifications \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
```

### 3c. Create a push subscription pointing at your backend
First, choose a random secret token (this stops random internet traffic
from hitting your webhook):
```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
```
Put that value in `backend/.env` as `PUBSUB_VERIFICATION_TOKEN=...`, then:
```bash
gcloud pubsub subscriptions create mailtrace-gmail-sub \
  --topic=mailtrace-gmail-notifications \
  --push-endpoint="https://YOUR-DEPLOYED-BACKEND-URL/api/v1/gmail/webhook?token=YOUR_SECRET_TOKEN" \
  --ack-deadline=30
```
(Replace `YOUR-DEPLOYED-BACKEND-URL` and `YOUR_SECRET_TOKEN` — no
`localhost` here, Google's servers need a public URL. See step 5.)

### 3d. Fill in the rest of `backend/.env`
```
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
PUBSUB_TOPIC=mailtrace-gmail-notifications
```

### 3e. Turn it on
On the **Live Gmail Inbox** page, click **Turn on real-time**. Behind the
scenes this calls `POST /api/v1/gmail/watch/start`. Send yourself a test
email from another account — it should appear in **Case Vault** within a
few seconds, no Sync click needed.

Watches expire after 7 days; the backend auto-renews them every 6 hours via
`app/scheduler.py` as long as the app keeps running — so keep your
deployment "always on" (see hosting notes in step 5), not something you
start manually each time.

---

## 4. Auto-quarantine — nothing extra to configure

This piggybacks on what you just set up. Any mail scoring
`>= QUARANTINE_RISK_THRESHOLD` (default `70`, edit in `.env`) and decided
`QUARANTINE`/`BLOCK` gets automatically labeled `MailTrace/Quarantined` and
removed from `INBOX` in Gmail. Check the **Quarantined** page on the website
to review and **Release to inbox** if it's a false positive. Nothing is
ever deleted.

---

## 5. Deploy the backend publicly (needed for real-time + the Add-on)

Any of these work and have a free tier — pick one:

**Render (easiest):**
1. Push your project to a GitHub repo
2. https://render.com → New → Web Service → connect the repo,
   root directory `backend`
3. Build command: `pip install -r requirements.txt`
   Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all your `.env` values under **Environment** in Render's dashboard
   (don't commit `.env` to GitHub — it's already gitignored)
5. Once live, copy the `https://xxxx.onrender.com` URL and:
   - Add `https://xxxx.onrender.com/api/v1/gmail/callback` as an
     Authorized redirect URI in Google Cloud Credentials (step 2.4)
   - Use `https://xxxx.onrender.com/api/v1/gmail/webhook?token=...` as the
     Pub/Sub push endpoint (step 3c)
   - Set `FRONTEND_URL` in Render's env vars to your deployed frontend URL

**Quick demo alternative (no deployment, just for a live demo):**
```bash
ngrok http 8000
```
Use the `https://xxxx.ngrok-free.app` URL the same way as above. Good for a
5-minute SIH demo; the URL changes every restart, so redo steps 2.4/3c if
you restart ngrok.

**Frontend:** deploy `frontend/` to Vercel or Netlify (`npm run build`,
serve the `dist` folder) — point it at your deployed backend URL via the
frontend's API base config.

---

## 6. Set up the Gmail Add-on (chhota UI inside Gmail)

1. Go to https://script.google.com → **New project**
2. Rename it "MailTrace AI Add-on" (top left)
3. Delete the default `Code.gs` content, paste in
   `gmail-addon/Code.gs` from this project
4. Click the gear icon (Project Settings) → check **"Show appsscript.json
   manifest file in editor"**
5. Open `appsscript.json` in the editor, replace its contents with
   `gmail-addon/appsscript.json` from this project, but replace
   `YOUR-BACKEND-URL.example.com` (both places) with your real deployed
   backend URL from step 5
6. **Deploy → Test deployments → Install add-on** (this installs it only
   for your own Google account — perfect for a hackathon demo, no
   Google Workspace Marketplace review needed)
7. Open Gmail (refresh the tab) → look for the MailTrace icon in the
   right-hand vertical rail → click it → paste your backend URL again here
   in the Settings card

### Getting your access token for the Add-on
The Add-on needs your MailTrace login token (not your Google password):
1. Log into the MailTrace website normally
2. Open browser DevTools (F12) → **Application/Storage** tab → **Local
   Storage** → find the key holding your JWT (however `AuthContext.jsx`
   stores it) → copy the value
3. Paste that into the Add-on's Settings card as the "Access token"

Tokens expire after 24 hours by default (`ACCESS_TOKEN_EXPIRE_MINUTES` in
`.env`) — for a demo day, temporarily bump this to something like `10080`
(7 days) so you don't have to re-paste it mid-demo.

8. Now open any email in Gmail → the MailTrace sidebar shows the risk score
   for that message (if it's already been analyzed — real-time detection
   from step 3 needs to be on for this to populate automatically).

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Real-time detection isn't configured yet" | `GOOGLE_CLOUD_PROJECT` blank in `.env` |
| Webhook never fires | Push endpoint URL/token mismatch, or backend isn't publicly reachable (localhost won't work) |
| `engine_used: "local-sklearn"` always | Groq/Gemini keys blank, invalid, or rate-limited (both free tiers cap at 1,000 req/day) |
| Add-on shows "Not analyzed yet" forever | Real-time watch isn't on, or the message arrived before you turned it on — click Sync once to backfill |
| Google login shows "unverified app" | Expected in testing mode — click Advanced → proceed, and make sure your email is under Test users (step 2.3) |
| Gmail watch stops working after ~7 days | Scheduler only renews while the backend process is alive — make sure your deployment doesn't sleep/spin down (Render's free tier spins down after inactivity; a paid "always on" tier or a cron ping keeps it alive) |
