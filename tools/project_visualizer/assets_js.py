"""Client-side interactive JavaScript application for project visualizer."""

from __future__ import annotations


def get_client_js() -> str:
    """Return client-side JavaScript engine."""
    return """
// Runefoble Project Visualizer Client Engine
(function() {
  const state = {
    data: window.INITIAL_PROJECT_DATA || {},
    currentTab: 'traceability',
    selectedNode: null, // { type, id }
    filters: {
      persona: 'all',
      status: 'all',
      bc: 'all',
      search: ''
    },
    activeDrawerItem: null,
    isDark: true
  };

  // --- INITIALIZATION ---
  function init() {
    // Load theme preference
    const savedTheme = localStorage.getItem('rf_theme');
    if (savedTheme === 'light') {
      setTheme(false);
    } else {
      setTheme(true);
    }

    renderKPICounters();
    switchTab('traceability');
    setupKeyboardShortcuts();

    if (window.IS_LIVE_SERVER) {
      startLiveSync();
    }
  }

  // --- THEME SWITCHER ---
  function setTheme(isDark) {
    state.isDark = isDark;
    const html = document.documentElement;
    const iconSun = document.getElementById('theme-icon-sun');
    const iconMoon = document.getElementById('theme-icon-moon');

    if (isDark) {
      html.classList.add('dark');
      html.classList.remove('light');
      iconSun?.classList.add('hidden');
      iconMoon?.classList.remove('hidden');
      localStorage.setItem('rf_theme', 'dark');
    } else {
      html.classList.remove('dark');
      html.classList.add('light');
      iconSun?.classList.remove('hidden');
      iconMoon?.classList.add('hidden');
      localStorage.setItem('rf_theme', 'light');
    }
  }

  function toggleTheme() {
    setTheme(!state.isDark);
  }

  // --- KPI COUNTERS ---
  function renderKPICounters() {
    const m = state.data.metrics || {};
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val ?? 0;
    };
    setTxt('kpi-complete', m.completed_tasks);
    setTxt('kpi-refined', m.refined_tasks);
    setTxt('kpi-stories', m.total_stories);
    setTxt('kpi-prds', m.total_prds);
    setTxt('kpi-adrs', m.total_adrs);
  }

  // --- TAB NAVIGATION ---
  function switchTab(tabId) {
    state.currentTab = tabId;
    document.querySelectorAll('.tab-btn').forEach(btn => {
      if (btn.dataset.tab === tabId) {
        btn.className = 'tab-btn px-3 py-1.5 rounded-md font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 flex items-center gap-1.5 transition';
      } else {
        btn.className = 'tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition';
      }
    });

    const container = document.getElementById('view-content');
    if (!container) return;

    if (tabId === 'traceability') {
      container.innerHTML = renderTraceabilityView();
      setupTraceabilityInteractions();
    } else if (tabId === 'roadmap') {
      container.innerHTML = renderRoadmapView();
    } else if (tabId === 'kanban') {
      container.innerHTML = renderKanbanView();
    } else if (tabId === 'prds') {
      container.innerHTML = renderPRDView();
    } else if (tabId === 'personas') {
      container.innerHTML = renderPersonasView();
    } else if (tabId === 'adrs') {
      container.innerHTML = renderADRView();
    }
  }

  // --- VIEW 1: TRACEABILITY NETWORK ---
  function renderTraceabilityView() {
    const personas = state.data.personas || [];
    const stories = state.data.stories || [];
    const prds = state.data.prds || [];
    const tasks = state.data.tasks || [];
    const adrs = state.data.adrs || [];

    // Filter nodes based on state.filters
    const filteredStories = stories.filter(s => {
      if (state.filters.persona !== 'all' && !s.persona.toLowerCase().includes(state.filters.persona)) return false;
      return true;
    });

    const filteredTasks = tasks.filter(t => {
      if (state.filters.status !== 'all' && t.status.toLowerCase() !== state.filters.status.toLowerCase()) return false;
      if (state.filters.bc !== 'all' && t.target_bc !== state.filters.bc) return false;
      return true;
    });

    return `
      <div class="space-y-6">
        <!-- Traceability Controls Bar -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div class="flex items-center gap-3">
            <span class="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path></svg>
              Filter Graph:
            </span>
            <!-- Persona Filter -->
            <select onchange="window.app.setGraphFilter('persona', this.value)" class="bg-[var(--bg-elevated)] border border-subtle rounded-lg px-2.5 py-1 text-xs text-muted focus:outline-none">
              <option value="all" ${state.filters.persona === 'all' ? 'selected' : ''}>All Personas</option>
              <option value="evelyn" ${state.filters.persona === 'evelyn' ? 'selected' : ''}>Evelyn (DM)</option>
              <option value="marcus" ${state.filters.persona === 'marcus' ? 'selected' : ''}>Marcus (Player)</option>
              <option value="sarah" ${state.filters.persona === 'sarah' ? 'selected' : ''}>Sarah (Absentee)</option>
              <option value="devon" ${state.filters.persona === 'devon' ? 'selected' : ''}>Devon (Streamer)</option>
              <option value="alex" ${state.filters.persona === 'alex' ? 'selected' : ''}>Alex (Dev)</option>
            </select>
            <!-- Task Status Filter -->
            <select onchange="window.app.setGraphFilter('status', this.value)" class="bg-[var(--bg-elevated)] border border-subtle rounded-lg px-2.5 py-1 text-xs text-muted focus:outline-none">
              <option value="all" ${state.filters.status === 'all' ? 'selected' : ''}>All Task Statuses</option>
              <option value="complete" ${state.filters.status === 'complete' ? 'selected' : ''}>Complete (34)</option>
              <option value="refined" ${state.filters.status === 'refined' ? 'selected' : ''}>Refined (7)</option>
              <option value="proposed" ${state.filters.status === 'proposed' ? 'selected' : ''}>Proposed (17)</option>
            </select>
          </div>

          <div class="flex items-center space-x-2 text-xs">
            <button onclick="window.app.clearGraphSelection()" class="px-2.5 py-1 rounded bg-[var(--bg-elevated)] border border-subtle hover:border-strong text-muted hover:text-white transition">Reset Highlights</button>
            <span class="text-muted">Click any node to trace Redstring lineage.</span>
          </div>
        </div>

        <!-- Active Breadcrumb Bar -->
        <div id="trace-breadcrumbs" class="px-4 py-2.5 rounded-lg bg-indigo-500/5 border border-indigo-500/20 text-xs font-mono text-indigo-300 flex items-center gap-2 overflow-x-auto">
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
                  <div onclick="window.app.selectTraceNode('persona', '${p.id}')" data-node-type="persona" data-node-id="${p.id}" class="node-card p-3 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-indigo-500/50 cursor-pointer shadow-sm relative group">
                    <div class="flex items-center space-x-2.5">
                      <div class="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-white text-xs shadow-sm" style="background-color: ${p.avatar_color}">
                        ${p.name[0]}
                      </div>
                      <div class="overflow-hidden">
                        <h4 class="text-xs font-bold truncate group-hover:text-indigo-400 transition">${p.name}</h4>
                        <p class="text-[10px] text-muted truncate">${p.role}</p>
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
                  <div onclick="window.app.selectTraceNode('story', '${s.id}')" data-node-type="story" data-node-id="${s.id}" class="node-card p-2.5 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-violet-500/50 cursor-pointer shadow-sm group">
                    <div class="flex items-center justify-between text-[10px] font-mono">
                      <span class="font-bold text-violet-400">${s.id}</span>
                      <span class="text-muted truncate max-w-[90px]">${s.persona.split(' ')[0]}</span>
                    </div>
                    <h5 class="text-xs font-medium mt-1 line-clamp-2 leading-tight group-hover:text-white transition">${s.title}</h5>
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
                  <div onclick="window.app.selectTraceNode('prd', '${prd.id}')" data-node-type="prd" data-node-id="${prd.id}" class="node-card p-3 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-cyan-500/50 cursor-pointer shadow-sm group">
                    <div class="flex items-center justify-between text-[10px] font-mono">
                      <span class="font-bold text-cyan-400">${prd.id}</span>
                      <span class="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${prd.status}</span>
                    </div>
                    <h5 class="text-xs font-semibold mt-1 group-hover:text-cyan-300 transition line-clamp-2">${prd.title}</h5>
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
                  <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Backlog Tasks (${filteredTasks.length})
                </span>
              </div>
              <div class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                ${filteredTasks.slice(0, 35).map(t => {
                  const statusColor = t.status === 'Complete' ? 'emerald' : (t.status === 'Refined' ? 'amber' : 'indigo');
                  return `
                    <div onclick="window.app.selectTraceNode('task', '${t.id}')" data-node-type="task" data-node-id="${t.id}" class="node-card p-2.5 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-${statusColor}-500/50 cursor-pointer shadow-sm group">
                      <div class="flex items-center justify-between text-[10px] font-mono">
                        <span class="font-bold text-${statusColor}-400">${t.id}</span>
                        <span class="px-1.5 py-0.2 rounded bg-${statusColor}-500/10 text-${statusColor}-400 border border-${statusColor}-500/20">${t.status}</span>
                      </div>
                      <h5 class="text-xs font-medium mt-1 line-clamp-2 leading-tight group-hover:text-white transition">${t.title}</h5>
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
                  <div onclick="window.app.selectTraceNode('adr', '${adr.id}')" data-node-type="adr" data-node-id="${adr.id}" class="node-card p-3 rounded-xl bg-[var(--bg-card)] border border-subtle hover:border-amber-500/50 cursor-pointer shadow-sm group">
                    <div class="flex items-center justify-between text-[10px] font-mono">
                      <span class="font-bold text-amber-400">${adr.id}</span>
                      <span class="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">${adr.domain}</span>
                    </div>
                    <h5 class="text-xs font-semibold mt-1 group-hover:text-amber-300 transition line-clamp-2">${adr.title}</h5>
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

  // --- TRACEABILITY HIGHLIGHT LOGIC ---
  function selectTraceNode(type, id) {
    state.selectedNode = { type, id };
    const edges = state.data.edges || [];

    // Find all directly and transitively connected nodes
    const connected = new Set();
    connected.add(`${type}:${id}`);

    // Upstream & downstream traversal
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

    // Apply classes to DOM cards
    document.querySelectorAll('.node-card').forEach(card => {
      const cType = card.dataset.nodeType;
      const cId = card.dataset.nodeId;
      const key = `${cType}:${cId}`;

      if (connected.has(key)) {
        card.classList.remove('dimmed');
        card.classList.add('highlighted');
      } else {
        card.classList.remove('highlighted');
        card.classList.add('dimmed');
      }
    });

    // Update Breadcrumb text
    const breadcrumbEl = document.getElementById('breadcrumb-text');
    if (breadcrumbEl) {
      breadcrumbEl.innerHTML = `Active Focus: <strong class="text-white">${id}</strong> (${type}) — <span class="text-emerald-400">${connected.size} nodes</span> illuminated across the Redstring dependency thread. Double click to open full reader.`;
    }

    // Open detail drawer on double click or click
    openDrawer(type, id);
  }

  function clearGraphSelection() {
    state.selectedNode = null;
    document.querySelectorAll('.node-card').forEach(card => {
      card.classList.remove('dimmed');
      card.classList.remove('highlighted');
    });
    const breadcrumbEl = document.getElementById('breadcrumb-text');
    if (breadcrumbEl) {
      breadcrumbEl.textContent = 'Select any persona, user story, PRD, task, or ADR to illuminate its end-to-end dependency thread.';
    }
  }

  function setupTraceabilityInteractions() {
    // Optional canvas bezier lines or column scrolls
  }

  // --- VIEW 2: ROADMAP & MILESTONES ---
  function renderRoadmapView() {
    const milestones = state.data.milestones || [];
    const tasks = state.data.tasks || [];
    const completeCount = tasks.filter(t => t.status === 'Complete').length;

    return `
      <div class="space-y-6">
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 class="text-lg font-bold tracking-tight">Platform Roadmap & Delivery Horizon</h2>
              <p class="text-xs text-muted mt-1">Multi-milestone delivery progression from UV monorepo foundation to broadcast studio.</p>
            </div>
            <div class="flex items-center space-x-4">
              <div class="text-right">
                <span class="text-2xl font-black text-indigo-400">${completeCount} / ${tasks.length}</span>
                <span class="block text-[10px] uppercase font-mono text-muted">Tasks Completed (${Math.round((completeCount/tasks.length)*100)}%)</span>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          ${milestones.map((m, idx) => {
            const isDone = m.status === 'Complete';
            const isCurrent = m.status === 'Current';
            const badgeColor = isDone ? 'emerald' : (isCurrent ? 'indigo' : 'slate');
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

                  <h3 class="text-base font-bold mt-3">${m.name}</h3>

                  <div class="w-full bg-[var(--bg-elevated)] h-2 rounded-full mt-3 overflow-hidden">
                    <div class="bg-${badgeColor}-500 h-full rounded-full transition-all duration-500" style="width: ${m.completion_pct}%"></div>
                  </div>

                  <div class="mt-4 space-y-2">
                    <h4 class="text-xs font-semibold text-muted uppercase tracking-wider">Governing Platform Tasks</h4>
                    <div class="flex flex-wrap gap-1.5">
                      ${m.task_ids.map(tid => `
                        <span onclick="window.app.openDrawer('task', '${tid}')" class="px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-subtle text-[11px] font-mono text-indigo-300 hover:border-indigo-400 cursor-pointer transition">
                          ${tid}
                        </span>
                      `).join('')}
                    </div>
                  </div>
                </div>

                <div class="mt-6 pt-4 border-t border-subtle flex items-center justify-between text-xs text-muted">
                  <span>Milestone Stage ${idx + 1} of 4</span>
                  <button onclick="window.app.switchTab('kanban')" class="text-indigo-400 hover:underline">View Pipeline Tasks →</button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  // --- VIEW 3: KANBAN BACKLOG PIPELINE ---
  function renderKanbanView() {
    const tasks = state.data.tasks || [];
    const bcs = Array.from(new Set(tasks.map(t => t.target_bc).filter(Boolean)));

    const completeTasks = tasks.filter(t => t.status === 'Complete');
    const refinedTasks = tasks.filter(t => t.status === 'Refined');
    const proposedTasks = tasks.filter(t => t.status === 'Proposed');

    return `
      <div class="space-y-6">
        <!-- Kanban Filter Header -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs font-semibold text-muted">Filter Bounded Context:</span>
            <button onclick="window.app.setKanbanBC('all')" class="px-2.5 py-1 rounded text-xs font-mono font-medium ${state.filters.bc === 'all' ? 'bg-indigo-500 text-white' : 'bg-[var(--bg-elevated)] text-muted hover:text-white'} transition">All</button>
            ${bcs.map(bc => `
              <button onclick="window.app.setKanbanBC('${bc}')" class="px-2.5 py-1 rounded text-xs font-mono font-medium ${state.filters.bc === bc ? 'bg-indigo-500 text-white' : 'bg-[var(--bg-elevated)] text-muted hover:text-white'} transition">${bc}</button>
            `).join('')}
          </div>
          <div class="text-xs text-muted">
            Buffer: <strong class="text-amber-400">${refinedTasks.length} Refined</strong> (Optimal: 2–3)
          </div>
        </div>

        <!-- 3-Column Kanban Board -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">

          <!-- Column 1: Refined Ready Buffer -->
          <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 flex flex-col h-[750px]">
            <div class="flex items-center justify-between pb-3 border-b border-subtle">
              <div class="flex items-center space-x-2">
                <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <h3 class="text-xs font-bold uppercase tracking-wider">Refined (Ready Buffer)</h3>
              </div>
              <span class="px-2 py-0.5 rounded-full text-xs font-mono bg-amber-500/10 text-amber-400 font-bold border border-amber-500/20">${refinedTasks.length}</span>
            </div>
            <div class="flex-1 overflow-y-auto space-y-3 mt-3 pr-1">
              ${refinedTasks.map(t => renderTaskCard(t, 'amber')).join('')}
            </div>
          </div>

          <!-- Column 2: Proposed Pool -->
          <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 flex flex-col h-[750px]">
            <div class="flex items-center justify-between pb-3 border-b border-subtle">
              <div class="flex items-center space-x-2">
                <span class="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
                <h3 class="text-xs font-bold uppercase tracking-wider">Proposed (Candidate Pool)</h3>
              </div>
              <span class="px-2 py-0.5 rounded-full text-xs font-mono bg-indigo-500/10 text-indigo-400 font-bold border border-indigo-500/20">${proposedTasks.length}</span>
            </div>
            <div class="flex-1 overflow-y-auto space-y-3 mt-3 pr-1">
              ${proposedTasks.map(t => renderTaskCard(t, 'indigo')).join('')}
            </div>
          </div>

          <!-- Column 3: Complete -->
          <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 flex flex-col h-[750px]">
            <div class="flex items-center justify-between pb-3 border-b border-subtle">
              <div class="flex items-center space-x-2">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <h3 class="text-xs font-bold uppercase tracking-wider">Complete (Shipped)</h3>
              </div>
              <span class="px-2 py-0.5 rounded-full text-xs font-mono bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">${completeTasks.length}</span>
            </div>
            <div class="flex-1 overflow-y-auto space-y-3 mt-3 pr-1">
              ${completeTasks.map(t => renderTaskCard(t, 'emerald')).join('')}
            </div>
          </div>

        </div>
      </div>
    `;
  }

  function renderTaskCard(t, theme) {
    if (state.filters.bc !== 'all' && t.target_bc !== state.filters.bc) return '';
    return `
      <div onclick="window.app.openDrawer('task', '${t.id}')" class="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-subtle hover:border-${theme}-500/50 cursor-pointer shadow-sm transition hover:shadow-md group">
        <div class="flex items-center justify-between text-[11px] font-mono">
          <span class="font-bold text-${theme}-400">${t.id}</span>
          <span class="text-muted text-[10px]">${t.target_release || 'v0.1.0'}</span>
        </div>
        <h4 class="text-xs font-semibold mt-1 group-hover:text-white transition leading-snug">${t.title}</h4>
        <p class="text-[11px] text-muted mt-1.5 line-clamp-2">${t.summary || ''}</p>

        <div class="mt-3 flex items-center justify-between pt-2 border-t border-subtle/50 text-[10px] font-mono">
          <span class="px-1.5 py-0.5 rounded bg-[var(--bg-card)] text-indigo-300 font-medium">${t.target_bc}</span>
          <div class="flex items-center gap-1 text-muted">
            ${t.governing_adrs.length ? `<span>${t.governing_adrs.length} ADRs</span>` : ''}
            ${t.microfrontends.length ? `<span class="text-pink-400 font-bold">UI</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }

  // --- VIEW 4: PRDs & FEATURE MATRIX ---
  function renderPRDView() {
    const prds = state.data.prds || [];
    const features = state.data.features || [];

    return `
      <div class="space-y-6">
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm">
          <h2 class="text-base font-bold">Product Requirements & Speculative Feature Inventory</h2>
          <p class="text-xs text-muted mt-1">Checkable user outcomes, PRD definitions, and multi-tier feature capability catalog (P0 Launch MVP, P1 Beta, P2 Horizon).</p>
        </div>

        <!-- PRD Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          ${prds.map(p => `
            <div onclick="window.app.openDrawer('prd', '${p.id}')" class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm hover:border-cyan-500/50 cursor-pointer transition flex flex-col justify-between group">
              <div>
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-cyan-400">${p.id}</span>
                  <span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px] font-medium">${p.status}</span>
                </div>
                <h3 class="text-sm font-bold mt-2 group-hover:text-cyan-300 transition">${p.title}</h3>
                <p class="text-xs text-muted mt-2 line-clamp-3">${p.problem_statement || ''}</p>

                <div class="mt-4 space-y-1.5">
                  <span class="text-[10px] font-semibold uppercase tracking-wider text-muted font-mono">Checkable Outcomes (${p.outcomes.length})</span>
                  <ul class="text-[11px] text-muted space-y-1">
                    ${p.outcomes.slice(0, 3).map(o => `<li class="truncate flex items-center gap-1.5"><span class="w-1 h-1 rounded-full bg-cyan-400"></span>${o}</li>`).join('')}
                  </ul>
                </div>
              </div>

              <div class="mt-5 pt-3 border-t border-subtle flex items-center justify-between text-[11px] font-mono text-muted">
                <span>${p.linked_stories.length} User Stories</span>
                <span class="text-cyan-400 font-semibold group-hover:translate-x-0.5 transition">Details →</span>
              </div>
            </div>
          `).join('')}
        </div>

        <!-- Feature Capability Inventory Table -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm mt-8">
          <div class="flex items-center justify-between pb-4 border-b border-subtle">
            <div>
              <h3 class="text-sm font-bold">Speculative Feature Capability Matrix (${features.length} Features)</h3>
              <p class="text-xs text-muted">Categorized by functional domain and milestone tier.</p>
            </div>
          </div>
          <div class="overflow-x-auto mt-4">
            <table class="w-full text-left text-xs">
              <thead class="bg-[var(--bg-elevated)] text-muted font-mono text-[11px] uppercase border-b border-subtle">
                <tr>
                  <th class="py-2.5 px-3">ID</th>
                  <th class="py-2.5 px-3">Feature Name</th>
                  <th class="py-2.5 px-3">Domain</th>
                  <th class="py-2.5 px-3">Tier</th>
                  <th class="py-2.5 px-3">Governing Systems</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-subtle font-normal">
                ${features.map(f => {
                  const isP0 = f.tier.includes('P0');
                  const tierColor = isP0 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
                  return `
                    <tr class="hover:bg-[var(--bg-elevated)]/50 transition">
                      <td class="py-2 px-3 font-mono font-bold text-indigo-300">${f.id}</td>
                      <td class="py-2 px-3 font-semibold text-white">${f.name}</td>
                      <td class="py-2 px-3 text-muted">${f.domain}</td>
                      <td class="py-2 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-mono border ${tierColor}">${f.tier}</span></td>
                      <td class="py-2 px-3 font-mono text-muted text-[11px]">${f.governing_systems.join(', ')}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  // --- VIEW 5: PERSONAS & STORIES ---
  function renderPersonasView() {
    const personas = state.data.personas || [];
    const stories = state.data.stories || [];

    return `
      <div class="space-y-6">
        <!-- Personas Grid -->
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
          ${personas.map(p => `
            <div onclick="window.app.openDrawer('persona', '${p.id}')" class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 shadow-sm hover:border-indigo-500/50 cursor-pointer transition flex flex-col justify-between group">
              <div>
                <div class="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white shadow-md text-base" style="background-color: ${p.avatar_color}">
                  ${p.name[0]}
                </div>
                <h3 class="text-sm font-bold mt-3 group-hover:text-indigo-400 transition">${p.name}</h3>
                <p class="text-xs text-muted mt-0.5">${p.role}</p>
                <div class="mt-3 text-[11px] text-muted italic line-clamp-2">"${p.quote}"</div>
              </div>
              <div class="mt-4 pt-3 border-t border-subtle flex items-center justify-between text-xs font-mono">
                <span class="text-indigo-400 font-semibold">${p.story_ids.length} Stories</span>
                <span class="text-muted group-hover:text-white transition">Dossier →</span>
              </div>
            </div>
          `).join('')}
        </div>

        <!-- 40 User Stories Catalog -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm mt-8">
          <div class="flex items-center justify-between pb-4 border-b border-subtle">
            <div>
              <h3 class="text-sm font-bold">Accepted User Stories Catalog (${stories.length} Stories)</h3>
              <p class="text-xs text-muted">Persona-grounded end-to-end acceptance criteria and scenarios.</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
            ${stories.map(s => `
              <div onclick="window.app.openDrawer('story', '${s.id}')" class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle hover:border-violet-500/50 cursor-pointer transition shadow-sm group">
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-violet-400">${s.id}</span>
                  <span class="text-muted text-[11px]">${s.persona}</span>
                </div>
                <h4 class="text-xs font-bold mt-1.5 group-hover:text-white transition leading-snug">${s.title}</h4>
                <div class="mt-2 text-xs text-muted pl-2 border-l-2 border-violet-500/50 italic line-clamp-2">
                  "As a ${s.as_a}, I want to ${s.i_want}..."
                </div>
                <div class="mt-3 flex items-center justify-between text-[11px] font-mono text-muted">
                  <span>${s.acceptance_criteria.length} Criteria</span>
                  <span class="text-violet-400 font-semibold">Inspect Story →</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  // --- VIEW 6: ADR ARCHITECTURE RADAR ---
  function renderADRView() {
    const adrs = state.data.adrs || [];
    return `
      <div class="space-y-6">
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm">
          <h2 class="text-base font-bold">Architectural Decision Records (ADRs)</h2>
          <p class="text-xs text-muted mt-1">Zanzibar authorization, event sourcing, UV monorepo, Lit microfrontends, and Kubernetes-first infrastructure.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          ${adrs.map(adr => `
            <div onclick="window.app.openDrawer('adr', '${adr.id}')" class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm hover:border-amber-500/50 cursor-pointer transition flex flex-col justify-between group">
              <div>
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-amber-400">${adr.id}</span>
                  <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-semibold">${adr.domain}</span>
                </div>
                <h3 class="text-sm font-bold mt-2 group-hover:text-amber-300 transition">${adr.title}</h3>
                <p class="text-xs text-muted mt-2 line-clamp-3">${adr.context || ''}</p>

                <div class="mt-4 p-2.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-[11px] text-muted">
                  <strong class="text-amber-400 uppercase font-mono text-[9px] block">Decision Summary</strong>
                  <span class="line-clamp-2 mt-0.5">${adr.decision || ''}</span>
                </div>
              </div>

              <div class="mt-5 pt-3 border-t border-subtle flex items-center justify-between text-[11px] font-mono text-muted">
                <span>${adr.implementing_tasks.length} Implemented Tasks</span>
                <span class="text-amber-400 font-semibold group-hover:translate-x-0.5 transition">Read ADR →</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // --- DETAIL DRAWER & MARKDOWN VIEWER ---
  function openDrawer(type, id) {
    let item = null;
    if (type === 'task') item = (state.data.tasks || []).find(x => x.id === id);
    else if (type === 'story') item = (state.data.stories || []).find(x => x.id === id);
    else if (type === 'prd') item = (state.data.prds || []).find(x => x.id === id);
    else if (type === 'adr') item = (state.data.adrs || []).find(x => x.id === id);
    else if (type === 'persona') item = (state.data.personas || []).find(x => x.id === id);

    if (!item) return;
    state.activeDrawerItem = item;

    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    const badge = document.getElementById('drawer-type-badge');
    const titleId = document.getElementById('drawer-id');
    const body = document.getElementById('drawer-body');
    const filepathEl = document.getElementById('drawer-filepath');

    if (badge) badge.textContent = type.toUpperCase();
    if (titleId) titleId.textContent = item.id || item.name;

    if (filepathEl) {
      filepathEl.innerHTML = `<span>File:</span> <span class="text-indigo-400 font-semibold truncate">${item.file_path || 'docs/project/...'}</span>`;
    }

    // Build Drawer Body Content
    if (body) {
      body.innerHTML = renderDrawerContent(type, item);
    }

    // Slide in
    backdrop?.classList.remove('hidden');
    setTimeout(() => backdrop?.classList.remove('opacity-0'), 10);
    drawer?.classList.remove('translate-x-full');
  }

  function renderDrawerContent(type, item) {
    let html = `
      <div>
        <h1 class="text-xl font-bold tracking-tight text-white">${item.title || item.name}</h1>
        <div class="mt-2 flex items-center gap-2 flex-wrap">
          ${item.status ? `<span class="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${item.status}</span>` : ''}
          ${item.target_bc ? `<span class="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${item.target_bc}</span>` : ''}
          ${item.domain ? `<span class="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">${item.domain}</span>` : ''}
        </div>
      </div>
    `;

    // Persona Dossier
    if (type === 'persona') {
      html += `
        <div class="space-y-4">
          <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle">
            <h4 class="text-xs font-semibold uppercase text-muted font-mono">Archetype & Role</h4>
            <p class="text-sm font-medium mt-1">${item.role}</p>
          </div>
          <div>
            <h4 class="text-xs font-semibold uppercase text-muted font-mono mb-2">Pain Points</h4>
            <ul class="space-y-1.5 text-xs text-muted">
              ${(item.pain_points || []).map(p => `<li class="flex items-start gap-2"><span class="text-rose-400">•</span><span>${p}</span></li>`).join('')}
            </ul>
          </div>
          <div>
            <h4 class="text-xs font-semibold uppercase text-muted font-mono mb-2">Goals with Runefoble</h4>
            <ul class="space-y-1.5 text-xs text-muted">
              ${(item.goals || []).map(g => `<li class="flex items-start gap-2"><span class="text-emerald-400">•</span><span>${g}</span></li>`).join('')}
            </ul>
          </div>
        </div>
      `;
    }

    // Markdown Body preview
    if (item.raw_markdown) {
      html += `
        <div class="pt-4 border-t border-subtle">
          <h4 class="text-xs font-semibold uppercase text-muted font-mono mb-3">Rendered Document Content</h4>
          <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle text-xs text-muted leading-relaxed font-sans space-y-3 whitespace-pre-wrap">
${escapeHtml(item.raw_markdown)}
          </div>
        </div>
      `;
    }

    return html;
  }

  function closeDrawer() {
    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    drawer?.classList.add('translate-x-full');
    backdrop?.classList.add('opacity-0');
    setTimeout(() => backdrop?.classList.add('hidden'), 300);
    state.activeDrawerItem = null;
  }

  function copyDrawerFilepath() {
    if (state.activeDrawerItem && state.activeDrawerItem.file_path) {
      navigator.clipboard.writeText(state.activeDrawerItem.file_path);
      alert('Filepath copied: ' + state.activeDrawerItem.file_path);
    }
  }

  // --- OMNIBAR SEARCH ---
  function toggleOmnibar(show) {
    const modal = document.getElementById('omnibar-modal');
    const backdrop = document.getElementById('omnibar-backdrop');
    const input = document.getElementById('omnibar-input');

    if (show) {
      backdrop?.classList.remove('hidden');
      setTimeout(() => backdrop?.classList.remove('opacity-0'), 10);
      modal?.classList.remove('hidden');
      input?.focus();
      input.value = '';
      handleOmnibarSearch('');
    } else {
      modal?.classList.add('hidden');
      backdrop?.classList.add('opacity-0');
      setTimeout(() => backdrop?.classList.add('hidden'), 200);
    }
  }

  function handleOmnibarSearch(q) {
    const resultsEl = document.getElementById('omnibar-results');
    if (!resultsEl) return;
    const query = (q || '').toLowerCase().trim();

    const pool = [
      ...(state.data.tasks || []).map(x => ({ type: 'task', id: x.id, title: x.title })),
      ...(state.data.stories || []).map(x => ({ type: 'story', id: x.id, title: x.title })),
      ...(state.data.prds || []).map(x => ({ type: 'prd', id: x.id, title: x.title })),
      ...(state.data.adrs || []).map(x => ({ type: 'adr', id: x.id, title: x.title })),
      ...(state.data.personas || []).map(x => ({ type: 'persona', id: x.id, title: x.name }))
    ];

    const matches = pool.filter(item => {
      if (!query) return true;
      return item.id.toLowerCase().includes(query) || item.title.toLowerCase().includes(query);
    }).slice(0, 15);

    resultsEl.innerHTML = matches.map(m => `
      <div onclick="window.app.openDrawer('${m.type}', '${m.id}'); window.app.toggleOmnibar(false);" class="p-2.5 rounded-lg hover:bg-[var(--bg-elevated)] cursor-pointer flex items-center justify-between transition">
        <div class="flex items-center space-x-2">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-indigo-500/10 text-indigo-400">${m.type}</span>
          <span class="text-xs font-semibold text-white">${m.id}</span>
          <span class="text-xs text-muted truncate max-w-[360px]">${m.title}</span>
        </div>
        <span class="text-[10px] text-muted font-mono">Select ↵</span>
      </div>
    `).join('') || '<div class="p-4 text-xs text-muted text-center">No matching project records found.</div>';
  }

  function setupKeyboardShortcuts() {
    window.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleOmnibar(true);
      } else if (e.key === 'Escape') {
        closeDrawer();
        toggleOmnibar(false);
      }
    });
  }

  // --- DYNAMIC LIVE SYNC ENGINE ---
  function startLiveSync() {
    setInterval(async () => {
      try {
        const res = await fetch('/api/data');
        if (res.ok) {
          const fresh = await res.json();
          if (fresh.last_updated !== state.data.last_updated) {
            state.data = fresh;
            renderKPICounters();
            switchTab(state.currentTab);
            const statusEl = document.getElementById('sync-status');
            if (statusEl) {
              statusEl.classList.add('bg-indigo-500/20', 'text-indigo-400');
              setTimeout(() => statusEl.classList.remove('bg-indigo-500/20', 'text-indigo-400'), 1000);
            }
          }
        }
      } catch (err) {
        // quiet error on connection drop
      }
    }, 2000);
  }

  function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // --- PUBLIC API EXPORTS ---
  window.app = {
    switchTab,
    selectTraceNode,
    clearGraphSelection,
    openDrawer,
    closeDrawer,
    copyDrawerFilepath,
    toggleTheme,
    toggleOmnibar,
    handleOmnibarSearch,
    setGraphFilter: (key, val) => { state.filters[key] = val; switchTab('traceability'); },
    setKanbanBC: (bc) => { state.filters.bc = bc; switchTab('kanban'); }
  };

  document.addEventListener('DOMContentLoaded', init);
})();
"""
