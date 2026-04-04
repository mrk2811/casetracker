# NY Court Case Tracker

A fullstack mobile application that aggregates NY court case schedules, allowing users to view all upcoming cases in one unified dashboard with notifications.

## Project Structure

```
ny-court-tracker/
├── ny-court-tracker-backend/    # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── auth.py              # JWT authentication
│   │   ├── database.py          # SQLite database setup
│   │   ├── routers/             # API route handlers
│   │   │   ├── auth.py          # Login/Register endpoints
│   │   │   ├── cases.py         # Case CRUD endpoints
│   │   │   ├── appearances.py   # Appearance CRUD endpoints
│   │   │   ├── dashboard.py     # Dashboard & calendar endpoints
│   │   │   └── notifications.py # Notification endpoints
│   │   └── schemas/             # Pydantic models
│   ├── pyproject.toml
│   └── poetry.lock
├── ny-court-tracker-mobile/     # React Native (Expo) mobile app
│   ├── App.tsx                  # App entry point
│   ├── src/
│   │   ├── context/
│   │   │   └── AuthContext.tsx   # Authentication state management
│   │   ├── navigation/
│   │   │   └── AppNavigator.tsx  # React Navigation setup
│   │   ├── screens/
│   │   │   ├── LoginScreen.tsx
│   │   │   ├── RegisterScreen.tsx
│   │   │   ├── DashboardScreen.tsx
│   │   │   ├── CasesScreen.tsx
│   │   │   ├── CaseDetailScreen.tsx
│   │   │   ├── CaseFormScreen.tsx
│   │   │   ├── CalendarScreen.tsx
│   │   │   ├── NotificationsScreen.tsx
│   │   │   └── SettingsScreen.tsx
│   │   └── services/
│   │       ├── api.ts           # Axios API client
│   │       └── storage.ts       # Platform-aware secure storage
│   ├── package.json
│   └── tsconfig.json
└── README.md
```

## Features

- **User Authentication** - Register/login with JWT-based auth
- **Case Management** - Add, edit, and delete court cases (Supreme, Criminal, Local Civil)
- **Unified Dashboard** - All upcoming appearances sorted by date with stats
- **Calendar View** - Monthly calendar with color-coded court type indicators
- **Notifications** - Configurable reminder settings (1/7/15/30 days before)
- **Settings** - Account info, notification preferences, sign out

## Tech Stack

### Backend
- **FastAPI** (Python)
- **SQLite** with persistent storage
- **JWT** authentication with bcrypt password hashing
- **Poetry** for dependency management

### Mobile App
- **React Native** with **Expo**
- **TypeScript**
- **React Navigation** (native-stack + bottom-tabs)
- **Axios** for API communication
- **expo-secure-store** for secure token storage (native) / localStorage (web)

## Getting Started

### Backend

```bash
cd ny-court-tracker-backend
poetry install
poetry run fastapi dev app/main.py
```

The backend will be available at `http://localhost:8000`.

### Mobile App

```bash
cd ny-court-tracker-mobile
npm install
npx expo start
```

- Press `w` for web browser
- Press `a` for Android (requires emulator or Expo Go)
- Press `i` for iOS (requires simulator, macOS only)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| GET | `/api/cases` | List user's cases |
| POST | `/api/cases` | Create a case |
| GET | `/api/cases/{id}` | Get case detail |
| PUT | `/api/cases/{id}` | Update a case |
| DELETE | `/api/cases/{id}` | Delete a case |
| POST | `/api/cases/{id}/appearances` | Add appearance |
| DELETE | `/api/appearances/{id}` | Delete appearance |
| GET | `/api/dashboard/upcoming` | Get upcoming appearances |
| GET | `/api/dashboard/calendar` | Get calendar data |
| GET | `/api/notifications` | List notifications |
| PUT | `/api/notifications/{id}/read` | Mark notification read |
| GET | `/api/notifications/settings` | Get notification settings |
| PUT | `/api/notifications/settings` | Update notification settings |
