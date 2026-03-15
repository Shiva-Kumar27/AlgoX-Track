"""
Analytics module for AlgoX Track
Provides data processing functions for dashboard visualizations + smart insights
"""

from typing import List, Dict
from datetime import datetime, timedelta
import math

def prepare_topic_chart_data(topic_dist: List[Dict]) -> Dict:
    if not topic_dist:
        return {'labels': [], 'data': []}
    labels = [item['topic'] for item in topic_dist]
    data = [item['count'] for item in topic_dist]
    return {'labels': labels, 'data': data}

def prepare_difficulty_chart_data(difficulty_dist: Dict[str, int]) -> Dict:
    labels = ['Easy', 'Medium', 'Hard']
    data = [
        difficulty_dist.get('Easy', 0),
        difficulty_dist.get('Medium', 0),
        difficulty_dist.get('Hard', 0)
    ]
    colors = ['#4ade80', '#fbbf24', '#f87171']
    return {'labels': labels, 'data': data, 'colors': colors}

def prepare_progress_chart_data(weekly_progress: List[Dict], weeks: int = 4) -> Dict:
    from datetime import date
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=weeks * 7)
    progress_dict = {}
    for item in weekly_progress:
        date_str = item['date']
        progress_dict[date_str] = item['count']
    labels = []
    data = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        labels.append(current_date.strftime('%m/%d'))
        data.append(progress_dict.get(date_str, 0))
        current_date += timedelta(days=1)
    return {'labels': labels, 'data': data}

def calculate_success_rate(stats: Dict) -> float:
    if not stats or stats.get('total_attempted', 0) == 0:
        return 0.0
    total_solved = stats.get('total_solved', 0)
    total_attempted = stats.get('total_attempted', 0)
    return round((total_solved / total_attempted) * 100, 1)

def calculate_xp(easy: int, medium: int, hard: int) -> int:
    return (easy * 10) + (medium * 25) + (hard * 50)

def calculate_level(total_xp: int) -> int:
    if total_xp <= 0:
        return 1
    return max(1, int(math.floor(math.sqrt(total_xp / 50))) + 1)

def get_level_info(total_xp: int) -> Dict:
    level = calculate_level(total_xp)
    current_level_xp = int(50 * ((level - 1) ** 2))
    next_level_xp = int(50 * (level ** 2))
    progress_xp = total_xp - current_level_xp
    needed_xp = next_level_xp - current_level_xp
    progress_pct = min(100, int((progress_xp / needed_xp * 100)) if needed_xp > 0 else 100)
    return {
        'level': level,
        'total_xp': total_xp,
        'progress_xp': progress_xp,
        'needed_xp': needed_xp,
        'progress_pct': progress_pct,
        'next_level_xp': next_level_xp
    }

def get_performance_metrics(stats: Dict) -> Dict:
    if not stats:
        return {
            'total_solved': 0,
            'success_rate': 0,
            'total_time': 0,
            'avg_time': 0,
            'score': 0,
            'xp': 0,
            'level_info': get_level_info(0)
        }
    total_solved = stats.get('total_solved', 0)
    total_time = stats.get('total_time_spent', 0)
    avg_time = round(total_time / total_solved, 1) if total_solved > 0 else 0
    easy = stats.get('easy_solved', 0)
    medium = stats.get('medium_solved', 0)
    hard = stats.get('hard_solved', 0)
    total_xp = calculate_xp(easy, medium, hard)
    return {
        'total_solved': total_solved,
        'success_rate': calculate_success_rate(stats),
        'total_time': total_time,
        'avg_time': avg_time,
        'score': stats.get('score', 0),
        'streak': stats.get('streak_days', 0),
        'xp': total_xp,
        'level_info': get_level_info(total_xp)
    }

