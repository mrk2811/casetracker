# NY Court Case Tracker - Codebase Documentation

## Table of Contents

- [1. Project Overview](#1-project-overview)
  - [1.1 What the App Does](#11-what-the-app-does)
  - [1.2 High-Level Architecture](#12-high-level-architecture)
  - [1.3 Tech Stack Summary](#13-tech-stack-summary)
- [2. Backend Architecture](#2-backend-architecture)
  - [2.1 Project Structure](#21-project-structure)
  - [2.2 FastAPI App Setup](#22-fastapi-app-setup)
  - [2.3 Database Layer](#23-database-layer)
  - [2.4 Authentication](#24-authentication)
  - [2.5 API Routers](#25-api-routers)
  - [2.6 Schemas](#26-schemas)
  - [2.7 Email Integration](#27-email-integration)
  - [2.8 Scraper Engine](#28-scraper-engine)
  - [2.9 Notifications Engine](#29-notifications-engine)
  - [2.10 Discovery Engine](#210-discovery-engine)
  - [2.11 Court Adapters](#211-court-adapters)
- [3. Frontend Architecture](#3-frontend-architecture)
  - [3.1 Project Structure](#31-project-structure)
  - [3.2 Navigation](#32-navigation)
  - [3.3 Screens](#33-screens)
  - [3.4 Services](#34-services)
  - [3.5 Context](#35-context)
  - [3.6 Key UI Patterns](#36-key-ui-patterns)
- [4. Data Flow Diagrams](#4-data-flow-diagrams)
  - [4.1 User Registration / Login Flow](#41-user-registration--login-flow)
  - [4.2 Adding a Case Manually](#42-adding-a-case-manually)
  - [4.3 Email Forwarding Flow](#43-email-forwarding-flow)
  - [4.4 Scraper Flow](#44-scraper-flow)
  - [4.5 Notification Flow](#45-notification-flow)
  - [4.6 Weekly Discovery Flow](#46-weekly-discovery-flow)
- [5. API Reference](#5-api-reference)
  - [5.1 Authentication](#51-authentication)
  - [5.2 Cases](#52-cases)
  - [5.3 Appearances](#53-appearances)
  - [5.4 Dashboard](#54-dashboard)
  - [5.5 Notifications](#55-notifications)
  - [5.6 Scraper](#56-scraper)
  - [5.7 Email Integration](#57-email-integration)
  - [5.8 Discovery](#58-discovery)
  - [5.9 Court Configs](#59-court-configs)
- [6. Database Schema](#6-database-schema)
  - [6.1 Tables](#61-tables)
  - [6.2 Entity Relationships](#62-entity-relationships)

---

## 1. Project Overview

### 1.1 What the App Does

The **NY Court Case Tracker** is a full-stack application that helps attorneys and legal professionals aggregate and monitor New York court case schedules from a single unified dashboard. Key capabilities include:

- **Multi-source case tracking**: Cases can be added manually, imported via web scraping from NY WebCivil and NY WebCriminal court systems, received via email forwarding from eTrack court notifications, or fetched from API providers.
- **Unified dashboard**: All upcoming court appearances are displayed in a single chronological view with priority badges, court type indicators, and data freshness status.
- **Calendar view**: A month-by-month calendar showing court appearances with color-coded court type dots.
- **Automated web scraping**: Scheduled scraping of NY court websites with configurable priority levels (normal: 2x/day, high: every 2-4 hours).
- **Email integration**: Users get a unique forwarding email address. Court notification emails (from eTrack) are automatically parsed to extract case events, filings, and appearance changes.
- **Push and email notifications**: Configurable reminders before court dates, alerts for case changes, daily/weekly digest summaries.
- **Weekly case discovery**: Automatic scanning of court systems to find new cases associated with an attorney's name.
- **Data deduplication**: Intelligent reconciliation where email data (push) always takes priority over scraper data (pull).

### 1.2 High-Level Architecture

```
+-----------------------------------------------------+
|              React Native Expo Frontend               |
|  (iOS / Android / Web)                               |
|  - Dashboard, Cases, Calendar, Notifications, Settings|
+----------------------------+-------------------------+
                             |
                        HTTPS / REST
                             |
+----------------------------v-------------------------+
|              FastAPI Python Backend                    |
|  - JWT Auth, REST API, Background Schedulers          |
+---+--------+--------+---------+---------+-----+------+
    |        |        |         |         |     |
    v        v        v         v         v     v
  SQLite  Scraper  Email     Notif.   Discovery Court
   DB     Engine   Webhooks  Engine   Engine    Adapters
                                                  |
                                      +-----------+-----------+
                                      |                       |
                                 NY WebCivil            NY WebCriminal
                                 (iapps.courts          (iapps.courts
                                  .state.ny.us)          .state.ny.us)
```

### 1.3 Tech Stack Summary

**Backend (`ny-court-tracker-backend/`)**

| Component | Technology |
|-----------|-----------|
| Web framework | FastAPI (with Uvicorn) |
| Language | Python 3.12+ |
| Database | SQLite (WAL mode, foreign keys enabled) |
| Authentication | JWT (PyJWT) + bcrypt password hashing |
| Package manager | Poetry |
| HTTP client | httpx (async) |
| HTML parsing | BeautifulSoup4 + lxml |
| Task scheduling | APScheduler |
| Email sending | aiosmtplib |
| Validation | Pydantic v2 (with email support) |

**Frontend (`ny-court-tracker-mobile/`)**

| Component | Technology |
|-----------|-----------|
| Framework | React Native 0.81 + Expo SDK 54 |
| Language | TypeScript 5.9 |
| Navigation | React Navigation 7 (bottom tabs + native stack) |
| HTTP client | Axios |
| Secure storage | expo-secure-store (native) / localStorage (web) |
| Push notifications | expo-notifications |
| Icons | @expo/vector-icons (Ionicons) |
| Calendar | react-native-calendars |

---

## 2. Backend Architecture

### 2.1 Project Structure

```
ny-court-tracker-backend/
├── pyproject.toml          # Poetry dependencies and project metadata
├── app/
│   ├── main.py             # FastAPI app creation, CORS, startup/shutdown, router registration
│   ├── database.py         # SQLite connection management, schema creation, migrations, seeding
│   ├── auth.py             # JWT token creation/validation, password hashing, auth dependency
│   ├── routers/            # API endpoint definitions
│   │   ├── auth.py         # Registration, login, user profile
│   │   ├── cases.py        # Case CRUD, search, verify, freshness
│   │   ├── appearances.py  # Appearance CRUD per case
│   │   ├── dashboard.py    # Dashboard and calendar aggregation
│   │   ├── notifications.py# Notification settings, list, push tokens, per-case prefs
│   │   ├── court_configs.py# Court configuration listing
│   │   ├── scraper.py      # Manual scrape triggers, status, history
│   │   ├── email_integration.py # Email setup, webhooks, verification
│   │   └── discovery.py    # Discovery settings, accept/dismiss, trigger
│   ├── schemas/
│   │   └── __init__.py     # All Pydantic request/response models
│   ├── adapters/           # Court system adapters (strategy pattern)
│   │   ├── base.py         # Abstract CourtAdapter, DataSource, CaseSource enum
│   │   ├── registry.py     # Adapter registry (get_adapter, list_adapters)
│   │   ├── ny_webcivil.py  # NY WebCivil scraper adapter (Supreme & Civil)
│   │   └── ny_webcrimin.py # NY WebCriminal scraper adapter
│   ├── email/              # Email integration subsystem
│   │   ├── parser.py       # Court notification email parsing (regex-based)
│   │   ├── webhook.py      # Inbound email webhook handlers (SendGrid, Mailgun)
│   │   └── dedup.py        # Deduplication and reconciliation engine
│   ├── scraper/            # Web scraping subsystem
│   │   ├── engine.py       # Core HTTP scraping engine with rate limiting
│   │   └── scheduler.py    # APScheduler-based scrape job scheduling
│   ├── notifications/      # Notification subsystem
│   │   ├── engine.py       # Notification creation and dispatch
│   │   ├── push.py         # Expo Push Notification service
│   │   └── scheduler.py    # Notification scheduling (reminders, digests, escalation)
│   └── discovery/          # Case discovery subsystem
│       └── engine.py       # Weekly attorney-based case scanning
```

### 2.2 FastAPI App Setup

**File**: `app/main.py`

The FastAPI application is configured with:

- **CORS Middleware**: Allows all origins (`*`), all methods, and all headers for development flexibility.
- **Startup Event (`@app.on_event("startup")`)**:
  1. Initializes the SQLite database (creates tables, runs migrations, seeds default data).
  2. Starts the scraper scheduler (APScheduler) for background scrape jobs.
  3. Starts the notification scheduler for reminders, digests, and auto-escalation.
- **Shutdown Event (`@app.on_event("shutdown")`)**:
  1. Shuts down the scraper scheduler.
  2. Shuts down the notification scheduler.
- **Health Check**: `GET /health` returns `{"status": "ok"}`.
- **Router Registration**: All routers are included under the `/api` prefix:
  - `/api/auth` - Authentication
  - `/api/cases` - Cases
  - `/api/dashboard` - Dashboard
  - `/api/notifications` - Notifications
  - `/api/scraper` - Scraper
  - `/api/email` - Email integration
  - `/api/court-configs` - Court configs
  - `/api/discovery` - Discovery
  - `/api/appearances` - Appearances (top-level for update/delete by appearance ID)

### 2.3 Database Layer

**File**: `app/database.py`

The database layer uses raw SQLite (via Python's `sqlite3` module), not an ORM. Key design decisions:

- **WAL Mode**: `PRAGMA journal_mode=WAL` for concurrent read/write performance.
- **Foreign Keys**: `PRAGMA foreign_keys=ON` enforced on every connection.
- **Connection Management**: `get_db()` context manager provides thread-local connections.
- **Schema Initialization**: `init_db()` creates all tables with `CREATE TABLE IF NOT EXISTS`.
- **Migrations**: `run_migrations()` adds columns to existing tables (e.g., `priority`, `source`, `last_checked_at`, `court_system`, `verified`, `last_source`) using `ALTER TABLE ADD COLUMN` wrapped in try/except for idempotency.
- **Seeding**: `seed_court_configs()` inserts default court configurations for NY WebCivil and NY WebCriminal.
- **Indexes**: Created on frequently queried columns (e.g., `user_id`, `case_id`, `appearance_date`).

### 2.4 Authentication

**Files**: `app/auth.py`, `app/routers/auth.py`

**JWT-based authentication flow:**

1. **Registration** (`POST /api/auth/register`):
   - Accepts email, password, first_name, last_name, optional attorney_reg_number.
   - Password is hashed with bcrypt (12 rounds).
   - Returns a JWT access token and user object.
   - Automatically creates default notification settings and discovery settings for the new user.

2. **Login** (`POST /api/auth/login`):
   - Validates email/password against bcrypt hash.
   - Returns JWT access token (24-hour expiry) and user object.

3. **Token Validation**:
   - `get_current_user_id()` is a FastAPI dependency that extracts the user ID from the `Authorization: Bearer <token>` header.
   - Tokens are signed with HS256 using a configurable `JWT_SECRET` (defaults to a hardcoded development secret).

### 2.5 API Routers

#### 2.5.1 Auth Router (`app/routers/auth.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register a new user account |
| `/api/auth/login` | POST | Authenticate and receive JWT token |
| `/api/auth/me` | GET | Get current authenticated user profile |

#### 2.5.2 Cases Router (`app/routers/cases.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cases` | GET | List all cases for the authenticated user (with optional filters) |
| `/api/cases` | POST | Create a new case manually |
| `/api/cases/search` | POST | Search a court system for cases (uses adapter) |
| `/api/cases/verify` | POST | Create a case with verified data from court search + trigger initial scrape |
| `/api/cases/{id}` | GET | Get a specific case by ID |
| `/api/cases/{id}/events` | GET | Get all events for a case |
| `/api/cases/{id}/freshness` | GET | Get freshness status for a case |
| `/api/cases/{id}/priority` | PUT | Update case priority (normal/high) |
| `/api/cases/{id}` | PUT | Update case details |
| `/api/cases/{id}` | DELETE | Delete a case and all related data |

**Filters on `GET /api/cases`**: `court_type`, `county`, `status`, `priority`, `source`, `verified`, `sort_by` (supports `next_appearance`, `created_at`, `updated_at`).

**Search flow**: The `POST /api/cases/search` endpoint delegates to the appropriate court adapter (NYWebCivil or NYWebCriminal) based on `court_system` parameter. It returns search results that the frontend displays for user selection.

**Verify flow**: `POST /api/cases/verify` creates the case, marks it as `verified=true`, sets the appropriate `source` and `court_system`, and triggers an initial background scrape to fetch appearances.

#### 2.5.3 Appearances Router (`app/routers/appearances.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cases/{case_id}/appearances` | GET | List all appearances for a case |
| `/api/cases/{case_id}/appearances` | POST | Add a new appearance to a case |
| `/api/appearances/{id}` | PUT | Update an appearance |
| `/api/appearances/{id}` | DELETE | Delete an appearance |

#### 2.5.4 Dashboard Router (`app/routers/dashboard.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard` | GET | Get upcoming appearances across all cases (with filters) |
| `/api/dashboard/calendar` | GET | Get appearances for a specific month/year |

**Dashboard query**: Joins `appearances` with `cases` to produce `DashboardAppearance` objects that include both appearance details and case metadata (court type, county, parties, priority, freshness). Default look-ahead is 90 days.

**Calendar query**: Filters appearances to a specific month, returning the same `DashboardAppearance` format.

#### 2.5.5 Notifications Router (`app/routers/notifications.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications/settings` | GET | Get user's notification settings |
| `/api/notifications/settings` | PUT | Update notification settings |
| `/api/notifications` | GET | List notifications (with type/unread filters) |
| `/api/notifications/unread-count` | GET | Get count of unread notifications |
| `/api/notifications/{id}/read` | PUT | Mark a notification as read |
| `/api/notifications/read-all` | PUT | Mark all notifications as read |
| `/api/notifications/{id}` | DELETE | Delete a notification |
| `/api/notifications` | DELETE | Delete all notifications |
| `/api/notifications/push-token` | POST | Register a push notification token |
| `/api/notifications/push-token` | DELETE | Unregister a push token |
| `/api/notifications/push-tokens` | GET | List registered push tokens |
| `/api/notifications/case/{case_id}/prefs` | GET | Get per-case notification preferences |
| `/api/notifications/case/{case_id}/prefs` | PUT | Update per-case notification preferences |
| `/api/notifications/trigger-checks` | POST | Manually trigger notification checks (testing) |

#### 2.5.6 Court Configs Router (`app/routers/court_configs.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/court-configs` | GET | List all court configurations |
| `/api/court-configs/adapters` | GET | List available adapter classes |

#### 2.5.7 Scraper Router (`app/routers/scraper.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scraper/status` | GET | Get scraper scheduler status and job info |
| `/api/scraper/trigger-manual` | POST | Trigger a manual scrape for a specific case |
| `/api/scraper/history/{case_id}` | GET | Get scrape job history for a case |
| `/api/scraper/trigger-batch` | POST | Trigger batch scraping for all cases of a given priority |

#### 2.5.8 Email Integration Router (`app/routers/email_integration.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/email/setup` | POST | Generate a unique inbound email address for the user |
| `/api/email/config` | GET | Get user's email integration configuration |
| `/api/email/verify` | POST | Mark email forwarding as verified |
| `/api/email/config` | DELETE | Remove email integration |
| `/api/email/setup-guide` | GET | Get step-by-step setup instructions |
| `/api/email/log` | GET | Get recent email processing log |
| `/api/email/webhook/sendgrid` | POST | SendGrid inbound email webhook |
| `/api/email/webhook/mailgun` | POST | Mailgun inbound email webhook |
| `/api/email/webhook/test` | POST | Test webhook endpoint for development |

#### 2.5.9 Discovery Router (`app/routers/discovery.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/discovery/settings` | GET | Get user's discovery settings |
| `/api/discovery/settings` | PUT | Update discovery settings |
| `/api/discovery` | GET | List discovered cases (with status filter) |
| `/api/discovery/pending-count` | GET | Get count of pending discoveries |
| `/api/discovery/{id}/accept` | POST | Accept a discovered case (adds to tracked cases) |
| `/api/discovery/{id}/dismiss` | POST | Dismiss a discovered case |
| `/api/discovery/trigger` | POST | Manually trigger a discovery scan |

### 2.6 Schemas

**File**: `app/schemas/__init__.py`

All Pydantic models for request validation and response serialization:

**Authentication:**
- `UserRegister`: email, password, first_name, last_name, attorney_reg_number (optional)
- `UserLogin`: email, password
- `UserOut`: id, email, first_name, last_name, attorney_reg_number, created_at
- `TokenOut`: access_token, token_type, user (UserOut)

**Cases:**
- `CaseCreate`: court_type, county, index_number, case_year, case_status, priority, plaintiff, defendant, plaintiff_firm, defendant_firm, justice, part, notes
- `CaseUpdate`: All fields optional
- `CaseOut`: Full case data including id, user_id, source, verified, last_checked_at, last_source, court_system, freshness, next_appearance, created_at, updated_at
- `CaseSearchRequest`: index_number, court_type, county, court_system
- `CaseSearchResult`: index_number, court_type, county, case_year, case_status, plaintiff, defendant, plaintiff_firm, defendant_firm, justice, part, last_action, last_action_date, source
- `CaseSearchResponse`: results, court_system, message

**Appearances:**
- `AppearanceCreate`: appearance_date, appearance_time, appearance_type, location, notes
- `AppearanceUpdate`: All fields optional
- `AppearanceOut`: Full appearance data with timestamps

**Dashboard:**
- `DashboardAppearance`: Combined appearance + case data (appearance_id, case_id, appearance_date, appearance_time, court_type, county, index_number, plaintiff, defendant, priority, freshness, etc.)

**Notifications:**
- `NotificationSettingsUpdate`: email_enabled, push_enabled, reminder_days, case_updates_enabled, digest_frequency, digest_time
- `NotificationSettingsOut`: Full settings with id and user_id
- `NotificationOut`: id, user_id, case_id, appearance_id, type, title, message, read, push_sent, created_at
- `PushTokenRegister`: token, device_name, platform
- `CaseNotificationPrefsUpdate`: push_enabled, email_enabled, priority_override

**Email:**
- `EmailSetupResponse`: inbound_email, forwarding_verified, provider, already_setup
- `EmailConfigOut`: id, user_id, inbound_email, forwarding_verified, provider, created_at

**Discovery:**
- `DiscoverySettingsOut`: id, user_id, enabled, attorney_name, attorney_reg_number, search_courts, search_county, last_run_at, next_run_at
- `DiscoveredCaseOut`: id, user_id, index_number, court_type, county, court_system, plaintiff, defendant, case_status, last_action, last_action_date, source_adapter, status, discovered_at, resolved_at

### 2.7 Email Integration

#### 2.7.1 Email Parser (`app/email/parser.py`)

Parses court notification emails (primarily from eTrack/NYSCEF) to extract structured case event data.

**Key data structures:**
- `ParsedEmailEvent`: Represents a single extracted event with fields: event_type (filing, appearance_scheduled, appearance_changed, decision, status_change), index_number, court_type, county, case_title, event_date, event_time, description, location, justice, part, raw_text.
- `ParsedEmail`: Container for parse results: is_court_notification flag, sender, subject, events list, raw_body, parse_errors.

**Parsing approach:**
1. `is_court_notification()` checks sender domain and subject line patterns to determine if an email is a court notification.
2. `parse_email()` applies regex patterns to extract:
   - Index numbers (e.g., `123456/2026`)
   - Court types and counties from header patterns
   - Event types from subject and body keywords
   - Dates and times in various formats
   - Party names, justice, and part assignments
3. `parse_multi_case_email()` handles emails that reference multiple cases (e.g., bulk filing notifications).

**Supported email formats:**
- NYSCEF filing notifications
- eTrack appearance scheduled/changed notices
- Court calendar updates
- Decision/order notifications

#### 2.7.2 Email Webhook Handler (`app/email/webhook.py`)

Handles inbound email webhooks from email service providers.

**Unique email generation:**
- Each user gets a deterministic forwarding email: `case-{sha256_hash}@{domain}`
- Hash is based on `courttracker-user-{user_id}-salt-v1`, making it consistent across sessions.

**Webhook processing flow:**
1. Extract sender, subject, and body text from the webhook payload.
2. Identify which user owns the inbound email address via `get_user_id_from_inbound_email()`.
3. Parse the email using `parse_email()` from the parser module.
4. Process extracted events through the deduplication engine.
5. Log the email processing result.

**Supported providers:**
- **SendGrid** (`POST /api/email/webhook/sendgrid`): Parses SendGrid's inbound parse webhook format (multipart form data with `from`, `subject`, `text` fields).
- **Mailgun** (`POST /api/email/webhook/mailgun`): Parses Mailgun's inbound routing format (similar multipart structure).
- **Test** (`POST /api/email/webhook/test`): Simplified endpoint for development testing.

#### 2.7.3 Deduplication Engine (`app/email/dedup.py`)

Reconciles data from multiple sources with a clear priority hierarchy.

**Core rule: Email (push) always wins over scraper (pull).**

**Key functions:**
- `find_matching_case()`: Finds a tracked case matching an email event by index_number, county, and court_type.
- `is_duplicate_event()`: Checks if an identical event already exists in the database.
- `reconcile_event()`: Merges event data into the case, applying the source priority rule.
- `process_email_events()`: Main orchestrator that processes a list of parsed email events for a user:
  1. For each event, finds or creates the matching case.
  2. Checks for duplicates.
  3. Creates case events and upserts appearances.
  4. Generates notifications for new filings, appearance changes, etc.
  5. Updates the case's `last_checked_at` and `last_source` fields.
- `_upsert_appearance()`: Creates or updates an appearance record, preferring email data over scraper data.
- `_create_notification()`: Creates a notification for the user about the event.

### 2.8 Scraper Engine

#### 2.8.1 Core Engine (`app/scraper/engine.py`)

HTTP-based web scraping engine with robustness features.

**Key classes:**
- `ScrapeResult`: Contains success flag, HTML content, BeautifulSoup object, status code, error message, CAPTCHA detection flag, and response time.
- `RateLimitConfig`: Configures max requests/minute (10), min/max delay between requests (2-8s), backoff multiplier (2x), and max backoff (120s).
- `ScraperEngine`: Main engine class providing:
  - **User-Agent rotation**: Maintains a pool of realistic browser user-agent strings, rotating on each request.
  - **Rate limiting**: Enforces minimum delays between requests to avoid triggering court website protections.
  - **CAPTCHA detection**: Scans response HTML for common CAPTCHA indicators (reCAPTCHA, hCaptcha, challenge forms).
  - **Exponential backoff**: On rate limit errors (429) or server errors (5xx), backs off with exponential delay.
  - **Retry logic**: Configurable retry count with increasing delays.
  - **Session management**: Uses `httpx.AsyncClient` with persistent sessions for cookie handling.

**Methods:**
- `get(url, params, headers)` -> `ScrapeResult`
- `post(url, data, headers)` -> `ScrapeResult`
- `health_check(url)` -> `bool`
- `close()`: Cleanup async resources.

#### 2.8.2 Scraper Scheduler (`app/scraper/scheduler.py`)

APScheduler-based background job scheduler for automated scraping.

**Schedule configuration:**

| Job | Schedule | Description |
|-----|----------|-------------|
| Normal priority scrape | 6:00 AM, 12:30 PM ET daily | Scrapes all normal-priority cases |
| High priority scrape | Every 3 hours (6am-9pm ET) | Scrapes all high-priority cases |
| Notification checks | After each scrape batch | Checks for appearance reminders, stale cases |
| Daily digest | 8:00 AM ET daily | Sends daily digest emails |
| Weekly digest | 8:00 AM ET Monday | Sends weekly summary digest |

**Scrape job flow:**
1. Query all cases matching the target priority level.
2. For each case, determine the appropriate court adapter.
3. Call the adapter's `get_case_details()` and `get_appearances()`.
4. Update the case's `last_checked_at` timestamp and `last_source`.
5. Upsert appearances into the database.
6. Record a `scrape_jobs` entry with status (success/failure/skipped).
7. Generate notifications for any detected changes.

### 2.9 Notifications Engine

#### 2.9.1 Notification Engine (`app/notifications/engine.py`)

Central notification creation and dispatch system.

**Core function: `create_notification()`**
1. Checks user's global notification settings (push_enabled, email_enabled).
2. Checks per-case notification preferences (if case_id provided).
3. Inserts notification record into the `notifications` table.
4. If push is enabled, calls `send_push_notification()`.
5. Returns the created notification record.

**Trigger functions** (called by schedulers and event processors):
- `notify_new_filing(user_id, case_id, description)`: New court filing detected.
- `notify_court_date_scheduled(user_id, case_id, appearance_id, date)`: New court date added.
- `notify_court_date_changed(user_id, case_id, appearance_id, old_date, new_date)`: Court date modified.
- `notify_case_update(user_id, case_id, description)`: General case update.
- `notify_appearance_reminder(user_id, case_id, appearance_id, days_until)`: Upcoming appearance reminder.
- `notify_stale_case(user_id, case_id, hours_stale)`: Case data hasn't been refreshed.
- `notify_priority_escalation(user_id, case_id)`: Case auto-escalated from normal to high priority.

#### 2.9.2 Push Notification Service (`app/notifications/push.py`)

Integrates with the Expo Push API for mobile push notifications.

**Functions:**
- `register_push_token(user_id, token, device_name, platform)`: Stores an Expo push token for a user's device.
- `unregister_push_token(user_id, token)`: Removes a push token.
- `deactivate_token(token)`: Marks a token as inactive (e.g., if Expo reports it as invalid).
- `get_user_push_tokens(user_id)`: Returns all active push tokens for a user.
- `send_push_notification(user_id, title, body, data, badge)`: Sends a push notification to all of a user's registered devices via the Expo Push API (`https://exp.host/--/api/v2/push/send`).
- `send_push_to_multiple_users(user_ids, title, body, data)`: Batch sends to multiple users.

#### 2.9.3 Notification Scheduler (`app/notifications/scheduler.py`)

APScheduler-based background jobs for notification-related tasks.

| Job | Schedule | Description |
|-----|----------|-------------|
| `check_appearance_reminders` | 7:00 AM ET daily | Sends reminders for appearances within the user's configured reminder window (default 1 day) |
| `check_auto_priority_escalation` | 7:15 AM ET daily | Escalates normal-priority cases to high when court date is within 7 days |
| `check_stale_cases` | Every 6 hours | Alerts users about cases that haven't been checked (high: >8 hours, normal: >48 hours) |
| `generate_daily_digest` | 8:00 AM ET daily | Sends a summary of today's appearances and recent case activity |
| `generate_weekly_digest` | 8:00 AM ET Monday | Sends a weekly summary with upcoming appearances, case statistics, and recent changes |

### 2.10 Discovery Engine

**File**: `app/discovery/engine.py`

The discovery engine automatically scans court systems to find new cases associated with an attorney.

**Settings management:**
- `get_discovery_settings(user_id)`: Returns the user's discovery configuration.
- `create_or_update_discovery_settings(user_id, data)`: Saves attorney name, registration number, search courts, and county preferences.

**Discovery flow (`run_discovery_for_user`):**
1. Load the user's discovery settings (attorney name, courts to search).
2. For each configured court system (ny_webcivil, ny_webcrimin):
   a. Get the appropriate adapter from the registry.
   b. Call `adapter.search_by_attorney(attorney_name, reg_number, county)`.
   c. For each result, check if the case is already tracked by this user.
   d. If new, insert a row into `discovered_cases` with status "pending".
   e. Create a notification alerting the user.
3. Return statistics (cases found, errors).

**Case resolution:**
- `accept_discovered_case(discovery_id, user_id)`: Creates a tracked case from the discovery, marks discovery as "accepted", and triggers an initial scrape.
- `dismiss_discovered_case(discovery_id, user_id)`: Marks the discovery as "dismissed".
- `get_pending_discoveries(user_id)`: Returns unresolved discoveries.
- `get_all_discoveries(user_id, status, limit)`: Returns discoveries with optional status filter.

**Weekly schedule:** Discovery runs every Monday at 7:00 AM ET via the scraper scheduler.

### 2.11 Court Adapters

#### 2.11.1 Base Interfaces (`app/adapters/base.py`)

**`CaseSource` enum:**
- `MANUAL`: User-entered data
- `WEBCIVIL_SCRAPER`: Scraped from NY WebCivil
- `WEBCRIMIN_SCRAPER`: Scraped from NY WebCriminal
- `ETRACK_EMAIL`: Parsed from eTrack email notifications
- `API_PROVIDER`: Received from an API provider

**`CourtAdapter` abstract class:**
```
Properties:
  court_system -> CourtSystem enum
  display_name -> str
  state -> str

Methods:
  search(params: SearchParams) -> list[CourtRecord]
  get_case_details(index_number, court_type, county) -> Optional[CourtRecord]
  get_appearances(index_number, court_type, county) -> list[AppearanceRecord]
  search_by_attorney(attorney_name, reg_number, county) -> list[CourtRecord]
  health_check() -> bool
```

**`SearchParams` dataclass:** index_number, plaintiff, defendant, county, court_type, case_year

**`CourtRecord` dataclass:** index_number, court_type, county, case_year, case_status, plaintiff, defendant, plaintiff_firm, defendant_firm, justice, part, last_action, last_action_date, appearances list

**`AppearanceRecord` dataclass:** appearance_date, appearance_time, appearance_type, location, notes

#### 2.11.2 Adapter Registry (`app/adapters/registry.py`)

- `get_adapter(court_system: str) -> CourtAdapter`: Returns the adapter instance for a given court system identifier.
- `list_adapters() -> list[dict]`: Returns metadata about all registered adapters.

Registered adapters:
- `ny_webcivil` -> `NYWebCivilAdapter`
- `ny_webcrimin` -> `NYWebCriminAdapter`

#### 2.11.3 NY WebCivil Adapter (`app/adapters/ny_webcivil.py`)

Scrapes the NY WebCivil system at `https://iapps.courts.state.ny.us/webcivil`.

**Capabilities:**
- Search by index number: Navigates to the case search page, submits the form, parses the results table.
- Search by party name: Searches by plaintiff or defendant name, returns matching cases.
- Search by attorney: Searches using attorney name and optional registration number.
- Get case details: Fetches the full case detail page, extracts parties, justice, part, status, and recent actions.
- Get appearances: Parses the appearances/calendar section of the case detail page.
- Health check: Verifies that the WebCivil site is accessible.

**HTML parsing:** Uses BeautifulSoup4 with lxml parser. The adapter contains detailed CSS/HTML selectors and regex patterns specific to the WebCivil page structure, including handling of session tokens and multi-step form submissions.

**Covers:** Supreme Court, Civil Court, and Housing Court cases.

#### 2.11.4 NY WebCriminal Adapter (`app/adapters/ny_webcrimin.py`)

Scrapes the NY WebCriminal system at `https://iapps.courts.state.ny.us/webcrimin`.

**Capabilities:**
- Same interface as NYWebCivilAdapter but targeting criminal court cases.
- Search by defendant name, index/docket number, or attorney.
- Get case details and appearances from criminal court pages.
- Health check for WebCriminal site availability.

**Covers:** Criminal Court cases across all NY counties.

---

## 3. Frontend Architecture

### 3.1 Project Structure

```
ny-court-tracker-mobile/
├── App.tsx                   # Root component: SafeAreaProvider > AuthProvider > AppNavigator
├── package.json              # Dependencies and scripts
├── index.ts                  # Entry point
├── src/
│   ├── navigation/
│   │   └── AppNavigator.tsx  # Tab navigation, stack navigators, auth flow
│   ├── context/
│   │   └── AuthContext.tsx    # Authentication state management
│   ├── services/
│   │   ├── api.ts            # Axios API client, all API calls, TypeScript interfaces
│   │   ├── storage.ts        # Platform-aware secure storage
│   │   └── pushNotifications.ts # Expo push notification registration and handling
│   └── screens/
│       ├── LoginScreen.tsx         # Sign in form
│       ├── RegisterScreen.tsx      # Account creation form
│       ├── DashboardScreen.tsx     # Upcoming appearances overview
│       ├── CasesScreen.tsx         # Case list with filters
│       ├── CaseDetailScreen.tsx    # Individual case view with appearances
│       ├── CaseFormScreen.tsx      # Add/edit case form with court search
│       ├── CalendarScreen.tsx      # Monthly calendar view
│       ├── NotificationsScreen.tsx # Notification center
│       ├── SettingsScreen.tsx      # Preferences and configuration
│       ├── DiscoveriesScreen.tsx   # Discovered cases from weekly scans
│       └── EmailSetupScreen.tsx    # Email integration setup wizard
```

### 3.2 Navigation

**File**: `src/navigation/AppNavigator.tsx`

The app uses React Navigation 7 with a conditional navigation structure:

```
AppNavigator
├── If NOT authenticated:
│   └── AuthStack (NativeStackNavigator)
│       ├── Login -> LoginScreen
│       └── Register -> RegisterScreen
│
└── If authenticated:
    └── MainTabs (BottomTabNavigator)
        ├── Dashboard -> DashboardScreen
        ├── CasesTab -> CasesStackNavigator
        │   ├── CasesList -> CasesScreen
        │   ├── CaseDetail -> CaseDetailScreen
        │   └── CaseForm -> CaseFormScreen
        ├── Calendar -> CalendarScreen
        ├── Notifications -> NotificationsScreen (with unread badge)
        └── Settings -> SettingsStackNavigator
            ├── SettingsMain -> SettingsScreen
            ├── EmailSetup -> EmailSetupScreen
            └── Discoveries -> DiscoveriesScreen
```

**Tab bar features:**
- Icons from Ionicons (filled when active, outlined when inactive).
- Notification badge shows unread count (polled every 60 seconds).
- Push notification registration occurs on MainTabs mount.
- Notification tap handler navigates to the relevant case or notifications tab.

### 3.3 Screens

#### 3.3.1 LoginScreen

- Email and password input fields with validation.
- Password visibility toggle (show/hide).
- "Sign In" button with loading spinner.
- Link to RegisterScreen ("Don't have an account? Create one").
- Calls `authApi.login()`, then `AuthContext.login()` to store token.

#### 3.3.2 RegisterScreen

- Form fields: First Name*, Last Name*, Email*, Attorney Registration Number (optional), Password* (min 7 chars), Confirm Password*.
- Client-side validation for required fields, password length, and password match.
- Calls `authApi.register()`, auto-logs in on success.
- Link to LoginScreen ("Already have an account? Sign in").

#### 3.3.3 DashboardScreen

The main landing screen showing upcoming court appearances.

**Features:**
- **Summary stats cards**: Today's count, This Week's count, High Priority count (with colored left borders).
- **Priority filter chips**: All, High Priority, Normal (toggle filters).
- **Appearances grouped by date**: Each date group shows:
  - Day label ("Today", "Tomorrow", "In 3 days", or formatted date).
  - Appearance cards with:
    - Court type badge (color-coded: blue=Supreme, green=Local Civil, red=Criminal).
    - Priority flag badge ("HIGH" with red flag icon).
    - Index number and county.
    - Party names (plaintiff v. defendant).
    - Freshness indicator (green/yellow/red dot with "Xh ago" text and source).
    - Time, location, and justice/part info.
- **Empty state**: Calendar icon with "No Upcoming Appearances" message and "Add Your First Case" button.
- **Pull-to-refresh**: Refreshes dashboard data.
- **Navigation**: Tapping an appearance navigates to CaseDetail.

**Data freshness colors:**
- Green (fresh): Checked less than 6 hours ago
- Yellow (stale): Checked less than 24 hours ago
- Red (outdated): Checked more than 24 hours ago
- Gray (unknown): Never checked

#### 3.3.4 CasesScreen

List of all tracked cases.

**Features:**
- **Header**: "My Cases" title with case count and "Add" button.
- **Horizontal filter chips**: All, High Priority, Manual, eTrack Email.
- **Case cards** showing:
  - Court type badge, status badge (active/pending/disposed), priority flag.
  - Index number with year.
  - County, party names, justice/part.
  - Next appearance date (if any).
  - Freshness indicator, source label, verified badge.
- **Empty state**: "No Cases Yet" with "Add Case" button.
- **Pull-to-refresh** and **FlatList** for efficient rendering.
- **Navigation**: Tapping a case navigates to CaseDetail.

#### 3.3.5 CaseDetailScreen

Detailed view of a single case with all related data.

**Sections:**
1. **Action buttons**: Edit (navigates to CaseForm) and Delete (with confirmation dialog).
2. **Case info card**: Court type badge, status badge, index number, county, justice, part, parties with firms, notes.
3. **Tracking info card**:
   - Priority level with flag icon.
   - Source label.
   - Verified status with checkmark.
   - Freshness bar with colored dot and last-checked time.
   - "Check for Updates Now" button (triggers manual scrape via `scraperApi.triggerManual()`).
4. **Notification preferences card**: Per-case push and email notification toggles (overrides global settings).
5. **Scheduled appearances**: List of appearances with date, time, type, location, notes. Past appearances are dimmed with "Past" badge. Each has a delete button. "Add" button opens a modal form for new appearances.
6. **Add appearance modal**: Date, time, type, location, and notes fields.

#### 3.3.6 CaseFormScreen

Add or edit a case with optional court system verification.

**Two modes:**
- **Add mode**: Full form with "Search & Verify Case" button.
- **Edit mode**: Pre-populated form without search capability.

**Form fields:**
- Court Type picker (Civil Supreme, Local Civil, Criminal).
- County picker (all 62 NY counties).
- Index Number and Year.
- Status picker (Active, Pending, Disposed).
- Priority picker (Normal: "Updated 2x/day", High: "Updated every 2-4 hours").
- Parties section: Plaintiff, Defendant, Plaintiff Firm, Defendant Firm.
- Justice, Part, Notes.

**Search & Verify flow (add mode only):**
1. User enters index number and county, taps "Search & Verify Case".
2. App calls `casesApi.search()` with the appropriate court system.
3. Results are displayed as selectable cards showing case details.
4. User selects a result, form auto-fills with verified data.
5. "Track This Case" button calls `casesApi.verify()` to create a verified case.
6. Alternatively, user can go "Back to Form" to edit details manually.

#### 3.3.7 CalendarScreen

Monthly calendar view of court appearances.

**Features:**
- **Month navigation**: Previous/next month arrows with month/year label.
- **Calendar grid**: 7-column grid with day-of-week headers, numbered day cells.
  - Today highlighted in dark.
  - Selected day highlighted in blue.
  - Color-coded dots under days with appearances (up to 3 dots per day).
  - Dot colors match court types (blue=Supreme, green=Civil, red=Criminal).
- **Legend**: Color key for court types below the calendar.
- **Appearances list**: Below the calendar, shows appearances for the selected day or the entire month.
  - Clicking "Show all" clears the day filter.
  - Each appearance card shows day number, day-of-week, court badge, index number, county, time, and type.
  - Tapping navigates to CaseDetail.
- **Data source**: Uses `dashboardApi.calendar()` filtered by month/year.

#### 3.3.8 NotificationsScreen

Notification center for all alerts and reminders.

**Features:**
- **Header**: "Notifications" title with unread count, "Mark All Read" button, and "Clear All" button.
- **Filter chips**: All, Unread, Reminders, Updates, System.
- **Notification cards**:
  - Type-specific icon (alarm for reminders, document for updates, info for system).
  - Unread notifications have blue background and bold title with blue dot.
  - Title, message (2 lines max), timestamp (relative: "5m ago", "2h ago", "3d ago").
  - Type badge (colored label).
  - Push sent indicator (phone icon).
- **Interactions**:
  - Tap: Marks as read and navigates to related case (if case_id present).
  - Long press: Context menu with "Mark as Read" and "Delete" options.
- **Empty state**: "No Notifications" / "No Matching Notifications" with appropriate message.
- **Pull-to-refresh**.

#### 3.3.9 SettingsScreen

User preferences and configuration hub.

**Sections:**
1. **Account Information**: Name, email, attorney registration number, member since date.
2. **Push Notifications**:
   - Push notifications toggle (on/off).
   - Case updates toggle.
   - Appearance reminder window picker (1, 7, 15, or 30 days before).
3. **Email & Digest**:
   - Email notifications toggle.
   - Digest frequency picker (Off, Daily, Weekly).
   - Court email integration status (green=verified, yellow=pending, gray=not connected).
   - "Set Up Email Integration" / "Manage Email Integration" button -> navigates to EmailSetupScreen.
4. **Weekly Case Discovery**:
   - Enable/disable toggle ("Scan every Monday at 7am ET").
   - Attorney name and registration number display.
   - Courts being searched.
   - Last scan timestamp.
   - "View Discovered Cases" button -> navigates to DiscoveriesScreen.
5. **Sign Out**: Red sign-out button with confirmation dialog.

#### 3.3.10 EmailSetupScreen

Step-by-step email integration setup wizard.

**States:**
- **Not set up**: "How It Works" explainer (3 steps: Set Up Forwarding, Automatic Parsing, Real-Time Updates) with "Set Up Email Integration" button.
- **Set up, not verified**: Shows unique forwarding email with copy button, "Mark as Verified" button.
- **Set up and verified**: Shows "Connected & Verified" status with green indicator.

**Tab navigation** (visible when email is configured):
- **Steps**: Setup steps checklist with completion indicators.
- **Gmail**: Gmail-specific forwarding instructions.
- **Outlook**: Outlook-specific forwarding instructions.
- **Activity**: Recent email processing log showing subject, events extracted, and date.

**Additional features:**
- Privacy notice card: "We only parse court notification emails. All other emails are automatically discarded."
- "Disconnect Email Integration" button with confirmation dialog.
- Copy-to-clipboard for the forwarding email address.

#### 3.3.11 DiscoveriesScreen

View and act on automatically discovered cases.

**Features:**
- **Header**: "Case Discovery" title with pending count and "Scan Now" button.
- **Filter chips**: Pending, All, Accepted, Dismissed.
- **Discovery cards**:
  - Status badge (yellow=Pending, green=Accepted, gray=Dismissed) with discovery date.
  - Case number, party names, court system, county, court type.
  - Last action (if available).
  - **Pending cards**: "Track This Case" (accept) and "Dismiss" action buttons with confirmation.
- **Empty state**: "No New Cases Found" with "Scan Now" button and explanation text.
- **Pull-to-refresh**.

### 3.4 Services

#### 3.4.1 API Client (`src/services/api.ts`)

Centralized Axios-based API client.

**Configuration:**
- Base URL: `https://app-ujjdvsxl.fly.dev` (configurable via `setApiUrl()`).
- Request interceptor: Automatically attaches `Authorization: Bearer <token>` header from secure storage.

**API modules** (exported as named objects):
- `authApi`: register, login, me
- `casesApi`: list, get, create, update, delete, search, verify, getEvents, getFreshness, updatePriority
- `appearancesApi`: list, create, update, delete
- `dashboardApi`: get, calendar
- `courtConfigsApi`: list, adapters
- `scraperApi`: getStatus, triggerManual, getHistory, triggerBatch
- `emailApi`: setup, getConfig, verify, deleteConfig, getSetupGuide, getLog, testWebhook
- `discoveryApi`: getSettings, updateSettings, list, getPendingCount, accept, dismiss, trigger
- `notificationsApi`: getSettings, updateSettings, list, markRead, markAllRead, deleteNotification, clearAll, getUnreadCount, registerPushToken, unregisterPushToken, getCasePrefs, updateCasePrefs, triggerChecks

**TypeScript interfaces**: The file defines comprehensive TypeScript interfaces for all API types (User, Case, Appearance, DashboardAppearance, CaseSearchResult, CourtConfig, CaseEvent, NotificationSettings, NotificationItem, PushTokenData, CaseNotificationPrefs, ScrapeJobResponse, ScraperStatusResponse, EmailSetupResponse, EmailConfigResponse, DiscoverySettings, DiscoveredCase, etc.).

#### 3.4.2 Storage Service (`src/services/storage.ts`)

Platform-aware key-value storage abstraction.

- **Native (iOS/Android)**: Uses `expo-secure-store` for encrypted storage.
- **Web**: Uses `localStorage` as a fallback.
- **API**: `getItem(key)`, `setItem(key, value)`, `deleteItem(key)`.
- **Used for**: Storing JWT token and user object.

#### 3.4.3 Push Notifications Service (`src/services/pushNotifications.ts`)

Expo push notification integration.

**Functions:**
- `registerForPushNotifications()`: Checks permissions, requests if needed, gets Expo push token, registers with backend, sets up Android notification channels ("default", "court-reminders", "case-updates").
- `unregisterPushToken(token)`: Removes token from backend.
- `setupNotificationResponseListener(callback)`: Handles notification tap events (navigates to relevant case).
- `setupNotificationReceivedListener(callback)`: Handles foreground notification display.
- `getBadgeCount()` / `setBadgeCount(count)`: Manage app icon badge.

**Foreground notification config**: Shows alerts, plays sound, sets badge, shows banner and list entry.

### 3.5 Context

#### AuthContext (`src/context/AuthContext.tsx`)

React Context for authentication state management.

**State:**
- `user: User | null` - Current authenticated user.
- `token: string | null` - JWT token.
- `loading: boolean` - True during initial auth check.

**Behavior on app launch:**
1. Reads stored token and user from secure storage.
2. If found, sets them in state and validates the token by calling `authApi.me()`.
3. If validation fails (expired/invalid token), clears stored credentials and sets user to null.
4. Sets `loading = false` when complete.

**Functions:**
- `login(token, user)`: Stores credentials in secure storage and sets state.
- `logout()`: Clears credentials from storage and state (triggers navigation to auth stack).

### 3.6 Key UI Patterns

**Loading States:**
- Full-screen `ActivityIndicator` (centered, dark color) shown while data is loading.
- Inline `ActivityIndicator` used for buttons during save/submit operations.
- Button disabled state with reduced opacity (0.6) during loading.

**Error States:**
- `Alert.alert()` for error messages (native alert on mobile, web polyfill).
- Console errors logged for debugging.
- Graceful fallbacks (empty arrays, null states) when API calls fail.

**Pull-to-Refresh:**
- `RefreshControl` component on `ScrollView` and `FlatList` components.
- Separate `refreshing` state from initial `loading` state.
- Data refetched on pull with `isRefresh` flag to control loading indicator.

**Focus-based Data Refresh:**
- `useFocusEffect()` from React Navigation triggers data refetch when a screen gains focus.
- Ensures data is fresh when navigating between tabs or returning from detail screens.

**Filter Chips:**
- Horizontally scrollable chip/pill buttons for filtering data.
- Active chip has dark background with white text; inactive has light border.
- Tapping an active chip deselects it (toggles back to "All").

**Color System:**
- Court types: Blue (#3b82f6) = Supreme, Green (#10b981) = Local Civil, Red (#ef4444) = Criminal.
- Status: Green = Active, Yellow (#f59e0b) = Pending, Gray (#6b7280) = Disposed.
- Freshness: Green = Fresh, Yellow = Stale, Red = Outdated, Gray = Unknown.
- Priority: Red flag icon and badge for high priority.

**Card-based Layout:**
- White cards with subtle shadow (0.04 opacity), rounded corners (10-12px radius).
- Cards separated by 8-12px margins.
- Consistent padding (14-16px internal).

---

## 4. Data Flow Diagrams

### 4.1 User Registration / Login Flow

```
User                    Frontend                   Backend                  Database
  |                        |                          |                        |
  |-- Fill form ---------->|                          |                        |
  |                        |-- POST /api/auth/register|                        |
  |                        |     or /api/auth/login ->|                        |
  |                        |                          |-- Hash password (bcrypt)|
  |                        |                          |-- INSERT user -------->|
  |                        |                          |-- INSERT notification  |
  |                        |                          |   settings ----------->|
  |                        |                          |-- INSERT discovery     |
  |                        |                          |   settings ----------->|
  |                        |                          |-- Generate JWT ------->|
  |                        |<-- { token, user } ------|                        |
  |                        |                          |                        |
  |                        |-- Store token in ------->|                        |
  |                        |   SecureStore/localStorage                        |
  |                        |                          |                        |
  |                        |-- Set AuthContext ------->|                        |
  |                        |   (user, token)          |                        |
  |                        |                          |                        |
  |<-- Navigate to --------|                          |                        |
  |   MainTabs (Dashboard) |                          |                        |
  |                        |                          |                        |
  |                        |-- Register push token -->|                        |
  |                        |   POST /api/notifications|                        |
  |                        |        /push-token       |-- INSERT push_tokens ->|
```

### 4.2 Adding a Case Manually

```
User                    Frontend                   Backend                  Database
  |                        |                          |                        |
  |-- Open CaseForm ------>|                          |                        |
  |-- Fill in details ---->|                          |                        |
  |                        |                          |                        |
  |-- (Optional) Tap ----->|                          |                        |
  |   "Search & Verify"   |                          |                        |
  |                        |-- POST /api/cases/search->|                       |
  |                        |                          |-- Get adapter -------->|
  |                        |                          |-- adapter.search() --->| Court Website
  |                        |                          |<-- CourtRecord[] ------|
  |                        |<-- { results, message } -|                        |
  |                        |                          |                        |
  |-- Select a result ---->|                          |                        |
  |   (auto-fills form)    |                          |                        |
  |                        |                          |                        |
  |-- Tap "Track This ---->|                          |                        |
  |   Case" or "Save"     |                          |                        |
  |                        |-- POST /api/cases/verify -|                       |
  |                        |   or POST /api/cases     |                        |
  |                        |                          |-- INSERT case -------->|
  |                        |                          |-- Set verified=true -->|
  |                        |                          |-- Trigger initial ---->|
  |                        |                          |   scrape (background)  |
  |                        |                          |   adapter.get_appearances()
  |                        |                          |-- INSERT appearances ->|
  |                        |<-- CaseOut --------------|                        |
  |                        |                          |                        |
  |<-- Navigate back ------|                          |                        |
  |   to CasesList         |                          |                        |
```

### 4.3 Email Forwarding Flow

```
Court System          User's Gmail          Email Service         Backend              Database
     |                     |                    (Mailgun/           |                     |
     |                     |                    SendGrid)           |                     |
     |-- eTrack email ---->|                       |                |                     |
     |   notification      |                       |                |                     |
     |                     |-- Auto-forward to --->|                |                     |
     |                     |  case-{hash}@domain   |                |                     |
     |                     |                       |                |                     |
     |                     |                       |-- POST ------->|                     |
     |                     |                       |   /api/email/  |                     |
     |                     |                       |   webhook/     |                     |
     |                     |                       |   {provider}   |                     |
     |                     |                       |                |                     |
     |                     |                       |                |-- Lookup user by    |
     |                     |                       |                |   inbound email --->|
     |                     |                       |                |                     |
     |                     |                       |                |-- parse_email() --->|
     |                     |                       |                |   Extract events    |
     |                     |                       |                |                     |
     |                     |                       |                |-- For each event:   |
     |                     |                       |                |   find_matching_case |
     |                     |                       |                |   is_duplicate_event |
     |                     |                       |                |   reconcile_event    |
     |                     |                       |                |                     |
     |                     |                       |                |-- Upsert case ----->|
     |                     |                       |                |-- Upsert appearance>|
     |                     |                       |                |-- Insert event ---->|
     |                     |                       |                |-- Update last_      |
     |                     |                       |                |   checked_at ------>|
     |                     |                       |                |                     |
     |                     |                       |                |-- Create            |
     |                     |                       |                |   notification ---->|
     |                     |                       |                |-- Send push ------->|
     |                     |                       |                |   (Expo API)        |
     |                     |                       |                |                     |
     |                     |                       |                |-- Log email ------->|
     |                     |                       |                |   (email_log)       |
```

### 4.4 Scraper Flow

```
APScheduler                Backend                   Court Website            Database
     |                        |                          |                       |
     |-- Cron trigger ------->|                          |                       |
     |   (e.g. 6am ET)       |                          |                       |
     |                        |                          |                       |
     |                        |-- Query cases by ------->|                       |
     |                        |   priority               |<-- case list --------|
     |                        |                          |                       |
     |                        |-- For each case:         |                       |
     |                        |   get_adapter(court_sys) |                       |
     |                        |                          |                       |
     |                        |-- adapter.get_case_ ---->|                       |
     |                        |   details()              |                       |
     |                        |                          |-- HTTP GET ---------->|
     |                        |                          |   (with user-agent   Court
     |                        |                          |    rotation, rate    Website
     |                        |                          |    limiting)          |
     |                        |                          |<-- HTML response ----|
     |                        |                          |                       |
     |                        |-- adapter.get_ --------->|                       |
     |                        |   appearances()          |                       |
     |                        |                          |<-- Parsed results ---|
     |                        |                          |                       |
     |                        |-- Update case ---------->|                       |
     |                        |   last_checked_at,       |                       |
     |                        |   last_source            |                       |
     |                        |                          |                       |
     |                        |-- Upsert appearances --->|                       |
     |                        |   (email data wins over  |                       |
     |                        |    scraper data)         |                       |
     |                        |                          |                       |
     |                        |-- Record scrape_job ---->|                       |
     |                        |   (status, timing)       |                       |
     |                        |                          |                       |
     |                        |-- If changes detected:   |                       |
     |                        |   create_notification -->|                       |
     |                        |   send_push ------------>|                       |
```

### 4.5 Notification Flow

```
APScheduler                Backend                   Expo Push API            Database
     |                        |                          |                       |
     |== Daily at 7am ET ====>|                          |                       |
     |  check_appearance_     |                          |                       |
     |  reminders()           |                          |                       |
     |                        |-- Query appearances ---->|                       |
     |                        |   within reminder window |<-- appearance list --|
     |                        |                          |                       |
     |                        |-- For each upcoming:     |                       |
     |                        |   Check user settings -->|                       |
     |                        |   Check case prefs ----->|                       |
     |                        |                          |                       |
     |                        |-- INSERT notification -->|                       |
     |                        |                          |                       |
     |                        |-- If push_enabled:       |                       |
     |                        |   Get push tokens ------>|                       |
     |                        |   POST to Expo API ----->|                       |
     |                        |                          |-- Deliver to device  |
     |                        |                          |                       |
     |== Daily at 7:15am ===>|                          |                       |
     |  check_auto_priority_  |                          |                       |
     |  escalation()          |                          |                       |
     |                        |-- Find normal-priority   |                       |
     |                        |   cases with court date  |                       |
     |                        |   within 7 days -------->|                       |
     |                        |-- UPDATE priority=high ->|                       |
     |                        |-- Notify user ---------->|                       |
     |                        |                          |                       |
     |== Every 6 hours =====>|                          |                       |
     |  check_stale_cases()   |                          |                       |
     |                        |-- Find cases not checked |                       |
     |                        |   (high: >8h, normal:    |                       |
     |                        |    >48h) --------------->|                       |
     |                        |-- Notify user ---------->|                       |
     |                        |                          |                       |
     |== Daily at 8am ET ===>|                          |                       |
     |  generate_daily_       |                          |                       |
     |  digest()              |                          |                       |
     |                        |-- Aggregate today's      |                       |
     |                        |   appearances + recent   |                       |
     |                        |   activity ------------->|                       |
     |                        |-- Send digest email ---->|                       |
     |                        |                          |                       |
     |== Monday 8am ET =====>|                          |                       |
     |  generate_weekly_      |                          |                       |
     |  digest()              |                          |                       |
     |                        |-- Aggregate week's data->|                       |
     |                        |-- Send weekly summary -->|                       |
```

### 4.6 Weekly Discovery Flow

```
APScheduler                Backend                   Court Adapters           Database
     |                        |                          |                       |
     |== Monday 7am ET =====>|                          |                       |
     |  run_weekly_discovery()|                          |                       |
     |                        |                          |                       |
     |                        |-- Query users with ------>|                      |
     |                        |   discovery enabled       |<-- user list -------|
     |                        |                          |                       |
     |                        |-- For each user:         |                       |
     |                        |   Load discovery settings |                      |
     |                        |   (attorney_name, courts) |                      |
     |                        |                          |                       |
     |                        |-- For each court system: |                       |
     |                        |   get_adapter()          |                       |
     |                        |   adapter.search_by_ --->|                       |
     |                        |   attorney()             |-- Scrape court ----->|
     |                        |                          |   website            Court
     |                        |                          |<-- CourtRecord[] ----|Website
     |                        |                          |                       |
     |                        |-- For each result:       |                       |
     |                        |   Check if already ------>|                      |
     |                        |   tracked                 |<-- existing case? --|
     |                        |                          |                       |
     |                        |-- If new case:           |                       |
     |                        |   INSERT discovered_ ---->|                      |
     |                        |   cases (status=pending)  |                      |
     |                        |                          |                       |
     |                        |   Create notification --->|                      |
     |                        |   "New case found"        |                      |
     |                        |   Send push ------------->|                      |
     |                        |                          |                       |
     |              Later...  |                          |                       |
     |                        |                          |                       |
  User -- Accept ------------->|                         |                       |
     |                        |-- POST /api/discovery/   |                       |
     |                        |   {id}/accept            |                       |
     |                        |-- INSERT case ---------->|                       |
     |                        |-- UPDATE discovered_case |                       |
     |                        |   status=accepted ------>|                       |
     |                        |-- Trigger initial scrape |                       |
```

---

## 5. API Reference

All endpoints require authentication via `Authorization: Bearer <token>` header unless noted otherwise.

### 5.1 Authentication

| Method | Path | Auth | Request Body | Response | Description |
|--------|------|------|-------------|----------|-------------|
| POST | `/api/auth/register` | No | `{ email, password, first_name, last_name, attorney_reg_number? }` | `{ access_token, token_type, user }` | Register new account |
| POST | `/api/auth/login` | No | `{ email, password }` | `{ access_token, token_type, user }` | Login and get token |
| GET | `/api/auth/me` | Yes | - | `{ id, email, first_name, last_name, attorney_reg_number, created_at }` | Get current user |

### 5.2 Cases

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/cases` | Yes | Query: `court_type`, `county`, `status`, `priority`, `source`, `verified`, `sort_by` | `Case[]` | List user's cases |
| POST | `/api/cases` | Yes | `{ court_type, county, index_number, case_year?, case_status, priority?, plaintiff?, defendant?, plaintiff_firm?, defendant_firm?, justice?, part?, notes? }` | `Case` | Create case manually |
| POST | `/api/cases/search` | Yes | `{ index_number, court_type, county, court_system? }` | `{ results: CaseSearchResult[], court_system, message }` | Search court system |
| POST | `/api/cases/verify` | Yes | `{ court_type, county, index_number, ... court_system, search_params }` | `Case` | Create verified case |
| GET | `/api/cases/{id}` | Yes | - | `Case` | Get case by ID |
| GET | `/api/cases/{id}/events` | Yes | - | `CaseEvent[]` | Get case events |
| GET | `/api/cases/{id}/freshness` | Yes | - | `{ last_checked_at, last_source, hours_since_check, status }` | Get freshness info |
| PUT | `/api/cases/{id}/priority` | Yes | Query: `priority` | `Case` | Update priority |
| PUT | `/api/cases/{id}` | Yes | Partial case fields | `Case` | Update case |
| DELETE | `/api/cases/{id}` | Yes | - | `{ status: "deleted" }` | Delete case |

### 5.3 Appearances

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/cases/{case_id}/appearances` | Yes | - | `Appearance[]` | List appearances |
| POST | `/api/cases/{case_id}/appearances` | Yes | `{ appearance_date, appearance_time?, appearance_type?, location?, notes? }` | `Appearance` | Add appearance |
| PUT | `/api/appearances/{id}` | Yes | Partial appearance fields | `Appearance` | Update appearance |
| DELETE | `/api/appearances/{id}` | Yes | - | `{ status: "deleted" }` | Delete appearance |

### 5.4 Dashboard

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/dashboard` | Yes | Query: `court_type`, `county`, `priority`, `source`, `days_ahead` (default 90) | `DashboardAppearance[]` | Upcoming appearances |
| GET | `/api/dashboard/calendar` | Yes | Query: `month`, `year` | `DashboardAppearance[]` | Monthly appearances |

### 5.5 Notifications

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/notifications/settings` | Yes | - | `NotificationSettings` | Get notification settings |
| PUT | `/api/notifications/settings` | Yes | `{ email_enabled?, push_enabled?, reminder_days?, case_updates_enabled?, digest_frequency?, digest_time? }` | `NotificationSettings` | Update settings |
| GET | `/api/notifications` | Yes | Query: `notification_type`, `unread_only`, `limit` | `NotificationItem[]` | List notifications |
| GET | `/api/notifications/unread-count` | Yes | - | `{ count: number }` | Unread count |
| PUT | `/api/notifications/{id}/read` | Yes | - | `{ status: "read" }` | Mark as read |
| PUT | `/api/notifications/read-all` | Yes | - | `{ status: "all_read" }` | Mark all read |
| DELETE | `/api/notifications/{id}` | Yes | - | `{ status: "deleted" }` | Delete notification |
| DELETE | `/api/notifications` | Yes | - | `{ status: "cleared" }` | Clear all |
| POST | `/api/notifications/push-token` | Yes | `{ token, device_name?, platform? }` | `{ status: "registered" }` | Register push token |
| DELETE | `/api/notifications/push-token` | Yes | Query: `token` | `{ status: "unregistered" }` | Remove push token |
| GET | `/api/notifications/push-tokens` | Yes | - | `PushToken[]` | List push tokens |
| GET | `/api/notifications/case/{case_id}/prefs` | Yes | - | `CaseNotificationPrefs` | Get per-case prefs |
| PUT | `/api/notifications/case/{case_id}/prefs` | Yes | `{ push_enabled?, email_enabled?, priority_override? }` | `CaseNotificationPrefs` | Update per-case prefs |
| POST | `/api/notifications/trigger-checks` | Yes | - | `{ status: "triggered" }` | Trigger checks (test) |

### 5.6 Scraper

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/scraper/status` | Yes | - | `{ scheduler_running, jobs[], total_scrape_jobs, recent_failures }` | Scheduler status |
| POST | `/api/scraper/trigger-manual` | Yes | `{ case_id }` | `{ status, case_id, last_action, error_message }` | Manual scrape |
| GET | `/api/scraper/history/{case_id}` | Yes | Query: `limit` (default 20) | `ScrapeJob[]` | Scrape history |
| POST | `/api/scraper/trigger-batch` | Yes | Query: `priority` | `{ status, count }` | Batch scrape |

### 5.7 Email Integration

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| POST | `/api/email/setup` | Yes | - | `{ inbound_email, forwarding_verified, provider, already_setup }` | Generate inbound email |
| GET | `/api/email/config` | Yes | - | `{ id, user_id, inbound_email, forwarding_verified, provider, created_at }` | Get email config |
| POST | `/api/email/verify` | Yes | - | `{ verified, inbound_email }` | Mark as verified |
| DELETE | `/api/email/config` | Yes | - | `{ status: "deleted" }` | Remove integration |
| GET | `/api/email/setup-guide` | Yes | - | `{ inbound_email, forwarding_verified, steps[], gmail_instructions, outlook_instructions, privacy_note }` | Setup guide |
| GET | `/api/email/log` | Yes | Query: `limit` (default 20) | `EmailLogEntry[]` | Email log |
| POST | `/api/email/webhook/sendgrid` | No | SendGrid multipart form | `{ status: "processed" }` | SendGrid webhook |
| POST | `/api/email/webhook/mailgun` | No | Mailgun multipart form | `{ status: "processed" }` | Mailgun webhook |
| POST | `/api/email/webhook/test` | Yes | Query: `sender?`, `subject?`, `text` | `{ status: "processed" }` | Test webhook |

### 5.8 Discovery

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/discovery/settings` | Yes | - | `DiscoverySettings` | Get settings |
| PUT | `/api/discovery/settings` | Yes | `{ enabled?, attorney_name?, attorney_reg_number?, search_courts?, search_county? }` | `DiscoverySettings` | Update settings |
| GET | `/api/discovery` | Yes | Query: `status`, `limit` | `DiscoveredCase[]` | List discoveries |
| GET | `/api/discovery/pending-count` | Yes | - | `{ count: number }` | Pending count |
| POST | `/api/discovery/{id}/accept` | Yes | - | `{ status, case_id, message }` | Accept discovery |
| POST | `/api/discovery/{id}/dismiss` | Yes | - | `{ status, message }` | Dismiss discovery |
| POST | `/api/discovery/trigger` | Yes | - | `{ users_checked, total_discoveries, errors }` | Trigger scan |

### 5.9 Court Configs

| Method | Path | Auth | Request/Params | Response | Description |
|--------|------|------|---------------|----------|-------------|
| GET | `/api/court-configs` | Yes | - | `CourtConfig[]` | List configurations |
| GET | `/api/court-configs/adapters` | Yes | - | `AdapterInfo[]` | List adapters |

---

## 6. Database Schema

### 6.1 Tables

#### `users`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | User ID |
| email | TEXT | UNIQUE NOT NULL | Email address |
| password_hash | TEXT | NOT NULL | bcrypt-hashed password |
| first_name | TEXT | NOT NULL | First name |
| last_name | TEXT | NOT NULL | Last name |
| attorney_reg_number | TEXT | | NY attorney registration number |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation time |

#### `cases`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Case ID |
| user_id | INTEGER | NOT NULL, FK -> users.id | Owning user |
| court_type | TEXT | NOT NULL | supreme, local_civil, criminal |
| county | TEXT | NOT NULL | NY county name |
| index_number | TEXT | NOT NULL | Court index/docket number |
| case_year | INTEGER | | Filing year |
| case_status | TEXT | DEFAULT 'active' | active, pending, disposed |
| plaintiff | TEXT | | Plaintiff name |
| defendant | TEXT | | Defendant name |
| plaintiff_firm | TEXT | | Plaintiff's law firm |
| defendant_firm | TEXT | | Defendant's law firm |
| justice | TEXT | | Assigned justice |
| part | TEXT | | Court part |
| notes | TEXT | | User notes |
| priority | TEXT | DEFAULT 'normal' | normal or high |
| source | TEXT | DEFAULT 'manual' | Case source (manual, webcivil_scraper, etc.) |
| last_checked_at | TIMESTAMP | | Last scrape/email check time |
| last_source | TEXT | | Source of last update |
| court_system | TEXT | | Court system identifier |
| verified | BOOLEAN | DEFAULT 0 | Whether case was verified against court records |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

#### `appearances`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Appearance ID |
| case_id | INTEGER | NOT NULL, FK -> cases.id | Parent case |
| appearance_date | TEXT | NOT NULL | Date (YYYY-MM-DD) |
| appearance_time | TEXT | | Time string |
| appearance_type | TEXT | | Type of appearance |
| location | TEXT | | Courtroom/location |
| notes | TEXT | | Notes |
| source | TEXT | DEFAULT 'manual' | Data source |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

#### `case_events`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Event ID |
| case_id | INTEGER | NOT NULL, FK -> cases.id | Parent case |
| event_type | TEXT | NOT NULL | filing, appearance_scheduled, decision, etc. |
| event_date | TEXT | | Date of the event |
| description | TEXT | | Event description |
| source | TEXT | NOT NULL | Data source |
| raw_data | TEXT | | Raw source data (JSON) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `court_configs`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Config ID |
| state | TEXT | NOT NULL | State (e.g., "NY") |
| court_system | TEXT | NOT NULL UNIQUE | System identifier (ny_webcivil, ny_webcrimin) |
| display_name | TEXT | NOT NULL | Human-readable name |
| base_url | TEXT | | Court website URL |
| adapter_class | TEXT | NOT NULL | Python class name |
| enabled | BOOLEAN | DEFAULT 1 | Whether adapter is active |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `scrape_jobs`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Job ID |
| case_id | INTEGER | NOT NULL, FK -> cases.id | Target case |
| court_system | TEXT | NOT NULL | Court system scraped |
| status | TEXT | NOT NULL | pending, running, success, failed, skipped |
| scheduled_at | TIMESTAMP | | Scheduled run time |
| started_at | TIMESTAMP | | Actual start time |
| completed_at | TIMESTAMP | | Completion time |
| result | TEXT | | Result summary |
| error_message | TEXT | | Error details (if failed) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `email_configs`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Config ID |
| user_id | INTEGER | NOT NULL UNIQUE, FK -> users.id | Owning user |
| inbound_email | TEXT | NOT NULL UNIQUE | Generated forwarding address |
| forwarding_verified | BOOLEAN | DEFAULT 0 | Whether forwarding is verified |
| provider | TEXT | | Email provider (sendgrid, mailgun) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `email_log`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Log ID |
| user_id | INTEGER | NOT NULL, FK -> users.id | Recipient user |
| sender | TEXT | | Email sender address |
| subject | TEXT | | Email subject line |
| events_extracted | INTEGER | DEFAULT 0 | Number of events parsed |
| is_court_notification | BOOLEAN | DEFAULT 0 | Whether email was a court notification |
| received_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When email was received |

#### `notification_settings`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Settings ID |
| user_id | INTEGER | NOT NULL UNIQUE, FK -> users.id | Owning user |
| email_enabled | BOOLEAN | DEFAULT 0 | Email notifications on/off |
| push_enabled | BOOLEAN | DEFAULT 1 | Push notifications on/off |
| reminder_days | INTEGER | DEFAULT 1 | Days before appearance to remind |
| case_updates_enabled | BOOLEAN | DEFAULT 1 | Case change notifications on/off |
| digest_frequency | TEXT | DEFAULT 'off' | off, daily, weekly |
| digest_time | TEXT | DEFAULT '08:00' | Time to send digests |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `notifications`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Notification ID |
| user_id | INTEGER | NOT NULL, FK -> users.id | Recipient user |
| case_id | INTEGER | FK -> cases.id | Related case (optional) |
| appearance_id | INTEGER | FK -> appearances.id | Related appearance (optional) |
| type | TEXT | NOT NULL | reminder, update, system |
| title | TEXT | NOT NULL | Notification title |
| message | TEXT | NOT NULL | Notification body |
| read | BOOLEAN | DEFAULT 0 | Read status |
| push_sent | BOOLEAN | DEFAULT 0 | Whether push was sent |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `push_tokens`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Token ID |
| user_id | INTEGER | NOT NULL, FK -> users.id | Owning user |
| token | TEXT | NOT NULL UNIQUE | Expo push token |
| device_name | TEXT | | Device model name |
| platform | TEXT | | ios, android, web |
| active | BOOLEAN | DEFAULT 1 | Whether token is active |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration time |

#### `case_notification_prefs`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Pref ID |
| case_id | INTEGER | NOT NULL, FK -> cases.id | Case |
| user_id | INTEGER | NOT NULL, FK -> users.id | User |
| push_enabled | BOOLEAN | DEFAULT 1 | Push override for this case |
| email_enabled | BOOLEAN | DEFAULT 1 | Email override for this case |
| priority_override | TEXT | | Priority override for this case |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

**Unique constraint**: `(case_id, user_id)` pair must be unique.

#### `discovered_cases`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Discovery ID |
| user_id | INTEGER | NOT NULL, FK -> users.id | User who the case was found for |
| index_number | TEXT | NOT NULL | Case index number |
| court_type | TEXT | | supreme, local_civil, criminal |
| county | TEXT | | County name |
| court_system | TEXT | | ny_webcivil, ny_webcrimin |
| plaintiff | TEXT | | Plaintiff name |
| defendant | TEXT | | Defendant name |
| case_status | TEXT | | Case status |
| last_action | TEXT | | Last court action |
| last_action_date | TEXT | | Date of last action |
| source_adapter | TEXT | | Adapter that found the case |
| status | TEXT | DEFAULT 'pending' | pending, accepted, dismissed |
| notification_id | INTEGER | | Related notification |
| discovered_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Discovery time |
| resolved_at | TIMESTAMP | | When accepted or dismissed |

#### `discovery_settings`

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Settings ID |
| user_id | INTEGER | NOT NULL UNIQUE, FK -> users.id | Owning user |
| enabled | BOOLEAN | DEFAULT 1 | Whether discovery is active |
| attorney_name | TEXT | | Attorney name to search for |
| attorney_reg_number | TEXT | | Attorney registration number |
| search_courts | TEXT | DEFAULT 'ny_webcivil,ny_webcrimin' | Comma-separated court systems |
| search_county | TEXT | | Specific county to search (optional) |
| last_run_at | TIMESTAMP | | Last discovery run time |
| next_run_at | TIMESTAMP | | Next scheduled run time |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |

### 6.2 Entity Relationships

```
users
├── 1:N -> cases (user_id)
├── 1:N -> notifications (user_id)
├── 1:N -> push_tokens (user_id)
├── 1:1 -> notification_settings (user_id, UNIQUE)
├── 1:1 -> email_configs (user_id, UNIQUE)
├── 1:1 -> discovery_settings (user_id, UNIQUE)
├── 1:N -> email_log (user_id)
└── 1:N -> discovered_cases (user_id)

cases
├── N:1 -> users (user_id)
├── 1:N -> appearances (case_id)
├── 1:N -> case_events (case_id)
├── 1:N -> scrape_jobs (case_id)
├── 1:N -> notifications (case_id)
└── 1:N -> case_notification_prefs (case_id)

appearances
├── N:1 -> cases (case_id)
└── 1:N -> notifications (appearance_id)

case_notification_prefs
├── N:1 -> cases (case_id)
└── N:1 -> users (user_id)
   (UNIQUE constraint on case_id + user_id)
```

**Key relationship patterns:**
- A **user** owns multiple **cases**, each with multiple **appearances** and **case_events**.
- **Notifications** can reference both a case and a specific appearance.
- Each user has exactly one set of **notification_settings**, **email_configs**, and **discovery_settings**.
- **case_notification_prefs** allows per-case overrides of the global notification settings.
- **scrape_jobs** track the history of automated scraping attempts per case.
- **discovered_cases** are potential cases found by the discovery engine, pending user review.
- **email_log** records all inbound emails processed for a user.
- **push_tokens** can have multiple entries per user (one per device).
