(function () {
  var key = "zh-study-theme";
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");

  function current() {
    var set = root.getAttribute("data-theme");
    if (set === "light" || set === "dark") return set;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  if (!btn) return;

  btn.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(key, next);
    } catch (e) {}
    root.setAttribute("data-theme", next);
    btn.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
  });

  btn.setAttribute("aria-pressed", current() === "dark" ? "true" : "false");
})();
