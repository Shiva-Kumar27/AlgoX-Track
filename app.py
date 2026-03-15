from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash)
from functools import wraps
import os

from db.models import (
    init_db,
    run_migrations,
    add_problem,
    add_attempt,
    get_all_problems,
    get_user_attempts,
    get_topic_distribution,
    get_difficulty_distribution,
    get_weekly_progress,
    get_leaderboard_page,
    get_user_stats,
    get_today_stats,
    get_today_solved_problems,
    get_platform_activity,
    search_problems,
    get_user,
    get_db_connection,
    register_user,
    login_user,
    update_username,
    update_email,
    update_password,
    update_platform_usernames,
    update_user_daily_stats,
)
from Core.leaderboard import get_rank_badge, get_achievement_level, get_streak_status, calculate_xp
from Core.analysis import (
    calculate_success_rate, generate_insights, get_level_info
)
from Core.scheduler import start_scheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

_db_initialized = False

# Start background scheduler only in non-debug "real" process
if os.getenv('FLASK_ENV') == 'production' or os.getenv('ENABLE_SCHEDULER') == '1':
    # When using the Werkzeug reloader, only start in the child process
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        try:
            start_scheduler()
        except Exception:
            # Scheduler failures should not prevent the app from starting
            pass

@app.before_request
def init_database():
    global _db_initialized
    if not _db_initialized:
        needs_init = not os.path.exists(DB_PATH)
        if not needs_init:
            try:
                conn = get_db_connection()
                conn.execute("SELECT 1 FROM user_stats LIMIT 1")
                conn.close()
            except Exception:
                needs_init = True
        if needs_init:
            init_db()
        else:
            run_migrations()
        _db_initialized = True

# ============= AUTH HELPERS =============

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' in session:
        return get_user(session['user_id'])
    return None

@app.context_processor
def inject_user():
    return {'current_user': get_current_user()}

