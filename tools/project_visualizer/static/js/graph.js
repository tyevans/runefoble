// --- Runefoble Project Content Visualizer: Interactive 2D Relationship Graph Network ---
(function() {
  const root = typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this);
  root.visualizer = root.visualizer || {};

  const canvasWidth = 2200, canvasHeight = 1400;
  const graphState = root.visualizer.graphState = root.visualizer.graphState || {
    nodes: [], edges: [], selectedId: null, zoom: 0.72, panX: 0, panY: 0,
    canvasWidth, canvasHeight, isDraggingCanvas: false, isDraggingMinimap: false,
    dragNode: null, dragOffsetX: 0, dragOffsetY: 0, dragDistance: 0,
    startX: 0, startY: 0, startPanX: 0, startPanY: 0,
    activeTypeFilter: 'all', activeLayout: 'network', depth: 'lineage',
    physicsRunning: true, isFullscreen: false, initialized: false,
  };

  function renderGraph(container, state) {
    const d = state.data;
    if (!d) return;
    const nodes = root.visualizer.extractNodes ? root.visualizer.extractNodes(d, state.filters, graphState.activeTypeFilter) : [];
    const edges = root.visualizer.filterEdges ? root.visualizer.filterEdges(d.edges || [], nodes) : [];
    graphState.nodes = nodes;
    graphState.edges = edges;

    if (root.visualizer.initSimulation) root.visualizer.initSimulation(nodes, edges, updatePositions);
    if (root.visualizer.renderViewportShell) container.innerHTML = root.visualizer.renderViewportShell(nodes, edges, state);
    if (root.visualizer.setupGraphInteractions) root.visualizer.setupGraphInteractions();
    if (!graphState.initialized) {
      if (root.visualizer.resetGraphView) root.visualizer.resetGraphView();
      graphState.initialized = true;
    } else if (root.visualizer.applyTransform) {
      root.visualizer.applyTransform();
    }
    updatePositions();
  }

  function updatePositions() {
    if (root.visualizer.updateNodePositions) root.visualizer.updateNodePositions(graphState.nodes);
    if (root.visualizer.updateEdgePositions) root.visualizer.updateEdgePositions(graphState.edges, graphState.nodes);
    if (root.visualizer.updateMinimap) root.visualizer.updateMinimap();
  }

  function handleGraphNodeClick(nodeId) {
    if (graphState.dragDistance > 6) return;
    if (graphState.selectedId === nodeId) {
      if (root.visualizer.openDrawer) root.visualizer.openDrawer(nodeId);
      return;
    }
    graphState.selectedId = nodeId;
    const net = root.visualizer.findConnectedNetwork ? root.visualizer.findConnectedNetwork(nodeId, graphState.edges, graphState.depth) : { nodeIds: new Set([nodeId]), edgeIds: new Set() };
    if (root.visualizer.highlightNodes) root.visualizer.highlightNodes(graphState.nodes, nodeId, net.nodeIds);
    if (root.visualizer.highlightEdges) root.visualizer.highlightEdges(graphState.edges, net.edgeIds);
  }

  function clearNodeHighlights() {
    graphState.selectedId = null;
    if (root.visualizer.clearNodeHighlightsVisual) root.visualizer.clearNodeHighlightsVisual(graphState.nodes);
    if (root.visualizer.clearEdgeHighlightsVisual) root.visualizer.clearEdgeHighlightsVisual(graphState.edges);
  }

  const api = { renderGraph, updatePositions, handleGraphNodeClick, clearNodeHighlights };
  Object.assign(root.visualizer, api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
