let currentMatrixData = null;

async function loadMatrix() {
    const table = document.getElementById("matrix-table");
    if (!table) return;

    const year = state.currentYear;
    const month = state.currentMonth;

    table.innerHTML = `
        <tbody>
            <tr>
                <td class="text-center py-16 text-slate-500">
                    <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-2"></div>
                    <div>Loading monthly matrix...</div>
                </td>
            </tr>
        </tbody>
    `;

    try {
        const res = await fetch(`/api/matrix?year=${year}&month=${month}`);
        const json = await res.json();
        if (!json.success) {
            table.innerHTML = `<tbody><tr><td class="text-center py-12 text-red-400">${json.error}</td></tr></tbody>`;
            return;
        }

        currentMatrixData = json.data;

        // Sync threshold select with backend setting
        if (currentMatrixData.goal_threshold) {
            const thresholdSelect = document.getElementById("goal-threshold-select");
            if (thresholdSelect) thresholdSelect.value = currentMatrixData.goal_threshold;
            const hint = document.getElementById("threshold-hint-text");
            if (hint) hint.textContent = `${currentMatrixData.goal_threshold} task${currentMatrixData.goal_threshold > 1 ? 's' : ''}`;
        }

        renderMatrix(currentMatrixData);

        // Update last updated text
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const lastUpdatedEl = document.getElementById("matrix-last-updated");
        if (lastUpdatedEl) lastUpdatedEl.textContent = `Synced at ${timeStr}`;

        // Also refresh heatmap & streaks in background
        if (window.loadHeatmap) window.loadHeatmap(false);

    } catch (err) {
        console.error("Error loading matrix:", err);
        table.innerHTML = `<tbody><tr><td class="text-center py-12 text-red-400">Failed to load matrix data</td></tr></tbody>`;
    }
}

