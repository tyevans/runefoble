// --- Runefoble Project Content Visualizer: Persona Card Subview ---
(function() {
  window.visualizer = window.visualizer || {};
  window.visualizer.drawer = window.visualizer.drawer || {};

  function renderPersonaCard(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    const inlineMd = window.visualizer.renderInlineMarkdown || esc;

    return `
      <div class="space-y-5">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-white text-lg shadow-md" style="background-color: ${entity.avatar_color || '#6366F1'};">
            ${(entity.name || 'P')[0]}
          </div>
          <div>
            <h3 class="text-lg font-bold text-white">${esc(entity.name)}</h3>
            <p class="text-xs text-muted">${esc(entity.role)}</p>
          </div>
        </div>

        <blockquote class="p-3.5 rounded-xl bg-[var(--bg-elevated)] border-l-4 border-indigo-500 text-xs text-slate-300 italic">
          "${inlineMd(entity.quote)}"
        </blockquote>

        <div class="space-y-2">
          <h4 class="text-xs font-bold text-amber-400 uppercase tracking-wider">Pain Points</h4>
          <ul class="space-y-1.5">
            ${(entity.pain_points || []).map(p => `<li class="text-xs text-slate-300 flex items-start gap-2"><span>⚠️</span><span class="flex-1 leading-relaxed">${inlineMd(p)}</span></li>`).join('')}
          </ul>
        </div>

        <div class="space-y-2">
          <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Goals with Runefoble</h4>
          <ul class="space-y-1.5">
            ${(entity.goals || []).map(g => `<li class="text-xs text-slate-300 flex items-start gap-2"><span>🎯</span><span class="flex-1 leading-relaxed">${inlineMd(g)}</span></li>`).join('')}
          </ul>
        </div>

        ${(entity.key_features && entity.key_features.length > 0) ? `
          <div class="space-y-2 pt-2 border-t border-subtle">
            <h4 class="text-xs font-bold text-cyan-400 uppercase tracking-wider">Key Features Used</h4>
            <div class="flex flex-wrap gap-1.5">
              ${entity.key_features.map(f => `<span class="px-2 py-0.5 rounded font-mono text-xs bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">${f}</span>`).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  window.visualizer.drawer.renderPersonaCard = renderPersonaCard;
})();
