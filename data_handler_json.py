"""
Data handler for managing JSON storage of mental health responses
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from config import DATA_DIR

logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self):
        self.data_file = f"{DATA_DIR}/responses.json"
        self.ensure_data_directory()
        self.ensure_data_file()
    
    def ensure_data_directory(self) -> None:
        """Create data directory if it doesn't exist"""
        try:
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
                logger.info(f"Created data directory: {DATA_DIR}")
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            raise
    
    def ensure_data_file(self) -> None:
        """Create data file with initial structure if it doesn't exist"""
        try:
            if not os.path.exists(self.data_file):
                initial_data = {
                    "responses": [],
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0",
                        "total_sessions": 0
                    }
                }
                with open(self.data_file, 'w') as f:
                    json.dump(initial_data, f, indent=2)
                logger.info(f"Created data file: {self.data_file}")
        except Exception as e:
            logger.error(f"Failed to create data file: {e}")
            raise
    
    def load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            logger.warning("Data file not found, creating new one")
            self.ensure_data_file()
            return self.load_data()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in data file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def save_data(self, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise
    
    def save_session(self, user_id: int, session_type: str, responses: Dict[str, Any]) -> None:
        """
        Save a complete session (morning or evening) with responses
        
        Args:
            user_id: Telegram user ID
            session_type: 'morning' or 'evening'
            responses: Dictionary of question_id -> response
        """
        try:
            data = self.load_data()
            
            session_entry = {
                "user_id": user_id,
                "session_type": session_type,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "responses": responses,
                "session_id": f"{user_id}_{session_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            data["responses"].append(session_entry)
            data["metadata"]["total_sessions"] = len(data["responses"])
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            self.save_data(data)
            logger.info(f"Saved session: {session_entry['session_id']}")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise
    
    def get_user_sessions(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get user sessions from the last N days
        
        Args:
            user_id: Telegram user ID
            days: Number of days to look back
            
        Returns:
            List of session entries
        """
        try:
            data = self.load_data()
            user_sessions = []
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            for session in data["responses"]:
                if session["user_id"] == user_id:
                    session_date = datetime.fromisoformat(session["timestamp"])
                    if session_date >= cutoff_date:
                        user_sessions.append(session)
            
            return sorted(user_sessions, key=lambda x: x["timestamp"])
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    def get_today_sessions(self, user_id: int, user_timezone: str = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get today's sessions for a user (timezone-aware)

        Returns:
            Dictionary with 'morning' and 'evening' keys, values are session data or None
        """
        try:
            # Use user timezone if provided, otherwise use system time
            if user_timezone:
                import pytz
                tz = pytz.timezone(user_timezone)
                today = datetime.now(tz).strftime("%Y-%m-%d")
            else:
                today = datetime.now().strftime("%Y-%m-%d")
            data = self.load_data()
            
            today_sessions = {"morning": None, "evening": None}
            
            for session in data["responses"]:
                if session["user_id"] == user_id and session["date"] == today:
                    today_sessions[session["session_type"]] = session
            
            return today_sessions
            
        except Exception as e:
            logger.error(f"Failed to get today's sessions: {e}")
            return {"morning": None, "evening": None}
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get basic statistics for a user
        
        Returns:
            Dictionary with user statistics
        """
        try:
            data = self.load_data()
            user_sessions = [s for s in data["responses"] if s["user_id"] == user_id]
            
            if not user_sessions:
                return {"total_sessions": 0, "morning_sessions": 0, "evening_sessions": 0}
            
            morning_count = len([s for s in user_sessions if s["session_type"] == "morning"])
            evening_count = len([s for s in user_sessions if s["session_type"] == "evening"])
            
            # Get date range
            dates = [s["date"] for s in user_sessions]
            first_date = min(dates) if dates else None
            last_date = max(dates) if dates else None
            
            return {
                "total_sessions": len(user_sessions),
                "morning_sessions": morning_count,
                "evening_sessions": evening_count,
                "first_session_date": first_date,
                "last_session_date": last_date,
                "unique_dates": len(set(dates))
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_sessions": 0, "morning_sessions": 0, "evening_sessions": 0}
    
    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user preferences
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User preferences dictionary or None if not found
        """
        try:
            data = self.load_data()
            return data.get("user_preferences", {}).get(str(user_id))
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return None
    
    def save_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """
        Save user preferences
        
        Args:
            user_id: Telegram user ID
            preferences: User preferences dictionary
        """
        try:
            data = self.load_data()
            
            if "user_preferences" not in data:
                data["user_preferences"] = {}
            
            data["user_preferences"][str(user_id)] = preferences
            data["user_preferences"][str(user_id)]["last_updated"] = datetime.now().isoformat()
            
            self.save_data(data)
            logger.info(f"Saved preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
            raise
    
    def delete_user_preferences(self, user_id: int) -> None:
        """
        Delete user preferences
        
        Args:
            user_id: Telegram user ID
        """
        try:
            data = self.load_data()
            
            if "user_preferences" in data and str(user_id) in data["user_preferences"]:
                del data["user_preferences"][str(user_id)]
                self.save_data(data)
                logger.info(f"Deleted preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete user preferences: {e}")
            raise
    
    def get_all_users_with_preferences(self) -> List[int]:
        """
        Get list of all user IDs that have preferences stored
        
        Returns:
            List of user IDs
        """
        try:
            data = self.load_data()
            user_preferences = data.get("user_preferences", {})
            return [int(user_id) for user_id in user_preferences.keys()]
        except Exception as e:
            logger.error(f"Failed to get users with preferences: {e}")
            return []
    
    def ensure_data_structure(self) -> None:
        """
        Ensure the data file has the proper structure for preferences and unique users
        """
        try:
            data = self.load_data()
            
            # Ensure user_preferences section exists
            if "user_preferences" not in data:
                data["user_preferences"] = {}
                self.save_data(data)
                logger.info("Added user_preferences section to data structure")
            
            # Ensure unique_users section exists
            if "unique_users" not in data:
                data["unique_users"] = {
                    "count": 0,
                    "users": {}
                }
                self.save_data(data)
                logger.info("Added unique_users section to data structure")
                
        except Exception as e:
            logger.error(f"Failed to ensure data structure: {e}")
            raise
    
    def register_unique_user(self, user_id: int, user_info: dict) -> bool:
        """
        Register a new unique user if under the limit
        
        Args:
            user_id: Telegram user ID
            user_info: Dictionary with user details (username, first_name, last_name)
            
        Returns:
            bool: True if user was registered, False if limit reached
        """
        try:
            data = self.load_data()
            
            # Ensure unique_users structure exists
            if "unique_users" not in data:
                data["unique_users"] = {"count": 0, "users": {}}
            
            # Check if user is already registered
            if str(user_id) in data["unique_users"]["users"]:
                return True  # Already registered, allow access
            
            # Check if we've reached the limit (100 users)
            if data["unique_users"]["count"] >= 100:
                return False  # Limit reached, deny access
            
            # Register new user
            from datetime import datetime
            from config import ADMIN_USER_ID
            data["unique_users"]["users"][str(user_id)] = {
                "username": user_info.get("username", ""),
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
                "first_seen": datetime.now().isoformat(),
                "is_admin": user_id == ADMIN_USER_ID  # Mark admin user from config
            }
            
            data["unique_users"]["count"] = len(data["unique_users"]["users"])
            self.save_data(data)
            
            logger.info(f"Registered new user {user_id} ({user_info.get('first_name', '')} {user_info.get('last_name', '')}) @{user_info.get('username', 'no_username')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register unique user {user_id}: {e}")
            return False
    
    def get_unique_user_count(self) -> int:
        """
        Get the current count of unique users
        
        Returns:
            int: Number of registered unique users
        """
        try:
            data = self.load_data()
            if "unique_users" not in data:
                return 0
            return data["unique_users"]["count"]
        except Exception as e:
            logger.error(f"Failed to get unique user count: {e}")
            return 0
    
    def get_all_unique_users(self) -> dict:
        """
        Get all registered unique users with their details
        
        Returns:
            dict: Dictionary of user_id -> user_info
        """
        try:
            data = self.load_data()
            if "unique_users" not in data or "users" not in data["unique_users"]:
                return {}
            return data["unique_users"]["users"]
        except Exception as e:
            logger.error(f"Failed to get unique users: {e}")
            return {}
    
    def is_registered_user(self, user_id: int) -> bool:
        """
        Check if a user is already registered
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is registered, False otherwise
        """
        try:
            data = self.load_data()
            if "unique_users" not in data or "users" not in data["unique_users"]:
                return False
            return str(user_id) in data["unique_users"]["users"]
        except Exception as e:
            logger.error(f"Failed to check if user {user_id} is registered: {e}")
            return False
    
    def migrate_existing_users(self) -> None:
        """
        Migrate existing users from session data to unique_users system
        """
        try:
            from config import ADMIN_USER_ID
            data = self.load_data()
            
            # Ensure unique_users structure exists
            if "unique_users" not in data:
                data["unique_users"] = {"count": 0, "users": {}}
            
            # Get all unique user IDs from existing session data
            existing_user_ids = set()
            for session in data.get("responses", []):
                existing_user_ids.add(session.get("user_id"))
            
            # Migrate existing users found in session data
            from datetime import datetime
            migrated_count = 0
            
            for user_id in existing_user_ids:
                if user_id and str(user_id) not in data["unique_users"]["users"]:
                    # Try to get user info from session data
                    user_sessions = [s for s in data.get("responses", []) if s.get("user_id") == user_id]
                    
                    # Default user info
                    user_info = {
                        "username": "",
                        "first_name": f"User_{user_id}",
                        "last_name": "",
                        "first_seen": user_sessions[0]["timestamp"] if user_sessions else datetime.now().isoformat(),
                        "is_admin": user_id == ADMIN_USER_ID
                    }
                    
                    # If this is the admin user, set proper info
                    if user_id == ADMIN_USER_ID:
                        user_info.update({
                            "username": "SlavaShkirskiy",
                            "first_name": "Slava",
                            "last_name": ""
                        })
                    
                    data["unique_users"]["users"][str(user_id)] = user_info
                    migrated_count += 1
            
            data["unique_users"]["count"] = len(data["unique_users"]["users"])
            self.save_data(data)
            
            if migrated_count > 0:
                logger.info(f"Migrated {migrated_count} existing users to unique_users system")
                
        except Exception as e:
            logger.error(f"Failed to migrate existing users: {e}")
    
    def get_week_sessions(self, user_id: int, week_start_date: str) -> List[Dict[str, Any]]:
        """
        Get user sessions for a specific week
        
        Args:
            user_id: Telegram user ID
            week_start_date: Week start date in YYYY-MM-DD format (Monday)
            
        Returns:
            List of session entries for that week
        """
        try:
            from datetime import datetime, timedelta
            
            start_date = datetime.strptime(week_start_date, "%Y-%m-%d")
            end_date = start_date + timedelta(days=6)  # Sunday
            
            data = self.load_data()
            week_sessions = []
            
            for session in data["responses"]:
                if session["user_id"] == user_id:
                    session_date = datetime.strptime(session["date"], "%Y-%m-%d")
                    if start_date <= session_date <= end_date:
                        week_sessions.append(session)
            
            return sorted(week_sessions, key=lambda x: x["timestamp"])
            
        except Exception as e:
            logger.error(f"Failed to get week sessions: {e}")
            return []
    
    def save_weekly_report(self, user_id: int, week_start: str, report_content: str, input_data: str, data_days_count: int, llm_model: str = None) -> None:
        """
        Save a weekly AI-generated report
        
        Args:
            user_id: Telegram user ID
            week_start: Week start date in YYYY-MM-DD format
            report_content: Generated AI report content
            input_data: Formatted input data sent to AI
            data_days_count: Number of days with data in this week
            llm_model: LLM model used for generation
        """
        try:
            from datetime import datetime, timedelta
            
            data = self.load_data()
            
            # Ensure weekly_reports structure exists
            if "weekly_reports" not in data:
                data["weekly_reports"] = {}
            
            user_id_str = str(user_id)
            if user_id_str not in data["weekly_reports"]:
                data["weekly_reports"][user_id_str] = {}
            
            # Create week key (format: YYYY_week_NN)
            week_date = datetime.strptime(week_start, "%Y-%m-%d")
            week_end = week_date + timedelta(days=6)
            week_key = f"{week_date.year}_week_{week_date.isocalendar()[1]:02d}"
            
            # Create report entry
            report_entry = {
                "week_start": week_start,
                "week_end": week_end.strftime("%Y-%m-%d"),
                "generated_at": datetime.now().isoformat(),
                "report_content": report_content,
                "input_data": input_data,
                "data_days_count": data_days_count,
                "week_number": week_date.isocalendar()[1],
                "year": week_date.year,
                "llm_model": llm_model,  # Track the model used
                "generation_attempts": 1  # Track number of attempts
            }
            
            data["weekly_reports"][user_id_str][week_key] = report_entry
            
            # Update metadata
            if "metadata" not in data:
                data["metadata"] = {}
            data["metadata"]["last_report_generated"] = datetime.now().isoformat()
            
            self.save_data(data)
            logger.info(f"Saved weekly report for user {user_id}, week {week_key}, model: {llm_model}")
            
        except Exception as e:
            logger.error(f"Failed to save weekly report: {e}")
            raise
    
    def get_weekly_report(self, user_id: int, week_start: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific weekly report
        
        Args:
            user_id: Telegram user ID
            week_start: Week start date in YYYY-MM-DD format
            
        Returns:
            Report data dictionary or None if not found
        """
        try:
            from datetime import datetime
            
            data = self.load_data()
            weekly_reports = data.get("weekly_reports", {})
            user_reports = weekly_reports.get(str(user_id), {})
            
            # Create week key
            week_date = datetime.strptime(week_start, "%Y-%m-%d")
            week_key = f"{week_date.year}_week_{week_date.isocalendar()[1]:02d}"
            
            return user_reports.get(week_key)
            
        except Exception as e:
            logger.error(f"Failed to get weekly report: {e}")
            return None
    
    def get_user_weekly_reports(self, user_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get all weekly reports for a user, sorted by date (newest first)
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of reports to return
            
        Returns:
            List of report dictionaries with week_key added
        """
        try:
            data = self.load_data()
            weekly_reports = data.get("weekly_reports", {})
            user_reports = weekly_reports.get(str(user_id), {})
            
            # Convert to list with week_key included
            reports_list = []
            for week_key, report_data in user_reports.items():
                report_with_key = report_data.copy()
                report_with_key["week_key"] = week_key
                reports_list.append(report_with_key)
            
            # Sort by week_start date (newest first)
            reports_list.sort(key=lambda x: x["week_start"], reverse=True)
            
            if limit:
                reports_list = reports_list[:limit]
            
            return reports_list
            
        except Exception as e:
            logger.error(f"Failed to get user weekly reports: {e}")
            return []
    
    def get_previous_reports_for_context(self, user_id: int, current_week_start: str, count: int = 3) -> List[str]:
        """
        Get previous report contents for AI context
        
        Args:
            user_id: Telegram user ID
            current_week_start: Current week start date to exclude
            count: Number of previous reports to get (max 3)
            
        Returns:
            List of previous report contents (newest first)
        """
        try:
            from datetime import datetime, timedelta
            
            # Get all user reports
            all_reports = self.get_user_weekly_reports(user_id)
            
            # Filter out current week and get only previous reports
            current_week_date = datetime.strptime(current_week_start, "%Y-%m-%d")
            previous_reports = []
            
            for report in all_reports:
                report_week_date = datetime.strptime(report["week_start"], "%Y-%m-%d")
                if report_week_date < current_week_date:
                    previous_reports.append(report["report_content"])
            
            # Return up to 'count' previous reports
            return previous_reports[:count]
            
        except Exception as e:
            logger.error(f"Failed to get previous reports for context: {e}")
            return []
    
    def ensure_weekly_reports_structure(self) -> None:
        """
        Ensure the data file has the proper structure for weekly reports
        """
        try:
            data = self.load_data()
            
            # Ensure weekly_reports section exists
            if "weekly_reports" not in data:
                data["weekly_reports"] = {}
                self.save_data(data)
                logger.info("Added weekly_reports section to data structure")
            
            # Ensure failed_reports section exists
            if "failed_reports" not in data:
                data["failed_reports"] = {}
                self.save_data(data)
                logger.info("Added failed_reports section to data structure")
            
            # Ensure admin_notifications section exists
            if "admin_notifications" not in data:
                data["admin_notifications"] = {
                    "daily_notifications": {},
                    "pending_issues": []
                }
                self.save_data(data)
                logger.info("Added admin_notifications section to data structure")
                
        except Exception as e:
            logger.error(f"Failed to ensure weekly reports structure: {e}")
            raise
    
    def save_failed_report_attempt(self, user_id: int, week_start: str, error_message: str, llm_model: str, retry_scheduled: str = None) -> None:
        """
        Save information about a failed report generation attempt
        
        Args:
            user_id: Telegram user ID
            week_start: Week start date in YYYY-MM-DD format
            error_message: Error message from the failure
            llm_model: LLM model that was attempted
            retry_scheduled: ISO format datetime when retry is scheduled
        """
        try:
            from datetime import datetime
            
            data = self.load_data()
            
            # Ensure failed_reports structure exists
            if "failed_reports" not in data:
                data["failed_reports"] = {}
            
            user_id_str = str(user_id)
            if user_id_str not in data["failed_reports"]:
                data["failed_reports"][user_id_str] = []
            
            # Add failure attempt
            failure_entry = {
                "timestamp": datetime.now().isoformat(),
                "week_start": week_start,
                "error": error_message,
                "model": llm_model,
                "retry_scheduled": retry_scheduled
            }
            
            data["failed_reports"][user_id_str].append(failure_entry)
            
            self.save_data(data)
            logger.info(f"Saved failed report attempt for user {user_id}, week {week_start}")
            
        except Exception as e:
            logger.error(f"Failed to save failed report attempt: {e}")
    
    def get_pending_report_retries(self) -> List[Dict[str, Any]]:
        """
        Get all pending report retries that should be processed
        
        Returns:
            List of pending retries with user_id and week_start
        """
        try:
            from datetime import datetime
            
            data = self.load_data()
            failed_reports = data.get("failed_reports", {})
            
            pending_retries = []
            current_time = datetime.now()
            
            for user_id_str, failures in failed_reports.items():
                for failure in failures:
                    retry_scheduled = failure.get("retry_scheduled")
                    if retry_scheduled:
                        retry_time = datetime.fromisoformat(retry_scheduled)
                        if retry_time <= current_time:
                            pending_retries.append({
                                "user_id": int(user_id_str),
                                "week_start": failure.get("week_start"),
                                "original_error": failure.get("error"),
                                "attempts": len([f for f in failures if f.get("week_start") == failure.get("week_start")])
                            })
            
            return pending_retries
            
        except Exception as e:
            logger.error(f"Failed to get pending report retries: {e}")
            return []
    
    def clear_failed_report_attempts(self, user_id: int, week_start: str) -> None:
        """
        Clear failed report attempts after successful generation
        
        Args:
            user_id: Telegram user ID
            week_start: Week start date that was successfully generated
        """
        try:
            data = self.load_data()
            
            user_id_str = str(user_id)
            if "failed_reports" in data and user_id_str in data["failed_reports"]:
                # Remove failures for this specific week
                data["failed_reports"][user_id_str] = [
                    failure for failure in data["failed_reports"][user_id_str]
                    if failure.get("week_start") != week_start
                ]
                
                # If no more failures for this user, remove the user entry
                if not data["failed_reports"][user_id_str]:
                    del data["failed_reports"][user_id_str]
                
                self.save_data(data)
                logger.info(f"Cleared failed report attempts for user {user_id}, week {week_start}")
                
        except Exception as e:
            logger.error(f"Failed to clear failed report attempts: {e}")
    
    def can_export_data(self, user_id: int) -> tuple[bool, str]:
        """
        Check if user can export data (rate limited to once per week)
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            tuple: (can_export, message) - bool and message for user
        """
        try:
            from datetime import datetime, timedelta
            
            preferences = self.get_user_preferences(user_id)
            if not preferences:
                # First time export
                return True, "Ready to export"
            
            last_export = preferences.get("last_data_export")
            if not last_export:
                # Never exported before
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
            return True, "Ready to export"  # Allow export on error
    
    def update_export_timestamp(self, user_id: int) -> None:
        """
        Update the last data export timestamp for a user
        
        Args:
            user_id: Telegram user ID
        """
        try:
            from datetime import datetime
            
            preferences = self.get_user_preferences(user_id) or {}
            preferences["last_data_export"] = datetime.now().isoformat()
            self.save_user_preferences(user_id, preferences)
            
            logger.info(f"Updated export timestamp for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update export timestamp: {e}")
    
    def export_user_data_to_csv(self, user_id: int) -> Optional[str]:
        """
        Export all user data to a CSV file
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            str: Path to the generated CSV file, or None on error
        """
        try:
            import csv
            import os
            from datetime import datetime
            import tempfile
            
            # Create temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"mental_health_data_{user_id}_{timestamp}.csv"
            csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
            
            # Get all user data
            data = self.load_data()
            user_sessions = [s for s in data.get("responses", []) if s.get("user_id") == user_id]
            user_preferences = self.get_user_preferences(user_id) or {}
            weekly_reports = data.get("weekly_reports", {}).get(str(user_id), {})
            user_info = data.get("unique_users", {}).get("users", {}).get(str(user_id), {})
            
            # Get statistics
            stats = self.get_stats(user_id)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([f"Mental Health Data Export for User {user_id}"])
                writer.writerow([f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([])  # Empty row
                
                # Section 1: User Information
                writer.writerow(["USER INFORMATION"])
                writer.writerow(["Field", "Value"])
                writer.writerow(["Username", user_info.get("username", "Not provided")])
                writer.writerow(["First Name", user_info.get("first_name", "Not provided")])
                writer.writerow(["Last Name", user_info.get("last_name", "Not provided")])
                writer.writerow(["First Seen", user_info.get("first_seen", "Unknown")])
                writer.writerow([])  # Empty row
                
                # Section 2: Statistics
                writer.writerow(["STATISTICS"])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Sessions", stats.get("total_sessions", 0)])
                writer.writerow(["Morning Sessions", stats.get("morning_sessions", 0)])
                writer.writerow(["Evening Sessions", stats.get("evening_sessions", 0)])
                writer.writerow(["Unique Days Tracked", stats.get("unique_dates", 0)])
                writer.writerow(["First Session Date", stats.get("first_session_date", "N/A")])
                writer.writerow(["Last Session Date", stats.get("last_session_date", "N/A")])
                writer.writerow([])  # Empty row
                
                # Section 3: User Preferences
                writer.writerow(["USER PREFERENCES & SETTINGS"])
                writer.writerow(["Setting", "Value"])
                writer.writerow(["Timezone", user_preferences.get("timezone", "Not set")])
                writer.writerow(["Reminders Enabled", user_preferences.get("reminders_enabled", "Not set")])
                writer.writerow(["Morning Reminder Time", user_preferences.get("morning_reminder_time", "Not set")])
                writer.writerow(["Evening Reminder Time", user_preferences.get("evening_reminder_time", "Not set")])
                writer.writerow(["Morning Session Enabled", user_preferences.get("morning_enabled", "Not set")])
                writer.writerow(["Evening Session Enabled", user_preferences.get("evening_enabled", "Not set")])
                writer.writerow(["Onboarding Completed", user_preferences.get("onboarding_completed", False)])
                writer.writerow([])  # Empty row
                
                # Section 4: Session Data
                writer.writerow(["SESSION DATA"])
                writer.writerow(["Date", "Time", "Session Type", "Energy Level", "Mood", "Stress Level", 
                               "Intention", "Day Word", "Reflection"])
                
                # Sort sessions by timestamp
                sorted_sessions = sorted(user_sessions, key=lambda x: x.get("timestamp", ""))
                
                for session in sorted_sessions:
                    responses = session.get("responses", {})
                    
                    # Sanitize text fields to prevent CSV injection
                    def sanitize_csv_field(value):
                        if value is None:
                            return ""
                        value = str(value)
                        # Remove potential CSV injection characters
                        if value.startswith(('=', '+', '-', '@')):
                            value = "'" + value
                        # Escape quotes
                        value = value.replace('"', '""')
                        return value
                    
                    writer.writerow([
                        session.get("date", ""),
                        session.get("time", ""),
                        session.get("session_type", ""),
                        responses.get("energy_level", ""),
                        responses.get("mood", ""),
                        responses.get("stress_level", ""),
                        sanitize_csv_field(responses.get("intention", "")),
                        sanitize_csv_field(responses.get("day_word", "")),
                        sanitize_csv_field(responses.get("reflection", ""))
                    ])
                
                writer.writerow([])  # Empty row
                
                # Section 5: Weekly Reports
                writer.writerow(["WEEKLY AI REPORTS"])
                writer.writerow(["Week Start", "Week End", "Generated At", "Days of Data", "Report Summary"])
                
                # Sort reports by week_start
                sorted_reports = sorted(weekly_reports.items(), 
                                      key=lambda x: x[1].get("week_start", ""), 
                                      reverse=True)
                
                for week_key, report in sorted_reports:
                    # Extract first paragraph of report as summary
                    report_content = report.get("report_content", "")
                    # Remove HTML tags for CSV
                    import re
                    report_summary = re.sub(r'<[^>]+>', '', report_content)
                    # Get first 200 characters as summary
                    if len(report_summary) > 200:
                        report_summary = report_summary[:200] + "..."
                    
                    writer.writerow([
                        report.get("week_start", ""),
                        report.get("week_end", ""),
                        report.get("generated_at", ""),
                        report.get("data_days_count", ""),
                        sanitize_csv_field(report_summary)
                    ])
                
                # Add full reports section
                writer.writerow([])  # Empty row
                writer.writerow(["FULL WEEKLY REPORTS CONTENT"])
                writer.writerow([])
                
                for week_key, report in sorted_reports:
                    writer.writerow([f"Week of {report.get('week_start', '')}"])
                    # Clean HTML from report content
                    report_content = report.get("report_content", "")
                    report_content = re.sub(r'<[^>]+>', '', report_content)
                    # Write report content (may span multiple lines)
                    for line in report_content.split('\n'):
                        if line.strip():
                            writer.writerow([sanitize_csv_field(line.strip())])
                    writer.writerow([])  # Empty row between reports
            
            logger.info(f"Successfully exported data to CSV for user {user_id}: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Failed to export user data to CSV: {e}")
            return None
