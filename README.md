# GoalPlanner 🚀

A modern, responsive, daily habit, goal, and task matrix application inspired by spreadsheet matrices (Google Sheets) and developer activity trackers (GitHub contribution heatmap).

---

## ✨ Features

1. **Monthly Grid Matrix (Spreadsheet Tracker)**
   - Matrix layout with your tasks on the Y-axis and days of the month ($1$ to $31$) on the X-axis.
   - Distinct weekend highlighting (warm amber) matching Google Sheets behavior.
   - Today's date column automatically highlighted with an active glow.
   - Smooth, optimistic checkmark toggling that saves immediately without page reload.
   - Daily progress row showing completion fraction ($7/9$) and mini progress bars.
   - Monthly total column calculating accomplishment totals and completion rates per task.

2. **GitHub-Style Contribution Heatmap**
   - 52-week activity grid tracking your consistency across the entire year.
   - 5 intensity levels with classic GitHub green shading.
   - Interactive hover tooltips showing date, completion percentage, and exact tasks accomplished.
   - **Filter Mode**: View overall aggregate consistency or isolate an individual habit (e.g. *DSA* or *Exercise*).
   - Streak counters: Current Active Streak 🔥, Longest Streak 🏆, Total Active Days 📅, and Total Check-offs 🎯.

3. **Task Management Flow**
   - Add new custom tasks with custom category, accent color, and target frequency.
   - Edit, reorder, or archive tasks at any time while preserving historical data.
   - Pre-seeded with core habits: *Goal, Office, DSA, System Design, Development, Content, Expenses, Exercise, Cleaning*.

4. **Today's Quick Checklist & Mobile View (PWA)**
   - Fast, mobile-first daily checklist view with an animated circular progress ring.
   - Daily reflection note box for jotting down reflections or milestones.
   - Progressive Web App (PWA) enabled: tap **"Add to Home Screen"** on iOS/Android for a native app feel.

5. **Yearly Progress Archives**
   - 12-month summary breakdown displaying month-over-month completion rates and best month badges.
   - Switch back and forth between past months and years with full persistence.

6. **Data Portability & Backups**
   - Download full data backups in JSON format.
   - Export spreadsheet-ready CSV files.
   - One-click restore from JSON backups.

---

## 🛠️ Quick Local Setup

### Prerequisites
* Python 3.10+ (Python 3.11 recommended)

### Run Locally
```bash
# Clone or navigate to the directory
cd GoalPlanner

# Install dependencies (Flask is included, gunicorn is optional for production)
pip install -r requirements.txt

# Start the application
python app.py
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

## 🌐 Free Cloud Deployment (Deploy in ~3 Minutes)

You can host GoalPlanner for free on platforms like **Render**, **Railway**, or **Fly.io**:

### Option 1: Deploy on Render
1. Push this project to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of GoalPlanner"
   git remote add origin https://github.com/YOUR_USERNAME/GoalPlanner.git
   git push -u origin main
   ```
2. Go to [render.com](https://render.com) and click **New + > Web Service**.
3. Connect your GitHub repository.
4. Set the settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Click **Create Web Service**. Render will deploy it and give you a permanent HTTPS URL!

### Option 2: Deploy on Railway
1. Go to [railway.app](https://railway.app) and click **New Project > Deploy from GitHub repo**.
2. Select your GoalPlanner repository.
3. Railway automatically detects Python, installs dependencies, and deploys.

---

## 📱 Daily Workflow
1. Bookmark your URL on your phone or desktop (or tap **"Add to Home Screen"** on mobile).
2. The app automatically loads the current month and highlights today's date.
3. Tap checkmarks for the habits you completed today.
4. Your heatmap, current streaks, and monthly stats update instantly!
