// --- Runefoble Project Content Visualizer: Antigravity (AGY) Agent Launcher ---
(function() {
  window.visualizer = window.visualizer || {};

  let activeJobId = null;
  let pollTimer = null;
  let timerInterval = null;
  let jobStartTime = null;
  let currentOffset = 0;
  let currentTargetEntityId = null;

  function openAgyModal(prefilledPrompt = '', targetEntityId = null) {
    const modal = document.getElementById('agy-modal');
    const backdrop = document.getElementById('agy-modal-backdrop');
    const promptInput = document.getElementById('agy-prompt-input');
    const targetBadge = document.getElementById('agy-target-badge');

    if (!modal || !backdrop) return;

    currentTargetEntityId = targetEntityId;
    if (targetBadge) {
      targetBadge.textContent = targetEntityId || 'General Workspace';
    }

    if (promptInput) {
      if (prefilledPrompt) {
        promptInput.value = prefilledPrompt;
      } else if (!promptInput.value.trim()) {
        setAgyPreset('feature_process');
      }
    }

    updateAgyCommandPreview();

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

    navigator.clipboard.writeText(previewEl.textContent.trim()).then(() => {
      if (labelEl) {
        const orig = labelEl.textContent;
        labelEl.textContent = 'Copied!';
        setTimeout(() => { labelEl.textContent = orig; }, 1500);
      }
    });
  }

  function clearAgyOutput() {
    const outputEl = document.getElementById('agy-terminal-output');
    if (outputEl) {
      outputEl.textContent = 'Logs cleared.\n';
    }
  }

  function setAgyPreset(presetKey) {
    const promptInput = document.getElementById('agy-prompt-input');
    if (!promptInput) return;

    const d = window.visualizer.state ? window.visualizer.state.data : null;

    if (presetKey === 'feature_process') {
      promptInput.value = `I want to add this feature: [Describe your feature here]

Please move this feature through the Runefoble end-to-end development process:
1. Product & Stories: If needed, create or update PRDs in docs/project/product/ and User Stories in docs/project/user_stories/.
2. Architecture: Review and cite governing ADRs in docs/project/adrs/accepted/ (or author an ADR if establishing new patterns).
3. Backlog Task: Ensure a scoped task is created in docs/project/backlog/ adhering to INVEST criteria and Definition of Ready (DoR).
4. Blackbox TDD: Implement the feature in its owning bounded context, verifying strictly through public frontdoors (HTTP, WebSockets, or CloudEvents).
5. Invariants: Strictly enforce the <500 lines per file limit with zero exceptions.
6. Verification Gates: Run and pass 'uv run pytest', 'make lint', and 'make health-check'.
7. Documentation & Changelog: Update Diataxis guides in docs/ and log user-facing changes in CHANGELOG.md under [Unreleased].`;
    } else if (presetKey === 'task') {
      if (currentTargetEntityId && d && d.tasks) {
        const task = d.tasks.find(t => t.id === currentTargetEntityId);
        if (task) {
          promptInput.value = buildTaskPrompt(task);
          updateAgyCommandPreview();
          return;
        }
      }
      // If no current entity, pick top refined task or general instruction
      promptInput.value = `Work on top backlog item in docs/project/backlog/refined/.
Follow the Runefoble Definition of Done in AGENTS.md:
1. Blackbox TDD suite with public frontdoor setup.
2. File length limit strictly enforced (<500 lines per file).
3. Verify test suite passes ('uv run pytest').
4. Keep docs, CHANGELOG.md, and registries synchronized.`;
    } else if (presetKey === 'backlog_curator') {
      promptInput.value = `Activate the 'backlog-curator' skill in .agents/skills/backlog-curator/SKILL.md:
1. Review files approaching 500 lines and propose refactoring tasks in docs/project/backlog/proposed/ if needed.
2. Inspect docs/project/backlog/ROADMAP.md Milestone 2 and ensure foundational enablers are prioritized.
3. Check the ready buffer in docs/project/backlog/refined/. Keep buffer to ~10 items.
4. Synchronize docs/project/backlog/PRIORITY.md.`;
    } else if (presetKey === 'health_check') {
      promptInput.value = `Run codebase health check via 'python3 scripts/health_check.py'.
Verify all files satisfy the <500 lines invariant and inspect any backlog items violating the Definition of Ready.
Decompose any oversized files into focused modules.`;
    } else if (presetKey === 'test_suite') {
      promptInput.value = `Execute the complete Runefoble test suite:
1. 'uv run pytest'
2. 'make test-entrypoints'
3. 'make helm-lint'
Diagnose and repair any failing tests or regressions using blackbox public entrypoints.`;
    }

    updateAgyCommandPreview();
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

  function launchAgyForEntity(entityId) {
    const d = window.visualizer.state ? window.visualizer.state.data : null;
    let prefilled = '';

    if (d && d.tasks) {
      const task = d.tasks.find(t => t.id === entityId);
      if (task) {
        prefilled = buildTaskPrompt(task);
      }
    }

    openAgyModal(prefilled, entityId);
  }

  function launchAgyJob() {
    const promptInput = document.getElementById('agy-prompt-input');
    const continueCheck = document.getElementById('agy-continue-session');
    const launchBtn = document.getElementById('agy-launch-btn');
    const cancelBtn = document.getElementById('agy-cancel-btn');
    const statusChip = document.getElementById('agy-status-chip');
    const outputEl = document.getElementById('agy-terminal-output');
    const timerEl = document.getElementById('agy-timer');

    if (!promptInput || !promptInput.value.trim()) {
      alert('Please specify a prompt for the Antigravity agent.');
      return;
    }

    const prompt = promptInput.value.trim();
    const continueSession = continueCheck ? continueCheck.checked : false;

    // Reset status & output
    currentOffset = 0;
    if (outputEl) outputEl.textContent = '🚀 Dispatching Antigravity AGY Agent...\n';
    if (statusChip) {
      statusChip.textContent = 'STARTING';
      statusChip.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30';
    }
    if (launchBtn) launchBtn.disabled = true;
    if (cancelBtn) cancelBtn.classList.remove('hidden');

    fetch('/api/agy/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        continue_session: continueSession,
        target_entity_id: currentTargetEntityId,
      }),
    })
    .then(res => {
      if (!res.ok) return res.json().then(err => Promise.reject(err.error || 'Server error'));
      return res.json();
    })
    .then(data => {
      activeJobId = data.job.job_id;
      jobStartTime = Date.now();
      startTimer();
      startPolling(activeJobId);
    })
    .catch(err => {
      if (outputEl) outputEl.textContent += `\n❌ Launch failed: ${err}\n`;
      if (statusChip) {
        statusChip.textContent = 'FAILED';
        statusChip.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30';
      }
      if (launchBtn) launchBtn.disabled = false;
      if (cancelBtn) cancelBtn.classList.add('hidden');
    });
  }

  function startTimer() {
    const timerEl = document.getElementById('agy-timer');
    if (!timerEl) return;
    timerEl.classList.remove('hidden');
    clearInterval(timerInterval);

    timerInterval = setInterval(() => {
      if (!jobStartTime) return;
      const elapsedSec = Math.floor((Date.now() - jobStartTime) / 1000);
      const m = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
      const s = String(elapsedSec % 60).padStart(2, '0');
      timerEl.textContent = `${m}:${s}`;
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  function startPolling(jobId) {
    clearInterval(pollTimer);
    pollTimer = setInterval(() => {
      fetch(`/api/agy/status?job_id=${encodeURIComponent(jobId)}&offset=${currentOffset}`)
      .then(res => res.json())
      .then(data => {
        if (!data || !data.job) return;

        const job = data.job;
        const outputEl = document.getElementById('agy-terminal-output');
        const statusChip = document.getElementById('agy-status-chip');
        const launchBtn = document.getElementById('agy-launch-btn');
        const cancelBtn = document.getElementById('agy-cancel-btn');

        if (data.output_chunk && outputEl) {
          outputEl.textContent += data.output_chunk;
          outputEl.scrollTop = outputEl.scrollHeight;
          currentOffset = data.next_offset;
        }

        if (job.status === 'running') {
          if (statusChip) {
            statusChip.textContent = 'RUNNING';
            statusChip.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse';
          }
        } else if (job.status === 'completed') {
          clearInterval(pollTimer);
          stopTimer();
          if (statusChip) {
            statusChip.textContent = 'COMPLETED (Exit 0)';
            statusChip.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
          }
          if (launchBtn) launchBtn.disabled = false;
          if (cancelBtn) cancelBtn.classList.add('hidden');
        } else if (job.status === 'failed' || job.status === 'terminated') {
          clearInterval(pollTimer);
          stopTimer();
          const exitLabel = job.exit_code !== null ? `Exit ${job.exit_code}` : job.status.toUpperCase();
          if (statusChip) {
            statusChip.textContent = exitLabel;
            statusChip.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30';
          }
          if (launchBtn) launchBtn.disabled = false;
          if (cancelBtn) cancelBtn.classList.add('hidden');
        }
      })
      .catch(err => {
        // Soft error during polling
      });
    }, 750);
  }

  function terminateAgyJob() {
    if (!activeJobId) return;

    fetch('/api/agy/terminate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: activeJobId }),
    })
    .then(res => res.json())
    .then(data => {
      const outputEl = document.getElementById('agy-terminal-output');
      if (outputEl) outputEl.textContent += '\n⚠️ Cancellation requested...\n';
    });
  }

  // Bind live listeners on DOM load
  document.addEventListener('DOMContentLoaded', () => {
    const promptInput = document.getElementById('agy-prompt-input');
    const continueCheck = document.getElementById('agy-continue-session');

    if (promptInput) {
      promptInput.addEventListener('input', updateAgyCommandPreview);
    }
    if (continueCheck) {
      continueCheck.addEventListener('change', updateAgyCommandPreview);
    }
  });

  function renderTaskDrawerActions(entity) {
    const esc = window.visualizer.escapeHtml || (s => s);
    return `
      <button onclick="window.visualizer.launchAgyForEntity('${esc(entity.id)}')" class="ml-auto px-2.5 py-1 rounded bg-gradient-to-r from-amber-500/20 to-indigo-500/20 hover:from-amber-500/30 hover:to-indigo-500/30 text-amber-300 border border-amber-500/30 hover:border-amber-400 text-xs font-medium flex items-center gap-1.5 transition shadow-sm" title="Launch bespoke agy prompt for ${esc(entity.id)}">
        <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        <span>Launch AGY</span>
      </button>
    `;
  }

  window.visualizer.renderTaskDrawerActions = renderTaskDrawerActions;
  window.visualizer.openAgyModal = openAgyModal;
  window.visualizer.closeAgyModal = closeAgyModal;
  window.visualizer.updateAgyCommandPreview = updateAgyCommandPreview;
  window.visualizer.copyAgyCommand = copyAgyCommand;
  window.visualizer.clearAgyOutput = clearAgyOutput;
  window.visualizer.setAgyPreset = setAgyPreset;
  window.visualizer.launchAgyForEntity = launchAgyForEntity;
  window.visualizer.launchAgyJob = launchAgyJob;
  window.visualizer.terminateAgyJob = terminateAgyJob;
})();
