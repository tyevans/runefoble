// --- Runefoble Project Content Visualizer: Roadmap & Milestones ---
(function() {
  window.visualizer = window.visualizer || {};

  function renderRoadmap(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;

    const milestones = d.milestones || [];
    const tasks = d.tasks || [];
    const completeCount = tasks.filter(t => t.status === 'Complete').length;

    const filteredMilestones = milestones.filter(m => {
      if (state.filters.hideDone && m.status === 'Complete') return false;
      return true;
    });

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Header -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <span>Platform Roadmap & Delivery Horizon</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono border border-indigo-500/20">${filteredMilestones.length} Milestones</span>
            </h2>
            <p class="text-xs text-muted mt-1">Multi-milestone delivery progression from platform foundation to broadcast studio.</p>
          </div>

          <div class="flex items-center space-x-4">
            <!-- Hide Done Toggle -->
            <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'roadmap')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Complete</span>
            </label>

            <div class="text-right">
              <span class="text-2xl font-black text-indigo-400">${completeCount} / ${tasks.length}</span>
              <span class="block text-[10px] uppercase font-mono text-muted">Tasks Shipped (${Math.round((completeCount / Math.max(tasks.length, 1)) * 100)}%)</span>
            </div>
          </div>
        </div>

        <!-- Milestones Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          ${filteredMilestones.map(m => {
            const isDone = m.status === 'Complete';
            const isCurrent = m.status === 'Current' || m.status === 'In Progress';
            const badgeColor = isDone ? 'emerald' : (isCurrent ? 'amber' : 'slate');
            return `
              <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm relative overflow-hidden flex flex-col justify-between">
                <div class="absolute top-0 right-0 w-32 h-32 bg-${badgeColor}-500/5 rounded-bl-full pointer-events-none"></div>
                <div>
                  <div class="flex items-center justify-between">
                    <span class="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-${badgeColor}-500/10 text-${badgeColor}-400 border border-${badgeColor}-500/20">
                      ${m.id}: ${m.status}
                    </span>
                    <span class="text-xs font-mono font-bold text-muted">${m.completion_pct}% Delivered</span>
                  </div>

                  <h3 class="text-base font-bold text-white mt-3">${esc(m.name)}</h3>

                  <div class="w-full bg-[var(--bg-elevated)] h-2 rounded-full mt-3 overflow-hidden">
                    <div class="bg-${badgeColor}-500 h-full rounded-full transition-all duration-500" style="width: ${m.completion_pct}%"></div>
                  </div>

                  <div class="mt-4 space-y-2">
                    <h4 class="text-xs font-semibold text-muted uppercase tracking-wider">Governing Platform Tasks</h4>
                    <div class="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
                      ${m.task_ids.map(tid => `
                        <span onclick="window.visualizer.openDrawer('${tid}')" class="px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-subtle text-[11px] font-mono text-indigo-300 hover:border-indigo-400 cursor-pointer transition">
                          ${tid}
                        </span>
                      `).join('')}
                    </div>
                  </div>
                </div>

                <div class="mt-6 pt-4 border-t border-subtle flex items-center justify-between text-xs text-muted">
                  <span>${m.task_ids.length} Linked Tasks</span>
                  <button onclick="window.visualizer.switchTab('gantt')" class="text-indigo-400 hover:text-white transition font-mono">View in Gantt →</button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  window.visualizer.renderRoadmap = renderRoadmap;
})();
