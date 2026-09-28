// --- Runefoble Project Content Visualizer: Graph Node Renderer ---
(function() {
  const root = typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this);
  root.visualizer = root.visualizer || {};

  function extractNodes(d, filters = {}, activeTypeFilter = 'all') {
    const raw = [];
    (d.personas || []).forEach(p => raw.push({ id: p.id, label: p.name, type: 'persona', color: '#F59E0B', role: p.role }));
    (d.stories || []).forEach(s => raw.push({ id: s.id, label: s.title, type: 'story', color: '#06B6D4', persona: s.persona }));
    (d.prds || []).forEach(p => raw.push({ id: p.id, label: p.title, type: 'prd', color: '#F43F5E', status: p.status }));
    (d.tasks || []).forEach(t => {
      const color = t.status === 'Complete' ? '#10B981' : (t.status === 'Refined' ? '#F59E0B' : '#8B5CF6');
      raw.push({ id: t.id, label: t.title, type: 'task', color, status: t.status, bc: t.target_bc, prs: t.prs || [] });
    });
    (d.adrs || []).forEach(a => raw.push({ id: a.id, label: a.title, type: 'adr', color: '#6366F1', domain: a.domain }));

    return raw.filter(n => {
      if (filters.hideDone && n.type === 'task' && n.status === 'Complete') return false;
      if (activeTypeFilter !== 'all' && n.type !== activeTypeFilter) return false;
      if (filters.bc !== 'all' && n.bc && n.bc !== filters.bc) return false;
      return true;
    });
  }

  function renderNodeSVG(n) {
    const isTask = n.type === 'task';
    const hasPR = isTask && n.prs && n.prs.length > 0;
    const initial = n.type === 'persona' ? n.label[0] : (isTask ? 'T' : (n.type === 'adr' ? 'A' : (n.type === 'prd' ? 'P' : 'S')));

    return `<g id="node-${n.id}" class="graph-node-svg" transform="translate(${n.x || 0}, ${n.y || 0})"
         onclick="window.visualizer.handleGraphNodeClick('${n.id}')"
         ondblclick="window.visualizer.openDrawer('${n.id}')"
         onmouseenter="window.visualizer.showGraphTooltip(event, '${n.id}')"
         onmouseleave="window.visualizer.hideGraphTooltip()">
        <circle r="22" fill="${n.color}" fill-opacity="0.12" stroke="${n.color}" stroke-opacity="0.3" stroke-width="1.2" />
        <circle r="14" fill="${n.color}" fill-opacity="0.9" stroke="#111827" stroke-width="2.5" />
        <text text-anchor="middle" y="4" fill="#FFFFFF" font-size="9" font-family="monospace" font-weight="bold">${initial}</text>
        <g transform="translate(18, -10)">
          <rect rx="4" width="${n.id.length * 7 + 12}" height="18" fill="#111827" fill-opacity="0.92" stroke="#374151" stroke-width="0.8" />
          <text x="6" y="12" fill="#F3F4F6" font-size="9.5" font-family="monospace" font-weight="700">${n.id}</text>
        </g>
        ${hasPR ? `<g transform="translate(18, 10)"><rect rx="3" width="36" height="14" fill="#06B6D4" fill-opacity="0.2" stroke="#06B6D4" stroke-width="0.8" /><text x="4" y="10" fill="#22D3EE" font-size="8" font-family="monospace" font-weight="bold">${n.prs[0]}</text></g>` : ''}
      </g>`;
  }

  function renderNodesLayer(nodes) {
    return (nodes || []).map(renderNodeSVG).join('');
  }

  function renderMinimapNodes(nodes) {
    return (nodes || []).map(n => `<circle id="mm-node-${n.id}" class="mm-node" cx="${n.x || 0}" cy="${n.y || 0}" r="18" fill="${n.color}" opacity="0.85" stroke="#111827" stroke-width="2" />`).join('');
  }

  function updateNodePositions(nodes) {
    (nodes || []).forEach(n => {
      const el = document.getElementById(`node-${n.id}`);
      if (el) el.setAttribute('transform', `translate(${n.x}, ${n.y})`);
      const mm = document.getElementById(`mm-node-${n.id}`);
      if (mm) { mm.setAttribute('cx', n.x); mm.setAttribute('cy', n.y); }
    });
  }

  function highlightNodes(nodes, selectedId, connIds) {
    (nodes || []).forEach(n => {
      const isConn = connIds.has(n.id);
      const isSel = n.id === selectedId;
      const el = document.getElementById(`node-${n.id}`);
      if (el) {
        el.style.opacity = isConn ? '1' : '0.12';
        el.style.filter = isSel ? 'drop-shadow(0 0 16px rgba(99, 102, 241, 1))' : 'none';
      }
      const mm = document.getElementById(`mm-node-${n.id}`);
      if (mm) {
        mm.setAttribute('opacity', isConn ? '1' : '0.18');
        mm.setAttribute('r', isSel ? '26' : (isConn ? '20' : '14'));
      }
    });
  }

  function clearNodeHighlightsVisual(nodes) {
    (nodes || []).forEach(n => {
      const el = document.getElementById(`node-${n.id}`);
      if (el) { el.style.opacity = '1'; el.style.filter = 'none'; }
      const mm = document.getElementById(`mm-node-${n.id}`);
      if (mm) { mm.setAttribute('opacity', '0.85'); mm.setAttribute('r', '18'); }
    });
  }

  const api = { extractNodes, renderNodeSVG, renderNodesLayer, renderMinimapNodes, updateNodePositions, highlightNodes, clearNodeHighlightsVisual };
  root.visualizer.graphNodes = api;
  Object.assign(root.visualizer, api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
