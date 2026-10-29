// Global Application State
const state = {
    currentYear: new Date().getFullYear(),
    currentMonth: new Date().getMonth() + 1,
    todayDateStr: new Date().toISOString().split("T")[0],
    selectedDateStr: new Date().toISOString().split("T")[0],
    activeView: "matrix",
    tasks: [],
    streak: 0
};

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initStateFromUI();
    loadTasks();
    switchView("matrix");
});

function initStateFromUI() {
    const monthSelect = document.getElementById("matrix-month-select");
    const yearSelect = document.getElementById("matrix-year-select");
    const heatmapYearSelect = document.getElementById("heatmap-year-select");
    const yearlySelect = document.getElementById("yearly-view-year-select");

    if (monthSelect) monthSelect.value = state.currentMonth;
    if (yearSelect) yearSelect.value = state.currentYear;
    if (heatmapYearSelect) heatmapYearSelect.value = state.currentYear;
    if (yearlySelect) yearlySelect.value = state.currentYear;
}

// ----------------- View Navigation ----------------- //

function switchView(viewName) {
    state.activeView = viewName;

    // Update Tab Styles
    document.querySelectorAll(".view-tab").forEach(tab => {
        tab.classList.remove("text-white", "bg-blue-600", "shadow-sm");
        tab.classList.add("text-slate-400");
    });

    const activeTab = document.getElementById(`view-tab-${viewName}`);
    if (activeTab) {
        activeTab.classList.remove("text-slate-400");
        activeTab.classList.add("text-white", "bg-blue-600", "shadow-sm");
    }

    // Toggle Section Visibility
    document.getElementById("view-matrix").classList.toggle("hidden", viewName !== "matrix");
    document.getElementById("view-heatmap").classList.toggle("hidden", viewName !== "heatmap");
    document.getElementById("view-today").classList.toggle("hidden", viewName !== "today");
    document.getElementById("view-yearly").classList.toggle("hidden", viewName !== "yearly");

    // Load data for active view
    if (viewName === "matrix") {
        if (window.loadMatrix) window.loadMatrix();
    } else if (viewName === "heatmap") {
        if (window.loadHeatmap) window.loadHeatmap();
    } else if (viewName === "today") {
        loadTodayChecklist();
    } else if (viewName === "yearly") {
        loadYearlyOverview();
    }
}

// ----------------- Month / Year Navigation ----------------- //

function changeMonth(delta) {
    state.currentMonth += delta;
    if (state.currentMonth > 12) {
        state.currentMonth = 1;
        state.currentYear += 1;
    } else if (state.currentMonth < 1) {
        state.currentMonth = 12;
        state.currentYear -= 1;
    }
    updateDateSelects();
    if (window.loadMatrix) window.loadMatrix();
}

function jumpToCurrentMonth() {
    const now = new Date();
    state.currentYear = now.getFullYear();
    state.currentMonth = now.getMonth() + 1;
    updateDateSelects();
    if (window.loadMatrix) window.loadMatrix();
}

function onDateSelectChange() {
    const monthSelect = document.getElementById("matrix-month-select");
    const yearSelect = document.getElementById("matrix-year-select");
    state.currentMonth = parseInt(monthSelect.value);
    state.currentYear = parseInt(yearSelect.value);
    if (window.loadMatrix) window.loadMatrix();
}

function updateDateSelects() {
    const monthSelect = document.getElementById("matrix-month-select");
    const yearSelect = document.getElementById("matrix-year-select");
    if (monthSelect) monthSelect.value = state.currentMonth;
    if (yearSelect) yearSelect.value = state.currentYear;
}

// ----------------- Tasks Management ----------------- //

async function loadTasks() {
    try {
        const res = await fetch("/api/tasks");
        const data = await res.json();
        if (data.success) {
            state.tasks = data.tasks;
            populateHeatmapTaskFilter();
        }
    } catch (err) {
        console.error("Failed to load tasks", err);
    }
}

