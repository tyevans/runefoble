// --- Runefoble Project Content Visualizer: Gantt Chart & Delivery Timeline ---
(function() {
  window.visualizer = window.visualizer || {};

  const milestoneShortNames = {
    'M1': 'Foundations',
    'M2': 'Alpha',
    'M3': 'AI DM',
    'M4': 'Studio',
    'M5': 'Downtime',
    'M6': 'Worlds',
    'M7': 'Voice / 3D',
    'M8': 'Reactions',
    'M9': 'Immersion',
    'M10': 'App Shell',
  };

  const defaultMilestones = [
    { id: 'M1', name: 'Platform Foundation & Core Loop', status: 'Complete', completion_pct: 100 },
    { id: 'M2', name: 'Live Collaborative Alpha', status: 'Complete', completion_pct: 100 },
    { id: 'M3', name: 'AI DM & Ecosystem Expansion', status: 'Complete', completion_pct: 100 },
    { id: 'M4', name: 'Broadcast Studio & Community Platform', status: 'Complete', completion_pct: 100 },
    { id: 'M5', name: 'Collaborative Creation, Downtime & Tactile Immersion', status: 'Complete', completion_pct: 100 },
    { id: 'M6', name: 'Intelligent Living Worlds & Spatial Multi-Party Universes', status: 'Complete', completion_pct: 100 },
    { id: 'M7', name: 'Neural Audio Duplex & Tangible 3D Tabletop', status: 'Complete', completion_pct: 100 },
    { id: 'M8', name: 'Reactive Tactical Environments & In-World DM Tools', status: 'Complete', completion_pct: 100 },
    { id: 'M9', name: 'Persona Immersion & Community Ecosystem', status: 'In Progress', completion_pct: 2 },
    { id: 'M10', name: 'Complete Frontend Application Experience, User Identity & Campaign Orchestration', status: 'Current', completion_pct: 0 },
  ];

  function renderGantt(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;
    const tasks = d.tasks || [];
    const rawMilestones = (d.milestones && d.milestones.length > 0) ? d.milestones : defaultMilestones;

    // Sort milestones numerically M1 to M10
    const sortedMilestones = [...rawMilestones].sort((a, b) => {
      const na = parseInt(a.id.replace(/\D/g, ''), 10) || 0;
      const nb = parseInt(b.id.replace(/\D/g, ''), 10) || 0;
      return na - nb;
    });
    const totalMilestones = Math.max(sortedMilestones.length, 1);

    // Build milestone lookup maps
    const milestoneTitles = {};
    const milestoneTaskMap = {};
    sortedMilestones.forEach(m => {
      const cleanName = m.name.replace(/\s*\((Complete|Current|Active|Planned|In Progress)[^)]*\)/i, '').trim();
      milestoneTitles[m.id] = `Milestone ${m.id.replace('M', '')}: ${cleanName}`;
      (m.task_ids || []).forEach(tid => {
        milestoneTaskMap[tid] = m.id;
      });
    });

    function resolveMilestone(t) {
      if (t.milestone && t.milestone.startsWith('M')) {
        return t.milestone.toUpperCase();
      }
      if (milestoneTaskMap[t.id]) {
        return milestoneTaskMap[t.id];
      }
      const rel = t.target_release || '';
      const match = rel.match(/0\.(\d+)/);
      if (match) {
        return 'M' + match[1];
      }
      if (rel.startsWith('1.')) return 'M10';
      const numMatch = t.id.match(/\d+/);
      if (numMatch) {
        const n = parseInt(numMatch[0], 10);
        if (n <= 14) return 'M1';
        if (n <= 46) return 'M2';
        if (n <= 74) return 'M3';
        if (n <= 99) return 'M4';
        if (n <= 125) return 'M5';
        if (n <= 140) return 'M6';
        if (n <= 154) return 'M7';
        if (n <= 160) return 'M8';
        if (n <= 205) return 'M9';
        return 'M10';
      }
      return 'M10';
    }

    // Filter tasks
    const filteredTasks = tasks.filter(t => {
      if (state.filters.hideDone && t.status === 'Complete') return false;
      if (state.filters.bc !== 'all' && t.target_bc !== state.filters.bc) return false;
      const tMilestone = resolveMilestone(t);
      if (state.filters.milestone !== 'all' && tMilestone !== state.filters.milestone) return false;
      if (state.filters.search) {
        const q = state.filters.search.toLowerCase();
        const matchTitle = t.title.toLowerCase().includes(q);
        const matchId = t.id.toLowerCase().includes(q);
        const matchPR = (t.prs || []).some(pr => pr.toLowerCase().includes(q));
        if (!matchTitle && !matchId && !matchPR) return false;
      }
      return true;
    });

    const bcs = Array.from(new Set(tasks.map(t => t.target_bc).filter(Boolean))).sort();
    const groupBy = state.gantt.groupBy || 'milestone';

    // Map tasks to milestone groups or BC groups
    const groups = {};
    if (groupBy === 'milestone') {
      sortedMilestones.forEach(m => {
        const gTitle = milestoneTitles[m.id] || `Milestone ${m.id.replace('M', '')}: ${m.name}`;
        groups[gTitle] = [];
      });

      filteredTasks.forEach(t => {
        const mKey = resolveMilestone(t);
        const gTitle = milestoneTitles[mKey] || `Milestone ${mKey.replace('M', '')}`;
        if (!groups[gTitle]) groups[gTitle] = [];
        groups[gTitle].push(t);
      });

      // Remove empty groups (e.g. when filters are active)
      Object.keys(groups).forEach(g => {
        if (groups[g].length === 0) delete groups[g];
      });
    } else {
      // Group by Bounded Context
      filteredTasks.forEach(t => {
        const bc = t.target_bc || 'platform';
        if (!groups[bc]) groups[bc] = [];
        groups[bc].push(t);
      });
    }

    const totalComplete = tasks.filter(t => t.status === 'Complete').length;

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Header & Toolbar -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[var(--bg-card)] border border-subtle">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>Roadmap Gantt & Delivery Timeline</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono border border-indigo-500/20">${filteredTasks.length} Tasks Scheduled</span>
            </h2>
            <p class="text-xs text-muted">Interactive timeline chart showing milestone horizons, durations, dependencies, and PR deliveries.</p>
          </div>

          <!-- Controls -->
          <div class="flex flex-wrap items-center gap-2.5">
            <!-- Hide Done Toggle -->
            <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" id="gantt-hide-done" class="rounded accent-indigo-500" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'gantt')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span>
              ${state.filters.hideDone ? `<span class="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">${totalComplete} hidden</span>` : ''}
            </label>

            <!-- Group By Selector -->
            <select class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition"
                    onchange="window.visualizer.setGanttGroup(this.value)">
              <option value="milestone" ${groupBy === 'milestone' ? 'selected' : ''}>Group by Milestone</option>
              <option value="bc" ${groupBy === 'bc' ? 'selected' : ''}>Group by Bounded Context</option>
            </select>

            <!-- Milestone Filter -->
            <select class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition"
                    onchange="window.visualizer.setFilter('milestone', this.value, 'gantt')">
              <option value="all" ${state.filters.milestone === 'all' ? 'selected' : ''}>All Milestones</option>
              ${sortedMilestones.map(m => {
                const short = milestoneShortNames[m.id] || m.id;
                const activeTag = (m.status === 'Current' || m.id === 'M10') ? ' (Active)' : '';
                return `<option value="${m.id}" ${state.filters.milestone === m.id ? 'selected' : ''}>${m.id}: ${short}${activeTag}</option>`;
              }).join('')}
            </select>

            <!-- BC Filter -->
            <select class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition"
                    onchange="window.visualizer.setFilter('bc', this.value, 'gantt')">
              <option value="all" ${state.filters.bc === 'all' ? 'selected' : ''}>All Contexts</option>
              ${bcs.map(bc => `<option value="${bc}" ${state.filters.bc === bc ? 'selected' : ''}>${bc}</option>`).join('')}
            </select>

            <!-- Search -->
            <div class="relative">
              <input type="text" placeholder="Filter tasks..." value="${esc(state.filters.search)}"
                     class="px-3 py-1.5 pl-8 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition w-36"
                     oninput="window.visualizer.setFilter('search', this.value, 'gantt')">
              <svg class="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>
          </div>
        </div>

        <!-- Gantt Timeline Canvas Container -->
        <div class="rounded-xl bg-[var(--bg-card)] border border-subtle overflow-hidden">
          <!-- Timeline Scale Header -->
          <div class="grid grid-cols-12 border-b border-subtle bg-[var(--bg-elevated)] text-xs font-mono font-medium text-muted py-2.5 px-4">
            <div class="col-span-5 md:col-span-4 text-slate-300 font-bold">Task & Specification</div>
            <div class="col-span-7 md:col-span-8 flex items-center text-center overflow-hidden">
              ${sortedMilestones.map((m, idx) => {
                const isComplete = m.status === 'Complete';
                const isCurrent = m.status === 'Current' || m.id === 'M10';
                const isInProgress = m.status === 'In Progress';

                let textColor = 'text-slate-400';
                if (isComplete) textColor = 'text-emerald-400';
                else if (isCurrent) textColor = 'text-amber-400 font-bold';
                else if (isInProgress) textColor = 'text-sky-400 font-semibold';

                const shortName = milestoneShortNames[m.id] || m.id;
                const isLast = idx === sortedMilestones.length - 1;

                return `
                  <div class="flex-1 truncate px-0.5 ${!isLast ? 'border-r border-subtle/50' : ''} ${textColor}"
                       title="${m.id}: ${esc(m.name)} (${m.status}) - ${m.completion_pct}% Delivered">
                    <span class="text-[11px] font-bold">${m.id}</span>
                    <span class="hidden xl:inline text-[9px] ml-0.5 opacity-90">${esc(shortName)}</span>
                    ${isCurrent ? '<span class="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse ml-0.5" title="Active Milestone"></span>' : ''}
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Gantt Groups and Rows -->
          <div class="divide-y divide-subtle max-h-[75vh] overflow-y-auto">
            ${Object.keys(groups).map(gName => `
              <div class="p-3 bg-[var(--bg-card)]">
                <div class="flex items-center justify-between pb-2 mb-2 border-b border-subtle/50">
                  <h3 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
                    ${esc(gName)}
                  </h3>
                  <span class="px-2 py-0.5 rounded text-[11px] font-mono text-muted bg-[var(--bg-elevated)]">${groups[gName].length} tasks</span>
                </div>

                <div class="space-y-2">
                  ${groups[gName].map(task => renderGanttRow(task, esc, resolveMilestone, sortedMilestones)).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  function renderGanttRow(task, esc, resolveMilestone, sortedMilestones) {
    const prs = task.prs || [];
    const isComplete = task.status === 'Complete';
    const isRefined = task.status === 'Refined';

    const mKey = resolveMilestone(task);
    const mNum = parseInt(mKey.replace(/\D/g, ''), 10) || 1;
    const totalM = Math.max(sortedMilestones.length, 1);

    // Find index of this milestone in sortedMilestones (0-indexed)
    let mIndex = sortedMilestones.findIndex(m => m.id === mKey);
    if (mIndex === -1) {
      mIndex = Math.min(Math.max(mNum - 1, 0), totalM - 1);
    }

    const colWidth = 100 / totalM;
    const slotStart = mIndex * colWidth;

    // Position bar within the milestone column with small padding
    const hasDeps = task.dependencies && task.dependencies.length > 0;
    const offset = hasDeps ? colWidth * 0.15 : colWidth * 0.05;
    const startPct = Math.min(Math.max(slotStart + offset, 0.2), 99.0);

    // Width spans most of the milestone slot, slightly expanded if task has multiple PRs
    let widthPct = colWidth * (hasDeps ? 0.8 : 0.9);
    if (prs.length > 2) {
      widthPct = Math.min(colWidth * 1.3, 100 - startPct - 0.5);
    }
    widthPct = Math.max(widthPct, 4.0);

    const barColor = isComplete
      ? 'from-emerald-600/80 to-emerald-500/80 border-emerald-400/40 text-emerald-200'
      : isRefined
      ? 'from-amber-600/80 to-amber-500/80 border-amber-400/40 text-amber-200 animate-pulse'
      : task.status === 'In Progress'
      ? 'from-sky-600/80 to-blue-500/80 border-sky-400/40 text-sky-200'
      : 'from-indigo-600/80 to-purple-500/80 border-indigo-400/40 text-indigo-200';

    return `
      <div class="grid grid-cols-12 items-center hover:bg-[var(--bg-elevated)]/40 p-1.5 rounded-lg transition group">
        <!-- Task Meta -->
        <div class="col-span-5 md:col-span-4 pr-3 flex items-center justify-between overflow-hidden">
          <div class="flex items-center space-x-2 overflow-hidden cursor-pointer" onclick="window.visualizer.openDrawer('${task.id}')">
            <span class="font-mono text-xs font-bold text-indigo-400 group-hover:text-white shrink-0">${task.id}</span>
            <span class="text-xs text-slate-300 truncate" title="${esc(task.title)}">${esc(task.title)}</span>
          </div>
          <div class="flex items-center gap-1 shrink-0 ml-2">
            ${prs.map(pr => `
              <span class="px-1 py-0.2 rounded text-[9px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${pr}</span>
            `).join('')}
          </div>
        </div>

        <!-- Gantt Bar Lane -->
        <div class="col-span-7 md:col-span-8 relative h-7 flex items-center bg-black/20 rounded px-1 gantt-grid"
             style="background-size: ${colWidth.toFixed(2)}% 100%;">
          <div onclick="window.visualizer.openDrawer('${task.id}')"
               style="margin-left: ${startPct.toFixed(2)}%; width: ${widthPct.toFixed(2)}%;"
               class="gantt-bar h-5.5 rounded-md bg-gradient-to-r ${barColor} border text-[11px] font-semibold flex items-center justify-between px-2 cursor-pointer shadow-sm overflow-hidden select-none"
               title="${task.id}: ${esc(task.title)} (${task.status}) - ${mKey}">
            <span class="truncate font-mono text-[10px]">${task.target_release ? `v${task.target_release}` : (task.status === 'Refined' ? 'Active' : task.status)}</span>
            ${task.dependencies && task.dependencies.length > 0 ? `<span class="text-[9px] font-mono opacity-80">⛓️${task.dependencies.length}</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }

  window.visualizer.renderGantt = renderGantt;
  window.visualizer.setGanttGroup = (val) => {
    window.visualizer.state.gantt.groupBy = val;
    window.visualizer.renderGantt(document.getElementById('view-content'), window.visualizer.state);
  };
})();
