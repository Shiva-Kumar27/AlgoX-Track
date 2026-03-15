# AlgoX Track

AlgoX Track is a full-stack coding activity tracker that automatically tracks your problem-solving progress across platforms like LeetCode and Codeforces. It provides analytics such as daily streaks, activity heatmaps, leaderboard rankings, and performance insights to help developers stay consistent with their Data Structures and Algorithms practice.

---

# Features

* Automatic fetching of solved problems from coding platforms
* Manual problem logging for custom practice
* Daily activity heatmap
* Current streak tracking
* Platform activity analytics
* Leaderboard with rankings
* Difficulty and topic analytics
* Recent solved problems display
* Profile management

---

# Supported Platforms

* LeetCode
* Codeforces

The system fetches solved problems using their APIs and updates the analytics automatically.

---

# Tech Stack

Backend

* Python
* Flask

Frontend

* HTML
* Tailwind CSS
* JavaScript
* Chart.js
* Alpine.js

Database

* SQLite (development)
* PostgreSQL (recommended for deployment)

Background Tasks

* APScheduler (for periodic platform data fetching)

---

# Project Structure

```
DsaTracker
│
├── app.py
├── Core
│   ├── analysis.py
│   ├── fetch_problems.py
│   ├── leaderboard.py
│   └── scheduler.py
│
├── db
│   ├── models.py
│   └── Schema.sql
│
├── templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   └── leaderboard.html
│
├── static
│   ├── main.js
│   └── style.css
│
├── requirements.txt
└── README.md
```

---

# Required Python Packages

Install these dependencies before running the project.

```
Flask
requests
apscheduler
psycopg2-binary
```

If requirements.txt is present, install everything using:

```
pip install -r requirements.txt
```

---

# How to Run the Project

1. Clone the repository

```
git clone https://github.com/YOUR_USERNAME/algox-track.git
```

2. Navigate to the project folder

```
cd algox-track
```

3. Create a virtual environment

```
python -m venv venv
```

4. Activate the virtual environment

Windows

```
venv\Scripts\activate
```

Linux / Mac

```
source venv/bin/activate
```

5. Install dependencies

```
pip install -r requirements.txt
```

6. Run the application

```
python app.py
```

7. Open the application in browser

```
http://localhost:5000
```

---

# How It Works

1. Users create an account and link their platform usernames.
2. The system fetches solved problems from platforms using their APIs.
3. Data is stored in the database for analytics.
4. Dashboards visualize the data using charts and heatmaps.

---

# Why This Project Is Useful

* Helps developers stay consistent with DSA practice
* Tracks progress automatically across platforms
* Provides insights into weak topics and difficulty distribution
* Encourages consistency through streak tracking
* Helps compare progress with peers using leaderboards

---

# Future Improvements

* Support for more coding platforms
* Docker-based deployment
* Email reminders for daily coding streaks
* Advanced analytics with machine learning recommendations

---


