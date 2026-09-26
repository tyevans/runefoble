// --- Runefoble Project Content Visualizer: Interactive 2D Relationship Graph Network ---
(function() {
  window.visualizer = window.visualizer || {};

  let sim = null;

  if (typeof window.visualizer.ForceSimulation !== 'function') {
    window.visualizer.ForceSimulation = class {
      constructor(n, e) { this.nodes = n; this.edges = e; }
      start(cb) { if (cb) cb(); } stop() {} reheat() {} applyFlowLayout() {} applyRadialLayout() {}
    };
  }

  const canvasWidth = 2200;
  const canvasHeight = 1400;

  const graphState = window.visualizer.graphState = window.visualizer.graphState || {
    nodes: [],
    edges: [],
    selectedId: null,
    zoom: 0.72,
    panX: 0,
    panY: 0,
    canvasWidth,
    canvasHeight,
    isDraggingCanvas: false,
    isDraggingMinimap: false,
    dragNode: null,
    dragOffsetX: 0,
    dragOffsetY: 0,
    dragDistance: 0,
    startX: 0,
    startY: 0,
    startPanX: 0,
    startPanY: 0,
    activeTypeFilter: 'all',
    activeLayout: 'network',
    depth: 'lineage',
    physicsRunning: true,
    isFullscreen: false,
    initialized: false,
  };

  function renderGraph(container, state) {
    const d = state.data;
    if (!d) return;

    let rawNodes = [];
    (d.personas || []).forEach(p => rawNodes.push({ id: p.id, label: p.name, type: 'persona', color: '#F59E0B', role: p.role }));
    (d.stories || []).forEach(s => rawNodes.push({ id: s.id, label: s.title, type: 'story', color: '#06B6D4', persona: s.persona }));
    (d.prds || []).forEach(p => rawNodes.push({ id: p.id, label: p.title, type: 'prd', color: '#F43F5E', status: p.status }));
    (d.tasks || []).forEach(t => {
      const color = t.status === 'Complete' ? '#10B981' : (t.status === 'Refined' ? '#F59E0B' : '#8B5CF6');
      rawNodes.push({ id: t.id, label: t.title, type: 'task', color, status: t.status, bc: t.target_bc, prs: t.prs || [] });
    });
    (d.adrs || []).forEach(a => rawNodes.push({ id: a.id, label: a.title, type: 'adr', color: '#6366F1', domain: a.domain }));

    const nodes = rawNodes.filter(n => {
      if (state.filters.hideDone && n.type === 'task' && n.status === 'Complete') return false;
      if (graphState.activeTypeFilter !== 'all' && n.type !== graphState.activeTypeFilter) return false;
      if (state.filters.bc !== 'all' && n.bc && n.bc !== state.filters.bc) return false;
      return true;
    });

    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = (d.edges || []).filter(e => nodeIds.has(e.source_id) && nodeIds.has(e.target_id));

    graphState.nodes = nodes;
    graphState.edges = edges;

    if (sim) sim.stop();
    sim = new window.visualizer.ForceSimulation(nodes, edges, { width: canvasWidth, height: canvasHeight });
    window.visualizer.sim = sim;

    if (graphState.activeLayout === 'flow') sim.applyFlowLayout();
    else if (graphState.activeLayout === 'radial') sim.applyRadialLayout();
    else if (graphState.physicsRunning) sim.start(updatePositions);

    container.innerHTML = `
      <div class="space-y-4">
        <!-- Floating HUD Header & Controls -->
        <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-4 p-4 rounded-xl bg-[var(--bg-card)] border border-subtle shadow-md">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-sm font-bold text-sm">🌐</div>
            <div>
              <h2 class="text-base font-bold text-white flex items-center gap-2">
                <span>Interactive Relationship Graph</span>
                <span id="graph-stat-pill" class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono border border-indigo-500/20">${nodes.length} Nodes · ${edges.length} Edges</span>
              </h2>
              <p class="text-xs text-muted">Organic force simulation, focal zoom, tactile dragging, and live minimap tracking.</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <div class="flex items-center p-0.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs">
              <button id="layout-btn-network" onclick="window.visualizer.switchGraphLayout('network')" class="px-2.5 py-1 rounded-md font-medium transition ${graphState.activeLayout === 'network' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🪐 Force</button>
              <button id="layout-btn-flow" onclick="window.visualizer.switchGraphLayout('flow')" class="px-2.5 py-1 rounded-md font-medium transition ${graphState.activeLayout === 'flow' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🌊 Flow DAG</button>
              <button id="layout-btn-radial" onclick="window.visualizer.switchGraphLayout('radial')" class="px-2.5 py-1 rounded-md font-medium transition ${graphState.activeLayout === 'radial' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🎯 Radar</button>
            </div>

            <button onclick="window.visualizer.toggleGraphPhysics()" id="graph-physics-btn" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-slate-300 hover:border-strong transition flex items-center gap-1">
              <span>${graphState.physicsRunning ? '⏸️ Freeze' : '▶️ Run'}</span>
            </button>
            <button onclick="window.visualizer.reheatGraphPhysics()" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-amber-400 hover:border-strong transition flex items-center gap-1" title="Inject kinetic energy to shuffle nodes">
              <span>⚡ Shuffle</span>
            </button>

            <label class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'graph')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span>
            </label>

            <div class="relative">
              <input type="text" id="graph-search-input" placeholder="Find node & focus camera..."
                     class="px-3 py-1.5 pl-7 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition w-44"
                     onkeydown="if(event.key==='Enter') window.visualizer.focusNodeFromSearch(this.value)">
              <svg class="w-3.5 h-3.5 absolute left-2 top-2 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>

            <button onclick="window.visualizer.zoomGraph(1.25)" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Zoom In (Centered)">➕</button>
            <button onclick="window.visualizer.zoomGraph(0.8)" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Zoom Out (Centered)">➖</button>
            <button onclick="window.visualizer.resetGraphView()" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Center Entire Graph">🎯</button>
            <button onclick="window.visualizer.toggleGraphFullscreen()" id="graph-fs-btn" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Toggle Fullscreen">⛶</button>
          </div>
        </div>

        <!-- Interactive SVG Viewport -->
        <div id="graph-viewport-wrapper" class="relative rounded-xl border border-subtle overflow-hidden shadow-2xl bg-[var(--bg-card)]">
          <div id="graph-viewport" class="graph-viewport graph-canvas-bg h-[76vh] w-full">
            <svg id="graph-svg" class="w-full h-full overflow-hidden">
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563" /></marker>
                <marker id="arrow-glow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#6366F1" /></marker>
              </defs>

              <g id="graph-pan-layer" transform="translate(${graphState.panX}, ${graphState.panY}) scale(${graphState.zoom})">
                <circle id="graph-focus-ping" class="focus-ripple pointer-events-none hidden" cx="0" cy="0" r="16" fill="none" stroke="#6366F1" stroke-width="2" />
                <g id="graph-edges-group">
                  ${edges.map(e => `<line id="edge-${e.source_id}-${e.target_id}" x1="0" y1="0" x2="0" y2="0" stroke="#374151" stroke-width="1.3" stroke-opacity="0.38" marker-end="url(#arrow)" />`).join('')}
                </g>
                <g id="graph-nodes-group">
                  ${nodes.map(n => renderNodeSVG(n)).join('')}
                </g>
              </g>
            </svg>

            <div id="graph-tooltip" class="graph-tooltip p-3 rounded-xl border border-strong hidden opacity-0 text-xs w-64"></div>

            <!-- Minimap -->
            <div class="graph-minimap" id="graph-minimap" title="Minimap: Click or drag to reposition camera">
              <svg id="minimap-svg" class="w-full h-full" viewBox="0 0 ${canvasWidth} ${canvasHeight}" preserveAspectRatio="none">
                <g id="minimap-nodes">
                  ${nodes.map(n => `<circle id="mm-node-${n.id}" class="mm-node" cx="${n.x || 0}" cy="${n.y || 0}" r="18" fill="${n.color}" opacity="0.85" stroke="#111827" stroke-width="2" />`).join('')}
                </g>
                <rect id="minimap-view-rect" class="minimap-rect" x="0" y="0" width="200" height="150" rx="12" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    `;

    if (window.visualizer.setupGraphInteractions) window.visualizer.setupGraphInteractions();
    if (!graphState.initialized) {
      if (window.visualizer.resetGraphView) window.visualizer.resetGraphView();
      graphState.initialized = true;
    } else {
      if (window.visualizer.applyTransform) window.visualizer.applyTransform();
    }
    updatePositions();
  }

  function renderNodeSVG(n) {
    const isTask = n.type === 'task';
    const hasPR = isTask && n.prs && n.prs.length > 0;
    const typeInitial = n.type === 'persona' ? n.label[0] : (isTask ? 'T' : (n.type === 'adr' ? 'A' : (n.type === 'prd' ? 'P' : 'S')));

    return `
      <g id="node-${n.id}" class="graph-node-svg" transform="translate(${n.x || 0}, ${n.y || 0})"
         onclick="window.visualizer.handleGraphNodeClick('${n.id}')"
         ondblclick="window.visualizer.openDrawer('${n.id}')"
         onmouseenter="window.visualizer.showGraphTooltip(event, '${n.id}')"
         onmouseleave="window.visualizer.hideGraphTooltip()">
        <circle r="22" fill="${n.color}" fill-opacity="0.12" stroke="${n.color}" stroke-opacity="0.3" stroke-width="1.2" />
        <circle r="14" fill="${n.color}" fill-opacity="0.9" stroke="#111827" stroke-width="2.5" />
        <text text-anchor="middle" y="4" fill="#FFFFFF" font-size="9" font-family="monospace" font-weight="bold">${typeInitial}</text>
        <g transform="translate(18, -10)">
          <rect rx="4" width="${n.id.length * 7 + 12}" height="18" fill="#111827" fill-opacity="0.92" stroke="#374151" stroke-width="0.8" />
          <text x="6" y="12" fill="#F3F4F6" font-size="9.5" font-family="monospace" font-weight="700">${n.id}</text>
        </g>
        ${hasPR ? `
          <g transform="translate(18, 10)">
            <rect rx="3" width="36" height="14" fill="#06B6D4" fill-opacity="0.2" stroke="#06B6D4" stroke-width="0.8" />
            <text x="4" y="10" fill="#22D3EE" font-size="8" font-family="monospace" font-weight="bold">${n.prs[0]}</text>
          </g>
        ` : ''}
      </g>
    `;
  }

  function updatePositions() {
    const nodes = graphState.nodes;
    const edges = graphState.edges;
    const nodeMap = new Map();

    nodes.forEach(n => {
      nodeMap.set(n.id, n);
      const el = document.getElementById(`node-${n.id}`);
      if (el) el.setAttribute('transform', `translate(${n.x}, ${n.y})`);
      const mm = document.getElementById(`mm-node-${n.id}`);
      if (mm) {
        mm.setAttribute('cx', n.x);
        mm.setAttribute('cy', n.y);
      }
    });

    edges.forEach(e => {
      const s = nodeMap.get(e.source_id);
      const t = nodeMap.get(e.target_id);
      const el = document.getElementById(`edge-${e.source_id}-${e.target_id}`);
      if (el && s && t) {
        el.setAttribute('x1', s.x);
        el.setAttribute('y1', s.y);
        el.setAttribute('x2', t.x);
        el.setAttribute('y2', t.y);
      }
    });

    if (window.visualizer.updateMinimap) window.visualizer.updateMinimap();
  }

  function handleGraphNodeClick(nodeId) {
    if (graphState.dragDistance > 6) return;
    if (graphState.selectedId === nodeId) {
      window.visualizer.openDrawer(nodeId);
      return;
    }
    graphState.selectedId = nodeId;
    const edges = graphState.edges;
    const connectedNodeIds = new Set([nodeId]);
    const connectedEdgeIds = new Set();
    let queue = [nodeId];

    while (queue.length > 0) {
      const cur = queue.shift();
      edges.forEach(e => {
        if (e.source_id === cur && !connectedNodeIds.has(e.target_id)) {
          connectedNodeIds.add(e.target_id);
          connectedEdgeIds.add(`${e.source_id}-${e.target_id}`);
          if (graphState.depth === 'lineage') queue.push(e.target_id);
        }
        if (e.target_id === cur && !connectedNodeIds.has(e.source_id)) {
          connectedNodeIds.add(e.source_id);
          connectedEdgeIds.add(`${e.source_id}-${e.target_id}`);
          if (graphState.depth === 'lineage') queue.push(e.source_id);
        }
      });
    }

    graphState.nodes.forEach(n => {
      const isConn = connectedNodeIds.has(n.id);
      const isSelected = n.id === nodeId;
      const el = document.getElementById(`node-${n.id}`);
      if (el) {
        el.style.opacity = isConn ? '1' : '0.12';
        el.style.filter = isSelected ? 'drop-shadow(0 0 16px rgba(99, 102, 241, 1))' : 'none';
      }
      const mm = document.getElementById(`mm-node-${n.id}`);
      if (mm) {
        mm.setAttribute('opacity', isConn ? '1' : '0.18');
        mm.setAttribute('r', isSelected ? '26' : (isConn ? '20' : '14'));
      }
    });

    edges.forEach(e => {
      const el = document.getElementById(`edge-${e.source_id}-${e.target_id}`);
      if (!el) return;
      const isConn = connectedEdgeIds.has(`${e.source_id}-${e.target_id}`);
      el.setAttribute('stroke', isConn ? '#818CF8' : '#374151');
      el.setAttribute('stroke-width', isConn ? '2.8' : '1');
      el.setAttribute('stroke-opacity', isConn ? '1' : '0.06');
      el.setAttribute('marker-end', isConn ? 'url(#arrow-glow)' : 'url(#arrow)');
      el.classList.toggle('edge-active-flow', isConn);
    });
  }

  function clearNodeHighlights() {
    graphState.selectedId = null;
    graphState.nodes.forEach(n => {
      const el = document.getElementById(`node-${n.id}`);
      if (el) { el.style.opacity = '1'; el.style.filter = 'none'; }
      const mm = document.getElementById(`mm-node-${n.id}`);
      if (mm) { mm.setAttribute('opacity', '0.85'); mm.setAttribute('r', '18'); }
    });
    graphState.edges.forEach(e => {
      const el = document.getElementById(`edge-${e.source_id}-${e.target_id}`);
      if (el) {
        el.setAttribute('stroke', '#374151'); el.setAttribute('stroke-width', '1.3');
        el.setAttribute('stroke-opacity', '0.38'); el.setAttribute('marker-end', 'url(#arrow)');
        el.classList.remove('edge-active-flow');
      }
    });
  }

  function focusNodeFromSearch(query) {
    if (!query) return;
    const q = query.toLowerCase().trim();
    const node = graphState.nodes.find(n => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q));
    if (!node) return;

    const vp = document.getElementById('graph-viewport');
    const vw = vp ? vp.clientWidth : 1200;
    const vh = vp ? vp.clientHeight : 800;

    graphState.zoom = 1.35;
    graphState.panX = (vw / 2) - (node.x * graphState.zoom);
    graphState.panY = (vh / 2) - (node.y * graphState.zoom);
    if (window.visualizer.applyTransform) window.visualizer.applyTransform();

    const ping = document.getElementById('graph-focus-ping');
    if (ping) {
      ping.setAttribute('cx', node.x);
      ping.setAttribute('cy', node.y);
      ping.classList.remove('hidden');
      setTimeout(() => ping.classList.add('hidden'), 2200);
    }
    handleGraphNodeClick(node.id);
  }

  function toggleGraphPhysics() {
    graphState.physicsRunning = !graphState.physicsRunning;
    const btn = document.getElementById('graph-physics-btn');
    if (btn) btn.textContent = graphState.physicsRunning ? '⏸️ Freeze' : '▶️ Run';
    if (sim) {
      if (graphState.physicsRunning) sim.start(updatePositions);
      else sim.stop();
    }
  }

  function reheatGraphPhysics() {
    if (sim) {
      graphState.physicsRunning = true;
      const btn = document.getElementById('graph-physics-btn');
      if (btn) btn.textContent = '⏸️ Freeze';
      sim.reheat(0.9);
    }
  }

  function switchGraphLayout(layout) {
    graphState.activeLayout = layout;
    ['network', 'flow', 'radial'].forEach(l => {
      const btn = document.getElementById(`layout-btn-${l}`);
      if (btn) {
        btn.className = l === layout
          ? 'px-2.5 py-1 rounded-md font-medium transition bg-indigo-600 text-white shadow-sm'
          : 'px-2.5 py-1 rounded-md font-medium transition text-muted hover:text-white';
      }
    });
    if (sim) {
      if (layout === 'flow') sim.applyFlowLayout();
      else if (layout === 'radial') sim.applyRadialLayout();
      else sim.reheat(0.85);
      updatePositions();
    }
  }

  Object.assign(window.visualizer, {
    renderGraph, updatePositions, handleGraphNodeClick, clearNodeHighlights,
    focusNodeFromSearch, toggleGraphPhysics, reheatGraphPhysics, switchGraphLayout,
  });
})();
