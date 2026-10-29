let heatmapTooltip = null;

async function loadHeatmap(renderDOM = true) {
    const yearSelect = document.getElementById("heatmap-year-select");
    const taskSelect = document.getElementById("heatmap-task-filter");
    if (!yearSelect) return;

    const year = parseInt(yearSelect.value);
    const taskId = taskSelect ? taskSelect.value : "all";

    try {
        const res = await fetch(`/api/heatmap?year=${year}&task_id=${taskId}`);
        const json = await res.json();
        if (!json.success) return;

        const data = json.data;

        // Update Stats & Badges
        document.getElementById("stat-current-streak").textContent = `${data.current_streak} Day${data.current_streak === 1 ? '' : 's'}`;
        document.getElementById("stat-longest-streak").textContent = `${data.longest_streak} Day${data.longest_streak === 1 ? '' : 's'}`;
        document.getElementById("stat-active-days").textContent = data.total_active_days;
        document.getElementById("stat-total-actions").textContent = data.total_completed_actions;

        // Update Header Streak Badge
        const headerStreak = document.getElementById("streak-counter-text");
        if (headerStreak) {
            headerStreak.textContent = `${data.current_streak} Day Streak`;
        }

        const summarySentence = document.getElementById("heatmap-summary-sentence");
        if (summarySentence) {
            const habitLabel = data.filter_task ? `for "${data.filter_task.title}"` : "across all habits";
            summarySentence.textContent = `${data.total_completed_actions} tasks checked off in ${data.year} ${habitLabel}`;
        }

        if (renderDOM) {
            renderHeatmapGrid(data);
        }

    } catch (err) {
        console.error("Failed to load heatmap:", err);
    }
}

