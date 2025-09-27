"""
Utility functions for the Telegram Mental Health Bot
"""

import logging
from typing import Any, Dict
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import MESSAGES

def setup_logging() -> None:
    """Set up logging configuration"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )

def authorized_only(func):
    """Decorator to check if user is authorized with dynamic user limit (100 users max)"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Handle both function calls and method calls
        # If first arg is 'self' (instance), then update is second arg
        # If first arg is Update, then it's a direct function call
        
        if len(args) >= 2 and hasattr(args[0], '__class__') and hasattr(args[1], 'effective_user'):
            # Class method call: (self, update, context, ...)
            self_instance, update, context = args[0], args[1], args[2] if len(args) > 2 else None
        elif len(args) >= 1 and hasattr(args[0], 'effective_user'):
            # Direct function call: (update, context, ...)
            update, context = args[0], args[1] if len(args) > 1 else None
        else:
            # Fallback - call original function
            return await func(*args, **kwargs)
            
        user_id = update.effective_user.id if update.effective_user else None
        user = update.effective_user
        
        if not user_id or not user:
            logger = logging.getLogger(__name__)
            logger.warning("Access attempt with no user information")
            return
        
        # Import data_handler here to avoid circular imports
        from data_handler import DataHandler
        data_handler = DataHandler()
        
        # Ensure data structure exists and migrate existing users if needed
        try:
            data_handler.ensure_data_structure()
            data_handler.migrate_existing_users()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to ensure data structure: {e}")
        
        # Check if user is already registered
        if data_handler.is_registered_user(user_id):
            return await func(*args, **kwargs)
        
        # Try to register new user
        user_info = {
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or ""
        }
        
        if data_handler.register_unique_user(user_id, user_info):
            # Successfully registered, allow access
            return await func(*args, **kwargs)
        else:
            # Registration failed - limit reached
            logger = logging.getLogger(__name__)
            logger.warning(f"User limit reached - denied access to user {user_id} ({user.first_name} {user.last_name or ''}) @{user.username or 'no_username'}")
            
            limit_message = """🚫 <b>User Limit Reached</b>

Sorry, this bot has reached its maximum capacity of 100 users. No new users can be added at this time.

Thank you for your interest in using our mental health tracking bot."""
            
            if update.message:
                await update.message.reply_text(limit_message, parse_mode='HTML')
            elif update.callback_query:
                await update.callback_query.answer("User limit reached. Bot is at full capacity.", show_alert=True)
            
            return
        
    return wrapper

async def safe_message_send(update: Update, text: str, reply_markup=None, parse_mode='HTML') -> bool:
    """
    Safely send a message with error handling
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        elif update.message:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            logger.error("No valid message context found")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        
        # Try to send a simple error message without formatting
        try:
            if update.callback_query:
                await update.callback_query.answer("An error occurred. Please try again.")
            elif update.message:
                await update.message.reply_text("An error occurred. Please try again.")
        except:
            logger.error("Failed to send error message")
        
        return False

async def safe_callback_answer(update: Update, text: str = None, show_alert: bool = False) -> bool:
    """
    Safely answer a callback query
    
    Returns:
        bool: True if callback was answered successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        if update.callback_query:
            await update.callback_query.answer(text=text, show_alert=show_alert)
            return True
        else:
            logger.warning("Attempted to answer callback query but no callback_query found")
            return False
            
    except Exception as e:
        logger.error(f"Failed to answer callback query: {e}")
        return False

def format_user_info(update: Update) -> str:
    """Format user information for logging"""
    if not update.effective_user:
        return "Unknown user"
    
    user = update.effective_user
    return f"User {user.id} ({user.first_name} {user.last_name or ''}) @{user.username or 'no_username'}"

def get_user_context_key(user_id: int, key: str) -> str:
    """Generate a context key for storing user-specific data"""
    return f"user_{user_id}_{key}"

