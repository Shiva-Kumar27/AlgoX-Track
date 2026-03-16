import requests
import json

query = '''query userProfile($username: String!) {
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
}'''

try:
    resp = requests.post(
        'https://leetcode.com/graphql',
        json={'query': query, 'variables': {'username': 'seishero'}},
        headers={'Content-Type': 'application/json', 'Referer': 'https://leetcode.com', 'User-Agent': 'Mozilla/5.0'}
    )
    with open('lc_out.json', 'w') as f:
        json.dump(resp.json(), f, indent=2)
except Exception as e:
    with open('lc_out.json', 'w') as f:
        f.write(str(e))
