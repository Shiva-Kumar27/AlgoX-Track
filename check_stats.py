import sqlite3
import json

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

daily_stats = [dict(r) for r in conn.execute("SELECT * FROM daily_stats WHERE user_id = 3").fetchall()]
recent_problems = [dict(r) for r in conn.execute("SELECT * FROM recent_problems WHERE user_id = 3").fetchall()]

with open('stats_out.json', 'w') as f:
    json.dump({'daily_stats': daily_stats, 'recent_problems': recent_problems}, f, indent=2)
