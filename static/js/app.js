// Global Application State
const state = {
    currentYear: new Date().getFullYear(),
    currentMonth: new Date().getMonth() + 1,
    todayDateStr: new Date().toISOString().split("T")[0],
    selectedDateStr: new Date().toISOString().split("T")[0],
    activeView: "matrix",
    tasks: [],
    categories: [],
    goalThreshold: 3,
    streak: 0
};

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initStateFromUI();
    loadCategories().then(() => {
        loadTasks();
    });
    loadThreshold();
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

// ----------------- Categories Management ----------------- //

async function loadCategories() {
    try {
        const res = await fetch("/api/categories");
        const json = await res.json();
        if (json.success) {
            state.categories = json.categories;
            populateCategoryDropdowns();
            renderCategoriesManagerList();
        }
    } catch (err) {
        console.error("Failed to load categories", err);
    }
}

function getCategoryColor(categoryName) {
    const found = state.categories.find(c => c.name.toLowerCase() === categoryName.toLowerCase());
    return found ? found.color : "#3b82f6";
}

function populateCategoryDropdowns(preserveValue = null) {
    const taskCatSelect = document.getElementById("task-category-select");
    if (!taskCatSelect) return;

    const currentVal = preserveValue !== null ? preserveValue : taskCatSelect.value;
    taskCatSelect.innerHTML = "";

    state.categories.forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat.name;
        opt.textContent = `${cat.name}`;
        opt.dataset.color = cat.color;
        taskCatSelect.appendChild(opt);
    });

    if (currentVal && state.categories.some(c => c.name.toLowerCase() === currentVal.toLowerCase())) {
        const matched = state.categories.find(c => c.name.toLowerCase() === currentVal.toLowerCase());
        taskCatSelect.value = matched.name;
    } else if (state.categories.length > 0) {
        taskCatSelect.value = state.categories[0].name;
    }

    onCategorySelectChange(taskCatSelect.value);
}

function renderCategoriesManagerList() {
    const container = document.getElementById("categories-list-container");
    if (!container) return;

    container.innerHTML = "";
    if (state.categories.length === 0) {
        container.innerHTML = `<div class="text-center py-4 text-xs text-slate-500">No categories found. Add one above!</div>`;
        return;
    }

    state.categories.forEach(cat => {
        const row = document.createElement("div");
        row.className = "flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 gap-2";
        row.innerHTML = `
            <div class="flex items-center gap-2.5 flex-1">
                <input type="color" value="${cat.color}" onchange="handleUpdateCategoryColor(${cat.id}, '${cat.name.replace(/'/g, "\\'")}', this.value)" class="w-7 h-7 rounded cursor-pointer bg-transparent border-0 p-0" title="Change color">
                <input type="text" value="${cat.name}" onblur="handleUpdateCategoryName(${cat.id}, this.value, '${cat.color}')" class="bg-transparent text-xs font-semibold text-white px-2 py-1 rounded focus:bg-slate-900 border border-transparent focus:border-slate-700 flex-1">
            </div>
            <button onclick="handleDeleteCategory(${cat.id}, '${cat.name.replace(/'/g, "\\'")}')" class="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-slate-900 transition-colors" title="Delete Category">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
        `;
        container.appendChild(row);
    });
    lucide.createIcons();
}

function openCategoriesModal() {
    document.getElementById("categories-modal").classList.remove("hidden");
    renderCategoriesManagerList();
    lucide.createIcons();
}

function closeCategoriesModal() {
    document.getElementById("categories-modal").classList.add("hidden");
    const currentSelectedCat = document.getElementById("task-category-select") ? document.getElementById("task-category-select").value : null;
    populateCategoryDropdowns(currentSelectedCat);
    loadTasks();
    if (window.loadMatrix) window.loadMatrix();
}

async function handleAddCategory() {
    const nameInput = document.getElementById("new-cat-name");
    const colorInput = document.getElementById("new-cat-color");
    const name = nameInput.value.trim();
    const color = colorInput.value;

    if (!name) {
        showToast("Category name is required", "error");
        return;
    }

    try {
        const res = await fetch("/api/categories", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, color })
        });
        const json = await res.json();
        if (json.success) {
            nameInput.value = "";
            showToast(`Category '${name}' added!`, "success");
            await loadCategories();
        } else {
            showToast(json.error || "Failed to add category", "error");
        }
    } catch (err) {
        showToast("Network error creating category", "error");
    }
}

async function handleUpdateCategoryColor(id, name, color) {
    try {
        const res = await fetch(`/api/categories/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, color })
        });
        const json = await res.json();
        if (json.success) {
            await loadCategories();
            showToast("Category color updated!", "success");
        }
    } catch (err) {
        showToast("Failed to update color", "error");
    }
}

async function handleUpdateCategoryName(id, newName, color) {
    const trimmed = newName.trim();
    if (!trimmed) return;

    try {
        const res = await fetch(`/api/categories/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: trimmed, color })
        });
        const json = await res.json();
        if (json.success) {
            await loadCategories();
            showToast("Category name updated!", "success");
        }
    } catch (err) {
        showToast("Failed to update category name", "error");
    }
}

