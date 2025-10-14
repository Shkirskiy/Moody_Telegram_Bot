"""
Data handler with automatic SQLite database management and JSON migration support
"""

import os
import logging
import time
from typing import Dict, List, Any, Optional
from threading import Thread
from datetime import datetime

# Import both backends
from data_handler_json import DataHandler as JSONDataHandler
from data_handler_sqlite import SQLiteDataHandler
from database.migration import DatabaseMigration

logger = logging.getLogger(__name__)

class DataHandler:
    """
    Data handler that uses SQLite as the primary backend with automatic migration
    from legacy JSON format if needed
    """
    
    def __init__(self):
        """Initialize the data handler with automatic migration"""
        self.json_path = "data/responses.json"
        self.sqlite_path = "data/mental_health.db"
        self.backend = None
        self.fallback_backend = None
        self.migration_in_progress = False
        
        # Check and perform automatic migration if needed
        self._initialize_backend()
    
    def _initialize_backend(self) -> None:
        """Initialize the appropriate backend, with automatic migration if needed"""
        try:
            # Check what exists
            json_exists = os.path.exists(self.json_path)
            sqlite_exists = os.path.exists(self.sqlite_path)
            
            logger.info(f"Initializing DataHandler - SQLite exists: {sqlite_exists}, Legacy JSON exists: {json_exists}")
            
            # Case 1: SQLite already exists - use it
            if sqlite_exists:
                logger.info("Using existing SQLite database")
                self.backend = SQLiteDataHandler(self.sqlite_path)
                # Keep JSON as fallback if it exists
                if json_exists:
                    self.fallback_backend = JSONDataHandler()
                return
            
            # Case 2: Only JSON exists - migrate to SQLite
            if json_exists and not sqlite_exists:
                logger.info("Legacy JSON database found - starting automatic migration to SQLite")
                
                # Use JSON backend during migration
                self.backend = JSONDataHandler()
                
                # Start migration in background
                self._perform_automatic_migration()
                
                return
            
            # Case 3: Neither exists - create new SQLite database
            logger.info("No existing database found, creating new SQLite database")
            self.backend = SQLiteDataHandler(self.sqlite_path)
            
        except Exception as e:
            logger.error(f"Error initializing backend: {e}")
            # Fallback to JSON if anything goes wrong
            self.backend = JSONDataHandler()
    
    def _perform_automatic_migration(self) -> None:
        """Perform automatic migration from JSON to SQLite"""
        try:
            # Check if migration is really needed
            migration = DatabaseMigration(
                json_path=self.json_path,
                sqlite_path=self.sqlite_path,
                schema_path="database/schema.sql"
            )
            
            if not migration.needs_migration():
                logger.info("Migration not needed")
                return
            
            # Set flag to indicate migration in progress
            self.migration_in_progress = True
            
            # Log migration start
            logger.info("=" * 60)
            logger.info("Starting automatic migration from JSON to SQLite...")
            logger.info("=" * 60)
            
            # Perform migration
            start_time = time.time()
            success = migration.migrate()
            elapsed = time.time() - start_time
            
            if success:
                logger.info("=" * 60)
                logger.info(f"✅ MIGRATION COMPLETED SUCCESSFULLY in {elapsed:.2f} seconds")
                logger.info("Migration complete - now using SQLite database")
                
                # Switch to SQLite backend
                self.backend = SQLiteDataHandler(self.sqlite_path)
                
                # Keep JSON as fallback
                try:
                    self.fallback_backend = JSONDataHandler()
                except:
                    self.fallback_backend = None
                
            else:
                logger.error("Migration failed - continuing with JSON backend")
                logger.error("=" * 60)
            
            self.migration_in_progress = False
            
        except Exception as e:
            logger.error(f"Error during automatic migration: {e}")
            self.migration_in_progress = False
    
    def __getattr__(self, name):
        """
        Delegate all method calls to the active backend
        This provides transparent access to all DataHandler methods
        """
        # Get the method from the backend
        method = getattr(self.backend, name)
        
        # If it's a callable, wrap it with error handling
        if callable(method):
            def wrapped_method(*args, **kwargs):
                try:
                    # Try primary backend
                    return method(*args, **kwargs)
                except Exception as e:
                    # Log the error
                    logger.error(f"Error in {name} with primary backend: {e}")
                    
                    # Try fallback backend if available
                    if self.fallback_backend and hasattr(self.fallback_backend, name):
                        logger.warning(f"Using fallback backend for {name}")
                        fallback_method = getattr(self.fallback_backend, name)
                        return fallback_method(*args, **kwargs)
                    
                    # Re-raise if no fallback
                    raise
            
            return wrapped_method
        
        # If it's not callable, just return it
        return method
    
    # Explicitly define critical methods for better IDE support
    def load_data(self) -> Dict[str, Any]:
        """Load all data from the active backend"""
        return self.backend.load_data()
    
    def save_data(self, data: Dict[str, Any]) -> None:
        """Save data to the active backend"""
        return self.backend.save_data(data)
    
    def save_session(self, user_id: int, session_type: str, responses: Dict[str, Any]) -> None:
        """Save a complete session with responses"""
        return self.backend.save_session(user_id, session_type, responses)
    
    def get_user_sessions(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get user sessions from the last N days"""
        return self.backend.get_user_sessions(user_id, days)
    
    def get_today_sessions(self, user_id: int, user_timezone: str = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get today's sessions for a user (timezone-aware)"""
        return self.backend.get_today_sessions(user_id, user_timezone)
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """Get basic statistics for a user"""
        return self.backend.get_stats(user_id)
    
    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences"""
        return self.backend.get_user_preferences(user_id)
    
    def save_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """Save user preferences"""
        return self.backend.save_user_preferences(user_id, preferences)
    
    def delete_user_preferences(self, user_id: int) -> None:
        """Delete user preferences"""
        return self.backend.delete_user_preferences(user_id)
    
    def get_all_users_with_preferences(self) -> List[int]:
        """Get list of all user IDs that have preferences stored"""
        return self.backend.get_all_users_with_preferences()
    
    def ensure_data_structure(self) -> None:
        """Ensure the data has proper structure"""
        return self.backend.ensure_data_structure()
    
    def register_unique_user(self, user_id: int, user_info: dict) -> bool:
        """Register a new unique user if under the limit"""
        return self.backend.register_unique_user(user_id, user_info)
    
    def get_unique_user_count(self) -> int:
        """Get the current count of unique users"""
        return self.backend.get_unique_user_count()
    
    def get_all_unique_users(self) -> dict:
        """Get all registered unique users with their details"""
        return self.backend.get_all_unique_users()
    
    def is_registered_user(self, user_id: int) -> bool:
        """Check if a user is already registered"""
        return self.backend.is_registered_user(user_id)
    
    def migrate_existing_users(self) -> None:
        """Migrate existing users (handled automatically)"""
        return self.backend.migrate_existing_users()
    
    def get_week_sessions(self, user_id: int, week_start_date: str) -> List[Dict[str, Any]]:
        """Get user sessions for a specific week"""
        return self.backend.get_week_sessions(user_id, week_start_date)
    
    def save_weekly_report(self, user_id: int, week_start: str, report_content: str, 
                          input_data: str, data_days_count: int, llm_model: str = None) -> None:
        """Save a weekly AI-generated report"""
        return self.backend.save_weekly_report(user_id, week_start, report_content, 
                                              input_data, data_days_count, llm_model)
    
    def get_weekly_report(self, user_id: int, week_start: str) -> Optional[Dict[str, Any]]:
        """Get a specific weekly report"""
        return self.backend.get_weekly_report(user_id, week_start)
    
    def get_user_weekly_reports(self, user_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Get all weekly reports for a user"""
        return self.backend.get_user_weekly_reports(user_id, limit)
    
    def get_previous_reports_for_context(self, user_id: int, current_week_start: str, count: int = 3) -> List[str]:
        """Get previous report contents for AI context"""
        return self.backend.get_previous_reports_for_context(user_id, current_week_start, count)
    
    def ensure_weekly_reports_structure(self) -> None:
        """Ensure weekly reports structure exists"""
        return self.backend.ensure_weekly_reports_structure()
    
    def save_failed_report_attempt(self, user_id: int, week_start: str, error_message: str, 
                                  llm_model: str, retry_scheduled: str = None) -> None:
        """Save information about a failed report generation attempt"""
        return self.backend.save_failed_report_attempt(user_id, week_start, error_message, 
                                                      llm_model, retry_scheduled)
    
    def get_pending_report_retries(self) -> List[Dict[str, Any]]:
        """Get all pending report retries that should be processed"""
        return self.backend.get_pending_report_retries()
    
    def clear_failed_report_attempts(self, user_id: int, week_start: str) -> None:
        """Clear failed report attempts after successful generation"""
        return self.backend.clear_failed_report_attempts(user_id, week_start)
    
    def can_export_data(self, user_id: int) -> tuple[bool, str]:
        """Check if user can export data (rate limited)"""
        return self.backend.can_export_data(user_id)
    
    def update_export_timestamp(self, user_id: int) -> None:
        """Update the last data export timestamp"""
        return self.backend.update_export_timestamp(user_id)
    
    def export_user_data_to_csv(self, user_id: int) -> Optional[str]:
        """Export all user data to a CSV file"""
        return self.backend.export_user_data_to_csv(user_id)
    
    def get_backend_type(self) -> str:
        """Get the current backend type for debugging"""
        if isinstance(self.backend, SQLiteDataHandler):
            return "SQLite"
        else:
            return "JSON"
    
    def is_migration_complete(self) -> bool:
        """Check if migration to SQLite is complete"""
        return os.path.exists(self.sqlite_path) and isinstance(self.backend, SQLiteDataHandler)


# For backward compatibility during import
__all__ = ['DataHandler']
