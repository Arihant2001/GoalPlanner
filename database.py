import sqlite3
import os
import calendar
from datetime import datetime, date, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "goalplanner.db")

# Default preset categories
DEFAULT_CATEGORIES = [
    {"name": "Mind", "color": "#eab308"},
    {"name": "Power", "color": "#a855f7"},
    {"name": "Reality", "color": "#ef4444"},
    {"name": "Soul", "color": "#f97316"},
    {"name": "Space", "color": "#3b82f6"},
    {"name": "Time", "color": "#22c55e"}
]

DEFAULT_TASKS = [
    {"title": "Goal", "category": "Mind", "color": "#eab308", "icon": "flag", "sort_order": 0},
    {"title": "Full Day", "category": "Mind", "color": "#f59e0b", "icon": "sun", "sort_order": 1},
    {"title": "Office", "category": "Space", "color": "#3b82f6", "icon": "briefcase", "sort_order": 2},
    {"title": "DSA", "category": "Time", "color": "#22c55e", "icon": "code-2", "sort_order": 3},
    {"title": "System Design", "category": "Power", "color": "#a855f7", "icon": "network", "sort_order": 4},
    {"title": "Development", "category": "Space", "color": "#3b82f6", "icon": "laptop", "sort_order": 5},
    {"title": "Content", "category": "Soul", "color": "#f97316", "icon": "video", "sort_order": 6},
    {"title": "Expenses", "category": "Mind", "color": "#eab308", "icon": "wallet", "sort_order": 7},
    {"title": "Exercise", "category": "Reality", "color": "#ef4444", "icon": "dumbbell", "sort_order": 8},
    {"title": "Cleaning", "category": "Time", "color": "#22c55e", "icon": "sparkles", "sort_order": 9},
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
    
    # Categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        color TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Seed default categories if empty
    cursor.execute("SELECT COUNT(*) AS cnt FROM categories")
    if cursor.fetchone()["cnt"] == 0:
        for idx, cat in enumerate(DEFAULT_CATEGORIES):
            cursor.execute("""
            INSERT OR IGNORE INTO categories (name, color, sort_order)
            VALUES (?, ?, ?)
            """, (cat["name"], cat["color"], idx))
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'Mind',
        color TEXT DEFAULT '#eab308',
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
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('goal_threshold', '3')")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_summaries (
        date TEXT PRIMARY KEY,
        daily_goal_achieved INTEGER DEFAULT 0,
        focus_note TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 1. Ensure 'Goal' task exists at sort_order 0
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'goal'")
    goal_row = cursor.fetchone()
    if not goal_row:
        cursor.execute("""
        INSERT INTO tasks (title, category, color, icon, target_frequency, sort_order)
        VALUES ('Goal', 'Mind', '#eab308', 'flag', 'daily', 0)
        """)
        
    # 2. Ensure 'Full Day' task exists at sort_order 1
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'full day'")
    full_day_row = cursor.fetchone()
    if not full_day_row:
        cursor.execute("""
        INSERT INTO tasks (title, category, color, icon, target_frequency, sort_order)
        VALUES ('Full Day', 'Mind', '#f59e0b', 'sun', 'daily', 1)
        """)
    else:
        # ensure unarchived
        cursor.execute("UPDATE tasks SET is_archived = 0, sort_order = 1 WHERE id = ?", (full_day_row["id"],))
        
    # Check if other default tasks need seeding
    cursor.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE is_archived = 0")
    count = cursor.fetchone()["cnt"]
    if count <= 2:
        for t in DEFAULT_TASKS:
            if t["title"].lower() in ("goal", "full day"):
                continue
            cursor.execute("""
            INSERT INTO tasks (title, category, color, icon, target_frequency, sort_order)
            VALUES (?, ?, ?, ?, 'daily', ?)
            """, (t["title"], t["category"], t["color"], t["icon"], t["sort_order"]))
    
    conn.commit()
    conn.close()

# ----------------- Categories CRUD ----------------- #

def get_all_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY sort_order ASC, id ASC")
    cats = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return cats

def get_category_color_map():
    cats = get_all_categories()
    return {c["name"]: c["color"] for c in cats}

def add_category(name, color):
    name = name.strip()
    color = color.strip()
    if not name:
        raise ValueError("Category name cannot be empty.")
    if not color:
        color = "#3b82f6"
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM categories WHERE LOWER(TRIM(name)) = LOWER(?)", (name,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Category '{name}' already exists.")
        
    cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM categories")
    next_order = cursor.fetchone()["next_order"]
    
    cursor.execute("""
    INSERT INTO categories (name, color, sort_order)
    VALUES (?, ?, ?)
    """, (name, color, next_order))
    cat_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    cat = dict(cursor.fetchone())
    conn.close()
    return cat

