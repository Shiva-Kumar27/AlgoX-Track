"""
Core module for AlgoX Track
"""

from .analysis import (
    prepare_topic_chart_data,
    prepare_difficulty_chart_data,
    prepare_progress_chart_data,
    calculate_success_rate,
    get_performance_metrics,
    format_leaderboard_rank,
    get_top_topics,
    calculate_topic_percentages,
    generate_insights,
    get_level_info,
    calculate_xp,
    calculate_level,
    compute_agi_score
)

from .leaderboard import (
    calculate_user_score,
    calculate_xp,
    calculate_level,
    get_rank_badge,
    get_badges,
    calculate_percentile,
    get_achievement_level,
    format_rank_change,
    get_streak_status
)

__all__ = [
    'prepare_topic_chart_data', 'prepare_difficulty_chart_data',
    'prepare_progress_chart_data', 'calculate_success_rate',
    'get_performance_metrics', 'format_leaderboard_rank',
    'get_top_topics', 'calculate_topic_percentages',
    'generate_insights', 'get_level_info', 'calculate_xp',
    'calculate_level', 'compute_agi_score',
    'calculate_user_score', 'get_rank_badge', 'get_badges',
    'calculate_percentile', 'get_achievement_level',
    'format_rank_change', 'get_streak_status'
]
