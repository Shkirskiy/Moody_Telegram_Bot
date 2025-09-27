"""
Automatic migration from JSON to SQLite database
"""

import json
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import shutil

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """Handles automatic migration from JSON to SQLite"""
    
    def __init__(self, json_path: str = "data/responses.json", 
                 sqlite_path: str = "data/mental_health.db",
                 schema_path: str = "database/schema.sql"):
        self.json_path = json_path
        self.sqlite_path = sqlite_path
        self.schema_path = schema_path
        self.conn = None
        self.cursor = None
        
    def needs_migration(self) -> bool:
        """Check if migration is needed"""
        return (
            os.path.exists(self.json_path) and  # JSON exists
            not os.path.exists(self.sqlite_path) and  # SQLite doesn't exist
            os.path.getsize(self.json_path) > 100  # JSON has data
        )
    
    def migrate(self) -> bool:
        """
        Perform automatic migration from JSON to SQLite
        
        Returns:
            bool: True if migration successful, False otherwise
        """
        try:
            logger.info("Starting automatic database migration...")
            
            # Step 1: Backup JSON file
            backup_path = self._backup_json()
            logger.info(f"Created backup: {backup_path}")
            
            # Step 2: Load JSON data
            json_data = self._load_json_data()
            if not json_data:
                logger.warning("No data to migrate")
                return False
            
            # Step 3: Create SQLite database and tables
            self._create_database()
            logger.info(f"Created SQLite database: {self.sqlite_path}")
            
            # Step 4: Migrate data
            migrated_counts = self._migrate_all_data(json_data)
            
            # Step 5: Verify migration
            if self._verify_migration(json_data, migrated_counts):
                # Step 6: Save migration metadata
                self._save_migration_metadata(migrated_counts)
                logger.info("Migration completed successfully!")
                return True
            else:
                logger.error("Migration verification failed, rolling back...")
                self._rollback()
                return False
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self._rollback()
            return False
        finally:
            self._close_connection()
    
    def _backup_json(self) -> str:
        """Create a backup of the JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.json_path}.backup_{timestamp}"
        shutil.copy2(self.json_path, backup_path)
        return backup_path
    
    def _load_json_data(self) -> Optional[Dict[str, Any]]:
        """Load and validate JSON data"""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load JSON data: {e}")
            return None
    
    def _create_database(self) -> None:
        """Create SQLite database and execute schema"""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        
        # Connect to database
        self.conn = sqlite3.connect(self.sqlite_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        
        # Read and execute schema
        with open(self.schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema
        self.conn.executescript(schema_sql)
        self.conn.commit()
    
    def _migrate_all_data(self, json_data: Dict[str, Any]) -> Dict[str, int]:
        """Migrate all data from JSON to SQLite"""
        counts = {
            'users': 0,
            'sessions': 0,
            'preferences': 0,
            'weekly_reports': 0,
            'failed_reports': 0
        }
        
        try:
            # Start transaction
            self.conn.execute("BEGIN TRANSACTION")
            
            # 1. Migrate unique users
            counts['users'] = self._migrate_users(json_data)
            logger.info(f"Migrated {counts['users']} users")
            
            # 2. Migrate sessions
            counts['sessions'] = self._migrate_sessions(json_data)
            logger.info(f"Migrated {counts['sessions']} sessions")
            
            # 3. Migrate user preferences
            counts['preferences'] = self._migrate_preferences(json_data)
            logger.info(f"Migrated {counts['preferences']} user preferences")
            
            # 4. Migrate weekly reports
            counts['weekly_reports'] = self._migrate_weekly_reports(json_data)
            logger.info(f"Migrated {counts['weekly_reports']} weekly reports")
            
            # 5. Migrate failed reports (if exists)
            counts['failed_reports'] = self._migrate_failed_reports(json_data)
            if counts['failed_reports'] > 0:
                logger.info(f"Migrated {counts['failed_reports']} failed report attempts")
            
            # Commit transaction
            self.conn.commit()
            return counts
            
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def _migrate_users(self, json_data: Dict[str, Any]) -> int:
        """Migrate users from unique_users section"""
        users_data = json_data.get("unique_users", {}).get("users", {})
        count = 0
        
        for user_id_str, user_info in users_data.items():
            try:
                self.cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, first_seen, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    int(user_id_str),
                    user_info.get("username", ""),
                    user_info.get("first_name", ""),
                    user_info.get("last_name", ""),
                    user_info.get("first_seen"),
                    1 if user_info.get("is_admin", False) else 0
                ))
                count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"User {user_id_str} already exists, skipping...")
        
        # Also check for users in sessions that might not be in unique_users
        sessions = json_data.get("responses", [])
        existing_users = set(int(uid) for uid in users_data.keys())
        
        for session in sessions:
            user_id = session.get("user_id")
            if user_id and user_id not in existing_users:
                try:
                    self.cursor.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, first_seen)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        "",
                        f"User_{user_id}",
                        "",
                        session.get("timestamp")
                    ))
                    existing_users.add(user_id)
                    count += 1
                except sqlite3.IntegrityError:
                    pass
        
        return count
    
    def _migrate_sessions(self, json_data: Dict[str, Any]) -> int:
        """Migrate session data"""
        sessions = json_data.get("responses", [])
        count = 0
        
        for session in sessions:
            try:
                responses = session.get("responses", {})
                
                # Handle both 'day' and 'day_word' field names (legacy support)
                day_word = responses.get("day_word") or responses.get("day", "")
                if day_word and day_word.startswith("word_"):
                    day_word = day_word[5:]  # Remove 'word_' prefix
                
                self.cursor.execute("""
                    INSERT INTO sessions (
                        session_id, user_id, session_type, date, time, timestamp,
                        energy_level, mood, stress_level, intention, day_word, reflection,
                        responses_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.get("session_id"),
                    session.get("user_id"),
                    session.get("session_type"),
                    session.get("date"),
                    session.get("time"),
                    session.get("timestamp"),
                    responses.get("energy_level"),
                    responses.get("mood"),
                    responses.get("stress_level"),
                    responses.get("intention"),
                    day_word,
                    responses.get("reflection"),
                    json.dumps(responses)
                ))
                count += 1
            except sqlite3.IntegrityError as e:
                logger.warning(f"Session {session.get('session_id')} already exists: {e}")
            except Exception as e:
                logger.error(f"Error migrating session: {e}")
        
        return count
    
    def _migrate_preferences(self, json_data: Dict[str, Any]) -> int:
        """Migrate user preferences"""
        preferences = json_data.get("user_preferences", {})
        count = 0
        
        for user_id_str, prefs in preferences.items():
            try:
                self.cursor.execute("""
                    INSERT INTO user_preferences (
                        user_id, timezone, reminders_enabled, 
                        morning_reminder_time, evening_reminder_time,
                        morning_enabled, evening_enabled, onboarding_completed,
                        last_setup, last_data_export, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(user_id_str),
                    prefs.get("timezone", "Europe/Paris"),
                    1 if prefs.get("reminders_enabled", True) else 0,
                    prefs.get("morning_reminder_time", "07:00"),
                    prefs.get("evening_reminder_time", "22:00"),
                    1 if prefs.get("morning_enabled", True) else 0,
                    1 if prefs.get("evening_enabled", True) else 0,
                    1 if prefs.get("onboarding_completed", False) else 0,
                    prefs.get("last_setup"),
                    prefs.get("last_data_export"),
                    prefs.get("last_updated")
                ))
                count += 1
            except sqlite3.IntegrityError:
                logger.warning(f"Preferences for user {user_id_str} already exist")
            except Exception as e:
                logger.error(f"Error migrating preferences: {e}")
        
        return count
    
    def _migrate_weekly_reports(self, json_data: Dict[str, Any]) -> int:
        """Migrate weekly reports"""
        weekly_reports = json_data.get("weekly_reports", {})
        count = 0
        
        for user_id_str, user_reports in weekly_reports.items():
            for week_key, report in user_reports.items():
                try:
                    self.cursor.execute("""
                        INSERT INTO weekly_reports (
                            user_id, week_key, week_start, week_end, year, week_number,
                            report_content, input_data, data_days_count,
                            llm_model, generation_attempts, generated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        int(user_id_str),
                        week_key,
                        report.get("week_start"),
                        report.get("week_end"),
                        report.get("year"),
                        report.get("week_number"),
                        report.get("report_content"),
                        report.get("input_data"),
                        report.get("data_days_count"),
                        report.get("llm_model"),
                        report.get("generation_attempts", 1),
                        report.get("generated_at")
                    ))
                    count += 1
                except sqlite3.IntegrityError:
                    logger.warning(f"Weekly report {week_key} for user {user_id_str} already exists")
                except Exception as e:
                    logger.error(f"Error migrating weekly report: {e}")
        
        return count
    
    def _migrate_failed_reports(self, json_data: Dict[str, Any]) -> int:
        """Migrate failed report attempts"""
        failed_reports = json_data.get("failed_reports", {})
        count = 0
        
        for user_id_str, failures in failed_reports.items():
            for failure in failures:
                try:
                    self.cursor.execute("""
                        INSERT INTO failed_reports (
                            user_id, week_start, error_message, model, retry_scheduled
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        int(user_id_str),
                        failure.get("week_start"),
                        failure.get("error"),
                        failure.get("model"),
                        failure.get("retry_scheduled")
                    ))
                    count += 1
                except Exception as e:
                    logger.error(f"Error migrating failed report: {e}")
        
        return count
    
    def _verify_migration(self, json_data: Dict[str, Any], counts: Dict[str, int]) -> bool:
        """Verify that migration was successful"""
        try:
            # Check session count
            json_session_count = len(json_data.get("responses", []))
            db_session_count = self.cursor.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            
            if json_session_count != db_session_count:
                logger.error(f"Session count mismatch: JSON={json_session_count}, DB={db_session_count}")
                return False
            
            # Check user count
            json_user_count = len(json_data.get("unique_users", {}).get("users", {}))
            db_user_count = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            
            # DB might have more users (from sessions), that's OK
            if db_user_count < json_user_count:
                logger.error(f"User count mismatch: JSON={json_user_count}, DB={db_user_count}")
                return False
            
            logger.info("Migration verification passed!")
            return True
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
    
    def _save_migration_metadata(self, counts: Dict[str, int]) -> None:
        """Save migration metadata"""
        metadata = {
            'migration_date': datetime.now().isoformat(),
            'migration_source': self.json_path,
            'migrated_users': counts['users'],
            'migrated_sessions': counts['sessions'],
            'migrated_preferences': counts['preferences'],
            'migrated_reports': counts['weekly_reports']
        }
        
        for key, value in metadata.items():
            self.cursor.execute("""
                INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, str(value)))
        
        self.conn.commit()
    
    def _rollback(self) -> None:
        """Rollback migration by removing SQLite database"""
        try:
            self._close_connection()
            if os.path.exists(self.sqlite_path):
                os.remove(self.sqlite_path)
                logger.info(f"Removed incomplete SQLite database: {self.sqlite_path}")
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    def _close_connection(self) -> None:
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
