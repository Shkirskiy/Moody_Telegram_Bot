"""
Main bot application for Telegram Mental Health Bot
"""

import asyncio
import logging
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)

from config import BOT_TOKEN, MESSAGES, COLORS, ADMIN_USER_ID
from data_handler import DataHandler
from question_manager import QuestionManager
from reminder_manager import ReminderManager
from settings_manager import SettingsManager
from report_manager import ReportManager
from utils import (
    setup_logging, 
    authorized_only, 
    safe_message_send, 
    safe_callback_answer,
    log_user_action,
    handle_error,
    sanitize_text_input,
    create_session_summary
)

# Initialize components
setup_logging()
logger = logging.getLogger(__name__)

data_handler = DataHandler()
question_manager = QuestionManager()
reminder_manager = ReminderManager(data_handler)
settings_manager = SettingsManager(reminder_manager)
report_manager = ReportManager(data_handler)

class MentalHealthBot:
    """Main bot class"""
    
    def __init__(self):
        self.application = None
        
    async def setup(self) -> None:
        """Set up the bot application"""
        try:
            # Create application
            self.application = Application.builder().token(BOT_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("stats", self.stats_command))
            self.application.add_handler(CommandHandler("weekly_reports", self.weekly_reports_command))
            self.application.add_handler(CommandHandler("admin_stats", self.admin_stats_command))
            self.application.add_handler(CommandHandler("generate_report", self.generate_report_command))
            self.application.add_handler(CommandHandler("settings", self.settings_command))
            self.application.add_handler(CommandHandler("reminders", self.reminders_command))
            self.application.add_handler(CommandHandler("output_data", self.output_data_command))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
            
            # Error handler
            self.application.add_error_handler(self.error_handler)
            
            # Initialize reminder system
            await self._initialize_reminder_system()
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up bot: {e}")
            raise
    
    @authorized_only
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        try:
            log_user_action(update, "START_COMMAND")
            
            user_id = update.effective_user.id
            
            # Check if this is first-time user who hasn't completed onboarding
            if not reminder_manager.has_completed_onboarding(user_id):
                # Show onboarding flow
                await safe_message_send(
                    update, 
                    MESSAGES["first_time_welcome"], 
                    reply_markup=reminder_manager.get_onboarding_timezone_keyboard()
                )
                return
            
            # User has completed onboarding - show normal main menu
            # Get user data for smart menu
            try:
                preferences = reminder_manager.get_user_preferences(user_id)
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(
                update, 
                MESSAGES["welcome"], 
                reply_markup=keyboard
            )
            
        except Exception as e:
            await handle_error(update, context, f"Error in start command: {e}")
    
    @authorized_only  
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        try:
            log_user_action(update, "HELP_COMMAND")
            
            help_message = """🆘 <b>Mental Health Bot - Complete Guide</b> 🆘

<b>📋 Available Commands:</b>
• <code>/start</code> - Show main menu and bot overview
• <code>/help</code> - Show this comprehensive guide
• <code>/stats</code> - View detailed usage statistics
• <code>/weekly_reports</code> - Browse AI-powered weekly insights
• <code>/generate_report</code> - Generate current week's AI report manually
• <code>/output_data</code> - Export all your data to CSV (once per week limit)
• <code>/settings</code> - Configure reminders, timezone & preferences
• <code>/reminders</code> - Quick toggle reminders on/off

<b>🎯 How Check-ins Work:</b>
1. Choose Morning Check-in or Evening Review
2. Answer questions using buttons or typing text directly
3. Progress through 3-4 questions with visual progress bar
4. All responses automatically saved with timestamps

<b>📝 Question Details:</b>

🕘 <b>Morning Check-in (3 questions):</b>
• ⚡ Energy level (0-10 scale) - How energized you feel
• 😊 Mood (0-10 scale) - Your emotional positivity 
• 🎯 Daily intention (word selection) - Choose from 35+ curated words across 5 categories

🌙 <b>Evening Review (4 questions):</b>
• 😊 Mood (0-10 scale) - Current emotional state
• 😰 Stress level (0-10 scale) - Today's stress intensity
• 📝 Day description (word selection) - Choose from 28+ words across 4 categories
• 💭 Reflection (text input) - One sentence about what most affected your mood

<b>🤖 AI-Powered Weekly Reports:</b>
• Automatically generated every Sunday evening (after 3+ days of data)
• Personalized insights analyzing mood patterns and trends
• Actionable suggestions for the upcoming week
• Browse through previous reports to track long-term progress
• Use <code>/weekly_reports</code> to access your reports

<b>⏰ Smart Reminder System:</b>
• Customizable morning (default 7:00) and evening (default 22:00) reminders
• Full timezone support with automatic scheduling
• Individual session type enable/disable (morning/evening)
• Snooze options (1, 2, or 4 hours)
• First-time setup wizard for new users

<b>📊 Statistics & Tracking:</b>
• Total check-ins completed (morning/evening breakdown)
• Unique days tracked and date ranges
• First and most recent session dates
• Progress tracking with visual indicators

<b>📥 Data Export:</b>
• Use <code>/output_data</code> to export all your data to CSV format
• Includes all sessions, preferences, reports, and statistics
• Rate limited to once per week to prevent system abuse
• Compatible with Excel, Google Sheets, and other spreadsheet tools

<b>⚙️ Settings & Customization:</b>
• Timezone configuration with major cities worldwide
• Individual reminder time settings (hour/minute precision)
• Quick time presets and full time picker interface
• Session-specific settings (morning/evening independently)
• Reset options for individual settings or complete reset

<b>🔒 Privacy & Security:</b>
• Personal use only - bot restricted to authorized users
• All data stored locally in secure SQLite database
• Advanced text validation and content filtering
• Secure session management and data handling

<b>💡 Tips for Best Results:</b>
• Try to maintain consistent check-in times
• Be honest in your responses for accurate tracking
• Complete at least 3 days per week to get AI reports
• Use the weekly reports to identify patterns and improve
• Adjust reminder settings to match your schedule

Take care of yourself and stay mindful! 💚"""
            
            # Get user data for smart menu with check marks
            user_id = update.effective_user.id
            try:
                preferences = reminder_manager.get_user_preferences(user_id)
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, help_message, reply_markup=keyboard)
            
        except Exception as e:
            await handle_error(update, context, f"Error in help command: {e}")
    
    @authorized_only
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command"""
        try:
            log_user_action(update, "STATS_COMMAND")
            
            user_id = update.effective_user.id
            stats = data_handler.get_stats(user_id)
            stats_message = question_manager.format_stats_message(stats)
            
            # Get user data for smart menu with check marks
            try:
                preferences = reminder_manager.get_user_preferences(user_id)
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, stats_message, reply_markup=keyboard)
            
        except Exception as e:
            await handle_error(update, context, f"Error in stats command: {e}")
    
    @authorized_only
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command"""
        try:
            log_user_action(update, "SETTINGS_COMMAND")
            
            user_id = update.effective_user.id
            
            # Check if first-time user
            if reminder_manager.is_first_time_user(user_id):
                message = settings_manager.get_first_time_setup_message()
                keyboard = settings_manager.create_first_time_setup_keyboard()
            else:
                message = settings_manager.get_settings_message(user_id)
                keyboard = settings_manager.create_main_settings_keyboard(user_id)
            
            await safe_message_send(update, message, reply_markup=keyboard)
            
        except Exception as e:
            await handle_error(update, context, f"Error in settings command: {e}")
    
    @authorized_only
    async def reminders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reminders command - quick reminder toggle"""
        try:
            log_user_action(update, "REMINDERS_COMMAND")
            
            user_id = update.effective_user.id
            preferences = reminder_manager.get_user_preferences(user_id)
            
            current_state = preferences.get("reminders_enabled", True)
            preferences["reminders_enabled"] = not current_state
            reminder_manager.save_user_preferences(user_id, preferences)
            
            if preferences["reminders_enabled"]:
                await reminder_manager.schedule_user_reminders(user_id)
                status_msg = "✅ Reminders enabled!"
            else:
                reminder_manager.cancel_user_reminders(user_id)
                status_msg = "❌ Reminders disabled!"
            
            # Get user data for smart menu with check marks
            try:
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, f"{status_msg}\n\nUse /settings for more options.", reply_markup=keyboard)
            
        except Exception as e:
            await handle_error(update, context, f"Error in reminders command: {e}")
    
    @authorized_only
    async def weekly_reports_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /weekly_reports command"""
        try:
            log_user_action(update, "WEEKLY_REPORTS_COMMAND")
            
            user_id = update.effective_user.id
            
            # Get latest report for user
            latest_report = report_manager.get_user_latest_report(user_id)
            
            if not latest_report:
                # No reports available
                no_reports_message = """📊 <b>Weekly Reports</b>

🤖 <b>AI-Powered Weekly Insights</b>

You don't have any weekly reports yet. Reports are automatically generated every Sunday evening after you complete at least 3 days of check-ins during the week.

<b>📋 How it works:</b>
• Complete morning and evening check-ins throughout the week
• After 3+ days of data, a personalized AI report is generated
• Reports include mood patterns, insights, and actionable suggestions
• Browse through your previous reports to track progress over time

<b>💡 Get your first report:</b>
Keep doing your daily check-ins! Your first report will appear here once you have enough data.

Take care of yourself! 💚"""
                
                # Get user data for smart menu
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, no_reports_message, reply_markup=keyboard)
                return
            
            # Display latest report
            await self._display_weekly_report(update, user_id, latest_report["week_start"])
            
        except Exception as e:
            await handle_error(update, context, f"Error in weekly reports command: {e}")
    
    @authorized_only
    async def output_data_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /output_data command - export all user data to CSV with rate limiting"""
        try:
            log_user_action(update, "OUTPUT_DATA_COMMAND")
            
            user_id = update.effective_user.id
            
            # Check rate limiting (once per week)
            can_export, message = data_handler.can_export_data(user_id)
            
            if not can_export:
                # Rate limited - show friendly message
                rate_limit_message = f"""📊 <b>Data Export - Rate Limited</b>

