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

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT NULL,
        name TEXT NOT NULL,
        color TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT NULL,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'Mind',
        color TEXT DEFAULT '#eab308',
        icon TEXT DEFAULT 'check-circle',
        target_frequency TEXT DEFAULT 'daily',
        sort_order INTEGER DEFAULT 0,
        is_archived INTEGER DEFAULT 0,
        parent_id INTEGER DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # 4. Completions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT NULL,
        task_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 1,
        notes TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(task_id, date)
    )
    """)
    
    # 5. Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # 6. Daily summaries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT NULL,
        date TEXT NOT NULL,
        daily_goal_achieved INTEGER DEFAULT 0,
        focus_note TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    # Migrations: Ensure user_id exists on all tables
    for tbl in ("categories", "tasks", "completions", "settings", "daily_summaries"):
        cursor.execute(f"PRAGMA table_info({tbl})")
        cols = [r["name"] for r in cursor.fetchall()]
        if "user_id" not in cols:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN user_id INTEGER DEFAULT NULL REFERENCES users(id) ON DELETE CASCADE")
            
    cursor.execute("PRAGMA table_info(tasks)")
    t_cols = [r["name"] for r in cursor.fetchall()]
    if "parent_id" not in t_cols:
        cursor.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER DEFAULT NULL REFERENCES tasks(id) ON DELETE CASCADE")

    # Multi-tenant constraint migration: ensure categories has UNIQUE(user_id, name)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'")
    cat_sql = cursor.fetchone()["sql"]
    if "UNIQUE(user_id, name)" not in cat_sql and "UNIQUE (user_id, name)" not in cat_sql:
        cursor.execute("""
        CREATE TABLE categories_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, name)
        )
        """)
        cursor.execute("INSERT OR IGNORE INTO categories_v2 (id, user_id, name, color, sort_order, created_at) SELECT id, user_id, name, color, sort_order, created_at FROM categories")
        cursor.execute("DROP TABLE categories")
        cursor.execute("ALTER TABLE categories_v2 RENAME TO categories")

    # Multi-tenant constraint migration: ensure settings has UNIQUE(user_id, key)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='settings'")
    set_sql = cursor.fetchone()["sql"]
    if "UNIQUE(user_id, key)" not in set_sql and "UNIQUE (user_id, key)" not in set_sql:
        cursor.execute("""
        CREATE TABLE settings_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, key)
        )
        """)
        cursor.execute("INSERT OR IGNORE INTO settings_v2 (user_id, key, value, updated_at) SELECT user_id, key, value, updated_at FROM settings")
        cursor.execute("DROP TABLE settings")
        cursor.execute("ALTER TABLE settings_v2 RENAME TO settings")

    # Multi-tenant constraint migration: ensure daily_summaries has UNIQUE(user_id, date)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_summaries'")
    ds_sql = cursor.fetchone()["sql"]
    if "UNIQUE(user_id, date)" not in ds_sql and "UNIQUE (user_id, date)" not in ds_sql:
        cursor.execute("""
        CREATE TABLE daily_summaries_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT NULL,
            date TEXT NOT NULL,
            daily_goal_achieved INTEGER DEFAULT 0,
            focus_note TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, date)
        )
        """)
        cursor.execute("INSERT OR IGNORE INTO daily_summaries_v2 (user_id, date, daily_goal_achieved, focus_note, updated_at) SELECT user_id, date, daily_goal_achieved, focus_note, updated_at FROM daily_summaries")
        cursor.execute("DROP TABLE daily_summaries")
        cursor.execute("ALTER TABLE daily_summaries_v2 RENAME TO daily_summaries")
        
    # Create indexes for fast sub-millisecond lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_completions_user_date ON completions(user_id, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_completions_task_date ON completions(task_id, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_user_key ON settings(user_id, key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_summaries_user_date ON daily_summaries(user_id, date)")

    # Ensure Goal task icon is set to 'target'
    cursor.execute("UPDATE tasks SET icon = 'target' WHERE LOWER(TRIM(title)) = 'goal'")
    
    conn.commit()
    conn.close()

# ----------------- User Management & Authentication ----------------- #

def create_user(username, password_hash):
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Username '{username}' is already taken. Please choose another.")
        
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
    user_id = cursor.lastrowid
    conn.commit()
    
    # If this is the very first registered user, claim any legacy data from single-user mode
    cursor.execute("SELECT COUNT(*) AS cnt FROM users")
    if cursor.fetchone()["cnt"] == 1:
        cursor.execute("UPDATE tasks SET user_id = ? WHERE user_id IS NULL", (user_id,))
        cursor.execute("UPDATE completions SET user_id = ? WHERE user_id IS NULL", (user_id,))
        cursor.execute("UPDATE categories SET user_id = ? WHERE user_id IS NULL", (user_id,))
        cursor.execute("UPDATE settings SET user_id = ? WHERE user_id IS NULL", (user_id,))
        cursor.execute("UPDATE daily_summaries SET user_id = ? WHERE user_id IS NULL", (user_id,))
        conn.commit()
        
    # Ensure this user has their initial Goal & Full Day tasks, categories, and settings
    seed_user_defaults(user_id, conn=conn)
    
    cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def seed_user_defaults(user_id, conn=None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    cursor = conn.cursor()
    
    # 1. Preset Categories for this user
    cursor.execute("SELECT COUNT(*) AS cnt FROM categories WHERE user_id = ?", (user_id,))
    if cursor.fetchone()["cnt"] == 0:
        for idx, cat in enumerate(DEFAULT_CATEGORIES):
            cursor.execute("""
            INSERT INTO categories (user_id, name, color, sort_order)
            VALUES (?, ?, ?, ?)
            """, (user_id, cat["name"], cat["color"], idx))
            
    # 2. Goal task (Row 0)
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'goal'", (user_id,))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO tasks (user_id, title, category, color, icon, target_frequency, sort_order)
        VALUES (?, 'Goal', 'Mind', '#eab308', 'target', 'daily', 0)
        """, (user_id,))
        
    # 3. Full Day task (Row 1)
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'full day'", (user_id,))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO tasks (user_id, title, category, color, icon, target_frequency, sort_order)
        VALUES (?, 'Full Day', 'Mind', '#f59e0b', 'sun', 'daily', 1)
        """, (user_id,))
        
    # 4. Default Goal Threshold Setting = 3
    cursor.execute("SELECT value FROM settings WHERE user_id = ? AND key = 'goal_threshold'", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (user_id, key, value) VALUES (?, 'goal_threshold', '3')", (user_id,))
        
    conn.commit()
    if should_close:
        conn.close()

# ----------------- Categories CRUD ----------------- #

def get_all_categories(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY sort_order ASC, id ASC", (user_id,))
    cats = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return cats

def get_category_color_map(user_id):
    cats = get_all_categories(user_id)
    return {c["name"]: c["color"] for c in cats}

def add_category(user_id, name, color):
    name = name.strip()
    color = color.strip()
    if not name:
        raise ValueError("Category name cannot be empty.")
    if not color:
        color = "#3b82f6"
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM categories WHERE user_id = ? AND LOWER(TRIM(name)) = LOWER(?)", (user_id, name))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Category '{name}' already exists.")
        
    cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM categories WHERE user_id = ?", (user_id,))
    next_order = cursor.fetchone()["next_order"]
    
    cursor.execute("""
    INSERT INTO categories (user_id, name, color, sort_order)
    VALUES (?, ?, ?, ?)
    """, (user_id, name, color, next_order))
    cat_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    cat = dict(cursor.fetchone())
    conn.close()
    return cat

def update_category(user_id, cat_id, name=None, color=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
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
        
    cursor.execute("SELECT id FROM categories WHERE user_id = ? AND LOWER(TRIM(name)) = LOWER(?) AND id != ?", (user_id, new_name, cat_id))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Category name '{new_name}' is already used.")
        
    cursor.execute("UPDATE categories SET name = ?, color = ? WHERE id = ? AND user_id = ?", (new_name, new_color, cat_id, user_id))
    
    cursor.execute("""
    UPDATE tasks 
    SET category = ?, color = ? 
    WHERE category = ? AND user_id = ?
    """, (new_name, new_color, old_name, user_id))
    
    conn.commit()
    cursor.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    updated = dict(cursor.fetchone())
    conn.close()
    return updated

def delete_category(user_id, cat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    cat = cursor.fetchone()
    if not cat:
        conn.close()
        raise ValueError("Category not found.")
        
    cursor.execute("SELECT COUNT(*) AS cnt FROM categories WHERE user_id = ?", (user_id,))
    if cursor.fetchone()["cnt"] <= 1:
        conn.close()
        raise ValueError("Cannot delete the only remaining category.")
        
    cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    conn.commit()
    conn.close()
    return True

# ----------------- Settings API ----------------- #

def get_setting(user_id, key, default="3"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE user_id = ? AND key = ?", (user_id, key))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(user_id, key, value):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT rowid AS rid FROM settings WHERE user_id = ? AND key = ?", (user_id, key))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE rowid = ?", (str(value), row["rid"]))
    else:
        cursor.execute("INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, key, str(value)))
        
    conn.commit()
    conn.close()
    
    if key == "goal_threshold":
        recalculate_all_goals(user_id, int(value))
    return value

def get_goal_threshold(user_id):
    try:
        return int(get_setting(user_id, "goal_threshold", "3"))
    except ValueError:
        return 3

# ----------------- Auto Goal Logic ----------------- #

def get_special_task_ids(user_id, cursor):
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'goal' AND is_archived = 0 LIMIT 1", (user_id,))
    goal_row = cursor.fetchone()
    goal_id = goal_row["id"] if goal_row else None
    
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'full day' AND is_archived = 0 LIMIT 1", (user_id,))
    full_day_row = cursor.fetchone()
    full_day_id = full_day_row["id"] if full_day_row else None
    
    return goal_id, full_day_id

def evaluate_goal_for_date(user_id, date_str, conn=None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
        
    cursor = conn.cursor()
    threshold = get_goal_threshold(user_id)
    
    goal_id, full_day_id = get_special_task_ids(user_id, cursor)
    if not goal_id:
        if should_close:
            conn.close()
        return False
        
    # Check if 'Full Day' is checked on this date
    full_day_checked = False
    if full_day_id:
        cursor.execute("SELECT completed FROM completions WHERE user_id = ? AND task_id = ? AND date = ?", (user_id, full_day_id, date_str))
        f_row = cursor.fetchone()
        full_day_checked = bool(f_row and f_row["completed"] == 1)
        
    # Count completed regular top-level tasks (excluding Goal, Full Day, and subtasks)
    excluded_ids = [goal_id]
    if full_day_id:
        excluded_ids.append(full_day_id)
        
    placeholders = ",".join("?" for _ in excluded_ids)
    cursor.execute(f"""
    SELECT COUNT(DISTINCT t.id) AS cnt
    FROM completions c
    JOIN tasks t ON c.task_id = t.id
    WHERE c.user_id = ?
      AND c.date = ? 
      AND c.completed = 1 
      AND t.is_archived = 0
      AND t.parent_id IS NULL
      AND t.id NOT IN ({placeholders})
    """, [user_id, date_str] + excluded_ids)
    
    regular_completed = cursor.fetchone()["cnt"]

    # Full Day rule: Full Day cannot stay checked if 0 regular tasks are done
    if regular_completed == 0 and full_day_id and full_day_checked:
        cursor.execute("""
        UPDATE completions SET completed = 0, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND task_id = ? AND date = ?
        """, (user_id, full_day_id, date_str))
        full_day_checked = False
    
    # Goal condition:
    # 1. regular_completed >= threshold, OR
    # 2. full_day_checked is True and regular_completed >= 1
    if regular_completed >= threshold or (full_day_checked and regular_completed >= 1):
        goal_state = 1
    else:
        goal_state = 0
        
    cursor.execute("""
    INSERT INTO completions (user_id, task_id, date, completed, updated_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(task_id, date) DO UPDATE SET completed = excluded.completed, updated_at = CURRENT_TIMESTAMP
    """, (user_id, goal_id, date_str, goal_state))
    
    cursor.execute("SELECT rowid AS rid FROM daily_summaries WHERE user_id = ? AND date = ?", (user_id, date_str))
    d_row = cursor.fetchone()
    if d_row:
        cursor.execute("UPDATE daily_summaries SET daily_goal_achieved = ?, updated_at = CURRENT_TIMESTAMP WHERE rowid = ?", (goal_state, d_row["rid"]))
    else:
        cursor.execute("INSERT INTO daily_summaries (user_id, date, daily_goal_achieved) VALUES (?, ?, ?)", (user_id, date_str, goal_state))
        
    conn.commit()
    if should_close:
        conn.close()
    return bool(goal_state)

def recalculate_all_goals(user_id, threshold: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    goal_id, full_day_id = get_special_task_ids(user_id, cursor)
    if not goal_id:
        conn.close()
        return
        
    excluded_ids = [goal_id]
    if full_day_id:
        excluded_ids.append(full_day_id)
    placeholders = ",".join("?" for _ in excluded_ids)
    
    # Dates with regular completions (top-level tasks only)
    cursor.execute(f"""
    SELECT c.date, COUNT(DISTINCT t.id) as cnt
    FROM completions c
    JOIN tasks t ON c.task_id = t.id
    WHERE c.user_id = ? AND c.completed = 1 AND t.is_archived = 0 AND t.parent_id IS NULL AND t.id NOT IN ({placeholders})
    GROUP BY c.date
    """, [user_id] + excluded_ids)
    date_counts = {r["date"]: r["cnt"] for r in cursor.fetchall()}
    
    # Dates with Full Day checked
    full_day_dates = set()
    if full_day_id:
        cursor.execute("SELECT date FROM completions WHERE user_id = ? AND task_id = ? AND completed = 1", (user_id, full_day_id))
        full_day_dates = {r["date"] for r in cursor.fetchall()}
        
    # Existing Goal dates
    cursor.execute("SELECT date FROM completions WHERE user_id = ? AND task_id = ? AND completed = 1", (user_id, goal_id))
    existing_goal_dates = {r["date"] for r in cursor.fetchall()}
    
    all_dates = set(date_counts.keys()).union(full_day_dates).union(existing_goal_dates)
    for d_str in all_dates:
        cnt = date_counts.get(d_str, 0)
        fd = d_str in full_day_dates
        new_state = 1 if (cnt >= threshold or (fd and cnt >= 1)) else 0
        
        cursor.execute("""
        INSERT INTO completions (user_id, task_id, date, completed, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(task_id, date) DO UPDATE SET completed = excluded.completed, updated_at = CURRENT_TIMESTAMP
        """, (user_id, goal_id, d_str, new_state))
        
        cursor.execute("SELECT rowid AS rid FROM daily_summaries WHERE user_id = ? AND date = ?", (user_id, d_str))
        d_row = cursor.fetchone()
        if d_row:
            cursor.execute("UPDATE daily_summaries SET daily_goal_achieved = ?, updated_at = CURRENT_TIMESTAMP WHERE rowid = ?", (new_state, d_row["rid"]))
        else:
            cursor.execute("INSERT INTO daily_summaries (user_id, date, daily_goal_achieved) VALUES (?, ?, ?)", (user_id, d_str, new_state))
            
    conn.commit()
    conn.close()

# ----------------- Tasks CRUD ----------------- #

def get_all_tasks(user_id, include_archived=False):
    conn = get_connection()
    cursor = conn.cursor()
    
    top_arch = "" if include_archived else "AND is_archived = 0"
    cursor.execute(f"""
    SELECT * FROM tasks 
    WHERE user_id = ? AND parent_id IS NULL {top_arch}
    ORDER BY 
        CASE WHEN LOWER(TRIM(title)) = 'goal' THEN 0 
             WHEN LOWER(TRIM(title)) = 'full day' THEN 1 
             ELSE 2 END,
        sort_order ASC, id ASC
    """, (user_id,))
    parents = [dict(r) for r in cursor.fetchall()]
    
    sub_arch = "" if include_archived else "AND is_archived = 0"
    cursor.execute(f"""
    SELECT * FROM tasks 
    WHERE user_id = ? AND parent_id IS NOT NULL {sub_arch}
    ORDER BY sort_order ASC, id ASC
    """, (user_id,))
    subtasks = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    subtasks_by_parent = {}
    for st in subtasks:
        subtasks_by_parent.setdefault(st["parent_id"], []).append(st)
        
    ordered = []
    for p in parents:
        ordered.append(p)
        if p["id"] in subtasks_by_parent:
            ordered.extend(subtasks_by_parent[p["id"]])
            
    return ordered

def add_task(user_id, title, category="General", parent_id=None):
    clean_title = title.strip().lower()
    if clean_title in ("goal", "full day"):
        raise ValueError(f"Cannot create task named '{title}'. It is a reserved system task.")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    if parent_id is not None:
        try:
            parent_id = int(parent_id)
        except (ValueError, TypeError):
            conn.close()
            raise ValueError("Invalid parent task ID.")
            
        cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ? AND is_archived = 0", (parent_id, user_id))
        parent_task = cursor.fetchone()
        if not parent_task:
            conn.close()
            raise ValueError("Parent task does not exist or is archived.")
            
        p_clean = parent_task["title"].strip().lower()
        if p_clean in ("goal", "full day"):
            conn.close()
            raise ValueError("Cannot create subtasks for system tasks (Goal or Full Day).")
            
        # Strict level-1 nesting constraint
        if parent_task["parent_id"] is not None:
            conn.close()
            raise ValueError("Subtasks cannot have nested subtasks (maximum 1 level of nesting allowed).")
            
        category = ""
        color = parent_task["color"] or "#94a3b8"
    else:
        category = category.strip()
        color_map = get_category_color_map(user_id)
        color = color_map.get(category, "#3b82f6")
        
    cursor.execute("SELECT COALESCE(MAX(sort_order), 1) + 1 AS next_order FROM tasks WHERE user_id = ?", (user_id,))
    next_order = cursor.fetchone()["next_order"]
    
    cursor.execute("""
    INSERT INTO tasks (user_id, title, category, color, icon, target_frequency, sort_order, parent_id)
    VALUES (?, ?, ?, ?, 'check-circle', 'daily', ?, ?)
    """, (user_id, title.strip(), category, color, next_order, parent_id))
    task_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    task = dict(cursor.fetchone())
    conn.close()
    return task

def update_task(user_id, task_id, title=None, category=None, is_archived=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return None
        
    clean_title = existing["title"].strip().lower()
    is_protected = clean_title in ("goal", "full day")
    is_subtask = existing["parent_id"] is not None
    
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
        
    if category is not None and not is_subtask:
        cat = category.strip()
        color_map = get_category_color_map(user_id)
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
    values.append(user_id)
    sql = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ? AND user_id = ?"
    cursor.execute(sql, values)
    
    if is_archived and not is_subtask:
        cursor.execute("UPDATE tasks SET is_archived = 1 WHERE parent_id = ? AND user_id = ?", (task_id, user_id))
        
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_task(user_id, task_id, hard_delete=False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, parent_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    if row["title"].strip().lower() in ("goal", "full day"):
        conn.close()
        raise ValueError(f"The '{row['title']}' task cannot be deleted.")
        
    if hard_delete:
        cursor.execute("DELETE FROM completions WHERE user_id = ? AND (task_id = ? OR task_id IN (SELECT id FROM tasks WHERE parent_id = ? AND user_id = ?))", (user_id, task_id, task_id, user_id))
        cursor.execute("DELETE FROM tasks WHERE parent_id = ? AND user_id = ?", (task_id, user_id))
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    else:
        cursor.execute("UPDATE tasks SET is_archived = 1 WHERE user_id = ? AND (id = ? OR parent_id = ?)", (user_id, task_id, task_id))
        
    conn.commit()
    conn.close()
    return True

def reorder_tasks(user_id, task_ids):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'goal' AND is_archived = 0 LIMIT 1", (user_id,))
    goal_row = cursor.fetchone()
    goal_id = goal_row["id"] if goal_row else None
    
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'full day' AND is_archived = 0 LIMIT 1", (user_id,))
    full_day_row = cursor.fetchone()
    full_day_id = full_day_row["id"] if full_day_row else None

    if goal_id:
        cursor.execute("UPDATE tasks SET sort_order = 0 WHERE id = ? AND user_id = ?", (goal_id, user_id))
    if full_day_id:
        cursor.execute("UPDATE tasks SET sort_order = 1 WHERE id = ? AND user_id = ?", (full_day_id, user_id))

    order_idx = 2
    for t_id in task_ids:
        if t_id not in (goal_id, full_day_id):
            cursor.execute("UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?", (order_idx, t_id, user_id))
            order_idx += 1
            
    if task_ids:
        placeholders = ",".join("?" for _ in task_ids)
        cursor.execute(f"""
        SELECT id FROM tasks 
        WHERE user_id = ? AND parent_id IS NULL AND id NOT IN ({placeholders}) 
          AND LOWER(TRIM(title)) NOT IN ('goal', 'full day')
        ORDER BY sort_order ASC, id ASC
        """, [user_id] + task_ids)
        for r in cursor.fetchall():
            cursor.execute("UPDATE tasks SET sort_order = ? WHERE id = ? AND user_id = ?", (order_idx, r["id"], user_id))
            order_idx += 1

    conn.commit()
    conn.close()
    return True

# ----------------- Completions & Matrix ----------------- #

def toggle_completion(user_id, task_id, date_str, target_state=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, parent_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    task_row = cursor.fetchone()
    if not task_row:
        conn.close()
        raise ValueError("Task not found")
        
    t_clean = task_row["title"].strip().lower()
    if t_clean == "goal":
        conn.close()
        raise ValueError("The 'Goal' main task is automated and cannot be manually toggled.")
        
    cursor.execute("SELECT completed FROM completions WHERE user_id = ? AND task_id = ? AND date = ?", (user_id, task_id, date_str))
    row = cursor.fetchone()
    
    if target_state is not None:
        new_state = 1 if target_state else 0
    else:
        new_state = 0 if (row and row["completed"] == 1) else 1

    # Full Day rule: Full Day cannot be checked if 0 regular tasks are completed on that date
    if t_clean == "full day" and new_state == 1:
        cursor.execute("""
        SELECT COUNT(DISTINCT t.id) AS cnt
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.user_id = ?
          AND c.date = ?
          AND c.completed = 1
          AND t.is_archived = 0
          AND t.parent_id IS NULL
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
        """, (user_id, date_str))
        if cursor.fetchone()["cnt"] == 0:
            conn.close()
            raise ValueError("At least 1 habit must be checked before marking Full Day.")
        
    if row:
        cursor.execute("""
        UPDATE completions 
        SET completed = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE user_id = ? AND task_id = ? AND date = ?
        """, (new_state, user_id, task_id, date_str))
    else:
        cursor.execute("""
        INSERT INTO completions (user_id, task_id, date, completed)
        VALUES (?, ?, ?, ?)
        """, (user_id, task_id, date_str, new_state))
        
    # Automatic parent tick: ticking subtask automatically ticks the parent!
    parent_id = task_row["parent_id"]
    if parent_id and new_state == 1:
        cursor.execute("""
        INSERT INTO completions (user_id, task_id, date, completed, updated_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(task_id, date) DO UPDATE SET completed = 1, updated_at = CURRENT_TIMESTAMP
        """, (user_id, parent_id, date_str))
        
    conn.commit()
    goal_completed = evaluate_goal_for_date(user_id, date_str, conn=conn)
    conn.close()
    
    return {
        "task_id": task_id,
        "date": date_str,
        "completed": bool(new_state),
        "parent_id": parent_id,
        "goal_auto_completed": goal_completed
    }

def toggle_daily_goal(user_id, date_str, target_state=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rowid AS rid, daily_goal_achieved FROM daily_summaries WHERE user_id = ? AND date = ?", (user_id, date_str))
    row = cursor.fetchone()
    
    if target_state is not None:
        new_state = 1 if target_state else 0
    else:
        new_state = 0 if (row and row["daily_goal_achieved"] == 1) else 1
        
    if row:
        cursor.execute("""
        UPDATE daily_summaries 
        SET daily_goal_achieved = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE rowid = ?
        """, (new_state, row["rid"]))
    else:
        cursor.execute("""
        INSERT INTO daily_summaries (user_id, date, daily_goal_achieved)
        VALUES (?, ?, ?)
        """, (user_id, date_str, new_state))
        
    conn.commit()
    conn.close()
    return {"date": date_str, "daily_goal_achieved": bool(new_state)}

def save_daily_note(user_id, date_str, note):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rowid AS rid FROM daily_summaries WHERE user_id = ? AND date = ?", (user_id, date_str))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE daily_summaries SET focus_note = ?, updated_at = CURRENT_TIMESTAMP WHERE rowid = ?", (note, row["rid"]))
    else:
        cursor.execute("INSERT INTO daily_summaries (user_id, date, focus_note) VALUES (?, ?, ?)", (user_id, date_str, note))
    conn.commit()
    conn.close()
    return {"date": date_str, "note": note}

def get_matrix(user_id: int, year: int, month: int):
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
        
    tasks = get_all_tasks(user_id, include_archived=False)
    
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{num_days:02d}"
    cursor.execute("""
    SELECT task_id, date, completed 
    FROM completions 
    WHERE user_id = ? AND date >= ? AND date <= ? AND completed = 1
    """, (user_id, start_date, end_date))
    
    completed_map = set()
    for r in cursor.fetchall():
        completed_map.add((r["task_id"], r["date"]))
        
    cursor.execute("""
    SELECT date, daily_goal_achieved, focus_note 
    FROM daily_summaries 
    WHERE user_id = ? AND date >= ? AND date <= ?
    """, (user_id, start_date, end_date))
    daily_summaries = {r["date"]: dict(r) for r in cursor.fetchall()}
    
    threshold = get_goal_threshold(user_id)
    conn.close()
    
    task_rows = []
    for task in tasks:
        task_id = task["id"]
        cells = []
        task_total_completed = 0
        t_clean = task["title"].strip().lower()
        is_goal = t_clean == "goal"
        is_full_day = t_clean == "full day"
        is_subtask = bool(task.get("parent_id"))
        
        for idx, d_str in enumerate(day_date_strs):
            is_done = (task_id, d_str) in completed_map
            cells.append(is_done)
            if is_done:
                task_total_completed += 1
                
        task_rows.append({
            "task": task,
            "is_goal": is_goal,
            "is_full_day": is_full_day,
            "is_subtask": is_subtask,
            "parent_id": task.get("parent_id"),
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
        "total_habits": len([t for t in tasks if t["title"].strip().lower() not in ("goal", "full day")]),
        "num_days": num_days,
        "goal_threshold": threshold
    }

# ----------------- Heatmap & Streaks ----------------- #

def get_heatmap(user_id: int, year: int, task_id: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM tasks WHERE user_id = ? AND LOWER(TRIM(title)) = 'goal' AND is_archived = 0 LIMIT 1", (user_id,))
    goal_row = cursor.fetchone()
    goal_id = goal_row["id"] if goal_row else None
    
    if task_id:
        cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND id = ?", (user_id, task_id))
        task_row = cursor.fetchone()
        filter_task = dict(task_row) if task_row else None
        total_tasks_target = 1
    else:
        filter_task = None
        # Heatmap counts regular tasks (excludes Goal and Full Day)
        cursor.execute("""
        SELECT COUNT(*) AS cnt FROM tasks 
        WHERE user_id = ? AND is_archived = 0 AND LOWER(TRIM(title)) NOT IN ('goal', 'full day')
        """, (user_id,))
        total_tasks_target = cursor.fetchone()["cnt"] or 1
        
    start_date = f"{year:04d}-01-01"
    end_date = f"{year:04d}-12-31"
    
    if task_id:
        cursor.execute("""
        SELECT date, COUNT(*) AS count
        FROM completions
        WHERE user_id = ? AND date >= ? AND date <= ? AND task_id = ? AND completed = 1
        GROUP BY date
        """, (user_id, start_date, end_date, task_id))
    else:
        cursor.execute("""
        SELECT c.date, COUNT(*) AS count
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.user_id = ? AND c.date >= ? AND c.date <= ? AND c.completed = 1 AND t.is_archived = 0 
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
        GROUP BY c.date
        """, (user_id, start_date, end_date))
        
    day_counts = {r["date"]: r["count"] for r in cursor.fetchall()}
    
    # Dates where Goal was achieved for this user
    goal_dates = set()
    if goal_id:
        cursor.execute("""
        SELECT date FROM completions 
        WHERE user_id = ? AND date >= ? AND date <= ? AND task_id = ? AND completed = 1
        """, (user_id, start_date, end_date, goal_id))
        goal_dates = {r["date"] for r in cursor.fetchall()}
        
    if task_id:
        cursor.execute("""
        SELECT date, t.title
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.user_id = ? AND c.date >= ? AND c.date <= ? AND task_id = ? AND completed = 1
        """, (user_id, start_date, end_date, task_id))
    else:
        cursor.execute("""
        SELECT c.date, t.title
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.user_id = ? AND c.date >= ? AND c.date <= ? AND c.completed = 1 AND t.is_archived = 0 
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
        """, (user_id, start_date, end_date))
        
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
        
    # Streak Calculation based on GOAL continuity
    longest_streak = 0
    cur_streak_run = 0
    
    for day_obj, d_str in all_dates:
        if day_obj > today:
            break
        if d_str in goal_dates:
            cur_streak_run += 1
            if cur_streak_run > longest_streak:
                longest_streak = cur_streak_run
        else:
            cur_streak_run = 0
            
    current_streak = 0
    check_date = today
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

def get_yearly_stats(user_id: int, year: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT COUNT(*) AS cnt FROM tasks 
    WHERE user_id = ? AND is_archived = 0 AND LOWER(TRIM(title)) NOT IN ('goal', 'full day')
    """, (user_id,))
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
        WHERE c.user_id = ? AND c.date >= ? AND c.date <= ? AND c.completed = 1 AND t.is_archived = 0 
          AND LOWER(TRIM(t.title)) NOT IN ('goal', 'full day')
        """, (user_id, start_date, end_date))
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

def export_all(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM categories WHERE user_id = ?", (user_id,))
    categories = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
    tasks = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM completions WHERE user_id = ?", (user_id,))
    completions = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
    settings = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM daily_summaries WHERE user_id = ?", (user_id,))
    summaries = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "exported_at": datetime.now().isoformat(),
        "version": "4.0",
        "user_id": user_id,
        "categories": categories,
        "tasks": tasks,
        "completions": completions,
        "settings": settings,
        "daily_summaries": summaries
    }

def import_backup(user_id: int, data_dict: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    if "categories" in data_dict:
        for c in data_dict["categories"]:
            cursor.execute("""
            INSERT OR REPLACE INTO categories (user_id, name, color, sort_order)
            VALUES (?, ?, ?, ?)
            """, (user_id, c["name"], c.get("color", "#3b82f6"), c.get("sort_order", 0)))
            
    color_map = {c["name"]: c["color"] for c in data_dict.get("categories", [])}
    
    if "tasks" in data_dict:
        for t in data_dict["tasks"]:
            cat = t.get("category", "General")
            col = color_map.get(cat, t.get("color", "#3b82f6"))
            cursor.execute("""
            INSERT INTO tasks (user_id, title, category, color, icon, target_frequency, sort_order, is_archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, t.get("title"), cat, col,
                  t.get("icon", "check-circle"), t.get("target_frequency", "daily"),
                  t.get("sort_order", 0), t.get("is_archived", 0)))
                  
    if "completions" in data_dict:
        for c in data_dict["completions"]:
            cursor.execute("""
            INSERT INTO completions (user_id, task_id, date, completed, notes)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, c["task_id"], c["date"], c.get("completed", 1), c.get("notes", "")))
            
    if "settings" in data_dict:
        for s in data_dict["settings"]:
            cursor.execute("""
            INSERT INTO settings (user_id, key, value)
            VALUES (?, ?, ?)
            """, (user_id, s["key"], s["value"]))
            
    if "daily_summaries" in data_dict:
        for s in data_dict["daily_summaries"]:
            cursor.execute("""
            INSERT INTO daily_summaries (user_id, date, daily_goal_achieved, focus_note)
            VALUES (?, ?, ?, ?)
            """, (user_id, s["date"], s.get("daily_goal_achieved", 0), s.get("focus_note", "")))
            
    conn.commit()
    conn.close()
    
    threshold = get_goal_threshold(user_id)
    recalculate_all_goals(user_id, threshold)
    return True
