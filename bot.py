from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from database import conn, cursor
from scheduler import scheduler,daily_job, send_reminders
from datetime import datetime,timedelta
import re
import os

TOKEN = os.getenv("TOKEN")

#----------REMAINDER-------------
def schedule_daily(app, chat_id, briefing_time):
    hour, minute = map(int, briefing_time.split(":"))

    def job():
        reminders = daily_job(app, chat_id)
        if reminders:
            app.create_task(send_reminders(app, chat_id, reminders))

    scheduler.add_job(
    job,
    'cron',
    hour=hour,
    minute=minute,
    id=f"daily_{chat_id}",
    replace_existing=True
)

# ---------- STATES ----------
ADD_SUBJECT, ADD_TITLE, ADD_DATE = range(3)
BRIEF_TIME = 3
TT_DAY, TT_SUBJECT, TT_TIME = range(4,7)
CLEAR_DAY = 7

# ---------- KEYBOARD ----------
keyboard = [
    ["Add Task", "Tasks"],
    ["Today", "Done"],
    ["Timetable", "Brief"]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Atlas Online.\n\nYour Personal Academic Assistant.",
        reply_markup=reply_markup
    )

# ---------- HELP ----------
async def help_command(update, context):
    await update.message.reply_text(
        "/add\n/tasks\n/done\n/brief\n/today\n/time\n/clearday"
    )

# ---------- BUTTON ROUTER ----------
async def button_router(update, context):
    text = update.message.text

    if text == "Tasks":
        return await tasks(update, context)

    if text == "Today":
        return await today(update, context)

    if text == "Done":
        return await done(update, context)

# ---------- ADD ASSIGNMENT ----------
async def add(update, context):
    await update.message.reply_text("Subject?")
    return ADD_SUBJECT

async def subject(update, context):
    context.user_data["subject"] = update.message.text
    await update.message.reply_text("Assignment title?")
    return ADD_TITLE

async def title(update, context):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Due date (YYYY-MM-DD)?")
    return ADD_DATE

async def date(update, context):
    subject = context.user_data["subject"]
    title = context.user_data["title"]
    due_date = update.message.text

    cursor.execute(
        "INSERT INTO assignments (subject,title,due_date,status) VALUES (?,?,?,?)",
        (subject,title,due_date,"pending")
    )
    conn.commit()

    await update.message.reply_text("Assignment saved.")
    return ConversationHandler.END

# ---------- TASK LIST ----------
async def tasks(update, context):

    cursor.execute("SELECT id,subject,title,due_date FROM assignments WHERE status='pending'")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No pending assignments.")
        return

    today = datetime.today().date()
    message = "Assignments\n\n"

    for i,r in enumerate(rows,start=1):

        due = datetime.strptime(r[3], "%Y-%m-%d").date()
        days = (due - today).days

        message += f"{i}. {r[1]} – {r[2]}\nDue: {r[3]} ({days} days left)\n\n"

    await update.message.reply_text(message)

