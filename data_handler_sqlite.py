"""
SQLite implementation of the data handler
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import contextlib
from threading import Lock

logger = logging.getLogger(__name__)

class SQLiteDataHandler:
    """SQLite-based data handler with connection pooling and thread safety"""
    
    def __init__(self, db_path: str = "data/mental_health.db"):
        self.db_path = db_path
        self._lock = Lock()
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Ensure database exists and has correct schema"""
        if not os.path.exists(self.db_path):
            logger.warning(f"Database {self.db_path} does not exist")
            return
        
        # Verify tables exist
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """)
            if not cursor.fetchone():
                logger.error("Database exists but has no tables!")
    
    @contextlib.contextmanager
    def _get_connection(self):
        """Get a database connection with proper handling"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def load_data(self) -> Dict[str, Any]:
        """
        Load all data from database in JSON-compatible format
        For backward compatibility during migration period
        """
        with self._lock:
            try:
                data = {
                    "responses": self._load_sessions(),
                    "metadata": self._load_metadata(),
                    "user_preferences": self._load_preferences(),
                    "unique_users": self._load_unique_users(),
                    "weekly_reports": self._load_weekly_reports(),
                    "failed_reports": self._load_failed_reports()
                }
                return data
            except Exception as e:
                logger.error(f"Failed to load data from SQLite: {e}")
                raise
    
    def _load_sessions(self) -> List[Dict[str, Any]]:
        """Load all sessions from database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, user_id, session_type, date, time, 
                       timestamp, responses_json
                FROM sessions
                ORDER BY timestamp
            """)
            
            sessions = []
            for row in cursor.fetchall():
                session = {
                    "user_id": row["user_id"],
                    "session_type": row["session_type"],
                    "timestamp": row["timestamp"],
                    "date": row["date"],
                    "time": row["time"],
                    "responses": json.loads(row["responses_json"]),
                    "session_id": row["session_id"]
                }
                sessions.append(session)
            
            return sessions
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load system metadata"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session count
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            total_sessions = cursor.fetchone()["count"]
            
            # Get creation date
            cursor.execute("""
                SELECT value FROM system_metadata 
                WHERE key = 'migration_date'
            """)
            row = cursor.fetchone()
            created_at = row["value"] if row else datetime.now().isoformat()
            
            # Get last update
            cursor.execute("""
                SELECT MAX(timestamp) as last_update FROM sessions
            """)
            row = cursor.fetchone()
            last_updated = row["last_update"] if row and row["last_update"] else datetime.now().isoformat()
            
            return {
                "created_at": created_at,
                "version": "2.0",  # SQLite version
                "total_sessions": total_sessions,
                "last_updated": last_updated
            }
    
    def _load_preferences(self) -> Dict[str, Dict[str, Any]]:
        """Load all user preferences"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, timezone, reminders_enabled,
                       morning_reminder_time, evening_reminder_time,
                       morning_enabled, evening_enabled,
                       onboarding_completed, last_setup,
                       last_data_export, last_updated
                FROM user_preferences
            """)
            
            preferences = {}
            for row in cursor.fetchall():
                user_prefs = {
                    "timezone": row["timezone"],
                    "reminders_enabled": bool(row["reminders_enabled"]),
                    "morning_reminder_time": row["morning_reminder_time"],
                    "evening_reminder_time": row["evening_reminder_time"],
                    "morning_enabled": bool(row["morning_enabled"]),
                    "evening_enabled": bool(row["evening_enabled"]),
                    "onboarding_completed": bool(row["onboarding_completed"]),
                    "last_setup": row["last_setup"],
                    "last_updated": row["last_updated"]
                }
                if row["last_data_export"]:
                    user_prefs["last_data_export"] = row["last_data_export"]
                    
                preferences[str(row["user_id"])] = user_prefs
            
            return preferences
    
    def _load_unique_users(self) -> Dict[str, Any]:
        """Load unique users data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, last_name,
                       first_seen, is_admin
                FROM users
            """)
            
            users = {}
            for row in cursor.fetchall():
                users[str(row["user_id"])] = {
                    "username": row["username"] or "",
                    "first_name": row["first_name"] or "",
                    "last_name": row["last_name"] or "",
                    "first_seen": row["first_seen"],
                    "is_admin": bool(row["is_admin"])
                }
            
            return {
                "count": len(users),
                "users": users
            }
    
    def _load_weekly_reports(self) -> Dict[str, Dict[str, Any]]:
        """Load all weekly reports"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, week_key, week_start, week_end,
                       year, week_number, report_content, input_data,
                       data_days_count, llm_model, generation_attempts,
                       generated_at
                FROM weekly_reports
                ORDER BY week_start DESC
            """)
            
            reports = {}
            for row in cursor.fetchall():
                user_id_str = str(row["user_id"])
                if user_id_str not in reports:
                    reports[user_id_str] = {}
                
                reports[user_id_str][row["week_key"]] = {
                    "week_start": row["week_start"],
                    "week_end": row["week_end"],
                    "generated_at": row["generated_at"],
                    "report_content": row["report_content"],
                    "input_data": row["input_data"],
                    "data_days_count": row["data_days_count"],
                    "week_number": row["week_number"],
                    "year": row["year"],
                    "llm_model": row["llm_model"],
                    "generation_attempts": row["generation_attempts"]
                }
            
            return reports
    
    def _load_failed_reports(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load failed report attempts"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, week_start, error_message,
                       model, retry_scheduled, created_at
                FROM failed_reports
                ORDER BY created_at DESC
            """)
            
            failed = {}
            for row in cursor.fetchall():
                user_id_str = str(row["user_id"])
                if user_id_str not in failed:
                    failed[user_id_str] = []
                
                failed[user_id_str].append({
                    "timestamp": row["created_at"],
                    "week_start": row["week_start"],
                    "error": row["error_message"],
                    "model": row["model"],
                    "retry_scheduled": row["retry_scheduled"]
                })
            
            return failed
    
    def save_data(self, data: Dict[str, Any]) -> None:
        """
        Save data - for backward compatibility
        Actually does nothing as SQLite auto-saves
        """
        logger.debug("save_data called - SQLite auto-saves, no action needed")
    
    def save_session(self, user_id: int, session_type: str, responses: Dict[str, Any]) -> None:
        """Save a complete session with responses"""
        with self._lock:
            try:
                timestamp = datetime.now().isoformat()
                date = datetime.now().strftime("%Y-%m-%d")
                time = datetime.now().strftime("%H:%M:%S")
                session_id = f"{user_id}_{session_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Extract individual fields
                energy_level = responses.get("energy_level")
                mood = responses.get("mood")
                stress_level = responses.get("stress_level")
                intention = responses.get("intention")
                
                # Handle both 'day' and 'day_word' field names
                day_word = responses.get("day_word") or responses.get("day", "")
                if day_word and day_word.startswith("word_"):
                    day_word = day_word[5:]
                
                reflection = responses.get("reflection")
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Ensure user exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO users (user_id, first_name)
                        VALUES (?, ?)
                    """, (user_id, f"User_{user_id}"))
                    
                    # Insert session
                    cursor.execute("""
                        INSERT INTO sessions (
                            session_id, user_id, session_type, date, time, timestamp,
                            energy_level, mood, stress_level, intention, day_word, reflection,
                            responses_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, user_id, session_type, date, time, timestamp,
                        energy_level, mood, stress_level, intention, day_word, reflection,
                        json.dumps(responses)
                    ))
                
                logger.info(f"Saved session: {session_id}")
                
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
                raise
    
    def get_user_sessions(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get user sessions from the last N days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, user_id, session_type, date, time,
                           timestamp, responses_json
                    FROM sessions
                    WHERE user_id = ? AND date >= ?
                    ORDER BY timestamp
                """, (user_id, cutoff_date))
                
                sessions = []
                for row in cursor.fetchall():
                    session = {
                        "user_id": row["user_id"],
                        "session_type": row["session_type"],
                        "timestamp": row["timestamp"],
                        "date": row["date"],
                        "time": row["time"],
                        "responses": json.loads(row["responses_json"]),
                        "session_id": row["session_id"]
                    }
                    sessions.append(session)
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    def get_today_sessions(self, user_id: int) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get today's sessions for a user"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, user_id, session_type, date, time,
                           timestamp, responses_json
                    FROM sessions
                    WHERE user_id = ? AND date = ?
                """, (user_id, today))
                
                today_sessions = {"morning": None, "evening": None}
                
                for row in cursor.fetchall():
                    session = {
                        "user_id": row["user_id"],
                        "session_type": row["session_type"],
                        "timestamp": row["timestamp"],
                        "date": row["date"],
                        "time": row["time"],
                        "responses": json.loads(row["responses_json"]),
                        "session_id": row["session_id"]
                    }
                    today_sessions[row["session_type"]] = session
                
                return today_sessions
                
        except Exception as e:
            logger.error(f"Failed to get today's sessions: {e}")
            return {"morning": None, "evening": None}
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """Get basic statistics for a user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Use the pre-created view for efficiency
                cursor.execute("""
                    SELECT * FROM user_stats WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                
                if not row:
                    return {"total_sessions": 0, "morning_sessions": 0, "evening_sessions": 0}
                
                return {
                    "total_sessions": row["total_sessions"],
                    "morning_sessions": row["morning_sessions"],
                    "evening_sessions": row["evening_sessions"],
                    "first_session_date": row["first_session_date"],
                    "last_session_date": row["last_session_date"],
                    "unique_dates": row["unique_dates"]
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_sessions": 0, "morning_sessions": 0, "evening_sessions": 0}
    
    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timezone, reminders_enabled,
                           morning_reminder_time, evening_reminder_time,
                           morning_enabled, evening_enabled,
                           onboarding_completed, last_setup,
                           last_data_export, last_updated
                    FROM user_preferences
                    WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                prefs = {
                    "timezone": row["timezone"],
                    "reminders_enabled": bool(row["reminders_enabled"]),
                    "morning_reminder_time": row["morning_reminder_time"],
                    "evening_reminder_time": row["evening_reminder_time"],
                    "morning_enabled": bool(row["morning_enabled"]),
                    "evening_enabled": bool(row["evening_enabled"]),
                    "onboarding_completed": bool(row["onboarding_completed"]),
                    "last_setup": row["last_setup"],
                    "last_updated": row["last_updated"]
                }
                
                if row["last_data_export"]:
                    prefs["last_data_export"] = row["last_data_export"]
                
                return prefs
                
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return None
    
    def save_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """Save user preferences"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Ensure user exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO users (user_id, first_name)
                        VALUES (?, ?)
                    """, (user_id, f"User_{user_id}"))
                    
                    # Upsert preferences
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_preferences (
                            user_id, timezone, reminders_enabled,
                            morning_reminder_time, evening_reminder_time,
                            morning_enabled, evening_enabled,
                            onboarding_completed, last_setup,
                            last_data_export, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        user_id,
                        preferences.get("timezone", "Europe/Paris"),
                        1 if preferences.get("reminders_enabled", True) else 0,
                        preferences.get("morning_reminder_time", "07:00"),
                        preferences.get("evening_reminder_time", "22:00"),
                        1 if preferences.get("morning_enabled", True) else 0,
                        1 if preferences.get("evening_enabled", True) else 0,
                        1 if preferences.get("onboarding_completed", False) else 0,
                        preferences.get("last_setup"),
                        preferences.get("last_data_export")
                    ))
                
                logger.info(f"Saved preferences for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to save user preferences: {e}")
                raise
    
    def delete_user_preferences(self, user_id: int) -> None:
        """Delete user preferences"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM user_preferences WHERE user_id = ?
                    """, (user_id,))
                
                logger.info(f"Deleted preferences for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to delete user preferences: {e}")
                raise
    
    def get_all_users_with_preferences(self) -> List[int]:
        """Get list of all user IDs that have preferences stored"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id FROM user_preferences
                """)
                
                return [row["user_id"] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get users with preferences: {e}")
            return []
    
    def ensure_data_structure(self) -> None:
        """Ensure the database has proper structure"""
        # SQLite schema is enforced by schema.sql, nothing to do here
        logger.debug("ensure_data_structure called - SQLite schema already enforced")
    
    def register_unique_user(self, user_id: int, user_info: dict) -> bool:
        """Register a new unique user if under the limit"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Check if user already exists
                    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
                    if cursor.fetchone():
                        return True  # Already registered
                    
                    # Check user count limit
                    cursor.execute("SELECT COUNT(*) as count FROM users")
                    if cursor.fetchone()["count"] >= 100:
                        return False  # Limit reached
                    
                    # Register new user
                    from config import ADMIN_USER_ID
                    cursor.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, is_admin)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        user_info.get("username", ""),
                        user_info.get("first_name", ""),
                        user_info.get("last_name", ""),
                        1 if user_id == ADMIN_USER_ID else 0
                    ))
                    
                    logger.info(f"Registered new user {user_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to register unique user {user_id}: {e}")
                return False
    
    def get_unique_user_count(self) -> int:
        """Get the current count of unique users"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users")
                return cursor.fetchone()["count"]
        except Exception as e:
            logger.error(f"Failed to get unique user count: {e}")
            return 0
    
    def get_all_unique_users(self) -> dict:
        """Get all registered unique users with their details"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, username, first_name, last_name,
                           first_seen, is_admin
                    FROM users
                """)
                
                users = {}
                for row in cursor.fetchall():
                    users[str(row["user_id"])] = {
                        "username": row["username"] or "",
                        "first_name": row["first_name"] or "",
                        "last_name": row["last_name"] or "",
                        "first_seen": row["first_seen"],
                        "is_admin": bool(row["is_admin"])
                    }
                
                return users
                
        except Exception as e:
            logger.error(f"Failed to get unique users: {e}")
            return {}
    
    def is_registered_user(self, user_id: int) -> bool:
        """Check if a user is already registered"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if user {user_id} is registered: {e}")
            return False
    
    def migrate_existing_users(self) -> None:
        """This is handled by the migration script"""
        logger.debug("migrate_existing_users called - handled by migration script")
    
    def get_week_sessions(self, user_id: int, week_start_date: str) -> List[Dict[str, Any]]:
        """Get user sessions for a specific week"""
        try:
            week_start = datetime.strptime(week_start_date, "%Y-%m-%d")
            week_end = week_start + timedelta(days=6)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, user_id, session_type, date, time,
                           timestamp, responses_json
                    FROM sessions
                    WHERE user_id = ? AND date >= ? AND date <= ?
                    ORDER BY timestamp
                """, (user_id, week_start_date, week_end.strftime("%Y-%m-%d")))
                
                sessions = []
                for row in cursor.fetchall():
                    session = {
                        "user_id": row["user_id"],
                        "session_type": row["session_type"],
                        "timestamp": row["timestamp"],
                        "date": row["date"],
                        "time": row["time"],
                        "responses": json.loads(row["responses_json"]),
                        "session_id": row["session_id"]
                    }
                    sessions.append(session)
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get week sessions: {e}")
            return []
    
    def save_weekly_report(self, user_id: int, week_start: str, report_content: str, 
                          input_data: str, data_days_count: int, llm_model: str = None) -> None:
        """Save a weekly AI-generated report"""
        with self._lock:
            try:
                week_date = datetime.strptime(week_start, "%Y-%m-%d")
                week_end = week_date + timedelta(days=6)
                week_key = f"{week_date.year}_week_{week_date.isocalendar()[1]:02d}"
                
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO weekly_reports (
                            user_id, week_key, week_start, week_end, year, week_number,
                            report_content, input_data, data_days_count,
                            llm_model, generation_attempts
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, week_key, week_start,
                        week_end.strftime("%Y-%m-%d"),
                        week_date.year,
                        week_date.isocalendar()[1],
                        report_content, input_data, data_days_count,
                        llm_model, 1
                    ))
                
                logger.info(f"Saved weekly report for user {user_id}, week {week_key}")
                
            except Exception as e:
                logger.error(f"Failed to save weekly report: {e}")
                raise
    
    def get_weekly_report(self, user_id: int, week_start: str) -> Optional[Dict[str, Any]]:
        """Get a specific weekly report"""
        try:
            week_date = datetime.strptime(week_start, "%Y-%m-%d")
            week_key = f"{week_date.year}_week_{week_date.isocalendar()[1]:02d}"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM weekly_reports
                    WHERE user_id = ? AND week_key = ?
                """, (user_id, week_key))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "week_start": row["week_start"],
                    "week_end": row["week_end"],
                    "generated_at": row["generated_at"],
                    "report_content": row["report_content"],
                    "input_data": row["input_data"],
                    "data_days_count": row["data_days_count"],
                    "week_number": row["week_number"],
                    "year": row["year"],
                    "llm_model": row["llm_model"],
                    "generation_attempts": row["generation_attempts"]
                }
                
        except Exception as e:
            logger.error(f"Failed to get weekly report: {e}")
            return None
    
    def get_user_weekly_reports(self, user_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Get all weekly reports for a user, sorted by date (newest first)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM weekly_reports
                    WHERE user_id = ?
                    ORDER BY week_start DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query, (user_id,))
                
                reports = []
                for row in cursor.fetchall():
                    report = {
                        "week_key": row["week_key"],
                        "week_start": row["week_start"],
                        "week_end": row["week_end"],
                        "generated_at": row["generated_at"],
                        "report_content": row["report_content"],
                        "input_data": row["input_data"],
                        "data_days_count": row["data_days_count"],
                        "week_number": row["week_number"],
                        "year": row["year"],
                        "llm_model": row["llm_model"],
                        "generation_attempts": row["generation_attempts"]
                    }
                    reports.append(report)
                
                return reports
                
        except Exception as e:
            logger.error(f"Failed to get user weekly reports: {e}")
            return []
    
    def get_previous_reports_for_context(self, user_id: int, current_week_start: str, count: int = 3) -> List[str]:
        """Get previous report contents for AI context"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT report_content FROM weekly_reports
                    WHERE user_id = ? AND week_start < ?
                    ORDER BY week_start DESC
                    LIMIT ?
                """, (user_id, current_week_start, count))
                
                return [row["report_content"] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get previous reports for context: {e}")
            return []
    
    def ensure_weekly_reports_structure(self) -> None:
        """Ensure the database has proper structure for weekly reports"""
        logger.debug("ensure_weekly_reports_structure called - SQLite schema already enforced")
    
    def save_failed_report_attempt(self, user_id: int, week_start: str, error_message: str, 
                                  llm_model: str, retry_scheduled: str = None) -> None:
        """Save information about a failed report generation attempt"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO failed_reports (
                            user_id, week_start, error_message, model, retry_scheduled
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (user_id, week_start, error_message, llm_model, retry_scheduled))
                
                logger.info(f"Saved failed report attempt for user {user_id}, week {week_start}")
                
            except Exception as e:
                logger.error(f"Failed to save failed report attempt: {e}")
    
    def get_pending_report_retries(self) -> List[Dict[str, Any]]:
        """Get all pending report retries that should be processed"""
        try:
            current_time = datetime.now().isoformat()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT user_id, week_start, 
                           MAX(error_message) as error_message,
                           COUNT(*) as attempts
                    FROM failed_reports
                    WHERE retry_scheduled IS NOT NULL AND retry_scheduled <= ?
                    GROUP BY user_id, week_start
                """, (current_time,))
                
                pending = []
                for row in cursor.fetchall():
                    pending.append({
                        "user_id": row["user_id"],
                        "week_start": row["week_start"],
                        "original_error": row["error_message"],
                        "attempts": row["attempts"]
                    })
                
                return pending
                
        except Exception as e:
            logger.error(f"Failed to get pending report retries: {e}")
            return []
    
    def clear_failed_report_attempts(self, user_id: int, week_start: str) -> None:
        """Clear failed report attempts after successful generation"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM failed_reports 
                        WHERE user_id = ? AND week_start = ?
                    """, (user_id, week_start))
                
                logger.info(f"Cleared failed report attempts for user {user_id}, week {week_start}")
                
            except Exception as e:
                logger.error(f"Failed to clear failed report attempts: {e}")
    
    def can_export_data(self, user_id: int) -> tuple[bool, str]:
        """Check if user can export data (rate limited to once per week)"""
        try:
            preferences = self.get_user_preferences(user_id)
            if not preferences:
                return True, "Ready to export"
            
            last_export = preferences.get("last_data_export")
            if not last_export:
                return True, "Ready to export"
            
            last_export_date = datetime.fromisoformat(last_export)
            current_date = datetime.now()
            days_passed = (current_date - last_export_date).days
            
            if days_passed >= 7:
                return True, "Ready to export"
            else:
                days_remaining = 7 - days_passed
                hours_remaining = int((7 * 24) - ((current_date - last_export_date).total_seconds() / 3600))
                
                if days_remaining > 0:
                    return False, f"You can export your data again in {days_remaining} days"
                else:
                    return False, f"You can export your data again in {hours_remaining} hours"
                
        except Exception as e:
            logger.error(f"Failed to check export eligibility: {e}")
            return True, "Ready to export"
    
    def update_export_timestamp(self, user_id: int) -> None:
        """Update the last data export timestamp for a user"""
        with self._lock:
            try:
                preferences = self.get_user_preferences(user_id) or {}
                preferences["last_data_export"] = datetime.now().isoformat()
                self.save_user_preferences(user_id, preferences)
                
                logger.info(f"Updated export timestamp for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to update export timestamp: {e}")
    
    def get_admin_notifications(self) -> Dict[str, Any]:
        """Get admin notifications data"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get today's notification status
                today = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("""
                    SELECT COUNT(*) as count FROM admin_notifications
                    WHERE DATE(created_at) = ? AND notification_type = 'daily_summary'
                """, (today,))
                
                today_sent = cursor.fetchone()["count"] > 0
                
                # Get pending issues
                cursor.execute("""
                    SELECT * FROM admin_notifications
                    WHERE notification_type != 'daily_summary'
                    AND DATE(created_at) >= DATE('now', '-1 day')
                    ORDER BY created_at DESC
                """)
                
                pending_issues = []
                for row in cursor.fetchall():
                    issue = {
                        "timestamp": row["created_at"],
                        "type": row["notification_type"],
                        "user_id": row["user_id"],
                        "details": row["message"]
                    }
                    if row["data_json"]:
                        issue["data"] = json.loads(row["data_json"])
                    pending_issues.append(issue)
                
                return {
                    "daily_notifications": {
                        today: {"sent": today_sent}
                    },
                    "pending_issues": pending_issues
                }
                
        except Exception as e:
            logger.error(f"Failed to get admin notifications: {e}")
            return {"daily_notifications": {}, "pending_issues": []}
    
    def add_admin_notification(self, notification_type: str, user_id: int, message: str, data: Dict = None) -> None:
        """Add an admin notification"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO admin_notifications (notification_type, user_id, message, data_json)
                        VALUES (?, ?, ?, ?)
                    """, (
                        notification_type,
                        user_id,
                        message,
                        json.dumps(data) if data else None
                    ))
                
                logger.info(f"Added admin notification: {notification_type} for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to add admin notification: {e}")
    
    def mark_admin_notified_today(self, issues_count: int, issues_summary: Dict) -> None:
        """Mark that admin has been notified today"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Add daily summary notification
                    cursor.execute("""
                        INSERT INTO admin_notifications (notification_type, user_id, message, data_json)
                        VALUES (?, ?, ?, ?)
                    """, (
                        "daily_summary",
                        None,
                        f"Daily summary sent with {issues_count} issues",
                        json.dumps({"issues_count": issues_count, "summary": issues_summary})
                    ))
                    
                    # Clear old pending issues (older than 1 day)
                    cursor.execute("""
                        DELETE FROM admin_notifications
                        WHERE notification_type != 'daily_summary'
                        AND DATE(created_at) < DATE('now', '-1 day')
                    """)
                
                logger.info(f"Marked admin as notified today with {issues_count} issues")
                
            except Exception as e:
                logger.error(f"Failed to mark admin notified: {e}")
    
    def clear_pending_admin_issues(self) -> None:
        """Clear pending admin notification issues"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM admin_notifications
                        WHERE notification_type != 'daily_summary'
                    """)
                
                logger.info("Cleared pending admin issues")
                
            except Exception as e:
                logger.error(f"Failed to clear pending admin issues: {e}")
    
    def export_user_data_to_csv(self, user_id: int) -> Optional[str]:
        """Export all user data to a CSV file"""
        try:
            import csv
            import tempfile
            
            # Create temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"mental_health_data_{user_id}_{timestamp}.csv"
            csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get user info
                cursor.execute("""
                    SELECT * FROM users WHERE user_id = ?
                """, (user_id,))
                user_info = cursor.fetchone()
                
                # Get sessions
                cursor.execute("""
                    SELECT * FROM sessions WHERE user_id = ?
                    ORDER BY timestamp
                """, (user_id,))
                sessions = cursor.fetchall()
                
                # Get preferences
                preferences = self.get_user_preferences(user_id) or {}
                
                # Get stats
                stats = self.get_stats(user_id)
                
                # Get weekly reports
                weekly_reports = self.get_user_weekly_reports(user_id)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([f"Mental Health Data Export for User {user_id}"])
                writer.writerow([f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([])
                
                # Section 1: User Information
                writer.writerow(["USER INFORMATION"])
                writer.writerow(["Field", "Value"])
                if user_info:
                    writer.writerow(["Username", user_info["username"] or "Not provided"])
                    writer.writerow(["First Name", user_info["first_name"] or "Not provided"])
                    writer.writerow(["Last Name", user_info["last_name"] or "Not provided"])
                    writer.writerow(["First Seen", user_info["first_seen"] or "Unknown"])
                writer.writerow([])
                
                # Section 2: Statistics
                writer.writerow(["STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Sessions", stats.get("total_sessions", 0)])
                writer.writerow(["Morning Sessions", stats.get("morning_sessions", 0)])
                writer.writerow(["Evening Sessions", stats.get("evening_sessions", 0)])
                writer.writerow(["Unique Days Tracked", stats.get("unique_dates", 0)])
                writer.writerow(["First Session Date", stats.get("first_session_date", "N/A")])
                writer.writerow(["Last Session Date", stats.get("last_session_date", "N/A")])
                writer.writerow([])
                
                # Section 3: User Preferences
                writer.writerow(["USER PREFERENCES & SETTINGS"])
                writer.writerow(["Setting", "Value"])
                writer.writerow(["Timezone", preferences.get("timezone", "Not set")])
                writer.writerow(["Reminders Enabled", preferences.get("reminders_enabled", "Not set")])
                writer.writerow(["Morning Reminder Time", preferences.get("morning_reminder_time", "Not set")])
                writer.writerow(["Evening Reminder Time", preferences.get("evening_reminder_time", "Not set")])
                writer.writerow(["Morning Session Enabled", preferences.get("morning_enabled", "Not set")])
                writer.writerow(["Evening Session Enabled", preferences.get("evening_enabled", "Not set")])
                writer.writerow(["Onboarding Completed", preferences.get("onboarding_completed", False)])
                writer.writerow([])
                
                # Section 4: Session Data
                writer.writerow(["SESSION DATA"])
                writer.writerow(["Date", "Time", "Session Type", "Energy Level", "Mood", "Stress Level", 
                               "Intention", "Day Word", "Reflection"])
                
                # Sanitize text fields to prevent CSV injection
                def sanitize_csv_field(value):
                    if value is None:
                        return ""
                    value = str(value)
                    if value.startswith(('=', '+', '-', '@')):
                        value = "'" + value
                    value = value.replace('"', '""')
                    return value
                
                for session in sessions:
                    writer.writerow([
                        session["date"],
                        session["time"],
                        session["session_type"],
                        session["energy_level"] or "",
                        session["mood"] or "",
                        session["stress_level"] or "",
                        sanitize_csv_field(session["intention"]),
                        sanitize_csv_field(session["day_word"]),
                        sanitize_csv_field(session["reflection"])
                    ])
                
                writer.writerow([])
                
                # Section 5: Weekly Reports
                writer.writerow(["WEEKLY AI REPORTS"])
                writer.writerow(["Week Start", "Week End", "Generated At", "Days of Data", "Report Summary"])
                
                for report in weekly_reports[:10]:  # Limit to last 10 reports for summary
                    # Extract first paragraph of report as summary
                    report_content = report.get("report_content", "")
                    import re
                    report_summary = re.sub(r'<[^>]+>', '', report_content)
                    if len(report_summary) > 200:
                        report_summary = report_summary[:200] + "..."
                    
                    writer.writerow([
                        report.get("week_start", ""),
                        report.get("week_end", ""),
                        report.get("generated_at", ""),
                        report.get("data_days_count", ""),
                        sanitize_csv_field(report_summary)
                    ])
            
            logger.info(f"Successfully exported data to CSV for user {user_id}: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Failed to export user data to CSV: {e}")
            return None
