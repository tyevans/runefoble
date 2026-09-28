// --- Runefoble Project Content Visualizer: AGY Modal Controller ---
(function() {
  window.visualizer = window.visualizer || {};
  const agy = window.visualizer.agy = window.visualizer.agy || {};

  function openAgyModal(prefilledPrompt = '', targetEntityId = null) {
    const modal = document.getElementById('agy-modal');
    const backdrop = document.getElementById('agy-modal-backdrop');
    const promptInput = document.getElementById('agy-prompt-input');
    const targetBadge = document.getElementById('agy-target-badge');

    if (!modal || !backdrop) return;

    agy.currentTargetEntityId = targetEntityId;
    if (targetBadge) {
      targetBadge.textContent = targetEntityId || 'General Workspace';
    }

    if (promptInput) {
      if (prefilledPrompt) {
        promptInput.value = prefilledPrompt;
      } else if (!promptInput.value.trim()) {
        if (typeof window.visualizer.setAgyPreset === 'function') {
          window.visualizer.setAgyPreset('feature_process');
        }
      }
    }

    if (typeof window.visualizer.updateAgyCommandPreview === 'function') {
      window.visualizer.updateAgyCommandPreview();
    }

    backdrop.classList.remove('hidden');
    modal.classList.remove('hidden');
    setTimeout(() => {
      backdrop.classList.remove('opacity-0');
      if (promptInput) promptInput.focus();
    }, 10);
  }

  function closeAgyModal() {
    const modal = document.getElementById('agy-modal');
    const backdrop = document.getElementById('agy-modal-backdrop');
    if (!modal || !backdrop) return;

    backdrop.classList.add('opacity-0');
    setTimeout(() => {
      backdrop.classList.add('hidden');
      modal.classList.add('hidden');
    }, 200);
  }

  function launchAgyForEntity(entityId) {
    const d = window.visualizer.state ? window.visualizer.state.data : null;
    let prefilled = '';

    if (d && d.tasks) {
      const task = d.tasks.find(t => t.id === entityId);
      if (task && typeof agy.buildTaskPrompt === 'function') {
        prefilled = agy.buildTaskPrompt(task);
      }
    }

    openAgyModal(prefilled, entityId);
  }

  function renderTaskDrawerActions(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    return `
      <button onclick="window.visualizer.launchAgyForEntity('${esc(entity.id)}')" class="ml-auto px-2.5 py-1 rounded bg-gradient-to-r from-amber-500/20 to-indigo-500/20 hover:from-amber-500/30 hover:to-indigo-500/30 text-amber-300 border border-amber-500/30 hover:border-amber-400 text-xs font-medium flex items-center gap-1.5 transition shadow-sm" title="Launch bespoke agy prompt for ${esc(entity.id)}">
        <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        <span>Launch AGY</span>
      </button>
    `;
  }

  const addKeyHandler = (target) => {
    if (typeof target?.addEventListener === 'function') {
      target.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          const modal = document.getElementById('agy-modal');
          if (modal && !modal.classList.contains('hidden')) {
            closeAgyModal();
          }
        }
      });
    }
  };
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    addKeyHandler(window);
  } else if (typeof document !== 'undefined') {
    addKeyHandler(document);
  }

  Object.assign(agy, { openAgyModal, closeAgyModal, launchAgyForEntity, renderTaskDrawerActions });
  Object.assign(window.visualizer, { openAgyModal, closeAgyModal, launchAgyForEntity, renderTaskDrawerActions });
})();
