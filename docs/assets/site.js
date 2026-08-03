(() => {
  const tabButtons = document.querySelectorAll("[data-sample-target]");
  const samplePanels = document.querySelectorAll("[data-sample-panel]");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.sampleTarget;

      tabButtons.forEach((candidate) => {
        const selected = candidate === button;
        candidate.classList.toggle("active", selected);
        candidate.setAttribute("aria-selected", String(selected));
      });

      samplePanels.forEach((panel) => {
        panel.classList.toggle("active", panel.dataset.samplePanel === target);
      });
    });
  });

  const copyButton = document.querySelector("[data-copy-citation]");
  const citation = document.getElementById("citation-text");
  const copyStatus = document.getElementById("copy-status");

  if (copyButton && citation) {
    copyButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(citation.textContent.trim());
        copyStatus.textContent = "Copied";
      } catch (_error) {
        const range = document.createRange();
        range.selectNodeContents(citation);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        copyStatus.textContent = "Selected — press Ctrl/Cmd+C";
      }

      window.setTimeout(() => {
        copyStatus.textContent = "";
      }, 2200);
    });
  }

  const year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();
})();
