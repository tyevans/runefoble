// --- Runefoble Project Content Visualizer: Task Card Subview ---
(function() {
  window.visualizer = window.visualizer || {};
  window.visualizer.drawer = window.visualizer.drawer || {};

  function renderTaskCard(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    const prs = entity.prs || [];
    const commits = entity.commits || [];
    const statusClasses = entity.status === 'Complete'
      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
      : entity.status === 'Refined'
      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
      : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30';

    return `
      <div class="space-y-5">
        <div>
          <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
          <div class="flex flex-wrap items-center gap-2 mt-2">
            <span class="px-2 py-0.5 rounded text-xs font-semibold ${statusClasses}">${entity.status}</span>
            ${entity.target_bc ? `<span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-cyan-300 font-mono border border-slate-700">${entity.target_bc}</span>` : ''}
            ${entity.target_release ? `<span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-purple-300 font-mono border border-slate-700">Release ${entity.target_release}</span>` : ''}
            ${window.visualizer.renderTaskDrawerActions ? window.visualizer.renderTaskDrawerActions(entity) : ''}
          </div>
        </div>

        <!-- Git Commits & Pull Requests Section -->
        <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle space-y-3">
          <h4 class="text-xs font-bold text-white uppercase tracking-wider flex items-center justify-between">
            <span class="flex items-center gap-1.5">
              <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
              Git Commits & Pull Requests
            </span>
            <span class="font-mono text-[11px] text-muted">${commits.length} commits / ${prs.length} PRs</span>
          </h4>
          ${prs.length > 0 ? `
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs text-muted">Pull Requests:</span>
              ${prs.map(pr => `<span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono text-xs font-semibold flex items-center gap-1"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>${pr}</span>`).join('')}
            </div>` : ''}
          ${commits.length > 0 ? `
            <div class="space-y-2 max-h-48 overflow-y-auto pr-1">
              ${commits.map(c => `
                <div class="p-2 rounded bg-[var(--bg-card)] border border-subtle text-xs flex flex-col gap-1">
                  <div class="flex items-center justify-between">
                    <span class="font-mono font-bold text-indigo-400">${c.hash}</span>
                    <span class="text-[10px] text-muted">${c.date} by ${esc(c.author)}</span>
                  </div>
                  <p class="text-slate-300 font-mono text-[11px] leading-tight">${esc(c.subject)}</p>
                </div>`).join('')}
            </div>` : `
            <p class="text-xs text-muted italic">No linked git commits detected. Commits matching <code class="text-indigo-300">task-${entity.id.split('-')[1]}</code> or task frontmatter <code class="text-indigo-300">prs:</code> are linked automatically.</p>`}
        </div>

        <!-- Microfrontends -->
        ${(entity.microfrontends && entity.microfrontends.length > 0) ? `
          <div class="p-3.5 rounded-xl bg-purple-500/5 border border-purple-500/20 space-y-2">
            <h4 class="text-xs font-bold text-purple-400 uppercase tracking-wider">Microfrontends Exposed</h4>
            <div class="flex flex-wrap gap-1.5">
              ${entity.microfrontends.map(mf => `<span class="px-2 py-0.5 rounded font-mono text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">${mf}</span>`).join('')}
            </div>
          </div>` : ''}

        <!-- Governing Documents & Traceability Links -->
        <div class="grid grid-cols-2 gap-3 text-xs">
          <div class="p-3 rounded-lg bg-[var(--bg-elevated)] border border-subtle">
            <div class="font-semibold text-muted mb-1.5">Governing ADRs</div>
            <div class="flex flex-wrap gap-1">
              ${(entity.governing_adrs && entity.governing_adrs.length > 0)
                ? entity.governing_adrs.map(a => `<button onclick="window.visualizer.openDrawer('${a}')" class="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono hover:bg-purple-500/20">${a}</button>`).join('')
                : '<span class="text-muted italic">None</span>'}
            </div>
          </div>
          <div class="p-3 rounded-lg bg-[var(--bg-elevated)] border border-subtle">
            <div class="font-semibold text-muted mb-1.5">Dependencies</div>
            <div class="flex flex-wrap gap-1">
              ${(entity.dependencies && entity.dependencies.length > 0)
                ? entity.dependencies.map(d => `<button onclick="window.visualizer.openDrawer('${d}')" class="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono hover:bg-indigo-500/20">${d}</button>`).join('')
                : '<span class="text-muted italic">None</span>'}
            </div>
          </div>
        </div>

        <!-- Raw Markdown Content Preview -->
        <div class="pt-4 border-t border-subtle">
          <h4 class="text-xs font-bold text-white uppercase tracking-wider mb-2">Specification Markdown</h4>
          <div class="p-4 rounded-xl bg-[var(--bg-card)] border border-subtle overflow-x-auto text-xs font-mono leading-relaxed text-slate-300 max-h-96 overflow-y-auto whitespace-pre-wrap">${esc(entity.raw_markdown || 'No body content available.')}</div>
        </div>
      </div>
    `;
  }

  window.visualizer.drawer.renderTaskCard = renderTaskCard;
})();
