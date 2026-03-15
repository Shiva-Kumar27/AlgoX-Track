"""
Leaderboard calculation module for AlgoX Track
Handles scoring logic, XP, levels, and ranking
"""

from typing import Dict
import math

DIFFICULTY_POINTS = {
    'Easy': 1,
    'Medium': 2,
    'Hard': 3
}

XP_VALUES = {
    'Easy': 10,
    'Medium': 25,
    'Hard': 50
}

def calculate_user_score(easy: int, medium: int, hard: int) -> int:
    return (easy * DIFFICULTY_POINTS['Easy'] +
            medium * DIFFICULTY_POINTS['Medium'] +
            hard * DIFFICULTY_POINTS['Hard'])

def calculate_xp(easy: int, medium: int, hard: int) -> int:
    return (easy * XP_VALUES['Easy'] +
            medium * XP_VALUES['Medium'] +
            hard * XP_VALUES['Hard'])

def calculate_level(total_xp: int) -> int:
    if total_xp <= 0:
        return 1
    return max(1, int(math.floor(math.sqrt(total_xp / 50))) + 1)

def get_rank_badge(rank: int) -> str:
    return f'#{rank}'

def calculate_percentile(user_score: int, all_scores: list) -> float:
    if not all_scores:
        return 0.0
    below = sum(1 for score in all_scores if score < user_score)
    percentile = (below / len(all_scores)) * 100
    return round(percentile, 1)

def get_achievement_level(total_solved: int) -> Dict:
    levels = [
        {'name': 'Recruit', 'min': 0, 'max': 10, 'icon': ''},
        {'name': 'Novice', 'min': 11, 'max': 25, 'icon': ''},
        {'name': 'Apprentice', 'min': 26, 'max': 50, 'icon': ''},
        {'name': 'Adept', 'min': 51, 'max': 100, 'icon': ''},
        {'name': 'Expert', 'min': 101, 'max': 200, 'icon': ''},
        {'name': 'Master', 'min': 201, 'max': 999999, 'icon': ''}
    ]
    for level in levels:
        if level['min'] <= total_solved <= level['max']:
            return {
                'name': level['name'],
                'icon': level['icon'],
                'progress': total_solved - level['min'],
                'next_milestone': level['max'] + 1 if level['max'] < 999999 else None
            }
    return {'name': 'Recruit', 'icon': '', 'progress': 0, 'next_milestone': 10}

def get_badges(total_solved: int, streak: int, hard_solved: int, success_rate: float) -> list:
    badges = []
    if streak >= 7:
        badges.append({'name': 'Consistency King', 'icon': '', 'desc': f'{streak}-day streak'})
    if hard_solved >= 10:
        badges.append({'name': 'Hard Crusher', 'icon': '', 'desc': f'{hard_solved} Hard solved'})
    if success_rate >= 80 and total_solved >= 10:
        badges.append({'name': 'Sharp Mind', 'icon': '', 'desc': f'{success_rate}% success rate'})
    if total_solved >= 50:
        badges.append({'name': 'Half Century', 'icon': '', 'desc': '50+ problems solved'})
    if total_solved >= 100:
        badges.append({'name': 'Centurion', 'icon': '', 'desc': '100+ problems solved'})
    return badges

def format_rank_change(current_rank: int, previous_rank: int = None) -> str:
    if previous_rank is None:
        return 'NEW'
    change = previous_rank - current_rank
    if change > 0:
        return f'↑{change}'
    elif change < 0:
        return f'↓{abs(change)}'
    else:
        return '━'

def get_streak_status(streak_days: int) -> Dict:
    if streak_days == 0:
        return {'status': 'inactive', 'message': 'No streak', 'color': 'gray'}
    elif streak_days < 7:
        return {'status': 'building', 'message': f'{streak_days}d streak', 'color': 'orange'}
    elif streak_days < 30:
        return {'status': 'strong', 'message': f'{streak_days}d streak', 'color': 'red'}
    else:
        return {'status': 'legendary', 'message': f'{streak_days}d streak', 'color': 'purple'}