# ---------- DONE ----------
async def done(update, context):

    cursor.execute("SELECT id,subject,title FROM assignments WHERE status='pending'")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No pending tasks.")
        return

    keyboard = []

    for r in rows:
        keyboard.append(
            [InlineKeyboardButton(f"{r[1]} – {r[2]}", callback_data=f"done_{r[0]}")]
        )

    await update.message.reply_text(
        "Select task to complete",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def complete(update, context):

    query = update.callback_query
    await query.answer()

    task_id = query.data.split("_")[1]

    cursor.execute(
        "UPDATE assignments SET status='completed' WHERE id=?",
        (task_id,)
    )
    conn.commit()

    await query.edit_message_text("Task completed.")

# ---------- BRIEF ----------
async def brief(update, context):
    await update.message.reply_text("Enter briefing time (HH:MM 24-hour format)")
    return BRIEF_TIME

async def save_brief(update, context):

    user_id = update.message.from_user.id
    time = update.message.text.strip()

    if not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", time):
        await update.message.reply_text(
            "Invalid time format.\nPlease enter time like 07:30 or 19:45"
        )
        return BRIEF_TIME

    cursor.execute(
        """INSERT INTO users (telegram_id,briefing_time)
        VALUES (?,?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET briefing_time=excluded.briefing_time""",
        (user_id, time)
    )

    conn.commit()

    # Schedule reminder job
    schedule_daily(context.application, user_id, time)

    await update.message.reply_text(
        f"Daily briefing set for {time}",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

# ---------- TODAY ----------
async def today(update, context):

    message = "Today's Summary\n\n"

    day = datetime.today().strftime("%A")

    cursor.execute("SELECT subject,time FROM timetable WHERE day=?", (day,))
    classes = cursor.fetchall()

    if classes:
        message += "Today's Classes\n"
        for c in classes:
            message += f"{c[1]}  {c[0]}\n"

    cursor.execute("SELECT subject,title,due_date FROM assignments WHERE status='pending'")
    rows = cursor.fetchall()

    if rows:

        today = datetime.today().date()
        message += "\nAssignments\n\n"

        for r in rows:

            due = datetime.strptime(r[2], "%Y-%m-%d").date()
            days = (due - today).days

            if days >= 0:
                message += f"{r[0]} – {r[1]}\nDue {r[2]} ({days} days left)\n\n"

    await update.message.reply_text(message)

# ---------- TIMETABLE ----------
async def time(update, context):

    keyboard = [
        ["Monday", "Tuesday", "Wednesday"],
        ["Thursday", "Friday", "Saturday"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Select day",
        reply_markup=reply_markup
    )

    return TT_DAY

async def save_day(update, context):

    context.user_data["day"] = update.message.text

    await update.message.reply_text(
        "Subject?",
        reply_markup=reply_markup
    )

    return TT_SUBJECT

async def save_subject(update, context):
    context.user_data["subject"] = update.message.text

    await update.message.reply_text(
        "Time (HH:MM) (24 Hour Format)",
        reply_markup=reply_markup
    )

    return TT_TIME

async def save_class(update, context):

    time = update.message.text.strip()

    if not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", time):
        await update.message.reply_text(
            "Invalid time format.\nPlease enter time like 09:00 or 14:30"
        )
        return TT_TIME

    day = context.user_data["day"]
    subject = context.user_data["subject"]

    cursor.execute(
        "INSERT INTO timetable (day,subject,time) VALUES (?,?,?)",
        (day, subject, time)
    )

    conn.commit()

    await update.message.reply_text(
        "Class added.",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

#---------CLEAR TIMETABLE------
async def clear_day(update, context):

    keyboard = [
        ["Monday", "Tuesday", "Wednesday"],
        ["Thursday", "Friday", "Saturday"]
    ]

    reply_markup_days = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Select day to clear",
        reply_markup=reply_markup_days
    )

    return CLEAR_DAY

async def delete_day(update, context):

    day = update.message.text

    cursor.execute(
        "DELETE FROM timetable WHERE day=?",
        (day,)
    )

    conn.commit()

    await update.message.reply_text(
        f"All classes for {day} removed.",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

#----------SNOOZE----------

async def snooze(update, context):

    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    hours = int(data[1])
    task_id = data[2]

    run_time = datetime.now() + timedelta(hours=hours)

    def job():
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Snoozed reminder for task {task_id}"
        )

    scheduler.add_job(job, 'date', run_date=run_time)

    await query.edit_message_text(f"Reminder snoozed for {hours} hours.")

# ---------- BOT ----------
app = ApplicationBuilder().token(TOKEN).build()

add_handler = ConversationHandler(
    entry_points=[
        CommandHandler("add", add),
        MessageHandler(filters.Regex("^Add Task$"), add)
    ],
    states={
        ADD_SUBJECT:[MessageHandler(filters.TEXT,subject)],
        ADD_TITLE:[MessageHandler(filters.TEXT,title)],
        ADD_DATE:[MessageHandler(filters.TEXT,date)]
    },
    fallbacks=[]
)

brief_handler = ConversationHandler(
    entry_points=[
        CommandHandler("brief", brief),
        MessageHandler(filters.Regex("^Brief$"), brief)
    ],
    states={BRIEF_TIME:[MessageHandler(filters.TEXT,save_brief)]},
    fallbacks=[]
)

time_handler = ConversationHandler(
    entry_points=[
    CommandHandler("time", time),
    MessageHandler(filters.Regex("^Timetable$"), time)
],
    states={
        TT_DAY:[MessageHandler(filters.TEXT,save_day)],
        TT_SUBJECT:[MessageHandler(filters.TEXT,save_subject)],
        TT_TIME:[MessageHandler(filters.TEXT,save_class)]
    },
    fallbacks=[]
)

clear_handler = ConversationHandler(
    entry_points=[CommandHandler("clearday", clear_day)],
    states={
        CLEAR_DAY: [MessageHandler(filters.TEXT, delete_day)]
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(add_handler)
app.add_handler(brief_handler)
app.add_handler(time_handler)
app.add_handler(clear_handler)
app.add_handler(CommandHandler("tasks", tasks))
app.add_handler(CommandHandler("today", today))
app.add_handler(CommandHandler("done", done))
app.add_handler(CallbackQueryHandler(snooze, pattern="^snooze"))
app.add_handler(CallbackQueryHandler(complete, pattern="^done"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_router))

print("Atlas running...")
app.run_polling()