function populateHeatmapTaskFilter() {
    const select = document.getElementById("heatmap-task-filter");
    if (!select) return;

    const currentVal = select.value;
    select.innerHTML = '<option value="all">⚡ All Habits (Aggregate)</option>';
    state.tasks.forEach(task => {
        const opt = document.createElement("option");
        opt.value = task.id;
        opt.textContent = `${task.title} (${task.category})`;
        select.appendChild(opt);
    });
    select.value = currentVal || "all";
}

function openAddTaskModal() {
    document.getElementById("task-modal-title").innerHTML = '<i data-lucide="plus-circle" class="w-5 h-5 text-blue-400"></i> Add New Task';
    document.getElementById("task-id-input").value = "";
    document.getElementById("task-title-input").value = "";
    document.getElementById("task-category-input").value = "General";
    document.getElementById("task-frequency-input").value = "daily";
    document.getElementById("task-delete-btn").classList.add("hidden");
    selectColor("#3b82f6");

    document.getElementById("task-modal").classList.remove("hidden");
    lucide.createIcons();
}

function openEditTaskModal(task) {
    document.getElementById("task-modal-title").innerHTML = '<i data-lucide="edit-3" class="w-5 h-5 text-blue-400"></i> Edit Task';
    document.getElementById("task-id-input").value = task.id;
    document.getElementById("task-title-input").value = task.title;
    document.getElementById("task-category-input").value = task.category || "General";
    document.getElementById("task-frequency-input").value = task.target_frequency || "daily";
    document.getElementById("task-delete-btn").classList.remove("hidden");
    selectColor(task.color || "#3b82f6");

    document.getElementById("task-modal").classList.remove("hidden");
    lucide.createIcons();
}

function closeTaskModal() {
    document.getElementById("task-modal").classList.add("hidden");
}

function selectColor(hex) {
    document.getElementById("task-color-input").value = hex;
    document.querySelectorAll("#color-palette-picker button").forEach(btn => {
        btn.classList.remove("ring-2", "ring-offset-2", "ring-offset-slate-900", "ring-blue-500");
    });
    const clickedBtn = Array.from(document.querySelectorAll("#color-palette-picker button")).find(
        b => b.getAttribute("onclick") && b.getAttribute("onclick").includes(hex)
    );
    if (clickedBtn) {
        clickedBtn.classList.add("ring-2", "ring-offset-2", "ring-offset-slate-900", "ring-blue-500");
    }
}