def generate_insights(stats: Dict, topic_dist: List[Dict], recent_attempts: List[Dict]) -> List[Dict]:
    """Generate smart, actionable insights from user data."""
    insights = []
    if not stats:
        return insights

    total_solved = stats.get('total_solved', 0)
    easy = stats.get('easy_solved', 0)
    medium = stats.get('medium_solved', 0)
    hard = stats.get('hard_solved', 0)
    success_rate = calculate_success_rate(stats)
    streak = stats.get('streak_days', 0)

    # 1. Weakest topic insight
    if topic_dist and len(topic_dist) > 1:
        weakest = topic_dist[-1]
        strongest = topic_dist[0]
        insights.append({
            'type': 'weakness',
            'icon': '',
            'title': 'Weakest Topic',
            'message': f"You've only solved {weakest['count']} {weakest['topic']} problems. Focus here to round out your skills.",
            'color': 'warning'
        })

    # 2. Difficulty recommendation
    if total_solved > 0:
        hard_ratio = hard / total_solved if total_solved else 0
        medium_ratio = medium / total_solved if total_solved else 0
        if success_rate >= 75 and medium_ratio < 0.3:
            insights.append({
                'type': 'recommendation',
                'icon': '',
                'title': 'Ready to Level Up',
                'message': f"Your {success_rate}% success rate is strong. Try more Medium problems to accelerate growth.",
                'color': 'success'
            })
        elif success_rate >= 80 and hard_ratio < 0.15 and medium > 5:
            insights.append({
                'type': 'recommendation',
                'icon': '',
                'title': 'Hard Mode Unlocked',
                'message': f"Excellent {success_rate}% success rate with {medium} Mediums solved. You're ready for Hard problems.",
                'color': 'success'
            })
        elif success_rate < 50 and total_solved >= 5:
            insights.append({
                'type': 'warning',
                'icon': '',
                'title': 'Success Rate Drop',
                'message': f"Your success rate is {success_rate}%. Focus on Easy problems to build confidence and patterns.",
                'color': 'danger'
            })

    # 3. Streak insight
    if streak >= 7:
        insights.append({
            'type': 'streak',
            'icon': '',
            'title': 'Consistency King',
            'message': f"{streak}-day streak! You're building powerful habits. Keep it going.",
            'color': 'success'
        })
    elif streak == 0 and total_solved > 0:
        insights.append({
            'type': 'streak',
            'icon': '',
            'title': 'Streak Reset',
            'message': "You broke your streak. Solve just one problem today to restart your momentum.",
            'color': 'warning'
        })

    # 4. Burnout risk detection from recent attempts
    if recent_attempts and len(recent_attempts) >= 5:
        recent_failed = sum(1 for a in recent_attempts[:5] if a.get('result') in ('Attempted', 'Revisit'))
        if recent_failed >= 4:
            insights.append({
                'type': 'burnout',
                'icon': '',
                'title': 'Burnout Risk',
                'message': f"{recent_failed} of your last 5 attempts weren't solved. Take a break or revisit fundamentals.",
                'color': 'danger'
            })

    # 5. AGI Score
    if total_solved >= 3:
        agi = compute_agi_score(stats, topic_dist)
        insights.append({
            'type': 'agi',
            'icon': '',
            'title': 'Algorithmic Growth Index',
            'message': f"Your AGI Score is {agi}/100. This combines difficulty weight, consistency, and improvement trend.",
            'color': 'info',
            'agi_score': agi
        })

    return insights

def compute_agi_score(stats: Dict, topic_dist: List[Dict]) -> int:
    """Compute the Algorithmic Growth Index (0-100)."""
    if not stats:
        return 0
    easy = stats.get('easy_solved', 0)
    medium = stats.get('medium_solved', 0)
    hard = stats.get('hard_solved', 0)
    total = stats.get('total_solved', 1) or 1
    streak = stats.get('streak_days', 0)
    success_rate = calculate_success_rate(stats)

    difficulty_score = min(40, int((easy * 1 + medium * 2.5 + hard * 5) / max(total, 1) * 10))
    consistency_score = min(25, streak * 2)
    improvement_score = min(20, int(success_rate / 5))
    breadth_score = min(15, len(topic_dist) * 2)

    return min(100, difficulty_score + consistency_score + improvement_score + breadth_score)

def format_leaderboard_rank(rankings: List[Dict]) -> List[Dict]:
    formatted = []
    for i, user in enumerate(rankings, 1):
        formatted.append({
            'rank': i,
            'username': user['username'],
            'total_solved': user['total_solved'],
            'easy': user['easy_solved'],
            'medium': user['medium_solved'],
            'hard': user['hard_solved'],
            'score': user['score'],
            'streak': user.get('streak_days', 0)
        })
    return formatted

def get_top_topics(topic_dist: List[Dict], limit: int = 5) -> List[Dict]:
    return topic_dist[:limit] if topic_dist else []

def calculate_topic_percentages(topic_dist: List[Dict]) -> List[Dict]:
    if not topic_dist:
        return []
    total = sum(item['count'] for item in topic_dist)
    result = []
    for item in topic_dist:
        percentage = round((item['count'] / total) * 100, 1) if total > 0 else 0
        result.append({
            'topic': item['topic'],
            'count': item['count'],
            'percentage': percentage
        })
    return result
