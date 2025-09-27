"""
Report manager for handling weekly AI report generation and scheduling
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from ai_service import AIService
from data_handler import DataHandler
from admin_notifier import AdminNotifier

logger = logging.getLogger(__name__)

class ReportManager:
    """Manages weekly report generation and scheduling"""
    
    def __init__(self, data_handler: DataHandler):
        self.data_handler = data_handler
        self.ai_service = AIService()
        self.admin_notifier = AdminNotifier(data_handler)
        self.bot_application = None  # Will be set during initialization
        
    def get_current_week_start(self) -> str:
        """
        Get the start date (Monday) of the current week
        
        Returns:
            Week start date in YYYY-MM-DD format
        """
        today = datetime.now()
        # Calculate Monday of current week (weekday() returns 0 for Monday)
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        return monday.strftime("%Y-%m-%d")
    
    def get_previous_week_start(self) -> str:
        """
        Get the start date (Monday) of the previous week
        
        Returns:
            Previous week start date in YYYY-MM-DD format
        """
        current_week_start = datetime.strptime(self.get_current_week_start(), "%Y-%m-%d")
        previous_week_start = current_week_start - timedelta(days=7)
        return previous_week_start.strftime("%Y-%m-%d")
    
    def should_generate_report(self, user_id: int) -> Tuple[bool, str, str]:
        """
        Check if a weekly report should be generated for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (should_generate, reason, week_start_date)
        """
        try:
            # Get previous week dates
            previous_week_start = self.get_previous_week_start()
            
            # Check if report already exists for previous week
            existing_report = self.data_handler.get_weekly_report(user_id, previous_week_start)
            if existing_report:
                return False, "Report already exists for previous week", previous_week_start
            
            # Check if there's sufficient data for previous week
            week_sessions = self.data_handler.get_week_sessions(user_id, previous_week_start)
            is_sufficient, days_count, message = self.ai_service.validate_data_sufficiency(week_sessions)
            
            if not is_sufficient:
                return False, message, previous_week_start
            
            return True, f"Ready to generate report ({days_count} days of data)", previous_week_start
            
        except Exception as e:
            logger.error(f"Error checking if report should be generated: {e}")
            return False, f"Error: {str(e)}", ""
    
    async def generate_weekly_report(self, user_id: int, week_start: str, is_retry: bool = False) -> Tuple[bool, str]:
        """
        Generate a weekly report for a user
        
        Args:
            user_id: Telegram user ID
            week_start: Week start date in YYYY-MM-DD format
            is_retry: Whether this is a retry attempt
            
        Returns:
            Tuple of (success, report_content_or_error_message)
        """
        try:
            # Get specific week data
            sessions = self.data_handler.get_week_sessions(user_id, week_start)
            
            # Validate data sufficiency
            is_sufficient, days_count, message = self.ai_service.validate_data_sufficiency(sessions)
            if not is_sufficient:
                return False, message
            
            # Format session data for AI
            formatted_data = self.ai_service.format_session_data(sessions)
            
            # Get previous reports for context
            previous_reports = self.data_handler.get_previous_reports_for_context(user_id, week_start)
            
            # Generate AI report with enhanced error handling
            success, report_content, metadata = await self.ai_service.generate_report(formatted_data, previous_reports)
            
            if not success:
                # Handle failure - schedule retry and notify
                if not is_retry:
                    await self._handle_report_generation_failure(
                        user_id, 
                        week_start, 
                        report_content,  # Error message
                        metadata.get("model_used", "unknown"),
                        metadata.get("error_type", "unknown")
                    )
                return False, report_content  # report_content contains error message
            
            # Save report
            try:
                self.data_handler.save_weekly_report(
                    user_id=user_id,
                    week_start=week_start,
                    report_content=report_content,
                    input_data=formatted_data,
                    data_days_count=days_count,
                    llm_model=metadata.get("model_used")
                )
                logger.info(f"Saved weekly report for user {user_id}, week {week_start}, model: {metadata.get('model_used')}")
                
                # Clear any failed attempts for this week
                self.data_handler.clear_failed_report_attempts(user_id, week_start)
                
            except Exception as e:
                logger.error(f"Failed to save weekly report: {e}")
                return False, f"Report generated but failed to save: {str(e)}"
            
            return True, report_content
            
        except Exception as e:
            error_msg = f"Failed to generate weekly report: {str(e)}"
            logger.error(error_msg)
            
            # Handle unexpected failure
            if not is_retry:
                await self._handle_report_generation_failure(
                    user_id,
                    week_start,
                    error_msg,
                    self.ai_service.model,
                    "unexpected_error"
                )
            
            return False, error_msg
    
    async def _handle_report_generation_failure(
        self, 
        user_id: int, 
        week_start: str, 
        error_message: str, 
        model_name: str,
        error_type: str
    ) -> None:
        """
        Handle failure in report generation
        
        Args:
            user_id: User whose report failed
            week_start: Week start date
            error_message: Error message from failure
            model_name: LLM model that was used
            error_type: Type of error (timeout, api_error, etc.)
        """
        try:
            # Schedule retry in 2 days
            retry_date = datetime.now() + timedelta(days=2)
            retry_scheduled = retry_date.isoformat()
            
            # Save failure information
            self.data_handler.save_failed_report_attempt(
                user_id=user_id,
                week_start=week_start,
                error_message=error_message,
                llm_model=model_name,
                retry_scheduled=retry_scheduled
            )
            
            # Notify user about the failure and retry
            await self._notify_user_of_failure(user_id, week_start, retry_date)
            
            # Add to admin notifications
            if self.bot_application:
                await self.admin_notifier.notify_llm_failure(
                    user_id=user_id,
                    error_message=f"{error_type}: {error_message}",
                    model_name=model_name,
                    bot_application=self.bot_application
                )
            
            logger.info(f"Scheduled retry for user {user_id}, week {week_start} at {retry_scheduled}")
            
        except Exception as e:
            logger.error(f"Error handling report generation failure: {e}")
    
    async def _notify_user_of_failure(self, user_id: int, week_start: str, retry_date: datetime) -> None:
        """
        Notify user about report generation failure and scheduled retry
        
        Args:
            user_id: User to notify
            week_start: Week that failed
            retry_date: When retry is scheduled
        """
        try:
            if not self.bot_application:
                logger.warning("Bot application not set, cannot notify user")
                return
            
            # Format retry date nicely
            retry_str = retry_date.strftime("%A, %B %d at %H:%M")
            
            message = f"""⚠️ <b>Report Generation Issue</b>

