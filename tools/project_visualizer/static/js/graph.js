// --- Runefoble Project Content Visualizer: Interactive 2D Relationship Graph Network ---
(function() {
  window.visualizer = window.visualizer || {};

  let sim = null;

  // Fallback simulation engine if graph_physics.js was omitted, delayed, or running on stale assets
  if (typeof window.visualizer.ForceSimulation !== 'function') {
    window.visualizer.ForceSimulation = class FallbackSimulation {
      constructor(nodes, edges, opts = {}) {
        this.nodes = nodes; this.edges = edges;
        this.w = opts.width || 1200; this.h = opts.height || 800;
        this.cx = this.w / 2; this.cy = this.h / 2;
      }
      start(cb) { this.applyFlowLayout(); if (cb) cb(); }
      stop() {}
      reheat() {}
      applyFlowLayout() {
        const cols = { persona: 160, story: 560, prd: 1000, task: 1460, adr: 1900 };
        const c = {};
        this.nodes.forEach(n => {
          c[n.type] = (c[n.type] || 0) + 1;
          n.x = (cols[n.type] || 1000) + (Math.sin(c[n.type] * 2) * 20);
          n.y = 90 + c[n.type] * 50;
        });
      }
      applyRadialLayout() {
        this.nodes.forEach((n, i) => {
          const a = (i / Math.max(this.nodes.length, 1)) * 2 * Math.PI;
          n.x = this.cx + Math.cos(a) * 450;
          n.y = this.cy + Math.sin(a) * 450;
        });
      }
    };
  }

  const graphState = {
    nodes: [],
    edges: [],
    selectedId: null,
    zoom: 0.72,
    panX: 0,
    panY: 0,
    isDraggingCanvas: false,
    dragNode: null,
    startX: 0,
    startY: 0,
    activeTypeFilter: 'all',
    activeLayout: 'network',
    depth: 'lineage',
    physicsRunning: true,
    isFullscreen: false,
  };

  const canvasWidth = 2200;
  const canvasHeight = 1400;

  function renderGraph(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;

    // Collect all nodes
    let rawNodes = [];
    (d.personas || []).forEach(p => rawNodes.push({ id: p.id, label: p.name, type: 'persona', color: '#F59E0B', role: p.role }));
    (d.stories || []).forEach(s => rawNodes.push({ id: s.id, label: s.title, type: 'story', color: '#06B6D4', persona: s.persona }));
    (d.prds || []).forEach(p => rawNodes.push({ id: p.id, label: p.title, type: 'prd', color: '#F43F5E', status: p.status }));
    (d.tasks || []).forEach(t => {
      const color = t.status === 'Complete' ? '#10B981' : (t.status === 'Refined' ? '#F59E0B' : '#8B5CF6');
      rawNodes.push({ id: t.id, label: t.title, type: 'task', color, status: t.status, bc: t.target_bc, prs: t.prs || [] });
    });
    (d.adrs || []).forEach(a => rawNodes.push({ id: a.id, label: a.title, type: 'adr', color: '#6366F1', domain: a.domain }));

    // Apply Hide Done & filters
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

    if (graphState.activeLayout === 'flow') sim.applyFlowLayout();
    else if (graphState.activeLayout === 'radial') sim.applyRadialLayout();
    else sim.start(updatePositions);

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
              <p class="text-xs text-muted">Organic force simulation, tactile drag, and bidirectional lineage illumination.</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <!-- Layout Switcher -->
            <div class="flex items-center p-0.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs">
              <button onclick="window.visualizer.switchGraphLayout('network')" class="px-2.5 py-1 rounded-md font-medium transition ${graphState.activeLayout === 'network' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🪐 Force</button>
              <button onclick="window.visualizer.switchGraphLayout('flow')" class="px-2.5 py-1 rounded-md font-medium transition ${graphState.activeLayout === 'flow' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🌊 Flow DAG</button>
              <button onclick="window.visualizer.switchGraphLayout('radial')" class="px-2.5 py-1 rounded-md font-medium transition ${graphState.activeLayout === 'radial' ? 'bg-indigo-600 text-white shadow-sm' : 'text-muted hover:text-white'}">🎯 Radar</button>
            </div>

            <!-- Physics Play/Pause & Reheat -->
            <button onclick="window.visualizer.toggleGraphPhysics()" id="graph-physics-btn" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-slate-300 hover:border-strong transition flex items-center gap-1">
              <span>${graphState.physicsRunning ? '⏸️ Freeze' : '▶️ Run'}</span>
            </button>
            <button onclick="window.visualizer.reheatGraphPhysics()" class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-amber-400 hover:border-strong transition flex items-center gap-1" title="Inject kinetic energy to shuffle nodes">
              <span>⚡ Shuffle</span>
            </button>

            <!-- Hide Done Filter -->
            <label class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'graph')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span>
            </label>

            <!-- Search Auto-Focus -->
            <div class="relative">
              <input type="text" id="graph-search-input" placeholder="Find node & focus camera..."
                     class="px-3 py-1.5 pl-7 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition w-44"
                     onkeydown="if(event.key==='Enter') window.visualizer.focusNodeFromSearch(this.value)">
              <svg class="w-3.5 h-3.5 absolute left-2 top-2 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>

            <!-- Camera & Fullscreen Controls -->
            <button onclick="window.visualizer.zoomGraph(1.2)" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Zoom In">➕</button>
            <button onclick="window.visualizer.zoomGraph(0.8)" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Zoom Out">➖</button>
            <button onclick="window.visualizer.resetGraphView()" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Center Camera">🎯</button>
            <button onclick="window.visualizer.toggleGraphFullscreen()" id="graph-fs-btn" class="p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-slate-300 hover:text-white" title="Toggle Fullscreen">⛶</button>
          </div>
        </div>

        <!-- Interactive SVG Viewport -->
        <div id="graph-viewport-wrapper" class="relative rounded-xl border border-subtle overflow-hidden shadow-2xl bg-[var(--bg-card)]">
          <div id="graph-viewport" class="graph-viewport graph-canvas-bg h-[76vh] w-full">
            <svg id="graph-svg" class="w-full h-full" viewBox="0 0 ${canvasWidth} ${canvasHeight}">
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

            <!-- Floating Tooltip -->
            <div id="graph-tooltip" class="graph-tooltip p-3 rounded-xl border border-strong hidden opacity-0 text-xs w-64"></div>

            <!-- Minimap -->
            <div class="graph-minimap" id="graph-minimap" onclick="window.visualizer.handleMinimapClick(event)">
              <svg id="minimap-svg" class="w-full h-full" viewBox="0 0 ${canvasWidth} ${canvasHeight}">
                <g id="minimap-nodes">${nodes.map(n => `<circle cx="${n.x || 0}" cy="${n.y || 0}" r="7" fill="${n.color}" opacity="0.75" />`).join('')}</g>
                <rect id="minimap-view-rect" class="minimap-rect" x="0" y="0" width="200" height="150" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    `;

    setupInteractions();
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

    updateMinimap();
  }

  function updateMinimap() {
    const rect = document.getElementById('minimap-view-rect');
    if (!rect) return;
    const vW = canvasWidth / graphState.zoom;
    const vH = canvasHeight / graphState.zoom;
    const vX = -graphState.panX / graphState.zoom;
    const vY = -graphState.panY / graphState.zoom;
    rect.setAttribute('x', Math.max(0, vX));
    rect.setAttribute('y', Math.max(0, vY));
    rect.setAttribute('width', Math.min(canvasWidth, vW));
    rect.setAttribute('height', Math.min(canvasHeight, vH));
  }

  function setupInteractions() {
    const viewport = document.getElementById('graph-viewport');
    if (!viewport) return;

    viewport.onwheel = (e) => {
      e.preventDefault();
      zoomGraph(e.deltaY < 0 ? 1.12 : 0.89);
    };

    viewport.onmousedown = (e) => {
      const nodeEl = e.target.closest('.graph-node-svg');
      if (nodeEl) {
        const nId = nodeEl.id.replace('node-', '');
        const targetNode = graphState.nodes.find(n => n.id === nId);
        if (targetNode) {
          graphState.dragNode = targetNode;
          targetNode.isFixed = true;
          if (sim) sim.reheat(0.6);
        }
        return;
      }
      graphState.isDraggingCanvas = true;
      graphState.startX = e.clientX - graphState.panX;
      graphState.startY = e.clientY - graphState.panY;
    };

    window.onmousemove = (e) => {
      if (graphState.dragNode) {
        const rect = viewport.getBoundingClientRect();
        graphState.dragNode.x = (e.clientX - rect.left - graphState.panX) / graphState.zoom;
        graphState.dragNode.y = (e.clientY - rect.top - graphState.panY) / graphState.zoom;
        updatePositions();
        return;
      }
      if (graphState.isDraggingCanvas) {
        graphState.panX = e.clientX - graphState.startX;
        graphState.panY = e.clientY - graphState.startY;
        applyTransform();
      }
    };

    window.onmouseup = () => {
      if (graphState.dragNode) {
        graphState.dragNode.isFixed = false;
        graphState.dragNode = null;
      }
      graphState.isDraggingCanvas = false;
    };
  }

  function applyTransform() {
    const layer = document.getElementById('graph-pan-layer');
    if (layer) layer.setAttribute('transform', `translate(${graphState.panX}, ${graphState.panY}) scale(${graphState.zoom})`);
    updateMinimap();
  }

  function zoomGraph(factor) {
    graphState.zoom = Math.max(0.3, Math.min(3.5, graphState.zoom * factor));
    applyTransform();
  }

  function resetGraphView() {
    graphState.zoom = 0.72;
    graphState.panX = 0;
    graphState.panY = 0;
    applyTransform();
    clearNodeHighlights();
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
    if (sim) {
      if (layout === 'flow') sim.applyFlowLayout();
      else if (layout === 'radial') sim.applyRadialLayout();
      else sim.reheat(0.85);
      updatePositions();
    }
  }

  function handleGraphNodeClick(nodeId) {
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
      const el = document.getElementById(`node-${n.id}`);
      if (el) {
        el.style.opacity = connectedNodeIds.has(n.id) ? '1' : '0.12';
        el.style.filter = n.id === nodeId ? 'drop-shadow(0 0 16px rgba(99, 102, 241, 1))' : 'none';
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

    graphState.zoom = 1.4;
    graphState.panX = (canvasWidth / 2) - (node.x * graphState.zoom);
    graphState.panY = (canvasHeight / 2) - (node.y * graphState.zoom);
    applyTransform();

    const ping = document.getElementById('graph-focus-ping');
    if (ping) {
      ping.setAttribute('cx', node.x);
      ping.setAttribute('cy', node.y);
      ping.classList.remove('hidden');
      setTimeout(() => ping.classList.add('hidden'), 2200);
    }
    handleGraphNodeClick(node.id);
  }

  function showGraphTooltip(e, id) {
    const node = graphState.nodes.find(n => n.id === id);
    const tooltip = document.getElementById('graph-tooltip');
    const viewport = document.getElementById('graph-viewport');
    if (!node || !tooltip || !viewport) return;

    const vpRect = viewport.getBoundingClientRect();
    tooltip.style.left = `${e.clientX - vpRect.left + 15}px`;
    tooltip.style.top = `${e.clientY - vpRect.top + 15}px`;

    const esc = window.visualizer.escapeHtml;
    tooltip.innerHTML = `
      <div class="space-y-1.5">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-white">${node.id}</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase" style="color: ${node.color}; background-color: ${node.color}22;">${node.type}</span>
        </div>
        <p class="text-slate-200 font-semibold text-xs leading-tight">${esc(node.label)}</p>
        ${node.status ? `<div class="text-[10px] text-muted">Status: <span class="text-white font-medium">${node.status}</span></div>` : ''}
        ${node.prs && node.prs.length ? `<div class="text-[10px] text-cyan-400 font-mono">Linked PR: ${node.prs[0]}</div>` : ''}
        <div class="pt-1.5 border-t border-subtle flex items-center justify-between text-[10px] text-muted">
          <span>Click to trace</span>
          <span class="text-indigo-400">Double-click: reader →</span>
        </div>
      </div>
    `;
    tooltip.classList.remove('hidden');
    setTimeout(() => tooltip.classList.remove('opacity-0'), 10);
  }

  function hideGraphTooltip() {
    const tooltip = document.getElementById('graph-tooltip');
    if (tooltip) { tooltip.classList.add('opacity-0'); setTimeout(() => tooltip.classList.add('hidden'), 150); }
  }

  function toggleGraphFullscreen() {
    const wrap = document.getElementById('graph-viewport-wrapper');
    const btn = document.getElementById('graph-fs-btn');
    if (!wrap) return;
    graphState.isFullscreen = !graphState.isFullscreen;
    wrap.classList.toggle('graph-fullscreen', graphState.isFullscreen);
    if (btn) btn.textContent = graphState.isFullscreen ? '✖' : '⛶';
  }

  function handleMinimapClick(e) {
    const mm = document.getElementById('graph-minimap');
    if (!mm) return;
    const rect = mm.getBoundingClientRect();
    const targetX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
    const targetY = ((e.clientY - rect.top) / rect.height) * canvasHeight;
    graphState.panX = (canvasWidth / 2) - (targetX * graphState.zoom);
    graphState.panY = (canvasHeight / 2) - (targetY * graphState.zoom);
    applyTransform();
  }

  Object.assign(window.visualizer, {
    renderGraph, switchGraphLayout, toggleGraphPhysics, reheatGraphPhysics,
    handleGraphNodeClick, zoomGraph, resetGraphView, focusNodeFromSearch,
    showGraphTooltip, hideGraphTooltip, toggleGraphFullscreen, handleMinimapClick,
  });
})();
