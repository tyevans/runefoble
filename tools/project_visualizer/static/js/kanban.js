// --- Runefoble Project Content Visualizer: Kanban Pipeline ---
(function() {
  window.visualizer = window.visualizer || {};

  function renderKanban(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;
    const tasks = d.tasks || [];

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

    const completeTasks = filteredTasks.filter(t => t.status === 'Complete');
    const refinedTasks = filteredTasks.filter(t => t.status === 'Refined');
    const proposedTasks = filteredTasks.filter(t => t.status === 'Proposed');

    const totalComplete = tasks.filter(t => t.status === 'Complete').length;

    // Unique bounded contexts
    const bcs = Array.from(new Set(tasks.map(t => t.target_bc).filter(Boolean))).sort();

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Header & Filter Toolbar -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[var(--bg-card)] border border-subtle">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>Backlog Engineering Pipeline</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono border border-indigo-500/20">${filteredTasks.length} Visible Tasks</span>
            </h2>
            <p class="text-xs text-muted">Kanban workflow tracking Complete, Refined JIT buffer, and Proposed tasks.</p>
          </div>

          <!-- Filters -->
          <div class="flex flex-wrap items-center gap-2.5">
            <!-- Hide Done Toggle -->
            <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" id="kanban-hide-done" class="rounded accent-indigo-500" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'kanban')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span>
              ${state.filters.hideDone ? `<span class="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">${totalComplete} hidden</span>` : ''}
            </label>

            <!-- Bounded Context Filter -->
            <select class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition"
                    onchange="window.visualizer.setFilter('bc', this.value, 'kanban')">
              <option value="all" ${state.filters.bc === 'all' ? 'selected' : ''}>All Bounded Contexts</option>
              ${bcs.map(bc => `<option value="${bc}" ${state.filters.bc === bc ? 'selected' : ''}>${bc}</option>`).join('')}
            </select>

            <!-- Text Search Filter -->
            <div class="relative">
              <input type="text" placeholder="Filter tasks or PR #..." value="${esc(state.filters.search)}"
                     class="px-3 py-1.5 pl-8 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition w-44"
                     oninput="window.visualizer.setFilter('search', this.value, 'kanban')">
              <svg class="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>
          </div>
        </div>

        <!-- Kanban Board Columns -->
        <div class="grid grid-cols-1 ${state.filters.hideDone ? 'md:grid-cols-2' : 'md:grid-cols-3'} gap-5">
          ${!state.filters.hideDone ? `
            <!-- COMPLETE COLUMN -->
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-subtle">
                <div class="flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                  <h3 class="font-bold text-sm text-white">Complete</h3>
                </div>
                <span class="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${completeTasks.length}</span>
              </div>
              <div class="space-y-3 max-h-[78vh] overflow-y-auto pr-1">
                ${completeTasks.map(t => renderTaskCard(t, esc)).join('')}
              </div>
            </div>
          ` : ''}

          <!-- REFINED COLUMN -->
          <div class="space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-subtle">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></span>
                <h3 class="font-bold text-sm text-white">Refined (JIT Buffer)</h3>
              </div>
              <span class="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">${refinedTasks.length}</span>
            </div>
            <div class="space-y-3 max-h-[78vh] overflow-y-auto pr-1">
              ${refinedTasks.length > 0
                ? refinedTasks.map(t => renderTaskCard(t, esc)).join('')
                : '<div class="p-6 rounded-xl border border-dashed border-subtle text-center text-xs text-muted">Ready buffer empty. JIT refine candidates from Proposed.</div>'}
            </div>
          </div>

          <!-- PROPOSED COLUMN -->
          <div class="space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-subtle">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
                <h3 class="font-bold text-sm text-white">Proposed</h3>
              </div>
              <span class="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${proposedTasks.length}</span>
            </div>
            <div class="space-y-3 max-h-[78vh] overflow-y-auto pr-1">
              ${proposedTasks.map(t => renderTaskCard(t, esc)).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function renderTaskCard(t, esc) {
    const prs = t.prs || [];
    const commits = t.commits || [];

    return `
      <div onclick="window.visualizer.openDrawer('${t.id}')"
           class="p-4 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-indigo-500/50 hover:shadow-lg transition cursor-pointer group flex flex-col justify-between space-y-3">
        <div>
          <div class="flex items-center justify-between gap-2 mb-1.5">
            <span class="font-mono text-xs font-bold text-indigo-400 group-hover:text-white transition">${t.id}</span>
            <div class="flex items-center gap-1.5">
              ${prs.map(pr => `
                <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 flex items-center gap-0.5" title="Pull Request ${pr}">
                  <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                  ${pr}
                </span>
              `).join('')}
              ${(commits.length > 0 && prs.length === 0) ? `
                <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700" title="${commits.length} git commits">
                  ${commits.length}c
                </span>
              ` : ''}
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--bg-elevated)] text-muted">${t.target_bc || 'platform'}</span>
            </div>
          </div>
          <h4 class="text-xs font-semibold text-white leading-snug line-clamp-2">${esc(t.title)}</h4>
        </div>

        <div class="flex items-center justify-between text-[11px] text-muted pt-2 border-t border-subtle">
          <div class="flex items-center gap-1">
            ${(t.governing_adrs && t.governing_adrs.length > 0)
              ? `<span class="font-mono text-[10px] text-purple-400">${t.governing_adrs[0]}</span>`
              : ''}
            ${(t.microfrontends && t.microfrontends.length > 0)
              ? `<span class="font-mono text-[10px] text-purple-300">UI</span>`
              : ''}
          </div>
          <span class="text-[10px] font-mono">${t.target_release ? `v${t.target_release}` : ''}</span>
        </div>
      </div>
    `;
  }

  window.visualizer.renderKanban = renderKanban;
  window.visualizer.setFilter = (key, val, tab) => {
    window.visualizer.state.filters[key] = val;
    window.visualizer.switchTab(tab || window.visualizer.state.currentTab, true);
  };
})();
