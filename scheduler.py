from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from database import cursor
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pytz import timezone

scheduler = BackgroundScheduler(timezone=timezone("Asia/Kolkata"))
scheduler.start()

def daily_job(app, chat_id):

    # ---------- MORNING SUMMARY ----------
    summary = build_today_summary()

    app.create_task(
    app.bot.send_message(
        chat_id=chat_id,
        text=summary
    )
)

    # ---------- REMINDER CHECK ----------
    today = datetime.today().date()

    cursor.execute("""
        SELECT id, subject, title, due_date, reminder_3_sent, reminder_1_sent
        FROM assignments
        WHERE status='pending'
    """)

    rows = cursor.fetchall()

    reminders = []

    for r in rows:

        task_id, subject, title, due_date, r3, r1 = r
        due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        days_left = (due_date - today).days

        if days_left == 3 and not r3:

            reminders.append((task_id, subject, title, days_left))

            cursor.execute(
                "UPDATE assignments SET reminder_3_sent=1 WHERE id=?",
                (task_id,)
            )

        if days_left == 1 and not r1:

            reminders.append((task_id, subject, title, days_left))

            cursor.execute(
                "UPDATE assignments SET reminder_1_sent=1 WHERE id=?",
                (task_id,)
            )

    from database import conn
    conn.commit()

    return reminders

async def send_reminders(app, chat_id, reminders):

    for r in reminders:

        task_id, subject, title, days_left = r

        message = (
            f"Atlas Reminder\n\n"
            f"{subject} – {title}\n"
            f"{days_left} days left."
        )

        keyboard = [
            [
                InlineKeyboardButton("Snooze 1h", callback_data=f"snooze_1_{task_id}"),
                InlineKeyboardButton("Snooze 3h", callback_data=f"snooze_3_{task_id}")
            ],
            [
                InlineKeyboardButton("Snooze 6h", callback_data=f"snooze_6_{task_id}"),
                InlineKeyboardButton("Mark Done", callback_data=f"done_{task_id}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await app.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup
        )

def build_today_summary():

    today = datetime.today().date()
    day = datetime.today().strftime("%A")

    message = "Atlas Morning Briefing\n\n"

    # Today's classes
    cursor.execute(
        "SELECT subject,time FROM timetable WHERE day=?",
        (day,)
    )

    classes = cursor.fetchall()

    if classes:
        message += "Today's Classes\n"
        for subject, time in classes:
            message += f"{time}  {subject}\n"

    # Assignments
    cursor.execute(
        "SELECT subject,title,due_date FROM assignments WHERE status='pending'"
    )

    rows = cursor.fetchall()

    if rows:

        message += "\nAssignments\n"

        for subject, title, due in rows:

            due_date = datetime.strptime(due,"%Y-%m-%d").date()
            days_left = (due_date - today).days

            if days_left >= 0:
                message += f"{subject} – {title}\n"
                message += f"Due {due} ({days_left} days left)\n\n"

    return message