async function handleTaskSubmit(event) {
    event.preventDefault();
    const taskId = document.getElementById("task-id-input").value;
    const title = document.getElementById("task-title-input").value.trim();
    const category = document.getElementById("task-category-input").value.trim() || "General";
    const targetFrequency = document.getElementById("task-frequency-input").value;
    const color = document.getElementById("task-color-input").value;

    const payload = { title, category, target_frequency: targetFrequency, color };

    try {
        let res;
        if (taskId) {
            res = await fetch(`/api/tasks/${taskId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        } else {
            res = await fetch("/api/tasks", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        }

        const data = await res.json();
        if (data.success) {
            showToast(taskId ? "Task updated!" : "Task created successfully!", "success");
            closeTaskModal();
            await loadTasks();
            if (window.loadMatrix) window.loadMatrix();
            if (state.activeView === "today") loadTodayChecklist();
        } else {
            showToast(data.error || "Failed to save task", "error");
        }
    } catch (err) {
        showToast("Network error saving task", "error");
    }
}

async function handleTaskDelete() {
    const taskId = document.getElementById("task-id-input").value;
    if (!taskId) return;

    if (!confirm("Are you sure you want to remove this task? Past completion history will be archived.")) {
        return;
    }

    try {
        const res = await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
            showToast("Task removed", "info");
            closeTaskModal();
            await loadTasks();
            if (window.loadMatrix) window.loadMatrix();
            if (state.activeView === "today") loadTodayChecklist();
        }
    } catch (err) {
        showToast("Error deleting task", "error");
    }
}

// ----------------- Today's Checklist View ----------------- //

function changeTodayDate(deltaDays) {
    const d = new Date(state.selectedDateStr);
    d.setDate(d.getDate() + deltaDays);
    state.selectedDateStr = d.toISOString().split("T")[0];
    loadTodayChecklist();
}

async function loadTodayChecklist() {
    const container = document.getElementById("today-checklist-container");
    const d = new Date(state.selectedDateStr);
    const isToday = state.selectedDateStr === state.todayDateStr;

    // Header date labels
    const options = { weekday: "long", month: "short", day: "numeric", year: "numeric" };
    document.getElementById("today-header-date").textContent = isToday ? "Today" : d.toLocaleDateString(undefined, { weekday: "long" });
    document.getElementById("today-sub-date").textContent = d.toLocaleDateString(undefined, options);

    container.innerHTML = '<div class="text-center py-6 text-slate-500">Loading tasks...</div>';

    try {
        // Fetch matrix for that day's month
        const year = d.getFullYear();
        const month = d.getMonth() + 1;
        const res = await fetch(`/api/matrix?year=${year}&month=${month}`);
        const json = await res.json();

        if (!json.success) return;

        const matrixData = json.data;
        const dayIdx = d.getDate() - 1;
        const dailyStat = matrixData.daily_stats[dayIdx] || { completed_count: 0, total_tasks: 0, percentage: 0 };

        // Update progress ring
        updateProgressRing(dailyStat.completed_count, dailyStat.total_tasks, dailyStat.percentage);

        // Daily note input
        document.getElementById("today-note-input").value = dailyStat.focus_note || "";

        container.innerHTML = "";

        matrixData.matrix.forEach(row => {
            const task = row.task;
            const isCompleted = row.cells[dayIdx] || false;

            const card = document.createElement("div");
            card.className = `flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                isCompleted 
                ? "bg-slate-900/90 border-emerald-500/30 text-white shadow-sm" 
                : "bg-slate-900/40 border-slate-800 text-slate-300 hover:border-slate-700"
            }`;

            card.innerHTML = `
                <div class="flex items-center gap-3">
                    <div class="w-3.5 h-3.5 rounded-full" style="background-color: ${task.color || '#3b82f6'}"></div>
                    <div>
                        <div class="font-semibold text-sm ${isCompleted ? 'line-through text-slate-400' : 'text-white'}">${task.title}</div>
                        <div class="text-[11px] text-slate-400">${task.category} • ${task.target_frequency}</div>
                    </div>
                </div>
                <input type="checkbox" ${isCompleted ? 'checked' : ''} class="matrix-checkbox pointer-events-none" style="${isCompleted ? `background-color: ${task.color}; border-color: ${task.color};` : ''}">
            `;

            card.onclick = () => toggleTodayItem(task.id, isCompleted);
            container.appendChild(card);
        });

    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="text-center py-6 text-red-400">Failed to load day tasks</div>';
    }
}

async function toggleTodayItem(taskId, currentState) {
    try {
        const res = await fetch("/api/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                task_id: taskId,
                date: state.selectedDateStr,
                state: !currentState
            })
        });
        const data = await res.json();
        if (data.success) {
            loadTodayChecklist();
            if (window.loadHeatmap) window.loadHeatmap(false);
        }
    } catch (err) {
        showToast("Error updating task status", "error");
    }
}

function updateProgressRing(completed, total, percentage) {
    document.getElementById("today-progress-stats").textContent = `${completed} / ${total} Tasks`;
    document.getElementById("today-percentage-text").textContent = `${Math.round(percentage)}%`;

    const ring = document.getElementById("today-progress-ring");
    const circumference = 163.36; // 2 * pi * 26
    const offset = circumference - (percentage / 100) * circumference;
    ring.style.strokeDashoffset = offset;
}

async function saveCurrentDayNote() {
    const note = document.getElementById("today-note-input").value.trim();
    try {
        const res = await fetch("/api/daily-note", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                date: state.selectedDateStr,
                note: note
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Daily note saved!", "success");
        }
    } catch (err) {
        showToast("Failed to save note", "error");
    }
}

// ----------------- Yearly Stats Overview ----------------- //

async function loadYearlyOverview() {
    const yearSelect = document.getElementById("yearly-view-year-select");
    const year = parseInt(yearSelect.value);
    const container = document.getElementById("yearly-months-grid");

    container.innerHTML = '<div class="col-span-full text-center py-10 text-slate-500">Loading yearly breakdown...</div>';

    try {
        const res = await fetch(`/api/yearly-stats?year=${year}`);
        const json = await res.json();
        if (!json.success) return;

        const data = json.data;
        container.innerHTML = "";

        data.months.forEach(m => {
            const isBest = m.month_name === data.best_month && data.best_month_rate > 0;
            const card = document.createElement("div");
            card.className = `p-4 rounded-2xl border transition-all cursor-pointer ${
                isBest ? 'bg-gradient-to-br from-blue-900/30 to-slate-900 border-blue-500/40 shadow-lg' : 'bg-slate-900 border-slate-800 hover:border-slate-700'
            }`;

            card.onclick = () => {
                state.currentYear = year;
                state.currentMonth = m.month;
                updateDateSelects();
                switchView("matrix");
            };

            card.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <span class="font-bold text-sm text-white">${m.month_name}</span>
                    ${isBest ? '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">🏆 Best Month</span>' : ''}
                </div>
                <div class="text-2xl font-black text-white mt-1">${m.completion_rate}%</div>
                <div class="text-xs text-slate-400 mt-0.5">${m.completions} of ${m.max_possible} tasks</div>
                <div class="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                    <div class="bg-blue-500 h-full rounded-full transition-all duration-500" style="width: ${m.completion_rate}%"></div>
                </div>
            `;
            container.appendChild(card);
        });

    } catch (err) {
        container.innerHTML = '<div class="col-span-full text-center py-10 text-red-400">Failed to load yearly stats</div>';
    }
}

