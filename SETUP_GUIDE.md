# NY Court Case Tracker — Complete Setup & Run Guide

This guide walks you through cloning, configuring, and running the NY Court Case Tracker app from scratch on your local machine.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Backend Setup](#3-backend-setup)
4. [Frontend / Mobile Setup](#4-frontend--mobile-setup)
5. [Environment Variables Reference](#5-environment-variables-reference)
6. [Email Integration Setup (Mailgun)](#6-email-integration-setup-mailgun)
7. [Deployment to Production](#7-deployment-to-production)
8. [Building a Mobile APK / IPA](#8-building-a-mobile-apk--ipa)
9. [Testing Checklist](#9-testing-checklist)
10. [Troubleshooting](#10-troubleshooting)
11. [Architecture Overview](#11-architecture-overview)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.12+ | Backend runtime |
| **Poetry** | 1.7+ | Python dependency management |
| **Node.js** | 18+ (LTS recommended) | Frontend runtime |
| **npm** | 9+ | Node package manager (comes with Node.js) |
| **Git** | 2.x | Version control |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Expo CLI** | Latest | `npx expo` (no global install needed) |
| **Expo Go** (mobile) | Latest | Test on physical iOS/Android device |
| **Android Studio** | Latest | Android emulator |
| **Xcode** (macOS only) | Latest | iOS simulator |
| **Fly.io CLI** (`flyctl`) | Latest | Backend deployment |

### OS Compatibility

- **macOS**: Full support (backend + frontend + iOS simulator + Android emulator)
- **Linux**: Full support (backend + frontend + Android emulator)
- **Windows**: Full support via WSL2 recommended; native Windows works for backend + web frontend

### Install Prerequisites

**macOS (Homebrew):**
```bash
brew install python@3.12 node git
pip install poetry
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv nodejs npm git
pip install poetry
```

**Windows (via winget or manual):**
```powershell
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
winget install Git.Git
pip install poetry
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/mrk2811/casetracker.git
cd casetracker
```

The default branch is `devin/1775342725-initial-codebase`.

### Repository Structure

```
casetracker/
├── ny-court-tracker-backend/     # FastAPI Python backend
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── database.py           # SQLite database setup & migrations
│   │   ├── routers/              # API route handlers
│   │   │   ├── auth.py           # Registration, login, JWT auth
│   │   │   ├── cases.py          # Case CRUD, search, verify
│   │   │   ├── appearances.py    # Court appearance management
│   │   │   ├── dashboard.py      # Dashboard aggregation
│   │   │   ├── notifications.py  # Notification settings & delivery
│   │   │   ├── email_integration.py  # Email forwarding setup
│   │   │   ├── discovery.py      # Weekly case discovery
│   │   │   └── scraper.py        # Web scraper control
│   │   ├── email/                # Email parsing & webhook
│   │   │   ├── parser.py         # Court notification email parser
│   │   │   └── webhook.py        # Mailgun inbound webhook handler
│   │   ├── scraper/              # Court website scraping engine
│   │   ├── notifications/        # Notification generation engine
│   │   ├── discovery/            # Weekly case detection engine
│   │   ├── adapters/             # Court system adapters (NY WebCivil, WebCrimin)
│   │   └── schemas/              # Pydantic request/response models
│   ├── pyproject.toml            # Python dependencies (Poetry)
│   └── tests/                    # Backend tests
│
├── ny-court-tracker-mobile/      # React Native (Expo) frontend
│   ├── App.tsx                   # App entry point
│   ├── src/
│   │   ├── navigation/
│   │   │   └── AppNavigator.tsx  # Tab navigation & auth flow
│   │   ├── screens/              # All app screens
│   │   │   ├── DashboardScreen.tsx
│   │   │   ├── CasesScreen.tsx
│   │   │   ├── CaseDetailScreen.tsx
│   │   │   ├── CalendarScreen.tsx
│   │   │   ├── NotificationsScreen.tsx
│   │   │   ├── SettingsScreen.tsx
│   │   │   ├── DiscoveriesScreen.tsx
│   │   │   ├── SignInScreen.tsx
│   │   │   └── SignUpScreen.tsx
│   │   ├── services/
│   │   │   ├── api.ts            # API client & all endpoint calls
│   │   │   └── storage.ts        # Async storage wrapper
│   │   └── context/
│   │       └── AuthContext.tsx    # Authentication state management
│   ├── package.json              # Node dependencies
│   └── app.json                  # Expo configuration
│
├── CODEBASE_DOCUMENTATION.md     # Detailed code documentation
├── v2-architecture-plan.md       # Architecture design document
└── README.md
```

---

## 3. Backend Setup

### Step 1: Navigate to the backend directory

```bash
cd ny-court-tracker-backend
```

### Step 2: Install Python dependencies

```bash
poetry install
```

This installs all dependencies from `pyproject.toml`:
- `fastapi` — Web framework with auto-generated API docs
- `pyjwt` — JWT authentication tokens
- `bcrypt` — Password hashing
- `python-dotenv` — Environment variable loading
- `pydantic[email]` — Request/response validation
- `apscheduler` — Background job scheduling (scraper, notifications)
- `httpx` — Async HTTP client (for scraping)
- `beautifulsoup4` + `lxml` — HTML parsing (for scraping)
- `aiosmtplib` — Async email sending

### Step 3: Configure environment variables

Create a `.env` file in the `ny-court-tracker-backend/` directory:

```bash
# .env
SECRET_KEY=your-secret-key-here-change-in-production
INBOUND_EMAIL_DOMAIN=sandboxXXXXXX.mailgun.org
DB_DIR=/data
```

For local development, you can simplify:

```bash
# .env (local development)
SECRET_KEY=dev-secret-key-12345
INBOUND_EMAIL_DOMAIN=localhost
```

> **Note:** If `DB_DIR` is not set or the directory doesn't exist, the database file will be created in the `app/` directory automatically as a fallback.

### Step 4: Run the backend server

```bash
poetry run fastapi dev app/main.py
```

This starts the development server at **http://localhost:8000** with auto-reload enabled.

The database is automatically initialized on first startup (tables created, indexes built, default court configurations seeded). No manual migration step is needed.

### Step 5: Verify the backend is running

```bash
# Health check
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}

# Interactive API docs
open http://localhost:8000/docs
```

The FastAPI auto-generated docs at `/docs` show all available endpoints with try-it-out functionality.

---

## 4. Frontend / Mobile Setup

### Step 1: Navigate to the mobile directory

```bash
cd ny-court-tracker-mobile
```

### Step 2: Install Node.js dependencies

```bash
npm install
```

### Step 3: Configure the API URL

Edit `src/services/api.ts` and update the `API_URL` constant:

```typescript
// For local development (backend running on localhost)
const API_URL = "http://localhost:8000";

// For Android emulator (maps to host machine's localhost)
// const API_URL = "http://10.0.2.2:8000";

// For physical device on same WiFi (replace with your machine's IP)
// const API_URL = "http://192.168.x.x:8000";

// For production (deployed backend)
// const API_URL = "https://app-ujjdvsxl.fly.dev";
```

### Step 4: Run the app

**For Web (browser):**
```bash
npx expo start --web
```
Opens at **http://localhost:8081** in your default browser.

**For iOS Simulator (macOS only):**
```bash
npx expo start --ios
```
Requires Xcode installed with iOS simulator.

**For Android Emulator:**
```bash
npx expo start --android
```
Requires Android Studio with an emulator configured.

**For Physical Device (Expo Go):**
```bash
npx expo start
```
Scan the QR code with Expo Go app on your phone. Your phone and computer must be on the same WiFi network.

### Step 5: Build for web deployment

```bash
npx expo export --platform web
```
This creates a `dist/` folder with static files ready for deployment.

---

## 5. Environment Variables Reference

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | None | JWT signing key. Use a long random string in production. |
| `INBOUND_EMAIL_DOMAIN` | No | `courttracker.app` | Domain for user forwarding emails (e.g., Mailgun sandbox domain) |
| `DB_DIR` | No | `/data` | Directory for SQLite database file. Falls back to `app/` directory if not found. |
| `MAILGUN_API_KEY` | No | None | Mailgun API key (for sending emails, optional) |
| `MAILGUN_DOMAIN` | No | None | Mailgun sending domain (optional) |

### Frontend Configuration

| File | Variable | Description |
|------|----------|-------------|
| `src/services/api.ts` | `API_URL` | Backend API base URL. Change this for local dev vs production. |

---

## 6. Email Integration Setup (Mailgun)

The app supports email-based case tracking: court notification emails are forwarded to a unique per-user address, parsed, and case data is automatically updated.

### Step 1: Create a Mailgun account

Sign up at https://www.mailgun.com (free Flex plan works).

### Step 2: Get your sandbox domain

After signing up, Mailgun provides a sandbox domain like:
```
sandboxXXXXXXXXXX.mailgun.org
```
Find it in **Mailgun Dashboard → Sending → Domains**.

### Step 3: Set up an inbound route

Go to **Mailgun Dashboard → Receiving → Create Route**:

- **Expression Type:** Match Recipient
- **Recipient:** `.*@sandboxXXXXXXXXXX.mailgun.org` (catch-all for your sandbox)
- **Actions:** Forward → `https://YOUR_BACKEND_URL/api/email/webhook/mailgun`
  - For local testing with a tunnel: `https://your-ngrok-url/api/email/webhook/mailgun`
  - For production: `https://app-ujjdvsxl.fly.dev/api/email/webhook/mailgun`
- **Priority:** 0

### Step 4: Update backend environment

Set `INBOUND_EMAIL_DOMAIN` in your `.env` file:
```
INBOUND_EMAIL_DOMAIN=sandboxXXXXXXXXXX.mailgun.org
```

### Step 5: Add authorized recipients (sandbox only)

For Mailgun sandbox domains, you must authorize recipient emails:
- Go to **Mailgun Dashboard → Sending → Overview → Authorized Recipients**
- Add the email addresses that will receive forwarded emails

### Step 6: Test the flow

1. Open the app → **Settings → Email Integration → Set Up Email Integration**
2. You'll get a unique forwarding address like `case-abc123@sandboxXXXXXX.mailgun.org`
3. Forward a court notification email to that address
4. Check **Settings → Email Integration → Activity** to see parsed results

### Using a Custom Domain (Production)

For production, register a domain and configure DNS records in Mailgun:
1. Add your domain in Mailgun
2. Set up MX and TXT DNS records as instructed
3. Update `INBOUND_EMAIL_DOMAIN` to your custom domain
4. Gmail forwarding will work without sandbox restrictions

---

## 7. Deployment to Production

### Backend Deployment (Fly.io)

The backend is deployed as a FastAPI app on Fly.io with a persistent volume for SQLite.

**Install Fly.io CLI:**
```bash
curl -L https://fly.io/install.sh | sh
```

**Login:**
```bash
fly auth login
```

**Deploy (from ny-court-tracker-backend/):**
```bash
fly launch
fly volumes create data --size 1
fly deploy
```

**Set environment variables:**
```bash
fly secrets set SECRET_KEY=your-production-secret-key
fly secrets set INBOUND_EMAIL_DOMAIN=your-mailgun-domain.com
```

**View logs:**
```bash
fly logs
```

The current production backend is at: `https://app-ujjdvsxl.fly.dev`

### Frontend Deployment

Build the web export:
```bash
cd ny-court-tracker-mobile
npx expo export --platform web
```

Deploy the `dist/` folder to any static hosting service:
- **Vercel:** `npx vercel dist/`
- **Netlify:** Drag & drop `dist/` folder
- **Cloudflare Pages:** Connect repo or upload `dist/`

The current production frontend is at: `https://case-schedule-app-jgutrt5s.devinapps.com`

> **Important:** Before building for production, update `API_URL` in `src/services/api.ts` to point to your deployed backend URL.

---

## 8. Building a Mobile APK / IPA

### Using EAS Build (Expo Application Services)

**Install EAS CLI:**
```bash
npm install -g eas-cli
```

**Login to Expo:**
```bash
eas login
```

**Configure EAS Build:**
```bash
eas build:configure
```

**Build for Android (APK):**
```bash
eas build --platform android --profile preview
```
This produces an APK you can install directly on Android devices.

**Build for iOS:**
```bash
eas build --platform ios
```
Requires an Apple Developer account ($99/year).

### Local Android Build (without EAS)

If you prefer building locally:
```bash
npx expo prebuild --platform android
cd android
./gradlew assembleRelease
```
The APK will be at `android/app/build/outputs/apk/release/`.

---

## 9. Testing Checklist

After setup, verify these core workflows:

### Authentication
- [ ] Register a new account (tap "Create one" on sign-in screen)
- [ ] Login with the new account
- [ ] Sign out (Settings → Sign Out) — should show confirmation dialog
- [ ] Login again with the same credentials

### Cases & Dashboard
- [ ] Add a new case via the "+" button
- [ ] View the case on the Dashboard
- [ ] View the case in the Cases tab
- [ ] Tap a case to see Case Detail screen
- [ ] Edit case details
- [ ] Delete a case

### Calendar
- [ ] View the Calendar tab
- [ ] Tap on a date with appearances
- [ ] Verify the filtered list updates

### Notifications
- [ ] Check the Notifications tab
- [ ] Go to Settings → toggle notification preferences
- [ ] Verify settings persist after leaving and returning

### Email Integration
- [ ] Settings → Email Integration → Set Up
- [ ] Verify unique forwarding email is generated
- [ ] Forward a test court notification email
- [ ] Check Activity tab shows received email

### Settings
- [ ] Toggle all notification preferences
- [ ] Check discovery settings
- [ ] Sign out and verify redirect to sign-in screen

### Test Credentials (if using seeded data)
- **Email:** `john@example.com`
- **Password:** `Test1234`

---

## 10. Troubleshooting

### CORS Errors

If you see CORS errors in the browser console:
- Ensure the backend has CORS middleware enabled (it does by default in `app/main.py`)
- Check that `allow_origins=["*"]` is set (default configuration)
- If using a proxy, ensure it passes CORS headers through

### Database Issues

**"No such table" errors:**
- The database auto-initializes on startup. Restart the backend server.
- Check that `DB_DIR` points to a writable directory.

**Reset the database:**
```bash
# Delete the database file and restart
rm app/app.db  # or /data/app.db in production
poetry run fastapi dev app/main.py
```

### Expo / React Native Errors

**"Unable to resolve module" errors:**
```bash
# Clear Metro bundler cache
npx expo start --clear
```

**Expo Go can't connect to backend:**
- Ensure your phone and computer are on the same WiFi
- Use your machine's local IP (not `localhost`) in `API_URL`
- Check firewall settings

### Sign Out Not Working on Web

The Sign Out button uses `window.confirm()` on web and `Alert.alert()` on native. If you modify the sign-out logic, make sure to keep the `Platform.OS === "web"` check:

```typescript
if (Platform.OS === "web") {
  if (window.confirm("Are you sure you want to sign out?")) {
    logout();
  }
} else {
  Alert.alert("Sign Out", "Are you sure you want to sign out?", [
    { text: "Cancel", style: "cancel" },
    { text: "Sign Out", style: "destructive", onPress: logout },
  ]);
}
```

### Email Webhook Not Receiving Emails

1. Check that your Mailgun inbound route destination URL is correct:
   - Must end with `/api/email/webhook/mailgun` (not `/sendgrid`)
2. For sandbox domains, verify the sender is in Authorized Recipients
3. Check backend logs for incoming webhook requests
4. For local testing, use a tunnel (ngrok) to expose your local backend

### Port Conflicts

**Backend (port 8000):**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**Frontend (port 8081):**
```bash
# Find and kill process on port 8081
lsof -ti:8081 | xargs kill -9
```

---

## 11. Architecture Overview

### Why React Native with Expo?

- **Cross-platform**: Single codebase for iOS, Android, and Web
- **Expo**: Simplifies build process, provides OTA updates, managed workflow
- **React Native Web**: Same app runs in the browser for easy testing and web access

### Why FastAPI?

- **Async support**: Handles concurrent scraping and webhook processing
- **Auto-generated docs**: Interactive API documentation at `/docs`
- **Pydantic validation**: Type-safe request/response handling
- **Python ecosystem**: Rich libraries for web scraping (BeautifulSoup), email parsing, scheduling

### Why SQLite?

- **Zero configuration**: No separate database server needed
- **Single file**: Easy backup and migration
- **Sufficient for single-tenant**: Handles the expected load for individual users
- **Persistent volume on Fly.io**: Data survives deployments and restarts

### Email Forwarding Architecture

```
Court System (eTrack)
    │
    ▼
User's Gmail/Outlook
    │ (forwarding rule)
    ▼
Mailgun (inbound route)
    │ (HTTP POST)
    ▼
Backend Webhook (/api/email/webhook/mailgun)
    │
    ▼
Email Parser (regex extraction)
    │
    ▼
Database (case events, appearances)
    │
    ▼
Dashboard (updated view)
```

### Data Import Methods

1. **Manual Entry**: User adds cases directly in the app
2. **Search & Verify**: Search NY court systems and import verified cases
3. **Web Scraping**: Automated scraping of court websites (with CAPTCHA detection)
4. **Email Forwarding**: Parse court notification emails for case updates
5. **Weekly Discovery**: Automated scanning for new cases matching user criteria