⏰ <b>Export Limit Active</b>

{message}. This limit helps prevent system abuse and ensures smooth operation for all users.

<b>💡 In the meantime, you can:</b>
• View your statistics with /stats
• Browse weekly reports with /weekly_reports
• Check your current settings with /settings

<b>📅 Why the limit?</b>
Data exports are comprehensive and resource-intensive. The once-per-week limit ensures fair usage while giving you regular access to your complete data.

Take care of yourself! 💚"""
                
                # Get user data for smart menu
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, rate_limit_message, reply_markup=keyboard)
                return
            
            # Show processing message
            processing_message = """📊 <b>Exporting Your Data...</b>

⏳ Generating comprehensive CSV file with all your mental health data. This may take a moment...

<b>📋 Your export will include:</b>
• All session check-ins with timestamps
• Complete user preferences and settings
• All AI-generated weekly reports
• Comprehensive statistics and metrics

Please wait..."""
            
            await safe_message_send(update, processing_message)
            
            # Generate CSV file
            csv_path = data_handler.export_user_data_to_csv(user_id)
            
            if csv_path:
                try:
                    # Send the CSV file as a document
                    from datetime import datetime
                    
                    caption = f"""✅ <b>Data Export Complete!</b>

📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
📊 Format: CSV (Compatible with Excel, Google Sheets)
🔒 Privacy: This file contains only your personal data

