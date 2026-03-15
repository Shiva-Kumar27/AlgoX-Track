import sqlite3

def check_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT platform, problems_solved FROM daily_stats").fetchall()

    if not rows:
        print("No daily stats yet.")
    for r in rows:
        print(dict(r))

    conn.close()

if __name__ == "__main__":
    check_db()