// ----------------- Backup & Restore ----------------- //

function openBackupModal() {
    document.getElementById("backup-modal").classList.remove("hidden");
    lucide.createIcons();
}

function closeBackupModal() {
    document.getElementById("backup-modal").classList.add("hidden");
}

async function handleBackupImport() {
    const fileInput = document.getElementById("backup-file-input");
    if (!fileInput.files.length) {
        showToast("Please choose a JSON backup file first", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const res = await fetch("/api/import", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast("Backup restored successfully!", "success");
            closeBackupModal();
            loadTasks();
            if (window.loadMatrix) window.loadMatrix();
        } else {
            showToast(data.error || "Failed to restore backup", "error");
        }
    } catch (err) {
        showToast("Network error importing backup", "error");
    }
}

// ----------------- Theme & Toast Utilities ----------------- //

function initTheme() {
    const saved = localStorage.getItem("goalplanner_theme");
    const isDark = saved ? saved === "dark" : true;
    document.documentElement.classList.toggle("dark", isDark);
    updateThemeIcon(isDark);
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("goalplanner_theme", isDark ? "dark" : "light");
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    const icon = document.getElementById("theme-icon");
    if (icon) {
        icon.setAttribute("data-lucide", isDark ? "sun" : "moon");
        lucide.createIcons();
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");

    let borderClass = "border-blue-500/30 text-blue-300";
    let icon = "info";
    if (type === "success") {
        borderClass = "border-emerald-500/30 text-emerald-300";
        icon = "check-circle";
    } else if (type === "error") {
        borderClass = "border-red-500/30 text-red-300";
        icon = "alert-circle";
    }

    toast.className = `flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-slate-900 border ${borderClass} shadow-xl text-xs font-medium backdrop-blur-md pointer-events-auto transform translate-y-2 opacity-0 transition-all duration-300`;
    toast.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4"></i><span>${message}</span>`;
    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    }, 10);

    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}
