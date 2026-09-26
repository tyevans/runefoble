// --- Runefoble Project Content Visualizer: Graph Camera & Viewport Interactions ---
(function() {
  window.visualizer = window.visualizer || {};

  function getGraphState() {
    return window.visualizer.graphState;
  }

  function applyTransform() {
    const s = getGraphState();
    if (!s) return;
    const layer = document.getElementById('graph-pan-layer');
    if (layer) layer.setAttribute('transform', `translate(${s.panX}, ${s.panY}) scale(${s.zoom})`);
    updateMinimap();
  }

  function updateMinimap() {
    const s = getGraphState();
    const rect = document.getElementById('minimap-view-rect');
    const viewport = document.getElementById('graph-viewport');
    if (!s || !rect || !viewport) return;

    const vW = viewport.clientWidth;
    const vH = viewport.clientHeight;
    const vX = -s.panX / s.zoom;
    const vY = -s.panY / s.zoom;
    const rectW = vW / s.zoom;
    const rectH = vH / s.zoom;

    rect.setAttribute('x', vX);
    rect.setAttribute('y', vY);
    rect.setAttribute('width', Math.max(10, rectW));
    rect.setAttribute('height', Math.max(10, rectH));
  }

  function moveCameraToMinimapPoint(e) {
    const s = getGraphState();
    const mm = document.getElementById('graph-minimap');
    const viewport = document.getElementById('graph-viewport');
    if (!s || !mm || !viewport) return;

    const mmRect = mm.getBoundingClientRect();
    const vW = viewport.clientWidth;
    const vH = viewport.clientHeight;

    const clickX = Math.max(0, Math.min(mmRect.width, e.clientX - mmRect.left));
    const clickY = Math.max(0, Math.min(mmRect.height, e.clientY - mmRect.top));

    const worldX = (clickX / mmRect.width) * s.canvasWidth;
    const worldY = (clickY / mmRect.height) * s.canvasHeight;

    s.panX = (vW / 2) - (worldX * s.zoom);
    s.panY = (vH / 2) - (worldY * s.zoom);
    applyTransform();
  }

  function zoomGraph(factor, focalX, focalY) {
    const s = getGraphState();
    const vp = document.getElementById('graph-viewport');
    if (!s || !vp) return;
    const rect = vp.getBoundingClientRect();

    if (focalX === undefined || focalY === undefined) {
      focalX = rect.width / 2;
      focalY = rect.height / 2;
    }

    const oldZoom = s.zoom;
    const newZoom = Math.max(0.18, Math.min(4.0, oldZoom * factor));
    if (Math.abs(newZoom - oldZoom) < 0.0001) return;

    const ratio = newZoom / oldZoom;
    s.panX = focalX - (focalX - s.panX) * ratio;
    s.panY = focalY - (focalY - s.panY) * ratio;
    s.zoom = newZoom;

    applyTransform();
  }

  function resetGraphView() {
    const s = getGraphState();
    const vp = document.getElementById('graph-viewport');
    if (!s || !vp) return;

    const vw = vp.clientWidth || 1200;
    const vh = vp.clientHeight || 800;
    const fitZoom = Math.min(vw / s.canvasWidth, vh / s.canvasHeight) * 0.92;
    s.zoom = Math.max(0.35, Math.min(1.0, fitZoom || 0.65));
    s.panX = (vw - s.canvasWidth * s.zoom) / 2;
    s.panY = (vh - s.canvasHeight * s.zoom) / 2;
    applyTransform();
    if (window.visualizer.clearNodeHighlights) window.visualizer.clearNodeHighlights();
  }

  function setupGraphInteractions() {
    const s = getGraphState();
    const viewport = document.getElementById('graph-viewport');
    const minimap = document.getElementById('graph-minimap');
    if (!s || !viewport) return;

    viewport.onwheel = (e) => {
      e.preventDefault();
      const delta = e.deltaMode === 1 ? e.deltaY * 20 : e.deltaY;
      const factor = Math.max(0.68, Math.min(1.45, Math.exp(-delta * 0.0018)));
      const rect = viewport.getBoundingClientRect();
      zoomGraph(factor, e.clientX - rect.left, e.clientY - rect.top);
    };

    viewport.ondblclick = (e) => {
      if (e.target.closest('.graph-node-svg') || e.target.closest('#graph-minimap')) return;
      const rect = viewport.getBoundingClientRect();
      zoomGraph(1.35, e.clientX - rect.left, e.clientY - rect.top);
    };

    viewport.onmousedown = (e) => {
      if (e.target.closest('#graph-minimap')) return;
      const nodeEl = e.target.closest('.graph-node-svg');
      const rect = viewport.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (nodeEl) {
        const nId = nodeEl.id.replace('node-', '');
        const targetNode = s.nodes.find(n => n.id === nId);
        if (targetNode) {
          s.dragNode = targetNode;
          targetNode.isFixed = true;
          s.dragOffsetX = targetNode.x - (mouseX - s.panX) / s.zoom;
          s.dragOffsetY = targetNode.y - (mouseY - s.panY) / s.zoom;
          s.startX = e.clientX;
          s.startY = e.clientY;
          s.dragDistance = 0;
          if (window.visualizer.sim && s.physicsRunning) window.visualizer.sim.reheat(0.4);
        }
        return;
      }

      s.isDraggingCanvas = true;
      s.startX = e.clientX;
      s.startY = e.clientY;
      s.startPanX = s.panX;
      s.startPanY = s.panY;
      s.dragDistance = 0;
    };

    if (minimap) {
      minimap.onmousedown = (e) => {
        e.stopPropagation();
        e.preventDefault();
        s.isDraggingMinimap = true;
        moveCameraToMinimapPoint(e);
      };
    }

    window.onmousemove = (e) => {
      if (s.dragNode) {
        const rect = viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        s.dragDistance = Math.hypot(e.clientX - s.startX, e.clientY - s.startY);
        const nextX = (mouseX - s.panX) / s.zoom + s.dragOffsetX;
        const nextY = (mouseY - s.panY) / s.zoom + s.dragOffsetY;
        s.dragNode.x = Math.max(40, Math.min(s.canvasWidth - 40, nextX));
        s.dragNode.y = Math.max(40, Math.min(s.canvasHeight - 40, nextY));
        if (window.visualizer.updatePositions) window.visualizer.updatePositions();
        return;
      }

      if (s.isDraggingCanvas) {
        s.dragDistance = Math.hypot(e.clientX - s.startX, e.clientY - s.startY);
        s.panX = s.startPanX + (e.clientX - s.startX);
        s.panY = s.startPanY + (e.clientY - s.startY);
        applyTransform();
        return;
      }

      if (s.isDraggingMinimap) {
        moveCameraToMinimapPoint(e);
        return;
      }
    };

    window.onmouseup = () => {
      if (s.dragNode) {
        s.dragNode.isFixed = false;
        s.dragNode = null;
      }
      s.isDraggingCanvas = false;
      s.isDraggingMinimap = false;
    };

    window.onresize = () => {
      updateMinimap();
    };
  }

  function showGraphTooltip(e, id) {
    const s = getGraphState();
    if (!s || s.isDraggingCanvas || s.dragNode) return;
    const node = s.nodes.find(n => n.id === id);
    const tooltip = document.getElementById('graph-tooltip');
    const viewport = document.getElementById('graph-viewport');
    if (!node || !tooltip || !viewport) return;

    const vpRect = viewport.getBoundingClientRect();
    let left = e.clientX - vpRect.left + 15;
    let top = e.clientY - vpRect.top + 15;
    if (left + 265 > vpRect.width) left = Math.max(10, e.clientX - vpRect.left - 275);
    if (top + 165 > vpRect.height) top = Math.max(10, e.clientY - vpRect.top - 175);

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;

    const esc = window.visualizer.escapeHtml || (str => str);
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
    const s = getGraphState();
    const wrap = document.getElementById('graph-viewport-wrapper');
    const btn = document.getElementById('graph-fs-btn');
    if (!s || !wrap) return;
    s.isFullscreen = !s.isFullscreen;
    wrap.classList.toggle('graph-fullscreen', s.isFullscreen);
    if (btn) btn.textContent = s.isFullscreen ? '✖' : '⛶';
    setTimeout(() => { updateMinimap(); }, 50);
  }

  Object.assign(window.visualizer, {
    applyTransform, updateMinimap, moveCameraToMinimapPoint,
    zoomGraph, resetGraphView, setupGraphInteractions,
    showGraphTooltip, hideGraphTooltip, toggleGraphFullscreen,
  });
})();
