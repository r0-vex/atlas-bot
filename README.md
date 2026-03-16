# Atlas – Personal Academic Assistant Bot

Atlas is a Telegram bot designed to help students manage their academic life efficiently.  
It tracks assignments, schedules classes, and sends automated reminders based on deadlines and user-defined briefing times.

The goal of Atlas is to act as a lightweight personal assistant for academic productivity.

---

## Features

- Add and manage assignments
- Track deadlines with automated reminders
- Daily briefing with schedule and tasks
- Weekly timetable management
- Snooze reminders
- Clear timetable for a specific day
- Telegram inline buttons for quick actions
- Automated scheduling using APScheduler

---

## Commands

| Command | Description |
|-------|-------------|
| `/start` | Start the bot |
| `/add` | Add a new assignment |
| `/tasks` | View pending assignments |
| `/done` | Mark assignment as completed |
| `/today` | View today's classes and assignments |
| `/time` | Add a class to timetable |
| `/clearday` | Clear timetable for a specific day |
| `/brief` | Set daily briefing time |

---

## Tech Stack

- Python
- python-telegram-bot
- SQLite
- APScheduler
- Railway (deployment)

---

## Project Structure

```
atlas-bot/
│
├── bot.py          # Main bot logic
├── scheduler.py    # Reminder scheduling system
├── database.py     # SQLite database setup
├── requirements.txt
└── README.md
```

---

## How It Works

1. Users interact with the bot through Telegram commands.
2. Assignments and timetable data are stored in a SQLite database.
3. APScheduler runs background jobs for daily reminders.
4. The bot sends automated notifications based on deadlines.

---

## Deployment

The bot is deployed on Railway and runs 24/7.

To run locally:

```bash
pip install -r requirements.txt
python bot.py
```

Make sure to set your Telegram bot token as an environment variable.

---

## Future Improvements

- PostgreSQL database
- Smart scheduling recommendations
- AI-based study planning
- Web dashboard

---

## Author

Rohith
