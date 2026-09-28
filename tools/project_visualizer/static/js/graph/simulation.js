// --- Runefoble Project Content Visualizer: Graph Simulation Engine ---
(function() {
  const root = typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this);
  root.visualizer = root.visualizer || {};

  if (typeof root.visualizer.ForceSimulation !== 'function') {
    root.visualizer.ForceSimulation = class {
      constructor(n, e) { this.nodes = n; this.edges = e; }
      start(cb) { if (cb) cb(); } stop() {} reheat() {} applyFlowLayout() {} applyRadialLayout() {}
    };
  }

  function initSimulation(nodes, edges, updatePositions, options = {}) {
    if (root.visualizer.sim) root.visualizer.sim.stop();
    const gs = root.visualizer.graphState || {};
    const w = options.width || gs.canvasWidth || 2200;
    const h = options.height || gs.canvasHeight || 1400;
    const sim = new root.visualizer.ForceSimulation(nodes, edges, { width: w, height: h, ...options });
    root.visualizer.sim = sim;

    if (gs.activeLayout === 'flow') sim.applyFlowLayout();
    else if (gs.activeLayout === 'radial') sim.applyRadialLayout();
    else if (gs.physicsRunning) sim.start(updatePositions);
    return sim;
  }

  function toggleGraphPhysics(updatePositions) {
    const gs = root.visualizer.graphState;
    if (!gs) return;
    gs.physicsRunning = !gs.physicsRunning;
    const btn = document.getElementById('graph-physics-btn');
    if (btn) btn.textContent = gs.physicsRunning ? '⏸️ Freeze' : '▶️ Run';
    const sim = root.visualizer.sim;
    if (sim) {
      if (gs.physicsRunning) sim.start(updatePositions || root.visualizer.updatePositions);
      else sim.stop();
    }
  }

  function reheatGraphPhysics() {
    const gs = root.visualizer.graphState;
    if (gs) gs.physicsRunning = true;
    const btn = document.getElementById('graph-physics-btn');
    if (btn) btn.textContent = '⏸️ Freeze';
    if (root.visualizer.sim) root.visualizer.sim.reheat(0.9);
  }

  function switchGraphLayout(layout, updatePositions) {
    const gs = root.visualizer.graphState;
    if (!gs) return;
    gs.activeLayout = layout;
    ['network', 'flow', 'radial'].forEach(l => {
      const btn = document.getElementById(`layout-btn-${l}`);
      if (btn) {
        btn.className = l === layout
          ? 'px-2.5 py-1 rounded-md font-medium transition bg-indigo-600 text-white shadow-sm'
          : 'px-2.5 py-1 rounded-md font-medium transition text-muted hover:text-white';
      }
    });
    const sim = root.visualizer.sim;
    if (sim) {
      if (layout === 'flow') sim.applyFlowLayout();
      else if (layout === 'radial') sim.applyRadialLayout();
      else sim.reheat(0.85);
      const updateFn = updatePositions || root.visualizer.updatePositions;
      if (updateFn) updateFn();
    }
  }

  const api = { initSimulation, toggleGraphPhysics, reheatGraphPhysics, switchGraphLayout };
  root.visualizer.graphSimulation = api;
  Object.assign(root.visualizer, api);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
