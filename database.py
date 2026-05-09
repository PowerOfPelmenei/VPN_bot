import sqlite3
import time
from typing import Dict, Optional

from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referrer_id INTEGER,
            subscription_end INTEGER,
            created_at INTEGER,
            free_trial_used INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            awarded INTEGER DEFAULT 0,
            UNIQUE(referrer_id, referred_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount INTEGER,
            months INTEGER,
            status TEXT,
            created_at INTEGER
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(user_id: int, username: str = None, referrer_id: int = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = int(time.time())
    cur.execute(
        "INSERT INTO users (user_id, username, referrer_id, subscription_end, free_trial_used, created_at) VALUES (?, "
        "?, ?, ?, ?, ?)",
        (user_id, username, referrer_id, 0, 0, now)
    )
    conn.commit()
    conn.close()


def update_subscription_end(user_id: int, new_end_timestamp: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end_timestamp, user_id))
    conn.commit()
    conn.close()


def mark_free_trial_used(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET free_trial_used = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_reward_given(referrer_id: int, referred_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM referral_rewards WHERE referrer_id = ? AND referred_id = ? AND awarded = 1",
                (referrer_id, referred_id))
    res = cur.fetchone()
    conn.close()
    return res is not None


def mark_reward_given(referrer_id: int, referred_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO referral_rewards (referrer_id, referred_id, awarded) VALUES (?, ?, 1)",
                (referrer_id, referred_id))
    conn.commit()
    conn.close()


def add_payment(payment_id: str, user_id: int, amount: int, months: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments (payment_id, user_id, amount, months, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (payment_id, user_id, amount, months, status, int(time.time()))
    )
    conn.commit()
    conn.close()


def get_referrals_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count
