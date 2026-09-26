// --- Runefoble Project Content Visualizer: Multi-Column Traceability Matrix ---
(function() {
  window.visualizer = window.visualizer || {};

  function renderTraceability(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;

    const personas = d.personas || [];
    const stories = d.stories || [];
    const prds = d.prds || [];
    const tasks = d.tasks || [];
    const adrs = d.adrs || [];

    // Filter stories
    const filteredStories = stories.filter(s => {
      if (state.filters.persona !== 'all' && !s.persona.toLowerCase().includes(state.filters.persona)) return false;
      return true;
    });

    // Filter tasks
    const filteredTasks = tasks.filter(t => {
      if (state.filters.hideDone && t.status === 'Complete') return false;
      if (state.filters.status !== 'all' && t.status.toLowerCase() !== state.filters.status.toLowerCase()) return false;
      if (state.filters.bc !== 'all' && t.target_bc !== state.filters.bc) return false;
      return true;
    });

    const totalComplete = tasks.filter(t => t.status === 'Complete').length;

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Traceability Controls Bar -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div class="flex flex-wrap items-center gap-3">
            <span class="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path></svg>
              Filter Trace:
            </span>

            <!-- Hide Done Toggle -->
            <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'traceability')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span>
              ${state.filters.hideDone ? `<span class="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">${totalComplete} hidden</span>` : ''}
            </label>

            <!-- Persona Filter -->
            <select onchange="window.visualizer.setFilter('persona', this.value, 'traceability')" class="bg-[var(--bg-elevated)] border border-subtle rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none">
              <option value="all" ${state.filters.persona === 'all' ? 'selected' : ''}>All Personas</option>
              <option value="evelyn" ${state.filters.persona === 'evelyn' ? 'selected' : ''}>Evelyn (DM)</option>
              <option value="marcus" ${state.filters.persona === 'marcus' ? 'selected' : ''}>Marcus (Player)</option>
              <option value="sarah" ${state.filters.persona === 'sarah' ? 'selected' : ''}>Sarah (Absentee)</option>
              <option value="devon" ${state.filters.persona === 'devon' ? 'selected' : ''}>Devon (Streamer)</option>
              <option value="alex" ${state.filters.persona === 'alex' ? 'selected' : ''}>Alex (Dev)</option>
            </select>

            <!-- Task Status Filter -->
            <select onchange="window.visualizer.setFilter('status', this.value, 'traceability')" class="bg-[var(--bg-elevated)] border border-subtle rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none">
              <option value="all" ${state.filters.status === 'all' ? 'selected' : ''}>All Task Statuses</option>
              <option value="complete" ${state.filters.status === 'complete' ? 'selected' : ''}>Complete</option>
              <option value="refined" ${state.filters.status === 'refined' ? 'selected' : ''}>Refined</option>
              <option value="proposed" ${state.filters.status === 'proposed' ? 'selected' : ''}>Proposed</option>
            </select>
          </div>

          <div class="flex items-center space-x-2 text-xs">
            <button onclick="window.visualizer.clearGraphSelection()" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong text-muted hover:text-white transition">Reset Highlights</button>
            <span class="text-muted hidden sm:inline">Click node to trace lineage. Double-click opens drawer.</span>
          </div>
        </div>

        <!-- Active Breadcrumb Bar -->
        <div id="trace-breadcrumbs" class="px-4 py-2.5 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-xs font-mono text-indigo-300 flex items-center gap-2 overflow-x-auto">
          <span class="font-bold uppercase tracking-wider text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400">Lineage:</span>
          <span id="breadcrumb-text">Select any persona, user story, PRD, task, or ADR to illuminate its end-to-end dependency thread.</span>
        </div>

        <!-- Traceability Multi-Column Flow Container -->
        <div class="relative overflow-x-auto pb-6">
          <div class="grid grid-cols-1 md:grid-cols-5 gap-4 min-w-[1000px] relative z-10" id="network-columns">

            <!-- Column 1: Personas -->
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-subtle">
                <span class="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-indigo-500"></span> Personas (${personas.length})
                </span>
              </div>
              <div class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                ${personas.map(p => `
                  <div onclick="window.visualizer.selectTraceNode('persona', '${p.id}')" ondblclick="window.visualizer.openDrawer('${p.id}')" data-node-type="persona" data-node-id="${p.id}" class="node-card p-3 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-indigo-500/50 cursor-pointer shadow-sm relative group">
                    <div class="flex items-center space-x-2.5">
                      <div class="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-white text-xs shadow-sm" style="background-color: ${p.avatar_color}">
                        ${p.name[0]}
                      </div>
                      <div class="overflow-hidden">
                        <h4 class="text-xs font-bold truncate group-hover:text-indigo-400 transition">${esc(p.name)}</h4>
                        <p class="text-[10px] text-muted truncate">${esc(p.role)}</p>
                      </div>
                    </div>
                    <div class="mt-2 text-[10px] font-mono text-muted flex items-center justify-between">
                      <span>${p.story_ids.length} Stories</span>
                      <span class="text-indigo-400">Trace →</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Column 2: User Stories -->
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-subtle">
                <span class="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-violet-500"></span> User Stories (${filteredStories.length})
                </span>
              </div>
              <div class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                ${filteredStories.slice(0, 30).map(s => `
                  <div onclick="window.visualizer.selectTraceNode('story', '${s.id}')" ondblclick="window.visualizer.openDrawer('${s.id}')" data-node-type="story" data-node-id="${s.id}" class="node-card p-2.5 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-violet-500/50 cursor-pointer shadow-sm group">
                    <div class="flex items-center justify-between text-[10px] font-mono">
                      <span class="font-bold text-violet-400">${s.id}</span>
                      <span class="text-muted truncate max-w-[90px]">${esc(s.persona.split(' ')[0])}</span>
                    </div>
                    <h5 class="text-xs font-medium mt-1 line-clamp-2 leading-tight group-hover:text-white transition">${esc(s.title)}</h5>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Column 3: PRDs -->
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-subtle">
                <span class="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-cyan-500"></span> PRD Outcomes (${prds.length})
                </span>
              </div>
              <div class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                ${prds.map(prd => `
                  <div onclick="window.visualizer.selectTraceNode('prd', '${prd.id}')" ondblclick="window.visualizer.openDrawer('${prd.id}')" data-node-type="prd" data-node-id="${prd.id}" class="node-card p-3 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-cyan-500/50 cursor-pointer shadow-sm group">
                    <div class="flex items-center justify-between text-[10px] font-mono">
                      <span class="font-bold text-cyan-400">${prd.id}</span>
                      <span class="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${prd.status}</span>
                    </div>
                    <h5 class="text-xs font-semibold mt-1 group-hover:text-cyan-300 transition line-clamp-2">${esc(prd.title)}</h5>
                    <div class="mt-2 text-[10px] text-muted flex items-center justify-between font-mono">
                      <span>${prd.linked_stories.length} Stories</span>
                      <span>${prd.implementing_tasks.length} Tasks</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Column 4: Tasks -->
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-subtle">
                <span class="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Tasks (${filteredTasks.length})
                </span>
              </div>
              <div class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                ${filteredTasks.slice(0, 35).map(t => {
                  const statusColor = t.status === 'Complete' ? 'emerald' : (t.status === 'Refined' ? 'amber' : 'indigo');
                  const prs = t.prs || [];
                  return `
                    <div onclick="window.visualizer.selectTraceNode('task', '${t.id}')" ondblclick="window.visualizer.openDrawer('${t.id}')" data-node-type="task" data-node-id="${t.id}" class="node-card p-2.5 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-${statusColor}-500/50 cursor-pointer shadow-sm group">
                      <div class="flex items-center justify-between text-[10px] font-mono">
                        <span class="font-bold text-${statusColor}-400">${t.id}</span>
                        <div class="flex items-center gap-1">
                          ${prs.map(pr => `<span class="px-1 py-0.2 rounded text-[9px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${pr}</span>`).join('')}
                          <span class="px-1.5 py-0.2 rounded bg-${statusColor}-500/10 text-${statusColor}-400 border border-${statusColor}-500/20">${t.status}</span>
                        </div>
                      </div>
                      <h5 class="text-xs font-medium mt-1 line-clamp-2 leading-tight group-hover:text-white transition">${esc(t.title)}</h5>
                      <div class="mt-1.5 flex items-center gap-1 flex-wrap">
                        <span class="px-1.5 py-0.5 rounded bg-[var(--bg-elevated)] text-[9px] font-mono text-muted">${t.target_bc}</span>
                      </div>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>

            <!-- Column 5: ADRs -->
            <div class="space-y-3">
              <div class="flex items-center justify-between pb-2 border-b border-subtle">
                <span class="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-amber-500"></span> Governing ADRs (${adrs.length})
                </span>
              </div>
              <div class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                ${adrs.map(adr => `
                  <div onclick="window.visualizer.selectTraceNode('adr', '${adr.id}')" ondblclick="window.visualizer.openDrawer('${adr.id}')" data-node-type="adr" data-node-id="${adr.id}" class="node-card p-3 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-amber-500/50 cursor-pointer shadow-sm group">
                    <div class="flex items-center justify-between text-[10px] font-mono">
                      <span class="font-bold text-amber-400">${adr.id}</span>
                      <span class="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${adr.domain}</span>
                    </div>
                    <h5 class="text-xs font-semibold mt-1 group-hover:text-amber-300 transition line-clamp-2">${esc(adr.title)}</h5>
                    <div class="mt-2 text-[10px] text-muted flex items-center justify-between font-mono">
                      <span>${adr.implementing_tasks.length} Implemented</span>
                      <span class="text-amber-400">View ADR →</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>

          </div>
        </div>
      </div>
    `;
  }

  function selectTraceNode(type, id) {
    const edges = window.visualizer.state.data.edges || [];
    const connected = new Set();
    connected.add(`${type}:${id}`);

    let changed = true;
    while (changed) {
      changed = false;
      edges.forEach(e => {
        const sKey = `${e.source_type}:${e.source_id}`;
        const tKey = `${e.target_type}:${e.target_id}`;
        if (connected.has(sKey) && !connected.has(tKey)) {
          connected.add(tKey);
          changed = true;
        }
        if (connected.has(tKey) && !connected.has(sKey)) {
          connected.add(sKey);
          changed = true;
        }
      });
    }

    document.querySelectorAll('.node-card').forEach(card => {
      const cType = card.dataset.nodeType;
      const cId = card.dataset.nodeId;
      const key = `${cType}:${cId}`;

      if (cId === id) {
        card.classList.add('highlighted');
        card.classList.remove('dimmed');
      } else if (connected.has(key)) {
        card.classList.remove('dimmed', 'highlighted');
      } else {
        card.classList.add('dimmed');
        card.classList.remove('highlighted');
      }
    });

    const bText = document.getElementById('breadcrumb-text');
    if (bText) {
      bText.innerHTML = `Active trace focused on <strong class="text-white">${type.toUpperCase()} ${id}</strong> (${connected.size} linked records illuminated). Double-click node to inspect file.`;
    }
  }

  function clearGraphSelection() {
    document.querySelectorAll('.node-card').forEach(card => {
      card.classList.remove('dimmed', 'highlighted');
    });
    const bText = document.getElementById('breadcrumb-text');
    if (bText) {
      bText.textContent = 'Select any persona, user story, PRD, task, or ADR to illuminate its end-to-end dependency thread.';
    }
  }

  window.visualizer.renderTraceability = renderTraceability;
  window.visualizer.selectTraceNode = selectTraceNode;
  window.visualizer.clearGraphSelection = clearGraphSelection;

  window.app = window.app || {};
  window.app.selectTraceNode = selectTraceNode;
  window.app.clearGraphSelection = clearGraphSelection;
})();
