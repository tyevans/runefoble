// --- Runefoble Project Content Visualizer: Detail Drawer & Markdown Viewer ---
(function() {
  window.visualizer = window.visualizer || {};

  function openDrawer(id, animate = true) {
    const d = window.visualizer.state.data;
    if (!d) return;

    let entity = null;
    let type = 'TASK';

    entity = (d.tasks || []).find(t => t.id === id);
    if (!entity) {
      entity = (d.stories || []).find(s => s.id === id);
      if (entity) type = 'STORY';
    }
    if (!entity) {
      entity = (d.prds || []).find(p => p.id === id);
      if (entity) type = 'PRD';
    }
    if (!entity) {
      entity = (d.adrs || []).find(a => a.id === id);
      if (entity) type = 'ADR';
    }
    if (!entity) {
      entity = (d.personas || []).find(p => p.id === id || p.name.toLowerCase() === id.toLowerCase());
      if (entity) type = 'PERSONA';
    }

    if (!entity) return;
    window.visualizer.state.selectedNode = entity;

    const drawer = document.getElementById('drawer');
    const backdrop = document.getElementById('drawer-backdrop');
    const badge = document.getElementById('drawer-type-badge');
    const titleId = document.getElementById('drawer-id');
    const body = document.getElementById('drawer-body');
    const filepathEl = document.getElementById('drawer-filepath');

    if (!drawer || !body) return;

    if (badge) badge.textContent = type;
    if (titleId) titleId.textContent = entity.id || entity.name;
    if (filepathEl) {
      filepathEl.innerHTML = `<span>File:</span> <span class="text-indigo-400 font-semibold truncate max-w-[340px]">${entity.file_path || 'docs/project/'}</span>`;
    }

    body.innerHTML = renderEntityBody(entity, type);

    backdrop.classList.remove('hidden');
    setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
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
    window.visualizer.state.selectedNode = null;
  }

  function renderEntityBody(entity, type) {
    const esc = window.visualizer.escapeHtml;

    if (type === 'TASK') {
      const prs = entity.prs || [];
      const commits = entity.commits || [];

      return `
        <div class="space-y-5">
          <div>
            <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
            <div class="flex flex-wrap items-center gap-2 mt-2">
              <span class="px-2 py-0.5 rounded text-xs font-semibold ${
                entity.status === 'Complete' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                entity.status === 'Refined' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
              }">${entity.status}</span>
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
                ${prs.map(pr => `
                  <span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono text-xs font-semibold flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                    ${pr}
                  </span>
                `).join('')}
              </div>
            ` : ''}

            ${commits.length > 0 ? `
              <div class="space-y-2 max-h-48 overflow-y-auto pr-1">
                ${commits.map(c => `
                  <div class="p-2 rounded bg-[var(--bg-card)] border border-subtle text-xs flex flex-col gap-1">
                    <div class="flex items-center justify-between">
                      <span class="font-mono font-bold text-indigo-400">${c.hash}</span>
                      <span class="text-[10px] text-muted">${c.date} by ${esc(c.author)}</span>
                    </div>
                    <p class="text-slate-300 font-mono text-[11px] leading-tight">${esc(c.subject)}</p>
                  </div>
                `).join('')}
              </div>
            ` : `
              <p class="text-xs text-muted italic">No linked git commits detected. Commits matching <code class="text-indigo-300">task-${entity.id.split('-')[1]}</code> or task frontmatter <code class="text-indigo-300">prs:</code> are linked automatically.</p>
            `}
          </div>

          <!-- Microfrontends -->
          ${(entity.microfrontends && entity.microfrontends.length > 0) ? `
            <div class="p-3.5 rounded-xl bg-purple-500/5 border border-purple-500/20 space-y-2">
              <h4 class="text-xs font-bold text-purple-400 uppercase tracking-wider">Microfrontends Exposed</h4>
              <div class="flex flex-wrap gap-1.5">
                ${entity.microfrontends.map(mf => `<span class="px-2 py-0.5 rounded font-mono text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">${mf}</span>`).join('')}
              </div>
            </div>
          ` : ''}

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

    if (type === 'STORY') {
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

    if (type === 'PRD') {
      return `
        <div class="space-y-5">
          <div>
            <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
            <span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">${entity.status}</span>
          </div>

          <div class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle space-y-3">
            <h4 class="text-xs font-bold text-rose-400 uppercase tracking-wider">Problem Statement</h4>
            <p class="text-xs text-slate-300 leading-relaxed">${esc(entity.problem_statement || 'See specification document.')}</p>
          </div>

          <div class="space-y-2">
            <h4 class="text-xs font-bold text-white uppercase tracking-wider">Checkable Outcomes</h4>
            <ul class="space-y-2">
              ${(entity.outcomes || []).map(o => `
                <li class="p-2.5 rounded-lg bg-[var(--bg-card)] border border-subtle text-xs text-slate-300 flex items-start gap-2">
                  <span class="text-rose-400 font-bold">•</span>
                  <span>${esc(o)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        </div>
      `;
    }

    if (type === 'ADR') {
      return `
        <div class="space-y-5">
          <div>
            <h3 class="text-lg font-bold text-white mb-1">${esc(entity.title)}</h3>
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">${entity.status}</span>
              <span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 font-mono">${entity.domain}</span>
            </div>
          </div>

          <div class="space-y-3">
            <div class="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-subtle">
              <h4 class="text-xs font-bold text-purple-400 uppercase mb-1">Decision</h4>
              <p class="text-xs text-slate-300 leading-relaxed">${esc(entity.decision || 'See ADR document.')}</p>
            </div>
            <div class="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-subtle">
              <h4 class="text-xs font-bold text-slate-400 uppercase mb-1">Consequences</h4>
              <p class="text-xs text-slate-300 leading-relaxed">${esc(entity.consequences || 'Documented in architectural decision record.')}</p>
            </div>
          </div>
        </div>
      `;
    }

    if (type === 'PERSONA') {
      return `
        <div class="space-y-5">
          <div class="flex items-center space-x-3">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-white text-lg" style="background-color: ${entity.avatar_color || '#6366F1'};">
              ${(entity.name || 'P')[0]}
            </div>
            <div>
              <h3 class="text-lg font-bold text-white">${esc(entity.name)}</h3>
              <p class="text-xs text-muted">${esc(entity.role)}</p>
            </div>
          </div>

          <blockquote class="p-3.5 rounded-xl bg-[var(--bg-elevated)] border-l-4 border-indigo-500 text-xs text-slate-300 italic">
            "${esc(entity.quote)}"
          </blockquote>

          <div class="space-y-2">
            <h4 class="text-xs font-bold text-amber-400 uppercase tracking-wider">Pain Points</h4>
            <ul class="space-y-1.5">
              ${(entity.pain_points || []).map(p => `<li class="text-xs text-slate-300 flex items-start gap-2"><span>⚠️</span><span>${esc(p)}</span></li>`).join('')}
            </ul>
          </div>

          <div class="space-y-2">
            <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Goals with Runefoble</h4>
            <ul class="space-y-1.5">
              ${(entity.goals || []).map(g => `<li class="text-xs text-slate-300 flex items-start gap-2"><span>🎯</span><span>${esc(g)}</span></li>`).join('')}
            </ul>
          </div>
        </div>
      `;
    }

    return `<div class="text-xs text-muted">No details available.</div>`;
  }

  function copyDrawerFilepath() {
    const node = window.visualizer.state.selectedNode;
    if (!node || !node.file_path) return;
    navigator.clipboard.writeText(node.file_path).then(() => {
      const btn = event.currentTarget;
      const original = btn.innerHTML;
      btn.innerHTML = '<span>Copied!</span>';
      setTimeout(() => { btn.innerHTML = original; }, 1500);
    });
  }

  window.visualizer.openDrawer = openDrawer;
  window.visualizer.closeDrawer = closeDrawer;
  window.visualizer.copyDrawerFilepath = copyDrawerFilepath;

  // Global window.app bridge for legacy onclick handlers
  window.app = window.app || {};
  window.app.openDrawer = openDrawer;
  window.app.closeDrawer = closeDrawer;
  window.app.copyDrawerFilepath = copyDrawerFilepath;
  window.app.toggleTheme = () => window.visualizer.toggleTheme();
  window.app.toggleOmnibar = (s) => window.visualizer.toggleOmnibar(s);
  window.app.handleOmnibarSearch = (q) => window.visualizer.handleOmnibarSearch(q);
  window.app.switchTab = (t) => window.visualizer.switchTab(t);
})();
