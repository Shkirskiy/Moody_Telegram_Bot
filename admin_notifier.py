"""
Admin notification system with rate limiting for error reporting
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config import ADMIN_USER_ID

logger = logging.getLogger(__name__)

class AdminNotifier:
    """Handles admin notifications with daily rate limiting"""
    
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.admin_user_id = ADMIN_USER_ID
        
    def should_notify_admin_today(self) -> bool:
        """
        Check if admin has already been notified today
        
        Returns:
            bool: True if admin hasn't been notified today, False otherwise
        """
        try:
            # Use the new SQLite-compatible method
            notifications = self.data_handler.get_admin_notifications()
            daily_notifications = notifications.get("daily_notifications", {})
            
            today = datetime.now().strftime("%Y-%m-%d")
            today_notification = daily_notifications.get(today, {})
            
            return not today_notification.get("sent", False)
            
        except Exception as e:
            logger.error(f"Error checking admin notification status: {e}")
            return False
    
    def add_issue_for_notification(self, issue_type: str, user_id: int, details: str) -> None:
        """
        Add an issue to the pending admin notifications
        
        Args:
            issue_type: Type of issue (e.g., "llm_failure", "report_generation_failed")
            user_id: Affected user ID
            details: Detailed error message
        """
        try:
            # Use the new SQLite-compatible method
            self.data_handler.add_admin_notification(
                notification_type=issue_type,
                user_id=user_id,
                message=details,
                data={"timestamp": datetime.now().isoformat()}
            )
            
            logger.info(f"Added issue for admin notification: {issue_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding issue for notification: {e}")
    
    async def send_daily_admin_summary(self, bot_application) -> bool:
        """
        Send daily summary of issues to admin
        
        Args:
            bot_application: Telegram bot application for sending messages
            
        Returns:
            bool: True if summary was sent, False otherwise
        """
        try:
            if not self.should_notify_admin_today():
                logger.info("Admin already notified today, skipping")
                return False
            
            # Get notifications using SQLite-compatible method
            notifications = self.data_handler.get_admin_notifications()
            pending_issues = notifications.get("pending_issues", [])
            
            if not pending_issues:
                logger.info("No pending issues to notify admin about")
                return False
            
            # Group issues by type
            issues_by_type = {}
            for issue in pending_issues:
                issue_type = issue.get("type", "unknown")
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append(issue)
            
            # Create summary message
            message = "🔧 <b>Daily Error Report</b>\n\n"
            message += f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            message += f"⚠️ Total issues: {len(pending_issues)}\n\n"
            
            for issue_type, issues in issues_by_type.items():
                message += f"<b>{issue_type.replace('_', ' ').title()}:</b> {len(issues)} occurrence(s)\n"
                
                # Show first 3 issues of each type
                for issue in issues[:3]:
                    user_id = issue.get("user_id", "Unknown")
                    timestamp = issue.get("timestamp", "")
                    details = issue.get("details", "No details")
                    
                    # Format timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = "Unknown time"
                    
                    message += f"  • User {user_id} at {time_str}\n"
                    message += f"    {details[:100]}{'...' if len(details) > 100 else ''}\n"
                
                if len(issues) > 3:
                    message += f"  ... and {len(issues) - 3} more\n"
                
                message += "\n"
            
            message += "💡 <b>Action Required:</b>\n"
            message += "• Check logs for detailed error information\n"
            message += "• Monitor affected users for report generation\n"
            message += "• Verify API keys and LLM service status\n"
            
            # Send to admin
            await bot_application.bot.send_message(
                chat_id=self.admin_user_id,
                text=message,
                parse_mode='HTML'
            )
            
            # Mark as sent and clear pending issues using SQLite-compatible method
            issues_summary = {k: len(v) for k, v in issues_by_type.items()}
            self.data_handler.mark_admin_notified_today(len(pending_issues), issues_summary)
            self.data_handler.clear_pending_admin_issues()
            
            logger.info(f"Sent daily admin summary with {len(pending_issues)} issues")
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily admin summary: {e}")
            return False
    
    def get_notification_status(self) -> Dict[str, Any]:
        """
        Get current notification status and pending issues
        
        Returns:
            Dict with notification status information
        """
        try:
            # Use SQLite-compatible method
            notifications = self.data_handler.get_admin_notifications()
            
            today = datetime.now().strftime("%Y-%m-%d")
            today_notification = notifications.get("daily_notifications", {}).get(today, {})
            pending_issues = notifications.get("pending_issues", [])
            
            return {
                "notified_today": today_notification.get("sent", False),
                "notification_time": today_notification.get("timestamp"),
                "pending_issues_count": len(pending_issues),
                "pending_issues": pending_issues
            }
            
        except Exception as e:
            logger.error(f"Error getting notification status: {e}")
            return {
                "notified_today": False,
                "pending_issues_count": 0,
                "pending_issues": []
            }
    
    async def notify_llm_failure(self, user_id: int, error_message: str, model_name: str, bot_application) -> None:
        """
        Handle LLM failure notification
        
        Args:
            user_id: User whose report generation failed
            error_message: Detailed error message
            model_name: LLM model that failed
            bot_application: Bot application for sending messages
        """
        try:
            # Add issue for batch notification
            details = f"Model: {model_name}, Error: {error_message}"
            self.add_issue_for_notification("llm_failure", user_id, details)
            
            # If admin hasn't been notified today and this is critical, send immediate notification
            if self.should_notify_admin_today():
                # Check if we have enough issues to warrant immediate notification
                status = self.get_notification_status()
                if status["pending_issues_count"] >= 5:  # Threshold for immediate notification
                    await self.send_daily_admin_summary(bot_application)
            
            logger.info(f"Recorded LLM failure for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling LLM failure notification: {e}")
