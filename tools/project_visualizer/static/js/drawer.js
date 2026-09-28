// --- Runefoble Project Content Visualizer: Detail Drawer & Markdown Viewer ---
(function() {
  window.visualizer = window.visualizer || {};
  const d = window.visualizer.drawer || {};

  function openDrawer(id, animate = true) {
    return (window.visualizer.drawer?.openDrawer || d.openDrawer)(id, animate);
  }

  function closeDrawer() {
    return (window.visualizer.drawer?.closeDrawer || d.closeDrawer)();
  }

  function copyDrawerFilepath() {
    return (window.visualizer.drawer?.copyDrawerFilepath || d.copyDrawerFilepath)();
  }

  function renderEntityBody(entity, type) {
    return (window.visualizer.drawer?.renderEntityBody || d.renderEntityBody)(entity, type);
  }

  window.visualizer.openDrawer = openDrawer;
  window.visualizer.closeDrawer = closeDrawer;
  window.visualizer.copyDrawerFilepath = copyDrawerFilepath;
  window.visualizer.renderEntityBody = renderEntityBody;

  // Global window.app bridge for legacy onclick handlers
  window.app = window.app || {};
  window.app.openDrawer = openDrawer;
  window.app.closeDrawer = closeDrawer;
  window.app.copyDrawerFilepath = copyDrawerFilepath;
  window.app.toggleTheme = () => window.visualizer.toggleTheme?.();
  window.app.toggleOmnibar = (s) => window.visualizer.toggleOmnibar?.(s);
  window.app.handleOmnibarSearch = (q) => window.visualizer.handleOmnibarSearch?.(q);
  window.app.switchTab = (t) => window.visualizer.switchTab?.(t);
})();
