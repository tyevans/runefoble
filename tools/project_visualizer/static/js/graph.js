// --- Runefoble Project Content Visualizer: Interactive 2D Relationship Graph Network ---
(function() {
  window.visualizer = window.visualizer || {};

  let graphState = {
    nodes: [],
    edges: [],
    selectedId: null,
    zoom: 1,
    panX: 0,
    panY: 0,
    isDragging: false,
    dragNode: null,
    startX: 0,
    startY: 0,
    activeTypeFilter: 'all',
  };

  function renderGraph(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;

    // Build raw nodes
    let allNodes = [];
    (d.personas || []).forEach(p => allNodes.push({ id: p.id, label: p.name, type: 'persona', color: '#F59E0B', group: 0 }));
    (d.stories || []).forEach(s => allNodes.push({ id: s.id, label: s.title, type: 'story', color: '#06B6D4', group: 1, persona: s.persona }));
    (d.prds || []).forEach(p => allNodes.push({ id: p.id, label: p.title, type: 'prd', color: '#F43F5E', group: 2 }));
    (d.tasks || []).forEach(t => {
      const color = t.status === 'Complete' ? '#10B981' : (t.status === 'Refined' ? '#F59E0B' : '#8B5CF6');
      allNodes.push({ id: t.id, label: t.title, type: 'task', color, group: 3, status: t.status, bc: t.target_bc, prs: t.prs });
    });
    (d.adrs || []).forEach(a => allNodes.push({ id: a.id, label: a.title, type: 'adr', color: '#6366F1', group: 4, domain: a.domain }));

    // Apply Hide Done and type filters
    const nodes = allNodes.filter(n => {
      if (state.filters.hideDone && n.type === 'task' && n.status === 'Complete') return false;
      if (graphState.activeTypeFilter !== 'all' && n.type !== graphState.activeTypeFilter) return false;
      if (state.filters.bc !== 'all' && n.bc && n.bc !== state.filters.bc) return false;
      return true;
    });

    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = (d.edges || []).filter(e => nodeIds.has(e.source_id) && nodeIds.has(e.target_id));

    // Calculate node coordinates in layered layout
    const width = 1100;
    const height = 750;
    const cols = { persona: 80, story: 290, prd: 520, task: 760, adr: 1000 };

    const typeCounts = { persona: 0, story: 0, prd: 0, task: 0, adr: 0 };
    const typeTotals = { persona: 0, story: 0, prd: 0, task: 0, adr: 0 };
    nodes.forEach(n => { if (typeTotals[n.type] !== undefined) typeTotals[n.type]++; });

    nodes.forEach(n => {
      const colX = cols[n.type] || 500;
      const idx = typeCounts[n.type]++;
      const total = typeTotals[n.type] || 1;
      const stepY = (height - 120) / Math.max(total, 1);
      n.x = colX + (Math.sin(idx) * 15);
      n.y = 60 + (idx * stepY);
    });

    graphState.nodes = nodes;
    graphState.edges = edges;

    container.innerHTML = `
      <div class="space-y-4">
        <!-- Graph Controls Bar -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[var(--bg-card)] border border-subtle">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>Interactive Relationship Graph</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono border border-indigo-500/20">${nodes.length} Nodes / ${edges.length} Edges</span>
            </h2>
            <p class="text-xs text-muted">Click any node to trace upstream and downstream lineage. Drag to explore relationships.</p>
          </div>

          <!-- Controls -->
          <div class="flex flex-wrap items-center gap-2.5">
            <!-- Hide Done Toggle -->
            <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong cursor-pointer text-xs transition">
              <input type="checkbox" ${state.filters.hideDone ? 'checked' : ''} onchange="window.visualizer.setFilter('hideDone', this.checked, 'graph')">
              <span class="font-medium ${state.filters.hideDone ? 'text-amber-400 font-semibold' : 'text-slate-300'}">Hide Done</span>
            </label>

            <!-- Node Type Filter -->
            <select class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition"
                    onchange="window.visualizer.setGraphTypeFilter(this.value)">
              <option value="all" ${graphState.activeTypeFilter === 'all' ? 'selected' : ''}>All Entity Types</option>
              <option value="persona" ${graphState.activeTypeFilter === 'persona' ? 'selected' : ''}>Personas</option>
              <option value="story" ${graphState.activeTypeFilter === 'story' ? 'selected' : ''}>User Stories</option>
              <option value="prd" ${graphState.activeTypeFilter === 'prd' ? 'selected' : ''}>PRDs</option>
              <option value="task" ${graphState.activeTypeFilter === 'task' ? 'selected' : ''}>Backlog Tasks</option>
              <option value="adr" ${graphState.activeTypeFilter === 'adr' ? 'selected' : ''}>ADRs</option>
            </select>

            <!-- Reset View -->
            <button onclick="window.visualizer.resetGraphView()" class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle hover:border-strong text-xs text-slate-300 transition flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
              Reset View
            </button>
          </div>
        </div>

        <!-- Interactive SVG Canvas -->
        <div id="graph-viewport" class="graph-viewport rounded-xl bg-[var(--bg-card)] border border-subtle h-[75vh] relative overflow-hidden">
          <svg id="graph-svg" class="w-full h-full" viewBox="0 0 ${width} ${height}">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563" />
              </marker>
              <marker id="arrow-active" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366F1" />
              </marker>
            </defs>

            <g id="graph-pan-layer" transform="translate(${graphState.panX}, ${graphState.panY}) scale(${graphState.zoom})">
              <!-- Edges -->
              <g id="graph-edges">
                ${edges.map(e => {
                  const s = nodes.find(n => n.id === e.source_id);
                  const t = nodes.find(n => n.id === e.target_id);
                  if (!s || !t) return '';
                  return `<line id="edge-${e.source_id}-${e.target_id}" x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#374151" stroke-width="1.2" stroke-opacity="0.4" marker-end="url(#arrow)" />`;
                }).join('')}
              </g>

              <!-- Nodes -->
              <g id="graph-nodes">
                ${nodes.map(n => `
                  <g id="node-${n.id}" class="graph-node-svg" transform="translate(${n.x}, ${n.y})" onclick="window.visualizer.handleGraphNodeClick('${n.id}')">
                    <circle r="12" fill="${n.color}" fill-opacity="0.85" stroke="#1F2937" stroke-width="2" />
                    <text x="16" y="4" fill="#E5E7EB" font-size="10" font-family="monospace" font-weight="600">${n.id}</text>
                  </g>
                `).join('')}
              </g>
            </g>
          </svg>
        </div>
      </div>
    `;

    setupGraphInteractions();
  }

  function setupGraphInteractions() {
    const viewport = document.getElementById('graph-viewport');
    if (!viewport) return;

    viewport.onwheel = (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      graphState.zoom = Math.max(0.4, Math.min(3, graphState.zoom * zoomFactor));
      updateTransform();
    };

    viewport.onmousedown = (e) => {
      if (e.target.closest('.graph-node-svg')) return;
      graphState.isDragging = true;
      graphState.startX = e.clientX - graphState.panX;
      graphState.startY = e.clientY - graphState.panY;
    };

    window.onmousemove = (e) => {
      if (!graphState.isDragging) return;
      graphState.panX = e.clientX - graphState.startX;
      graphState.panY = e.clientY - graphState.startY;
      updateTransform();
    };

    window.onmouseup = () => {
      graphState.isDragging = false;
    };
  }

  function updateTransform() {
    const layer = document.getElementById('graph-pan-layer');
    if (layer) {
      layer.setAttribute('transform', `translate(${graphState.panX}, ${graphState.panY}) scale(${graphState.zoom})`);
    }
  }

  function resetGraphView() {
    graphState.zoom = 1;
    graphState.panX = 0;
    graphState.panY = 0;
    graphState.selectedId = null;
    updateTransform();
    renderGraph(document.getElementById('view-content'), window.visualizer.state);
  }

  function handleGraphNodeClick(nodeId) {
    if (graphState.selectedId === nodeId) {
      // Second click opens drawer
      window.visualizer.openDrawer(nodeId);
      return;
    }

    graphState.selectedId = nodeId;

    // Traverse upstream & downstream neighbors
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
          queue.push(e.target_id);
        }
        if (e.target_id === cur && !connectedNodeIds.has(e.source_id)) {
          connectedNodeIds.add(e.source_id);
          connectedEdgeIds.add(`${e.source_id}-${e.target_id}`);
          queue.push(e.source_id);
        }
      });
    }

    // Highlight connected elements and dim the rest
    graphState.nodes.forEach(n => {
      const el = document.getElementById(`node-${n.id}`);
      if (el) {
        if (connectedNodeIds.has(n.id)) {
          el.style.opacity = '1';
          el.style.filter = n.id === nodeId ? 'drop-shadow(0 0 10px rgba(99, 102, 241, 0.9))' : 'none';
        } else {
          el.style.opacity = '0.15';
          el.style.filter = 'none';
        }
      }
    });

    edges.forEach(e => {
      const el = document.getElementById(`edge-${e.source_id}-${e.target_id}`);
      if (el) {
        if (connectedEdgeIds.has(`${e.source_id}-${e.target_id}`)) {
          el.setAttribute('stroke', '#6366F1');
          el.setAttribute('stroke-width', '2.5');
          el.setAttribute('stroke-opacity', '1');
          el.setAttribute('marker-end', 'url(#arrow-active)');
        } else {
          el.setAttribute('stroke', '#374151');
          el.setAttribute('stroke-width', '1');
          el.setAttribute('stroke-opacity', '0.08');
          el.setAttribute('marker-end', 'url(#arrow)');
        }
      }
    });
  }

  window.visualizer.renderGraph = renderGraph;
  window.visualizer.resetGraphView = resetGraphView;
  window.visualizer.handleGraphNodeClick = handleGraphNodeClick;
  window.visualizer.setGraphTypeFilter = (type) => {
    graphState.activeTypeFilter = type;
    renderGraph(document.getElementById('view-content'), window.visualizer.state);
  };
})();