function renderHeatmapGrid(data) {
    const container = document.getElementById("github-heatmap-container");
    if (!container) return;

    // Remove any existing tooltip
    if (heatmapTooltip) {
        heatmapTooltip.remove();
        heatmapTooltip = null;
    }

    // Create Tooltip DOM
    heatmapTooltip = document.createElement("div");
    heatmapTooltip.className = "heatmap-tooltip opacity-0 pointer-events-none fixed z-50 bg-slate-900 border border-slate-700 text-white text-xs rounded-xl p-3 shadow-2xl backdrop-blur-md transition-opacity duration-150";
    document.body.appendChild(heatmapTooltip);

    const days = data.days; // 365 or 366 day objects
    
    // Group days into 7 rows (by day of week: 0=Mon ... 6=Sun) and ~53 week columns
    // First, align by week of year.
    // Sunday or Monday start: let's do Monday (0) to Sunday (6)
    const weeks = [];
    let currentWeek = [];

    // Pad first week with empty cells until day_of_week matches
    const firstDayOfWeek = days[0].day_of_week; // 0=Mon..6=Sun
    for (let i = 0; i < firstDayOfWeek; i++) {
        currentWeek.push(null);
    }

    days.forEach(day => {
        currentWeek.push(day);
        if (currentWeek.length === 7) {
            weeks.push(currentWeek);
            currentWeek = [];
        }
    });

    if (currentWeek.length > 0) {
        while (currentWeek.length < 7) {
            currentWeek.push(null);
        }
        weeks.push(currentWeek);
    }

    // Determine month label positions across week columns
    const monthLabels = [];
    let lastMonth = null;
    weeks.forEach((week, colIndex) => {
        // Find first non-null day in week
        const validDay = week.find(d => d !== null);
        if (validDay && validDay.month !== lastMonth) {
            lastMonth = validDay.month;
            const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            monthLabels.push({
                colIndex,
                name: monthNames[lastMonth - 1]
            });
        }
    });

    // Color mapper for GitHub levels
    const colorClasses = [
        "bg-slate-800/80 border border-slate-700/50",              // Level 0
        "bg-emerald-950 border border-emerald-900/60",             // Level 1
        "bg-emerald-800 border border-emerald-700/60",             // Level 2
        "bg-emerald-600 border border-emerald-500/60",             // Level 3
        "bg-emerald-400 border border-emerald-300 shadow-sm shadow-emerald-400/40" // Level 4
    ];

    let gridHtml = "";

    // Month Labels Row
    gridHtml += `<div class="flex items-center text-[10px] text-slate-400 font-semibold mb-1 pl-7 relative h-4">`;
    monthLabels.forEach(m => {
        const leftPx = m.colIndex * 15; // 12px cell + 3px gap
        gridHtml += `<span class="absolute" style="left: ${leftPx + 28}px">${m.name}</span>`;
    });
    gridHtml += `</div>`;

    // 7 Rows of Days: Mon, Tue, Wed, Thu, Fri, Sat, Sun
    const dayNames = ["Mon", "", "Wed", "", "Fri", "", "Sun"];

    gridHtml += `<div class="flex flex-col gap-[3px]">`;

    for (let rowIdx = 0; rowIdx < 7; rowIdx++) {
        gridHtml += `<div class="flex items-center gap-[3px]">`;
        
        // Day of week label
        gridHtml += `<span class="w-6 text-[10px] text-slate-500 font-medium select-none text-right pr-1">${dayNames[rowIdx]}</span>`;

        // Cells for each week
        weeks.forEach(week => {
            const day = week[rowIdx];
            if (!day) {
                gridHtml += `<div class="w-3 h-3 rounded-sm opacity-0 pointer-events-none"></div>`;
            } else {
                const colorClass = colorClasses[day.level] || colorClasses[0];
                const todayRing = day.is_today ? "ring-2 ring-blue-400 ring-offset-1 ring-offset-slate-900" : "";
                
                gridHtml += `
                    <div class="w-3 h-3 rounded-sm cursor-pointer transition-transform hover:scale-125 ${colorClass} ${todayRing}"
                        data-date="${day.date}"
                        data-count="${day.count}"
                        data-total="${day.total_tasks}"
                        data-pct="${day.percentage}"
                        data-tasks='${JSON.stringify(day.completed_tasks).replace(/'/g, "&apos;")}'
                        onmouseenter="onHeatmapCellEnter(event, this)"
                        onmouseleave="onHeatmapCellLeave()"
                    ></div>
                `;
            }
        });

        gridHtml += `</div>`;
    }

    gridHtml += `</div>`;

    container.innerHTML = gridHtml;
}

function onHeatmapCellEnter(event, cell) {
    if (!heatmapTooltip) return;

    const dateStr = cell.dataset.date;
    const count = parseInt(cell.dataset.count);
    const total = parseInt(cell.dataset.total);
    const pct = cell.dataset.pct;
    const tasks = JSON.parse(cell.dataset.tasks || "[]");

    const dateObj = new Date(dateStr);
    const dateFormatted = dateObj.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });

    let tasksHtml = "";
    if (tasks.length > 0) {
        tasksHtml = `
            <div class="mt-2 pt-2 border-t border-slate-800 flex flex-wrap gap-1 max-w-[200px]">
                ${tasks.map(t => `<span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px]">${t}</span>`).join("")}
            </div>
        `;
    }

    heatmapTooltip.innerHTML = `
        <div class="font-bold text-white">${dateFormatted}</div>
        <div class="text-emerald-400 font-semibold mt-0.5">${count} of ${total} habits completed (${pct}%)</div>
        ${tasksHtml}
    `;

    const rect = cell.getBoundingClientRect();
    heatmapTooltip.style.left = `${rect.left + rect.width / 2}px`;
    heatmapTooltip.style.top = `${rect.top - 8}px`;
    heatmapTooltip.classList.remove("opacity-0");
}

function onHeatmapCellLeave() {
    if (heatmapTooltip) {
        heatmapTooltip.classList.add("opacity-0");
    }
}

window.loadHeatmap = loadHeatmap;
