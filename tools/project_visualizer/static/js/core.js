// --- Runefoble Project Content Visualizer: Core Engine ---
(function() {
  window.visualizer = window.visualizer || {};

  const state = {
    data: window.INITIAL_PROJECT_DATA || {},
    currentTab: 'traceability',
    filters: {
      hideDone: false,
      bc: 'all',
      milestone: 'all',
      persona: 'all',
      status: 'all',
      nodeType: 'all',
      search: '',
    },
    graph: {
      zoom: 1,
      panX: 0,
      panY: 0,
      layout: 'network', // network | hierarchy
      selectedId: null,
    },
    gantt: {
      groupBy: 'milestone', // milestone | bc
      timeScale: 'weeks',
    },
    selectedNode: null,
    syncPaused: false,
  };

  window.visualizer.state = state;

  function init() {
    renderKPICounters();
    setupKeyboardShortcuts();
    setupTheme();

    // Check URL hash for tab
    const hash = window.location.hash.replace('#', '');
    const validTabs = ['traceability', 'graph', 'gantt', 'roadmap', 'kanban', 'prds', 'personas', 'adrs'];
    if (validTabs.includes(hash)) {
      switchTab(hash);
    } else {
      switchTab('traceability');
    }

    if (window.IS_LIVE_SERVER) {
      startLiveSync();
    }
  }

  function renderKPICounters() {
    const d = state.data;
    if (!d || !d.metrics) return;
    const m = d.metrics;
    const setEl = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };
    setEl('kpi-complete', m.completed_tasks ?? 0);
    setEl('kpi-refined', m.refined_tasks ?? 0);
    setEl('kpi-stories', m.total_stories ?? 0);
    setEl('kpi-prds', m.total_prds ?? 0);
    setEl('kpi-adrs', m.total_adrs ?? 0);
  }

  function switchTab(tabId, preserveScroll = false) {
    state.currentTab = tabId;
    window.location.hash = tabId;

    // Update tab bar buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
      const isTarget = btn.getAttribute('data-tab') === tabId;
      btn.className = isTarget
        ? 'tab-btn px-3 py-1.5 rounded-md font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 flex items-center gap-1.5 transition'
        : 'tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition';
    });

    const container = document.getElementById('view-content');
    if (!container) return;

    const savedScrollY = preserveScroll ? window.scrollY : 0;

    switch (tabId) {
      case 'traceability':
        if (window.visualizer.renderTraceability) window.visualizer.renderTraceability(container, state);
        break;
      case 'graph':
        if (window.visualizer.renderGraph) window.visualizer.renderGraph(container, state);
        break;
      case 'gantt':
        if (window.visualizer.renderGantt) window.visualizer.renderGantt(container, state);
        break;
      case 'roadmap':
        if (window.visualizer.renderRoadmap) window.visualizer.renderRoadmap(container, state);
        break;
      case 'kanban':
        if (window.visualizer.renderKanban) window.visualizer.renderKanban(container, state);
        break;
      case 'prds':
        if (window.visualizer.renderPRDs) window.visualizer.renderPRDs(container, state);
        break;
      case 'personas':
        if (window.visualizer.renderPersonas) window.visualizer.renderPersonas(container, state);
        break;
      case 'adrs':
        if (window.visualizer.renderADRs) window.visualizer.renderADRs(container, state);
        break;
      default:
        break;
    }

    if (preserveScroll && savedScrollY > 0) {
      window.scrollTo({ top: savedScrollY, behavior: 'instant' });
    }
  }

  // --- Dynamic Live Sync Engine with Scroll Preservation ---
  function startLiveSync() {
    setInterval(async () => {
      if (state.syncPaused) return;
      try {
        const verRes = await fetch('/api/version');
        if (!verRes.ok) return;
        const ver = await verRes.json();
        if (ver.data_hash && ver.data_hash === state.data.data_hash) {
          // Data is unchanged; do not touch DOM or scroll
          return;
        }

        // Fresh data detected!
        const res = await fetch('/api/data');
        if (res.ok) {
          const fresh = await res.json();
          const scrollY = window.scrollY;
          const openNodeId = state.selectedNode ? state.selectedNode.id : null;

          state.data = fresh;
          renderKPICounters();
          switchTab(state.currentTab, true);

          if (openNodeId && window.visualizer.openDrawer) {
            window.visualizer.openDrawer(openNodeId, false);
          }

          window.scrollTo({ top: scrollY, behavior: 'instant' });

          const statusEl = document.getElementById('sync-status');
          if (statusEl) {
            statusEl.classList.add('bg-indigo-500/20', 'text-indigo-400');
            setTimeout(() => statusEl.classList.remove('bg-indigo-500/20', 'text-indigo-400'), 1200);
          }
        }
      } catch (err) {
        // Quiet on network drops
      }
    }, 2500);
  }

  function toggleSyncPause() {
    state.syncPaused = !state.syncPaused;
    const statusEl = document.getElementById('sync-status');
    const labelEl = document.getElementById('sync-status-label');
    if (statusEl && labelEl) {
      if (state.syncPaused) {
        statusEl.className = 'flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 cursor-pointer';
        labelEl.textContent = 'Sync Paused';
      } else {
        statusEl.className = 'flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 cursor-pointer';
        labelEl.textContent = 'Dynamic Sync';
      }
    }
  }

  function setupTheme() {
    const isLight = localStorage.getItem('rf_theme') === 'light';
    if (isLight) {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
    updateThemeIcons();
  }

  function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    if (isDark) {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
      localStorage.setItem('rf_theme', 'light');
    } else {
      document.documentElement.classList.remove('light');
      document.documentElement.classList.add('dark');
      localStorage.setItem('rf_theme', 'dark');
    }
    updateThemeIcons();
  }

  function updateThemeIcons() {
    const isDark = document.documentElement.classList.contains('dark');
    const sun = document.getElementById('theme-icon-sun');
    const moon = document.getElementById('theme-icon-moon');
    if (sun && moon) {
      if (isDark) {
        sun.classList.add('hidden');
        moon.classList.remove('hidden');
      } else {
        sun.classList.remove('hidden');
        moon.classList.add('hidden');
      }
    }
  }

  function setupKeyboardShortcuts() {
    window.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleOmnibar(true);
      } else if (e.key === 'Escape') {
        if (window.visualizer.closeDrawer) window.visualizer.closeDrawer();
        toggleOmnibar(false);
      }
    });
  }

  function toggleOmnibar(show) {
    const backdrop = document.getElementById('omnibar-backdrop');
    const modal = document.getElementById('omnibar-modal');
    const input = document.getElementById('omnibar-input');
    if (!backdrop || !modal) return;

    if (show) {
      backdrop.classList.remove('hidden');
      setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
      modal.classList.remove('hidden');
      if (input) {
        input.value = '';
        input.focus();
        handleOmnibarSearch('');
      }
    } else {
      backdrop.classList.add('opacity-0');
      modal.classList.add('hidden');
      setTimeout(() => backdrop.classList.add('hidden'), 200);
    }
  }

  function handleOmnibarSearch(query) {
    const resultsEl = document.getElementById('omnibar-results');
    if (!resultsEl) return;
    const q = (query || '').toLowerCase().trim();
    const d = state.data;
    if (!d) return;

    const items = [];
    (d.tasks || []).forEach(t => {
      const prMatches = (t.prs || []).some(pr => pr.toLowerCase().includes(q));
      const commitMatches = (t.commits || []).some(c => c.hash.toLowerCase().includes(q) || c.subject.toLowerCase().includes(q));
      if (!q || t.id.toLowerCase().includes(q) || t.title.toLowerCase().includes(q) || prMatches || commitMatches) {
        items.push({ id: t.id, title: t.title, type: 'TASK', badge: t.status, prs: t.prs });
      }
    });
    (d.stories || []).forEach(s => {
      if (!q || s.id.toLowerCase().includes(q) || s.title.toLowerCase().includes(q) || s.persona.toLowerCase().includes(q)) {
        items.push({ id: s.id, title: s.title, type: 'STORY', badge: s.persona });
      }
    });
    (d.prds || []).forEach(p => {
      if (!q || p.id.toLowerCase().includes(q) || p.title.toLowerCase().includes(q)) {
        items.push({ id: p.id, title: p.title, type: 'PRD', badge: p.status });
      }
    });
    (d.adrs || []).forEach(a => {
      if (!q || a.id.toLowerCase().includes(q) || a.title.toLowerCase().includes(q) || a.domain.toLowerCase().includes(q)) {
        items.push({ id: a.id, title: a.title, type: 'ADR', badge: a.domain });
      }
    });

    if (items.length === 0) {
      resultsEl.innerHTML = '<div class="p-4 text-center text-xs text-muted">No entities match your query</div>';
      return;
    }

    resultsEl.innerHTML = items.slice(0, 20).map(item => `
      <div onclick="window.visualizer.openDrawer('${item.id}'); window.visualizer.toggleOmnibar(false);"
           class="p-2.5 rounded-lg hover:bg-[var(--bg-elevated)] flex items-center justify-between cursor-pointer group transition">
        <div class="flex items-center space-x-2.5 overflow-hidden">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${item.type}</span>
          <span class="font-mono text-xs font-semibold text-white group-hover:text-indigo-400">${item.id}</span>
          <span class="text-xs text-muted truncate">${escapeHtml(item.title)}</span>
        </div>
        <div class="flex items-center gap-1.5">
          ${(item.prs && item.prs.length > 0) ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${item.prs[0]}</span>` : ''}
          <span class="text-[11px] font-medium text-muted">${item.badge}</span>
        </div>
      </div>
    `).join('');
  }

  function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  window.visualizer.init = init;
  window.visualizer.switchTab = switchTab;
  window.visualizer.toggleTheme = toggleTheme;
  window.visualizer.toggleOmnibar = toggleOmnibar;
  window.visualizer.handleOmnibarSearch = handleOmnibarSearch;
  window.visualizer.toggleSyncPause = toggleSyncPause;
  window.visualizer.escapeHtml = escapeHtml;
  window.visualizer.renderKPICounters = renderKPICounters;

  document.addEventListener('DOMContentLoaded', init);
})();
