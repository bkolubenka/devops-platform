(function () {
  function navMarkup(pageType) {
    var isResume = pageType === "resume";
    return [
      '<div class="nav-shell">',
      '  <h1 class="brand">DevOps Platform</h1>',
      '  <div class="nav-links">',
      '    <a href="/#home" class="nav-link" data-section="home">Overview</a>',
      '    <a href="/#portfolio" class="nav-link" data-section="portfolio">Projects</a>',
      '    <a href="/#services" class="nav-link" data-section="services">Services</a>',
      '    <a href="/#incidents" class="nav-link" data-section="incidents">Incidents</a>',
      '    <a href="/#ai" class="nav-link" data-section="ai">Incident Assistant</a>',
      '    <a href="/#observability" class="nav-link" data-section="observability">Observability</a>',
      '    <a href="/resume/" class="nav-link' + (isResume ? ' active' : '') + '">Resume</a>',
      '  </div>',
      '</div>',
    ].join("\n");
  }

  function renderSharedNav(pageType) {
    var navRoot = document.getElementById("shared-nav-root");
    if (!navRoot) {
      return;
    }
    navRoot.innerHTML = navMarkup(pageType);
  }

  window.renderSharedNav = renderSharedNav;
})();
