import sqlite3
import os
import calendar
from datetime import datetime, date, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "goalplanner.db")

DEFAULT_TASKS = [
    {"title": "Goal", "category": "Milestone", "color": "#2563eb", "icon": "flag", "target_frequency": "daily", "sort_order": 0},
    {"title": "Office", "category": "Work", "color": "#4f46e5", "icon": "briefcase", "target_frequency": "weekdays", "sort_order": 1},
    {"title": "DSA", "category": "Learning", "color": "#10b981", "icon": "code-2", "target_frequency": "daily", "sort_order": 2},
    {"title": "System Design", "category": "Learning", "color": "#8b5cf6", "icon": "network", "target_frequency": "daily", "sort_order": 3},
    {"title": "Development", "category": "Work", "color": "#0ea5e9", "icon": "laptop", "target_frequency": "daily", "sort_order": 4},
    {"title": "Content", "category": "Creative", "color": "#ec4899", "icon": "video", "target_frequency": "daily", "sort_order": 5},
    {"title": "Expenses", "category": "Personal", "color": "#f59e0b", "icon": "wallet", "target_frequency": "daily", "sort_order": 6},
    {"title": "Exercise", "category": "Health", "color": "#16a34a", "icon": "dumbbell", "target_frequency": "daily", "sort_order": 7},
    {"title": "Cleaning", "category": "Personal", "color": "#06b6d4", "icon": "sparkles", "target_frequency": "daily", "sort_order": 8},
]

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        color TEXT DEFAULT '#3b82f6',
        icon TEXT DEFAULT 'check-circle',
        target_frequency TEXT DEFAULT 'daily',
        sort_order INTEGER DEFAULT 0,
        is_archived INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 1,
        notes TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        UNIQUE(task_id, date)
    )
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_completions_date ON completions(date);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_completions_task_date ON completions(task_id, date);
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_summaries (
        date TEXT PRIMARY KEY,
        daily_goal_achieved INTEGER DEFAULT 0,
        focus_note TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Check if tasks table is empty. If so, seed defaults.
    cursor.execute("SELECT COUNT(*) AS cnt FROM tasks")
    count = cursor.fetchone()["cnt"]
    if count == 0:
        for t in DEFAULT_TASKS:
            cursor.execute("""
            INSERT INTO tasks (title, category, color, icon, target_frequency, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (t["title"], t["category"], t["color"], t["icon"], t["target_frequency"], t["sort_order"]))
    
    conn.commit()
    conn.close()

# ----------------- Tasks CRUD ----------------- #

def get_all_tasks(include_archived=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_archived:
        cursor.execute("SELECT * FROM tasks ORDER BY sort_order ASC, id ASC")
    else:
        cursor.execute("SELECT * FROM tasks WHERE is_archived = 0 ORDER BY sort_order ASC, id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_task(title, category="General", color="#3b82f6", icon="check-circle", target_frequency="daily"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM tasks")
    next_order = cursor.fetchone()["next_order"]
    
    cursor.execute("""
    INSERT INTO tasks (title, category, color, icon, target_frequency, sort_order)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (title.strip(), category.strip(), color.strip(), icon.strip(), target_frequency, next_order))
    task_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()
    return task

def update_task(task_id, title=None, category=None, color=None, icon=None, target_frequency=None, is_archived=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    if title is not None:
        fields.append("title = ?")
        values.append(title.strip())
    if category is not None:
        fields.append("category = ?")
        values.append(category.strip())
    if color is not None:
        fields.append("color = ?")
        values.append(color.strip())
    if icon is not None:
        fields.append("icon = ?")
        values.append(icon.strip())
    if target_frequency is not None:
        fields.append("target_frequency = ?")
        values.append(target_frequency)
    if is_archived is not None:
        fields.append("is_archived = ?")
        values.append(1 if is_archived else 0)
        
    if not fields:
        conn.close()
        return None
        
    values.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(sql, values)
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_task(task_id, hard_delete=False):
    conn = get_connection()
    cursor = conn.cursor()
    if hard_delete:
        cursor.execute("DELETE FROM completions WHERE task_id = ?", (task_id,))
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    else:
        cursor.execute("UPDATE tasks SET is_archived = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True

def reorder_tasks(task_ids):
    conn = get_connection()
    cursor = conn.cursor()
    for index, task_id in enumerate(task_ids):
        cursor.execute("UPDATE tasks SET sort_order = ? WHERE id = ?", (index, task_id))
    conn.commit()
    conn.close()
    return True

# ----------------- Completions & Matrix ----------------- #

def toggle_completion(task_id, date_str, target_state=None):
    """
    Toggles or sets the completion state for a task on a given date (YYYY-MM-DD).
    Returns (task_id, date_str, completed: bool).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM completions WHERE task_id = ? AND date = ?", (task_id, date_str))
    row = cursor.fetchone()
    
    if target_state is not None:
        new_state = 1 if target_state else 0
    else:
        new_state = 0 if (row and row["completed"] == 1) else 1
        
    if row:
        cursor.execute("""
        UPDATE completions 
        SET completed = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE task_id = ? AND date = ?
        """, (new_state, task_id, date_str))
    else:
        cursor.execute("""
        INSERT INTO completions (task_id, date, completed)
        VALUES (?, ?, ?)
        """, (task_id, date_str, new_state))
        
    conn.commit()
    conn.close()
    return {"task_id": task_id, "date": date_str, "completed": bool(new_state)}

def toggle_daily_goal(date_str, target_state=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT daily_goal_achieved FROM daily_summaries WHERE date = ?", (date_str,))
    row = cursor.fetchone()
    
    if target_state is not None:
        new_state = 1 if target_state else 0
    else:
        new_state = 0 if (row and row["daily_goal_achieved"] == 1) else 1
        
    if row:
        cursor.execute("""
        UPDATE daily_summaries 
        SET daily_goal_achieved = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE date = ?
        """, (new_state, date_str))
    else:
        cursor.execute("""
        INSERT INTO daily_summaries (date, daily_goal_achieved)
        VALUES (?, ?)
        """, (date_str, new_state))
        
    conn.commit()
    conn.close()
    return {"date": date_str, "daily_goal_achieved": bool(new_state)}

def save_daily_note(date_str, note):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM daily_summaries WHERE date = ?", (date_str,))
    if cursor.fetchone():
        cursor.execute("UPDATE daily_summaries SET focus_note = ?, updated_at = CURRENT_TIMESTAMP WHERE date = ?", (note, date_str))
    else:
        cursor.execute("INSERT INTO daily_summaries (date, focus_note) VALUES (?, ?)", (date_str, note))
    conn.commit()
    conn.close()
    return {"date": date_str, "note": note}

def get_matrix(year: int, month: int):
    """
    Returns the full matrix view for the given year and month.
    Columns: Day 1..N with day of week, weekend indicator, today indicator.
    Rows: Each active task with completion array for days 1..N.
    Summary: Daily total & percentage, Task monthly total & rate.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Get days in the month
    num_days = calendar.monthrange(year, month)[1]
    today_str = date.today().isoformat()
    
    days_info = []
    day_date_strs = []
    for day in range(1, num_days + 1):
        cur_date = date(year, month, day)
        date_str = cur_date.isoformat()
        day_date_strs.append(date_str)
        is_weekend = cur_date.weekday() in (5, 6) # Saturday, Sunday
        days_info.append({
            "day": day,
            "date": date_str,
            "day_of_week": cur_date.strftime("%a"), # Mon, Tue, etc.
            "day_letter": cur_date.strftime("%a")[:2], # Mo, Tu, etc.
            "is_weekend": is_weekend,
            "is_today": (date_str == today_str)
        })
        
    # 2. Get active tasks
    cursor.execute("SELECT * FROM tasks WHERE is_archived = 0 ORDER BY sort_order ASC, id ASC")
    tasks = [dict(r) for r in cursor.fetchall()]
    
    # 3. Get all completions for this month
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{num_days:02d}"
    cursor.execute("""
    SELECT task_id, date, completed 
    FROM completions 
    WHERE date >= ? AND date <= ? AND completed = 1
    """, (start_date, end_date))
    
    completed_map = set() # (task_id, date_str)
    for r in cursor.fetchall():
        completed_map.add((r["task_id"], r["date"]))
        
    # 4. Get daily summaries (e.g. daily goal)
    cursor.execute("""
    SELECT date, daily_goal_achieved, focus_note 
    FROM daily_summaries 
    WHERE date >= ? AND date <= ?
    """, (start_date, end_date))
    daily_summaries = {r["date"]: dict(r) for r in cursor.fetchall()}
    
    conn.close()
    
    # 5. Build grid matrix
    task_rows = []
    daily_counts = [0] * num_days
    
    for task in tasks:
        task_id = task["id"]
        cells = []
        task_total_completed = 0
        
        for idx, d_str in enumerate(day_date_strs):
            is_done = (task_id, d_str) in completed_map
            cells.append(is_done)
            if is_done:
                task_total_completed += 1
                daily_counts[idx] += 1
                
        completion_pct = round((task_total_completed / num_days) * 100, 1) if num_days > 0 else 0
        task_rows.append({
            "task": task,
            "cells": cells,
            "total_completed": task_total_completed,
            "completion_percentage": completion_pct
        })
        
    # 6. Build daily progress stats
    total_active_tasks = len(tasks)
    daily_stats = []
    for idx, d_str in enumerate(day_date_strs):
        done = daily_counts[idx]
        pct = round((done / total_active_tasks) * 100, 1) if total_active_tasks > 0 else 0
        summary = daily_summaries.get(d_str, {"daily_goal_achieved": 0, "focus_note": ""})
        daily_stats.append({
            "day": idx + 1,
            "date": d_str,
            "completed_count": done,
            "total_tasks": total_active_tasks,
            "percentage": pct,
            "daily_goal_achieved": bool(summary.get("daily_goal_achieved", 0)),
            "focus_note": summary.get("focus_note", "")
        })
        
    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "days": days_info,
        "tasks": tasks,
        "matrix": task_rows,
        "daily_stats": daily_stats,
        "total_tasks": total_active_tasks,
        "num_days": num_days
    }

# ----------------- Heatmap & Streaks ----------------- #

def get_heatmap(year: int, task_id: int = None):
    """
    Returns full year (365/366 days) contribution heatmap data:
    Every day mapped to count, percentage, and intensity level (0 to 4).
    Also returns streak statistics.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total tasks active
    if task_id:
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        filter_task = dict(task_row) if task_row else None
        total_tasks_target = 1
    else:
        filter_task = None
        cursor.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE is_archived = 0")
        total_tasks_target = cursor.fetchone()["cnt"] or 1
        
    # 2. Query completions for the entire year
    start_date = f"{year:04d}-01-01"
    end_date = f"{year:04d}-12-31"
    
    if task_id:
        cursor.execute("""
        SELECT date, COUNT(*) AS count
        FROM completions
        WHERE date >= ? AND date <= ? AND task_id = ? AND completed = 1
        GROUP BY date
        """, (start_date, end_date, task_id))
    else:
        cursor.execute("""
        SELECT c.date, COUNT(*) AS count
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.date >= ? AND c.date <= ? AND c.completed = 1 AND t.is_archived = 0
        GROUP BY c.date
        """, (start_date, end_date))
        
    day_counts = {r["date"]: r["count"] for r in cursor.fetchall()}
    
    # 3. Fetch detailed task names for tooltips
    if task_id:
        cursor.execute("""
        SELECT date, t.title
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE date >= ? AND date <= ? AND task_id = ? AND completed = 1
        """, (start_date, end_date, task_id))
    else:
        cursor.execute("""
        SELECT c.date, t.title
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.date >= ? AND c.date <= ? AND c.completed = 1 AND t.is_archived = 0
        """, (start_date, end_date))
        
    tasks_per_day = {}
    for r in cursor.fetchall():
        tasks_per_day.setdefault(r["date"], []).append(r["title"])
        
    conn.close()
    
    # 4. Generate all calendar days of the year
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    cur = start
    today = date.today()
    today_str = today.isoformat()
    
    heatmap_days = []
    total_active_days = 0
    total_completed_actions = 0
    
    all_dates = []
    while cur <= end:
        d_str = cur.isoformat()
        all_dates.append((cur, d_str))
        cnt = day_counts.get(d_str, 0)
        total_completed_actions += cnt
        
        if cnt > 0:
            total_active_days += 1
            
        pct = round((cnt / total_tasks_target) * 100, 1) if total_tasks_target > 0 else 0
        
        # Intensity level: 0..4 (GitHub standard)
        if cnt == 0:
            level = 0
        elif task_id:
            level = 4 if cnt >= 1 else 0
        else:
            if pct <= 25:
                level = 1
            elif pct <= 50:
                level = 2
            elif pct <= 75:
                level = 3
            else:
                level = 4
                
        heatmap_days.append({
            "date": d_str,
            "day": cur.day,
            "month": cur.month,
            "day_of_week": cur.weekday(), # 0=Mon, 6=Sun
            "count": cnt,
            "total_tasks": total_tasks_target,
            "percentage": pct,
            "level": level,
            "completed_tasks": tasks_per_day.get(d_str, []),
            "is_today": (d_str == today_str),
            "is_future": (cur > today)
        })
        cur += timedelta(days=1)
        
    # 5. Compute Streak (Current & Longest)
    longest_streak = 0
    cur_streak_run = 0
    
    for day_obj, d_str in all_dates:
        if day_obj > today:
            break
        cnt = day_counts.get(d_str, 0)
        if cnt > 0:
            cur_streak_run += 1
            if cur_streak_run > longest_streak:
                longest_streak = cur_streak_run
        else:
            cur_streak_run = 0
            
    # Current active streak (checks today and yesterday)
    current_streak = 0
    check_date = today
    if day_counts.get(check_date.isoformat(), 0) == 0:
        check_date = today - timedelta(days=1)
        
    while check_date >= start:
        if day_counts.get(check_date.isoformat(), 0) > 0:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break
            
    return {
        "year": year,
        "filter_task": filter_task,
        "days": heatmap_days,
        "total_active_days": total_active_days,
        "total_completed_actions": total_completed_actions,
        "current_streak": current_streak,
        "longest_streak": longest_streak
    }

# ----------------- Year Overview & Statistics ----------------- #

def get_yearly_stats(year: int):
    """
    Returns high-level statistics for each month of the specified year.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Active tasks count
    cursor.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE is_archived = 0")
    total_active_tasks = cursor.fetchone()["cnt"] or 1
    
    monthly_data = []
    total_year_completions = 0
    best_month = None
    best_month_rate = -1
    
    for m in range(1, 13):
        num_days = calendar.monthrange(year, m)[1]
        start_date = f"{year:04d}-{m:02d}-01"
        end_date = f"{year:04d}-{m:02d}-{num_days:02d}"
        
        cursor.execute("""
        SELECT COUNT(*) AS cnt 
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.date >= ? AND c.date <= ? AND c.completed = 1 AND t.is_archived = 0
        """, (start_date, end_date))
        cnt = cursor.fetchone()["cnt"]
        total_year_completions += cnt
        
        max_possible = num_days * total_active_tasks
        rate = round((cnt / max_possible) * 100, 1) if max_possible > 0 else 0
        
        if rate > best_month_rate:
            best_month_rate = rate
            best_month = calendar.month_name[m]
            
        monthly_data.append({
            "month": m,
            "month_name": calendar.month_name[m],
            "days": num_days,
            "completions": cnt,
            "max_possible": max_possible,
            "completion_rate": rate
        })
        
    conn.close()
    
    return {
        "year": year,
        "total_completions": total_year_completions,
        "best_month": best_month,
        "best_month_rate": best_month_rate if best_month_rate >= 0 else 0,
        "months": monthly_data
    }

# ----------------- Export & Backup ----------------- #

def export_all():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks")
    tasks = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM completions")
    completions = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM daily_summaries")
    summaries = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "tasks": tasks,
        "completions": completions,
        "daily_summaries": summaries
    }

def import_backup(data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    if "tasks" in data_dict:
        for t in data_dict["tasks"]:
            cursor.execute("""
            INSERT OR REPLACE INTO tasks (id, title, category, color, icon, target_frequency, sort_order, is_archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (t.get("id"), t.get("title"), t.get("category", "General"), t.get("color", "#3b82f6"),
                  t.get("icon", "check-circle"), t.get("target_frequency", "daily"),
                  t.get("sort_order", 0), t.get("is_archived", 0)))
                  
    if "completions" in data_dict:
        for c in data_dict["completions"]:
            cursor.execute("""
            INSERT OR REPLACE INTO completions (id, task_id, date, completed, notes)
            VALUES (?, ?, ?, ?, ?)
            """, (c.get("id"), c["task_id"], c["date"], c.get("completed", 1), c.get("notes", "")))
            
    if "daily_summaries" in data_dict:
        for s in data_dict["daily_summaries"]:
            cursor.execute("""
            INSERT OR REPLACE INTO daily_summaries (date, daily_goal_achieved, focus_note)
            VALUES (?, ?, ?)
            """, (s["date"], s.get("daily_goal_achieved", 0), s.get("focus_note", "")))
            
    conn.commit()
    conn.close()
    return True
