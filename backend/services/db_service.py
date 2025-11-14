import sqlite3
import json
from config import DB_PATH
from utils.logger import log

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_text TEXT,
        items_json TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

def save_order(raw_text, items):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO orders (raw_text, items_json) VALUES (?, ?)",
        (raw_text, json.dumps(items))
    )

    conn.commit()
    conn.close()

    log("💾 Order saved.")

def get_orders():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows
