"""
Question manager for handling interactive questionnaires with UI components
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, time
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import MORNING_QUESTIONS, EVENING_QUESTIONS, SCALE_BUTTONS, COLORS, WORD_CATEGORIES, DAY_WORD_CATEGORIES

logger = logging.getLogger(__name__)

class QuestionSession:
    """Manages a single question session (morning or evening)"""
    
    def __init__(self, session_type: str, user_id: int):
        self.session_type = session_type
        self.user_id = user_id
        self.current_question_index = 0
        self.responses = {}
        self.questions = self._get_questions()
        self.is_complete = False
        
    def _get_questions(self) -> Dict[str, Any]:
        """Get question set based on session type"""
        if self.session_type == "morning":
            return MORNING_QUESTIONS
        elif self.session_type == "evening":
            return EVENING_QUESTIONS
        else:
            raise ValueError(f"Invalid session type: {self.session_type}")
    
    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Get the current question"""
        if self.current_question_index >= len(self.questions["questions"]):
            return None
        return self.questions["questions"][self.current_question_index]
    
    def save_response(self, question_id: str, response: Any) -> bool:
        """Save a response and move to next question"""
        try:
            self.responses[question_id] = response
            self.current_question_index += 1
            
            if self.current_question_index >= len(self.questions["questions"]):
                self.is_complete = True
            
            return True
        except Exception as e:
            logger.error(f"Failed to save response: {e}")
            return False
    
    def get_progress(self) -> Tuple[int, int]:
        """Get current progress (current_question, total_questions)"""
        return self.current_question_index + 1, len(self.questions["questions"])


