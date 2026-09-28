// --- Runefoble Project Content Visualizer: Graph Link & Marker Renderer ---
(function() {
  const root = typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this);
  root.visualizer = root.visualizer || {};

  function filterEdges(edges, nodes) {
    const nodeIds = new Set((nodes || []).map(n => n.id));
    return (edges || []).filter(e => nodeIds.has(e.source_id) && nodeIds.has(e.target_id));
  }

  function renderMarkerDefs() {
    return `<defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563" /></marker>
      <marker id="arrow-glow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#6366F1" /></marker>
    </defs>`;
  }

  function renderEdgesLayer(edges) {
    return (edges || []).map(e => `<line id="edge-${e.source_id}-${e.target_id}" x1="0" y1="0" x2="0" y2="0" stroke="#374151" stroke-width="1.3" stroke-opacity="0.38" marker-end="url(#arrow)" />`).join('');
  }

  function updateEdgePositions(edges, nodes) {
    const nodeMap = nodes instanceof Map ? nodes : new Map((nodes || []).map(n => [n.id, n]));
    (edges || []).forEach(e => {
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
  }

  function findConnectedNetwork(nodeId, edges, depth = 'lineage') {
    const connectedNodeIds = new Set([nodeId]);
    const connectedEdgeIds = new Set();
    const queue = [nodeId];

    while (queue.length > 0) {
      const cur = queue.shift();
      (edges || []).forEach(e => {
        if (e.source_id === cur && !connectedNodeIds.has(e.target_id)) {
          connectedNodeIds.add(e.target_id);
          connectedEdgeIds.add(`${e.source_id}-${e.target_id}`);
          if (depth === 'lineage') queue.push(e.target_id);
        }
        if (e.target_id === cur && !connectedNodeIds.has(e.source_id)) {
          connectedNodeIds.add(e.source_id);
          connectedEdgeIds.add(`${e.source_id}-${e.target_id}`);
          if (depth === 'lineage') queue.push(e.source_id);
        }
      });
    }
    return { nodeIds: connectedNodeIds, edgeIds: connectedEdgeIds };
  }

  function highlightEdges(edges, connectedEdgeIds) {
    (edges || []).forEach(e => {
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

  function clearEdgeHighlightsVisual(edges) {
    (edges || []).forEach(e => {
      const el = document.getElementById(`edge-${e.source_id}-${e.target_id}`);
      if (el) {
        el.setAttribute('stroke', '#374151');
        el.setAttribute('stroke-width', '1.3');
        el.setAttribute('stroke-opacity', '0.38');
        el.setAttribute('marker-end', 'url(#arrow)');
        el.classList.remove('edge-active-flow');
      }
    });
  }

  const api = { filterEdges, renderMarkerDefs, renderEdgesLayer, updateEdgePositions, findConnectedNetwork, highlightEdges, clearEdgeHighlightsVisual };
  root.visualizer.graphLinks = api;
  Object.assign(root.visualizer, api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
