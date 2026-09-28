// --- Runefoble Project Content Visualizer: Graph Zoom & Pan Controller ---
(function() {
  const root = typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this);
  root.visualizer = root.visualizer || {};

  function renderViewportShell(nodes, edges, state) {
    const gs = root.visualizer.graphState || {};
    const cw = gs.canvasWidth || 2200, ch = gs.canvasHeight || 1400;
    const markerDefs = root.visualizer.renderMarkerDefs ? root.visualizer.renderMarkerDefs() : '';
    const edgesHtml = root.visualizer.renderEdgesLayer ? root.visualizer.renderEdgesLayer(edges) : '';
    const nodesHtml = root.visualizer.renderNodesLayer ? root.visualizer.renderNodesLayer(nodes) : '';
    const minimapHtml = root.visualizer.renderMinimapNodes ? root.visualizer.renderMinimapNodes(nodes) : '';

    return `<div class="space-y-4">
      <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-4 p-4 rounded-xl bg-[var(--bg-card)] border border-subtle shadow-md">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-sm font-bold text-sm">🌐</div>
          <div><h2 class="text-base font-bold text-white flex items-center gap-2"><span>Interactive Relationship Graph</span><span id="graph-stat-pill" class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono border border-indigo-500/20">${nodes.length} Nodes · ${edges.length} Edges</span></h2><p class="text-xs text-muted">Organic force simulation, focal zoom, tactile dragging, and live minimap tracking.</p></div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center p-0.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs">
            <button id="layout-btn-network" onclick="window.visualizer.switchGraphLayout('network')" class="px-2.5 py-1 rounded-md font-medium transition ${gs.activeLayout === 'network' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🪐 Force</button>
            <button id="layout-btn-flow" onclick="window.visualizer.switchGraphLayout('flow')" class="px-2.5 py-1 rounded-md font-medium transition ${gs.activeLayout === 'flow' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🌊 Flow DAG</button>
            <button id="layout-btn-radial" onclick="window.visualizer.switchGraphLayout('radial')" class="px-2.5 py-1 rounded-md font-medium transition ${gs.activeLayout === 'radial' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🎯 Radar</button>
          </div>
          <button onclick="window.visualizer.toggleGraphPhysics()" id="graph-physics-btn" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-slate-300 hover:border-strong transition flex items-center gap-1"><span>${gs.physicsRunning ? '⏸️ Freeze' : '▶️ Run'}</span></button>
          <button onclick="window.visualizer.reheatGraphPhysics()" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-amber-400 hover:border-strong transition flex items-center gap-1" title="Inject kinetic energy to shuffle nodes"><span>⚡ Shuffle</span></button>
          <label class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition"><input type="checkbox" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'graph')"><span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span></label>
          <div class="relative">
            <input type="text" id="graph-search-input" placeholder="Find node & focus camera..." class="px-3 py-1.5 pl-7 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition w-44" onkeydown="if(event.key==='Enter') window.visualizer.focusNodeFromSearch(this.value)">
            <svg class="w-3.5 h-3.5 absolute left-2 top-2 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          </div>
          <button onclick="window.visualizer.zoomGraph(1.25)" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Zoom In (Centered)">➕</button><button onclick="window.visualizer.zoomGraph(0.8)" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Zoom Out (Centered)">➖</button><button onclick="window.visualizer.resetGraphView()" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Center Entire Graph">🎯</button><button onclick="window.visualizer.toggleGraphFullscreen()" id="graph-fs-btn" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Toggle Fullscreen">⛶</button>
        </div>
      </div>
      <div id="graph-viewport-wrapper" class="relative rounded-xl border border-subtle overflow-hidden shadow-2xl bg-[var(--bg-card)]">
        <div id="graph-viewport" class="graph-viewport graph-canvas-bg h-[76vh] w-full">
          <svg id="graph-svg" class="w-full h-full overflow-hidden">
            ${markerDefs}
            <g id="graph-pan-layer" transform="translate(${gs.panX || 0}, ${gs.panY || 0}) scale(${gs.zoom || 0.72})">
              <circle id="graph-focus-ping" class="focus-ripple pointer-events-none hidden" cx="0" cy="0" r="16" fill="none" stroke="#6366F1" stroke-width="2" />
              <g id="graph-edges-group">${edgesHtml}</g>
              <g id="graph-nodes-group">${nodesHtml}</g>
            </g>
          </svg>
          <div id="graph-tooltip" class="graph-tooltip p-3 rounded-xl border border-strong hidden opacity-0 text-xs w-64"></div>
          <div class="graph-minimap" id="graph-minimap" title="Minimap: Click or drag to reposition camera"><svg id="minimap-svg" class="w-full h-full" viewBox="0 0 ${cw} ${ch}" preserveAspectRatio="none"><g id="minimap-nodes">${minimapHtml}</g><rect id="minimap-view-rect" class="minimap-rect" x="0" y="0" width="200" height="150" rx="12" /></svg></div>
        </div>
      </div>
    </div>`;
  }

  function focusNodeFromSearch(query) {
    if (!query) return;
    const gs = root.visualizer.graphState;
    if (!gs || !gs.nodes) return;
    const q = query.toLowerCase().trim();
    const node = gs.nodes.find(n => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q));
    if (!node) return;
    const vp = document.getElementById('graph-viewport');
    const vw = vp ? vp.clientWidth : 1200, vh = vp ? vp.clientHeight : 800;
    gs.zoom = 1.35;
    gs.panX = (vw / 2) - (node.x * gs.zoom);
    gs.panY = (vh / 2) - (node.y * gs.zoom);
    if (root.visualizer.applyTransform) root.visualizer.applyTransform();
    const ping = document.getElementById('graph-focus-ping');
    if (ping) {
      ping.setAttribute('cx', node.x); ping.setAttribute('cy', node.y);
      ping.classList.remove('hidden');
      setTimeout(() => ping.classList.add('hidden'), 2200);
    }
    if (root.visualizer.handleGraphNodeClick) root.visualizer.handleGraphNodeClick(node.id);
  }

  const api = { renderViewportShell, focusNodeFromSearch };
  root.visualizer.graphZoom = api;
  Object.assign(root.visualizer, api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