<b>💡 What's included:</b>
• User information and registration details
• {data_handler.get_stats(user_id).get('total_sessions', 0)} total check-in sessions
• All preferences and reminder settings
• AI-generated weekly reports
• Complete mental health tracking history

<b>📝 Next export available:</b>
In 7 days (weekly limit)

Take care of yourself! 💚"""
                    
                    # Send the file
                    with open(csv_path, 'rb') as csv_file:
                        await update.message.reply_document(
                            document=csv_file,
                            filename=f"mental_health_export_{datetime.now().strftime('%Y%m%d')}.csv",
                            caption=caption,
                            parse_mode='HTML'
                        )
                    
                    # Update export timestamp
                    data_handler.update_export_timestamp(user_id)
                    
                    # Delete temporary file
                    import os
                    try:
                        os.remove(csv_path)
                        logger.info(f"Deleted temporary CSV file: {csv_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete temporary CSV file: {e}")
                    
                    log_user_action(update, "DATA_EXPORTED", f"Success")
                    
                except Exception as e:
                    logger.error(f"Failed to send CSV file: {e}")
                    await safe_message_send(
                        update,
                        "❌ <b>Export Error</b>\n\nThere was an error sending your data file. Please try again later.",
                        parse_mode='HTML'
                    )
            else:
                # Export failed
                await safe_message_send(
                    update,
                    "❌ <b>Export Failed</b>\n\nThere was an error generating your data export. Please try again later or contact support.",
                    parse_mode='HTML'
                )
                log_user_action(update, "DATA_EXPORT_FAILED", "CSV generation error")
            
        except Exception as e:
            await handle_error(update, context, f"Error in output_data command: {e}")
    
    @authorized_only
    async def generate_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /generate_report command - manual trigger for weekly report"""
        try:
            user_id = update.effective_user.id
            
            log_user_action(update, "GENERATE_REPORT_COMMAND")
            
            # Check if report should be generated
            should_generate, reason, week_start = report_manager.should_generate_report(user_id)
            
            if not should_generate:
                await safe_message_send(
                    update,
                    f"""📊 <b>Weekly Report Generation</b>

❌ Cannot generate report at this time.

<b>Reason:</b> {reason}

Your report will be generated automatically when conditions are met.""",
                    parse_mode='HTML'
                )
                return
            
            # Notify that generation is starting
            await safe_message_send(
                update,
                f"""📊 <b>Generating Weekly Report...</b>

⏳ Creating your personalized AI report for week starting {week_start}.

This may take a few seconds...""",
                parse_mode='HTML'
            )
            
            # Generate the report
            success, result = await report_manager.generate_weekly_report(user_id, week_start)
            
            if success:
                # Notify success and display report
                await safe_message_send(
                    update,
                    """✅ <b>Report Generated Successfully!</b>

Your weekly report is ready. Displaying it now...""",
                    parse_mode='HTML'
                )
                
                # Display the report
                await self._display_weekly_report(update, user_id, week_start)
            else:
                # Notify failure
                await safe_message_send(
                    update,
                    f"""❌ <b>Report Generation Failed</b>

Unfortunately, there was an error generating your report:

{result}

The system will automatically retry later.""",
                    parse_mode='HTML'
                )
            
        except Exception as e:
            await handle_error(update, context, f"Error in generate report command: {e}")
    
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin_stats command - restricted to admin user only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            if user_id != ADMIN_USER_ID:
                await safe_message_send(
                    update,
                    "🚫 <b>Access Denied</b>\n\nThis command is restricted to administrators only.",
                    parse_mode='HTML'
                )
                log_user_action(update, "ADMIN_STATS_DENIED")
                return
            
            log_user_action(update, "ADMIN_STATS_COMMAND")
            
            # Get unique users data
            unique_users_data = data_handler.get_all_unique_users()
            user_count = data_handler.get_unique_user_count()
            
            # Create admin stats message
            admin_message = f"""🔧 <b>Admin Statistics Dashboard</b>

📊 <b>User Metrics:</b>
• Total registered users: <b>{user_count}/100</b>
• Available slots: <b>{100 - user_count}</b>
• Registration rate: <b>{(user_count/100)*100:.1f}%</b>

👥 <b>Registered Users:</b>"""
            
            if not unique_users_data:
                admin_message += "\n\n❌ No users registered yet."
            else:
                # Sort users by first_seen date (newest first)
                sorted_users = []
                for user_id_str, user_info in unique_users_data.items():
                    try:
                        from datetime import datetime
                        first_seen = datetime.fromisoformat(user_info.get("first_seen", ""))
                        sorted_users.append((user_id_str, user_info, first_seen))
                    except:
                        # Fallback for invalid dates
                        sorted_users.append((user_id_str, user_info, datetime.min))
                
                sorted_users.sort(key=lambda x: x[2], reverse=True)
                
                for i, (user_id_str, user_info, first_seen) in enumerate(sorted_users, 1):
                    username = user_info.get("username", "")
                    first_name = user_info.get("first_name", "Unknown")
                    last_name = user_info.get("last_name", "")
                    is_admin = user_info.get("is_admin", False)
                    
                    # Format display name
                    display_name = f"{first_name}"
                    if last_name:
                        display_name += f" {last_name}"
                    
                    username_part = f"@{username}" if username else "No username"
                    admin_badge = " 👑" if is_admin else ""
                    
                    # Format date
                    try:
                        date_str = first_seen.strftime("%Y-%m-%d")
                    except:
                        date_str = "Unknown"
                    
                    admin_message += f"\n\n<b>{i}.</b> {display_name}{admin_badge}\n"
                    admin_message += f"   📱 ID: <code>{user_id_str}</code>\n"
                    admin_message += f"   👤 {username_part}\n"
                    admin_message += f"   📅 Joined: {date_str}"
                    
                    # Add session statistics for each user
                    try:
                        user_stats = data_handler.get_stats(int(user_id_str))
                        total_sessions = user_stats.get("total_sessions", 0)
                        if total_sessions > 0:
                            morning_sessions = user_stats.get("morning_sessions", 0)
                            evening_sessions = user_stats.get("evening_sessions", 0)
                            admin_message += f"\n   📊 Sessions: {total_sessions} total ({morning_sessions}🌅 {evening_sessions}🌙)"
                    except:
                        pass
            
            # Add system information
            admin_message += f"""

🔧 <b>System Information:</b>
• Data structure: ✅ Active
• User limit: 100 users maximum
• Current status: {"🟢 Accepting new users" if user_count < 100 else "🔴 At capacity"}

💡 <b>Quick Actions:</b>
• Use /start to test user experience
• Check individual user stats with /stats
• Monitor bot.log for detailed activity"""
            
            # Split message if it's too long (Telegram has a 4096 character limit)
            if len(admin_message) > 4090:
                # Send in chunks
                parts = []
                current_part = ""
                lines = admin_message.split('\n')
                
                for line in lines:
                    if len(current_part + line + '\n') > 4000:
                        parts.append(current_part.strip())
                        current_part = line + '\n'
                    else:
                        current_part += line + '\n'
                
                if current_part.strip():
                    parts.append(current_part.strip())
                
                # Send each part  
                for i, part in enumerate(parts):
                    if i == 0:
                        # Get user data for smart menu with check marks (for admin user)
                        try:
                            preferences = reminder_manager.get_user_preferences(user_id)
                            user_timezone = preferences.get("timezone", "Europe/Paris")
                            today_sessions = data_handler.get_today_sessions(user_id)
                            
                            # Use smart keyboard with session status
                            keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                        except Exception as e:
                            logger.warning(f"Failed to create smart menu, using fallback: {e}")
                            # Fallback to basic keyboard
                            keyboard = question_manager.create_main_menu_keyboard()
                        
                        await safe_message_send(update, part, reply_markup=keyboard)
                    else:
                        await safe_message_send(update, part)
            else:
                # Get user data for smart menu with check marks (for admin user)
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    # Use smart keyboard with session status
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    # Fallback to basic keyboard
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, admin_message, reply_markup=keyboard)
            
        except Exception as e:
            await handle_error(update, context, f"Error in admin stats command: {e}")
    
    @authorized_only
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Parse callback data
            action_info = question_manager.process_callback_data(query.data)
            action = action_info.get("action")
            
            log_user_action(update, f"CALLBACK: {action}", query.data)
            
            # Handle different actions
            if action == "start_session":
                await self._handle_start_session(update, context, action_info)
                
            elif action == "answer_question":
                await self._handle_answer_question(update, context, action_info)
                
            elif action == "text_prompt":
                await self._handle_text_prompt(update, context, action_info)
                
            elif action == "word_selected":
                await self._handle_word_selected(update, context, action_info)
                
            elif action == "show_more_words":
                await self._handle_show_more_words(update, context, action_info)
                
            elif action == "back_to_main_words":
                await self._handle_back_to_main_words(update, context, action_info)
                
            elif action == "main_menu":
                await self._handle_main_menu(update, context)
                
            elif action == "view_stats":
                await self._handle_view_stats(update, context)
                
            elif action == "onboarding_timezone":
                await self._handle_onboarding_timezone(update, context, action_info)
                
            elif action == "view_weekly_reports":
                await self._handle_view_weekly_reports(update, context)
                
            elif action == "show_report":
                await self._handle_show_report(update, context, action_info)
                
            # Handle reminder and settings actions - try settings manager for any other action
            else:
                # Try to handle with settings manager first
                try:
                    await self._handle_settings_actions(update, context, action_info)
                except Exception as e:
                    # If settings manager can't handle it, it's truly unknown
                    logger.error(f"Unknown action or settings error: {action} - {e}")
                    await safe_callback_answer(update, "Unknown action", show_alert=True)
            
            # Always answer the callback query
            await safe_callback_answer(update)
            
        except Exception as e:
            await handle_error(update, context, f"Error handling callback: {e}")
            await safe_callback_answer(update, "An error occurred")
    
    async def _handle_start_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle starting a new session with validation"""
        try:
            user_id = update.effective_user.id
            session_type = action_info.get("session_type")
            
            # Get user's timezone and today's sessions for validation
            preferences = reminder_manager.get_user_preferences(user_id)
            user_timezone = preferences.get("timezone", "Europe/Paris")
            today_sessions = data_handler.get_today_sessions(user_id)
            
            # Validate if session can be started
            can_start, validation_message, validation_keyboard = question_manager.validate_session_start(
                user_id, session_type, today_sessions, user_timezone
            )
            
            if not can_start:
                # Session cannot be started - show validation message
                await safe_message_send(update, validation_message, reply_markup=validation_keyboard)
                log_user_action(update, f"SESSION_BLOCKED", f"{session_type} - {validation_message[:50]}")
                return
            
            # Session is allowed - start new session
            session = question_manager.start_session(user_id, session_type)
            
            # Format and send first question
            message, keyboard = question_manager.format_question_message(session)
            
            # If it's a text question, set up for direct text input
            current_question = session.get_current_question()
            if current_question and current_question["type"] == "text":
                context.user_data["awaiting_text_for"] = current_question["id"]
            
            await safe_message_send(update, message, reply_markup=keyboard)
            
            log_user_action(update, f"STARTED_SESSION", session_type)
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            raise
    
    async def _handle_answer_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle answering a scale question"""
        try:
            user_id = update.effective_user.id
            question_id = action_info.get("question_id")
            answer = int(action_info.get("answer"))
            
            # Get current session
            session = question_manager.get_session(user_id)
            if not session:
                await safe_message_send(update, "❌ No active session found. Please start a new check-in.")
                return
            
            # Save response
            session.save_response(question_id, answer)
            
            # Check if session is complete
            if session.is_complete:
                await self._complete_session(update, context, session)
            else:
                # Show next question
                message, keyboard = question_manager.format_question_message(session)
                
                # If next question is text input, set up for direct text input
                current_question = session.get_current_question()
                if current_question and current_question["type"] == "text":
                    context.user_data["awaiting_text_for"] = current_question["id"]
                
                await safe_message_send(update, message, reply_markup=keyboard)
            
            log_user_action(update, f"ANSWERED", f"{question_id}={answer}")
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            raise
    
    async def _handle_text_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle text input prompt"""
        try:
            question_id = action_info.get("question_id")
            
            # Store the question_id in user context for the next text message
            context.user_data["awaiting_text_for"] = question_id
            
            await safe_message_send(
                update, 
                "✍️ Please type your response below:",
                parse_mode=None
            )
            
            log_user_action(update, f"TEXT_PROMPT", question_id)
            
        except Exception as e:
            logger.error(f"Error handling text prompt: {e}")
            raise
    
    async def _handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle return to main menu"""
        try:
            user_id = update.effective_user.id
            
            # End any active session
            question_manager.end_session(user_id)
            
            # Get user data for smart menu
            try:
                preferences = reminder_manager.get_user_preferences(user_id)
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, MESSAGES["welcome"], reply_markup=keyboard)
            
            log_user_action(update, "MAIN_MENU")
            
        except Exception as e:
            logger.error(f"Error handling main menu: {e}")
            raise
    
    async def _handle_view_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle viewing statistics"""
        try:
            user_id = update.effective_user.id
            stats = data_handler.get_stats(user_id)
            stats_message = question_manager.format_stats_message(stats)
            
            # Get user data for smart menu with check marks
            try:
                preferences = reminder_manager.get_user_preferences(user_id)
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, stats_message, reply_markup=keyboard)
            
            log_user_action(update, "VIEW_STATS")
            
        except Exception as e:
            logger.error(f"Error viewing stats: {e}")
            raise
    
    async def _handle_word_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle word selection from buttons"""
        try:
            user_id = update.effective_user.id
            question_id = action_info.get("question_id")
            word = action_info.get("word")
            
            # Get current session
            session = question_manager.get_session(user_id)
            if not session:
                await safe_message_send(update, "❌ No active session found. Please start a new check-in.")
                return
            
            # Save response
            session.save_response(question_id, word)
            
            # Check if session is complete
            if session.is_complete:
                await self._complete_session(update, context, session)
            else:
                # Show next question
                message, keyboard = question_manager.format_question_message(session)
                
                # If next question is text input, set up for direct text input
                current_question = session.get_current_question()
                if current_question and current_question["type"] == "text":
                    context.user_data["awaiting_text_for"] = current_question["id"]
                
                await safe_message_send(update, message, reply_markup=keyboard)
            
            log_user_action(update, f"WORD_SELECTED", f"{question_id}={word}")
            
        except Exception as e:
            logger.error(f"Error handling word selection: {e}")
            raise
    
    async def _handle_show_more_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle showing extended word list"""
        try:
            user_id = update.effective_user.id
            question_id = action_info.get("question_id")
            
            # Get current session
            session = question_manager.get_session(user_id)
            if not session:
                await safe_message_send(update, "❌ No active session found. Please start a new check-in.")
                return
            
            # Get current question details for message
            current_question = session.get_current_question()
            if not current_question:
                await safe_message_send(update, "❌ Invalid session state.")
                return
            
            current, total = session.get_progress()
            progress_bar = question_manager._create_progress_bar(current, total)
            color = COLORS["morning"] if session.session_type == "morning" else COLORS["evening"]
            
            # Create message for extended word selection
            message = f"""{color} {session.questions['title']}

