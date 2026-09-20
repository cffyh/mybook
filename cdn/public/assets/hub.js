(function () {
  const root = document.getElementById("spaces");

  fetch("/spaces.json")
    .then((r) => r.json())
    .then((data) => {
      root.innerHTML = (data.spaces || [])
        .map(
          (s) =>
            `<a class="space" href="${s.href}">` +
            `<div class="sub">${escapeHtml(s.subtitle || "SPACE")}</div>` +
            `<h2>${escapeHtml(s.title)}</h2>` +
            `<p>${escapeHtml(s.blurb || "")}</p>` +
            `</a>`,
        )
        .join("");
    })
    .catch(() => {
      root.textContent = "空间列表载入失败。";
    });

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
