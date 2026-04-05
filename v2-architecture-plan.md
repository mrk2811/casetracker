# NY Court Case Tracker v2 - Architecture & Implementation Plan

## Overview

Transform the app from manual-only case entry to a smart, multi-source case tracking platform. Starting with NY Housing Court, designed to scale to all NY courts and eventually all US states.

---

## Architecture: Adapter Pattern for Multi-Court Support

```
                         +------------------+
                         |   Court Adapter  |  (Abstract Interface)
                         |   Interface      |
                         +--------+---------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
    +---------v------+  +---------v------+  +---------v------+
    | NYWebCivil     |  | NYWebCriminal  |  | NYHousing      |
    | Adapter        |  | Adapter        |  | Adapter        |
    +----------------+  +----------------+  +----------------+
              |                   |                   |
              +-------------------+-------------------+
                                  |
                         +--------v---------+
                         |  Scraper Engine  |  (Headless Browser)
                         +------------------+

    +------------------+
    |  Data Source      |  (Abstract Interface)
    |  Interface        |
    +--------+---------+
             |
    +--------+--------+--------+
    |                 |        |
    v                 v        v
  Scraper          Email     Future: API
  Source           Source    (UniCourt, etc.)
```

### Key Design Principles
- **CourtAdapter** interface: Each court system (NY WebCivil, NY Housing, CA Courts, etc.) implements `search()`, `get_case_details()`, `get_appearances()`
- **DataSource** interface: Each import method (scraper, email, API) implements `fetch_updates()`, `parse_data()`, `get_source_type()`
- **CaseSource enum**: `WEBCIVIL_SCRAPER`, `ETRACK_EMAIL`, `MANUAL`, `API_PROVIDER`
- All adapters normalize data into a common `CaseRecord` schema regardless of source

---

## Data Import Methods

### Method 1: Manual Search + Scraper (Pull-Based)

**How it works:**
1. User provides search parameters (case number, court, county, party names)
2. App searches the court website via headless browser and shows results
3. User verifies and confirms the correct case (**Case Verification Step**)
4. App saves search parameters and schedules cron-based scraping

**Scraper Design:**
- Headless Selenium + ChromeDriver
- Cron schedule: 2x/day default (6am, 12:30pm ET) with randomized offset (+/- 30 min)
- High priority cases: every 2-4 hours
- User-Agent rotation (pool of 20+ realistic browser UAs)
- Future: proxy rotation service integration point (abstracted behind a `ProxyProvider` interface)
- Rate limiting: max N requests per minute, exponential backoff on errors

**Case Verification Step:**
- When user adds a case by case number, scraper pulls case details + last action
- Shows: "We found case #XYZ: Smith v. Jones, filed in NY County Supreme Court. Last action: Motion to Dismiss (April 2, 2026). Does this match your case?"
- User confirms before tracking begins
- This builds trust and avoids wrong-case tracking

**Important caveat:** NY Courts sites may have CAPTCHAs. The scraper will handle simple page loads but cannot solve CAPTCHAs automatically. If a CAPTCHA is encountered, the system will:
- Retry with a different User-Agent/timing
- Flag the update as "blocked" and notify the user
- Fall back to email-based updates as recommended

### Method 2: Email Forwarding from eTrack (Push-Based) -- RECOMMENDED

