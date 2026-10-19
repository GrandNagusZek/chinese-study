(function () {
  var table = document.getElementById("vocab-table");
  if (!table) return;

  var tbody = table.querySelector("tbody");
  var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
  var search = document.getElementById("vocab-search");
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".tag-filters [data-tag]"));
  var headers = Array.prototype.slice.call(table.querySelectorAll("th button[data-sort]"));
  var empty = document.getElementById("vocab-empty");
  var count = document.getElementById("vocab-count");
  var activeTag = "all";
  var sortKey = "date";
  var sortDir = -1;

  function fold(value) {
    return (value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function apply() {
    var query = fold(search ? search.value.trim() : "");
    var visible = rows.filter(function (row) {
      var tags = (row.getAttribute("data-tags") || "").split("|");
      if (activeTag !== "all" && tags.indexOf(activeTag) === -1) return false;
      if (!query) return true;
      return fold(row.getAttribute("data-search") || "").indexOf(query) !== -1;
    });

    visible.sort(function (a, b) {
      var va = a.getAttribute("data-" + sortKey) || "";
      var vb = b.getAttribute("data-" + sortKey) || "";
      if (sortKey === "pinyin") {
        va = fold(va);
        vb = fold(vb);
      }
      var locale = sortKey === "hanzi" ? "zh-Hans" : "en";
      return va.localeCompare(vb, locale, { numeric: true, sensitivity: "base" }) * sortDir;
    });

    rows.forEach(function (row) {
      row.hidden = true;
    });
    visible.forEach(function (row) {
      row.hidden = false;
      tbody.appendChild(row);
    });

    if (empty) empty.hidden = visible.length !== 0;
    if (count) count.textContent = visible.length + " / " + rows.length;

    headers.forEach(function (button) {
      var th = button.parentNode;
      var key = button.getAttribute("data-sort");
      if (key === sortKey) {
        th.setAttribute("aria-sort", sortDir < 0 ? "descending" : "ascending");
      } else {
        th.removeAttribute("aria-sort");
      }
    });
  }

  headers.forEach(function (button) {
    button.addEventListener("click", function () {
      var key = button.getAttribute("data-sort");
      if (key === sortKey) {
        sortDir = -sortDir;
      } else {
        sortKey = key;
        sortDir = key === "date" ? -1 : 1;
      }
      apply();
    });
  });

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      activeTag = button.getAttribute("data-tag");
      buttons.forEach(function (other) {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      apply();
    });
  });

  if (search) search.addEventListener("input", apply);
  apply();
})();
