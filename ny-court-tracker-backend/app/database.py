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
        # Step 1: Create tables (without new columns that might conflict with existing tables)
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
                priority TEXT DEFAULT 'normal',
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

            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT,
                subject TEXT,
                events_extracted INTEGER DEFAULT 0,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                email_enabled INTEGER DEFAULT 1,
                push_enabled INTEGER DEFAULT 1,
                reminder_days INTEGER DEFAULT 1,
                case_updates_enabled INTEGER DEFAULT 1,
                digest_frequency TEXT DEFAULT 'off',
                digest_time TEXT DEFAULT '08:00',
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
                push_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
                FOREIGN KEY (appearance_id) REFERENCES appearances(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS push_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                device_name TEXT,
                platform TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS case_notification_prefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                push_enabled INTEGER DEFAULT 1,
                email_enabled INTEGER DEFAULT 1,
                priority_override TEXT,
                UNIQUE(case_id, user_id),
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS discovered_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                index_number TEXT NOT NULL,
                court_type TEXT NOT NULL,
                county TEXT,
                court_system TEXT,
                plaintiff TEXT,
                defendant TEXT,
                case_status TEXT,
                last_action TEXT,
                last_action_date TEXT,
                source_adapter TEXT,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'dismissed')),
                notification_id INTEGER,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                UNIQUE(user_id, index_number, court_system),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS discovery_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                enabled INTEGER DEFAULT 1,
                attorney_name TEXT,
                attorney_reg_number TEXT,
                search_courts TEXT DEFAULT 'ny_webcivil,ny_webcrimin',
                search_county TEXT,
                last_run_at TIMESTAMP,
                next_run_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Step 2: Migrate existing tables — add new columns if they don't exist
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(cases)").fetchall()}
        migrations = [
            ("priority", "ALTER TABLE cases ADD COLUMN priority TEXT DEFAULT 'normal'"),
            ("source", "ALTER TABLE cases ADD COLUMN source TEXT DEFAULT 'manual'"),
            ("last_checked_at", "ALTER TABLE cases ADD COLUMN last_checked_at TIMESTAMP"),
            ("last_source", "ALTER TABLE cases ADD COLUMN last_source TEXT"),
            ("verified", "ALTER TABLE cases ADD COLUMN verified INTEGER DEFAULT 0"),
            ("search_params", "ALTER TABLE cases ADD COLUMN search_params TEXT"),
            ("court_system", "ALTER TABLE cases ADD COLUMN court_system TEXT"),
        ]
        for col_name, alter_sql in migrations:
            if col_name not in existing_cols:
                conn.execute(alter_sql)

        app_cols = {row[1] for row in conn.execute("PRAGMA table_info(appearances)").fetchall()}
        if "source" not in app_cols:
            conn.execute("ALTER TABLE appearances ADD COLUMN source TEXT DEFAULT 'manual'")

        # Migrate notification_settings table
        ns_cols = {row[1] for row in conn.execute("PRAGMA table_info(notification_settings)").fetchall()}
        ns_migrations = [
            ("push_enabled", "ALTER TABLE notification_settings ADD COLUMN push_enabled INTEGER DEFAULT 1"),
            ("digest_frequency", "ALTER TABLE notification_settings ADD COLUMN digest_frequency TEXT DEFAULT 'off'"),
            ("digest_time", "ALTER TABLE notification_settings ADD COLUMN digest_time TEXT DEFAULT '08:00'"),
        ]
        for col_name, alter_sql in ns_migrations:
            if col_name not in ns_cols:
                conn.execute(alter_sql)

        # Migrate notifications table
        notif_cols = {row[1] for row in conn.execute("PRAGMA table_info(notifications)").fetchall()}
        if "push_sent" not in notif_cols:
            conn.execute("ALTER TABLE notifications ADD COLUMN push_sent INTEGER DEFAULT 0")

        # Step 3: Create indexes (after migrations so columns exist)
        conn.executescript("""
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
            CREATE INDEX IF NOT EXISTS idx_push_tokens_user_id ON push_tokens(user_id);
            CREATE INDEX IF NOT EXISTS idx_push_tokens_token ON push_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_case_notification_prefs_case ON case_notification_prefs(case_id);
            CREATE INDEX IF NOT EXISTS idx_case_notification_prefs_user ON case_notification_prefs(user_id);
            CREATE INDEX IF NOT EXISTS idx_email_configs_user_id ON email_configs(user_id);
            CREATE INDEX IF NOT EXISTS idx_email_configs_inbound ON email_configs(inbound_email);
            CREATE INDEX IF NOT EXISTS idx_email_log_user_id ON email_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_discovered_cases_user_id ON discovered_cases(user_id);
            CREATE INDEX IF NOT EXISTS idx_discovered_cases_status ON discovered_cases(status);
            CREATE INDEX IF NOT EXISTS idx_discovery_settings_user_id ON discovery_settings(user_id);
            CREATE INDEX IF NOT EXISTS idx_password_resets_user_id ON password_resets(user_id);
            CREATE INDEX IF NOT EXISTS idx_password_resets_token_hash ON password_resets(token_hash);
        """)

        # Step 4: Seed default court configurations
        conn.execute("""
            INSERT OR IGNORE INTO court_configs (state, court_system, display_name, base_url, adapter_class)
            VALUES ('NY', 'ny_webcivil', 'NY WebCivil (Supreme & Civil)', 'https://iapps.courts.state.ny.us/webcivil', 'NYWebCivilAdapter')
        """)
        conn.execute("""
            INSERT OR IGNORE INTO court_configs (state, court_system, display_name, base_url, adapter_class)
            VALUES ('NY', 'ny_webcrimin', 'NY WebCriminal', 'https://iapps.courts.state.ny.us/webcrimin', 'NYWebCriminAdapter')
        """)
