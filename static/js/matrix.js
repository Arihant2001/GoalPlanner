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
            if (json.requires_login && window.showAuthModal) {
                window.showAuthModal();
                return;
            }
            table.innerHTML = `<tbody><tr><td class="text-center py-12 text-red-400">${json.error}</td></tr></tbody>`;
            return;
        }

        currentMatrixData = json.data;

        // Preserve custom habit order from local storage cache across load and sign in
        const savedOrderKey = `goalplanner_habit_order_${state.user?.id || 'default'}`;
        const savedOrderStr = localStorage.getItem(savedOrderKey);
        if (savedOrderStr && currentMatrixData && currentMatrixData.matrix) {
            try {
                const savedOrder = JSON.parse(savedOrderStr);
                if (Array.isArray(savedOrder) && savedOrder.length > 0) {
                    const fixedRows = currentMatrixData.matrix.filter(r => {
                        const t = r.task.title.trim().toLowerCase();
                        return t === "goal" || t === "full day";
                    });
                    const regularRows = currentMatrixData.matrix.filter(r => {
                        const t = r.task.title.trim().toLowerCase();
                        return t !== "goal" && t !== "full day" && !r.task.parent_id;
                    });
                    const subtaskRows = currentMatrixData.matrix.filter(r => Boolean(r.task.parent_id));

                    regularRows.sort((a, b) => {
                        const idxA = savedOrder.indexOf(a.task.id);
                        const idxB = savedOrder.indexOf(b.task.id);
                        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                        if (idxA !== -1) return -1;
                        if (idxB !== -1) return 1;
                        return (a.task.sort_order || 0) - (b.task.sort_order || 0);
                    });

                    const reassembled = [...fixedRows];
                    regularRows.forEach(parent => {
                        reassembled.push(parent);
                        const children = subtaskRows.filter(s => s.task.parent_id === parent.task.id);
                        reassembled.push(...children);
                    });
                    currentMatrixData.matrix = reassembled;
                }
            } catch (e) {
                console.warn("Failed to apply saved habit order:", e);
            }
        }

        // Sync threshold select with backend setting
        if (currentMatrixData.goal_threshold) {
            const thresholdSelect = document.getElementById("goal-threshold-select");
            if (thresholdSelect) thresholdSelect.value = currentMatrixData.goal_threshold;
        }

        renderMatrix(currentMatrixData);

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
    const regularHabits = taskRows.filter(r => !r.is_goal && !r.is_full_day);

    let html = "";

    // 0. COLGROUP: Explicit Column Geometry
    html += `<colgroup>`;
    html += `<col style="width: 220px; min-width: 220px; max-width: 220px;">`;
    days.forEach(() => {
        html += `<col style="width: 36px; min-width: 36px; max-width: 36px;">`;
    });
    html += `<col style="width: 70px; min-width: 70px; max-width: 70px;">`;
    html += `</colgroup>`;

    // 1. THEAD: Header Block (Date Headers + Goal + Full Day)
    html += `<thead>`;

    // Row 1: Date Headers
    html += `<tr class="bg-slate-900 border-b border-slate-800">`;
    html += `
        <th class="sticky-top-left bg-slate-900 border-r border-b border-slate-800 p-2.5 text-xs font-bold text-slate-300">
            <div class="flex items-center justify-between">
                <span class="text-amber-400 font-extrabold tracking-wide uppercase">${data.month_name.slice(0, 3)} ${data.year}</span>
                <span class="text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800 font-medium">${regularHabits.length} Habits</span>
            </div>
        </th>
    `;
    days.forEach(d => {
        const weekendClass = d.is_weekend ? "weekend-header text-amber-400/90 font-semibold" : "text-slate-300";
        const todayClass = d.is_today ? "today-header text-blue-400 font-black" : "";
        html += `
            <th class="sticky-header bg-slate-900 border-r border-b border-slate-800/60 text-center p-1.5 ${weekendClass} ${todayClass}" title="${d.date} (${d.day_of_week})">
                <div class="text-[10px] uppercase tracking-tighter opacity-70 leading-none">${d.day_letter}</div>
                <div class="text-xs font-bold mt-0.5 leading-none">${d.day}</div>
            </th>
        `;
    });
    html += `
        <th class="sticky-summary-header bg-slate-900 border-l border-b border-slate-800 p-2 text-center text-xs font-bold text-slate-300">
            Total
        </th>
    </tr>`;

    // Render fixed Goal and Full Day rows inside thead!
    taskRows.forEach((row, rowIndex) => {
        const task = row.task;
        const isGoalTask = row.is_goal || task.title.trim().toLowerCase() === "goal";
        const isFullDayTask = row.is_full_day || task.title.trim().toLowerCase() === "full day";
        if (!isGoalTask && !isFullDayTask) return;

        const rowClass = isGoalTask ? "goal-row" : "fullday-row";
        const leftStickyClass = isGoalTask ? "sticky-goal-left border-r border-b border-slate-800" : "sticky-fullday-left border-r border-b-2 border-slate-700/80";
        const cellStickyClass = isGoalTask ? "sticky-goal-cell border-r border-b border-slate-800/60" : "sticky-fullday-cell border-r border-b-2 border-slate-700/80";
        const rightStickyClass = isGoalTask ? "sticky-goal-summary border-l border-b border-slate-800" : "sticky-fullday-summary border-l border-b-2 border-slate-700/80";

        html += `<tr id="task-row-${task.id}" class="${rowClass} transition-colors group select-none" data-task-id="${task.id}" data-row-index="${rowIndex}" ondragover="onFixedRowDragOver(event)" ondragleave="onFixedRowDragLeave(event)" ondrop="onFixedRowDrop(event)">`;

        // Left Sticky Cell: Task Title, Icon & Meta
        html += `
            <td class="${leftStickyClass} p-2.5 transition-colors">
                <div class="flex items-center justify-between gap-1.5">
                    <div class="flex items-center gap-2 overflow-hidden flex-1">
                        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${task.color || (isGoalTask ? '#eab308' : '#f59e0b')}"></span>
                        <div class="truncate flex-1">
                            <span class="font-bold text-xs sm:text-sm ${isGoalTask ? 'text-amber-400 font-black flex items-center gap-1' : 'text-amber-300 font-bold flex items-center gap-1'}">
                                ${isGoalTask ? '<i data-lucide="target" class="w-3.5 h-3.5 text-amber-400 inline"></i>' : '<i data-lucide="sun" class="w-3.5 h-3.5 text-amber-400 inline"></i>'}
                                ${task.title}
                            </span>
                        </div>
                    </div>
                    ${isGoalTask ? `
                    <span class="text-[10px] text-amber-500/80 px-1 py-0.5 rounded bg-amber-500/10 font-medium" title="Auto-ticks when target is met or Full Day is checked">Auto</span>
                    ` : `
                    <span class="text-[10px] text-amber-400/80 px-1 py-0.5 rounded bg-amber-400/10 font-medium" title="If checked with >=1 task done, Goal counts as achieved">1-Task</span>
                    `}
                </div>
            </td>
        `;

        // Checkbox Cells for Days 1..N
        days.forEach((d, dayIndex) => {
            const isDone = row.cells[dayIndex] || false;
            if (isGoalTask) {
                html += `
                    <td class="text-center p-0 matrix-day-cell ${cellStickyClass}">
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
            } else {
                let regDone = 0;
                taskRows.forEach(tr => {
                    const t = tr.task.title.trim().toLowerCase();
                    if (t !== "goal" && t !== "full day" && !tr.task.parent_id) {
                        if (tr.cells[dayIndex]) regDone++;
                    }
                });
                const canCheckFullDay = regDone >= 1;
                const isFullDayActive = isDone && canCheckFullDay;

                html += `
                    <td class="text-center p-0 matrix-day-cell ${cellStickyClass}">
                        <div class="w-full h-full py-1.5 px-0.5 flex items-center justify-center">
                            <input type="checkbox" 
                                draggable="false"
                                id="fullday-cell-${dayIndex}"
                                class="matrix-checkbox ${canCheckFullDay ? 'cursor-pointer' : 'cursor-not-allowed opacity-30'}" 
                                ${isFullDayActive ? "checked" : ""} 
                                ${canCheckFullDay ? "" : "disabled"}
                                data-task-id="${task.id}" 
                                data-date="${d.date}" 
                                data-row-index="${rowIndex}" 
                                data-day-index="${dayIndex}"
                                onchange="onMatrixCellChange(this)"
                                style="${isFullDayActive ? `background-color: #f59e0b; border-color: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.4);` : ''}"
                                title="${canCheckFullDay ? `Full Day on ${d.date}: ${isFullDayActive ? 'Marked' : 'Check if 1 major habit took the entire day'}` : 'Check at least 1 habit first before marking Full Day'}">
                        </div>
                    </td>
                `;
            }
        });

        // Right Summary Cell
        html += `
            <td id="row-total-${rowIndex}" class="${rightStickyClass} p-2 text-center text-xs font-semibold text-slate-200">
                <span class="font-bold ${isGoalTask ? 'text-amber-400' : 'text-amber-500'} text-sm">${row.total_completed}</span>
                <span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>
            </td>
        </tr>`;
    });

    html += `</thead>`;

    // 2. TBODY: Regular Habit Rows
    html += `<tbody id="matrix-tbody" class="divide-y divide-slate-800/60">`;

    taskRows.forEach((row, rowIndex) => {
        const task = row.task;
        const isGoalTask = row.is_goal || task.title.trim().toLowerCase() === "goal";
        const isFullDayTask = row.is_full_day || task.title.trim().toLowerCase() === "full day";
        if (isGoalTask || isFullDayTask) return; // Already rendered in thead!

        const isSubtask = Boolean(row.is_subtask || task.parent_id);
        const rowClass = isSubtask ? "subtask-row select-none" : "hover:bg-slate-800/30 select-none";
        const leftStickyClass = isSubtask 
            ? "sticky-col border-r border-b border-slate-800/60" 
            : "sticky-col border-r border-b border-slate-800/60 bg-slate-900 group-hover:bg-slate-800/80";
        const cellStickyClass = "border-r border-b border-slate-800/60";
        const rightStickyClass = isSubtask 
            ? "sticky-summary-col border-l border-b border-slate-800/60" 
            : "sticky-summary-col border-l border-b border-slate-800/60 bg-slate-900 group-hover:bg-slate-800/80";
        const isDraggable = !isSubtask;

        const draggableAttr = isDraggable 
            ? `draggable="true" data-task-id="${task.id}" data-row-index="${rowIndex}" ondragstart="onTaskDragStart(event)" ondragover="onTaskDragOver(event)" ondragleave="onTaskDragLeave(event)" ondrop="onTaskDrop(event)" ondragend="onTaskDragEnd(event)"` 
            : `data-task-id="${task.id}" data-row-index="${rowIndex}"`;

        html += `<tr id="task-row-${task.id}" class="${rowClass} transition-colors group" ${draggableAttr}>`;

        // Left Sticky Cell: Task Title, Grip Handle & Meta
        html += `
            <td class="${leftStickyClass} p-2.5 transition-colors">
                <div class="flex items-center justify-between gap-1.5">
                    <div class="flex items-center gap-2 overflow-hidden flex-1 ${isSubtask ? 'pl-6' : ''}">
                        ${isDraggable ? `
                        <div class="drag-handle p-1 text-slate-500 hover:text-white rounded transition-colors flex items-center justify-center opacity-40 group-hover:opacity-100" title="Drag to reorder task position">
                            <i data-lucide="grip-vertical" class="w-3.5 h-3.5"></i>
                        </div>
                        ` : ''}
                        ${isSubtask ? `<i data-lucide="corner-down-right" class="w-3.5 h-3.5 text-blue-400/80 flex-shrink-0"></i>` : ''}
                        <span class="${isSubtask ? 'w-2 h-2' : 'w-2.5 h-2.5'} rounded-full flex-shrink-0" style="background-color: ${task.color || (isSubtask ? '#60a5fa' : '#3b82f6')}"></span>
                        <div class="truncate flex-1">
                            <span class="${isSubtask ? 'text-xs text-slate-300 font-normal leading-tight block truncate' : 'font-bold text-xs sm:text-sm text-slate-100'}">
                                ${task.title}
                            </span>
                            ${!isSubtask ? `<span class="text-[10px] text-slate-400 block truncate">${task.category || 'General'}</span>` : ''}
                        </div>
                    </div>
                    <div class="flex items-center gap-0.5">
                        ${!isSubtask ? `
                        <button draggable="false" onclick='openAddSubtaskModal(${task.id}, "${task.title.replace(/"/g, '&quot;')}")' class="opacity-0 group-hover:opacity-100 p-1 hover:text-emerald-400 text-slate-400 rounded transition-all" title="Add Subtask">
                            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
                        </button>
                        ` : ''}
                        <button draggable="false" onclick='openEditTaskModal(${JSON.stringify(task).replace(/'/g, "&apos;")})' class="opacity-0 group-hover:opacity-100 p-1 hover:text-white text-slate-400 rounded transition-opacity" title="${isSubtask ? 'Edit Subtask' : 'Edit Task'}">
                            <i data-lucide="more-horizontal" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </div>
            </td>
        `;

        // Checkbox Cells for Days 1..N
        days.forEach((d, dayIndex) => {
            const isDone = row.cells[dayIndex] || false;
            const weekendCellClass = d.is_weekend ? "weekend-cell" : "";
            const todayCellClass = d.is_today ? "today-cell" : "";

            html += `
                <td class="text-center p-0 matrix-day-cell ${cellStickyClass} ${weekendCellClass} ${todayCellClass}">
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
        });

        // Right Sticky Cell: Row Total with fraction (e.g. 4/31)
        html += `
            <td id="row-total-${rowIndex}" class="${rightStickyClass} p-2 text-center text-xs font-semibold text-slate-200">
                <span class="font-bold text-white text-sm">${row.total_completed}</span>
                <span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>
            </td>
        `;

        html += `</tr>`;
    });

    html += `</tbody>`;
    table.innerHTML = html;
    lucide.createIcons();
}