# ============= AUTH ROUTES =============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if password != confirm:
            error = 'Passwords do not match.'
        else:
            result = register_user(username, email, password)
            if result['ok']:
                session['user_id']  = result['user_id']
                session['username'] = username
                flash(f'Welcome, {username}! Your account is ready.', 'success')
                return redirect(url_for('index'))
            else:
                error = result['error']
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error   = None
    next_url = request.args.get('next', '/')
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        result   = login_user(username, password)
        if result['ok']:
            user = result['user']
            session['user_id']  = user['user_id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            next_url = request.form.get('next', next_url)
            return redirect(next_url if next_url and next_url.startswith('/') else url_for('index'))
        else:
            error = result['error']
    return render_template('login.html', error=error, next=next_url)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id     = session['user_id']
    user        = get_user(user_id)
    stats       = get_user_stats(user_id) or {}
    topic_dist  = get_topic_distribution(user_id)

    easy   = stats.get('easy_solved', 0)
    medium = stats.get('medium_solved', 0)
    hard   = stats.get('hard_solved', 0)
    total_xp    = calculate_xp(easy, medium, hard)
    level_info  = get_level_info(total_xp)
    achievement = get_achievement_level(stats.get('total_solved', 0))
    _conn = get_db_connection()
    manual_solved = _conn.execute(
        """SELECT COALESCE(COUNT(DISTINCT CASE WHEN result='Solved' THEN problem_id END),0)
           FROM attempts WHERE user_id = ?""",
        (user_id,)
    ).fetchone()[0]
    _conn.close()

    stats['success_rate'] = calculate_success_rate({
        'total_solved': manual_solved,
        'total_attempted': stats.get('total_attempted', 0)
    })

    error       = None
    success_msg = None

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_username':
            res = update_username(user_id, request.form.get('new_username', ''))
            if res['ok']:
                session['username'] = request.form.get('new_username', '').strip()
                success_msg = 'Username updated.'
                user = get_user(user_id)
            else:
                error = res['error']
        elif action == 'update_email':
            res = update_email(user_id, request.form.get('new_email', ''))
            if res['ok']:
                success_msg = 'Email updated.'
                user = get_user(user_id)
            else:
                error = res['error']
        elif action == 'update_password':
            new_pw     = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if new_pw != confirm_pw:
                error = 'New passwords do not match.'
            else:
                res = update_password(user_id, request.form.get('current_password', ''), new_pw)
                if res['ok']:
                    success_msg = 'Password changed successfully.'
                else:
                    error = res['error']
        elif action == 'update_platforms':
            leetcode_username   = request.form.get('leetcode_username', '')
            codeforces_username = request.form.get('codeforces_username', '')
            res = update_platform_usernames(user_id, leetcode_username, codeforces_username)
            if res.get('ok'):
                success_msg = 'Platform usernames updated.'
                user = get_user(user_id)
                # Refresh daily stats for this user with new handles
                try:
                    update_user_daily_stats(user)
                except Exception:
                    # Do not block the request if external APIs fail
                    pass
            else:
                error = res.get('error', 'Unable to update platform usernames.')

    # We removed the synchronous update_user_daily_stats(user) call here
    # to prevent page load delays. Stats are refreshed in the background
    # by the scheduler every 30 mins, or on-demand via the refresh button.

    return render_template('profile.html',
                           user=user, stats=stats,
                           level_info=level_info, achievement=achievement,
                           topic_dist=topic_dist[:5],
                           error=error, success_msg=success_msg)

# ============= MAIN ROUTES =============

@app.route('/')
@login_required
def index():
    user_id = session['user_id']
    user    = get_user(user_id)
    # Background scheduler handles stats fetching now, no sync delay here

    stats   = get_user_stats(user_id) or {}
    topic_dist      = get_topic_distribution(user_id)
    recent_attempts = get_user_attempts(user_id, limit=10)
    today_stats     = get_today_stats(user_id)  # Platform stats for today
    today_problems = get_today_solved_problems(user_id)  # Today's solved problems list

    # total_solved = manual attempts + platform fetches (get_user_stats already includes both)
    total_solved = stats.get('total_solved', 0)

    # Success rate uses only manual attempts for consistency (not inflated by platform counts)
    _conn = get_db_connection()
    manual_solved = _conn.execute(
        """SELECT COALESCE(COUNT(DISTINCT CASE WHEN result='Solved' THEN problem_id END),0)
           FROM attempts WHERE user_id = ?""",
        (user_id,)
    ).fetchone()[0]
    _conn.close()

    stats['success_rate'] = calculate_success_rate({
        'total_solved': manual_solved,
        'total_attempted': stats.get('total_attempted', 0)
    })
    easy, medium, hard = stats.get('easy_solved',0), stats.get('medium_solved',0), stats.get('hard_solved',0)
    total_xp    = calculate_xp(easy, medium, hard)
    level_info  = get_level_info(total_xp)
    achievement = get_achievement_level(total_solved)
    insights    = generate_insights(stats, topic_dist, recent_attempts)
    return render_template('index.html',
                           stats=stats, level_info=level_info,
                           achievement=achievement, insights=insights,
                           recent_attempts=recent_attempts,
                           today_stats=today_stats,
                           today_problems=today_problems,
                           total_solved=total_solved)  # Combined total


@app.route('/api/stats-refresh')
@login_required
def refresh_stats():
    user = get_user(session['user_id'])
    try:
        update_user_daily_stats(user)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/add-problem', methods=['GET', 'POST'])
@login_required
def add_problem_route():
    user_id = session['user_id']
    if request.method == 'POST':
        title, topic = request.form.get('title'), request.form.get('topic')
        difficulty   = request.form.get('difficulty')
        platform     = request.form.get('platform', '')
        problem_url  = request.form.get('problem_url', '')
        result       = request.form.get('result')
        time_taken   = request.form.get('time_taken')
        notes        = request.form.get('notes', '')
        if not all([title, topic, difficulty, result]):
            return jsonify({'error': 'Missing required fields'}), 400
        problem_id = add_problem(title=title, topic=topic, difficulty=difficulty,
                                 platform=platform, problem_url=problem_url)
        add_attempt(user_id=user_id, problem_id=problem_id, result=result,
                    time_taken=int(time_taken) if time_taken else None, notes=notes)
        flash('Problem added!', 'success')
        return redirect(url_for('index'))
    return render_template('add_problem.html')


@app.route('/leaderboard')
@login_required
def leaderboard():
    rankings = get_leaderboard_page(limit=20, offset=0)
    enhanced = []
    for i, rank in enumerate(rankings, 1):
        success_rate = calculate_success_rate({
            'total_solved': rank.get('total_solved', 0),
            'total_attempted': rank.get('total_attempted', 0)
        })
        enhanced.append({
            **rank,
            'rank': i,
            'badge': get_rank_badge(i),
            'achievement': get_achievement_level(rank.get('total_solved', 0)),
            'streak_status': get_streak_status(rank.get('streak_days', 0)),
            'success_rate': success_rate,
            'today_solved': rank.get('today_solved', 0),
        })
    return render_template('leaderboard.html', rankings=enhanced)

# ============= API ROUTES =============

@app.route('/api/problems')
@login_required
def api_get_problems():
    topic = request.args.get('topic')
    difficulty = request.args.get('difficulty')
    problems = search_problems(topic=topic, difficulty=difficulty) if (topic or difficulty) else get_all_problems()
    return jsonify(problems)

@app.route('/api/attempts')
@login_required
def api_get_attempts():
    return jsonify(get_user_attempts(session['user_id'], limit=request.args.get('limit', 50, type=int)))

@app.route('/api/stats')
@login_required
def api_get_stats():
    stats = get_user_stats(session['user_id']) or {}
    easy, medium, hard = stats.get('easy_solved',0), stats.get('medium_solved',0), stats.get('hard_solved',0)
    total_xp = calculate_xp(easy, medium, hard)
    stats['xp'] = total_xp
    stats['level_info'] = get_level_info(total_xp)
    return jsonify(stats)

@app.route('/api/analytics/topic')
@login_required
def api_topic_distribution():
    return jsonify(get_topic_distribution(session['user_id']))

@app.route('/api/analytics/difficulty')
@login_required
def api_difficulty_distribution():
    return jsonify(get_difficulty_distribution(session['user_id']))

@app.route('/api/analytics/progress')
@login_required
def api_weekly_progress():
    return jsonify(get_weekly_progress(session['user_id'], weeks=request.args.get('weeks', 4, type=int)))

@app.route('/api/analytics/platform')
@login_required
def api_platform_activity():
    return jsonify(get_platform_activity(session['user_id']))

@app.route('/api/analytics/heatmap')
@login_required
def api_heatmap():
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT date, SUM(count) as count
        FROM (
            SELECT DATE(attempt_date) as date, COUNT(*) as count
            FROM attempts
            WHERE user_id = ? AND result = 'Solved'
              AND attempt_date >= datetime('now', '-365 days')
            GROUP BY DATE(attempt_date)

            UNION ALL

            SELECT date, SUM(problems_solved) as count
            FROM daily_stats
            WHERE user_id = ?
              AND date >= DATE('now', '-365 days')
              AND problems_solved > 0
            GROUP BY date
        )
        GROUP BY date
        ORDER BY date ASC''',
        (session['user_id'], session['user_id'])
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/recent-solves')
@login_required
def api_recent_solves():
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT platform, title
        FROM recent_problems
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        ''',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/leaderboard/page')
@login_required
def api_leaderboard_page():
    limit  = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    rankings = get_leaderboard_page(limit=limit, offset=offset)
    enhanced = []
    for idx, rank in enumerate(rankings, start=offset + 1):
        success_rate = calculate_success_rate({
            'total_solved': rank.get('total_solved', 0),
            'total_attempted': rank.get('total_attempted', 0)
        })
        enhanced.append({
            **rank,
            'rank': idx,
            'badge': get_rank_badge(idx),
            'achievement': get_achievement_level(rank.get('total_solved', 0)),
            'streak_status': get_streak_status(rank.get('streak_days', 0)),
            'success_rate': success_rate,
            'today_solved': rank.get('today_solved', 0),
        })
    return jsonify(enhanced)

# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(e):   return render_template('404.html'), 404
@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)