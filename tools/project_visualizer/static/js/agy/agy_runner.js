// --- Runefoble Project Content Visualizer: AGY Execution & Stream Runner ---
(function() {
  window.visualizer = window.visualizer || {};
  const agy = window.visualizer.agy = window.visualizer.agy || {};

  let activeJobId = null, pollTimer = null, timerInterval = null, jobStartTime = null, currentOffset = 0;

  function clearAgyOutput() {
    const el = document.getElementById('agy-terminal-output');
    if (el) el.textContent = 'Logs cleared.\n';
  }

  function setJobUiState(status, badgeCls, isRunning = false) {
    const chip = document.getElementById('agy-status-chip');
    const launchBtn = document.getElementById('agy-launch-btn');
    const cancelBtn = document.getElementById('agy-cancel-btn');
    if (chip) {
      chip.textContent = status;
      chip.className = `px-2 py-0.5 rounded text-[10px] font-mono font-bold ${badgeCls}`;
    }
    if (launchBtn) launchBtn.disabled = isRunning;
    if (cancelBtn) cancelBtn.classList.toggle('hidden', !isRunning);
  }

  function startTimer() {
    const timerEl = document.getElementById('agy-timer');
    if (!timerEl) return;
    timerEl.classList.remove('hidden');
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      if (!jobStartTime) return;
      const sec = Math.floor((Date.now() - jobStartTime) / 1000);
      timerEl.textContent = `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  function startPolling(jobId) {
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/agy/status?job_id=${encodeURIComponent(jobId)}&offset=${currentOffset}`);
        const data = await res.json();
        if (!data?.job) return;
        const { job, output_chunk, next_offset } = data;
        const outputEl = document.getElementById('agy-terminal-output');

        if (output_chunk && outputEl) {
          outputEl.textContent += output_chunk;
          outputEl.scrollTop = outputEl.scrollHeight;
          currentOffset = next_offset;
        }

        if (job.status === 'running') {
          setJobUiState('RUNNING', 'bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse', true);
        } else if (job.status === 'completed') {
          clearInterval(pollTimer);
          stopTimer();
          setJobUiState('COMPLETED (Exit 0)', 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30', false);
        } else if (job.status === 'failed' || job.status === 'terminated') {
          clearInterval(pollTimer);
          stopTimer();
          const label = job.exit_code !== null ? `Exit ${job.exit_code}` : job.status.toUpperCase();
          setJobUiState(label, 'bg-rose-500/20 text-rose-300 border border-rose-500/30', false);
        }
      } catch (_) {}
    }, 750);
  }

  async function launchAgyJob() {
    const promptInput = document.getElementById('agy-prompt-input');
    const continueCheck = document.getElementById('agy-continue-session');
    const outputEl = document.getElementById('agy-terminal-output');

    if (!promptInput?.value.trim()) return alert('Please specify a prompt for the Antigravity agent.');

    currentOffset = 0;
    if (outputEl) outputEl.textContent = '🚀 Dispatching Antigravity AGY Agent...\n';
    setJobUiState('STARTING', 'bg-amber-500/20 text-amber-300 border border-amber-500/30', true);

    try {
      const res = await fetch('/api/agy/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptInput.value.trim(),
          continue_session: Boolean(continueCheck?.checked),
          target_entity_id: agy.currentTargetEntityId,
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Server error');
      }
      const data = await res.json();
      activeJobId = data.job.job_id;
      jobStartTime = Date.now();
      startTimer();
      startPolling(activeJobId);
    } catch (err) {
      if (outputEl) outputEl.textContent += `\n❌ Launch failed: ${err.message || err}\n`;
      setJobUiState('FAILED', 'bg-rose-500/20 text-rose-300 border border-rose-500/30', false);
    }
  }

  function terminateAgyJob() {
    if (!activeJobId) return;
    fetch('/api/agy/terminate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: activeJobId }),
    }).then(res => res.json()).then(() => {
      const outputEl = document.getElementById('agy-terminal-output');
      if (outputEl) outputEl.textContent += '\n⚠️ Cancellation requested...\n';
    });
  }

  Object.assign(agy, { clearAgyOutput, launchAgyJob, terminateAgyJob, startPolling, startTimer, stopTimer });
  Object.assign(window.visualizer, { clearAgyOutput, launchAgyJob, terminateAgyJob });
})();