async function handleDeleteCategory(id, name) {
    if (!confirm(`Are you sure you want to delete category '${name}'?`)) return;

    try {
        const res = await fetch(`/api/categories/${id}`, { method: "DELETE" });
        const json = await res.json();
        if (json.success) {
            showToast("Category deleted", "info");
            await loadCategories();
        } else {
            showToast(json.error || "Cannot delete category", "error");
        }
    } catch (err) {
        showToast("Error deleting category", "error");
    }
}

// ----------------- Goal Threshold Management ----------------- //

async function loadThreshold() {
    try {
        const res = await fetch("/api/settings/threshold");
        const json = await res.json();
        if (json.success) {
            state.goalThreshold = json.threshold;
            const thresholdSelect = document.getElementById("goal-threshold-select");
            if (thresholdSelect) thresholdSelect.value = json.threshold;
            const hint = document.getElementById("threshold-hint-text");
            if (hint) hint.textContent = `${json.threshold} task${json.threshold > 1 ? 's' : ''}`;
        }
    } catch (err) {
        console.error("Failed to load threshold", err);
    }
}

async function updateGoalThreshold(newThreshold) {
    state.goalThreshold = parseInt(newThreshold);
    try {
        const res = await fetch("/api/settings/threshold", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ threshold: state.goalThreshold })
        });
        const json = await res.json();
        if (json.success) {
            showToast(`Goal target updated to ${state.goalThreshold} tasks`, "success");
            const hint = document.getElementById("threshold-hint-text");
            if (hint) hint.textContent = `${state.goalThreshold} task${state.goalThreshold > 1 ? 's' : ''}`;
            if (window.loadMatrix) window.loadMatrix();
            if (state.activeView === "today") loadTodayChecklist();
        } else {
            showToast(json.error || "Failed to update threshold", "error");
        }
    } catch (err) {
        showToast("Network error updating goal target", "error");
    }
}

// ----------------- View Navigation ----------------- //

function switchView(viewName) {
    state.activeView = viewName;

    document.querySelectorAll(".view-tab").forEach(tab => {
        tab.classList.remove("text-white", "bg-blue-600", "shadow-sm");
        tab.classList.add("text-slate-400");
    });

    const activeTab = document.getElementById(`view-tab-${viewName}`);
    if (activeTab) {
        activeTab.classList.remove("text-slate-400");
        activeTab.classList.add("text-white", "bg-blue-600", "shadow-sm");
    }

    document.getElementById("view-matrix").classList.toggle("hidden", viewName !== "matrix");
    document.getElementById("view-heatmap").classList.toggle("hidden", viewName !== "heatmap");
    document.getElementById("view-today").classList.toggle("hidden", viewName !== "today");
    document.getElementById("view-yearly").classList.toggle("hidden", viewName !== "yearly");

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
        const tTitle = task.title.trim().toLowerCase();
        if (tTitle === "goal" || tTitle === "full day") return;
        const opt = document.createElement("option");
        opt.value = task.id;
        opt.textContent = `${task.title} (${task.category})`;
        select.appendChild(opt);
    });
    select.value = currentVal || "all";
}

function onCategorySelectChange(category) {
    const color = getCategoryColor(category);
    const dot = document.getElementById("category-preview-dot");
    if (dot) dot.style.backgroundColor = color;
}

function openAddTaskModal() {
    document.getElementById("task-modal-title").innerHTML = '<i data-lucide="plus-circle" class="w-5 h-5 text-blue-400"></i> Add New Task';
    document.getElementById("task-id-input").value = "";
    document.getElementById("task-title-input").value = "";
    document.getElementById("task-title-input").disabled = false;
    document.getElementById("task-delete-btn").classList.add("hidden");

    populateCategoryDropdowns();
    document.getElementById("task-modal").classList.remove("hidden");
    lucide.createIcons();
}

function openEditTaskModal(task) {
    const tClean = task.title.trim().toLowerCase();
    if (tClean === "goal" || tClean === "full day") {
        showToast(`The '${task.title}' task is a system task and cannot be edited.`, "info");
        return;
    }

    document.getElementById("task-modal-title").innerHTML = '<i data-lucide="edit-3" class="w-5 h-5 text-blue-400"></i> Edit Task';
    document.getElementById("task-id-input").value = task.id;
    document.getElementById("task-title-input").value = task.title;
    document.getElementById("task-title-input").disabled = false;
    document.getElementById("task-delete-btn").classList.remove("hidden");

    populateCategoryDropdowns();
    const catSelect = document.getElementById("task-category-select");
    if (catSelect && task.category) {
        catSelect.value = task.category;
    }
    onCategorySelectChange(catSelect ? catSelect.value : "");

    document.getElementById("task-modal").classList.remove("hidden");
    lucide.createIcons();
}

function closeTaskModal() {
    document.getElementById("task-modal").classList.add("hidden");
}

