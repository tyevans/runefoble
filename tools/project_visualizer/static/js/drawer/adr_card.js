// --- Runefoble Project Content Visualizer: ADR Card Subview ---
(function() {
  window.visualizer = window.visualizer || {};
  window.visualizer.drawer = window.visualizer.drawer || {};

  function renderAdrCard(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    const md = window.visualizer.renderMarkdown || esc;
    const implTasks = entity.implementing_tasks || [];

    return `
      <div class="space-y-5">
        <div>
          <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2 py-0.5 rounded text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">${entity.status}</span>
            <span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 font-mono">${entity.domain}</span>
            <span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400 font-mono">${entity.date || '2026-09-25'}</span>
          </div>
        </div>

        <div class="space-y-3">
          ${entity.context ? `
            <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle">
              <h4 class="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-2">Context</h4>
              <div class="text-xs text-slate-300 leading-relaxed">${md(entity.context)}</div>
            </div>
          ` : ''}

          <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle">
            <h4 class="text-xs font-bold text-purple-400 uppercase tracking-wider mb-2">Decision</h4>
            <div class="text-xs text-slate-300 leading-relaxed">${md(entity.decision || 'See ADR document.')}</div>
          </div>

          <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Consequences</h4>
            <div class="text-xs text-slate-300 leading-relaxed">${md(entity.consequences || 'Documented in architectural decision record.')}</div>
          </div>

          ${implTasks.length > 0 ? `
            <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle space-y-2">
              <h4 class="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between">
                <span>Implementing Tasks</span>
                <span class="font-mono text-[11px] text-muted">${implTasks.length} tasks</span>
              </h4>
              <div class="flex flex-wrap gap-1.5">
                ${implTasks.map(t => `<button onclick="window.visualizer.openDrawer('${t}')" class="px-2 py-0.5 rounded font-mono text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition">${t}</button>`).join('')}
              </div>
            </div>
          ` : ''}

          ${entity.raw_markdown ? `
            <div class="pt-4 border-t border-subtle">
              <h4 class="text-xs font-bold text-white uppercase tracking-wider mb-2">Full ADR Markdown</h4>
              <div class="p-4 rounded-xl bg-[var(--bg-card)] border border-subtle text-xs font-mono whitespace-pre-wrap max-h-64 overflow-y-auto text-slate-300">${esc(entity.raw_markdown)}</div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  window.visualizer.drawer.renderAdrCard = renderAdrCard;
})();
