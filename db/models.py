import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(BASE_DIR, 'database.db')

# Production-style database URL for PostgreSQL deployments.
# Example: postgresql://postgres:password@localhost:5432/dsatracker
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/dsatracker",
)


def get_db_connection():
    """
    Current implementation uses SQLite file for persistence.
    DATABASE_URL is provided for PostgreSQL deployments, but the
    default local dev setup remains SQLite so existing behavior
    is not broken.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Schema.sql')
    conn = get_db_connection()
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def run_migrations():
    """
    Add missing columns/tables to existing databases.
    Keeps backward compatibility with older SQLite files.
    """
    conn = get_db_connection()
    try:
        # ---- users table columns ----
        info = conn.execute("PRAGMA table_info(users)").fetchall()
        columns = [row[1] for row in info]

        if 'password_hash' not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''"
            )

        if 'leetcode_username' not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN leetcode_username VARCHAR(100)"
            )

        if 'codeforces_username' not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN codeforces_username VARCHAR(100)"
            )

        # ---- daily_stats table ----
        ds_info = conn.execute("PRAGMA table_info(daily_stats)").fetchall()
        if not ds_info:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    problems_solved INTEGER NOT NULL DEFAULT 0,
                    date DATE NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date "
                "ON daily_stats(user_id, date)"
            )

        # ---- recent_problems table ----
        rp_info = conn.execute("PRAGMA table_info(recent_problems)").fetchall()
        if not rp_info:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recent_problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    title VARCHAR(300) NOT NULL,
                    date DATE NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_recent_problems_user_date "
                "ON recent_problems(user_id, date DESC)"
            )

        conn.commit()
    finally:
        conn.close()


# ============= AUTH OPERATIONS =============

def register_user(username: str, email: str, password: str) -> Dict:
    """Register a new user. Returns {'ok': True, 'user_id': int} or {'ok': False, 'error': str}."""
    if len(username) < 3:
        return {'ok': False, 'error': 'Username must be at least 3 characters.'}
    if len(password) < 6:
        return {'ok': False, 'error': 'Password must be at least 6 characters.'}
    password_hash = generate_password_hash(password)
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username.strip(), email.strip() if email else None, password_hash)
        )
        user_id = cursor.lastrowid
        conn.execute('INSERT INTO user_stats (user_id) VALUES (?)', (user_id,))
        conn.commit()
        return {'ok': True, 'user_id': user_id}
    except sqlite3.IntegrityError as e:
        err = str(e)
        if 'username' in err:
            return {'ok': False, 'error': 'Username already taken.'}
        if 'email' in err:
            return {'ok': False, 'error': 'Email already registered.'}
        return {'ok': False, 'error': 'Registration failed.'}
    finally:
        conn.close()

def login_user(username: str, password: str) -> Dict:
    """Verify credentials. Returns {'ok': True, 'user': dict} or {'ok': False, 'error': str}."""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', (username.strip(),)
    ).fetchone()
    conn.close()
    if not user:
        return {'ok': False, 'error': 'Invalid username or password.'}
    if not check_password_hash(user['password_hash'], password):
        return {'ok': False, 'error': 'Invalid username or password.'}
    return {'ok': True, 'user': dict(user)}

def update_username(user_id: int, new_username: str) -> Dict:
    """Change a user's username."""
    if len(new_username.strip()) < 3:
        return {'ok': False, 'error': 'Username must be at least 3 characters.'}
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE users SET username = ? WHERE user_id = ?',
            (new_username.strip(), user_id)
        )
        conn.commit()
        return {'ok': True}
    except sqlite3.IntegrityError:
        return {'ok': False, 'error': 'Username already taken.'}
    finally:
        conn.close()

def update_email(user_id: int, new_email: str) -> Dict:
    """Change a user's email."""
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE users SET email = ? WHERE user_id = ?',
            (new_email.strip() if new_email else None, user_id)
        )
        conn.commit()
        return {'ok': True}
    except sqlite3.IntegrityError:
        return {'ok': False, 'error': 'Email already in use.'}
    finally:
        conn.close()

