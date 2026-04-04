import sqlite3
import os
from contextlib import contextmanager

DB_DIR = os.environ.get("DB_DIR", "/data")
DB_PATH = os.path.join(DB_DIR, "app.db")

# Fallback for local development
if not os.path.isdir(DB_DIR):
    DB_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(DB_DIR, "app.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                attorney_reg_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                court_type TEXT NOT NULL CHECK(court_type IN ('supreme', 'local_civil', 'criminal')),
                county TEXT NOT NULL,
                index_number TEXT NOT NULL,
                case_year INTEGER,
                case_status TEXT DEFAULT 'active' CHECK(case_status IN ('active', 'disposed', 'pending')),
                plaintiff TEXT,
                defendant TEXT,
                plaintiff_firm TEXT,
                defendant_firm TEXT,
                justice TEXT,
                part TEXT,
                notes TEXT,
                priority TEXT DEFAULT 'normal' CHECK(priority IN ('normal', 'high')),
                source TEXT DEFAULT 'manual',
                last_checked_at TIMESTAMP,
                last_source TEXT,
                verified INTEGER DEFAULT 0,
                search_params TEXT,
                court_system TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS appearances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                appearance_date DATE NOT NULL,
                appearance_time TEXT,
                appearance_type TEXT,
                location TEXT,
                notes TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS case_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT,
                description TEXT,
                source TEXT DEFAULT 'manual',
                source_raw TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS court_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                court_system TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                base_url TEXT,
                adapter_class TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                scrape_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scrape_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                court_system TEXT NOT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
                scheduled_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS email_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inbound_email TEXT UNIQUE,
                forwarding_verified INTEGER DEFAULT 0,
                provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                email_enabled INTEGER DEFAULT 1,
                reminder_days INTEGER DEFAULT 1,
                case_updates_enabled INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_id INTEGER,
                appearance_id INTEGER,
                type TEXT NOT NULL CHECK(type IN ('reminder', 'update', 'system')),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
                FOREIGN KEY (appearance_id) REFERENCES appearances(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cases_user_id ON cases(user_id);
            CREATE INDEX IF NOT EXISTS idx_cases_priority ON cases(priority);
            CREATE INDEX IF NOT EXISTS idx_cases_source ON cases(source);
            CREATE INDEX IF NOT EXISTS idx_cases_court_system ON cases(court_system);
            CREATE INDEX IF NOT EXISTS idx_appearances_case_id ON appearances(case_id);
            CREATE INDEX IF NOT EXISTS idx_appearances_date ON appearances(appearance_date);
            CREATE INDEX IF NOT EXISTS idx_case_events_case_id ON case_events(case_id);
            CREATE INDEX IF NOT EXISTS idx_scrape_jobs_case_id ON scrape_jobs(case_id);
            CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status ON scrape_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
        """)

        # Seed default court configurations
        conn.execute("""
            INSERT OR IGNORE INTO court_configs (state, court_system, display_name, base_url, adapter_class)
            VALUES ('NY', 'ny_webcivil', 'NY WebCivil (Supreme & Civil)', 'https://iapps.courts.state.ny.us/webcivil', 'NYWebCivilAdapter')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO court_configs (state, court_system, display_name, base_url, adapter_class)
            VALUES ('NY', 'ny_webcrimin', 'NY WebCriminal', 'https://iapps.courts.state.ny.us/webcrimin', 'NYWebCriminAdapter')
        """)
