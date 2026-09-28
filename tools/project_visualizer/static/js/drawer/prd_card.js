// --- Runefoble Project Content Visualizer: PRD & Story Subview ---
(function() {
  window.visualizer = window.visualizer || {};
  window.visualizer.drawer = window.visualizer.drawer || {};

  function renderStoryCard(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    return `
      <div class="space-y-5">
        <div>
          <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
          <span class="px-2 py-0.5 rounded text-xs font-semibold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">Persona: ${esc(entity.persona)}</span>
        </div>

        <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle space-y-2 text-sm">
          <p><strong class="text-cyan-400">As a:</strong> ${esc(entity.as_a || entity.persona)}</p>
          <p><strong class="text-cyan-400">I want to:</strong> ${esc(entity.i_want || entity.title)}</p>
          <p><strong class="text-cyan-400">So that:</strong> ${esc(entity.so_that || '')}</p>
        </div>

        <div class="space-y-2">
          <h4 class="text-xs font-bold text-white uppercase tracking-wider">Acceptance Criteria</h4>
          <ul class="space-y-2">
            ${(entity.acceptance_criteria || []).map(ac => `
              <li class="p-2.5 rounded-lg bg-[var(--bg-card)] border border-subtle text-xs flex items-start gap-2 text-slate-300">
                <span class="text-emerald-400 font-bold">✓</span>
                <span>${esc(ac)}</span>
              </li>
            `).join('')}
          </ul>
        </div>

        <div class="pt-4 border-t border-subtle">
          <h4 class="text-xs font-bold text-white uppercase tracking-wider mb-2">Full Markdown</h4>
          <div class="p-4 rounded-xl bg-[var(--bg-card)] border border-subtle text-xs font-mono whitespace-pre-wrap max-h-64 overflow-y-auto text-slate-300">${esc(entity.raw_markdown)}</div>
        </div>
      </div>
    `;
  }

  function renderPrdCard(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    const md = window.visualizer.renderMarkdown || esc;
    return `
      <div class="space-y-5">
        <div>
          <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
          <span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">${entity.status}</span>
        </div>

        <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle space-y-3">
          <h4 class="text-xs font-bold text-rose-400 uppercase tracking-wider">Problem Statement</h4>
          <div class="text-xs text-slate-300 leading-relaxed">${md(entity.problem_statement || 'See specification document.')}</div>
        </div>

        <div class="space-y-2">
          <h4 class="text-xs font-bold text-white uppercase tracking-wider">Checkable Outcomes</h4>
          <ul class="space-y-2">
            ${(entity.outcomes || []).map(o => `
              <li class="p-2.5 rounded-lg bg-[var(--bg-card)] border border-subtle text-xs text-slate-300 flex items-start gap-2">
                <span class="text-rose-400 font-bold">•</span>
                <span class="flex-1">${md(o)}</span>
              </li>
            `).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  window.visualizer.drawer.renderStoryCard = renderStoryCard;
  window.visualizer.drawer.renderPrdCard = renderPrdCard;
})();
