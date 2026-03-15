import datetime
from typing import Optional, Set, Tuple

import requests


CODEFORCES_API_URL = "https://codeforces.com/api/user.status"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"


def _today_utc() -> datetime.date:
    return datetime.datetime.utcnow().date()


def _today_local() -> datetime.date:
    return datetime.datetime.now().date()


def _clean_handle(raw: str) -> str:
    """
    Normalize a platform handle that might be a full URL into just the username.
    Examples:
      'https://leetcode.com/john_doe/' -> 'john_doe'
      'https://codeforces.com/profile/foo' -> 'foo'
    """
    if not raw:
        return ""
    raw = raw.strip()
    # If it's not URL-like, keep simple trimming behaviour
    if "://" not in raw:
        return raw.strip("/").split("/")[-1]
    try:
        without_proto = raw.split("://", 1)[1]
        parts = [p for p in without_proto.split("/") if p]
        if not parts:
            return ""
        return parts[-1]
    except Exception:
        return raw.strip("/").split("/")[-1]


def get_codeforces_today(username: str) -> Tuple[int, list]:
    """
    Return (count, titles) for unique Codeforces problems with verdict == 'OK'
    solved today (local date) for the given handle.
    """
    if not username:
        return 0, []

    handle = _clean_handle(username)
    print("Fetching Codeforces for:", handle)

    params = {
        "handle": handle,
        "from": 1,
        "count": 1000,
    }

    try:
        resp = requests.get(
            CODEFORCES_API_URL,
            params=params,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("Codeforces fetch error:", e)
        return 0, []

    if data.get("status") != "OK":
        print("Codeforces API status not OK:", data)
        return 0, []

    today = _today_local()
    # Map (contest_id, index) -> problem name for deduplication with titles
    solved_map: dict = {}

    for submission in data.get("result", []):
        if submission.get("verdict") != "OK":
            continue

        ts = submission.get("creationTimeSeconds")
        if not isinstance(ts, int):
            continue
        # Use local date for comparison (consistent with _today_local)
        sub_date = datetime.datetime.fromtimestamp(ts).date()
        if sub_date != today:
            continue

        problem = submission.get("problem") or {}
        contest_id = problem.get("contestId")
        index = problem.get("index")
        name = problem.get("name", "")
        if index is None:
            index = name
        if index is None:
            continue

        key = (contest_id, index)
        if key not in solved_map:
            solved_map[key] = name or f"Problem {index}"

    titles = list(solved_map.values())
    count = len(titles)
    print("Codeforces today solved (unique):", count)
    return count, titles


def get_leetcode_today(username: str) -> Tuple[int, list]:
    """
    Return (count, titles) for unique LeetCode problems accepted today
    (local date) for a user.

    Uses the recentSubmissionList GraphQL query and filters by
    statusDisplay == "Accepted".
    """
    if not username:
        return 0, []

    handle = _clean_handle(username)
    print("Fetching LeetCode for:", handle)

    query = """
    query userProfile($username: String!) {
      recentSubmissionList(username: $username) {
        titleSlug
        title
        statusDisplay
        timestamp
      }
      recentAcSubmissionList(username: $username) {
        titleSlug
        title
        timestamp
      }
    }
    """
    variables = {"username": handle}

    try:
        resp = requests.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            timeout=10,
            headers={
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com",
                "User-Agent": "Mozilla/5.0",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print("LeetCode fetch error:", e)
        return 0, []

    data = payload.get("data", {}) or {}
    recent = data.get("recentSubmissionList") or []
    accepted_only = data.get("recentAcSubmissionList") or []

    today = _today_local()
    # slug -> display title (slug used for dedup)
    solved_map: dict = {}

    # Primary: check statusDisplay == Accepted from full list
    for sub in recent:
        if sub.get("statusDisplay") != "Accepted":
            continue
        try:
            ts = int(sub["timestamp"])
        except (KeyError, ValueError, TypeError):
            continue
        # Use local date so IST users aren't off by a day
        sub_date = datetime.datetime.fromtimestamp(ts).date()
        if sub_date == today:
            slug = sub.get("titleSlug") or sub.get("title", "")
            title = sub.get("title") or slug
            if slug and slug not in solved_map:
                solved_map[slug] = title

    # Fallback: recentAcSubmissionList (no status filter needed)
    if not solved_map:
        print("LeetCode: falling back to recentAcSubmissionList")
        for sub in accepted_only:
            try:
                ts = int(sub["timestamp"])
            except (KeyError, ValueError, TypeError):
                continue
            sub_date = datetime.datetime.fromtimestamp(ts).date()
            if sub_date == today:
                slug = sub.get("titleSlug") or sub.get("title", "")
                title = sub.get("title") or slug
                if slug and slug not in solved_map:
                    solved_map[slug] = title

    titles = list(solved_map.values())
    count = len(titles)
    print("LeetCode today solved (unique):", count)
    return count, titles


def debug_fetch(username: str) -> None:
    """
    Simple helper to test platform fetching in a Python shell.
    """
    print("=== Debug fetch for:", username, "===")
    print("Codeforces:", get_codeforces_today(username))
    print("LeetCode:", get_leetcode_today(username))

