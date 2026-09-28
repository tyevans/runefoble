// --- Runefoble Project Content Visualizer: Drawer Controller ---
(function() {
  window.visualizer = window.visualizer || {};
  window.visualizer.drawer = window.visualizer.drawer || {};

  function renderEntityBody(entity, type) {
    const d = window.visualizer.drawer;
    const map = { TASK: d.renderTaskCard, STORY: d.renderStoryCard, PRD: d.renderPrdCard, ADR: d.renderAdrCard, PERSONA: d.renderPersonaCard };
    return map[type] ? map[type](entity) : '<div class="text-xs text-muted">No details available.</div>';
  }

  function findEntity(id) {
    const d = window.visualizer.state?.data;
    if (!d) return null;
    let entity = (d.tasks || []).find(t => t.id === id);
    if (entity) return { entity, type: 'TASK' };
    entity = (d.stories || []).find(s => s.id === id);
    if (entity) return { entity, type: 'STORY' };
    entity = (d.prds || []).find(p => p.id === id);
    if (entity) return { entity, type: 'PRD' };
    entity = (d.adrs || []).find(a => a.id === id);
    if (entity) return { entity, type: 'ADR' };
    entity = (d.personas || []).find(p => p.id === id || (p.name && p.name.toLowerCase() === id.toLowerCase()));
    return entity ? { entity, type: 'PERSONA' } : null;
  }

  function openDrawer(id, animate = true) {
    const match = findEntity(id);
    if (!match) return;
    const { entity, type } = match;
    if (window.visualizer.state) window.visualizer.state.selectedNode = entity;

    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    const badge = document.getElementById('drawer-type-badge');
    const titleId = document.getElementById('drawer-id');
    const body = document.getElementById('drawer-body');
    const filepathEl = document.getElementById('drawer-filepath');

    if (!drawer || !body) return;
    if (badge) badge.textContent = type;
    if (titleId) titleId.textContent = entity.id || entity.name;
    if (filepathEl) filepathEl.innerHTML = `<span>File:</span> <span class="text-indigo-400 font-semibold truncate max-w-[340px]">${entity.file_path || 'docs/project/'}</span>`;
    body.innerHTML = renderEntityBody(entity, type);

    if (backdrop) {
      backdrop.classList.remove('hidden');
      setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
    }
    drawer.classList.remove('translate-x-full');
  }

  function closeDrawer() {
    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    if (drawer) drawer.classList.add('translate-x-full');
    if (backdrop) {
      backdrop.classList.add('opacity-0');
      setTimeout(() => backdrop.classList.add('hidden'), 300);
    }
    if (window.visualizer.state) window.visualizer.state.selectedNode = null;
  }

  function copyDrawerFilepath() {
    const node = window.visualizer.state?.selectedNode;
    if (!node?.file_path) return;
    const nav = window.navigator || (typeof navigator !== 'undefined' ? navigator : null);
    if (!nav?.clipboard?.writeText) return;
    nav.clipboard.writeText(node.file_path).then(() => {
      const btn = typeof event !== 'undefined' ? event.currentTarget : null;
      if (!btn) return;
      const original = btn.innerHTML;
      btn.innerHTML = '<span>Copied!</span>';
      setTimeout(() => { btn.innerHTML = original; }, 1500);
    });
  }

  Object.assign(window.visualizer.drawer, { findEntity, openDrawer, closeDrawer, copyDrawerFilepath, renderEntityBody });
})();
