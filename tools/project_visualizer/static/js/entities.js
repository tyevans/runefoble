// --- Runefoble Project Content Visualizer: PRDs, Personas, and ADRs ---
(function() {
  window.visualizer = window.visualizer || {};

  function renderPRDs(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;

    const prds = d.prds || [];
    const features = d.features || [];

    container.innerHTML = `
      <div class="space-y-6">
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm">
          <h2 class="text-base font-bold text-white">Product Requirements & Speculative Feature Inventory</h2>
          <p class="text-xs text-muted mt-1">Checkable user outcomes, PRD definitions, and multi-tier capability catalog (P0 Launch MVP, P1 Beta, P2 Horizon).</p>
        </div>

        <!-- PRD Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          ${prds.map(p => `
            <div onclick="window.visualizer.openDrawer('${p.id}')" class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm hover:border-cyan-500/50 cursor-pointer transition flex flex-col justify-between group">
              <div>
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-cyan-400">${p.id}</span>
                  <span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px] font-medium">${p.status}</span>
                </div>
                <h3 class="text-sm font-bold text-white mt-2 group-hover:text-cyan-300 transition">${esc(p.title)}</h3>
                <p class="text-xs text-muted mt-2 line-clamp-3">${esc(p.problem_statement || '')}</p>

                <div class="mt-4 space-y-1.5">
                  <span class="text-[10px] font-semibold uppercase tracking-wider text-muted font-mono">Checkable Outcomes (${p.outcomes.length})</span>
                  <ul class="text-[11px] text-muted space-y-1">
                    ${p.outcomes.slice(0, 3).map(o => `<li class="truncate flex items-center gap-1.5"><span class="w-1 h-1 rounded-full bg-cyan-400"></span>${esc(o)}</li>`).join('')}
                  </ul>
                </div>
              </div>

              <div class="mt-5 pt-3 border-t border-subtle flex items-center justify-between text-[11px] font-mono text-muted">
                <span>${p.linked_stories.length} User Stories</span>
                <span class="text-cyan-400 font-semibold group-hover:translate-x-0.5 transition">Details →</span>
              </div>
            </div>
          `).join('')}
        </div>

        <!-- Feature Capability Inventory Table -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm mt-8">
          <div class="flex items-center justify-between pb-4 border-b border-subtle">
            <div>
              <h3 class="text-sm font-bold text-white">Speculative Feature Capability Matrix (${features.length} Features)</h3>
              <p class="text-xs text-muted">Categorized by functional domain and milestone tier.</p>
            </div>
          </div>
          <div class="overflow-x-auto mt-4">
            <table class="w-full text-left text-xs">
              <thead class="bg-[var(--bg-elevated)] text-muted font-mono text-[11px] uppercase border-b border-subtle">
                <tr>
                  <th class="py-2.5 px-3">ID</th>
                  <th class="py-2.5 px-3">Feature Name</th>
                  <th class="py-2.5 px-3">Domain</th>
                  <th class="py-2.5 px-3">Tier</th>
                  <th class="py-2.5 px-3">Governing Systems</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-subtle font-normal">
                ${features.map(f => {
                  const isP0 = f.tier.includes('P0');
                  const tierColor = isP0 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
                  return `
                    <tr class="hover:bg-[var(--bg-elevated)]/50 transition">
                      <td class="py-2 px-3 font-mono font-bold text-indigo-300">${f.id}</td>
                      <td class="py-2 px-3 font-semibold text-white">${esc(f.name)}</td>
                      <td class="py-2 px-3 text-muted">${esc(f.domain)}</td>
                      <td class="py-2 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-mono border ${tierColor}">${f.tier}</span></td>
                      <td class="py-2 px-3 font-mono text-muted text-[11px]">${esc(f.governing_systems.join(', '))}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  function renderPersonas(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;
    const inlineMd = window.visualizer.renderInlineMarkdown || esc;

    const personas = d.personas || [];
    const stories = d.stories || [];

    const filteredStories = stories.filter(s => {
      if (state.filters.persona !== 'all' && !s.persona.toLowerCase().includes(state.filters.persona.toLowerCase())) return false;
      return true;
    });

    container.innerHTML = `
      <div class="space-y-6">
        <!-- Personas Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
          ${personas.map(p => `
            <div onclick="window.visualizer.openDrawer('${p.id}')" class="bg-[var(--bg-card)] border border-subtle rounded-xl p-4 shadow-sm hover:border-indigo-500/50 cursor-pointer transition flex flex-col justify-between group">
              <div>
                <div class="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white shadow-md text-base" style="background-color: ${p.avatar_color}">
                  ${p.name[0]}
                </div>
                <h3 class="text-sm font-bold text-white mt-3 group-hover:text-indigo-400 transition">${esc(p.name)}</h3>
                <p class="text-xs text-muted mt-0.5">${esc(p.role)}</p>
                <div class="mt-3 text-[11px] text-muted italic line-clamp-2">"${inlineMd(p.quote)}"</div>
              </div>
              <div class="mt-4 pt-3 border-t border-subtle flex items-center justify-between text-xs font-mono">
                <span class="text-indigo-400 font-semibold">${p.story_ids.length} Stories</span>
                <span class="text-muted group-hover:text-white transition">Dossier →</span>
              </div>
            </div>
          `).join('')}
        </div>

        <!-- User Stories Catalog -->
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-6 shadow-sm mt-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
            <div>
              <h3 class="text-sm font-bold text-white">Accepted User Stories Catalog (${filteredStories.length} Stories)</h3>
              <p class="text-xs text-muted">Persona-grounded end-to-end acceptance criteria and scenarios.</p>
            </div>

            <!-- Persona Filter -->
            <select onchange="window.visualizer.setFilter('persona', this.value, 'personas')"
                    class="px-3 py-1.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-xs text-white focus:outline-none focus:border-indigo-500 transition">
              <option value="all" ${state.filters.persona === 'all' ? 'selected' : ''}>All Personas</option>
              ${personas.map(p => `<option value="${p.id}" ${state.filters.persona === p.id ? 'selected' : ''}>${p.name}</option>`).join('')}
            </select>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
            ${filteredStories.map(s => `
              <div onclick="window.visualizer.openDrawer('${s.id}')" class="p-4 rounded-xl bg-[var(--bg-elevated)] border border-subtle hover:border-violet-500/50 cursor-pointer transition shadow-sm group">
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-violet-400">${s.id}</span>
                  <span class="text-muted text-[11px]">${esc(s.persona)}</span>
                </div>
                <h4 class="text-xs font-bold text-white mt-1.5 group-hover:text-violet-300 transition leading-snug">${esc(s.title)}</h4>
                <div class="mt-2 text-xs text-muted pl-2 border-l-2 border-violet-500/50 italic line-clamp-2">
                  "As a ${esc(s.as_a)}, I want to ${esc(s.i_want)}..."
                </div>
                <div class="mt-3 flex items-center justify-between text-[11px] font-mono text-muted">
                  <span>${s.acceptance_criteria.length} Criteria</span>
                  <span class="text-violet-400 font-semibold">Inspect Story →</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  function renderADRs(container, state) {
    const d = state.data;
    if (!d) return;
    const esc = window.visualizer.escapeHtml;
    const inlineMd = window.visualizer.renderInlineMarkdown || esc;

    const adrs = d.adrs || [];

    container.innerHTML = `
      <div class="space-y-6">
        <div class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm">
          <h2 class="text-base font-bold text-white">Architectural Decision Records (ADRs)</h2>
          <p class="text-xs text-muted mt-1">Zanzibar authorization, event sourcing, UV monorepo, Lit microfrontends, and Kubernetes-first infrastructure.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          ${adrs.map(adr => `
            <div onclick="window.visualizer.openDrawer('${adr.id}')" class="bg-[var(--bg-card)] border border-subtle rounded-xl p-5 shadow-sm hover:border-amber-500/50 cursor-pointer transition flex flex-col justify-between group">
              <div>
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="font-bold text-amber-400">${adr.id}</span>
                  <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-semibold">${adr.domain}</span>
                </div>
                <h3 class="text-sm font-bold text-white mt-2 group-hover:text-amber-300 transition">${esc(adr.title)}</h3>
                <p class="text-xs text-muted mt-2 line-clamp-3">${inlineMd(adr.context || '')}</p>

                <div class="mt-4 p-2.5 rounded-lg bg-[var(--bg-elevated)] border border-subtle text-[11px] text-muted">
                  <strong class="text-amber-400 uppercase font-mono text-[9px] block">Decision Summary</strong>
                  <span class="line-clamp-2 mt-0.5 text-slate-300 block">${inlineMd(adr.decision || '')}</span>
                </div>
              </div>

              <div class="mt-5 pt-3 border-t border-subtle flex items-center justify-between text-[11px] font-mono text-muted">
                <span>${adr.implementing_tasks.length} Implemented Tasks</span>
                <span class="text-amber-400 font-semibold group-hover:translate-x-0.5 transition">Read ADR →</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  window.visualizer.renderPRDs = renderPRDs;
  window.visualizer.renderPersonas = renderPersonas;
  window.visualizer.renderADRs = renderADRs;
})();
