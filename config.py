"""
Configuration file for Telegram Mental Health Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Get from @BotFather on Telegram
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))  # Admin user ID for /admin_stats command

# OpenRouter AI configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5")

# Data file paths
DATA_DIR = "data"
# RESPONSES_FILE is deprecated - using SQLite database instead

# Question sets
MORNING_QUESTIONS = {
    "title": "🕘 Morning: Starting Point",
    "description": "Good morning! Let's check in on your starting point for today:",
    "questions": [
        {
            "id": "energy_level",
            "text": "⚡ Energy level (0–10): How energized do you feel?",
            "type": "scale",
            "emoji": "⚡"
        },
        {
            "id": "mood",
            "text": "😊 Mood (0–10): How positive do you feel emotionally?",
            "type": "scale",
            "emoji": "😊"
        },
        {
            "id": "intention",
            "text": "🎯 One-word intention: Choose what you want from today:",
            "type": "word_selection",
            "emoji": "🎯"
        }
    ]
}

EVENING_QUESTIONS = {
    "title": "🌙 Evening: Review",
    "description": "Good evening! Time to reflect on your day:",
    "questions": [
        {
            "id": "mood",
            "text": "😊 Mood (0–10): How do you feel emotionally right now?",
            "type": "scale",
            "emoji": "😊"
        },
        {
            "id": "stress_level",
            "text": "😰 Stress level (0–10): How stressed have you felt today?",
            "type": "scale",
            "emoji": "😰"
        },
        {
            "id": "day_word",
            "text": "📝 One word for the day: Describe your day in one word:",
            "type": "word_selection",
            "emoji": "📝"
        },
        {
            "id": "reflection",
            "text": "💭 One line reflection: One sentence about what affected your mood most:",
            "type": "text",
            "emoji": "💭"
        }
    ]
}

# UI Colors and styling
COLORS = {
    "morning": "🟢",
    "evening": "🔵",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️"
}

# Scale button styling
SCALE_BUTTONS = [
    [{"text": "0️⃣", "callback_data": "0"}, {"text": "1️⃣", "callback_data": "1"}, {"text": "2️⃣", "callback_data": "2"}],
    [{"text": "3️⃣", "callback_data": "3"}, {"text": "4️⃣", "callback_data": "4"}, {"text": "5️⃣", "callback_data": "5"}],
    [{"text": "6️⃣", "callback_data": "6"}, {"text": "7️⃣", "callback_data": "7"}, {"text": "8️⃣", "callback_data": "8"}],
    [{"text": "9️⃣", "callback_data": "9"}, {"text": "🔟", "callback_data": "10"}]
]

# Word selection options for morning intention question
WORD_CATEGORIES = {
    "main_words": [
        {"text": "🌿 Calm", "word": "Calm"},
        {"text": "🎯 Focused", "word": "Focused"},
        {"text": "💖 Grateful", "word": "Grateful"},
        {"text": "🌿 Patient", "word": "Patient"},
        {"text": "⚡ Energetic", "word": "Energetic"}
    ],
    "categories": {
        "calm_centered": {
            "emoji": "🌿",
            "title": "Calm & Centered",
            "words": ["Calm", "Peaceful", "Steady", "Grounded", "Patient", "Balanced", "Relaxed"]
        },
        "productive_active": {
            "emoji": "💪",
            "title": "Productive & Active", 
            "words": ["Focused", "Productive", "Efficient", "Driven", "Organized", "Motivated", "Disciplined"]
        },
        "emotional_relational": {
            "emoji": "💖",
            "title": "Emotional & Relational",
            "words": ["Kind", "Compassionate", "Caring", "Grateful", "Loving", "Supportive", "Generous"]
        },
        "growth_aspiration": {
            "emoji": "🌟",
            "title": "Growth & Aspiration",
            "words": ["Confident", "Brave", "Curious", "Creative", "Resilient", "Optimistic", "Determined"]
        },
        "self_care_wellbeing": {
            "emoji": "🎯",
            "title": "Self-Care & Well-Being",
            "words": ["Healthy", "Rested", "Nourished", "Energetic", "Mindful", "Joyful", "Present"]
        }
    }
}

# Word selection options for evening day_word question
DAY_WORD_CATEGORIES = {
    "main_words": [
        {"text": "🌈 Joyful", "word": "Joyful"},
        {"text": "🌤 Steady", "word": "Steady"},
        {"text": "🌧 Tired", "word": "Tired"},
        {"text": "🌟 Resilient", "word": "Resilient"}
    ],
    "categories": {
        "joyful": {
            "emoji": "🌈",
            "title": "Joyful",
            "words": ["Joyful", "Peaceful", "Exciting", "Productive", "Relaxed", "Inspired", "Optimistic"]
        },
        "steady": {
            "emoji": "🌤",
            "title": "Steady", 
            "words": ["Steady", "Okay", "Average", "Routine", "Quiet", "Normal", "Content"]
        },
        "tired": {
            "emoji": "🌧",
            "title": "Tired",
            "words": ["Tired", "Stressed", "Frustrated", "Overwhelmed", "Lonely", "Drained", "Anxious"]
        },
        "resilient": {
            "emoji": "🌟",
            "title": "Resilient",
            "words": ["Resilient", "Learning", "Challenging", "Courageous", "Progress", "Adaptive", "Determined"]
        }
    }
}

# Messages
MESSAGES = {
    "welcome": """🌟 <b>Welcome to Your Mental Health Tracker</b> 🌟