Unfortunately, I couldn't generate your weekly report for the week starting {week_start} due to a temporary issue with the AI service.

🔄 <b>Automatic Retry Scheduled</b>
Your report will be automatically retried on {retry_str}.

You don't need to do anything - I'll try again automatically and notify you once the report is ready.

If you continue to experience issues, the admin has been notified and will investigate.

Take care! 💚"""
            
            await self.bot_application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Notified user {user_id} about report failure and retry")
            
        except Exception as e:
            logger.error(f"Error notifying user about failure: {e}")
    
    async def process_pending_retries(self) -> None:
        """
        Process any pending report retries
        Called periodically to check for and process failed reports
        """
        try:
            pending_retries = self.data_handler.get_pending_report_retries()
            
            if not pending_retries:
                return
            
            logger.info(f"Processing {len(pending_retries)} pending report retries")
            
            for retry_info in pending_retries:
                user_id = retry_info["user_id"]
                week_start = retry_info["week_start"]
                attempts = retry_info.get("attempts", 1)
                
                # Limit retry attempts to 3
                if attempts >= 3:
                    logger.warning(f"Max retry attempts reached for user {user_id}, week {week_start}")
                    continue
                
                logger.info(f"Retrying report for user {user_id}, week {week_start} (attempt {attempts + 1})")
                
                # Try to generate report again
                success, result = await self.generate_weekly_report(
                    user_id, 
                    week_start, 
                    is_retry=True
                )
                
                if success:
                    # Notify user of successful retry
                    await self._notify_user_retry_success(user_id, week_start)
                else:
                    logger.error(f"Retry failed for user {user_id}, week {week_start}: {result}")
                    
                    # If this was the last attempt, notify user
                    if attempts >= 2:
                        await self._notify_user_max_retries(user_id, week_start)
            
        except Exception as e:
            logger.error(f"Error processing pending retries: {e}")
    
    async def _notify_user_retry_success(self, user_id: int, week_start: str) -> None:
        """Notify user that retry was successful"""
        try:
            if not self.bot_application:
                return
            
            message = f"""✅ <b>Report Successfully Generated!</b>

Good news! Your weekly report for the week starting {week_start} has been successfully generated after the retry.

Use /weekly_reports to view your report.

Take care! 💚"""
            
            await self.bot_application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error notifying user about retry success: {e}")
    
    async def _notify_user_max_retries(self, user_id: int, week_start: str) -> None:
        """Notify user that max retries have been reached"""
        try:
            if not self.bot_application:
                return
            
            message = f"""❌ <b>Report Generation Failed</b>

Unfortunately, I was unable to generate your weekly report for the week starting {week_start} after multiple attempts.

