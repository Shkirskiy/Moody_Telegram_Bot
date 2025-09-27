-- Mental Health Bot SQLite Database Schema
-- Auto-migration from JSON to SQLite

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table for mental health check-ins
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_type TEXT NOT NULL CHECK(session_type IN ('morning', 'evening')),
    date DATE NOT NULL,
    time TIME NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    -- Individual response columns for better querying
    energy_level INTEGER CHECK(energy_level IS NULL OR (energy_level >= 0 AND energy_level <= 10)),
    mood INTEGER CHECK(mood IS NULL OR (mood >= 0 AND mood <= 10)),
    stress_level INTEGER CHECK(stress_level IS NULL OR (stress_level >= 0 AND stress_level <= 10)),
    intention TEXT,
    day_word TEXT,
    reflection TEXT,
    -- JSON backup of all responses for flexibility
    responses_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- User preferences and settings
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    timezone TEXT DEFAULT 'Europe/Paris',
    reminders_enabled BOOLEAN DEFAULT 1,
    morning_reminder_time TIME DEFAULT '07:00',
    evening_reminder_time TIME DEFAULT '22:00',
    morning_enabled BOOLEAN DEFAULT 1,
    evening_enabled BOOLEAN DEFAULT 1,
    onboarding_completed BOOLEAN DEFAULT 0,
    last_setup TIMESTAMP,
    last_data_export TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Weekly AI-generated reports
CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_key TEXT NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    year INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    report_content TEXT NOT NULL,
    input_data TEXT NOT NULL,
    data_days_count INTEGER NOT NULL,
    llm_model TEXT,
    generation_attempts INTEGER DEFAULT 1,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, week_key),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Failed report attempts for retry logic
CREATE TABLE IF NOT EXISTS failed_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start DATE NOT NULL,
    error_message TEXT NOT NULL,
    model TEXT,
    retry_scheduled TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Admin notifications log
CREATE TABLE IF NOT EXISTS admin_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_type TEXT NOT NULL,
    user_id INTEGER,
    message TEXT NOT NULL,
    data_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System metadata for tracking migrations and system info
CREATE TABLE IF NOT EXISTS system_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_date ON sessions(user_id, date);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_user ON weekly_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_week ON weekly_reports(week_start);
CREATE INDEX IF NOT EXISTS idx_failed_reports_retry ON failed_reports(retry_scheduled);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Views for common queries
CREATE VIEW IF NOT EXISTS user_stats AS
SELECT 
    u.user_id,
    u.username,
    u.first_name,
    COUNT(DISTINCT s.session_id) as total_sessions,
    COUNT(DISTINCT CASE WHEN s.session_type = 'morning' THEN s.session_id END) as morning_sessions,
    COUNT(DISTINCT CASE WHEN s.session_type = 'evening' THEN s.session_id END) as evening_sessions,
    COUNT(DISTINCT s.date) as unique_dates,
    MIN(s.date) as first_session_date,
    MAX(s.date) as last_session_date
FROM users u
LEFT JOIN sessions s ON u.user_id = s.user_id
GROUP BY u.user_id;