async function handleTaskSubmit(event) {
    event.preventDefault();
    const taskId = document.getElementById("task-id-input").value;
    const title = document.getElementById("task-title-input").value.trim();
    const category = document.getElementById("task-category-select").value;

    if (title.toLowerCase() === "goal") {
        showToast("Cannot create or rename task to 'Goal' — it is reserved.", "error");
        return;
    }

    const payload = { title, category };

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

    if (!confirm("Are you sure you want to remove this task?")) {
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
        } else {
            showToast(data.error || "Could not delete task", "error");
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

    const options = { weekday: "long", month: "short", day: "numeric", year: "numeric" };
    document.getElementById("today-header-date").textContent = isToday ? "Today" : d.toLocaleDateString(undefined, { weekday: "long" });
    document.getElementById("today-sub-date").textContent = d.toLocaleDateString(undefined, options);

    container.innerHTML = '<div class="text-center py-6 text-slate-500">Loading tasks...</div>';

    try {
        const year = d.getFullYear();
        const month = d.getMonth() + 1;
        const res = await fetch(`/api/matrix?year=${year}&month=${month}`);
        const json = await res.json();

        if (!json.success) return;

        const matrixData = json.data;
        const dayIdx = d.getDate() - 1;
        const threshold = matrixData.goal_threshold || 3;

        let regularCompleted = 0;
        let regularTotal = 0;
        let goalIsCompleted = false;
        let fullDayIsCompleted = false;

        matrixData.matrix.forEach(row => {
            const tTitle = row.task.title.trim().toLowerCase();
            const isDone = Boolean(row.cells[dayIdx]);
            if (tTitle === "goal") {
                goalIsCompleted = isDone;
            } else if (tTitle === "full day") {
                fullDayIsCompleted = isDone;
            } else {
                regularTotal++;
                if (isDone) regularCompleted++;
            }
        });

        const pct = regularTotal > 0 ? Math.round((regularCompleted / regularTotal) * 100) : 0;
        updateProgressRing(regularCompleted, regularTotal, pct);

        container.innerHTML = "";

        // Render Goal Card at top (Non-clickable, automatic)
        const goalCard = document.createElement("div");
        goalCard.className = `p-4 rounded-2xl border transition-all ${
            goalIsCompleted 
            ? "bg-amber-500/10 border-amber-500/40 shadow-lg shadow-amber-500/10" 
            : "bg-slate-900/60 border-slate-800"
        }`;
        
        const goalStatusSubtext = goalIsCompleted 
            ? (fullDayIsCompleted ? '🎉 Goal achieved via Full Day focus!' : '🎉 Target reached! Main goal achieved.')
            : (fullDayIsCompleted 
                ? 'Check 1 task to complete your Full Day goal.' 
                : `Complete any ${threshold} tasks (or check Full Day with 1 task) to achieve.`);

        goalCard.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-xl ${goalIsCompleted ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-amber-400'} flex items-center justify-center font-bold">
                        <i data-lucide="crown" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="font-bold text-sm text-white flex items-center gap-1.5">
                            Daily Goal
                            <span class="text-[10px] px-1.5 py-0.5 rounded-full ${goalIsCompleted ? 'bg-amber-400 text-slate-950 font-bold' : 'bg-slate-800 text-slate-400'}">
                                ${goalIsCompleted ? 'ACHIEVED' : `${regularCompleted}/${threshold} tasks`}
                            </span>
                        </div>
                        <div class="text-[11px] text-slate-400">
                            ${goalStatusSubtext}
                        </div>
                    </div>
                </div>
                <input type="checkbox" ${goalIsCompleted ? 'checked' : ''} disabled class="matrix-checkbox pointer-events-none opacity-90" style="${goalIsCompleted ? 'background-color: #eab308; border-color: #eab308;' : ''}">
            </div>
        `;
        container.appendChild(goalCard);

        matrixData.matrix.forEach(row => {
            const task = row.task;
            if (row.is_goal || task.title.trim().toLowerCase() === "goal") return;

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
                        <div class="text-[11px] text-slate-400">${task.category}</div>
                    </div>
                </div>
                <input type="checkbox" ${isCompleted ? 'checked' : ''} class="matrix-checkbox pointer-events-none" style="${isCompleted ? `background-color: ${task.color}; border-color: ${task.color};` : ''}">
            `;

            card.onclick = () => toggleTodayItem(task.id, isCompleted);
            container.appendChild(card);
        });

        lucide.createIcons();

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
    const circumference = 163.36;
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
                isBest ? 'bg-gradient-to-br from-amber-900/20 to-slate-900 border-amber-500/40 shadow-lg' : 'bg-slate-900 border-slate-800 hover:border-slate-700'
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
                    ${isBest ? '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">🏆 Best Month</span>' : ''}
                </div>
                <div class="text-2xl font-black text-white mt-1">${m.completion_rate}%</div>
                <div class="text-xs text-slate-400 mt-0.5">${m.completions} of ${m.max_possible} tasks</div>
                <div class="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                    <div class="bg-amber-400 h-full rounded-full transition-all duration-500" style="width: ${m.completion_rate}%"></div>
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
            await loadCategories();
            loadTasks();
            loadThreshold();
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