async def cleanup_user_context(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Clean up user-specific context data"""
    try:
        keys_to_remove = []
        prefix = f"user_{user_id}_"
        
        for key in context.user_data.keys():
            if key.startswith(prefix):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del context.user_data[key]
            
        logger = logging.getLogger(__name__)
        logger.info(f"Cleaned up {len(keys_to_remove)} context keys for user {user_id}")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to cleanup user context: {e}")

def validate_scale_input(value: str) -> tuple[bool, int]:
    """
    Validate scale input (0-10)
    
    Returns:
        tuple: (is_valid, parsed_value)
    """
    try:
        parsed_value = int(value)
        if 0 <= parsed_value <= 10:
            return True, parsed_value
        else:
            return False, 0
    except (ValueError, TypeError):
        return False, 0

import re
import unicodedata

def is_safe_text_content(text: str, question_type: str = "general") -> tuple[bool, str]:
    """
    Comprehensive security validation for text input to prevent attacks
    
    Returns:
        tuple: (is_safe, error_message)
    """
    if not text or not text.strip():
        return False, "Please provide a valid response."
    
    text = text.strip()
    
    # Layer 1: Dangerous pattern detection
    dangerous_patterns = [
        # Code injection patterns
        r'<script[\s\S]*?</script>',
        r'javascript:',
        r'eval\s*\(',
        r'exec\s*\(',
        r'function\s*\(',
        r'var\s+\w+\s*=',
        r'let\s+\w+\s*=',
        r'const\s+\w+\s*=',
        r'import\s+',
        r'from\s+\w+\s+import',
        r'def\s+\w+\s*\(',
        r'class\s+\w+\s*:',
        
        # HTML/XML injection
        r'<[^>]*>',
        r'&[a-zA-Z]+;',
        r'&#\d+;',
        r'&#x[0-9a-fA-F]+;',
        
        # SQL injection patterns
        r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b',
        r'--\s*',
        r'/\*[\s\S]*?\*/',
        r"'\s*(OR|AND)\s*'",  # More specific: look for ' OR ' or ' AND ' patterns
        r'"\s*(OR|AND)\s*"',  # More specific: look for " OR " or " AND " patterns
        
        # Command injection
        r'\$\(',
        r'`[^`]*`',
        r'\|\s*\w+',
        r'&&\s*\w+',
        r';\s*\w+',
        
        # URL/Link injection (for reflection, we don't expect URLs)
        r'https?://',
        r'ftp://',
        r'file://',
        r'www\.[\w-]+\.[\w-]+',  # Fixed: include hyphens in domain names
        
        # System paths
        r'/etc/',
        r'/var/',
        r'/usr/',
        r'C:\\\\|C:\\',  # Fixed: handle both single and double backslashes
        r'\.\./|\.\.\\',  # Fixed: cover both forward and back slashes for traversal
        
        # Encoded attacks
        r'%[0-9a-fA-F]{2}',
        r'\\x[0-9a-fA-F]{2}',
        r'\\u[0-9a-fA-F]{4}',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Your response contains invalid characters or patterns. Please use only regular text."
    
    # Layer 2: Character validation
    # Allow only safe printable characters
    safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    safe_punctuation = set(' .,!?;:()\'-"')
    allowed_chars = safe_chars | safe_punctuation
    
    for char in text:
        if char not in allowed_chars:
            # Check if it's a safe unicode character (letters, numbers, punctuation)
            category = unicodedata.category(char)
            if not (category.startswith('L') or  # Letters
                   category.startswith('N') or   # Numbers  
                   category.startswith('P') or   # Punctuation
                   category.startswith('Z')):    # Separators (spaces)
                return False, f"Invalid character detected: '{char}'. Please use only letters, numbers, and basic punctuation."
    
    # Layer 3: Content structure validation
    if question_type == "reflection":
        # For reflection questions, expect sentence-like structure
        if len(text) < 3:
            return False, "Your reflection seems too short. Please provide at least a few words."
        
        if len(text) > 200:
            return False, "Please keep your reflection concise (max 200 characters)."
            
        # Check for excessive repetition (spam detection)
        words = text.lower().split()
        if len(words) > 0:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
                if word_counts[word] > 5:  # Same word repeated more than 5 times
                    return False, "Please avoid excessive repetition in your response."
    
    elif question_type == "word":
        # For word questions (intention, day_word)
        words = text.split()
        if len(words) > 3:
            return False, f"Please provide just a word or short phrase (you provided {len(words)} words)."
        
        if len(text) > 50:
            return False, "Please keep your response shorter (max 50 characters)."
    
    # Layer 4: Additional security checks
    # Check for suspicious patterns that might be encoded differently
    suspicious_sequences = ['eval', 'exec', 'script', 'function', 'alert', 'prompt', 'confirm']
    text_lower = text.lower().replace(' ', '').replace('-', '').replace('_', '')
    
    for seq in suspicious_sequences:
        if seq in text_lower:
            return False, "Your response contains words that are not allowed. Please use everyday language."
    
    return True, text


def sanitize_text_input(text: str) -> str:
    """Enhanced text sanitization with security focus"""
    if not text:
        return ""
    
    # Remove any potentially dangerous characters while preserving readability
    # Remove HTML/XML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove markdown that could break formatting  
    text = text.replace('*', '').replace('_', '').replace('`', '')
    
    # Remove potentially dangerous punctuation sequences
    text = re.sub(r'[{}[\]\\|]', '', text)
    
    # Normalize whitespace (remove excessive spaces, tabs, newlines)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove control characters but keep printable ones
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in ' \t')
    
    # Final length limit
    if len(text) > 500:
        text = text[:500] + "..."
    
    return text

def create_session_summary(responses: Dict[str, Any], session_type: str) -> str:
    """Create a human-readable summary of session responses"""
    try:
        summary = f"<b>{session_type.title()} Session Summary:</b>\n\n"
        
        if session_type == "morning":
            if "energy_level" in responses:
                summary += f"⚡ Energy Level: {responses['energy_level']}/10\n"
            if "mood" in responses:
                summary += f"😊 Mood: {responses['mood']}/10\n"
            if "intention" in responses:
                summary += f"🎯 Intention: {responses['intention']}\n"
        
        elif session_type == "evening":
            if "mood" in responses:
                summary += f"😊 Mood: {responses['mood']}/10\n"
            if "stress_level" in responses:
                summary += f"😰 Stress Level: {responses['stress_level']}/10\n"
            if "day_word" in responses:
                summary += f"📝 Day Word: {responses['day_word']}\n"
            if "reflection" in responses:
                summary += f"💭 Reflection: {responses['reflection']}\n"
        
        return summary.strip()
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create session summary: {e}")
        return f"Session completed with {len(responses)} responses."

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error_msg: str = None) -> None:
    """Generic error handler for bot functions"""
    logger = logging.getLogger(__name__)
    
    try:
        user_info = format_user_info(update)
        logger.error(f"Error for {user_info}: {error_msg or 'Unknown error'}")
        
        message = error_msg if error_msg else MESSAGES["error_occurred"]
        
        await safe_message_send(update, message)
    except Exception as e:
        logger.error(f"Error in error handler itself: {e}")
        # Try to send a basic message without using potentially problematic functions
        try:
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text("An error occurred. Please try /start to restart.")
            elif update and hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer("An error occurred. Please try /start to restart.", show_alert=True)
        except:
            logger.error("Could not send error message to user")

def log_user_action(update: Update, action: str, details: str = None) -> None:
    """Log user actions for monitoring and debugging"""
    logger = logging.getLogger(__name__)
    user_info = format_user_info(update)
    
    log_message = f"{user_info} - {action}"
    if details:
        log_message += f" - {details}"
    
    logger.info(log_message)
