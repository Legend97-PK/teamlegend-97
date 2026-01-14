import sqlite3
import json
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_name='bot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referral_link TEXT,
            invited_by INTEGER
        )''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY,
            country TEXT,
            numbers TEXT,  -- JSON list of numbers with timestamps
            uploaded_by INTEGER
        )''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS admin_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        self.conn.commit()

    # User methods
    def add_user(self, user_id, invited_by=None):
        self.conn.execute('INSERT OR IGNORE INTO users (user_id, balance, referral_link, invited_by) VALUES (?, 0, ?, ?)',
                          (user_id, f'https://t.me/yourbotusername?start={user_id}', invited_by))
        self.conn.commit()

    def get_user(self, user_id):
        return self.conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    def update_balance(self, user_id, amount):
        self.conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()

    # Number methods
    def add_numbers(self, country, numbers_list, admin_id):
        numbers_json = json.dumps([{'number': n, 'expires': (datetime.now() + timedelta(hours=24)).isoformat()} for n in numbers_list])
        self.conn.execute('INSERT INTO numbers (country, numbers, uploaded_by) VALUES (?, ?, ?)',
                          (country, numbers_json, admin_id))
        self.conn.commit()

    def get_countries(self):
        return [row[0] for row in self.conn.execute('SELECT DISTINCT country FROM numbers').fetchall()]

    def get_numbers(self, country, limit=3):
        row = self.conn.execute('SELECT numbers FROM numbers WHERE country = ?', (country,)).fetchone()
        if row:
            numbers = json.loads(row[0])
            available = [n for n in numbers if datetime.fromisoformat(n['expires']) > datetime.now()]
            return available[:limit]
        return []

    def delete_country(self, country):
        self.conn.execute('DELETE FROM numbers WHERE country = ?', (country,))
        self.conn.commit()

    def wipe_all(self):
        self.conn.execute('DELETE FROM numbers')
        self.conn.commit()

    # Admin settings
    def set_setting(self, key, value):
        self.conn.execute('INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def get_setting(self, key):
        row = self.conn.execute('SELECT value FROM admin_settings WHERE key = ?', (key,)).fetchone()
        return row[0] if row else None

    # Analytics
    def get_total_users(self):
        return self.conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

    # Auto-cleanup
    def cleanup_expired(self):
        for row in self.conn.execute('SELECT id, numbers FROM numbers'):
            numbers = json.loads(row[1])
            updated = [n for n in numbers if datetime.fromisoformat(n['expires']) > datetime.now()]
            self.conn.execute('UPDATE numbers SET numbers = ? WHERE id = ?', (json.dumps(updated), row[0]))
        self.conn.commit()