import os
import io
import csv
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import database

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "goalplanner-secret-key-2026")

# Initialize SQLite database on startup
database.init_db()

@app.route("/")
def index():
    now = datetime.now()
    return render_template("index.html", initial_year=now.year, initial_month=now.month)

# ----------------- Categories Endpoints ----------------- #

@app.route("/api/categories", methods=["GET"])
def list_categories():
    categories = database.get_all_categories()
    return jsonify({"success": True, "categories": categories})

@app.route("/api/categories", methods=["POST"])
def create_category():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    color = data.get("color", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Category name is required"}), 400
    if not color:
        return jsonify({"success": False, "error": "Category color is required"}), 400
        
    try:
        cat = database.add_category(name=name, color=color)
        return jsonify({"success": True, "category": cat}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/categories/<int:cat_id>", methods=["PUT"])
def update_category_endpoint(cat_id):
    data = request.get_json() or {}
    name = data.get("name")
    color = data.get("color")
    try:
        updated = database.update_category(cat_id=cat_id, name=name, color=color)
        return jsonify({"success": True, "category": updated})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/categories/<int:cat_id>", methods=["DELETE"])
def delete_category_endpoint(cat_id):
    try:
        database.delete_category(cat_id=cat_id)
        return jsonify({"success": True, "message": "Category removed"})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ----------------- Tasks Endpoints ----------------- #

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    include_archived = request.args.get("include_archived", "false").lower() == "true"
    tasks = database.get_all_tasks(include_archived=include_archived)
    return jsonify({"success": True, "tasks": tasks})

@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"success": False, "error": "Task title is required"}), 400
    if title.lower() == "goal":
        return jsonify({"success": False, "error": "'Goal' is reserved as the main task and cannot be created."}), 400
        
    category = data.get("category", "Mind")
    try:
        task = database.add_task(title=title, category=category)
        return jsonify({"success": True, "task": task}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task_endpoint(task_id):
    data = request.get_json() or {}
    try:
        updated = database.update_task(
            task_id=task_id,
            title=data.get("title"),
            category=data.get("category"),
            is_archived=data.get("is_archived")
        )
        if not updated:
            return jsonify({"success": False, "error": "Task not found"}), 404
        return jsonify({"success": True, "task": updated})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task_endpoint(task_id):
    hard_delete = request.args.get("hard", "false").lower() == "true"
    try:
        database.delete_task(task_id=task_id, hard_delete=hard_delete)
        return jsonify({"success": True, "message": "Task removed"})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/tasks/reorder", methods=["POST"])
def reorder_tasks_endpoint():
    data = request.get_json() or {}
    task_ids = data.get("task_ids", [])
    database.reorder_tasks(task_ids)
    return jsonify({"success": True})

# ----------------- Matrix View Endpoints ----------------- #

@app.route("/api/matrix", methods=["GET"])
def get_matrix_data():
    now = datetime.now()
    year = int(request.args.get("year", now.year))
    month = int(request.args.get("month", now.month))
    
    if month < 1 or month > 12:
        return jsonify({"success": False, "error": "Invalid month"}), 400
        
    data = database.get_matrix(year, month)
    return jsonify({"success": True, "data": data})

@app.route("/api/toggle", methods=["POST"])
def toggle_task_completion():
    data = request.get_json() or {}
    task_id = data.get("task_id")
    date_str = data.get("date")
    state = data.get("state")
    
    if not task_id or not date_str:
        return jsonify({"success": False, "error": "task_id and date are required"}), 400
        
    try:
        result = database.toggle_completion(task_id=int(task_id), date_str=date_str, target_state=state)
        return jsonify({"success": True, "result": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/settings/threshold", methods=["GET", "POST"])
def goal_threshold_endpoint():
    if request.method == "POST":
        data = request.get_json() or {}
        val = data.get("threshold")
        if val is None:
            return jsonify({"success": False, "error": "threshold is required"}), 400
        try:
            val = int(val)
            if val < 1:
                return jsonify({"success": False, "error": "Threshold must be at least 1"}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Threshold must be an integer"}), 400
            
        saved_val = database.set_setting("goal_threshold", val)
        return jsonify({"success": True, "threshold": int(saved_val)})
    else:
        threshold = database.get_goal_threshold()
        return jsonify({"success": True, "threshold": threshold})

@app.route("/api/daily-note", methods=["POST"])
def save_daily_note_endpoint():
    data = request.get_json() or {}
    date_str = data.get("date")
    note = data.get("note", "")
    
    if not date_str:
        return jsonify({"success": False, "error": "date is required"}), 400
        
    result = database.save_daily_note(date_str=date_str, note=note)
    return jsonify({"success": True, "result": result})

# ----------------- Heatmap & Yearly Stats ----------------- #

@app.route("/api/heatmap", methods=["GET"])
def get_heatmap_endpoint():
    now = datetime.now()
    year = int(request.args.get("year", now.year))
    task_id_param = request.args.get("task_id")
    task_id = int(task_id_param) if task_id_param and task_id_param != "all" else None
    
    data = database.get_heatmap(year=year, task_id=task_id)
    return jsonify({"success": True, "data": data})

@app.route("/api/yearly-stats", methods=["GET"])
def get_yearly_stats_endpoint():
    now = datetime.now()
    year = int(request.args.get("year", now.year))
    data = database.get_yearly_stats(year=year)
    return jsonify({"success": True, "data": data})

# ----------------- Export & Backup ----------------- #

@app.route("/api/export", methods=["GET"])
def export_data():
    fmt = request.args.get("format", "json").lower()
    data = database.export_all()
    
    if fmt == "json":
        return jsonify(data)
        
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["=== CATEGORIES ==="])
    writer.writerow(["ID", "Name", "Color", "Sort Order"])
    for c in data.get("categories", []):
        writer.writerow([c["id"], c["name"], c["color"], c.get("sort_order", 0)])
        
    writer.writerow([])
    writer.writerow(["=== TASKS ==="])
    writer.writerow(["ID", "Title", "Category", "Color", "Icon", "Target Frequency", "Sort Order", "Is Archived"])
    for t in data["tasks"]:
        writer.writerow([t["id"], t["title"], t["category"], t["color"], t["icon"], t.get("target_frequency", "daily"), t["sort_order"], t["is_archived"]])
        
    writer.writerow([])
    writer.writerow(["=== COMPLETIONS ==="])
    writer.writerow(["ID", "Task ID", "Date", "Completed", "Notes"])
    for c in data["completions"]:
        writer.writerow([c["id"], c["task_id"], c["date"], c["completed"], c.get("notes", "")])
        
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"goalplanner_backup_{date.today().isoformat()}.csv"
    )

@app.route("/api/import", methods=["POST"])
def import_data():
    if "file" not in request.files:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No file or JSON data provided"}), 400
    else:
        import json
        file = request.files["file"]
        try:
            data = json.load(file)
        except Exception as e:
            return jsonify({"success": False, "error": f"Invalid JSON file: {str(e)}"}), 400
            
    database.import_backup(data)
    return jsonify({"success": True, "message": "Backup imported successfully"})

# ----------------- PWA Files ----------------- #

@app.route("/manifest.json")
def pwa_manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")

@app.route("/service-worker.js")
def service_worker():
    return send_from_directory("static", "service-worker.js", mimetype="application/javascript")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"GoalPlanner server running at: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
