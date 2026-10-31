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

        // Also refresh heatmap silently in background
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

    // Top-Right Sticky Corner (Total)
    html += `
        <th class="sticky-summary-header bg-slate-900 border-l border-slate-800 p-2 min-w-[85px] text-center text-xs font-bold text-slate-300">
            Month Total
        </th>
    </tr></thead>`;

    // 2. TBODY: Task Rows
    html += `<tbody class="divide-y divide-slate-800/60">`;

    taskRows.forEach((row, rowIndex) => {
        const task = row.task;
        const isGoalTask = row.is_goal || task.title.trim().toLowerCase() === "goal";
        const rowClass = isGoalTask ? "goal-row bg-amber-500/[0.04]" : "hover:bg-slate-800/30";

        html += `<tr class="${rowClass} transition-colors group">`;

        // Left Sticky Cell: Task Title & Meta
        html += `
            <td class="sticky-col bg-slate-900 group-hover:bg-slate-800/80 border-r border-slate-800 p-2.5 transition-colors">
                <div class="flex items-center justify-between gap-1.5">
                    <div class="flex items-center gap-2 overflow-hidden">
                        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${task.color || '#eab308'}"></span>
                        <div class="truncate">
                            <span class="font-bold text-xs sm:text-sm ${isGoalTask ? 'text-amber-400 font-black flex items-center gap-1' : 'text-slate-100'}">
                                ${isGoalTask ? '<i data-lucide="crown" class="w-3.5 h-3.5 text-amber-400 inline"></i>' : ''}
                                ${task.title}
                            </span>
                            <span class="text-[10px] text-slate-400 block truncate">
                                ${isGoalTask ? '⭐ Main Daily Goal (Auto-ticks)' : (task.category || 'Mind')}
                            </span>
                        </div>
                    </div>
                    ${!isGoalTask ? `
                    <button onclick='openEditTaskModal(${JSON.stringify(task).replace(/'/g, "&apos;")})' class="opacity-0 group-hover:opacity-100 p-1 hover:text-white text-slate-400 rounded transition-opacity" title="Edit Task">
                        <i data-lucide="more-horizontal" class="w-3.5 h-3.5"></i>
                    </button>
                    ` : `
                    <span class="text-[10px] text-amber-500/80 px-1 py-0.5 rounded bg-amber-500/10" title="Auto-ticks when target is met">Auto</span>
                    `}
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
                                id="goal-cell-${dayIndex}"
                                class="matrix-checkbox goal-checkbox cursor-not-allowed opacity-90" 
                                ${isDone ? "checked" : ""} 
                                disabled
                                style="${isDone ? `background-color: #eab308; border-color: #eab308; box-shadow: 0 0 10px rgba(234, 179, 8, 0.45);` : ''}"
                                title="Goal on ${d.date}: ${isDone ? 'Achieved!' : 'Complete threshold tasks to achieve'}">
                        </div>
                    </td>
                `;
            } else {
                html += `
                    <td class="text-center p-0 border-r border-slate-800/60 ${weekendCellClass} ${todayCellClass}">
                        <div class="w-full h-full py-1.5 px-0.5 flex items-center justify-center">
                            <input type="checkbox" 
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

        // Right Sticky Cell: Row Total & Percentage
        html += `
            <td id="row-total-${rowIndex}" class="sticky-summary-col bg-slate-900 group-hover:bg-slate-800/80 border-l border-slate-800 p-2 text-center text-xs font-semibold text-slate-200">
                <span class="font-bold ${isGoalTask ? 'text-amber-400' : 'text-white'}">${row.total_completed}</span>
                <span class="text-slate-500 text-[10px]">/${numDays}</span>
                <div class="text-[10px] ${isGoalTask ? 'text-amber-400 font-bold' : 'text-blue-400 font-medium'}">${row.completion_percentage}%</div>
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

    // Recalculate row total
    let newRowTotal = 0;
    currentMatrixData.matrix[rowIndex].cells.forEach(c => {
        if (c) newRowTotal++;
    });
    const numDays = currentMatrixData.num_days;
    const newRowPct = Math.round((newRowTotal / numDays) * 100 * 10) / 10;
    currentMatrixData.matrix[rowIndex].total_completed = newRowTotal;
    currentMatrixData.matrix[rowIndex].completion_percentage = newRowPct;

    const rowTotalCell = document.getElementById(`row-total-${rowIndex}`);
    if (rowTotalCell) {
        rowTotalCell.innerHTML = `
            <span class="font-bold text-white">${newRowTotal}</span>
            <span class="text-slate-500 text-[10px]">/${numDays}</span>
            <div class="text-[10px] text-blue-400 font-medium">${newRowPct}%</div>
        `;
    }

    // Evaluate Goal auto-tick on client side for immediate feedback
    const threshold = currentMatrixData.goal_threshold || 3;
    let nonGoalDoneOnThisDay = 0;
    let goalRowIndex = -1;

    currentMatrixData.matrix.forEach((r, idx) => {
        if (r.is_goal || r.task.title.trim().toLowerCase() === "goal") {
            goalRowIndex = idx;
        } else {
            if (r.cells[dayIndex]) nonGoalDoneOnThisDay++;
        }
    });

    const shouldGoalBeDone = nonGoalDoneOnThisDay >= threshold;
    if (goalRowIndex !== -1) {
        currentMatrixData.matrix[goalRowIndex].cells[dayIndex] = shouldGoalBeDone;
        
        // Update Goal checkbox element on this day
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

        // Update Goal Row Total
        let goalTotal = 0;
        currentMatrixData.matrix[goalRowIndex].cells.forEach(c => {
            if (c) goalTotal++;
        });
        const goalPct = Math.round((goalTotal / numDays) * 100 * 10) / 10;
        currentMatrixData.matrix[goalRowIndex].total_completed = goalTotal;
        currentMatrixData.matrix[goalRowIndex].completion_percentage = goalPct;

        const goalRowTotalCell = document.getElementById(`row-total-${goalRowIndex}`);
        if (goalRowTotalCell) {
            goalRowTotalCell.innerHTML = `
                <span class="font-bold text-amber-400">${goalTotal}</span>
                <span class="text-slate-500 text-[10px]">/${numDays}</span>
                <div class="text-[10px] text-amber-400 font-bold">${goalPct}%</div>
            `;
        }
    }

    // Send async backend request
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
            checkbox.checked = !isChecked; // revert
        } else {
            // Silently update heatmap in background
            if (window.loadHeatmap) window.loadHeatmap(false);
        }
    } catch (err) {
        showToast("Network error syncing task", "error");
        checkbox.checked = !isChecked;
    }
}

window.loadMatrix = loadMatrix;
