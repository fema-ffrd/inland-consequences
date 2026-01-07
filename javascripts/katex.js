(function () {
  function renderKaTeX() {
    if (!window.renderMathInElement) return;

    renderMathInElement(document.body, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false }
      ],
      throwOnError: false
    });
  }

  // Initial load
  document.addEventListener("DOMContentLoaded", renderKaTeX);

  // Fallback for any dynamic injections (rare on RTD theme, but harmless)
  window.addEventListener("load", renderKaTeX);
})();
