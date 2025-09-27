"""
AI service for generating weekly mental health reports using OpenRouter API
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import openai
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

logger = logging.getLogger(__name__)

class AIService:
    """Handles AI-powered weekly report generation"""
    
    def __init__(self):
        # Configure OpenAI client for OpenRouter
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        )
        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-5")
        
    def format_session_data(self, sessions: List[Dict[str, Any]]) -> str:
        """
        Format session data to match the required LLM input format
        
        Args:
            sessions: List of user session data
            
        Returns:
            Formatted string for LLM input
        """
        try:
            if not sessions:
                return "No data available for this period."
            
            # Group sessions by date
            sessions_by_date = {}
            for session in sessions:
                date = session.get("date", "")
                if date not in sessions_by_date:
                    sessions_by_date[date] = {"morning": None, "evening": None}
                
                session_type = session.get("session_type", "")
                sessions_by_date[date][session_type] = session
            
            # Format according to required format
            formatted_lines = []
            
            for date in sorted(sessions_by_date.keys()):
                day_sessions = sessions_by_date[date]
                formatted_lines.append(f"\n*Data for* {date}")
                
                # Morning data
                morning_session = day_sessions.get("morning")
                if morning_session:
                    responses = morning_session.get("responses", {})
                    timestamp = morning_session.get("timestamp", "")
                    
                    # Extract time from timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = "unknown"
                    
                    energy = responses.get("energy_level", "N/A")
                    mood = responses.get("mood", "N/A") 
                    intention = responses.get("intention", "N/A")
                    
                    formatted_lines.append(
                        f'Morning data, registered at {time_str} : energy level={energy}, mood={mood}, intention word for the day="{intention}"'
                    )
                
                # Evening data
                evening_session = day_sessions.get("evening")
                if evening_session:
                    responses = evening_session.get("responses", {})
                    timestamp = evening_session.get("timestamp", "")
                    
                    # Extract time from timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = "unknown"
                    
                    mood = responses.get("mood", "N/A")
                    stress = responses.get("stress_level", "N/A")
                    
                    # Handle both old and new day_word formats
                    day_word = responses.get("day_word", "N/A")
                    if day_word == "N/A":
                        # Check for old format: "day": "word_X"
                        day_value = responses.get("day", "N/A")
                        if day_value != "N/A" and day_value.startswith("word_"):
                            # Extract the actual word from "word_X" format
                            day_word = day_value[5:]  # Remove "word_" prefix
                    
                    reflection = responses.get("reflection", "N/A")
                    
                    formatted_lines.append(
                        f'Evening data, registered at {time_str}: mood={mood}, stress={stress}, word that describes this day best="{day_word}", one sentence describing what had the most impact on your mood today="{reflection}"'
                    )
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Error formatting session data: {e}")
            return "Error formatting session data."
    
    def load_system_prompt(self) -> str:
        """Load the system prompt from file"""
        try:
            with open("system_promt/system_promt.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return "You are a licensed-therapist-style analytic coach reviewing mood tracking data."
    
    def build_prompt_with_context(
        self, 
        current_week_data: str, 
        previous_reports: List[str] = None
    ) -> str:
        """
        Build complete prompt with current week data and previous reports context
        
        Args:
            current_week_data: Formatted current week data
            previous_reports: List of previous report contents (up to 3)
            
        Returns:
            Complete prompt for LLM
        """
        try:
            prompt_parts = ["*Current week data:*", current_week_data]
            
            if previous_reports:
                for i, report in enumerate(previous_reports[:3], 1):
                    if report:
                        weeks_ago = "previous" if i == 1 else f"{i} weeks before"
                        prompt_parts.extend([
                            f"\n*Generated report for the {weeks_ago} week*:",
                            report
                        ])
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Error building prompt with context: {e}")
            return current_week_data
    
    async def generate_report(
        self, 
        current_week_data: str, 
        previous_reports: List[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Generate weekly report using AI
        
        Args:
            current_week_data: Formatted current week session data
            previous_reports: List of previous report contents for context
            
        Returns:
            Tuple of (success, report_content_or_error_message, metadata)
            metadata includes: model_used, error_type (if failed)
        """
        metadata = {"model_used": self.model}
        
        try:
            # Load system prompt
            system_prompt = self.load_system_prompt()
            
            # Build user prompt with context
            user_prompt = self.build_prompt_with_context(current_week_data, previous_reports)
            
            logger.info(f"Generating AI report using model: {self.model}")
            
            # Make API call to OpenRouter
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract generated content
            report_content = response.choices[0].message.content
            
            if not report_content or len(report_content.strip()) < 50:
                metadata["error_type"] = "insufficient_content"
                error_msg = "Generated report was too short or empty."
                logger.error(f"Report generation failed: {error_msg}, Model: {self.model}")
                return False, error_msg, metadata
            
            logger.info(f"Successfully generated AI report ({len(report_content)} characters) using model: {self.model}")
            metadata["report_length"] = len(report_content)
            return True, report_content.strip(), metadata
            
        except openai.APITimeoutError as e:
            metadata["error_type"] = "timeout"
            error_msg = f"LLM request timeout: {str(e)}"
            logger.error(f"LLM timeout error with model {self.model}: {error_msg}")
            return False, error_msg, metadata
        except openai.APIError as e:
            metadata["error_type"] = "api_error"
            error_msg = f"LLM API error: {str(e)}"
            logger.error(f"LLM API error with model {self.model}: {error_msg}")
            return False, error_msg, metadata
        except Exception as e:
            metadata["error_type"] = "unknown"
            error_msg = f"Failed to generate AI report: {str(e)}"
            logger.error(f"Unexpected error with model {self.model}: {error_msg}")
            return False, error_msg, metadata
    
    def validate_data_sufficiency(self, sessions: List[Dict[str, Any]]) -> Tuple[bool, int, str]:
        """
        Validate if there's sufficient data for report generation
        
        Args:
            sessions: List of user sessions from the past week
            
        Returns:
            Tuple of (is_sufficient, days_count, message)
        """
        try:
            if not sessions:
                return False, 0, "No data available for the past week."
            
            # Count unique days with data
            unique_dates = set()
            for session in sessions:
                date = session.get("date")
                if date:
                    unique_dates.add(date)
            
            days_count = len(unique_dates)
            
            if days_count < 3:
                return False, days_count, f"Insufficient data: only {days_count} day{'s' if days_count != 1 else ''} with entries. Need at least 3 days."
            
            return True, days_count, f"Sufficient data: {days_count} days with entries."
            
        except Exception as e:
            logger.error(f"Error validating data sufficiency: {e}")
            return False, 0, "Error validating data."