{progress_bar} Question {current} of {total}

{current_question['emoji']} {current_question['text']}

Choose from the complete word list:"""
            
            # Create extended keyboard
            keyboard = question_manager.create_extended_word_keyboard(question_id)
            
            await safe_message_send(update, message, reply_markup=keyboard)
            
            log_user_action(update, f"SHOW_MORE_WORDS", question_id)
            
        except Exception as e:
            logger.error(f"Error showing more words: {e}")
            raise
    
    async def _handle_back_to_main_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle returning to main word selection"""
        try:
            user_id = update.effective_user.id
            question_id = action_info.get("question_id")
            
            # Get current session
            session = question_manager.get_session(user_id)
            if not session:
                await safe_message_send(update, "❌ No active session found. Please start a new check-in.")
                return
            
            # Get current question details for message
            current_question = session.get_current_question()
            if not current_question:
                await safe_message_send(update, "❌ Invalid session state.")
                return
            
            current, total = session.get_progress()
            progress_bar = question_manager._create_progress_bar(current, total)
            color = COLORS["morning"] if session.session_type == "morning" else COLORS["evening"]
            
            # Create message for main word selection
            message = f"""{color} {session.questions['title']}

{progress_bar} Question {current} of {total}

{current_question['emoji']} {current_question['text']}"""
            
            # Create main word selection keyboard
            keyboard = question_manager.create_word_selection_keyboard(question_id)
            
            await safe_message_send(update, message, reply_markup=keyboard)
            
            log_user_action(update, f"BACK_TO_MAIN_WORDS", question_id)
            
        except Exception as e:
            logger.error(f"Error returning to main words: {e}")
            raise
    
    async def _handle_onboarding_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle timezone selection during onboarding"""
        try:
            user_id = update.effective_user.id
            selected_timezone = action_info.get("timezone", "Europe/Paris")
            
            # Complete onboarding with selected timezone
            reminder_manager.complete_onboarding(user_id, selected_timezone)
            
            # Schedule reminders for the user
            await reminder_manager.schedule_user_reminders(user_id)
            
            # Show explanation message with selected timezone
            explanation_message = MESSAGES["onboarding_explanation"].format(timezone=selected_timezone)
            
            # Get user data for smart menu with check marks (onboarding just completed, user is now set up)
            try:
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, selected_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, explanation_message, reply_markup=keyboard)
            
            log_user_action(update, f"ONBOARDING_COMPLETED", selected_timezone)
            
        except Exception as e:
            logger.error(f"Error handling onboarding timezone selection: {e}")
            await safe_message_send(update, "❌ An error occurred during setup. Please try /start again.")
            raise
    
    @authorized_only
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages (for text input questions)"""
        try:
            user_id = update.effective_user.id
            text = update.message.text.strip()
            
            # Check if we're waiting for text input
            awaiting_question_id = context.user_data.get("awaiting_text_for")
            if not awaiting_question_id:
                # Not expecting text input, show help
                await safe_message_send(
                    update,
                    "ℹ️ Use the buttons in the menu to interact with the bot. Type /help for assistance."
                )
                return
            
            # Get current session
            session = question_manager.get_session(user_id)
            if not session:
                await safe_message_send(update, "❌ No active session found. Please start a new check-in.")
                context.user_data.pop("awaiting_text_for", None)
                return
            
            # Validate text response
            is_valid, validated_text = question_manager.validate_text_response(
                awaiting_question_id, text, session.session_type
            )
            
            if not is_valid:
                await safe_message_send(update, f"❌ {validated_text}")
                return
            
            # Sanitize and save response
            sanitized_text = sanitize_text_input(validated_text)
            session.save_response(awaiting_question_id, sanitized_text)
            
            # Clear the awaiting flag
            context.user_data.pop("awaiting_text_for", None)
            
            # Check if session is complete
            if session.is_complete:
                await self._complete_session(update, context, session)
            else:
                # Show next question
                message, keyboard = question_manager.format_question_message(session)
                
                # If next question is also text input, set up for direct text input
                current_question = session.get_current_question()
                if current_question and current_question["type"] == "text":
                    context.user_data["awaiting_text_for"] = current_question["id"]
                
                await safe_message_send(update, message, reply_markup=keyboard)
            
            log_user_action(update, f"TEXT_RESPONSE", f"{awaiting_question_id}={sanitized_text[:50]}")
            
        except Exception as e:
            await handle_error(update, context, f"Error handling text message: {e}")
    
    async def _complete_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session) -> None:
        """Complete a session and save data"""
        try:
            user_id = update.effective_user.id
            
            # Save session data
            data_handler.save_session(user_id, session.session_type, session.responses)
            
            # End session
            question_manager.end_session(user_id)
            
            # Create summary
            summary = create_session_summary(session.responses, session.session_type)
            
            completion_message = f"""✅ <b>Check-in Complete!</b>

{summary}

Your responses have been saved successfully!

Take care of yourself! 💚"""
            
            # Get user data for smart menu with check marks (session just completed, so refresh data)
            try:
                preferences = reminder_manager.get_user_preferences(user_id)
                user_timezone = preferences.get("timezone", "Europe/Paris")
                today_sessions = data_handler.get_today_sessions(user_id)
                
                # Use smart keyboard with session status
                keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to create smart menu, using fallback: {e}")
                # Fallback to basic keyboard
                keyboard = question_manager.create_main_menu_keyboard()
            
            await safe_message_send(update, completion_message, reply_markup=keyboard)
            
            log_user_action(update, f"COMPLETED_SESSION", session.session_type)
            
            # Check if this was Sunday evening session - trigger report generation
            if session.session_type == "evening":
                from datetime import datetime
                import pytz
                
                # Get user's timezone and check if it's Sunday
                user_tz = pytz.timezone(preferences.get("timezone", "Europe/Paris"))
                current_user_time = datetime.now(user_tz)
                
                # Check if it's Sunday (weekday() returns 6 for Sunday)
                if current_user_time.weekday() == 6:
                    # Check if report should be generated
                    should_generate, reason, week_start = report_manager.should_generate_report(user_id)
                    
                    if should_generate:
                        # Notify user that report is being generated
                        await safe_message_send(
                            update,
                            """📊 <b>Generating Your Weekly Report...</b>

🎉 Congratulations on completing your week! 

⏳ I'm now analyzing your data and creating your personalized AI report. This will take just a few seconds...""",
                            parse_mode='HTML'
                        )
                        
                        # Generate report asynchronously
                        asyncio.create_task(self._generate_and_notify_report(user_id, week_start))
                        
                        logger.info(f"Triggered weekly report generation for user {user_id} after Sunday evening completion")
            
        except Exception as e:
            logger.error(f"Error completing session: {e}")
            await safe_message_send(update, "✅ Session completed, but there was an error saving. Please try again.")
            raise
    
    async def _generate_and_notify_report(self, user_id: int, week_start: str) -> None:
        """Generate weekly report and notify user when ready"""
        try:
            # Generate the report
            success, result = await report_manager.generate_weekly_report(user_id, week_start)
            
            if success:
                # Notify user that report is ready
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text="""✅ <b>Your Weekly Report is Ready!</b>

📊 Your personalized AI-powered weekly insights have been generated.

Use /weekly_reports to view your report now, or check it later at your convenience.

Great job completing this week! 🌟""",
                    parse_mode='HTML'
                )
                logger.info(f"Successfully generated and notified user {user_id} about weekly report")
            else:
                # Log the error but don't notify user - the fallback will handle it
                logger.error(f"Failed to generate immediate report for user {user_id}: {result}")
                
        except Exception as e:
            logger.error(f"Error in generate_and_notify_report for user {user_id}: {e}")
    
    async def _display_weekly_report(self, update: Update, user_id: int, week_start: str) -> None:
        """Display a weekly report with navigation"""
        try:
            # Get the report
            report_data = data_handler.get_weekly_report(user_id, week_start)
            
            if not report_data:
                no_report_message = """📊 <b>Weekly Report</b>

❌ <b>Report not found</b>

This report may have been deleted or there was an error retrieving it.

Use /weekly_reports to see your available reports.

Take care of yourself! 💚"""
                
                # Get user data for smart menu
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, no_report_message, reply_markup=keyboard)
                return
            
            # Format the report header
            date_header = report_manager.format_report_date_header(week_start)
            report_content = report_data["report_content"]
            
            # Get navigation info
            nav_info = report_manager.get_report_navigation_info(user_id, week_start)
            
            # Create header with navigation info
            header = f"""📊 <b>Weekly Report</b>

📅 <b>{date_header}</b>
📋 Report {nav_info['current_index']} of {nav_info['total_reports']}
🤖 Generated: {report_data.get('data_days_count', 'N/A')} days of data

"""
            
            full_report = header + report_content
            
            # Create navigation keyboard
            keyboard = []
            nav_row = []
            
            if nav_info["has_previous"]:
                nav_row.append(InlineKeyboardButton(
                    "← Previous Week", 
                    callback_data=f"action=show_report&week={nav_info['previous_week']}"
                ))
            
            if nav_info["has_next"]:
                nav_row.append(InlineKeyboardButton(
                    "Next Week →", 
                    callback_data=f"action=show_report&week={nav_info['next_week']}"
                ))
            
            if nav_row:
                keyboard.append(nav_row)
            
            # Add main menu button
            keyboard.append([InlineKeyboardButton(
                "🏠 Back to Main Menu", 
                callback_data="main_menu"
            )])
            
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Split message if too long
            if len(full_report) > 4000:
                parts = self._split_message(full_report)
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:  # Last part gets the keyboard
                        await safe_message_send(update, part, reply_markup=reply_markup)
                    else:
                        await safe_message_send(update, part)
            else:
                await safe_message_send(update, full_report, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error displaying weekly report: {e}")
            await safe_message_send(update, "❌ An error occurred while loading the report.")
    
    def _split_message(self, message: str, max_length: int = 4000) -> List[str]:
        """Split a long message into smaller parts"""
        if len(message) <= max_length:
            return [message]
        
        parts = []
        current_part = ""
        lines = message.split('\n')
        
        for line in lines:
            # If adding this line would exceed the limit
            if len(current_part + line + '\n') > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = line + '\n'
                else:
                    # Single line is too long, need to split it
                    while len(line) > max_length:
                        parts.append(line[:max_length])
                        line = line[max_length:]
                    current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    async def _handle_view_weekly_reports(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle viewing weekly reports (button callback)"""
        try:
            user_id = update.effective_user.id
            
            # Get latest report for user
            latest_report = report_manager.get_user_latest_report(user_id)
            
            if not latest_report:
                # No reports available
                no_reports_message = """📊 <b>Weekly Reports</b>

🤖 <b>AI-Powered Weekly Insights</b>

You don't have any weekly reports yet. Reports are automatically generated every Sunday evening after you complete at least 3 days of check-ins during the week.

<b>📋 How it works:</b>
• Complete morning and evening check-ins throughout the week
• After 3+ days of data, a personalized AI report is generated
• Reports include mood patterns, insights, and actionable suggestions
• Browse through your previous reports to track progress over time

<b>💡 Get your first report:</b>
Keep doing your daily check-ins! Your first report will appear here once you have enough data.

Take care of yourself! 💚"""
                
                # Get user data for smart menu
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, no_reports_message, reply_markup=keyboard)
                return
            
            # Display latest report
            await self._display_weekly_report(update, user_id, latest_report["week_start"])
            
            log_user_action(update, "VIEW_WEEKLY_REPORTS")
            
        except Exception as e:
            logger.error(f"Error viewing weekly reports: {e}")
            await safe_message_send(update, "❌ An error occurred while loading weekly reports.")
    
    async def _handle_show_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle showing a specific weekly report"""
        try:
            user_id = update.effective_user.id
            week_start = action_info.get("week")
            
            if not week_start:
                await safe_message_send(update, "❌ Invalid report selection.")
                return
            
            # Display the requested report
            await self._display_weekly_report(update, user_id, week_start)
            
            log_user_action(update, "SHOW_REPORT", week_start)
            
        except Exception as e:
            logger.error(f"Error showing report: {e}")
            await safe_message_send(update, "❌ An error occurred while loading the report.")
    
    async def _initialize_reminder_system(self) -> None:
        """Initialize the reminder system"""
        try:
            # Ensure data structure exists
            data_handler.ensure_data_structure()
            data_handler.ensure_weekly_reports_structure()
            
            # Initialize reminder manager with callback
            await reminder_manager.initialize(self._send_reminder_callback)
            
            # Set bot application reference in report manager
            report_manager.set_bot_application(self.application)
            
            # Set up weekly report scheduling
            reminder_manager.set_report_manager(report_manager)
            await reminder_manager.schedule_weekly_reports()
            
            # Schedule retry processing (every 6 hours)
            await self._schedule_retry_processing()
            
            # Schedule daily admin summary (once per day at 10:00 UTC)
            await self._schedule_admin_summary()
            
            logger.info("Reminder system, weekly report scheduling, and failure handling initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize reminder system: {e}")
            raise
    
    async def _schedule_retry_processing(self) -> None:
        """Schedule periodic processing of failed report retries"""
        try:
            from apscheduler.triggers.interval import IntervalTrigger
            
            # Process retries every 6 hours
            reminder_manager.scheduler.add_job(
                report_manager.process_pending_retries,
                IntervalTrigger(hours=6),
                id="process_report_retries",
                replace_existing=True
            )
            
            # Also process any pending retries on startup
            await report_manager.process_pending_retries()
            
            logger.info("Scheduled retry processing every 6 hours")
            
        except Exception as e:
            logger.error(f"Failed to schedule retry processing: {e}")
    
    async def _schedule_admin_summary(self) -> None:
        """Schedule daily admin summary notifications"""
        try:
            from apscheduler.triggers.cron import CronTrigger
            import pytz
            
            # Send admin summary daily at 10:00 UTC
            reminder_manager.scheduler.add_job(
                lambda: asyncio.create_task(
                    report_manager.admin_notifier.send_daily_admin_summary(self.application)
                ),
                CronTrigger(hour=10, minute=0, timezone=pytz.UTC),
                id="daily_admin_summary",
                replace_existing=True
            )
            
            logger.info("Scheduled daily admin summary at 10:00 UTC")
            
        except Exception as e:
            logger.error(f"Failed to schedule admin summary: {e}")
    
    async def _send_reminder_callback(self, user_id: int, message: str, keyboard) -> None:
        """Callback function for sending reminder messages"""
        try:
            # Send reminder message to user
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            log_user_action(None, "REMINDER_SENT", f"user_id={user_id}")
            
        except Exception as e:
            logger.error(f"Failed to send reminder to user {user_id}: {e}")
    
    async def _handle_settings_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_info: Dict[str, Any]) -> None:
        """Handle settings and reminder related actions"""
        try:
            user_id = update.effective_user.id
            action = action_info.get("action")
            
            if action == "snooze_reminder":
                hours = int(action_info.get("hours", 2))
                # Determine reminder type from context or default to morning
                reminder_type = action_info.get("reminder_type", "morning")
                
                await reminder_manager.snooze_reminder(user_id, reminder_type, hours)
                
                message = f"⏰ Reminder snoozed for {hours} hours!"
                
                # Get user data for smart menu with check marks
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    # Use smart keyboard with session status
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    # Fallback to basic keyboard
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, message, reply_markup=keyboard)
                
            elif action == "skip_reminder":
                message = "❌ Today's reminder skipped."
                
                # Get user data for smart menu with check marks
                try:
                    preferences = reminder_manager.get_user_preferences(user_id)
                    user_timezone = preferences.get("timezone", "Europe/Paris")
                    today_sessions = data_handler.get_today_sessions(user_id)
                    
                    # Use smart keyboard with session status
                    keyboard = question_manager.create_smart_main_menu_keyboard(user_id, today_sessions, user_timezone)
                except Exception as e:
                    logger.warning(f"Failed to create smart menu, using fallback: {e}")
                    # Fallback to basic keyboard
                    keyboard = question_manager.create_main_menu_keyboard()
                
                await safe_message_send(update, message, reply_markup=keyboard)
                
            elif action == "reminder_settings":
                # Redirect to main settings
                message = settings_manager.get_settings_message(user_id)
                keyboard = settings_manager.create_main_settings_keyboard(user_id)
                await safe_message_send(update, message, reply_markup=keyboard)
                
            else:
                # Handle other settings actions using settings manager
                message, keyboard = await settings_manager.handle_settings_action(action_info, user_id)
                await safe_message_send(update, message, reply_markup=keyboard)
                
            log_user_action(update, f"SETTINGS_ACTION", action)
            
        except Exception as e:
            logger.error(f"Error handling settings action {action}: {e}")
            await safe_message_send(update, "❌ An error occurred with settings.")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Only try to handle error if update is a proper Update object
        if isinstance(update, Update) and update.effective_user:
            try:
                await handle_error(update, context, "An unexpected error occurred")
            except Exception as e:
                logger.error(f"Failed to handle error properly: {e}")
                # Last resort - try to send a simple message
                try:
                    if update.message:
                        await update.message.reply_text("❌ An error occurred. Please try /start")
                    elif update.callback_query:
                        await update.callback_query.answer("❌ An error occurred. Please try /start", show_alert=True)
                except:
                    logger.error("Could not send any error message to user")
        else:
            logger.error("Could not process error - invalid update object or missing user info")
    
    async def start_bot(self) -> None:
        """Start the bot"""
        try:
            await self.setup()
            
            logger.info("Starting Mental Health Bot...")
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise
        finally:
            # Shutdown reminder system
            if reminder_manager:
                await reminder_manager.shutdown()
                
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

async def main():
    """Main function"""
    bot = MentalHealthBot()
    await bot.start_bot()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
