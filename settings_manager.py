"""
Settings manager for handling user preferences and settings interface
"""

import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import COLORS
import pytz

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages user settings and preferences interface"""
    
    def __init__(self, reminder_manager):
        self.reminder_manager = reminder_manager
    
    def create_main_settings_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Create main settings menu keyboard"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            
            # Status indicators
            tz_emoji = "🌍"
            reminders_status = "✅" if preferences.get("reminders_enabled", True) else "❌"
            morning_status = "✅" if preferences.get("morning_enabled", True) else "❌"
            evening_status = "✅" if preferences.get("evening_enabled", True) else "❌"
            
            keyboard = [
                [InlineKeyboardButton(
                    f"{tz_emoji} Timezone: {preferences.get('timezone', 'Europe/Paris')}",
                    callback_data="action=timezone_settings"
                )],
                [InlineKeyboardButton(
                    f"📱 Reminders: {reminders_status}",
                    callback_data="action=toggle_reminders"
                )],
                [InlineKeyboardButton(
                    f"🕘 Morning ({preferences.get('morning_reminder_time', '07:00')}): {morning_status}",
                    callback_data="action=morning_settings"
                )],
                [InlineKeyboardButton(
                    f"🌙 Evening ({preferences.get('evening_reminder_time', '22:00')}): {evening_status}",
                    callback_data="action=evening_settings"
                )],
                [InlineKeyboardButton(
                    "🔄 Reset to Defaults",
                    callback_data="action=reset_settings"
                )],
                [InlineKeyboardButton(
                    "◀️ Back to Menu",
                    callback_data="action=main_menu"
                )]
            ]
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"Error creating settings keyboard: {e}")
            return self._create_error_keyboard()
    
    def create_time_picker_keyboard(self, session_type: str, current_time: str = "07:00") -> InlineKeyboardMarkup:
        """Create time picker keyboard for reminder times"""
        try:
            current_hour, current_minute = map(int, current_time.split(":"))
            
            keyboard = []
            
            # Hour selection
            keyboard.append([InlineKeyboardButton(
                f"⏰ Hour: {current_hour:02d}",
                callback_data="time_selector"
            )])
            
            # Hour adjustment buttons
            hour_buttons = []
            for delta in [-2, -1, +1, +2]:
                new_hour = (current_hour + delta) % 24
                hour_buttons.append(InlineKeyboardButton(
                    f"{new_hour:02d}",
                    callback_data=f"action=set_{session_type}_hour&hour={new_hour}&minute={current_minute}"
                ))
            keyboard.append(hour_buttons)
            
            # Minute selection
            keyboard.append([InlineKeyboardButton(
                f"⏰ Minute: {current_minute:02d}",
                callback_data="time_selector"
            )])
            
            # Minute adjustment buttons (15-minute increments)
            minute_buttons = []
            for minute in [0, 15, 30, 45]:
                minute_buttons.append(InlineKeyboardButton(
                    f"{minute:02d}",
                    callback_data=f"action=set_{session_type}_minute&hour={current_hour}&minute={minute}"
                ))
            keyboard.append(minute_buttons)
            
            # Common time presets
            keyboard.append([InlineKeyboardButton(
                "📋 Quick Times",
                callback_data="time_selector"
            )])
            
            if session_type == "morning":
                preset_times = [("6:00", 6, 0), ("7:00", 7, 0), ("8:00", 8, 0), ("9:00", 9, 0)]
            else:  # evening
                preset_times = [("20:00", 20, 0), ("21:00", 21, 0), ("22:00", 22, 0), ("23:00", 23, 0)]
            
            preset_buttons = []
            for time_str, hour, minute in preset_times:
                preset_buttons.append(InlineKeyboardButton(
                    time_str,
                    callback_data=f"action=set_{session_type}_time&hour={hour}&minute={minute}"
                ))
            keyboard.append(preset_buttons)
            
            # Save and cancel buttons
            keyboard.extend([
                [InlineKeyboardButton(
                    "✅ Save Time",
                    callback_data=f"action=save_{session_type}_time&hour={current_hour}&minute={current_minute}"
                )],
                [InlineKeyboardButton(
                    "◀️ Back",
                    callback_data="action=settings_menu"
                )]
            ])
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"Error creating time picker: {e}")
            return self._create_error_keyboard()
    
    def create_session_settings_keyboard(self, session_type: str, user_id: int) -> InlineKeyboardMarkup:
        """Create settings for specific session type (morning/evening)"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            
            enabled_key = f"{session_type}_enabled"
            time_key = f"{session_type}_reminder_time"
            
            enabled = preferences.get(enabled_key, True)
            current_time = preferences.get(time_key, "07:00" if session_type == "morning" else "22:00")
            
            status_emoji = "✅" if enabled else "❌"
            session_emoji = "🕘" if session_type == "morning" else "🌙"
            
            keyboard = [
                [InlineKeyboardButton(
                    f"{session_emoji} {session_type.title()} Reminders: {status_emoji}",
                    callback_data=f"action=toggle_{session_type}_reminders"
                )],
                [InlineKeyboardButton(
                    f"⏰ Time: {current_time}",
                    callback_data=f"action=set_{session_type}_reminder_time"
                )],
                [InlineKeyboardButton(
                    "🔄 Reset to Default",
                    callback_data=f"action=reset_{session_type}_settings"
                )],
                [InlineKeyboardButton(
                    "◀️ Back to Settings",
                    callback_data="action=settings_menu"
                )]
            ]
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"Error creating session settings: {e}")
            return self._create_error_keyboard()
    
    def create_first_time_setup_keyboard(self) -> InlineKeyboardMarkup:
        """Create first-time setup keyboard"""
        keyboard = [
            [InlineKeyboardButton(
                "🌍 Set My Timezone",
                callback_data="action=first_time_timezone"
            )],
            [InlineKeyboardButton(
                "⏰ Configure Reminder Times",
                callback_data="action=first_time_times"
            )],
            [InlineKeyboardButton(
                "✅ Use Default Settings (Paris, 7AM/10PM)",
                callback_data="action=first_time_defaults"
            )]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_first_time_setup_message(self) -> str:
        """Get first-time setup message"""
        return """🌟 <b>Welcome! Let's set up your reminders</b>

To help you stay consistent with your mental health tracking, I can send you daily reminders.

<b>Default Settings:</b>
• 🌍 Timezone: Europe/Paris 
• 🕘 Morning reminder: 07:00
• 🌙 Evening reminder: 22:00

Would you like to customize these settings or use the defaults?"""
    
    def get_settings_message(self, user_id: int) -> str:
        """Get current settings display message"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            
            # Status indicators
            reminders_status = "Enabled ✅" if preferences.get("reminders_enabled", True) else "Disabled ❌"
            morning_status = "On ✅" if preferences.get("morning_enabled", True) else "Off ❌"
            evening_status = "On ✅" if preferences.get("evening_enabled", True) else "Off ❌"
            
            # Get timezone display name
            tz_name = preferences.get("timezone", "Europe/Paris")
            try:
                tz = pytz.timezone(tz_name)
                current_time = datetime.now(tz)
                tz_display = f"{tz_name} (UTC{current_time.strftime('%z')})"
            except:
                tz_display = tz_name
            
            message = f"""⚙️ <b>Reminder Settings</b>

<b>Current Configuration:</b>
🌍 <b>Timezone:</b> {tz_display}
📱 <b>Reminders:</b> {reminders_status}

<b>Schedule:</b>
🕘 <b>Morning:</b> {preferences.get('morning_reminder_time', '07:00')} - {morning_status}
🌙 <b>Evening:</b> {preferences.get('evening_reminder_time', '22:00')} - {evening_status}

Tap any option below to modify your settings:"""
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating settings message: {e}")
            return "⚙️ <b>Settings</b>\n\nSelect an option to configure your preferences:"
    
    def get_timezone_settings_message(self, current_timezone: str = "Europe/Paris") -> str:
        """Get timezone settings message"""
        try:
            tz = pytz.timezone(current_timezone)
            current_time = datetime.now(tz)
            
            message = f"""🌍 <b>Timezone Settings</b>

<b>Current Timezone:</b> {current_timezone}
<b>Local Time:</b> {current_time.strftime('%Y-%m-%d %H:%M:%S')}
<b>UTC Offset:</b> {current_time.strftime('%z')}

Select your timezone from the list below:"""
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating timezone message: {e}")
            return "🌍 <b>Timezone Settings</b>\n\nSelect your timezone:"
    
    async def handle_settings_action(self, action_info: Dict[str, Any], user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
        """Handle settings-related actions and return response message and keyboard"""
        try:
            action = action_info.get("action")
            
            if action == "settings_menu":
                message = self.get_settings_message(user_id)
                keyboard = self.create_main_settings_keyboard(user_id)
                
            elif action == "timezone_settings":
                preferences = self.reminder_manager.get_user_preferences(user_id)
                current_tz = preferences.get("timezone", "Europe/Paris")
                message = self.get_timezone_settings_message(current_tz)
                keyboard = self.reminder_manager.get_timezone_keyboard(current_tz)
                
            elif action == "set_timezone":
                timezone = action_info.get("timezone")
                await self._update_user_timezone(user_id, timezone)
                message = f"✅ Timezone updated to {timezone}!"
                keyboard = self.create_main_settings_keyboard(user_id)
                
            elif action == "toggle_reminders":
                await self._toggle_reminders(user_id)
                message = "✅ Reminder settings updated!"
                keyboard = self.create_main_settings_keyboard(user_id)
                
            elif action in ["morning_settings", "evening_settings"]:
                session_type = action.split("_")[0]
                message = f"⚙️ <b>{session_type.title()} Reminder Settings</b>\n\nConfigure your {session_type} reminder preferences:"
                keyboard = self.create_session_settings_keyboard(session_type, user_id)
                
            elif action.startswith("toggle_") and action.endswith("_reminders"):
                session_type = action.replace("toggle_", "").replace("_reminders", "")
                await self._toggle_session_reminders(user_id, session_type)
                message = f"✅ {session_type.title()} reminder settings updated!"
                keyboard = self.create_session_settings_keyboard(session_type, user_id)
                
            elif action.startswith("set_") and action.endswith("_reminder_time"):
                session_type = action.replace("set_", "").replace("_reminder_time", "")
                preferences = self.reminder_manager.get_user_preferences(user_id)
                current_time = preferences.get(f"{session_type}_reminder_time", "07:00")
                message = f"⏰ Set {session_type} reminder time:\n\nCurrent: {current_time}"
                keyboard = self.create_time_picker_keyboard(session_type, current_time)
                
            elif action.startswith("set_") and action.endswith("_hour"):
                # Handle time picker hour changes: set_morning_hour, set_evening_hour
                session_type = action.replace("set_", "").replace("_hour", "")
                hour = int(action_info.get("hour", 7))
                minute = int(action_info.get("minute", 0))
                current_time = f"{hour:02d}:{minute:02d}"
                message = f"⏰ Set {session_type} reminder time:\n\nCurrent: {current_time}"
                keyboard = self.create_time_picker_keyboard(session_type, current_time)
                
            elif action.startswith("set_") and action.endswith("_minute"):
                # Handle time picker minute changes: set_morning_minute, set_evening_minute
                session_type = action.replace("set_", "").replace("_minute", "")
                hour = int(action_info.get("hour", 7))
                minute = int(action_info.get("minute", 0))
                current_time = f"{hour:02d}:{minute:02d}"
                message = f"⏰ Set {session_type} reminder time:\n\nCurrent: {current_time}"
                keyboard = self.create_time_picker_keyboard(session_type, current_time)
                
            elif action.startswith("set_") and action.endswith("_time"):
                # Handle time picker preset selections: set_morning_time, set_evening_time
                session_type = action.replace("set_", "").replace("_time", "")
                hour = int(action_info.get("hour", 7))
                minute = int(action_info.get("minute", 0))
                current_time = f"{hour:02d}:{minute:02d}"
                message = f"⏰ Set {session_type} reminder time:\n\nCurrent: {current_time}"
                keyboard = self.create_time_picker_keyboard(session_type, current_time)
                
            elif action.startswith("save_") and action.endswith("_time"):
                session_type = action.replace("save_", "").replace("_time", "")
                hour = int(action_info.get("hour", 7))
                minute = int(action_info.get("minute", 0))
                await self._save_reminder_time(user_id, session_type, hour, minute)
                message = f"✅ {session_type.title()} reminder time saved!"
                keyboard = self.create_main_settings_keyboard(user_id)
                
            elif action == "reset_settings":
                await self._reset_user_settings(user_id)
                message = "🔄 Settings reset to defaults!"
                keyboard = self.create_main_settings_keyboard(user_id)
                
            elif action.startswith("reset_") and action.endswith("_settings"):
                # Handle sub-menu reset buttons: reset_morning_settings, reset_evening_settings
                session_type = action.replace("reset_", "").replace("_settings", "")
                await self._reset_session_settings(user_id, session_type)
                message = f"🔄 {session_type.title()} settings reset to defaults!"
                keyboard = self.create_session_settings_keyboard(session_type, user_id)
                
            elif action == "first_time_timezone":
                message = self.get_timezone_settings_message()
                keyboard = self.reminder_manager.get_timezone_keyboard()
                
            elif action == "first_time_times":
                message = "⏰ <b>Configure Reminder Times</b>\n\nChoose which times to configure:"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🕘 Set Morning Time", callback_data="action=set_morning_reminder_time")],
                    [InlineKeyboardButton("🌙 Set Evening Time", callback_data="action=set_evening_reminder_time")],
                    [InlineKeyboardButton("◀️ Back", callback_data="action=settings_menu")]
                ])
                
            elif action == "first_time_defaults":
                await self._setup_default_preferences(user_id)
                message = "✅ Default settings applied! You're all set up!"
                keyboard = self.create_main_settings_keyboard(user_id)
                
            else:
                message = "⚠️ Unknown settings action."
                keyboard = self.create_main_settings_keyboard(user_id)
            
            return message, keyboard
            
        except Exception as e:
            logger.error(f"Error handling settings action {action}: {e}")
            return "❌ An error occurred with settings.", self._create_error_keyboard()
    
    async def _update_user_timezone(self, user_id: int, timezone: str) -> None:
        """Update user's timezone preference"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            preferences["timezone"] = timezone
            self.reminder_manager.save_user_preferences(user_id, preferences)
            
            # Reschedule reminders with new timezone
            await self.reminder_manager.schedule_user_reminders(user_id)
            
        except Exception as e:
            logger.error(f"Error updating timezone: {e}")
            raise
    
    async def _toggle_reminders(self, user_id: int) -> None:
        """Toggle all reminders on/off"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            current_state = preferences.get("reminders_enabled", True)
            preferences["reminders_enabled"] = not current_state
            self.reminder_manager.save_user_preferences(user_id, preferences)
            
            if preferences["reminders_enabled"]:
                # Re-enable reminders
                await self.reminder_manager.schedule_user_reminders(user_id)
            else:
                # Disable reminders
                self.reminder_manager.cancel_user_reminders(user_id)
                
        except Exception as e:
            logger.error(f"Error toggling reminders: {e}")
            raise
    
    async def _toggle_session_reminders(self, user_id: int, session_type: str) -> None:
        """Toggle specific session reminders"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            enabled_key = f"{session_type}_enabled"
            current_state = preferences.get(enabled_key, True)
            preferences[enabled_key] = not current_state
            self.reminder_manager.save_user_preferences(user_id, preferences)
            
            # Reschedule reminders
            await self.reminder_manager.schedule_user_reminders(user_id)
            
        except Exception as e:
            logger.error(f"Error toggling {session_type} reminders: {e}")
            raise
    
    async def _save_reminder_time(self, user_id: int, session_type: str, hour: int, minute: int) -> None:
        """Save reminder time for session type"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            time_key = f"{session_type}_reminder_time"
            preferences[time_key] = f"{hour:02d}:{minute:02d}"
            self.reminder_manager.save_user_preferences(user_id, preferences)
            
            # Reschedule reminders
            await self.reminder_manager.schedule_user_reminders(user_id)
            
        except Exception as e:
            logger.error(f"Error saving reminder time: {e}")
            raise
    
    async def _reset_user_settings(self, user_id: int) -> None:
        """Reset user settings to defaults"""
        try:
            default_prefs = self.reminder_manager.get_default_preferences()
            default_prefs["last_setup"] = datetime.now().isoformat()
            self.reminder_manager.save_user_preferences(user_id, default_prefs)
            
            # Reschedule reminders
            await self.reminder_manager.schedule_user_reminders(user_id)
            
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            raise
    
    async def _setup_default_preferences(self, user_id: int) -> None:
        """Setup default preferences for first-time user"""
        try:
            preferences = self.reminder_manager.get_default_preferences()
            preferences["last_setup"] = datetime.now().isoformat()
            self.reminder_manager.save_user_preferences(user_id, preferences)
            
            # Schedule reminders
            await self.reminder_manager.schedule_user_reminders(user_id)
            
        except Exception as e:
            logger.error(f"Error setting up defaults: {e}")
            raise
    
    async def _reset_session_settings(self, user_id: int, session_type: str) -> None:
        """Reset specific session settings to defaults"""
        try:
            preferences = self.reminder_manager.get_user_preferences(user_id)
            
            # Reset session-specific settings to defaults
            if session_type == "morning":
                preferences["morning_enabled"] = True
                preferences["morning_reminder_time"] = "07:00"
            elif session_type == "evening":
                preferences["evening_enabled"] = True
                preferences["evening_reminder_time"] = "22:00"
            
            self.reminder_manager.save_user_preferences(user_id, preferences)
            
            # Reschedule reminders
            await self.reminder_manager.schedule_user_reminders(user_id)
            
        except Exception as e:
            logger.error(f"Error resetting {session_type} settings: {e}")
            raise
    
    def _create_error_keyboard(self) -> InlineKeyboardMarkup:
        """Create fallback keyboard for errors"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back to Menu", callback_data="action=main_menu")]
        ])
