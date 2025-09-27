"""
Reminder manager for handling scheduled notifications
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import COLORS

logger = logging.getLogger(__name__)

class ReminderManager:
    """Manages reminder scheduling and delivery"""
    
    def __init__(self, data_handler, bot_application=None):
        self.data_handler = data_handler
        self.bot_application = bot_application
        self.scheduler = None
        self.reminder_callback = None
        self.report_manager = None  # Will be set during initialization
        
    async def initialize(self, reminder_callback: Callable):
        """Initialize the reminder scheduler"""
        try:
            self.reminder_callback = reminder_callback
            
            # Configure scheduler
            executors = {
                'default': AsyncIOExecutor(),
            }
            
            job_defaults = {
                'coalesce': False,
                'max_instances': 3
            }
            
            self.scheduler = AsyncIOScheduler(
                executors=executors,
                job_defaults=job_defaults,
                timezone=pytz.UTC
            )
            
            self.scheduler.start()
            logger.info("Reminder scheduler initialized and started")
            
            # Schedule reminders for all users
            await self.schedule_all_user_reminders()
            
        except Exception as e:
            logger.error(f"Failed to initialize reminder manager: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the reminder scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Reminder scheduler shut down")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user reminder preferences"""
        try:
            # Use DataHandler's method that works with both JSON and SQLite
            preferences = self.data_handler.get_user_preferences(user_id)
            
            if preferences is None:
                preferences = {}
            
            # Default preferences
            default_prefs = {
                "timezone": "Europe/Paris",
                "reminders_enabled": True,
                "morning_reminder_time": "07:00",
                "evening_reminder_time": "22:00",
                "morning_enabled": True,
                "evening_enabled": True,
                "last_setup": None
            }
            
            # Merge with defaults
            for key, value in default_prefs.items():
                if key not in preferences:
                    preferences[key] = value
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return self.get_default_preferences()
    
    def get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            "timezone": "Europe/Paris",
            "reminders_enabled": True,
            "morning_reminder_time": "07:00",
            "evening_reminder_time": "22:00",
            "morning_enabled": True,
            "evening_enabled": True,
            "last_setup": None
        }
    
    def save_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """Save user reminder preferences"""
        try:
            # Add last_updated timestamp
            preferences["last_updated"] = datetime.now().isoformat()
            
            # Use DataHandler's method that works with both JSON and SQLite
            self.data_handler.save_user_preferences(user_id, preferences)
            logger.info(f"Saved preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
            raise
    
    async def schedule_user_reminders(self, user_id: int) -> None:
        """Schedule reminders for a specific user"""
        try:
            preferences = self.get_user_preferences(user_id)
            
            if not preferences.get("reminders_enabled", True):
                logger.info(f"Reminders disabled for user {user_id}")
                return
            
            user_tz = pytz.timezone(preferences.get("timezone", "Europe/Paris"))
            
            # Remove existing jobs for this user
            self.cancel_user_reminders(user_id)
            
            # Schedule morning reminder
            if preferences.get("morning_enabled", True):
                morning_time = preferences.get("morning_reminder_time", "07:00")
                hour, minute = map(int, morning_time.split(":"))
                
                self.scheduler.add_job(
                    self._send_reminder,
                    CronTrigger(hour=hour, minute=minute, timezone=user_tz),
                    args=[user_id, "morning"],
                    id=f"morning_{user_id}",
                    replace_existing=True
                )
                logger.info(f"Scheduled morning reminder for user {user_id} at {morning_time} {user_tz}")
            
            # Schedule evening reminder
            if preferences.get("evening_enabled", True):
                evening_time = preferences.get("evening_reminder_time", "22:00")
                hour, minute = map(int, evening_time.split(":"))
                
                self.scheduler.add_job(
                    self._send_reminder,
                    CronTrigger(hour=hour, minute=minute, timezone=user_tz),
                    args=[user_id, "evening"],
                    id=f"evening_{user_id}",
                    replace_existing=True
                )
                logger.info(f"Scheduled evening reminder for user {user_id} at {evening_time} {user_tz}")
            
        except Exception as e:
            logger.error(f"Error scheduling reminders for user {user_id}: {e}")
            raise
    
    def cancel_user_reminders(self, user_id: int) -> None:
        """Cancel all reminders for a user"""
        try:
            job_ids = [f"morning_{user_id}", f"evening_{user_id}"]
            
            for job_id in job_ids:
                try:
                    self.scheduler.remove_job(job_id)
                    logger.info(f"Cancelled job {job_id}")
                except Exception:
                    # Job doesn't exist, that's okay
                    pass
                    
        except Exception as e:
            logger.error(f"Error cancelling reminders for user {user_id}: {e}")
    
    async def schedule_all_user_reminders(self) -> None:
        """Schedule reminders for all users with preferences"""
        try:
            # Get all users with preferences using DataHandler's method
            user_ids = self.data_handler.get_all_users_with_preferences()
            
            for user_id in user_ids:
                await self.schedule_user_reminders(user_id)
                
            logger.info(f"Scheduled reminders for {len(user_ids)} users")
            
        except Exception as e:
            logger.error(f"Error scheduling all user reminders: {e}")
    
    async def _send_reminder(self, user_id: int, reminder_type: str) -> None:
        """Send a reminder to the user"""
        try:
            # Check if user has already completed today's session
            today_sessions = self.data_handler.get_today_sessions(user_id)
            
            # Don't send reminder if session already completed
            if today_sessions.get(reminder_type) is not None:
                logger.info(f"Session {reminder_type} already completed for user {user_id}, skipping reminder")
                return
            
            # Get user preferences for timezone
            preferences = self.get_user_preferences(user_id)
            user_tz = pytz.timezone(preferences.get("timezone", "Europe/Paris"))
            current_user_time = datetime.now(user_tz)
            
            # Create smart reminder message and keyboard
            message, keyboard = self._create_reminder_message(reminder_type, today_sessions, current_user_time)
            
            # Send reminder using the callback
            if self.reminder_callback:
                await self.reminder_callback(user_id, message, keyboard)
                logger.info(f"Sent {reminder_type} reminder to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending {reminder_type} reminder to user {user_id}: {e}")
    
    def _create_reminder_message(self, reminder_type: str, today_sessions: Dict, current_time: datetime) -> tuple:
        """Create reminder message and keyboard based on session status and time"""
        
        # Determine what buttons to show
        show_morning = False
        show_evening = False
        
        if reminder_type == "morning":
            # Morning reminder logic
            show_morning = today_sessions.get("morning") is None
            # Only show evening if it's after 6 PM and not completed
            show_evening = (current_time.hour >= 18 and 
                          today_sessions.get("evening") is None)
            
            base_message = f"""🌅 Good morning! Time for your morning check-in

You haven't completed today's morning reflection yet.

Start your day with a moment of self-awareness! 🌟"""
        
        else:  # evening
            # Evening reminder logic
            show_evening = today_sessions.get("evening") is None
            # Don't show morning button in evening (user missed it for today)
            show_morning = False
            
            base_message = f"""🌙 Good evening! Time to reflect on your day

Your evening review is waiting for you.

Take a moment to process today's experiences! ✨"""
        
        # Create keyboard based on what should be shown
        keyboard_buttons = []
        
        if show_morning:
            keyboard_buttons.append([InlineKeyboardButton(
                "🕘 Start Morning Check-in",
                callback_data="action=start_session&session_type=morning"
            )])
        
        if show_evening:
            keyboard_buttons.append([InlineKeyboardButton(
                "🌙 Start Evening Review", 
                callback_data="action=start_session&session_type=evening"
            )])
        
        # Always show these options
        keyboard_buttons.extend([
            [InlineKeyboardButton("⏰ Remind in 2 hours", callback_data="action=snooze_reminder&hours=2")],
            [InlineKeyboardButton("❌ Skip today", callback_data="action=skip_reminder")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="action=reminder_settings")]
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        return base_message, keyboard
    
    async def snooze_reminder(self, user_id: int, reminder_type: str, hours: int = 2) -> None:
        """Snooze a reminder for specified hours"""
        try:
            preferences = self.get_user_preferences(user_id)
            user_tz = pytz.timezone(preferences.get("timezone", "Europe/Paris"))
            
            # Calculate snooze time
            snooze_time = datetime.now(user_tz) + timedelta(hours=hours)
            
            # Schedule one-time reminder
            job_id = f"snooze_{reminder_type}_{user_id}_{int(datetime.now().timestamp())}"
            
            self.scheduler.add_job(
                self._send_reminder,
                'date',
                run_date=snooze_time,
                args=[user_id, reminder_type],
                id=job_id,
                timezone=user_tz
            )
            
            logger.info(f"Snoozed {reminder_type} reminder for user {user_id} until {snooze_time}")
            
        except Exception as e:
            logger.error(f"Error snoozing reminder: {e}")
    
    def is_first_time_user(self, user_id: int) -> bool:
        """Check if user needs first-time setup"""
        try:
            user_prefs = self.data_handler.get_user_preferences(user_id)
            return user_prefs is None or user_prefs.get("last_setup") is None
        except Exception as e:
            logger.error(f"Error checking first-time user status: {e}")
            return True
    
    def has_completed_onboarding(self, user_id: int) -> bool:
        """Check if user has completed the onboarding process"""
        try:
            user_prefs = self.data_handler.get_user_preferences(user_id)
            return user_prefs is not None and user_prefs.get("onboarding_completed", False)
        except Exception as e:
            logger.error(f"Error checking onboarding status: {e}")
            return False
    
    def complete_onboarding(self, user_id: int, selected_timezone: str = "Europe/Paris") -> None:
        """Complete the onboarding process and set up user with default preferences"""
        try:
            preferences = self.get_default_preferences()
            preferences["timezone"] = selected_timezone
            preferences["onboarding_completed"] = True
            preferences["last_setup"] = datetime.now().isoformat()
            
            self.save_user_preferences(user_id, preferences)
            logger.info(f"Completed onboarding for user {user_id} with timezone {selected_timezone}")
            
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            raise
    
    def get_timezone_keyboard(self, current_selection: str = None) -> InlineKeyboardMarkup:
        """Create timezone selection keyboard"""
        timezones = [
            ("🇪🇸 Madrid/Paris", "Europe/Paris"),
            ("🇬🇧 London", "Europe/London"), 
            ("🇺🇸 New York", "America/New_York"),
            ("🇺🇸 Los Angeles", "America/Los_Angeles"),
            ("🇷🇺 Moscow", "Europe/Moscow"),
            ("🇯🇵 Tokyo", "Asia/Tokyo"),
            ("🇦🇺 Sydney", "Australia/Sydney"),
            ("🇮🇳 Delhi", "Asia/Kolkata"),
            ("🇨🇳 Beijing", "Asia/Shanghai"),
            ("🇧🇷 São Paulo", "America/Sao_Paulo")
        ]
        
        keyboard = []
        for display_name, tz_name in timezones:
            emoji_prefix = "✅ " if tz_name == current_selection else ""
            keyboard.append([InlineKeyboardButton(
                f"{emoji_prefix}{display_name}",
                callback_data=f"action=set_timezone&timezone={tz_name}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="action=settings_menu")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def set_report_manager(self, report_manager) -> None:
        """Set the report manager reference for weekly report scheduling"""
        self.report_manager = report_manager
    
    async def schedule_weekly_reports(self) -> None:
        """Schedule weekly report generation for all users"""
        try:
            if not self.report_manager:
                logger.warning("Report manager not set, cannot schedule weekly reports")
                return
            
            # Schedule Sunday evening report generation (22:30 UTC)
            # This is after most evening check-ins should be completed
            self.scheduler.add_job(
                self._generate_weekly_reports,
                CronTrigger(day_of_week=6, hour=22, minute=30, timezone=pytz.UTC),  # Sunday 22:30 UTC
                id="weekly_reports_sunday",
                replace_existing=True
            )
            
            # Schedule Monday morning fallback (08:00 UTC)
            # For users who didn't get reports on Sunday
            self.scheduler.add_job(
                self._generate_weekly_reports,
                CronTrigger(day_of_week=0, hour=8, minute=0, timezone=pytz.UTC),  # Monday 08:00 UTC
                id="weekly_reports_monday",
                replace_existing=True
            )
            
            logger.info("Scheduled weekly report generation (Sunday 22:30 UTC and Monday 08:00 UTC)")
            
        except Exception as e:
            logger.error(f"Error scheduling weekly reports: {e}")
    
    async def _generate_weekly_reports(self) -> None:
        """Generate weekly reports for all eligible users"""
        try:
            if not self.report_manager:
                logger.error("Report manager not available for weekly report generation")
                return
            
            logger.info("Starting weekly report generation process")
            
            # Generate reports for all users
            results = await self.report_manager.check_and_generate_weekly_reports()
            
            generated_count = len(results.get("generated", []))
            skipped_count = len(results.get("skipped", []))
            
            logger.info(f"Weekly report generation complete: {generated_count} generated, {skipped_count} skipped")
            
            # Log details for debugging
            for msg in results.get("generated", []):
                logger.info(f"GENERATED: {msg}")
            
            for msg in results.get("skipped", []):
                logger.info(f"SKIPPED: {msg}")
            
        except Exception as e:
            logger.error(f"Error in weekly report generation process: {e}")
    
    def get_onboarding_timezone_keyboard(self) -> InlineKeyboardMarkup:
        """Create timezone selection keyboard for onboarding with Paris highlighted as default"""
        timezones = [
            ("🇪🇸 Madrid/Paris", "Europe/Paris"),
            ("🇬🇧 London", "Europe/London"), 
            ("🇺🇸 New York", "America/New_York"),
            ("🇺🇸 Los Angeles", "America/Los_Angeles"),
            ("🇷🇺 Moscow", "Europe/Moscow"),
            ("🇯🇵 Tokyo", "Asia/Tokyo"),
            ("🇦🇺 Sydney", "Australia/Sydney"),
            ("🇮🇳 Delhi", "Asia/Kolkata"),
            ("🇨🇳 Beijing", "Asia/Shanghai"),
            ("🇧🇷 São Paulo", "America/Sao_Paulo")
        ]
        
        keyboard = []
        for display_name, tz_name in timezones:
            # Highlight Paris as the recommended default
            if tz_name == "Europe/Paris":
                display_text = f"✅ {display_name} (Recommended)"
            else:
                display_text = display_name
                
            keyboard.append([InlineKeyboardButton(
                display_text,
                callback_data=f"action=onboarding_timezone&timezone={tz_name}"
            )])
        
        return InlineKeyboardMarkup(keyboard)