I'm here to help you build consistent mental health habits through daily check-ins, personalized reminders, and AI-powered weekly insights.

<b>✨ Key Features:</b>
• 🕘 Morning & 🌙 Evening check-ins with tailored questions
• 📱 Smart reminders with timezone support
• 🤖 AI-powered weekly reports with personalized insights
• 📊 Comprehensive progress statistics  
• ⚙️ Fully customizable settings

Choose your check-in type below, or explore /help for full details:""",
    "first_time_welcome": """🌟 <b>Welcome! Let's Get You Started</b> 🌟

This is your first time using the Mental Health Bot - let's set you up for success!

First, I need to know your timezone to send you reminders at the right time in your local area.

<b>🌍 Please select your timezone:</b>
<i>Paris timezone is recommended and pre-selected for you</i>""",
    "onboarding_explanation": """🎉 <b>Perfect! You're All Set Up</b> 🎉

<b>🧠 How This App Works:</b>

<b>📋 Two Types of Check-ins:</b>
• <b>🕘 Morning Check-in (3 questions, ~2 minutes):</b>
  - Energy level (0-10 scale)
  - Mood (0-10 scale)  
  - Daily intention (choose from curated words)

• <b>🌙 Evening Review (4 questions, ~3 minutes):</b>
  - Current mood (0-10 scale)
  - Stress level (0-10 scale)
  - Day description (choose descriptive words)
  - Personal reflection (one sentence)

<b>🤖 AI-Powered Weekly Reports:</b>
• Automatically generated every Sunday evening
• Requires at least 3 days of check-ins per week
• Provides personalized insights, patterns, and actionable suggestions
• Browse through previous reports to track your progress over time

<b>⏰ Your Default Settings (Already Configured):</b>
✅ <b>Timezone:</b> {timezone}
✅ <b>Morning reminder:</b> 7:00 AM (customizable)
✅ <b>Evening reminder:</b> 10:00 PM (customizable)
✅ <b>Smart reminders:</b> Only sent if you haven't completed that day's check-in

<b>📊 Features You Can Use:</b>
• View your progress with <code>/stats</code>
• Get AI weekly insights with <code>/weekly_reports</code>
• Test report generation with <code>/test_report</code>
• Customize all settings with <code>/settings</code>
• Get help anytime with <code>/help</code>
• Quick reminder toggle with <code>/reminders</code>

<b>💡 Pro Tips:</b>
• Be consistent - even 2 minutes daily makes a difference
• Be honest in your responses for better insights
• Aim for at least 3 check-ins per week to get AI reports
• Use the weekly reports to identify patterns and improve

<b>Ready to start your mental health journey? 🚀</b>""",
    "unauthorized": "❌ Sorry, you are not authorized to use this bot.",
    "data_saved": "✅ Your response has been saved successfully!",
    "session_complete": """🎉 <b>Check-in Complete!</b> 🎉

Thank you for taking the time to reflect on your mental state. Your responses have been saved for analysis.

Stay mindful and take care of yourself! 💚""",
    "error_occurred": "❌ An error occurred. Please try again or contact support.",
    "invalid_input": "⚠️ Please provide a valid response.",
    "reminder_sent": "📱 Reminder sent successfully!",
    "reminder_snoozed": "⏰ Reminder snoozed for {hours} hours.",
    "reminder_skipped": "❌ Today's reminder skipped.",
    "first_time_setup": """🌟 <b>Welcome! Let's set up your reminders</b>

To help you stay consistent with your mental health tracking, I can send you daily reminders.

<b>Default Settings:</b>
• 🌍 Timezone: Europe/Paris 
• 🕘 Morning reminder: 07:00
• 🌙 Evening reminder: 22:00

Would you like to customize these settings or use the defaults?""",
}

# Reminder settings
REMINDER_SETTINGS = {
    "default_timezone": "Europe/Paris",
    "default_morning_time": "07:00",
    "default_evening_time": "22:00",
    "snooze_hours": [1, 2, 4],
    "max_daily_reminders": 3,
    "reminder_enabled_by_default": True
}

# Report generation settings
REPORT_SETTINGS = {
    "retry_delay_days": 2,  # Days to wait before retrying failed report
    "max_retry_attempts": 3,  # Maximum number of retry attempts
    "retry_check_interval_hours": 6,  # How often to check for pending retries
    "admin_summary_time_utc": "10:00",  # When to send daily admin summary
    "min_days_for_report": 3,  # Minimum days of data needed for report
    "immediate_admin_notification_threshold": 5  # Send immediate admin notification after this many failures
}

# Logging settings
LOGGING_SETTINGS = {
    "log_file": "bot.log",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "max_log_size_mb": 10,
    "backup_count": 5
}