async function onMatrixCellChange(checkbox) {
    const numDays = (currentMatrixData && currentMatrixData.num_days) || 31;
    const taskId = parseInt(checkbox.dataset.taskId);
    const dateStr = checkbox.dataset.date;
    const rowIndex = parseInt(checkbox.dataset.rowIndex);
    const dayIndex = parseInt(checkbox.dataset.dayIndex);
    const isChecked = checkbox.checked;

    const task = currentMatrixData.matrix[rowIndex].task;
    const taskTitle = task.title.trim().toLowerCase();

    // Check count of regular top-level habits completed on this date
    let regularDoneOnThisDay = 0;
    let fullDayRowIndex = -1;
    let goalRowIndex = -1;

    currentMatrixData.matrix.forEach((r, idx) => {
        const t = r.task.title.trim().toLowerCase();
        if (t === "goal") {
            goalRowIndex = idx;
        } else if (t === "full day") {
            fullDayRowIndex = idx;
        } else if (!r.task.parent_id) {
            if (r.cells[dayIndex]) regularDoneOnThisDay++;
        }
    });

    // Guard: 'Full Day' cannot be checked if 0 regular tasks are checked
    if (taskTitle === "full day" && isChecked && regularDoneOnThisDay === 0) {
        checkbox.checked = false;
        checkbox.style.backgroundColor = "transparent";
        checkbox.style.borderColor = "rgba(148, 163, 184, 0.4)";
        checkbox.style.boxShadow = "none";
        currentMatrixData.matrix[rowIndex].cells[dayIndex] = false;
        showToast("At least 1 habit must be checked before marking Full Day", "error");
        return;
    }

    if (taskTitle === "full day") {
        if (isChecked) {
            checkbox.style.backgroundColor = "#f59e0b";
            checkbox.style.borderColor = "#f59e0b";
            checkbox.style.boxShadow = "0 0 8px rgba(245, 158, 11, 0.4)";
        } else {
            checkbox.style.backgroundColor = "transparent";
            checkbox.style.borderColor = "rgba(148, 163, 184, 0.4)";
            checkbox.style.boxShadow = "none";
        }
    } else {
        if (isChecked) {
            checkbox.style.backgroundColor = task.color || "#3b82f6";
            checkbox.style.borderColor = task.color || "#3b82f6";
        } else {
            checkbox.style.backgroundColor = "transparent";
            checkbox.style.borderColor = "rgba(148, 163, 184, 0.4)";
        }
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
        const isGoalTask = taskTitle === "goal";
        const totalColorClass = isGoalTask ? "text-amber-400" : (taskTitle === "full day" ? "text-amber-500" : "text-white");
        rowTotalCell.innerHTML = `<span class="font-bold ${totalColorClass} text-sm">${newRowTotal}</span><span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>`;
    }

    // Automatic parent tick: ticking the checkbox of a subtask automatically ticks the parent!
    if (task.parent_id && isChecked) {
        const parentRowIndex = currentMatrixData.matrix.findIndex(r => r.task.id === task.parent_id);
        if (parentRowIndex !== -1) {
            const parentRow = currentMatrixData.matrix[parentRowIndex];
            if (!parentRow.cells[dayIndex]) {
                parentRow.cells[dayIndex] = true;
                const parentCb = document.querySelector(`input[data-task-id="${task.parent_id}"][data-day-index="${dayIndex}"]`);
                if (parentCb) {
                    parentCb.checked = true;
                    parentCb.style.backgroundColor = parentRow.task.color || "#3b82f6";
                    parentCb.style.borderColor = parentRow.task.color || "#3b82f6";
                }
                let pTotal = 0;
                parentRow.cells.forEach(c => { if (c) pTotal++; });
                parentRow.total_completed = pTotal;
                const pTotalEl = document.getElementById(`row-total-${parentRowIndex}`);
                if (pTotalEl) {
                    pTotalEl.innerHTML = `<span class="font-bold text-white text-sm">${pTotal}</span><span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>`;
                }
            }
        }
    }

    // Recount regular habits after modification
    regularDoneOnThisDay = 0;
    let isFullDayCheckedOnThisDay = false;
    currentMatrixData.matrix.forEach(r => {
        const tTitle = r.task.title.trim().toLowerCase();
        if (tTitle === "full day") {
            isFullDayCheckedOnThisDay = Boolean(r.cells[dayIndex]);
        } else if (tTitle !== "goal" && !r.task.parent_id) {
            if (r.cells[dayIndex]) regularDoneOnThisDay++;
        }
    });

    // Dynamically update Full Day checkbox status and state on this day
    const fullDayCb = document.getElementById(`fullday-cell-${dayIndex}`);
    if (fullDayCb && fullDayRowIndex !== -1) {
        if (regularDoneOnThisDay === 0) {
            // Cannot be checked; disable and uncheck if previously checked
            fullDayCb.checked = false;
            fullDayCb.disabled = true;
            fullDayCb.classList.remove('cursor-pointer');
            fullDayCb.classList.add('cursor-not-allowed', 'opacity-30');
            fullDayCb.style.backgroundColor = "transparent";
            fullDayCb.style.borderColor = "rgba(148, 163, 184, 0.4)";
            fullDayCb.style.boxShadow = "none";
            fullDayCb.title = "Check at least 1 habit first before marking Full Day";

            if (isFullDayCheckedOnThisDay) {
                currentMatrixData.matrix[fullDayRowIndex].cells[dayIndex] = false;
                isFullDayCheckedOnThisDay = false;
                let fdTotal = 0;
                currentMatrixData.matrix[fullDayRowIndex].cells.forEach(c => { if (c) fdTotal++; });
                currentMatrixData.matrix[fullDayRowIndex].total_completed = fdTotal;
                const fdTotalCell = document.getElementById(`row-total-${fullDayRowIndex}`);
                if (fdTotalCell) {
                    fdTotalCell.innerHTML = `<span class="font-bold text-amber-500 text-sm">${fdTotal}</span><span class="text-slate-500 text-[11px] font-normal">/${numDays}</span>`;
                }
            }
        } else {
            // Can be clicked
            fullDayCb.disabled = false;
            fullDayCb.classList.remove('cursor-not-allowed', 'opacity-30');
            fullDayCb.classList.add('cursor-pointer');
            fullDayCb.title = `Full Day on ${dateStr}: ${fullDayCb.checked ? 'Marked' : 'Check if 1 major habit took the entire day'}`;
        }
    }

    // Evaluate Goal auto-tick on client side for instantaneous UI feedback
    const threshold = currentMatrixData.goal_threshold || 3;
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
            return !r.task.parent_id && title !== 'goal' && title !== 'full day';
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
    const userId = (window.state && window.state.user && window.state.user.id) || 'default';
    try {
        localStorage.setItem('goalplanner_habit_order_' + userId, JSON.stringify(orderedIds));
    } catch (e) {
        console.warn("Failed to persist order in localStorage:", e);
    }

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
            return !r.task.parent_id && title !== 'goal' && title !== 'full day';
        })
        .map(r => r.task);

    const fromIdx = regularTasks.findIndex(t => t.id === sourceTaskId);
    if (fromIdx === -1) return;

    // Move to top of regular tasks list (right below Full Day)
    const [movedTask] = regularTasks.splice(fromIdx, 1);
    regularTasks.unshift(movedTask);

    const orderedIds = regularTasks.map(t => t.id);
    const userId = (window.state && window.state.user && window.state.user.id) || 'default';
    try {
        localStorage.setItem('goalplanner_habit_order_' + userId, JSON.stringify(orderedIds));
    } catch (e) {
        console.warn("Failed to persist order in localStorage:", e);
    }

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
