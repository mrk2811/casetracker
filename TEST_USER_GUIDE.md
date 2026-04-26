# NY Court Case Tracker — Test User Guide

Welcome! You've been invited to test the **NY Court Case Tracker**, an app designed for attorneys and legal professionals who need to stay on top of their New York court case schedules.

---

## What Is This App?

If you practice law in New York, you know the pain: court appearance dates are scattered across the NY Courts eTrack system, and there's no single place to see all your upcoming dates at a glance. The eTrack website only lets you check cases one at a time.

**NY Court Case Tracker solves this.** It pulls all of your court cases into one app so you can see every upcoming appearance, get reminders, and never miss a court date.

---

## How to Access the App

**Live App URL:** [https://case-schedule-app-jgutrt5s.devinapps.com](https://case-schedule-app-jgutrt5s.devinapps.com)

Open the link on your phone's browser for the best experience — the app is designed with a mobile-first layout. It also works on desktop.

**Test Account (pre-loaded with sample data):**
- Email: `john@example.com`
- Password: `Test1234`

Or you can **create your own account** by tapping "Create one" on the login screen.

---

## App Walkthrough

The app has five main sections, accessible via the bottom navigation bar:

### 1. Dashboard (Home)

Your at-a-glance command center.

- **Summary cards** at the top show: appearances today, this week, and high-priority count
- **Upcoming appearances** listed chronologically, grouped by date
- Each card shows:
  - Court type (Supreme, Local Civil, Criminal) with a color-coded badge
  - Case index number and county
  - Party names (plaintiff v. defendant)
  - Time, location, and assigned justice
  - A **freshness indicator** (green = recently updated, yellow = stale, red = outdated)
- **Filter chips** let you filter by priority (All / High Priority / Normal)
- **Pull down to refresh** for the latest data
- Tap the **"+"** button to quickly add a new case

### 2. Cases

Your full case list with detailed management.

- All tracked cases with status badges (Active, Pending, Disposed)
- Shows next appearance date, parties, justice, and data source
- **Filter by**: All, High Priority, Manual entry, or eTrack Email source
- Tap any case to view its **full detail page** with:
  - Complete case information
  - All scheduled appearances
  - Case history and activity log
  - Options to edit or update the case

### 3. Calendar

A visual calendar view of your schedule.

- **Dot indicators** on dates that have appearances
- **Tap any date** to see that day's appearances listed below the calendar
- Tap "Today" to jump back to the current date
- Tap a listed appearance to navigate to its case detail

### 4. Notifications

Stay informed about case activity.

- Alerts for upcoming appearances (reminders)
- Case update notifications (new filings, status changes)
- Each notification shows the relevant case and what changed
- Tap a notification to navigate to the relevant case

### 5. Settings

Manage your account and preferences.

- **Account Information** — Name, email, attorney registration number
- **Push Notifications** — Toggle on/off, configure reminder timing (1, 7, 15, or 30 days before), toggle case update alerts
- **Email & Digest** — Enable email notifications, set digest frequency (daily/weekly/off)
- **Court Email Integration** — Connect your eTrack email forwarding (see below)
- **Weekly Case Discovery** — Auto-scan courts for new cases under your name
- **Sign Out**

---

## Key Features to Test

### Adding a Case Manually

1. Go to **Cases** tab, tap **"+ Add"**
2. Fill in case details:
   - Court Type (Supreme, Local Civil, Criminal)
   - County (dropdown with all NY counties)
   - Index Number (e.g., `152847/2026`)
   - Case Year
3. Tap **"Search & Verify Case"** — the app will attempt to look up the case on NY WebCivil
   - **Note for testers:** WebCivil currently blocks automated lookups with Cloudflare protection, so search may return "No Cases Found." This is expected during the beta.
   - You'll see an **"Add Manually"** button as a fallback — use this to add the case with the details you entered
4. The case will appear in your Cases list and any appearances will show on Dashboard and Calendar

### Email Integration (Court Notification Forwarding)

This is the most powerful feature — it lets the app automatically update your cases when you receive court notifications via email.

**How it works:**
1. Go to **Settings** > **Set Up Email Integration**
2. You'll receive a unique forwarding email address
3. Forward any court notification emails from NY eTrack to that address
4. The app automatically parses the email, matches it to your tracked case, and updates the appearance dates

**To test:**
- Forward a sample eTrack notification email to the forwarding address shown in Settings
- Check the Dashboard to see if the case updated
- View the Email Integration activity log in Settings to see processing status

### Password Reset

1. On the login screen, tap **"Forgot password?"**
2. Enter your registered email address
3. You'll receive a reset link (in test mode, the token is logged server-side)
4. Use the link to set a new password

### Weekly Case Discovery

1. Go to **Settings** > **Weekly Case Discovery**
2. Toggle it on — it automatically scans NY WebCivil and WebCriminal every Monday at 7am ET for new cases under your name
3. Tap **"View Discovered Cases"** to see any newly found cases
4. From Discoveries, you can choose to add a discovered case to your tracked list

---

## Things We'd Love Feedback On

As a tester, here's what's most helpful for us to hear about:

1. **First impressions** — Is the app's purpose clear when you first open it? Is navigation intuitive?
2. **Adding cases** — Was the flow of adding a case smooth? Any confusion?
3. **Dashboard usability** — Is the information density right? Too much? Too little?
4. **Calendar view** — Is it helpful? Easy to navigate between dates?
5. **Performance** — Any slow loading, freezing, or unexpected behavior?
6. **Missing features** — What would you expect to see that isn't there?
7. **Bugs** — Anything that doesn't work as expected (screenshots appreciated!)

---

## Known Limitations (Beta)

- **WebCivil search is currently blocked** by Cloudflare protection on the NY Courts website. The "Search & Verify" feature will return empty results. Manual case entry works as a fallback.
- **Email integration** requires a Mailgun sandbox domain for testing. Email forwarding from Gmail requires a workaround (manual forward rather than auto-forward).
- **Push notifications** are configured in the UI but actual push delivery is not yet wired up for the web version.
- **No native app store version yet** — this is a web app accessed through your phone's browser. A native Android/iOS build is planned for a future release.

---

## Quick Reference

| Item | Value |
|------|-------|
| **App URL** | [https://case-schedule-app-jgutrt5s.devinapps.com](https://case-schedule-app-jgutrt5s.devinapps.com) |
| **Test Login** | `john@example.com` / `Test1234` |
| **Supported Courts** | NY Supreme, Local Civil, Criminal |
| **Data Sources** | Manual entry, WebCivil scraper, eTrack email forwarding |

---

Thank you for testing! Your feedback directly shapes the next version of this app.
