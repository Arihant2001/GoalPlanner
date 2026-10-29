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
        renderMatrix(currentMatrixData);

        // Update last updated text
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        document.getElementById("matrix-last-updated").textContent = `Synced at ${timeStr}`;

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
    const dailyStats = data.daily_stats;
    const totalTasks = data.total_tasks;

    let html = "";

    // 1. THEAD: Date Headers
    html += `<thead><tr class="bg-slate-900 border-b border-slate-800">`;
    
    // Top-Left Sticky Corner
    html += `
        <th class="sticky-top-left bg-slate-900 border-r border-slate-800 p-2.5 min-w-[190px] max-w-[210px] text-xs font-bold text-slate-300">
            <div class="flex items-center justify-between">
                <span class="text-blue-400 font-extrabold tracking-wide uppercase">${data.month_name.slice(0, 3)} ${data.year}</span>
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
        const isGoalTask = task.title.toLowerCase() === "goal";
        const rowClass = isGoalTask ? "goal-row" : "hover:bg-slate-800/30";

        html += `<tr class="${rowClass} transition-colors group">`;

        // Left Sticky Cell: Task Title & Meta
        html += `
            <td class="sticky-col bg-slate-900 group-hover:bg-slate-800/80 border-r border-slate-800 p-2.5 transition-colors">
                <div class="flex items-center justify-between gap-1.5">
                    <div class="flex items-center gap-2 overflow-hidden">
                        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background-color: ${task.color || '#3b82f6'}"></span>
                        <div class="truncate">
                            <span class="font-bold text-xs sm:text-sm text-slate-100 ${isGoalTask ? 'text-blue-400 font-black' : ''}">${task.title}</span>
                            <span class="text-[10px] text-slate-400 block truncate">${task.category || 'General'}</span>
                        </div>
                    </div>
                    <button onclick='openEditTaskModal(${JSON.stringify(task).replace(/'/g, "&apos;")})' class="opacity-0 group-hover:opacity-100 p-1 hover:text-white text-slate-400 rounded transition-opacity" title="Edit Task">
                        <i data-lucide="more-horizontal" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            </td>
        `;

        // Checkbox Cells for Days 1..N
        days.forEach((d, dayIndex) => {
            const isDone = row.cells[dayIndex] || false;
            const weekendCellClass = d.is_weekend ? "weekend-cell" : "";
            const todayCellClass = d.is_today ? "today-cell" : "";

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
                            style="${isDone ? `background-color: ${task.color || '#2563eb'}; border-color: ${task.color || '#2563eb'};` : ''}"
                            title="${task.title} on ${d.date}">
                    </div>
                </td>
            `;
        });

        // Right Sticky Cell: Row Total & Percentage
        html += `
            <td id="row-total-${rowIndex}" class="sticky-summary-col bg-slate-900 group-hover:bg-slate-800/80 border-l border-slate-800 p-2 text-center text-xs font-semibold text-slate-200">
                <span class="font-bold text-white">${row.total_completed}</span>
                <span class="text-slate-500 text-[10px]">/${numDays}</span>
                <div class="text-[10px] text-blue-400 font-medium">${row.completion_percentage}%</div>
            </td>
        `;

        html += `</tr>`;
    });

    html += `</tbody>`;

    // 3. TFOOT: Daily Summary Progress Row
    html += `<tfoot><tr class="bg-slate-900/90 border-t-2 border-slate-800 font-semibold">`;

    // Left Sticky Bottom Corner
    html += `
        <td class="sticky-col bg-slate-900 border-r border-slate-800 p-2.5 text-xs font-bold text-slate-300">
            <div class="flex items-center gap-1.5">
                <i data-lucide="activity" class="w-3.5 h-3.5 text-emerald-400"></i>
                <span>Daily Progress</span>
            </div>
        </td>
    `;

    // Day Progress Columns
    let totalCompletedMonth = 0;
    days.forEach((d, dayIndex) => {
        const stat = dailyStats[dayIndex] || { completed_count: 0, total_tasks: totalTasks, percentage: 0 };
        totalCompletedMonth += stat.completed_count;
        const weekendCellClass = d.is_weekend ? "weekend-cell" : "";
        const todayCellClass = d.is_today ? "today-cell" : "";
        const pctColor = stat.percentage >= 75 ? "bg-emerald-500" : (stat.percentage >= 40 ? "bg-blue-500" : "bg-slate-700");

        html += `
            <td id="daily-stat-${dayIndex}" class="text-center p-1 border-r border-slate-800/60 ${weekendCellClass} ${todayCellClass}" title="${d.date}: ${stat.completed_count} of ${stat.total_tasks} (${stat.percentage}%)">
                <div class="text-[10px] font-bold text-slate-200">${stat.completed_count}</div>
                <div class="w-full bg-slate-800 h-1.5 rounded-full mt-0.5 overflow-hidden">
                    <div class="${pctColor} h-full rounded-full transition-all duration-300" style="width: ${stat.percentage}%"></div>
                </div>
            </td>
        `;
    });

    // Right Sticky Bottom Corner (Overall Rate)
    const maxPossible = numDays * totalTasks;
    const overallRate = maxPossible > 0 ? Math.round((totalCompletedMonth / maxPossible) * 100) : 0;

    html += `
        <td id="matrix-overall-rate" class="sticky-summary-col bg-slate-900 border-l border-slate-800 p-2 text-center text-xs font-bold text-emerald-400">
            ${overallRate}%
            <div class="text-[9px] text-slate-400 font-normal">avg</div>
        </td>
    `;

    html += `</tr></tfoot>`;

    table.innerHTML = html;
    lucide.createIcons();
}

