// --- Runefoble Project Content Visualizer: Gantt Chart & Delivery Timeline ---
(function() {
  window.visualizer = window.visualizer || {};

  function renderGantt(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;
    const tasks = d.tasks || [];
    const milestones = d.milestones || [];

    // Filter tasks
    const filteredTasks = tasks.filter(t => {
      if (state.filters.hideDone && t.status === 'Complete') return false;
      if (state.filters.bc !== 'all' && t.target_bc !== state.filters.bc) return false;
      if (state.filters.milestone !== 'all' && t.milestone !== state.filters.milestone) return false;
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
      const mNames = {
        'M1': 'Milestone 1: Platform Foundation & Core Loop',
        'M2': 'Milestone 2: Live Collaborative Alpha (Current)',
        'M3': 'Milestone 3: AI DM & Ecosystem Expansion',
        'M4': 'Milestone 4: Broadcast Studio & Community Platform',
      };

      // Assign default milestones based on status or release if unassigned
      filteredTasks.forEach(t => {
        let m = t.milestone;
        if (!m) {
          if (t.status === 'Complete') m = 'M1';
          else if (t.status === 'Refined') m = 'M2';
          else {
            const rel = t.target_release || '';
            if (rel.startsWith('0.1') || rel.startsWith('0.2')) m = 'M2';
            else if (rel.startsWith('0.3')) m = 'M3';
            else m = 'M4';
          }
        }
        const mKey = m.startsWith('M') ? m.slice(0, 2).toUpperCase() : 'M2';
        const groupTitle = mNames[mKey] || m;
        if (!groups[groupTitle]) groups[groupTitle] = [];
        groups[groupTitle].push(t);
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
            <div class="col-span-7 md:col-span-8 grid grid-cols-4 text-center">
              <span class="border-r border-subtle/50 text-emerald-400">Phase 1: Foundations</span>
              <span class="border-r border-subtle/50 text-amber-400 font-semibold">Phase 2: Alpha (Now)</span>
              <span class="border-r border-subtle/50 text-indigo-400">Phase 3: AI DM</span>
              <span class="text-purple-400">Phase 4: Studio</span>
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
                  ${groups[gName].map(task => renderGanttRow(task, esc)).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  function renderGanttRow(task, esc) {
    const prs = task.prs || [];
    const isComplete = task.status === 'Complete';
    const isRefined = task.status === 'Refined';

    // Calculate bar position along Phase 1 (0-25%), Phase 2 (25-50%), Phase 3 (50-75%), Phase 4 (75-100%)
    let startPct = 25;
    let widthPct = 22;

    if (isComplete) {
      const num = parseInt(task.id.replace('TASK-', ''), 10) || 0;
      startPct = Math.min(20, (num % 25));
      widthPct = 18;
    } else if (isRefined) {
      startPct = 27;
      widthPct = 20;
    } else {
      const rel = task.target_release || '';
      if (rel.startsWith('0.2')) {
        startPct = 35;
        widthPct = 18;
      } else if (rel.startsWith('0.3')) {
        startPct = 52;
        widthPct = 20;
      } else {
        startPct = 76;
        widthPct = 20;
      }
    }

    const barColor = isComplete
      ? 'from-emerald-600/80 to-emerald-500/80 border-emerald-400/40 text-emerald-200'
      : isRefined
      ? 'from-amber-600/80 to-amber-500/80 border-amber-400/40 text-amber-200 animate-pulse'
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
        <div class="col-span-7 md:col-span-8 relative h-7 flex items-center bg-black/20 rounded px-1 gantt-grid">
          <div onclick="window.visualizer.openDrawer('${task.id}')"
               style="margin-left: ${startPct}%; width: ${widthPct}%;"
               class="gantt-bar h-5.5 rounded-md bg-gradient-to-r ${barColor} border text-[11px] font-semibold flex items-center justify-between px-2 cursor-pointer shadow-sm overflow-hidden select-none"
               title="${task.id}: ${esc(task.title)} (${task.status})">
            <span class="truncate font-mono text-[10px]">${task.target_release ? `v${task.target_release}` : task.status}</span>
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