function renderMatrix(data) {
    const table = document.getElementById("matrix-table");
    const numDays = data.num_days;
    const days = data.days;
    const taskRows = data.matrix;

    let html = "";

    // 1. THEAD: Date Headers
    html += `<thead><tr class="bg-slate-900 border-b border-slate-800">`;
    
    // Top-Left Sticky Corner
    html += `
        <th class="sticky-top-left bg-slate-900 border-r border-slate-800 p-2.5 min-w-[200px] max-w-[220px] text-xs font-bold text-slate-300">
            <div class="flex items-center justify-between">
                <span class="text-amber-400 font-extrabold tracking-wide uppercase">${data.month_name.slice(0, 3)} ${data.year}</span>
                <span class="text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800 font-medium">${taskRows.length} Habits</span>
            </div>
        </th>
    `;

    // Days 1..N
    days.forEach(d => {
        const weekendClass = d.is_weekend ? "weekend-header text-amber-400/90 font-semibold" : "text-slate-300";
        const todayClass = d.is_today ? "today-header text-blue-400 font-black ring-1 ring-blue-500/50" : "";
        
        html += `
            <th class="sticky-header bg-slate-900 border-r border-slate-800/60 text-center p-1.5 min-w-[34px] max-w-[38px] ${weekendClass} ${todayClass}" title="${d.date} (${d.day_of_week})">
                <div class="text-[10px] uppercase tracking-tighter opacity-70 leading-none">${d.day_letter}</div>
                <div class="text-xs font-bold mt-0.5 leading-none">${d.day}</div>
            </th>
        `;
    });

    // Top-Right Sticky Corner (Total Days)
    html += `
        <th class="sticky-summary-header bg-slate-900 border-l border-slate-800 p-2 min-w-[70px] text-center text-xs font-bold text-slate-300">
            Total
        </th>
    </tr></thead>`;

    // 2. TBODY: Task Rows
    html += `<tbody id="matrix-tbody" class="divide-y divide-slate-800/60">`;

    taskRows.forEach((row, rowIndex) => {
        const task = row.task;
        const isGoalTask = row.is_goal || task.title.trim().toLowerCase() === "goal";
        const isFullDayTask = row.is_full_day || task.title.trim().toLowerCase() === "full day";
        const isFixedRow = isGoalTask || isFullDayTask;
        
        let rowClass = "hover:bg-slate-800/30";
        if (isGoalTask) {
            rowClass = "goal-row bg-amber-500/[0.04]";
        } else if (isFullDayTask) {
            rowClass = "bg-amber-500/[0.02] hover:bg-amber-500/[0.05]";
        }

        const draggableAttr = !isFixedRow 
            ? `draggable="true" data-task-id="${task.id}" data-row-index="${rowIndex}" ondragstart="onTaskDragStart(event)" ondragover="onTaskDragOver(event)" ondragleave="onTaskDragLeave(event)" ondrop="onTaskDrop(event)" ondragend="onTaskDragEnd(event)"` 
            : `data-task-id="${task.id}" data-row-index="${rowIndex}" ondragover="onFixedRowDragOver(event)" ondragleave="onFixedRowDragLeave(event)" ondrop="onFixedRowDrop(event)"`;

        html += `<tr id="task-row-${task.id}" class="${rowClass} transition-colors group select-none" ${draggableAttr}>`;

        // Left Sticky Cell: Task Title, Grip Handle & Meta
        html += `
            <td class="sticky-col bg-slate-900 group-hover:bg-slate-800/80 border-r border-slate-800 p-2.5 transition-colors">
                <div class="flex items-center justify-between gap-1.5">
                    <div class="flex items-center gap-2 overflow-hidden flex-1">
                        ${!isFixedRow ? `
                        <div class="drag-handle p-1 text-slate-500 hover:text-white rounded transition-colors flex items-center justify-center opacity-40 group-hover:opacity-100" title="Drag to reorder task position">
                            <i data-lucide="grip-vertical" class="w-3.5 h-3.5"></i>
                        </div>
                        ` : ''}
                        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${task.color || '#eab308'}"></span>
                        <div class="truncate flex-1">
                            <span class="font-bold text-xs sm:text-sm ${isGoalTask ? 'text-amber-400 font-black flex items-center gap-1' : (isFullDayTask ? 'text-amber-300 font-bold flex items-center gap-1' : 'text-slate-100')}">
                                ${isGoalTask ? '<i data-lucide="crown" class="w-3.5 h-3.5 text-amber-400 inline"></i>' : ''}
                                ${isFullDayTask ? '<i data-lucide="sun" class="w-3.5 h-3.5 text-amber-400 inline"></i>' : ''}
                                ${task.title}
                            </span>
                            ${!isFixedRow ? `<span class="text-[10px] text-slate-400 block truncate">${task.category || 'General'}</span>` : ''}
                        </div>
                    </div>
                    ${!isFixedRow ? `
                    <button draggable="false" onclick='openEditTaskModal(${JSON.stringify(task).replace(/'/g, "&apos;")})' class="opacity-0 group-hover:opacity-100 p-1 hover:text-white text-slate-400 rounded transition-opacity" title="Edit Task">
                        <i data-lucide="more-horizontal" class="w-3.5 h-3.5"></i>
                    </button>
                    ` : (isGoalTask ? `
                    <span class="text-[10px] text-amber-500/80 px-1 py-0.5 rounded bg-amber-500/10 font-medium" title="Auto-ticks when target is met or Full Day is checked">Auto</span>
                    ` : `
                    <span class="text-[10px] text-amber-400/80 px-1 py-0.5 rounded bg-amber-400/10 font-medium" title="If checked with >=1 task done, Goal counts as achieved">1-Task</span>
                    `)}
                </div>
            </td>
        `;

        // Checkbox Cells for Days 1..N
        days.forEach((d, dayIndex) => {
            const isDone = row.cells[dayIndex] || false;
            const weekendCellClass = d.is_weekend ? "weekend-cell" : "";
            const todayCellClass = d.is_today ? "today-cell" : "";

            if (isGoalTask) {
                // Goal task cannot be manually clicked; it is disabled with special goal styling
                html += `
                    <td class="text-center p-0 border-r border-slate-800/60 ${weekendCellClass} ${todayCellClass}">
                        <div class="w-full h-full py-1.5 px-0.5 flex items-center justify-center">
                            <input type="checkbox" 
                                draggable="false"
                                id="goal-cell-${dayIndex}"
                                class="matrix-checkbox goal-checkbox cursor-not-allowed opacity-90" 
                                ${isDone ? "checked" : ""} 
                                disabled
                                style="${isDone ? `background-color: #eab308; border-color: #eab308; box-shadow: 0 0 10px rgba(234, 179, 8, 0.45);` : ''}"
                                title="Goal on ${d.date}: ${isDone ? 'Achieved!' : 'Complete threshold tasks or Full Day to achieve'}">
                        </div>
                    </td>
                `;
            } else if (isFullDayTask) {
                // Full Day checkbox (actionable)
                html += `
                    <td class="text-center p-0 border-r border-slate-800/60 ${weekendCellClass} ${todayCellClass}">
                        <div class="w-full h-full py-1.5 px-0.5 flex items-center justify-center">
                            <input type="checkbox" 
                                draggable="false"
                                id="fullday-cell-${dayIndex}"
                                class="matrix-checkbox" 
                                ${isDone ? "checked" : ""} 
                                data-task-id="${task.id}" 
                                data-date="${d.date}" 
                                data-row-index="${rowIndex}" 
                                data-day-index="${dayIndex}"
                                onchange="onMatrixCellChange(this)"
                                style="${isDone ? `background-color: #f59e0b; border-color: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.4);` : ''}"
                                title="Full Day on ${d.date}: ${isDone ? 'Marked' : 'Check if 1 major task took the entire day'}">
                        </div>
                    </td>
                `;
            } else {
                html += `
                    <td class="text-center p-0 border-r border-slate-800/60 ${weekendCellClass} ${todayCellClass}">
                        <div class="w-full h-full py-1.5 px-0.5 flex items-center justify-center">
                            <input type="checkbox" 
                                draggable="false"
                                class="matrix-checkbox" 
                                ${isDone ? "checked" : ""} 
                                data-task-id="${task.id}" 
                                data-date="${d.date}" 
                                data-row-index="${rowIndex}" 
                                data-day-index="${dayIndex}"
                                onchange="onMatrixCellChange(this)"
                                style="${isDone ? `background-color: ${task.color || '#3b82f6'}; border-color: ${task.color || '#3b82f6'};` : ''}"
                                title="${task.title} on ${d.date}">
                        </div>
                    </td>
                `;
            }
        });

        // Right Sticky Cell: Row Total with fraction (e.g. 4/31)
        html += `
            <td id="row-total-${rowIndex}" class="sticky-summary-col bg-slate-900 group-hover:bg-slate-800/80 border-l border-slate-800 p-2 text-center text-xs font-semibold text-slate-200">
                <span class="font-bold ${isGoalTask ? 'text-amber-400' : 'text-white'} text-sm">${row.total_completed}</span>
                <span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>
            </td>
        `;

        html += `</tr>`;
    });

    html += `</tbody></table>`;
    table.innerHTML = html;
    lucide.createIcons();
}

async function onMatrixCellChange(checkbox) {
    const taskId = parseInt(checkbox.dataset.taskId);
    const dateStr = checkbox.dataset.date;
    const rowIndex = parseInt(checkbox.dataset.rowIndex);
    const dayIndex = parseInt(checkbox.dataset.dayIndex);
    const isChecked = checkbox.checked;

    const task = currentMatrixData.matrix[rowIndex].task;
    if (isChecked) {
        checkbox.style.backgroundColor = task.color || "#3b82f6";
        checkbox.style.borderColor = task.color || "#3b82f6";
    } else {
        checkbox.style.backgroundColor = "transparent";
        checkbox.style.borderColor = "rgba(148, 163, 184, 0.4)";
    }

    // Update memory representation for this task
    currentMatrixData.matrix[rowIndex].cells[dayIndex] = isChecked;

    // Recalculate row total count only
    let newRowTotal = 0;
    currentMatrixData.matrix[rowIndex].cells.forEach(c => {
        if (c) newRowTotal++;
    });
    currentMatrixData.matrix[rowIndex].total_completed = newRowTotal;

    const rowTotalCell = document.getElementById(`row-total-${rowIndex}`);
    if (rowTotalCell) {
        rowTotalCell.innerHTML = `<span class="font-bold text-white text-sm">${newRowTotal}</span><span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>`;
    }

    // Evaluate Goal auto-tick on client side for instantaneous UI feedback
    const threshold = currentMatrixData.goal_threshold || 3;
    let regularDoneOnThisDay = 0;
    let isFullDayCheckedOnThisDay = false;
    let goalRowIndex = -1;

    currentMatrixData.matrix.forEach((r, idx) => {
        const tTitle = r.task.title.trim().toLowerCase();
        if (tTitle === "goal") {
            goalRowIndex = idx;
        } else if (tTitle === "full day") {
            isFullDayCheckedOnThisDay = Boolean(r.cells[dayIndex]);
        } else {
            if (r.cells[dayIndex]) regularDoneOnThisDay++;
        }
    });

    // Goal is done if:
    // 1. Regular tasks completed >= threshold, OR
    // 2. Full Day is checked AND at least 1 regular task is completed!
    const shouldGoalBeDone = (regularDoneOnThisDay >= threshold) || (isFullDayCheckedOnThisDay && regularDoneOnThisDay >= 1);

    if (goalRowIndex !== -1) {
        currentMatrixData.matrix[goalRowIndex].cells[dayIndex] = shouldGoalBeDone;
        
        const goalCheckbox = document.getElementById(`goal-cell-${dayIndex}`);
        if (goalCheckbox) {
            goalCheckbox.checked = shouldGoalBeDone;
            if (shouldGoalBeDone) {
                goalCheckbox.style.backgroundColor = "#eab308";
                goalCheckbox.style.borderColor = "#eab308";
                goalCheckbox.style.boxShadow = "0 0 10px rgba(234, 179, 8, 0.45)";
            } else {
                goalCheckbox.style.backgroundColor = "transparent";
                goalCheckbox.style.borderColor = "rgba(148, 163, 184, 0.4)";
                goalCheckbox.style.boxShadow = "none";
            }
        }

        let goalTotal = 0;
        currentMatrixData.matrix[goalRowIndex].cells.forEach(c => {
            if (c) goalTotal++;
        });
        currentMatrixData.matrix[goalRowIndex].total_completed = goalTotal;

        const goalRowTotalCell = document.getElementById(`row-total-${goalRowIndex}`);
        if (goalRowTotalCell) {
            goalRowTotalCell.innerHTML = `<span class="font-bold text-amber-400 text-sm">${goalTotal}</span><span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>`;
        }
    }

    try {
        const res = await fetch("/api/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                task_id: taskId,
                date: dateStr,
                state: isChecked
            })
        });
        const json = await res.json();
        if (!json.success) {
            showToast(json.error || "Failed to save checkmark", "error");
            checkbox.checked = !isChecked;
        } else {
            // Silently update heatmap and streak in background
            if (window.loadHeatmap) window.loadHeatmap(false);
        }
    } catch (err) {
        showToast("Network error syncing task", "error");
        checkbox.checked = !isChecked;
    }
}

// ----------------- Drag & Drop Row Reordering ----------------- //
let draggedTaskId = null;

function onTaskDragStart(e) {
    if (e.target.tagName === 'INPUT' || e.target.closest('button')) {
        e.preventDefault();
        return false;
    }
    const row = e.currentTarget;
    draggedTaskId = parseInt(row.dataset.taskId);
    if (!draggedTaskId) return;

    row.classList.add('dragging-row');
    if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(draggedTaskId));
    }
}

function onTaskDragOver(e) {
    e.preventDefault(); // Required for drop event to fire
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';

    const row = e.currentTarget;
    const targetTaskId = parseInt(row.dataset.taskId);
    if (!targetTaskId || targetTaskId === draggedTaskId) return;

    row.classList.remove('drag-over-top', 'drag-over-bottom');
    const rect = row.getBoundingClientRect();
    const isAfter = (e.clientY - rect.top) > (rect.height / 2);
    if (isAfter) {
        row.classList.add('drag-over-bottom');
    } else {
        row.classList.add('drag-over-top');
    }
}

function onTaskDragLeave(e) {
    const row = e.currentTarget;
    row.classList.remove('drag-over-top', 'drag-over-bottom');
}

function onTaskDragEnd(e) {
    draggedTaskId = null;
    document.querySelectorAll('#matrix-tbody tr').forEach(r => {
        r.classList.remove('dragging-row', 'drag-over-top', 'drag-over-bottom');
    });
}

async function onTaskDrop(e) {
    e.preventDefault();
    const row = e.currentTarget;
    const targetTaskId = parseInt(row.dataset.taskId);
    const sourceTaskId = draggedTaskId || (e.dataTransfer ? parseInt(e.dataTransfer.getData('text/plain')) : null);

    document.querySelectorAll('#matrix-tbody tr').forEach(r => {
        r.classList.remove('dragging-row', 'drag-over-top', 'drag-over-bottom');
    });

    if (!sourceTaskId || !targetTaskId || sourceTaskId === targetTaskId) return;

    const rect = row.getBoundingClientRect();
    const isAfter = (e.clientY - rect.top) > (rect.height / 2);

    if (!currentMatrixData || !currentMatrixData.matrix) return;
    const regularTasks = currentMatrixData.matrix
        .filter(r => {
            const title = r.task.title.trim().toLowerCase();
            return title !== 'goal' && title !== 'full day';
        })
        .map(r => r.task);

    const fromIdx = regularTasks.findIndex(t => t.id === sourceTaskId);
    const toIdx = regularTasks.findIndex(t => t.id === targetTaskId);
    if (fromIdx === -1 || toIdx === -1) return;

    const [movedTask] = regularTasks.splice(fromIdx, 1);
    let insertIdx = regularTasks.findIndex(t => t.id === targetTaskId);
    if (isAfter) insertIdx += 1;
    regularTasks.splice(insertIdx, 0, movedTask);

    const orderedIds = regularTasks.map(t => t.id);

    try {
        const res = await fetch('/api/tasks/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_ids: orderedIds })
        });
        const json = await res.json();
        if (json.success) {
            if (window.loadTasks) await window.loadTasks();
            await loadMatrix();
            showToast("Task reordered successfully", "success");
        } else {
            showToast(json.error || "Failed to reorder task", "error");
        }
    } catch (err) {
        console.error("Reorder error:", err);
        showToast("Error updating task order", "error");
    }
}

function onFixedRowDragOver(e) {
    if (!draggedTaskId) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    const row = e.currentTarget;
    row.classList.add('drag-over-bottom');
}

function onFixedRowDragLeave(e) {
    e.currentTarget.classList.remove('drag-over-bottom');
}

async function onFixedRowDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over-bottom');
    const sourceTaskId = draggedTaskId || (e.dataTransfer ? parseInt(e.dataTransfer.getData('text/plain')) : null);
    if (!sourceTaskId) return;

    if (!currentMatrixData || !currentMatrixData.matrix) return;
    const regularTasks = currentMatrixData.matrix
        .filter(r => {
            const title = r.task.title.trim().toLowerCase();
            return title !== 'goal' && title !== 'full day';
        })
        .map(r => r.task);

    const fromIdx = regularTasks.findIndex(t => t.id === sourceTaskId);
    if (fromIdx === -1) return;

    // Move to top of regular tasks list (right below Full Day)
    const [movedTask] = regularTasks.splice(fromIdx, 1);
    regularTasks.unshift(movedTask);

    const orderedIds = regularTasks.map(t => t.id);

    try {
        const res = await fetch('/api/tasks/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_ids: orderedIds })
        });
        const json = await res.json();
        if (json.success) {
            if (window.loadTasks) await window.loadTasks();
            await loadMatrix();
            showToast("Task moved to top", "success");
        } else {
            showToast(json.error || "Failed to reorder task", "error");
        }
    } catch (err) {
        console.error("Reorder error:", err);
        showToast("Error updating task order", "error");
    }
}

window.loadMatrix = loadMatrix;
window.onTaskDragStart = onTaskDragStart;
window.onTaskDragOver = onTaskDragOver;
window.onTaskDragLeave = onTaskDragLeave;
window.onTaskDragEnd = onTaskDragEnd;
window.onTaskDrop = onTaskDrop;
window.onFixedRowDragOver = onFixedRowDragOver;
window.onFixedRowDragLeave = onFixedRowDragLeave;
window.onFixedRowDrop = onFixedRowDrop;
