import sqlite3
import json

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
users = conn.execute('SELECT user_id, username, leetcode_username, codeforces_username FROM users').fetchall()
with open('users.json', 'w') as f:
    json.dump([dict(u) for u in users], f, indent=2)