def update_password(user_id: int, current_password: str, new_password: str) -> Dict:
    """Change a user's password after verifying the current one."""
    if len(new_password) < 6:
        return {'ok': False, 'error': 'New password must be at least 6 characters.'}
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    if not user:
        return {'ok': False, 'error': 'User not found.'}
    if not check_password_hash(user['password_hash'], current_password):
        return {'ok': False, 'error': 'Current password is incorrect.'}
    new_hash = generate_password_hash(new_password)
    conn = get_db_connection()
    conn.execute('UPDATE users SET password_hash = ? WHERE user_id = ?', (new_hash, user_id))
    conn.commit()
    conn.close()
    return {'ok': True}

# ============= USER OPERATIONS =============

def get_user(user_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def update_platform_usernames(
    user_id: int,
    leetcode_username: Optional[str],
    codeforces_username: Optional[str],
) -> Dict:
    """
    Update a user's external platform usernames.
    """
    from Core.fetch_problems import _clean_handle  # reuse normalization

    conn = get_db_connection()
    try:
        lc = _clean_handle(leetcode_username) if leetcode_username else None
        cf = _clean_handle(codeforces_username) if codeforces_username else None
        conn.execute(
            '''
            UPDATE users
            SET leetcode_username = ?, codeforces_username = ?
            WHERE user_id = ?
            ''',
            (
                lc,
                cf,
                user_id,
            ),
        )
        conn.commit()
        return {'ok': True}
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict]:
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(username: str, email: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
        (username, email, '')
    )
    user_id = cursor.lastrowid
    conn.execute('INSERT INTO user_stats (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
    return user_id

# ============= PROBLEM OPERATIONS =============

def add_problem(title: str, topic: str, difficulty: str,
                platform: str = None, problem_url: str = None,
                tags: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.execute(
        '''INSERT INTO problems (title, topic, difficulty, platform, problem_url, tags)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (title, topic, difficulty, platform, problem_url, tags)
    )
    problem_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return problem_id

def get_problem(problem_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    problem = conn.execute('SELECT * FROM problems WHERE problem_id = ?', (problem_id,)).fetchone()
    conn.close()
    return dict(problem) if problem else None

def get_all_problems() -> List[Dict]:
    conn = get_db_connection()
    problems = conn.execute('SELECT * FROM problems ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(p) for p in problems]

def search_problems(topic: str = None, difficulty: str = None) -> List[Dict]:
    conn = get_db_connection()
    query = 'SELECT * FROM problems WHERE 1=1'
    params = []
    if topic:
        query += ' AND topic = ?'
        params.append(topic)
    if difficulty:
        query += ' AND difficulty = ?'
        params.append(difficulty)
    query += ' ORDER BY created_at DESC'
    problems = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(p) for p in problems]

# ============= ATTEMPT OPERATIONS =============

def add_attempt(user_id: int, problem_id: int, result: str,
                time_taken: int = None, notes: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.execute(
        '''INSERT INTO attempts (user_id, problem_id, result, time_taken, notes)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, problem_id, result, time_taken, notes)
    )
    attempt_id = cursor.lastrowid
    update_user_stats(user_id, conn)
    conn.commit()
    conn.close()
    return attempt_id

def get_user_attempts(user_id: int, limit: int = 50) -> List[Dict]:
    conn = get_db_connection()
    attempts = conn.execute(
        '''SELECT a.*, p.title, p.topic, p.difficulty, p.platform
           FROM attempts a
           JOIN problems p ON a.problem_id = p.problem_id
           WHERE a.user_id = ?
           ORDER BY a.attempt_date DESC
           LIMIT ?''',
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(a) for a in attempts]

def get_attempt(attempt_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    attempt = conn.execute('SELECT * FROM attempts WHERE attempt_id = ?', (attempt_id,)).fetchone()
    conn.close()
    return dict(attempt) if attempt else None

# ============= ANALYTICS OPERATIONS =============

def get_topic_distribution(user_id: int) -> List[Dict]:
    conn = get_db_connection()
    data = conn.execute(
        '''SELECT p.topic, COUNT(*) as count
           FROM attempts a
           JOIN problems p ON a.problem_id = p.problem_id
           WHERE a.user_id = ? AND a.result = 'Solved'
           GROUP BY p.topic
           ORDER BY count DESC''',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in data]

def get_difficulty_distribution(user_id: int) -> Dict[str, int]:
    conn = get_db_connection()
    data = conn.execute(
        '''SELECT p.difficulty, COUNT(*) as count
           FROM attempts a
           JOIN problems p ON a.problem_id = p.problem_id
           WHERE a.user_id = ? AND a.result = 'Solved'
           GROUP BY p.difficulty''',
        (user_id,)
    ).fetchall()
    conn.close()
    result = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    for row in data:
        result[row['difficulty']] = row['count']
    return result

def get_weekly_progress(user_id: int, weeks: int = 4) -> List[Dict]:
    conn = get_db_connection()
    data = conn.execute(
        '''SELECT DATE(attempt_date) as date, COUNT(*) as count
           FROM attempts
           WHERE user_id = ? AND result = 'Solved'
           AND attempt_date >= datetime('now', '-' || ? || ' days')
           GROUP BY DATE(attempt_date)
           ORDER BY date ASC''',
        (user_id, weeks * 7)
    ).fetchall()
    conn.close()
    return [dict(row) for row in data]

def get_platform_activity(user_id: int) -> List[Dict]:
    conn = get_db_connection()
    data = conn.execute(
        '''SELECT 'Manual' as platform, COUNT(*) as count
           FROM attempts
           WHERE user_id = ? AND result = 'Solved'
           UNION ALL
           SELECT platform, SUM(problems_solved) as count
           FROM daily_stats
           WHERE user_id = ? AND problems_solved > 0
           GROUP BY platform''',
        (user_id, user_id)
    ).fetchall()
    conn.close()
    
    total = sum(row['count'] for row in data if row['count'])
    
    result = []
    for row in data:
        count = row['count']
        if count > 0:
            pct = round((count / total) * 100) if total > 0 else 0
            # Capitalize platform name for UI consistency
            platform_name = row['platform'].title() if row['platform'] != 'Manual' else 'Manual'
            result.append({
                'platform': platform_name,
                'count': count,
                'pct': pct
            })
            
    # Sort by count descending
    result.sort(key=lambda x: x['count'], reverse=True)
    return result

def get_today_stats(user_id: int) -> Dict:
    """
    Get today's solved problems from daily_stats.
    Returns {'leetcode': int, 'codeforces': int, 'total': int}
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT platform, problems_solved
            FROM daily_stats
            WHERE user_id = ? AND date = DATE('now', 'localtime')
            """,
            (user_id,)
        ).fetchall()
        
        stats = {'leetcode': 0, 'codeforces': 0, 'total': 0}
        for row in rows:
            platform = row['platform']
            count = row['problems_solved']
            stats[platform] = count
            stats['total'] += count
        
        return stats
    finally:
        conn.close()

def get_today_solved_problems(user_id: int) -> List[Dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT platform, title
            FROM recent_problems
            WHERE user_id = ? AND date = DATE('now', 'localtime')
            ORDER BY platform, id ASC
            """,
            (user_id,)
        ).fetchall()

        problems = []
        for row in rows:
            problems.append({
                'platform': row['platform'],
                'title': row['title'],
                'time': 'Today'
            })

        return problems
    finally:
        conn.close()


def get_user_stats(user_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    stats = conn.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,)).fetchone()
    if not stats:
        conn.close()
        return None
    stats = dict(stats)

    # Add platform-fetched totals so profile page matches dashboard
    platform_total = conn.execute(
        """
        SELECT COALESCE(SUM(problems_solved), 0)
        FROM daily_stats
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]
    conn.close()

    stats['total_solved'] = (stats.get('total_solved') or 0) + platform_total
    return stats

# ============= LEADERBOARD OPERATIONS =============

def get_leaderboard(limit: int = 10) -> List[Dict]:
    conn = get_db_connection()
    leaderboard = conn.execute(
        '''
        SELECT
            u.username,
            s.total_solved,
            s.total_attempted,
            s.easy_solved,
            s.medium_solved,
            s.hard_solved,
            s.score,
            s.streak_days,
            s.total_time_spent,
            COALESCE(ds.today_solved, 0) AS today_solved
        FROM user_stats s
        JOIN users u ON s.user_id = u.user_id
        LEFT JOIN (
            SELECT user_id, SUM(problems_solved) AS today_solved
            FROM daily_stats
            WHERE date = DATE('now', 'localtime')
            GROUP BY user_id
        ) ds ON ds.user_id = s.user_id
        WHERE s.total_solved > 0
        ORDER BY s.score DESC, s.total_solved DESC, s.streak_days DESC
        LIMIT ?
        ''',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in leaderboard]

def get_leaderboard_page(limit: int = 10, offset: int = 0) -> List[Dict]:
    conn = get_db_connection()
    leaderboard = conn.execute(
        '''
        SELECT
            u.username,
            s.total_solved,
            s.total_attempted,
            s.easy_solved,
            s.medium_solved,
            s.hard_solved,
            s.score,
            s.streak_days,
            s.total_time_spent,
            COALESCE(ds.today_solved, 0) AS today_solved
        FROM user_stats s
        JOIN users u ON s.user_id = u.user_id
        LEFT JOIN (
            SELECT user_id, SUM(problems_solved) AS today_solved
            FROM daily_stats
            WHERE date = DATE('now', 'localtime')
            GROUP BY user_id
        ) ds ON ds.user_id = s.user_id
        WHERE s.total_solved > 0
        ORDER BY s.score DESC, s.total_solved DESC, s.streak_days DESC
        LIMIT ? OFFSET ?
        ''',
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(row) for row in leaderboard]


def update_user_daily_stats(user: Dict) -> None:
    """
    Fetch and persist today's solved counts + problem titles for supported platforms.

    `user` is the dict returned by `get_user` / `login_user`.
    """
    from Core.fetch_problems import (  # lazy import to avoid cycles
        get_codeforces_today,
        get_leetcode_today,
    )

    user_id = user.get('user_id')
    if not user_id:
        return

    leetcode_username = user.get('leetcode_username')
    codeforces_username = user.get('codeforces_username')

    # Nothing to do if user hasn't configured any handles
    if not leetcode_username and not codeforces_username:
        return

    today_str = date.today().strftime('%Y-%m-%d')
    conn = get_db_connection()
    try:
        if leetcode_username:
            try:
                lc_count, lc_titles = get_leetcode_today(leetcode_username)
            except Exception:
                lc_count, lc_titles = 0, []
            _upsert_daily_stat(conn, user_id, 'leetcode', lc_count, today_str)
            if lc_titles:
                _upsert_recent_problems(conn, user_id, 'leetcode', lc_titles, today_str)

        if codeforces_username:
            try:
                cf_count, cf_titles = get_codeforces_today(codeforces_username)
            except Exception:
                cf_count, cf_titles = 0, []
            _upsert_daily_stat(conn, user_id, 'codeforces', cf_count, today_str)
            if cf_titles:
                _upsert_recent_problems(conn, user_id, 'codeforces', cf_titles, today_str)

        # NOTE: We do NOT touch user_stats.total_solved here.
        # That column is managed exclusively by update_user_stats() which
        # counts from the attempts table. Platform solves are tracked in
        # daily_stats and recent_problems, and added at read time in
        # get_user_stats() so the profile page stays in sync.

        conn.commit()
    finally:
        conn.close()


def _upsert_recent_problems(
    conn: sqlite3.Connection,
    user_id: int,
    platform: str,
    titles: list,
    date_str: str,
) -> None:
    """
    Replace today's platform titles for this user.
    Deletes existing rows for (user, platform, date) and re-inserts
    so the list always reflects the latest fetch result.
    """
    conn.execute(
        'DELETE FROM recent_problems WHERE user_id = ? AND platform = ? AND date = ?',
        (user_id, platform, date_str),
    )
    for title in titles:
        conn.execute(
            'INSERT INTO recent_problems (user_id, platform, title, date) VALUES (?, ?, ?, ?)',
            (user_id, platform, title, date_str),
        )


def _upsert_daily_stat(
    conn: sqlite3.Connection,
    user_id: int,
    platform: str,
    problems_solved: int,
    date_str: str,
) -> None:
    """
    Insert or update a row in daily_stats for (user, platform, date).
    Compatible with older SQLite (no UPSERT syntax).
    """
    existing = conn.execute(
        '''
        SELECT id FROM daily_stats
        WHERE user_id = ? AND platform = ? AND date = ?
        ''',
        (user_id, platform, date_str),
    ).fetchone()

    if existing:
        conn.execute(
            '''
            UPDATE daily_stats
            SET problems_solved = ?
            WHERE id = ?
            ''',
            (problems_solved, existing['id']),
        )
    else:
        conn.execute(
            '''
            INSERT INTO daily_stats (user_id, platform, problems_solved, date)
            VALUES (?, ?, ?, ?)
            ''',
            (user_id, platform, problems_solved, date_str),
        )

# ============= STATS & PROGRESS HELPERS =============

def update_user_stats(user_id: int, conn=None):
    streak = calculate_streak(user_id)
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    stats = conn.execute(
        '''SELECT 
               COUNT(DISTINCT CASE WHEN a.result = 'Solved' THEN a.problem_id END) as total_solved,
               COUNT(*) as total_attempted,
               COUNT(DISTINCT CASE WHEN a.result = 'Solved' AND p.difficulty = 'Easy' THEN a.problem_id END) as easy_solved,
               COUNT(DISTINCT CASE WHEN a.result = 'Solved' AND p.difficulty = 'Medium' THEN a.problem_id END) as medium_solved,
               COUNT(DISTINCT CASE WHEN a.result = 'Solved' AND p.difficulty = 'Hard' THEN a.problem_id END) as hard_solved,
               SUM(CASE WHEN a.time_taken IS NOT NULL THEN a.time_taken ELSE 0 END) as total_time
           FROM attempts a
           JOIN problems p ON a.problem_id = p.problem_id
           WHERE a.user_id = ?''',
        (user_id,)
    ).fetchone()

    score = stats['easy_solved'] + (stats['medium_solved'] * 2) + (stats['hard_solved'] * 3)

    last_solved = conn.execute(
        '''SELECT MAX(DATE(attempt_date)) as last_date
           FROM attempts
           WHERE user_id = ? AND result = 'Solved' ''',
        (user_id,)
    ).fetchone()
    last_solved_date = last_solved['last_date'] if last_solved else None

    existing = conn.execute('SELECT user_id FROM user_stats WHERE user_id = ?', (user_id,)).fetchone()

    if existing:
        conn.execute(
            '''UPDATE user_stats
               SET total_solved = ?, total_attempted = ?, easy_solved = ?,
                   medium_solved = ?, hard_solved = ?, total_time_spent = ?,
                   score = ?, last_solved_date = ?, streak_days = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?''',
            (stats['total_solved'], stats['total_attempted'], stats['easy_solved'],
             stats['medium_solved'], stats['hard_solved'], stats['total_time'],
             score, last_solved_date, streak, user_id)
        )
    else:
        conn.execute(
            '''INSERT INTO user_stats 
               (user_id, total_solved, total_attempted, easy_solved, medium_solved,
                hard_solved, total_time_spent, score, last_solved_date, streak_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, stats['total_solved'], stats['total_attempted'], stats['easy_solved'],
             stats['medium_solved'], stats['hard_solved'], stats['total_time'],
             score, last_solved_date, streak)
        )

    if should_close:
        conn.commit()
        conn.close()

def calculate_streak(user_id: int) -> int:
    conn = get_db_connection()
    
    # Get all dates where user solved something (manual OR platform)
    dates = conn.execute(
        '''
        SELECT DISTINCT solve_date as date FROM (
            SELECT DATE(attempt_date) as solve_date
            FROM attempts
            WHERE user_id = ? AND result = 'Solved'
            
            UNION
            
            SELECT date as solve_date
            FROM daily_stats
            WHERE user_id = ? AND problems_solved > 0
        )
        ORDER BY date DESC
        ''',
        (user_id, user_id)
    ).fetchall()
    conn.close()

    if not dates:
        return 0

    streak = 1
    today = date.today()
    yesterday = today - timedelta(days=1)
    dates_list = [datetime.strptime(d['date'], '%Y-%m-%d').date() for d in dates]

    if dates_list[0] not in [today, yesterday]:
        return 0

    for i in range(len(dates_list) - 1):
        diff = (dates_list[i] - dates_list[i + 1]).days
        if diff == 1:
            streak += 1
        else:
            break

    return streak


# ============= DAILY UPDATE FOR ALL USERS =============

def get_all_users() -> List[Dict]:
    """
    Return all users as dicts.
    Used by the scheduled daily progress updater.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_user_daily_stats_by_id(user_id: int) -> None:
    """
    Convenience wrapper to update daily stats using only user_id.
    """
    user = get_user(user_id)
    if not user:
        return
    update_user_daily_stats(user)


def update_all_users_progress() -> None:
    """
    Iterate over all users and refresh their daily_stats entries
    for today from external coding platforms.
    """
    users = get_all_users()
    for user in users:
        user_id = user.get("user_id")
        if not user_id:
            continue
        print("Updating stats for user:", user_id)
        try:
            update_user_daily_stats_by_id(user_id)
        except Exception as e:
            # Log but continue with other users
            print("Error updating stats for user", user_id, ":", e)
            continue