**How it works:**
1. App guides user to create an eTrack account (if they don't have one)
2. User sets up email notifications on eTrack
3. User forwards court notification emails to a unique app-provided email address
4. App parses incoming emails and updates the dashboard

**Two email integration approaches:**

**Option A: Dedicated Inbound Mail (Recommended)**
- Use SendGrid Inbound Parse or Postmark
- Assign each user a unique email: `user-{hash}@courttracker.example.com`
- User adds this as a forwarding address in their email client
- Incoming emails are parsed via webhook

**Option B: Gmail/Microsoft Graph API**
- User grants read access to their email via OAuth
- App uses Gmail API / Microsoft Graph to filter and read court notification emails only
- Privacy policy explicitly states: only "Court Notification" emails are parsed, everything else is discarded
- More complex setup but more seamless for user

**Privacy & Trust:**
- Privacy policy must explicitly state email parsing is limited to court notifications only
- All other emails are discarded without reading
- Email content is not stored after parsing (only extracted case data is saved)
- SOC 2 / compliance considerations for future

### Deduplication & Reconciliation

When both scraper and email provide data for the same case:
- **Email (Push) is treated as TRUTH** -- direct from court system
- Scraper data is used to fill gaps or as a fallback
- Each update is tagged with `CaseSource` and timestamp
- Reconciliation logic:
  1. If email update exists, it wins
  2. If only scraper data exists, use it but mark as "scraper-sourced"
  3. If both exist with conflicting data, email wins and a note is logged
  4. Dedup key: `(case_number, court, county, event_date, event_type)`

---

## Database Schema Changes

### New/Modified Tables

```sql
-- Add to cases table
ALTER TABLE cases ADD COLUMN priority TEXT DEFAULT 'normal';  -- 'normal', 'high'
ALTER TABLE cases ADD COLUMN source TEXT DEFAULT 'manual';     -- CaseSource enum
ALTER TABLE cases ADD COLUMN last_checked_at TIMESTAMP;
ALTER TABLE cases ADD COLUMN last_source TEXT;                  -- source of last update
ALTER TABLE cases ADD COLUMN verified BOOLEAN DEFAULT FALSE;
ALTER TABLE cases ADD COLUMN search_params JSON;               -- saved search params for scraper

-- New: Court adapters configuration
CREATE TABLE court_configs (
    id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,           -- 'NY', 'CA', etc.
    court_system TEXT NOT NULL,    -- 'webcivil', 'webcrimin', 'housing'
    base_url TEXT NOT NULL,
    adapter_class TEXT NOT NULL,   -- 'NYWebCivilAdapter', etc.
    enabled BOOLEAN DEFAULT TRUE,
    scrape_config JSON             -- rate limits, UA pool, etc.
);

-- New: Scrape jobs
CREATE TABLE scrape_jobs (
    id INTEGER PRIMARY KEY,
    case_id INTEGER REFERENCES cases(id),
    status TEXT DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'blocked'
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSON,
    error_message TEXT
);

-- New: Case events / activity log
CREATE TABLE case_events (
    id INTEGER PRIMARY KEY,
    case_id INTEGER REFERENCES cases(id),
    event_type TEXT NOT NULL,      -- 'filing', 'hearing_scheduled', 'decision', etc.
    event_date TIMESTAMP,
    description TEXT,
    source TEXT NOT NULL,          -- CaseSource
    source_raw JSON,              -- raw data from source for audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- New: Email inbound config per user
CREATE TABLE email_configs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    inbound_email TEXT UNIQUE,    -- user-{hash}@courttracker.example.com
    forwarding_verified BOOLEAN DEFAULT FALSE,
    provider TEXT,                 -- 'sendgrid', 'postmark', 'gmail_api', 'microsoft_graph'
    oauth_token_encrypted TEXT,   -- for Gmail/MS Graph API approach
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Freshness Indicator

Each case on the dashboard shows:
- **"Last checked: 3 hours ago"** with color coding (green < 6hr, yellow < 24hr, red > 24hr)
- **"Source: Court notification"** or **"Source: Court website scrape"**
- **"Next check: ~6:15 AM tomorrow"** for scraper-sourced cases

---

## Priority System

| Priority | Scraper Frequency | Use Case |
|----------|------------------|----------|
| Normal   | 2x/day (6am, 12:30pm) | Most cases |
| High     | Every 2-4 hours | Active trials, upcoming deadlines |

High priority is set manually by user or auto-triggered when:
- Court date is within 7 days
- Recent filing detected

---

## Filtering System

Filters available on Dashboard and Cases list:
- **Court type**: Housing, Supreme, Criminal, Local Civil
- **County**: All NY counties
- **Status**: Active, Closed, Pending
- **Priority**: Normal, High
- **Source**: Manual, Scraper, Email
- **Date range**: Upcoming appearances within X days
- **Search**: Free text search across case number, parties, notes
- **Freshness**: Updated today, stale (>24h), needs attention

---

## Notifications Layer

- **Push notifications** (Expo Push): new filing, court date scheduled, case update
- **SMS alerts** (Twilio): configurable per case or globally
- **Email alerts**: summary digests (daily/weekly)
- **In-app**: notification center (already built)

Notification triggers:
- New filing added to a tracked case
- Court date scheduled or changed
- Scraper detected a change
- Email update received from court
- Case marked as stale (scraper blocked/failed)

---

## Implementation Phases

### Phase 1: Foundation (Recommended to start here)
- [ ] Refactor database schema (add new columns + tables)
- [ ] Implement CourtAdapter abstract interface
- [ ] Implement DataSource abstract interface  
- [ ] Implement CaseSource enum and tracking
- [ ] Add priority field to cases
- [ ] Add freshness indicator to dashboard/case detail
- [ ] Improve filtering system on frontend
- [ ] Add case verification flow (show case details before tracking)

### Phase 2: Scraper Engine
- [ ] Build headless Selenium scraper for NY Housing Court
- [ ] Implement NYHousingCourtAdapter
- [ ] Build cron job scheduler with randomized timing
- [ ] User-Agent rotation
- [ ] Implement search-and-verify flow in the mobile app
- [ ] Add scrape job tracking and status display
- [ ] Handle CAPTCHA detection and fallback

### Phase 3: Email Integration
- [ ] Set up SendGrid Inbound Parse (or Postmark)
- [ ] Implement unique email assignment per user
- [ ] Build email parser for eTrack notification format
- [ ] Implement forwarding verification flow
- [ ] Build deduplication/reconciliation engine
- [ ] Guide user through eTrack setup in-app

### Phase 4: Notifications & Polish
- [ ] Expo Push Notifications integration
- [ ] SMS via Twilio (optional)
- [ ] Notification preferences per case
- [ ] Daily/weekly digest emails
- [ ] Auto-priority escalation (upcoming court dates)

### Phase 5: Scale to Other Courts
- [ ] NYWebCivilAdapter
- [ ] NYWebCriminalAdapter  
- [ ] Abstract state-level configuration
- [ ] Admin panel for adding new court adapters
- [ ] Future: UniCourt API integration point

---

## Technical Decisions Needed

1. **Email service**: SendGrid Inbound Parse vs Postmark vs Mailgun? (affects cost & setup)
2. **SMS provider**: Twilio vs alternatives? (affects cost)
3. **Scraper hosting**: Run cron jobs on the same Fly.io backend or separate worker? (affects architecture)
4. **CAPTCHA handling**: Accept limitation or integrate a CAPTCHA-solving service?
5. **Proxy rotation**: Build custom or use a service like ScraperAPI/BrightData? (future consideration)
6. **Domain**: Need a custom domain for inbound email (e.g., `courttracker.com`)

---

## Risk Considerations

- **CAPTCHAs on NY court sites**: Headless browsers cannot reliably solve CAPTCHAs. Email-based approach is more reliable, which is why it's recommended.
- **Rate limiting/IP blocking**: Randomized timing + UA rotation helps, but proxy rotation will be needed at scale.
- **Court website changes**: Scrapers are fragile. Each adapter should have health checks and alerting.
- **Privacy/legal**: Parsing user emails requires clear consent and a strong privacy policy. Email forwarding approach is safer than OAuth access.
- **Data accuracy**: Court data can be inconsistent. The verification step and source tracking help maintain trust.
