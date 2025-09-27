# 🧠 Telegram Mental Health Bot  

👉 Already live! Try it here: [@MoodTrackerVS_bot](https://t.me/MoodTrackerVS_bot)  

This bot helps you **build awareness of your mental state** through short daily check-ins.  

**Main features:**  
- ⏱️ Quick 5–10 second questionnaires: how you feel, your expectations for the day, and how it actually went  
- ⏰ Customizable morning & evening reminders  
- 📊 Weekly AI-generated reports with tips  
- 📤 Export your data to Excel for deeper analysis  

<img src="logo.png" alt="Mental Health Bot" width="250"/>  

---

## ✨ Features  

### 🕘 Morning Check-in  
- ⚡ Energy (0–10)  
- 😊 Mood (0–10)  
- 🎯 Daily intention (35+ curated words across 5 categories)  

### 🌙 Evening Review 
- 😊 Mood (0–10)  
- 😰 Stress (0–10)  
- 📝 Day description (28+ words)  
- 💭 Reflection (1 sentence)  

### 🔔 Smart Reminders  
- Morning & evening, fully customizable  
- Timezone support  
- Snooze options (1–4 hours)  
- Independent toggle for morning/evening  

### 📊 Weekly Reports & Statistics  
- AI-powered advice (ChatGPT-generated tips)  
- Track unique days, first/last sessions, and progress patterns  
- Export to Excel for personal analysis  

### 🔐 Privacy & Security  
- Local SQLite storage (your data never leaves your server)  
- User authentication and input validation  
- No third-party services  

---

## 🚀 Quick Start  

1. Clone repo  
   ```bash
   git clone <repository-url>
   cd telegram_mental_health_bot
   ```

2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` with your credentials

   ```env
   BOT_TOKEN="YOUR_BOT_TOKEN"
   ADMIN_USER_ID=YOUR_USER_ID
   ```

4. Run the bot

   ```bash
   python bot.py
   ```

---

## 🆘 Troubleshooting

* **Bot not responding** → Check your token and user ID in `.env`
* **Unauthorized message** → Get correct ID from [@userinfobot](https://t.me/userinfobot)
* **Data not saving** → Verify `data/` folder permissions

---

## 💡 Tips

* Be consistent: check in around the same times daily
* Use reminders to build habits
* Review stats monthly to notice trends
* Be honest: more accurate responses = better insights

---

## 📄 License

This project is licensed under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).
You’re free to use, share, and adapt it with attribution.