async function onMatrixCellChange(checkbox) {
    const taskId = parseInt(checkbox.dataset.taskId);
    const dateStr = checkbox.dataset.date;
    const rowIndex = parseInt(checkbox.dataset.rowIndex);
    const dayIndex = parseInt(checkbox.dataset.dayIndex);
    const isChecked = checkbox.checked;

    // Optimistic UI updates
    const task = currentMatrixData.matrix[rowIndex].task;
    if (isChecked) {
        checkbox.style.backgroundColor = task.color || "#2563eb";
        checkbox.style.borderColor = task.color || "#2563eb";
    } else {
        checkbox.style.backgroundColor = "transparent";
        checkbox.style.borderColor = "rgba(148, 163, 184, 0.4)";
    }

    // Update memory representation
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

    // Recalculate daily stat
    let newDayDone = 0;
    currentMatrixData.matrix.forEach(r => {
        if (r.cells[dayIndex]) newDayDone++;
    });
    const totalTasks = currentMatrixData.total_tasks;
    const newDayPct = totalTasks > 0 ? Math.round((newDayDone / totalTasks) * 100) : 0;
    currentMatrixData.daily_stats[dayIndex].completed_count = newDayDone;
    currentMatrixData.daily_stats[dayIndex].percentage = newDayPct;

    const dayStatCell = document.getElementById(`daily-stat-${dayIndex}`);
    if (dayStatCell) {
        const pctColor = newDayPct >= 75 ? "bg-emerald-500" : (newDayPct >= 40 ? "bg-blue-500" : "bg-slate-700");
        dayStatCell.innerHTML = `
            <div class="text-[10px] font-bold text-slate-200">${newDayDone}</div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full mt-0.5 overflow-hidden">
                <div class="${pctColor} h-full rounded-full transition-all duration-300" style="width: ${newDayPct}%"></div>
            </div>
        `;
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
            showToast("Failed to save checkmark", "error");
            checkbox.checked = !isChecked; // revert
        } else {
            // Silently update heatmap and streak if in cache
            if (window.loadHeatmap) window.loadHeatmap(false);
        }
    } catch (err) {
        showToast("Network error syncing task", "error");
        checkbox.checked = !isChecked; // revert
    }
}

window.loadMatrix = loadMatrix;