def update_category(cat_id, name=None, color=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise ValueError("Category not found.")
        
    old_name = existing["name"]
    new_name = name.strip() if name is not None else old_name
    new_color = color.strip() if color is not None else existing["color"]
    
    if not new_name:
        conn.close()
        raise ValueError("Category name cannot be empty.")
        
    cursor.execute("SELECT id FROM categories WHERE LOWER(TRIM(name)) = LOWER(?) AND id != ?", (new_name, cat_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Category name '{new_name}' is already used.")
        
    cursor.execute("UPDATE categories SET name = ?, color = ? WHERE id = ?", (new_name, new_color, cat_id))
    
    cursor.execute("""
    UPDATE tasks 
    SET category = ?, color = ? 
    WHERE category = ?
    """, (new_name, new_color, old_name))
    
    conn.commit()
    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
    updated = dict(cursor.fetchone())
    conn.close()
    return updated

def delete_category(cat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    cat = cursor.fetchone()
    if not cat:
        conn.close()
        raise ValueError("Category not found.")
        
    cursor.execute("SELECT COUNT(*) AS cnt FROM categories")
    if cursor.fetchone()["cnt"] <= 1:
        conn.close()
        raise ValueError("Cannot delete the only remaining category.")
        
    cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return True

# ----------------- Settings API ----------------- #

def get_setting(key, default="3"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value, updated_at)
    VALUES (?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, str(value)))
    conn.commit()
    conn.close()
    
    if key == "goal_threshold":
        recalculate_all_goals(int(value))
    return value

def get_goal_threshold():
    try:
        return int(get_setting("goal_threshold", "3"))
    except ValueError:
        return 3

# ----------------- Auto Goal Logic ----------------- #

def get_special_task_ids(cursor):
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'goal' AND is_archived = 0 LIMIT 1")
    goal_row = cursor.fetchone()
    goal_id = goal_row["id"] if goal_row else None
    
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'full day' AND is_archived = 0 LIMIT 1")
    full_day_row = cursor.fetchone()
    full_day_id = full_day_row["id"] if full_day_row else None
    
    return goal_id, full_day_id

def evaluate_goal_for_date(date_str, conn=None):
    """
    Evaluates whether 'Goal' should be ticked on a specific date:
    - Normal rule: Completed count of regular tasks (excluding Goal and Full Day) >= threshold
    - Full Day rule: If 'Full Day' is checked AND at least 1 regular task is checked on that date,
      then Goal is considered achieved!
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
        
    cursor = conn.cursor()
    threshold = get_goal_threshold()
    
    goal_id, full_day_id = get_special_task_ids(cursor)
    if not goal_id:
        if should_close:
            conn.close()
        return False
        
    # Check if 'Full Day' is checked on this date
    full_day_checked = False
    if full_day_id:
        cursor.execute("SELECT completed FROM completions WHERE task_id = ? AND date = ?", (full_day_id, date_str))
        f_row = cursor.fetchone()
        full_day_checked = bool(f_row and f_row["completed"] == 1)
        
    # Count completed regular tasks (excluding Goal and Full Day)
    excluded_ids = [goal_id]
    if full_day_id:
        excluded_ids.append(full_day_id)
        
    placeholders = ",".join("?" for _ in excluded_ids)
    cursor.execute(f"""
    SELECT COUNT(*) AS cnt
    FROM completions c
    JOIN tasks t ON c.task_id = t.id
    WHERE c.date = ? 
      AND c.completed = 1 
      AND t.is_archived = 0
      AND t.id NOT IN ({placeholders})
    """, [date_str] + excluded_ids)
    
    regular_completed = cursor.fetchone()["cnt"]
    
    # Goal condition:
    # 1. regular_completed >= threshold, OR
    # 2. full_day_checked is True and regular_completed >= 1
    if regular_completed >= threshold or (full_day_checked and regular_completed >= 1):
        goal_state = 1
    else:
        goal_state = 0
        
    cursor.execute("""
    INSERT INTO completions (task_id, date, completed, updated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(task_id, date) DO UPDATE SET completed = excluded.completed, updated_at = CURRENT_TIMESTAMP
    """, (goal_id, date_str, goal_state))
    
    cursor.execute("""
    INSERT INTO daily_summaries (date, daily_goal_achieved, updated_at)
    VALUES (?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(date) DO UPDATE SET daily_goal_achieved = excluded.daily_goal_achieved, updated_at = CURRENT_TIMESTAMP
    """, (date_str, goal_state))
    
    conn.commit()
    if should_close:
        conn.close()
    return bool(goal_state)

def recalculate_all_goals(threshold: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    goal_id, full_day_id = get_special_task_ids(cursor)
    if not goal_id:
        conn.close()
        return
        
    excluded_ids = [goal_id]
    if full_day_id:
        excluded_ids.append(full_day_id)
    placeholders = ",".join("?" for _ in excluded_ids)
    
    # Dates with regular completions
    cursor.execute(f"""
    SELECT c.date, COUNT(*) as cnt
    FROM completions c
    JOIN tasks t ON c.task_id = t.id
    WHERE c.completed = 1 AND t.is_archived = 0 AND t.id NOT IN ({placeholders})
    GROUP BY c.date
    """, excluded_ids)
    date_counts = {r["date"]: r["cnt"] for r in cursor.fetchall()}
    
    # Dates with Full Day checked
    full_day_dates = set()
    if full_day_id:
        cursor.execute("SELECT date FROM completions WHERE task_id = ? AND completed = 1", (full_day_id,))
        full_day_dates = {r["date"] for r in cursor.fetchall()}
        
    # Existing Goal dates
    cursor.execute("SELECT date FROM completions WHERE task_id = ? AND completed = 1", (goal_id,))
    existing_goal_dates = {r["date"] for r in cursor.fetchall()}
    
    all_dates = set(date_counts.keys()).union(full_day_dates).union(existing_goal_dates)
    for d_str in all_dates:
        cnt = date_counts.get(d_str, 0)
        fd = d_str in full_day_dates
        new_state = 1 if (cnt >= threshold or (fd and cnt >= 1)) else 0
        
        cursor.execute("""
        INSERT INTO completions (task_id, date, completed, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(task_id, date) DO UPDATE SET completed = excluded.completed, updated_at = CURRENT_TIMESTAMP
        """, (goal_id, d_str, new_state))
        cursor.execute("""
        INSERT INTO daily_summaries (date, daily_goal_achieved, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(date) DO UPDATE SET daily_goal_achieved = excluded.daily_goal_achieved, updated_at = CURRENT_TIMESTAMP
        """, (d_str, new_state))
        
    conn.commit()
    conn.close()

# ----------------- Tasks CRUD ----------------- #

def get_all_tasks(include_archived=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_archived:
        cursor.execute("""
        SELECT * FROM tasks 
        ORDER BY 
            CASE WHEN LOWER(TRIM(title)) = 'goal' THEN 0 
                 WHEN LOWER(TRIM(title)) = 'full day' THEN 1 
                 ELSE 2 END,
            sort_order ASC, id ASC
        """)
    else:
        cursor.execute("""
        SELECT * FROM tasks 
        WHERE is_archived = 0 
        ORDER BY 
            CASE WHEN LOWER(TRIM(title)) = 'goal' THEN 0 
                 WHEN LOWER(TRIM(title)) = 'full day' THEN 1 
                 ELSE 2 END,
            sort_order ASC, id ASC
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_task(title, category="General"):
    category = category.strip()
    color_map = get_category_color_map()
    color = color_map.get(category, "#3b82f6")
    
    clean_title = title.strip().lower()
    if clean_title in ("goal", "full day"):
        raise ValueError(f"Cannot create task named '{title}'. It is a reserved system task.")
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(sort_order), 1) + 1 AS next_order FROM tasks")
    next_order = cursor.fetchone()["next_order"]
    
    cursor.execute("""
    INSERT INTO tasks (title, category, color, icon, target_frequency, sort_order)
    VALUES (?, ?, ?, 'check-circle', 'daily', ?)
    """, (title.strip(), category, color, next_order))
    task_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()
    return task

def update_task(task_id, title=None, category=None, is_archived=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return None
        
    clean_title = existing["title"].strip().lower()
    is_protected = clean_title in ("goal", "full day")
    
    if is_protected and is_archived:
        conn.close()
        raise ValueError(f"The '{existing['title']}' task cannot be deleted or archived.")
        
    fields = []
    values = []
    if title is not None:
        if is_protected and title.strip().lower() != clean_title:
            conn.close()
            raise ValueError(f"Cannot rename the reserved '{existing['title']}' task.")
        fields.append("title = ?")
        values.append(title.strip())
        
    if category is not None:
        cat = category.strip()
        color_map = get_category_color_map()
        color = color_map.get(cat, "#3b82f6")
        fields.append("category = ?")
        values.append(cat)
        fields.append("color = ?")
        values.append(color)
            
    if is_archived is not None and not is_protected:
        fields.append("is_archived = ?")
        values.append(1 if is_archived else 0)
        
    if not fields:
        conn.close()
        return dict(existing)
        
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
    cursor.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row and row["title"].strip().lower() in ("goal", "full day"):
        conn.close()
        raise ValueError(f"The '{row['title']}' task cannot be deleted.")
        
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
    # Goal is always 0, Full Day is always 1
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'goal' AND is_archived = 0 LIMIT 1")
    goal_row = cursor.fetchone()
    goal_id = goal_row["id"] if goal_row else None
    
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'full day' AND is_archived = 0 LIMIT 1")
    full_day_row = cursor.fetchone()
    full_day_id = full_day_row["id"] if full_day_row else None

    if goal_id:
        cursor.execute("UPDATE tasks SET sort_order = 0 WHERE id = ?", (goal_id,))
    if full_day_id:
        cursor.execute("UPDATE tasks SET sort_order = 1 WHERE id = ?", (full_day_id,))

    # Custom regular task order starts at 2
    order_idx = 2
    for t_id in task_ids:
        if t_id not in (goal_id, full_day_id):
            cursor.execute("UPDATE tasks SET sort_order = ? WHERE id = ?", (order_idx, t_id))
            order_idx += 1
            
    conn.commit()
    conn.close()
    return True

# ----------------- Completions & Matrix ----------------- #

def toggle_completion(task_id, date_str, target_state=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title FROM tasks WHERE id = ?", (task_id,))
    task_row = cursor.fetchone()
    if not task_row:
        conn.close()
        raise ValueError("Task not found")
        
    if task_row["title"].strip().lower() == "goal":
        conn.close()
        raise ValueError("The 'Goal' main task is automated and cannot be manually toggled.")
        
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
    goal_completed = evaluate_goal_for_date(date_str, conn=conn)
    conn.close()
    
    return {
        "task_id": task_id,
        "date": date_str,
        "completed": bool(new_state),
        "goal_auto_completed": goal_completed
    }

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
    conn = get_connection()
    cursor = conn.cursor()
    
    num_days = calendar.monthrange(year, month)[1]
    today_str = date.today().isoformat()
    
    days_info = []
    day_date_strs = []
    for day in range(1, num_days + 1):
        cur_date = date(year, month, day)
        date_str = cur_date.isoformat()
        day_date_strs.append(date_str)
        is_weekend = cur_date.weekday() in (5, 6)
        days_info.append({
            "day": day,
            "date": date_str,
            "day_of_week": cur_date.strftime("%a"),
            "day_letter": cur_date.strftime("%a")[:2],
            "is_weekend": is_weekend,
            "is_today": (date_str == today_str)
        })
        
    # Ensure Goal is 0, Full Day is 1, followed by others
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE is_archived = 0 
    ORDER BY 
        CASE WHEN LOWER(TRIM(title)) = 'goal' THEN 0 
             WHEN LOWER(TRIM(title)) = 'full day' THEN 1 
             ELSE 2 END, 
        sort_order ASC, id ASC
    """)
    tasks = [dict(r) for r in cursor.fetchall()]
    
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{num_days:02d}"
    cursor.execute("""
    SELECT task_id, date, completed 
    FROM completions 
    WHERE date >= ? AND date <= ? AND completed = 1
    """, (start_date, end_date))
    
    completed_map = set()
    for r in cursor.fetchall():
        completed_map.add((r["task_id"], r["date"]))
        
    cursor.execute("""
    SELECT date, daily_goal_achieved, focus_note 
    FROM daily_summaries 
    WHERE date >= ? AND date <= ?
    """, (start_date, end_date))
    daily_summaries = {r["date"]: dict(r) for r in cursor.fetchall()}
    
    threshold = get_goal_threshold()
    conn.close()
    
    task_rows = []
    for task in tasks:
        task_id = task["id"]
        cells = []
        task_total_completed = 0
        t_clean = task["title"].strip().lower()
        is_goal = t_clean == "goal"
        is_full_day = t_clean == "full day"
        
        for idx, d_str in enumerate(day_date_strs):
            is_done = (task_id, d_str) in completed_map
            cells.append(is_done)
            if is_done:
                task_total_completed += 1
                
        task_rows.append({
            "task": task,
            "is_goal": is_goal,
            "is_full_day": is_full_day,
            "cells": cells,
            "total_completed": task_total_completed
        })
        
    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "days": days_info,
        "tasks": tasks,
        "matrix": task_rows,
        "total_tasks": len(tasks),
        "num_days": num_days,
        "goal_threshold": threshold
    }

# ----------------- Heatmap & Streaks ----------------- #

def get_heatmap(year: int, task_id: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM tasks WHERE LOWER(TRIM(title)) = 'goal' AND is_archived = 0 LIMIT 1")
    goal_row = cursor.fetchone()
    goal_id = goal_row["id"] if goal_row else None
    
    if task_id:
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        filter_task = dict(task_row) if task_row else None
        total_tasks_target = 1
    else:
        filter_task = None
        # Heatmap counts regular tasks (excludes Goal and Full Day)
        cursor.execute("""
        SELECT COUNT(*) AS cnt FROM tasks 
        WHERE is_archived = 0 AND LOWER(TRIM(title)) NOT IN ('goal', 'full day')
        """)
        total_tasks_target = cursor.fetchone()["cnt"] or 1
        
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
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
        GROUP BY c.date
        """, (start_date, end_date))
        
    day_counts = {r["date"]: r["count"] for r in cursor.fetchall()}
    
    # Also fetch all dates where Goal was achieved (for Goal-based Streak calculation)
    goal_dates = set()
    if goal_id:
        cursor.execute("""
        SELECT date FROM completions 
        WHERE date >= ? AND date <= ? AND task_id = ? AND completed = 1
        """, (start_date, end_date, goal_id))
        goal_dates = {r["date"] for r in cursor.fetchall()}
        
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
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
        """, (start_date, end_date))
        
    tasks_per_day = {}
    for r in cursor.fetchall():
        tasks_per_day.setdefault(r["date"], []).append(r["title"])
        
    conn.close()
    
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
            "day_of_week": cur.weekday(),
            "count": cnt,
            "total_tasks": total_tasks_target,
            "percentage": pct,
            "level": level,
            "completed_tasks": tasks_per_day.get(d_str, []),
            "is_today": (d_str == today_str),
            "is_future": (cur > today)
        })
        cur += timedelta(days=1)
        
    # --- Streak Calculation based on GOAL continuity ---
    longest_streak = 0
    cur_streak_run = 0
    
    for day_obj, d_str in all_dates:
        if day_obj > today:
            break
        # Goal must be achieved on this day
        if d_str in goal_dates:
            cur_streak_run += 1
            if cur_streak_run > longest_streak:
                longest_streak = cur_streak_run
        else:
            cur_streak_run = 0
            
    current_streak = 0
    check_date = today
    # If Goal is not achieved today yet, allow continuation from yesterday
    if today_str not in goal_dates:
        check_date = today - timedelta(days=1)
        
    while check_date >= start:
        if check_date.isoformat() in goal_dates:
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
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT COUNT(*) AS cnt FROM tasks 
    WHERE is_archived = 0 AND LOWER(TRIM(title)) NOT IN ('goal', 'full day')
    """)
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
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
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
    
    cursor.execute("SELECT * FROM categories")
    categories = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM tasks")
    tasks = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM completions")
    completions = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM settings")
    settings = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM daily_summaries")
    summaries = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "exported_at": datetime.now().isoformat(),
        "version": "3.1",
        "categories": categories,
        "tasks": tasks,
        "completions": completions,
        "settings": settings,
        "daily_summaries": summaries
    }

def import_backup(data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    if "categories" in data_dict:
        for c in data_dict["categories"]:
            cursor.execute("""
            INSERT OR REPLACE INTO categories (id, name, color, sort_order)
            VALUES (?, ?, ?, ?)
            """, (c.get("id"), c["name"], c.get("color", "#3b82f6"), c.get("sort_order", 0)))
            
    color_map = {c["name"]: c["color"] for c in data_dict.get("categories", [])}
    
    if "tasks" in data_dict:
        for t in data_dict["tasks"]:
            cat = t.get("category", "General")
            col = color_map.get(cat, t.get("color", "#3b82f6"))
            cursor.execute("""
            INSERT OR REPLACE INTO tasks (id, title, category, color, icon, target_frequency, sort_order, is_archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (t.get("id"), t.get("title"), cat, col,
                  t.get("icon", "check-circle"), t.get("target_frequency", "daily"),
                  t.get("sort_order", 0), t.get("is_archived", 0)))
                  
    if "completions" in data_dict:
        for c in data_dict["completions"]:
            cursor.execute("""
            INSERT OR REPLACE INTO completions (id, task_id, date, completed, notes)
            VALUES (?, ?, ?, ?, ?)
            """, (c.get("id"), c["task_id"], c["date"], c.get("completed", 1), c.get("notes", "")))
            
    if "settings" in data_dict:
        for s in data_dict["settings"]:
            cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
            """, (s["key"], s["value"]))
            
    if "daily_summaries" in data_dict:
        for s in data_dict["daily_summaries"]:
            cursor.execute("""
            INSERT OR REPLACE INTO daily_summaries (date, daily_goal_achieved, focus_note)
            VALUES (?, ?, ?)
            """, (s["date"], s.get("daily_goal_achieved", 0), s.get("focus_note", "")))
            
    conn.commit()
    conn.close()
    
    threshold = get_goal_threshold()
    recalculate_all_goals(threshold)
    return True
