// --- Runefoble Project Content Visualizer: Antigravity (AGY) Agent Launcher Facade ---
(function() {
  window.visualizer = window.visualizer || {};
  const agy = window.visualizer.agy || {};

  window.visualizer.openAgyModal = (p, t) => (window.visualizer.agy?.openAgyModal || agy.openAgyModal)(p, t);
  window.visualizer.closeAgyModal = () => (window.visualizer.agy?.closeAgyModal || agy.closeAgyModal)();
  window.visualizer.launchAgyForEntity = (id) => (window.visualizer.agy?.launchAgyForEntity || agy.launchAgyForEntity)(id);
  window.visualizer.renderTaskDrawerActions = (e) => (window.visualizer.agy?.renderTaskDrawerActions || agy.renderTaskDrawerActions)(e);
  window.visualizer.setAgyPreset = (k) => (window.visualizer.agy?.setAgyPreset || agy.setAgyPreset)(k);
  window.visualizer.updateAgyCommandPreview = () => (window.visualizer.agy?.updateAgyCommandPreview || agy.updateAgyCommandPreview)();
  window.visualizer.copyAgyCommand = () => (window.visualizer.agy?.copyAgyCommand || agy.copyAgyCommand)();
  window.visualizer.launchAgyJob = () => (window.visualizer.agy?.launchAgyJob || agy.launchAgyJob)();
  window.visualizer.terminateAgyJob = () => (window.visualizer.agy?.terminateAgyJob || agy.terminateAgyJob)();
  window.visualizer.clearAgyOutput = () => (window.visualizer.agy?.clearAgyOutput || agy.clearAgyOutput)();
})();
