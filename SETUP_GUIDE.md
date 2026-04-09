# NY Court Case Tracker - Complete Setup Guide

A comprehensive guide to set up and run the NY Court Case Tracker application from scratch. This app helps attorneys track New York court cases, receive notifications about court dates, and automatically discover new cases.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Cloning the Repository](#2-cloning-the-repository)
3. [Backend Setup](#3-backend-setup)
4. [Frontend / Mobile Setup](#4-frontend--mobile-setup)
5. [Environment Variables Reference](#5-environment-variables-reference)
6. [Email Integration Setup (Mailgun)](#6-email-integration-setup-mailgun)
7. [Running in Production / Deployment](#7-running-in-production--deployment)
8. [Testing](#8-testing)
9. [Troubleshooting](#9-troubleshooting)
10. [Architecture Decisions](#10-architecture-decisions)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.12+ | Backend runtime |
| **Poetry** | 1.7+ | Python dependency management |
| **Node.js** | 18.x or 20.x (LTS) | Frontend runtime |
| **npm** | 9+ (comes with Node.js) | Node package management |
| **Git** | 2.x+ | Version control |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Expo CLI** | Latest (`npx expo`) | Mobile app development (installed via npx) |
| **Xcode** | 15+ | iOS simulator (macOS only) |
| **Android Studio** | Latest | Android emulator |
| **Expo Go** | Latest (App Store / Play Store) | Testing on physical device |
| **Fly.io CLI (`flyctl`)** | Latest | Production backend deployment |
| **EAS CLI** | Latest (`npx eas-cli`) | Mobile app builds for distribution |

### Operating System Compatibility

| OS | Backend | Frontend (Web) | Frontend (iOS Sim) | Frontend (Android Emu) |
|----|---------|---------------|--------------------|-----------------------|
| **macOS** | Yes | Yes | Yes | Yes |
| **Windows** | Yes | Yes | No (needs macOS) | Yes |
| **Linux** | Yes | Yes | No (needs macOS) | Yes |

### Required Accounts / Services

| Service | Required? | Purpose |
|---------|-----------|---------|
| **Mailgun** | Optional | Inbound email integration for court notifications |
| **Expo** | Optional | Push notifications and EAS builds |
| **Fly.io** | Optional | Production backend hosting |

### Install Prerequisites

**macOS (using Homebrew):**
```bash
# Install Python 3.12
brew install python@3.12

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Node.js (LTS)
brew install node@20

# Verify installations
python3 --version   # Should show 3.12.x
poetry --version     # Should show 1.7+
node --version       # Should show v20.x.x
npm --version        # Should show 9+
```

**Windows:**
```powershell
# Install Python 3.12 from https://www.python.org/downloads/
# Make sure to check "Add Python to PATH" during installation

# Install Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Install Node.js LTS from https://nodejs.org/

# Verify installations
python --version
poetry --version
node --version
npm --version
```

**Linux (Ubuntu/Debian):**
```bash
# Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Node.js 20.x (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
python3 --version
poetry --version
node --version
npm --version
```

---

## 2. Cloning the Repository

### Clone the Repo

```bash
git clone https://github.com/mrk2811/casetracker.git
cd casetracker
```

### Switch to the Default Branch

```bash
git checkout devin/1775342725-initial-codebase
```

### Repository Structure

```
casetracker/
├── ny-court-tracker-backend/     # FastAPI backend (Python)
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── database.py           # SQLite database setup & schema
│   │   ├── auth.py               # JWT authentication & password hashing
│   │   ├── routers/              # API route handlers
│   │   │   ├── cases.py          # Case CRUD endpoints
│   │   │   ├── appearances.py    # Court appearance endpoints
│   │   │   ├── dashboard.py      # Dashboard & calendar endpoints
│   │   │   ├── court_configs.py  # Court configuration endpoints
│   │   │   ├── scraper.py        # Scraper control endpoints
│   │   │   ├── notifications.py  # Notification endpoints
│   │   │   ├── email_integration.py  # Email webhook endpoints
│   │   │   └── discovery.py      # Case discovery endpoints
│   │   ├── schemas/
│   │   │   └── __init__.py       # Pydantic request/response schemas
│   │   ├── scraper/
│   │   │   ├── engine.py         # Web scraper with rate limiting
│   │   │   └── scheduler.py      # APScheduler for periodic scraping
│   │   ├── adapters/
│   │   │   ├── base.py           # Abstract court adapter interface
│   │   │   ├── registry.py       # Adapter registry
│   │   │   ├── ny_webcivil.py    # NY WebCivil Supreme/Civil adapter
│   │   │   └── ny_webcrimin.py   # NY WebCriminal adapter
│   │   ├── email/
│   │   │   ├── webhook.py        # Inbound email webhook handler
│   │   │   ├── parser.py         # Court notification email parser
│   │   │   └── dedup.py          # Email/scraper deduplication engine
│   │   ├── notifications/
│   │   │   ├── engine.py         # Notification creation & dispatch
│   │   │   ├── push.py           # Expo push notification service
│   │   │   └── scheduler.py      # Notification scheduler (reminders, digests)
│   │   └── discovery/
│   │       └── engine.py         # Weekly case discovery engine
│   ├── pyproject.toml            # Python dependencies (Poetry)
│   └── poetry.lock               # Locked dependency versions
│
├── ny-court-tracker-mobile/      # React Native / Expo frontend
│   ├── App.tsx                   # Root app component
│   ├── index.ts                  # Expo entry point
│   ├── src/
│   │   ├── context/
│   │   │   └── AuthContext.tsx    # Authentication state management
│   │   ├── navigation/
│   │   │   └── AppNavigator.tsx  # Tab & stack navigation
│   │   ├── screens/
│   │   │   ├── LoginScreen.tsx
│   │   │   ├── RegisterScreen.tsx
│   │   │   ├── DashboardScreen.tsx
│   │   │   ├── CasesScreen.tsx
│   │   │   ├── CaseDetailScreen.tsx
│   │   │   ├── CaseFormScreen.tsx
│   │   │   ├── CalendarScreen.tsx
│   │   │   ├── NotificationsScreen.tsx
│   │   │   ├── DiscoveriesScreen.tsx
│   │   │   ├── EmailSetupScreen.tsx
│   │   │   └── SettingsScreen.tsx
│   │   └── services/
│   │       ├── api.ts            # Axios API client & type definitions
│   │       ├── storage.ts        # Platform-aware secure storage
│   │       └── pushNotifications.ts  # Expo push notification service
│   ├── app.json                  # Expo configuration
│   ├── package.json              # Node.js dependencies
│   ├── package-lock.json         # Locked dependency versions
│   └── tsconfig.json             # TypeScript configuration
│
├── SETUP_GUIDE.md                # This file
└── README.md
```

---

## 3. Backend Setup

### 3.1. Navigate to the Backend Directory

```bash
cd ny-court-tracker-backend
```

### 3.2. Install Dependencies with Poetry

```bash
# Install all dependencies
poetry install

# Activate the virtual environment
poetry shell
```

> **Note:** If you prefer not to use `poetry shell`, you can prefix all commands with `poetry run` (e.g., `poetry run uvicorn app.main:app`).

### 3.3. Key Backend Dependencies

These are installed automatically by Poetry from `pyproject.toml`:

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ^0.115.3 | Web framework |
| `uvicorn` | ^0.34.0 | ASGI server |
| `pyjwt` | ^2.10.1 | JWT token handling |
| `bcrypt` | ^4.3.0 | Password hashing |
| `httpx` | ^0.28.1 | Async HTTP client (for scraper) |
| `beautifulsoup4` | ^4.13.3 | HTML parsing (for scraper) |
| `apscheduler` | ^3.11.0 | Background job scheduling |
| `python-multipart` | ^0.0.20 | Form data parsing |
| `pydantic` | (via FastAPI) | Request/response validation |

### 3.4. Set Up Environment Variables

Create a `.env` file in the `ny-court-tracker-backend/` directory:

```bash
# Required
export JWT_SECRET_KEY="your-secret-key-change-this-in-production"

# Optional - defaults shown
export DB_DIR="/data"                          # Database directory (falls back to app/ dir if /data doesn't exist)
export INBOUND_EMAIL_DOMAIN="your-mailgun-domain.mailgun.org"  # For email integration
```

> **For local development**, you don't need to create a `/data` directory. The app automatically falls back to storing the SQLite database (`app.db`) in the `app/` directory if `/data` doesn't exist.

**Generate a secure JWT secret:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Load the environment variables:
```bash
source .env
```

### 3.5. Initialize the Database

The database is **automatically initialized** when the backend starts. The `init_db()` function in `app/database.py` runs on startup and:

1. Creates all 13 tables if they don't exist
2. Runs column migrations for schema evolution
3. Creates indexes for performance
4. Seeds default court configurations (NY WebCivil and NY WebCriminal)

**No manual migration or seeding step is required.**

### 3.6. Run the Backend Server

```bash
# With Poetry shell activated:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or without activating the shell:
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables hot-reloading for development (auto-restarts on code changes).

### 3.7. Verify the Backend is Running

Open your browser or use `curl`:

```bash
# Health check endpoint
curl http://localhost:8000/health
# Expected response: {"status":"healthy"}

# Interactive API documentation (Swagger UI)
# Open in browser: http://localhost:8000/docs

# Alternative API docs (ReDoc)
# Open in browser: http://localhost:8000/redoc
```

### 3.8. Backend API Overview

Once running, the backend exposes these API groups:

| Endpoint Group | Base Path | Description |
|----------------|-----------|-------------|
| **Auth** | `/api/auth/*` | Register, login, get current user |
| **Cases** | `/api/cases/*` | CRUD for court cases, search, verify |
| **Appearances** | `/api/cases/{id}/appearances/*` | Court date management |
| **Dashboard** | `/api/dashboard/*` | Upcoming appearances, calendar view |
| **Court Configs** | `/api/court-configs/*` | Available court systems |
| **Scraper** | `/api/scraper/*` | Scraper status, manual triggers |
| **Notifications** | `/api/notifications/*` | Settings, push tokens, alerts |
| **Email** | `/api/email/*` | Email integration setup, webhooks |
| **Discovery** | `/api/discovery/*` | Auto-discovery settings, results |

---

## 4. Frontend / Mobile Setup

### 4.1. Navigate to the Frontend Directory

```bash
cd ny-court-tracker-mobile
```

### 4.2. Install Dependencies

```bash
npm install
```

### 4.3. Key Frontend Dependencies

These are installed automatically from `package.json`:

| Package | Version | Purpose |
|---------|---------|---------|
| `expo` | ~54.0.33 | App framework & build tooling |
| `react` | 19.1.0 | UI library |
| `react-native` | 0.81.5 | Cross-platform mobile framework |
| `@react-navigation/native` | ^7.1.6 | Navigation |
| `@react-navigation/bottom-tabs` | ^7.3.10 | Tab navigation |
| `@react-navigation/native-stack` | ^7.3.10 | Stack navigation |
| `axios` | ^1.9.0 | HTTP client |
| `expo-secure-store` | ~14.0.1 | Secure token storage (native) |
| `expo-notifications` | ~0.31.1 | Push notifications |
| `expo-device` | ~7.0.2 | Device info |
| `react-native-calendars` | ^1.1312.0 | Calendar component |
| `@expo/vector-icons` | ^14.1.0 | Icon library |

### 4.4. Configure the API URL

The API URL is hardcoded in `src/services/api.ts`. For local development, you need to update it to point to your local backend:

```bash
# Open src/services/api.ts and change line 4:
```

**Edit `src/services/api.ts`:**

```typescript
// Change this line:
const API_URL = "https://app-ujjdvsxl.fly.dev";

// To your local backend URL:
const API_URL = "http://localhost:8000";
```

> **Important for physical devices or emulators:**
> - **Android Emulator:** Use `http://10.0.2.2:8000` (maps to host machine's localhost)
> - **iOS Simulator:** Use `http://localhost:8000` (shares host network)
> - **Physical Device:** Use your computer's local IP (e.g., `http://192.168.1.100:8000`)
>
> Find your local IP:
> ```bash
> # macOS/Linux
> ifconfig | grep "inet " | grep -v 127.0.0.1
> # Windows
> ipconfig
> ```

### 4.5. Running the App

#### Web Browser

```bash
npx expo start --web
```

This will open the app in your default browser at `http://localhost:8081`.

#### iOS Simulator (macOS only)

```bash
npx expo start --ios
```

Requires Xcode to be installed with iOS simulators configured.

#### Android Emulator

```bash
npx expo start --android
```

Requires Android Studio with an emulator AVD configured.

#### Physical Device via Expo Go

1. Install **Expo Go** from the [App Store](https://apps.apple.com/app/expo-go/id982107779) (iOS) or [Google Play](https://play.google.com/store/apps/details?id=host.exp.exponent) (Android).

2. Start the development server:
   ```bash
   npx expo start
   ```

3. Scan the QR code shown in the terminal:
   - **iOS:** Use the Camera app to scan the QR code
   - **Android:** Use the Expo Go app's built-in scanner

> **Note:** Your phone and computer must be on the **same Wi-Fi network**.

#### Export for Web Deployment

```bash
npx expo export --platform web
```

This creates a static build in the `dist/` folder.

### 4.6. Verify the Frontend is Running

After starting with any method above:

1. You should see the **Login screen** with email and password fields
2. Register a new account using the **Sign Up** link
3. After logging in, you should see the **Dashboard** tab with upcoming appearances

---

## 5. Environment Variables Reference

### Backend Environment Variables

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens. **Must be set in production.** | **Yes** | `"changeme"` | `"a1b2c3d4e5f6..."` (64-char hex) |
| `DB_DIR` | Directory where SQLite database file is stored | No | `"/data"` (falls back to `app/` dir) | `"/data"` or `"/home/user/db"` |
| `INBOUND_EMAIL_DOMAIN` | Mailgun domain for inbound email addresses | No | `"sandboxd49565360f644e5385986fc016c23e16.mailgun.org"` | `"mg.yourdomain.com"` |

### Frontend Configuration

The frontend uses a hardcoded API URL in `src/services/api.ts` rather than environment variables:

| Config | Location | Description | Default | Local Dev Value |
|--------|----------|-------------|---------|-----------------|
| `API_URL` | `src/services/api.ts:4` | Backend API base URL | `"https://app-ujjdvsxl.fly.dev"` | `"http://localhost:8000"` |

### Expo Configuration (`app.json`)

| Field | Value | Description |
|-------|-------|-------------|
| `name` | `ny-court-tracker-mobile` | App display name |
| `slug` | `ny-court-tracker-mobile` | Expo project slug |
| `version` | `1.0.0` | App version |
| `orientation` | `portrait` | Screen orientation |
| `newArchEnabled` | `true` | React Native New Architecture |
| `plugins` | `["expo-font", "expo-secure-store"]` | Expo plugins |

---

## 6. Email Integration Setup (Mailgun)

The app supports automatic parsing of court notification emails (eTrack) via Mailgun inbound routing. This allows attorneys to forward their court notification emails to the app, which then automatically extracts case updates, court dates, and filing information.

### 6.1. How Email Integration Works

```
Attorney's Email (Gmail, Outlook, etc.)
    │
    ▼ (auto-forward rule)
Mailgun Inbound Route
    │
    ▼ (HTTP POST webhook)
Backend: POST /api/email/webhook/mailgun
    │
    ▼ (parse & extract)
Email Parser → Deduplication Engine → Database + Notifications
```

1. The user sets up email forwarding in the app (Settings > Email Setup)
2. The backend generates a unique inbound email address: `case-{hash}@{domain}`
3. The user configures their email client to auto-forward court notifications to this address
4. Mailgun receives the email and POSTs to the backend webhook
5. The backend parses the email, extracts case data, deduplicates, and creates notifications

### 6.2. Create a Mailgun Account

1. Go to [https://www.mailgun.com/](https://www.mailgun.com/) and sign up
2. Verify your email address
3. You'll start with a **sandbox domain** (free tier)

### 6.3. Sandbox Domain vs Custom Domain

| Feature | Sandbox Domain | Custom Domain |
|---------|---------------|---------------|
| Cost | Free | Paid plan required |
| Inbound email | Limited (authorized recipients only) | Unlimited |
| Setup difficulty | Easy | Requires DNS configuration |
| Good for | Development & testing | Production |

For **development/testing**, the sandbox domain is sufficient.

### 6.4. Set Up Inbound Routes

1. Log into the [Mailgun Dashboard](https://app.mailgun.com/)
2. Navigate to **Receiving** > **Create Route**
3. Configure the route:
   - **Expression Type:** Match Recipient
   - **Recipient:** `.*@YOUR_MAILGUN_DOMAIN` (e.g., `.*@sandboxXXXXXX.mailgun.org`)
   - **Actions:**
     - **Forward:** `https://YOUR_BACKEND_URL/api/email/webhook/mailgun`
     - **Store and Notify:** (optional, for debugging)
   - **Priority:** 0
   - **Description:** "Court Case Tracker Inbound Email"

4. Click **Create Route**

### 6.5. Configure the Backend

Set the `INBOUND_EMAIL_DOMAIN` environment variable to match your Mailgun domain:

```bash
export INBOUND_EMAIL_DOMAIN="sandboxXXXXXX.mailgun.org"
```

> The default value is `sandboxd49565360f644e5385986fc016c23e16.mailgun.org`. Change this to your own Mailgun domain.

### 6.6. Test Email Integration

#### Using the Test Webhook Endpoint

```bash
curl -X POST "http://localhost:8000/api/email/webhook/test?sender=etrack@nycourts.gov&subject=eTrack+Notification&text=Index+Number:+123456/2024+County:+New+York+Court+Type:+Supreme" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Using the In-App Setup

1. Log into the app
2. Go to **Settings** > **Email Integration**
3. Click **Set Up Email** — this generates your unique inbound email address
4. The app will show your address (e.g., `case-abc123@your-domain.mailgun.org`)
5. Follow the in-app instructions to set up forwarding in your email client

### 6.7. Set Up Gmail Forwarding

1. Open **Gmail** > **Settings** (gear icon) > **See all settings**
2. Go to the **Forwarding and POP/IMAP** tab
3. Click **Add a forwarding address**
4. Enter the inbound email address from the app
5. Gmail will send a verification email (to the Mailgun address)
6. The backend auto-verifies forwarding on the first received email

**For filtering only court notifications:**

1. In Gmail, go to **Settings** > **Filters and Blocked Addresses**
2. Click **Create a new filter**
3. Set **From:** `etrack@nycourts.gov` (or your court's notification email)
4. Click **Create filter**
5. Check **Forward it to:** and select your inbound address
6. Click **Create filter**

### 6.8. Supported Email Types

The parser recognizes emails from:
- `etrack@nycourts.gov` — NY eTrack notifications
- `ecf@` — ECF filing notifications
- Emails with subjects containing: "eTrack", "Court Notice", "Calendar Notice", "Filing", "Appearance"

Extracted event types:
- `filing` — New filings
- `appearance_scheduled` — Court date scheduled
- `decision` — Court decisions
- `status_change` — Case status changes
- `update` — General updates

---

## 7. Running in Production / Deployment

### 7.1. Backend Deployment (Fly.io)

The production backend is deployed on [Fly.io](https://fly.io/). The production URL is `https://app-ujjdvsxl.fly.dev`.

#### Install the Fly.io CLI

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

#### Authenticate

```bash
fly auth login
```

#### Create a `fly.toml` Configuration

Create `ny-court-tracker-backend/fly.toml`:

```toml
app = "your-app-name"
primary_region = "ewr"   # Choose: ewr (Newark), iad (Virginia), lax (LA), etc.

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[mounts]
  source = "data"
  destination = "/data"
```

#### Create a `Procfile`

Create `ny-court-tracker-backend/Procfile`:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### Deploy

```bash
cd ny-court-tracker-backend

# Create the app (first time only)
fly launch --name your-app-name --region ewr --no-deploy

# Create a persistent volume for SQLite
fly volumes create data --size 1 --region ewr

# Set environment variables
fly secrets set JWT_SECRET_KEY="your-production-secret-key"
fly secrets set INBOUND_EMAIL_DOMAIN="your-domain.mailgun.org"

# Deploy
fly deploy
```

#### Verify Deployment

```bash
curl https://your-app-name.fly.dev/health
# Expected: {"status":"healthy"}
```

> **Important:** SQLite with Fly.io requires a **persistent volume** mounted at `/data` to ensure the database survives deployments and restarts. The `[mounts]` section in `fly.toml` handles this.

### 7.2. Frontend Web Deployment

#### Build the Web App

```bash
cd ny-court-tracker-mobile

# Make sure API_URL in src/services/api.ts points to your production backend
# e.g., "https://your-app-name.fly.dev"

npx expo export --platform web
```

This creates a `dist/` folder with static files.

#### Deploy to Any Static Hosting

**Netlify:**
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist
```

**Vercel:**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod dist
```

**GitHub Pages:**
```bash
# Install gh-pages
npm install -g gh-pages

# Deploy
gh-pages -d dist
```

**Cloudflare Pages:**
```bash
# Install Wrangler
npm install -g wrangler

# Deploy
wrangler pages deploy dist --project-name=ny-court-tracker
```

### 7.3. Building Mobile APK / IPA (EAS Build)

#### Install EAS CLI

```bash
npm install -g eas-cli
```

#### Log in to Expo

```bash
eas login
```

#### Create `eas.json`

Create `ny-court-tracker-mobile/eas.json`:

```json
{
  "cli": {
    "version": ">= 3.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "android": {
        "buildType": "app-bundle"
      },
      "ios": {
        "buildConfiguration": "Release"
      }
    }
  }
}
```

#### Build for Android (APK)

```bash
cd ny-court-tracker-mobile

# Preview build (APK for testing)
eas build --platform android --profile preview

# Production build (AAB for Google Play)
eas build --platform android --profile production
```

#### Build for iOS (IPA)

```bash
cd ny-court-tracker-mobile

# Requires Apple Developer account ($99/year)
eas build --platform ios --profile production
```

> **Note:** iOS builds require an Apple Developer account. Android APK builds can be installed directly on devices without a Play Store listing.

---

## 8. Testing

### 8.1. Backend Tests

The backend does not include a pre-built test suite. You can test the API manually or create tests using `pytest`:

```bash
cd ny-court-tracker-backend

# Install pytest (if not already in dependencies)
poetry add --dev pytest pytest-asyncio httpx

# Run tests
poetry run pytest
```

#### Quick API Smoke Test Script

```bash
#!/bin/bash
# save as test_api.sh and run: bash test_api.sh

BASE_URL="http://localhost:8000"

echo "=== Health Check ==="
curl -s "$BASE_URL/health" | python3 -m json.tool

echo -e "\n=== Register User ==="
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!","first_name":"Test","last_name":"User"}')
echo "$REGISTER_RESPONSE" | python3 -m json.tool

echo -e "\n=== Login ==="
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}')
echo "$LOGIN_RESPONSE" | python3 -m json.tool
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -n "$TOKEN" ]; then
  echo -e "\n=== Get Current User ==="
  curl -s "$BASE_URL/api/auth/me" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

  echo -e "\n=== List Cases ==="
  curl -s "$BASE_URL/api/cases" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

  echo -e "\n=== Get Dashboard ==="
  curl -s "$BASE_URL/api/dashboard" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

  echo -e "\n=== Get Court Configs ==="
  curl -s "$BASE_URL/api/court-configs" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

  echo -e "\n=== Get Notification Settings ==="
  curl -s "$BASE_URL/api/notifications/settings" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
fi

echo -e "\n=== API Docs ==="
echo "Swagger UI: $BASE_URL/docs"
echo "ReDoc: $BASE_URL/redoc"
```

### 8.2. Frontend Tests

The frontend does not include a pre-built test suite. You can test components using Jest (already included with Expo):

```bash
cd ny-court-tracker-mobile

# Run tests (if test files exist)
npm test
```

### 8.3. Manual Testing Checklist

Use this checklist to verify the complete app flow:

- [ ] **Register a new account**
  - Navigate to the Register screen
  - Enter first name, last name, email, password
  - Optionally enter attorney registration number
  - Submit and verify you're redirected to the Dashboard

- [ ] **Login with existing account**
  - Go to the Login screen
  - Enter email and password
  - Verify you're logged in and see the Dashboard

- [ ] **Add a case manually**
  - Go to Cases tab > Add Case (+ button)
  - Enter case details: court type, county, index number
  - Save and verify the case appears in the list

- [ ] **Search & verify a case**
  - On the Add Case screen, use the Search feature
  - Enter an index number and county
  - Select a court system (NY WebCivil or NY WebCriminal)
  - Verify search results appear

- [ ] **View the Dashboard**
  - Check that upcoming appearances are listed
  - Verify case counts are displayed

- [ ] **Check the Calendar**
  - Go to the Calendar tab
  - Verify court dates appear on the calendar
  - Tap a date to see appearance details

- [ ] **Set up email integration**
  - Go to Settings > Email Integration
  - Click Set Up Email
  - Verify an inbound email address is generated

- [ ] **Test email forwarding** (if Mailgun configured)
  - Forward a test email to the inbound address
  - Check the email log in Settings > Email Integration
  - Verify events were extracted and notifications created

- [ ] **Check notifications**
  - Go to the Notifications tab
  - Verify notifications appear for case events
  - Mark notifications as read

- [ ] **Configure notification settings**
  - Go to Settings > Notification Preferences
  - Toggle push/email notifications
  - Set reminder days and digest frequency

- [ ] **Set up case discovery**
  - Go to Settings > Case Discovery
  - Enter attorney name and registration number
  - Enable discovery and verify settings are saved

- [ ] **Sign out**
  - Go to Settings > Sign Out
  - Verify you're returned to the Login screen
  - **On web:** Uses `window.confirm()` dialog
  - **On native:** Uses `Alert.alert()` dialog

---

## 9. Troubleshooting

### CORS Errors

**Symptom:** Frontend shows "Network Error" or CORS-related errors in browser console.

**Solution:** The backend includes CORS middleware that allows all origins:

```python
# In app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

If you're still seeing CORS errors:
- Ensure the backend is actually running
- Verify the `API_URL` in `src/services/api.ts` is correct
- Check that no proxy or firewall is blocking requests

### Database Issues

**Symptom:** SQLite errors or "database is locked."

**Solutions:**
- Ensure only one instance of the backend is running
- The database uses WAL mode and foreign keys by default
- If the database is corrupted, delete `app.db` and restart the server (it will be recreated)
- Check that the `DB_DIR` directory exists and is writable

**Symptom:** Missing columns after code update.

**Solution:** The database runs automatic migrations on startup. Simply restart the server:
```bash
# Stop the server (Ctrl+C), then restart
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Expo Build Errors

**Symptom:** `expo start` fails with dependency errors.

**Solutions:**
```bash
# Clear npm cache and reinstall
rm -rf node_modules
npm install

# Clear Expo cache
npx expo start --clear

# Fix Expo dependency versions
npx expo install --fix
```

**Symptom:** "Error: Unable to resolve module" or Metro bundler errors.

**Solutions:**
```bash
# Reset Metro cache
npx expo start --clear

# If using a monorepo, try:
watchman watch-del-all   # If watchman is installed
```

### Email Webhook Not Receiving Emails

**Symptom:** Emails forwarded to Mailgun address are not appearing in the app.

**Solutions:**
1. **Check Mailgun logs:** Go to Mailgun Dashboard > Logs > Inbound
2. **Verify the route:** Ensure the Mailgun route is pointing to the correct backend URL
3. **Check the backend is accessible:** The webhook endpoint must be publicly accessible (not localhost)
4. **Test the webhook manually:**
   ```bash
   curl -X POST "https://YOUR_BACKEND_URL/api/email/webhook/mailgun" \
     -F "sender=etrack@nycourts.gov" \
     -F "subject=eTrack Notification" \
     -F "body-plain=Index Number: 123456/2024 County: New York"
   ```
5. **Check email parsing:** The parser only processes emails that match court notification patterns (from `etrack@nycourts.gov` or with specific subjects)

### Sign Out Not Working on Web

**Symptom:** Tapping "Sign Out" does nothing on the web version.

**Explanation:** The app uses `Alert.alert()` for confirmation, which doesn't exist on web. The app has been updated to use `window.confirm()` on web platforms and `Alert.alert()` on native.

If you're still experiencing this, ensure you have the latest code from the `devin/1775342725-initial-codebase` branch.

### Push Notifications Not Working

**Symptom:** Not receiving push notifications.

**Solutions:**
1. **Physical device required:** Push notifications don't work in simulators/emulators
2. **Check Expo project ID:** Ensure `app.json` has a valid `extra.eas.projectId` if using EAS
3. **Check push token registration:** View the backend logs for token registration calls
4. **Verify notification settings:** Check Settings > Notification Preferences > Push Enabled

### Backend Server Won't Start

**Symptom:** `uvicorn` fails to start.

**Solutions:**
```bash
# Check Python version
python3 --version  # Must be 3.12+

# Ensure Poetry virtual environment is activated
poetry shell

# Check for port conflicts
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill existing process on port 8000
kill $(lsof -t -i:8000)  # macOS/Linux
```

### Android Emulator Can't Connect to Backend

**Symptom:** App shows connection error on Android emulator.

**Solution:** Android emulators use a special IP to reach the host machine:

```typescript
// In src/services/api.ts, use:
const API_URL = "http://10.0.2.2:8000";
```

### Scraper Getting Blocked (CAPTCHA)

**Symptom:** Scraper returns no results, logs show "CAPTCHA detected."

**Explanation:** The NY court websites may block automated requests. The scraper includes:
- User-Agent rotation (20 different agents)
- Rate limiting (max 10 requests/minute, 2-8 second random delays)
- Exponential backoff (up to 120 seconds)
- CAPTCHA detection

**Solutions:**
- Wait and retry later (the automated schedule handles this)
- Reduce scraping frequency in the scheduler configuration
- The email integration provides an alternative data source that doesn't rely on scraping

---

## 10. Architecture Decisions

### Why React Native with Expo?

- **Cross-platform:** Single codebase for iOS, Android, and Web
- **Expo:** Simplifies build tooling, push notifications, and over-the-air updates
- **React Native New Architecture:** Enabled for better performance (`newArchEnabled: true`)
- **Expo Go:** Enables rapid development and testing on physical devices without native builds
- **Web support:** The app works in browsers via `expo start --web`

### Why FastAPI?

- **Async/await:** Built-in async support, ideal for I/O-heavy operations (HTTP scraping, database queries)
- **Auto-generated API docs:** Swagger UI at `/docs` and ReDoc at `/redoc` out of the box
- **Type safety:** Pydantic schema validation for all requests/responses
- **Performance:** One of the fastest Python web frameworks
- **Minimal boilerplate:** Clean, readable route definitions

### Why SQLite?

- **Zero configuration:** No separate database server to install or manage
- **Single-file database:** Easy backup, migration, and deployment
- **Sufficient for workload:** Excellent for single-user or small-team applications
- **Fly.io compatible:** Works with persistent volumes for production deployment
- **WAL mode:** Enabled for better concurrent read performance
- **Built into Python:** No additional database driver installation needed

### Email Forwarding via Mailgun

- **Why Mailgun?** Reliable inbound email parsing with webhook support
- **Inbound routing:** Mailgun receives emails and POSTs the content to the backend webhook
- **Privacy-first:** Only emails matching court notification patterns are parsed; other emails are ignored
- **Dual data source:** Email data is considered more authoritative than scraper data (email "wins" in deduplication)
- **Deterministic addresses:** Each user gets a unique, deterministic address (`case-{hash}@domain`) based on their user ID
- **Auto-verification:** Forwarding is automatically verified on the first successful email receipt

### Scraper Architecture

- **Adapter pattern:** `CourtAdapter` abstract base class allows adding new court systems
- **Currently supported:** NY WebCivil (Supreme & Civil) and NY WebCriminal
- **Rate limiting:** Respectful scraping with randomized delays and exponential backoff
- **CAPTCHA detection:** Automatically detects and backs off when court websites show CAPTCHAs
- **APScheduler:** Background scheduling for periodic scraping (2x/day normal, every 3 hours high priority)

### Notification System

- **Expo Push API:** Uses `https://exp.host/--/api/v2/push/send` for mobile push notifications
- **Per-case preferences:** Users can customize notification settings per case
- **Digest emails:** Daily and weekly digest summaries of case activity
- **Auto-priority escalation:** Cases automatically escalate to high priority when court dates are within 7 days
- **Stale case detection:** Alerts when cases haven't been updated within expected timeframes

---

## Quick Start Summary

```bash
# 1. Clone the repo
git clone https://github.com/mrk2811/casetracker.git
cd casetracker
git checkout devin/1775342725-initial-codebase

# 2. Start the backend
cd ny-court-tracker-backend
poetry install
export JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. In a new terminal, start the frontend
cd ny-court-tracker-mobile
npm install
# Edit src/services/api.ts: change API_URL to "http://localhost:8000"
npx expo start --web

# 4. Open http://localhost:8081 in your browser
# 5. Register a new account and start tracking cases!
```

---

*Last updated: April 2026*
