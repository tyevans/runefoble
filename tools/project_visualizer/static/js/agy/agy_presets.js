// --- Runefoble Project Content Visualizer: AGY Presets & Command Builder ---
(function() {
  window.visualizer = window.visualizer || {};
  const agy = window.visualizer.agy = window.visualizer.agy || {};

  function updateAgyCommandPreview() {
    const promptInput = document.getElementById('agy-prompt-input');
    const continueCheck = document.getElementById('agy-continue-session');
    const previewEl = document.getElementById('agy-command-preview');

    if (!previewEl || !promptInput) return;

    const rawPrompt = promptInput.value || '';
    const isContinue = continueCheck && continueCheck.checked;
    const escaped = rawPrompt.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    const contFlag = isContinue ? '-c ' : '';

    previewEl.textContent = `agy --dangerously-skip-permissions ${contFlag}-p "${escaped || '...'}"`;
  }

  function copyAgyCommand() {
    const previewEl = document.getElementById('agy-command-preview');
    const labelEl = document.getElementById('agy-copy-label');
    if (!previewEl) return;

    const nav = window.navigator || (typeof navigator !== 'undefined' ? navigator : null);
    if (!nav?.clipboard?.writeText) return;

    nav.clipboard.writeText(previewEl.textContent.trim()).then(() => {
      if (labelEl) {
        const orig = labelEl.textContent;
        labelEl.textContent = 'Copied!';
        setTimeout(() => { labelEl.textContent = orig; }, 1500);
      }
    });
  }

  function buildTaskPrompt(task) {
    const adrs = (task.governing_adrs && task.governing_adrs.length > 0)
      ? task.governing_adrs.join(', ')
      : 'None explicitly listed';

    return `Work on ${task.id}: ${task.title}
Specification File: ${task.file_path || 'docs/project/backlog/'}
Target Bounded Context: ${task.target_bc || 'N/A'}
Governing ADRs: ${adrs}

Follow the Runefoble Definition of Done in AGENTS.md:
1. Blackbox TDD: verify feature strictly through public frontdoors (HTTP, WebSockets, or CloudEvents).
2. Maintain file length invariant (<500 lines per file).
3. Verify all tests pass ('uv run pytest').
4. Synchronize Diataxis docs, docs/marketing.md, and CHANGELOG.md under [Unreleased].`;
  }

  function setAgyPreset(presetKey) {
    const promptInput = document.getElementById('agy-prompt-input');
    if (!promptInput) return;

    const d = window.visualizer.state ? window.visualizer.state.data : null;
    const targetId = agy.currentTargetEntityId;

    if (presetKey === 'feature_process') {
      promptInput.value = `I want to add this feature: [Describe your feature here]\n\nPlease move this feature through the Runefoble end-to-end development process:\n1. Product & Stories: If needed, create or update PRDs in docs/project/product/ and User Stories in docs/project/user_stories/.\n2. Architecture: Review and cite governing ADRs in docs/project/adrs/accepted/ (or author an ADR if establishing new patterns).\n3. Backlog Task: Ensure a scoped task is created in docs/project/backlog/ adhering to INVEST criteria and Definition of Ready (DoR).\n4. Blackbox TDD: Implement the feature in its owning bounded context, verifying strictly through public frontdoors (HTTP, WebSockets, or CloudEvents).\n5. Invariants: Strictly enforce the <500 lines per file limit with zero exceptions.\n6. Verification Gates: Run and pass 'uv run pytest', 'make lint', and 'make health-check'.\n7. Documentation & Changelog: Update Diataxis guides in docs/ and log user-facing changes in CHANGELOG.md under [Unreleased].`;
    } else if (presetKey === 'task') {
      if (targetId && d && d.tasks) {
        const task = d.tasks.find(t => t.id === targetId);
        if (task) {
          promptInput.value = buildTaskPrompt(task);
          updateAgyCommandPreview();
          return;
        }
      }
      promptInput.value = `Work on top backlog item in docs/project/backlog/refined/.\nFollow the Runefoble Definition of Done in AGENTS.md:\n1. Blackbox TDD suite with public frontdoor setup.\n2. File length limit strictly enforced (<500 lines per file).\n3. Verify test suite passes ('uv run pytest').\n4. Keep docs, CHANGELOG.md, and registries synchronized.`;
    } else if (presetKey === 'backlog_curator') {
      promptInput.value = `Activate the 'backlog-curator' skill in .agents/skills/backlog-curator/SKILL.md:\n1. Review files approaching 500 lines and propose refactoring tasks in docs/project/backlog/proposed/ if needed.\n2. Inspect docs/project/backlog/ROADMAP.md Milestone 2 and ensure foundational enablers are prioritized.\n3. Check the ready buffer in docs/project/backlog/refined/. Keep buffer to ~10 items.\n4. Synchronize docs/project/backlog/PRIORITY.md.`;
    } else if (presetKey === 'health_check') {
      promptInput.value = `Run codebase health check via 'python3 scripts/health_check.py'.\nVerify all files satisfy the <500 lines invariant and inspect any backlog items violating the Definition of Ready.\nDecompose any oversized files into focused modules.`;
    } else if (presetKey === 'test_suite') {
      promptInput.value = `Execute the complete Runefoble test suite:\n1. 'uv run pytest'\n2. 'make test-entrypoints'\n3. 'make helm-lint'\nDiagnose and repair any failing tests or regressions using blackbox public entrypoints.`;
    }

    updateAgyCommandPreview();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const promptInput = document.getElementById('agy-prompt-input');
    const continueCheck = document.getElementById('agy-continue-session');
    if (promptInput) promptInput.addEventListener('input', updateAgyCommandPreview);
    if (continueCheck) continueCheck.addEventListener('change', updateAgyCommandPreview);
  });

  Object.assign(agy, { updateAgyCommandPreview, copyAgyCommand, buildTaskPrompt, setAgyPreset });
  Object.assign(window.visualizer, { updateAgyCommandPreview, copyAgyCommand, setAgyPreset });
})();
