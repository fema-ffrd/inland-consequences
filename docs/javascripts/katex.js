(function () {
  function renderKaTeX() {
    if (!window.renderMathInElement) return;

    // Target the main content area for better performance
    const content = document.querySelector(".md-content");
    if (!content) return;

    renderMathInElement(content, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false }
      ],
      throwOnError: false,
      ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"]
    });
  }

  // Initial load
  document.addEventListener("DOMContentLoaded", renderKaTeX);

  // Support Material theme instant loading (navigation without page reload)
  document.addEventListener("DOMContentSwitch", renderKaTeX);

  // Also handle any potential page lifecycle events
  if (typeof document$ !== "undefined") {
    document$.subscribe(renderKaTeX);
  }
})();
