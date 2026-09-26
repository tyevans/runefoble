"""HTML shell and layout template for Runefoble Project Content Visualizer."""

from __future__ import annotations


def render_html_shell(initial_data_json: str, is_live_server: bool = False) -> str:
    """Generate complete standalone or live-connected HTML dashboard."""
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Runefoble // Project Matrix & Lore Engine</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --bg-canvas: #0B0F17;
      --bg-card: #111827;
      --bg-elevated: #1F2937;
      --border-subtle: #1F2937;
      --border-strong: #374151;
      --text-main: #F9FAFB;
      --text-muted: #9CA3AF;
      --accent-indigo: #6366F1;
      --accent-amber: #F59E0B;
      --accent-emerald: #10B981;
      --accent-violet: #8B5CF6;
      --accent-cyan: #06B6D4;
      --accent-rose: #F43F5E;
    }}
    html.light {{
      --bg-canvas: #F8FAFC;
      --bg-card: #FFFFFF;
      --bg-elevated: #F1F5F9;
      --border-subtle: #E2E8F0;
      --border-strong: #CBD5E1;
      --text-main: #0F172A;
      --text-muted: #64748B;
      --accent-indigo: #4F46E5;
      --accent-amber: #D97706;
      --accent-emerald: #059669;
      --accent-violet: #7C3AED;
      --accent-cyan: #0891B2;
      --accent-rose: #E11D48;
    }}
    body {{
      background-color: var(--bg-canvas);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      overflow-x: hidden;
    }}
    .bg-card {{ background-color: var(--bg-card); }}
    .bg-elevated {{ background-color: var(--bg-elevated); }}
    .border-subtle {{ border-color: var(--border-subtle); }}
    .border-strong {{ border-color: var(--border-strong); }}
    .text-muted {{ color: var(--text-muted); }}

    /* Custom scrollbars */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: var(--border-strong); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--accent-indigo); }}

    /* Node highlight transitions */
    .node-card {{
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .node-card.dimmed {{
      opacity: 0.25;
      filter: grayscale(80%);
      transform: scale(0.98);
    }}
    .node-card.highlighted {{
      opacity: 1;
      box-shadow: 0 0 0 2px var(--accent-indigo), 0 8px 24px -4px rgba(99, 102, 241, 0.3);
      transform: scale(1.02);
      z-index: 10;
    }}
    .connection-line {{
      transition: stroke 0.3s ease, stroke-width 0.3s ease, opacity 0.3s ease;
    }}
  </style>
</head>
<body class="min-h-screen antialiased flex flex-col">

  <!-- TOP HEADER & BRAND -->
  <header class="sticky top-0 z-40 bg-[var(--bg-card)]/90 backdrop-blur-md border-b border-subtle px-4 lg:px-8 py-3.5 flex items-center justify-between shadow-sm">
    <div class="flex items-center space-x-4">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-amber-500 flex items-center justify-center font-bold text-white shadow-md text-sm tracking-wider">
          RF
        </div>
        <div>
          <h1 class="text-base font-bold tracking-tight flex items-center gap-2">
            <span>Runefoble</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono font-medium border border-indigo-500/20">Project Visualizer</span>
          </h1>
          <p class="text-xs text-muted">Speculative Lore, PRDs, User Stories & Engineering Backlog</p>
        </div>
      </div>

      <!-- Quick KPI Counters -->
      <div class="hidden xl:flex items-center space-x-2 pl-6 border-l border-subtle text-xs">
        <div class="px-2.5 py-1 rounded bg-[var(--bg-elevated)] flex items-center gap-1.5 font-mono">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span id="kpi-complete" class="font-semibold text-emerald-400">34</span>
          <span class="text-muted">Done</span>
        </div>
        <div class="px-2.5 py-1 rounded bg-[var(--bg-elevated)] flex items-center gap-1.5 font-mono">
          <span class="w-2 h-2 rounded-full bg-amber-500"></span>
          <span id="kpi-refined" class="font-semibold text-amber-400">7</span>
          <span class="text-muted">Refined Buffer</span>
        </div>
        <div class="px-2.5 py-1 rounded bg-[var(--bg-elevated)] flex items-center gap-1.5 font-mono">
          <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
          <span id="kpi-stories" class="font-semibold text-indigo-400">40</span>
          <span class="text-muted">Stories</span>
        </div>
        <div class="px-2.5 py-1 rounded bg-[var(--bg-elevated)] flex items-center gap-1.5 font-mono">
          <span class="w-2 h-2 rounded-full bg-cyan-500"></span>
          <span id="kpi-prds" class="font-semibold text-cyan-400">12</span>
          <span class="text-muted">PRDs</span>
        </div>
        <div class="px-2.5 py-1 rounded bg-[var(--bg-elevated)] flex items-center gap-1.5 font-mono">
          <span class="w-2 h-2 rounded-full bg-purple-500"></span>
          <span id="kpi-adrs" class="font-semibold text-purple-400">13</span>
          <span class="text-muted">ADRs</span>
        </div>
      </div>
    </div>

    <!-- Actions & Global Tools -->
    <div class="flex items-center space-x-3">
      <!-- Search Omnibar Trigger -->
      <button onclick="window.app.toggleOmnibar(true)" class="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong text-xs text-muted transition shadow-inner">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        <span class="hidden sm:inline">Search docs/project...</span>
        <kbd class="px-1.5 py-0.5 rounded bg-[var(--bg-card)] border border-subtle text-[10px] font-mono">⌘K</kbd>
      </button>

      <!-- Live Sync Status -->
      <div id="sync-status" class="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" title="Auto-reloads on file changes">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="hidden md:inline">Dynamic Sync</span>
      </div>

      <!-- Theme Switcher -->
      <button onclick="window.app.toggleTheme()" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong text-muted hover:text-white transition" title="Toggle Light / Dark mode">
        <svg id="theme-icon-sun" class="w-4 h-4 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
        <svg id="theme-icon-moon" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
      </button>
    </div>
  </header>

  <!-- NAVIGATION TABS -->
  <nav class="sticky top-[61px] z-30 bg-[var(--bg-card)]/80 backdrop-blur-md border-b border-subtle px-4 lg:px-8 flex items-center justify-between text-xs font-medium">
    <div class="flex items-center space-x-1 sm:space-x-2 py-2 overflow-x-auto" id="tab-nav">
      <button onclick="window.app.switchTab('traceability')" data-tab="traceability" class="tab-btn px-3 py-1.5 rounded-md font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 flex items-center gap-1.5 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        Traceability Network
      </button>
      <button onclick="window.app.switchTab('roadmap')" data-tab="roadmap" class="tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
        Milestones & Roadmap
      </button>
      <button onclick="window.app.switchTab('kanban')" data-tab="kanban" class="tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
        Backlog Pipeline
      </button>
      <button onclick="window.app.switchTab('prds')" data-tab="prds" class="tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        PRDs & Feature Matrix
      </button>
      <button onclick="window.app.switchTab('personas')" data-tab="personas" class="tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
        Personas & Stories
      </button>
      <button onclick="window.app.switchTab('adrs')" data-tab="adrs" class="tab-btn px-3 py-1.5 rounded-md text-muted hover:text-white flex items-center gap-1.5 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
        ADR Architecture Radar
      </button>
    </div>

    <div class="hidden sm:flex items-center space-x-2 text-muted text-[11px] font-mono">
      <span>Docs Root:</span>
      <span class="text-indigo-400">docs/project/</span>
    </div>
  </nav>

  <!-- MAIN VIEWPORT CONTAINER -->
  <main class="flex-1 p-4 lg:p-8 max-w-7xl mx-auto w-full relative">
    <div id="view-content" class="transition-opacity duration-200">
      <!-- Injected dynamically by assets_js.py -->
    </div>
  </main>

  <!-- SLIDE-OVER DETAIL DRAWER -->
  <div id="drawer-backdrop" onclick="window.app.closeDrawer()" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden opacity-0 transition-opacity duration-300"></div>
  <aside id="drawer" class="fixed right-0 top-0 bottom-0 w-full sm:w-[560px] lg:w-[680px] bg-[var(--bg-card)] border-l border-subtle z-50 shadow-2xl transform translate-x-full transition-transform duration-300 ease-in-out flex flex-col">
    <div class="p-5 border-b border-subtle flex items-center justify-between bg-[var(--bg-elevated)]">
      <div class="flex items-center space-x-2.5">
        <span id="drawer-type-badge" class="px-2 py-0.5 rounded text-[11px] font-mono font-semibold uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">TASK</span>
        <h2 id="drawer-id" class="text-base font-bold font-mono">TASK-0001</h2>
      </div>
      <button onclick="window.app.closeDrawer()" class="p-1.5 rounded-md hover:bg-subtle text-muted hover:text-white transition">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    </div>

    <!-- Drawer Content Scroll Area -->
    <div id="drawer-body" class="flex-1 overflow-y-auto p-6 space-y-6 text-sm">
      <!-- Populated dynamically -->
    </div>

    <!-- Drawer Footer -->
    <div class="p-4 border-t border-subtle bg-[var(--bg-elevated)] flex items-center justify-between text-xs text-muted">
      <div class="flex items-center space-x-1 font-mono text-[11px]" id="drawer-filepath">
        <span>File:</span>
        <span class="text-indigo-400 font-semibold truncate max-w-[340px]">docs/project/...</span>
      </div>
      <button onclick="window.app.copyDrawerFilepath()" class="px-2.5 py-1 rounded bg-[var(--bg-card)] border border-subtle hover:border-strong text-white font-medium transition flex items-center gap-1">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
        Copy Path
      </button>
    </div>
  </aside>

  <!-- OMNIBAR SEARCH MODAL -->
  <div id="omnibar-backdrop" onclick="window.app.toggleOmnibar(false)" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden opacity-0 transition-opacity duration-200"></div>
  <div id="omnibar-modal" class="fixed top-24 left-1/2 transform -translate-x-1/2 w-full max-w-2xl bg-[var(--bg-card)] border border-strong rounded-xl shadow-2xl z-50 hidden p-4">
    <div class="relative">
      <svg class="w-4 h-4 absolute left-3.5 top-3.5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
      <input id="omnibar-input" type="text" placeholder="Search tasks, stories, PRDs, ADRs, personas..." class="w-full bg-[var(--bg-elevated)] border border-subtle rounded-lg pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition" oninput="window.app.handleOmnibarSearch(this.value)">
    </div>
    <div id="omnibar-results" class="mt-3 max-h-80 overflow-y-auto space-y-1">
      <!-- Search results -->
    </div>
  </div>

  <!-- EMBEDDED PROJECT DATA -->
  <script>
    window.INITIAL_PROJECT_DATA = {initial_data_json};
    window.IS_LIVE_SERVER = {'true' if is_live_server else 'false'};
  </script>
</body>
</html>
"""
