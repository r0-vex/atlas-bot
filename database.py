import sqlite3
from datetime import datetime
conn = sqlite3.connect("atlas.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    title TEXT,
    due_date TEXT,
    status TEXT,
    reminder_3_sent INTEGER DEFAULT 0,
    reminder_1_sent INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    briefing_time TEXT
);""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT,
    subject TEXT,
    time TEXT
);""")
conn.commit()