This may be due to ongoing issues with the AI service. The admin has been notified and will investigate.

Your future reports should generate normally. If you continue to experience issues, please contact the admin.

Take care! 💚"""
            
            await self.bot_application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error notifying user about max retries: {e}")
    
    def set_bot_application(self, bot_application) -> None:
        """Set bot application reference for sending notifications"""
        self.bot_application = bot_application
        logger.info("Bot application set in ReportManager")
    
    def get_user_latest_report(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the latest weekly report for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Latest report dictionary or None if no reports exist
        """
        try:
            reports = self.data_handler.get_user_weekly_reports(user_id, limit=1)
            return reports[0] if reports else None
        except Exception as e:
            logger.error(f"Error getting latest report: {e}")
            return None
    
    def get_report_navigation_info(self, user_id: int, current_report_week: str) -> Dict[str, Any]:
        """
        Get navigation information for report browsing
        
        Args:
            user_id: Telegram user ID
            current_report_week: Current report week start date
            
        Returns:
            Dictionary with navigation info (has_previous, has_next, previous_week, next_week, etc.)
        """
        try:
            # Get all user reports
            all_reports = self.data_handler.get_user_weekly_reports(user_id)
            
            if not all_reports:
                return {
                    "has_previous": False,
                    "has_next": False,
                    "current_index": 0,
                    "total_reports": 0
                }
            
            # Find current report index
            current_index = -1
            for i, report in enumerate(all_reports):
                if report["week_start"] == current_report_week:
                    current_index = i
                    break
            
            if current_index == -1:
                # Current report not found, assume it's the latest
                current_index = 0
            
            # Calculate navigation info
            has_previous = current_index > 0
            has_next = current_index < len(all_reports) - 1
            
            previous_week = None
            next_week = None
            
            if has_previous:
                previous_week = all_reports[current_index - 1]["week_start"]
            
            if has_next:
                next_week = all_reports[current_index + 1]["week_start"]
            
            return {
                "has_previous": has_previous,
                "has_next": has_next,
                "previous_week": previous_week,
                "next_week": next_week,
                "current_index": current_index + 1,  # 1-based for display
                "total_reports": len(all_reports)
            }
            
        except Exception as e:
            logger.error(f"Error getting navigation info: {e}")
            return {
                "has_previous": False,
                "has_next": False,
                "current_index": 0,
                "total_reports": 0
            }
    
    def format_report_date_header(self, week_start: str) -> str:
        """
        Format a week start date into a readable header
        
        Args:
            week_start: Week start date in YYYY-MM-DD format
            
        Returns:
            Formatted date string (e.g., "Week of January 15-21, 2025")
        """
        try:
            start_date = datetime.strptime(week_start, "%Y-%m-%d")
            end_date = start_date + timedelta(days=6)
            
            # Format as "Week of January 15-21, 2025"
            if start_date.month == end_date.month:
                # Same month
                return f"Week of {start_date.strftime('%B %d')}-{end_date.strftime('%d, %Y')}"
            else:
                # Different months
                return f"Week of {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
                
        except Exception as e:
            logger.error(f"Error formatting report date header: {e}")
            return f"Week of {week_start}"
    
    async def check_and_generate_weekly_reports(self) -> Dict[str, List[str]]:
        """
        Check all users and generate weekly reports where needed
        Used by the weekly scheduler
        
        Returns:
            Dictionary with 'generated' and 'skipped' lists of user info
        """
        try:
            # Get all users with preferences (active users)
            active_users = self.data_handler.get_all_users_with_preferences()
            
            generated = []
            skipped = []
            
            for user_id in active_users:
                try:
                    should_generate, reason, week_start = self.should_generate_report(user_id)
                    
                    if should_generate:
                        success, result = await self.generate_weekly_report(user_id, week_start)
                        if success:
                            generated.append(f"User {user_id}: Generated report for {week_start}")
                            logger.info(f"Generated weekly report for user {user_id}")
                        else:
                            skipped.append(f"User {user_id}: Generation failed - {result}")
                    else:
                        skipped.append(f"User {user_id}: {reason}")
                        
                except Exception as e:
                    skipped.append(f"User {user_id}: Error - {str(e)}")
                    logger.error(f"Error generating report for user {user_id}: {e}")
            
            logger.info(f"Weekly report check complete: {len(generated)} generated, {len(skipped)} skipped")
            
            return {
                "generated": generated,
                "skipped": skipped
            }
            
        except Exception as e:
            logger.error(f"Error in weekly report check: {e}")
            return {
                "generated": [],
                "skipped": [f"System error: {str(e)}"]
            }