class QuestionManager:
    """Manages question sessions and UI generation"""
    
    def __init__(self):
        self.active_sessions = {}  # user_id -> QuestionSession
        
    def start_session(self, user_id: int, session_type: str) -> QuestionSession:
        """Start a new question session"""
        try:
            session = QuestionSession(session_type, user_id)
            self.active_sessions[user_id] = session
            logger.info(f"Started {session_type} session for user {user_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise
    
    def get_session(self, user_id: int) -> Optional[QuestionSession]:
        """Get active session for user"""
        return self.active_sessions.get(user_id)
    
    def end_session(self, user_id: int) -> Optional[QuestionSession]:
        """End and return session for user"""
        return self.active_sessions.pop(user_id, None)
    
    def create_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Create the main menu keyboard for choosing session type"""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{COLORS['morning']} 🕘 Morning Check-in", 
                    callback_data="start_morning"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{COLORS['evening']} 🌙 Evening Review", 
                    callback_data="start_evening"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Weekly Reports", 
                    callback_data="view_weekly_reports"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_scale_keyboard(self, question_id: str) -> InlineKeyboardMarkup:
        """Create keyboard for scale questions (0-10)"""
        keyboard = []
        
        for row in SCALE_BUTTONS:
            keyboard_row = []
            for button in row:
                callback_data = f"answer_{question_id}_{button['callback_data']}"
                keyboard_row.append(
                    InlineKeyboardButton(button["text"], callback_data=callback_data)
                )
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_text_input_keyboard(self, question_id: str) -> InlineKeyboardMarkup:
        """Create keyboard for text input questions"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "✍️ Type your response below", 
                    callback_data=f"text_prompt_{question_id}"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_word_selection_keyboard(self, question_id: str) -> InlineKeyboardMarkup:
        """Create keyboard for primary word selection with appropriate layout"""
        keyboard = []
        
        # Determine which word categories to use based on question_id
        if question_id == "intention":
            # Morning intention - use WORD_CATEGORIES with 2-2-2 layout (5 words + More)
            main_words = WORD_CATEGORIES["main_words"]
            
            # Add first 4 main words (2 per row)
            for i in range(0, 4, 2):
                row = []
                for j in range(2):
                    if i + j < len(main_words) and i + j < 4:
                        word_data = main_words[i + j]
                        callback_data = f"word_{question_id}_{word_data['word']}"
                        row.append(
                            InlineKeyboardButton(word_data["text"], callback_data=callback_data)
                        )
                keyboard.append(row)
            
            # Add 5th word and More button on the same row
            last_row = []
            if len(main_words) >= 5:
                word_data = main_words[4]  # 5th word (Energetic)
                callback_data = f"word_{question_id}_{word_data['word']}"
                last_row.append(
                    InlineKeyboardButton(word_data["text"], callback_data=callback_data)
                )
            
            last_row.append(
                InlineKeyboardButton(
                    "➕ More", 
                    callback_data=f"more_words_{question_id}"
                )
            )
            keyboard.append(last_row)
            
        elif question_id == "day_word":
            # Evening day_word - use DAY_WORD_CATEGORIES with 2-2-1 layout (4 words + More alone)
            main_words = DAY_WORD_CATEGORIES["main_words"]
            
            # Add all 4 main words (2 per row)
            for i in range(0, len(main_words), 2):
                row = []
                for j in range(2):
                    if i + j < len(main_words):
                        word_data = main_words[i + j]
                        callback_data = f"word_{question_id}_{word_data['word']}"
                        row.append(
                            InlineKeyboardButton(word_data["text"], callback_data=callback_data)
                        )
                keyboard.append(row)
            
            # Add More button alone on its own row
            keyboard.append([
                InlineKeyboardButton(
                    "➕ More", 
                    callback_data=f"more_words_{question_id}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_extended_word_keyboard(self, question_id: str) -> InlineKeyboardMarkup:
        """Create keyboard for extended word selection (categorized list)"""
        keyboard = []
        
        # Determine which word categories to use based on question_id
        if question_id == "intention":
            word_categories = WORD_CATEGORIES["categories"]
        elif question_id == "day_word":
            word_categories = DAY_WORD_CATEGORIES["categories"]
        else:
            word_categories = WORD_CATEGORIES["categories"]  # fallback
        
        # Add category sections
        for category_id, category_data in word_categories.items():
            words = category_data["words"]
            
            # Add category header button (clickable, selects first word of category)
            if words:
                main_word = words[0]  # Use first word as the main category word
                category_button_text = f"{category_data['emoji']} {main_word}"
                callback_data = f"word_{question_id}_{main_word}"
                keyboard.append([
                    InlineKeyboardButton(category_button_text, callback_data=callback_data)
                ])
                
                # Add remaining words from this category (2 per row)
                remaining_words = words[1:]  # Skip the first word since it's the header
                for i in range(0, len(remaining_words), 2):
                    row = []
                    for j in range(2):
                        if i + j < len(remaining_words):
                            word = remaining_words[i + j]
                            callback_data = f"word_{question_id}_{word}"
                            row.append(
                                InlineKeyboardButton(word, callback_data=callback_data)
                            )
                    keyboard.append(row)
        
        # Add Back button
        keyboard.append([
            InlineKeyboardButton(
                "← Back", 
                callback_data=f"back_to_main_{question_id}"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_question_message(self, session: QuestionSession) -> Tuple[str, InlineKeyboardMarkup]:
        """Format the current question message and keyboard"""
        try:
            current_question = session.get_current_question()
            if not current_question:
                return self._format_completion_message(session)
            
            # Build message with simpler formatting to avoid markdown issues
            current, total = session.get_progress()
            progress_bar = self._create_progress_bar(current, total)
            
            color = COLORS["morning"] if session.session_type == "morning" else COLORS["evening"]
            
            if current_question["type"] == "text":
                # For text questions, add instruction directly in message
                message = f"""{color} {session.questions['title']}

{progress_bar} Question {current} of {total}

{current_question['emoji']} {current_question['text']}

✍️ Please type your response below:"""
                keyboard = None  # No keyboard needed for text input
            elif current_question["type"] == "word_selection":
                # For word selection questions, show normal message
                message = f"""{color} {session.questions['title']}

{progress_bar} Question {current} of {total}

{current_question['emoji']} {current_question['text']}"""
                keyboard = self.create_word_selection_keyboard(current_question["id"])
            else:
                # For scale questions, show normal message
                message = f"""{color} {session.questions['title']}

{progress_bar} Question {current} of {total}

{current_question['emoji']} {current_question['text']}"""
                keyboard = self.create_scale_keyboard(current_question["id"])
            
            return message.strip(), keyboard
            
        except Exception as e:
            logger.error(f"Failed to format question message: {e}")
            raise
    
    def _format_completion_message(self, session: QuestionSession) -> Tuple[str, InlineKeyboardMarkup]:
        """Format completion message"""
        color = COLORS["morning"] if session.session_type == "morning" else COLORS["evening"]
        
        message = f"""{color} Session Complete! {COLORS['success']}

Thank you for completing your {session.session_type} check-in!

Your responses have been saved for analysis.

Take care of yourself! 💚"""
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "🏠 Back to Main Menu", 
                    callback_data="main_menu"
                )
            ]
        ]
        
        return message.strip(), InlineKeyboardMarkup(keyboard)
    
    def _create_progress_bar(self, current: int, total: int) -> str:
        """Create a visual progress bar"""
        filled = "🟢" if current <= total else "🔵"
        empty = "⚪"
        
        bar_length = min(total, 10)  # Max 10 circles
        filled_count = int((current - 1) / total * bar_length) if total > 0 else 0
        
        bar = filled * filled_count + empty * (bar_length - filled_count)
        return f"Progress: {bar} ({current}/{total})"
    
    def process_callback_data(self, callback_data: str) -> Dict[str, Any]:
        """Parse callback data and return action information"""
        try:
            # Handle settings format: action=morning_settings&param=value
            if callback_data.startswith("action="):
                # Parse action=something&param=value format
                params = {}
                parts = callback_data.split("&")
                action = parts[0].replace("action=", "")
                
                # Extract additional parameters if present
                for part in parts[1:]:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        params[key] = value
                
                # Return the action with all parameters
                result = {"action": action}
                result.update(params)
                return result
            
            elif callback_data.startswith("start_"):
                session_type = callback_data.replace("start_", "")
                return {"action": "start_session", "session_type": session_type}
            
            elif callback_data.startswith("answer_"):
                # Fixed parsing: answer_energy_level_8 -> ["answer", "energy", "level", "8"]
                parts = callback_data.split("_")
                if len(parts) >= 3:
                    # Extract question_id and answer properly
                    question_id = "_".join(parts[1:-1])  # "energy_level"
                    answer = parts[-1]                   # "8"
                    return {
                        "action": "answer_question", 
                        "question_id": question_id, 
                        "answer": answer
                    }
            
            elif callback_data.startswith("text_prompt_"):
                question_id = callback_data.replace("text_prompt_", "")
                return {"action": "text_prompt", "question_id": question_id}
            
            elif callback_data.startswith("word_"):
                # Handle word selection: word_intention_Calm or word_day_word_Tired
                # Remove the "word_" prefix first
                remaining = callback_data[5:]  # Remove "word_"
                
                # For day_word questions, we need to handle the underscore in the question_id
                if remaining.startswith("day_word_"):
                    question_id = "day_word"
                    word = remaining[9:]  # Remove "day_word_"
                elif remaining.startswith("intention_"):
                    question_id = "intention" 
                    word = remaining[10:]  # Remove "intention_"
                else:
                    # Fallback to original logic for other questions
                    parts = callback_data.split("_", 2)
                    if len(parts) == 3:
                        question_id = parts[1]
                        word = parts[2]
                    else:
                        logger.error(f"Invalid word callback format: {callback_data}")
                        return {"action": "error"}
                
                return {
                    "action": "word_selected", 
                    "question_id": question_id, 
                    "word": word
                }
            
            elif callback_data.startswith("more_words_"):
                question_id = callback_data.replace("more_words_", "")
                return {"action": "show_more_words", "question_id": question_id}
            
            elif callback_data.startswith("back_to_main_"):
                question_id = callback_data.replace("back_to_main_", "")
                return {"action": "back_to_main_words", "question_id": question_id}
            
            elif callback_data == "main_menu":
                return {"action": "main_menu"}
            
            elif callback_data == "view_stats":
                return {"action": "view_stats"}
            
            elif callback_data == "view_weekly_reports":
                return {"action": "view_weekly_reports"}
            
            return {"action": "unknown", "callback_data": callback_data}
            
        except Exception as e:
            logger.error(f"Failed to process callback data: {e}")
            return {"action": "error"}
    
    def validate_text_response(self, question_id: str, text: str, session_type: str) -> Tuple[bool, str]:
        """Validate text response based on question requirements with enhanced security"""
        try:
            # Import the security validation function
            from utils import is_safe_text_content
            
            if not text or not text.strip():
                return False, "Please provide a valid response."
            
            text = text.strip()
            
            # Get question details
            questions = MORNING_QUESTIONS if session_type == "morning" else EVENING_QUESTIONS
            question = next((q for q in questions["questions"] if q["id"] == question_id), None)
            
            if not question:
                return False, "Invalid question."
            
            # Layer 1: Security validation (most important - check first)
            question_type = "reflection" if question_id == "reflection" else "word"
            is_safe, security_message = is_safe_text_content(text, question_type)
            
            if not is_safe:
                # Log security violations for monitoring
                logger.warning(f"Security validation failed for question {question_id}: {security_message}")
                return False, security_message
            
            # Layer 2: Question-specific validation (now redundant with security layer but kept for extra validation)
            if question_id == "intention" or question_id == "day_word":
                # The security layer already handles this, but we can add specific guidance
                words = text.split()
                if len(words) > 3:
                    return False, f"Please provide just a word or short phrase (you provided {len(words)} words)."
                
                if len(text) > 50:
                    return False, "Please keep your response shorter (max 50 characters)."
            
            elif question_id == "reflection":
                # The security layer already handles this, but we can add specific guidance
                if len(text) > 200:
                    return False, "Please keep your reflection concise (max 200 characters)."
                
                # Additional reflection-specific checks
                if len(text.split()) < 3:
                    return False, "Please provide a more complete reflection (at least a few words)."
            
            return True, text
            
        except Exception as e:
            logger.error(f"Failed to validate text response: {e}")
            return False, "An error occurred while processing your response."
    
    def format_stats_message(self, stats: Dict[str, Any]) -> str:
        """Format statistics message"""
        try:
            if stats["total_sessions"] == 0:
                return f"""📊 <b>Your Statistics</b>

You haven't completed any check-ins yet.

Start your first check-in to begin tracking your mental health journey! 🌟"""
            
            message = f"""📊 <b>Your Statistics</b>

🎯 <b>Total Check-ins:</b> {stats['total_sessions']}
🕘 <b>Morning Sessions:</b> {stats['morning_sessions']}
🌙 <b>Evening Sessions:</b> {stats['evening_sessions']}
📅 <b>Days Tracked:</b> {stats['unique_dates']}
📆 <b>First Check-in:</b> {stats.get('first_session_date', 'N/A')}
📆 <b>Latest Check-in:</b> {stats.get('last_session_date', 'N/A')}

Keep up the great work! 💪"""
            
            return message.strip()
            
        except Exception as e:
            logger.error(f"Failed to format stats message: {e}")
            return "❌ Could not load statistics."
    
    def is_session_allowed(self, session_type: str, user_timezone: str) -> Tuple[bool, str]:
        """
        Check if a session is allowed based on time windows and user timezone
        
        Args:
            session_type: 'morning' or 'evening'
            user_timezone: User's timezone (e.g., 'Europe/Paris')
            
        Returns:
            Tuple of (is_allowed, reason_message)
        """
        try:
            user_tz = pytz.timezone(user_timezone)
            current_time = datetime.now(user_tz)
            current_hour = current_time.hour
            
            if session_type == "morning":
                # Morning check-ins: 5am to 12pm (noon)
                if 5 <= current_hour < 12:
                    return True, ""
                else:
                    next_window_start = "5:00 AM"
                    next_window_end = "12:00 PM"
                    if current_hour < 5:
                        next_available = "today"
                    else:
                        next_available = "tomorrow"
                    
                    return False, f"Morning check-ins are available between {next_window_start} - {next_window_end}. Next available: {next_available} at {next_window_start}."
            
            elif session_type == "evening":
                # Evening check-ins: 3pm current day until 5am next day
                if current_hour >= 15 or current_hour < 5:  # 3pm-11:59pm OR 12am-4:59am
                    return True, ""
                else:
                    next_window_start = "3:00 PM"
                    if current_hour < 5:
                        next_available = "until 5:00 AM"
                    else:
                        next_available = f"today at {next_window_start}"
                    
                    return False, f"Evening reviews are available from {next_window_start} until 5:00 AM next day. Next available: {next_available}."
            
            else:
                return False, "Invalid session type."
                
        except Exception as e:
            logger.error(f"Error checking session time: {e}")
            return False, "Unable to check time availability."
    
    def validate_session_start(self, user_id: int, session_type: str, today_sessions: Dict[str, Any], user_timezone: str) -> Tuple[bool, str, Optional[InlineKeyboardMarkup]]:
        """
        Validate if user can start a session, considering time windows and frequency limits
        
        Args:
            user_id: User ID
            session_type: 'morning' or 'evening'  
            today_sessions: Dict with today's completed sessions
            user_timezone: User's timezone
            
        Returns:
            Tuple of (can_start, message, keyboard)
        """
        try:
            # Check if session already completed today
            if today_sessions.get(session_type) is not None:
                return self._handle_already_completed_session(session_type, today_sessions[session_type], user_timezone)
            
            # Check if current time is within allowed window
            time_allowed, time_message = self.is_session_allowed(session_type, user_timezone)
            if not time_allowed:
                return self._handle_time_restriction(session_type, time_message)
            
            # Session is allowed
            return True, "", None
            
        except Exception as e:
            logger.error(f"Error validating session start: {e}")
            return False, "An error occurred while validating the session.", self._create_back_to_menu_keyboard()
    
    def _handle_already_completed_session(self, session_type: str, completed_session: Dict[str, Any], user_timezone: str) -> Tuple[bool, str, InlineKeyboardMarkup]:
        """Handle case where user already completed this session type today"""
        try:
            # Get session details
            completion_time = datetime.fromisoformat(completed_session["timestamp"])
            user_tz = pytz.timezone(user_timezone)
            local_completion_time = completion_time.astimezone(user_tz)
            
            # Format completion time
            time_str = local_completion_time.strftime("%I:%M %p").lstrip("0")
            
            # Create summary of responses
            responses = completed_session.get("responses", {})
            summary_parts = []
            
            # Format responses based on session type
            if session_type == "morning":
                emoji = "🕘"
                session_name = "Morning Check-in"
                next_window = "Tomorrow between 5:00 AM - 12:00 PM"
                
                if "energy_level" in responses:
                    summary_parts.append(f"⚡ Energy: {responses['energy_level']}/10")
                if "mood" in responses:
                    summary_parts.append(f"😊 Mood: {responses['mood']}/10")
                if "intention" in responses:
                    summary_parts.append(f"🎯 Intention: {responses['intention']}")
            else:  # evening
                emoji = "🌙"
                session_name = "Evening Review"
                # Calculate next evening window
                current_time = datetime.now(user_tz)
                if current_time.hour < 5:  # Before 5am, evening window is still active
                    next_window = "Today until 5:00 AM"
                else:  # After 5am, wait until 3pm
                    next_window = "Today from 3:00 PM - 5:00 AM (next day)"
                
                if "mood" in responses:
                    summary_parts.append(f"😊 Mood: {responses['mood']}/10")
                if "stress_level" in responses:
                    summary_parts.append(f"😰 Stress: {responses['stress_level']}/10")
                if "day_word" in responses:
                    summary_parts.append(f"📝 Day: {responses['day_word']}")
                if "reflection" in responses:
                    reflection = responses['reflection']
                    if len(reflection) > 50:
                        reflection = reflection[:47] + "..."
                    summary_parts.append(f"💭 Reflection: {reflection}")
            
            # Create message
            summary_text = "\n".join(summary_parts) if summary_parts else "No responses recorded."
            
            message = f"""{emoji} <b>{session_name} Already Completed</b>

✅ <b>Completed at:</b> {time_str}

<b>Your responses:</b>
{summary_text}

<b>Next {session_name.lower()}:</b> {next_window}

Take care of yourself! 💚"""
            
            keyboard = self._create_back_to_menu_keyboard()
            return False, message, keyboard
            
        except Exception as e:
            logger.error(f"Error handling completed session: {e}")
            return False, f"You already completed your {session_type} check-in today.", self._create_back_to_menu_keyboard()
    
    def _handle_time_restriction(self, session_type: str, time_message: str) -> Tuple[bool, str, InlineKeyboardMarkup]:
        """Handle case where current time is outside allowed window"""
        emoji = "🕘" if session_type == "morning" else "🌙"
        session_name = "Morning Check-in" if session_type == "morning" else "Evening Review"
        
        message = f"""{emoji} <b>{session_name} Not Available</b>

⏰ {time_message}

The timing restrictions help maintain consistency in your daily routine and provide more meaningful insights from your responses.

Take care of yourself! 💚"""
        
        keyboard = self._create_back_to_menu_keyboard()
        return False, message, keyboard
    
    def _create_back_to_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Create a simple back to menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "🏠 Back to Main Menu", 
                    callback_data="main_menu"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_smart_main_menu_keyboard(self, user_id: int, today_sessions: Dict[str, Any], user_timezone: str) -> InlineKeyboardMarkup:
        """Create main menu keyboard with session status indicators"""
        try:
            keyboard = []
            
            # Morning check-in button
            morning_completed = today_sessions.get("morning") is not None
            morning_allowed, _ = self.is_session_allowed("morning", user_timezone)
            
            if morning_completed:
                morning_text = f"{COLORS['morning']} 🕘 Morning Check-in ✅"
                morning_callback = "start_morning"  # Will show completion message
            elif morning_allowed:
                morning_text = f"{COLORS['morning']} 🕘 Morning Check-in"
                morning_callback = "start_morning"
            else:
                morning_text = f"{COLORS['morning']} 🕘 Morning Check-in 🚫"
                morning_callback = "start_morning"  # Will show time restriction message
            
            keyboard.append([InlineKeyboardButton(morning_text, callback_data=morning_callback)])
            
            # Evening review button
            evening_completed = today_sessions.get("evening") is not None
            evening_allowed, _ = self.is_session_allowed("evening", user_timezone)
            
            if evening_completed:
                evening_text = f"{COLORS['evening']} 🌙 Evening Review ✅"
                evening_callback = "start_evening"  # Will show completion message
            elif evening_allowed:
                evening_text = f"{COLORS['evening']} 🌙 Evening Review"
                evening_callback = "start_evening"
            else:
                evening_text = f"{COLORS['evening']} 🌙 Evening Review 🚫"
                evening_callback = "start_evening"  # Will show time restriction message
            
            keyboard.append([InlineKeyboardButton(evening_text, callback_data=evening_callback)])
            
            # Weekly Reports button
            keyboard.append([
                InlineKeyboardButton(
                    "📊 Weekly Reports", 
                    callback_data="view_weekly_reports"
                )
            ])
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"Error creating smart menu keyboard: {e}")
            # Fallback to original keyboard
            return self.create_main_menu_keyboard()
