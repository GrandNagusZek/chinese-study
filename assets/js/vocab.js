(function () {
  var bootEl = document.getElementById("vocab-boot");
  var tbody = document.getElementById("vocab-body");
  if (!bootEl || !tbody) return;

  var boot = JSON.parse(bootEl.textContent);
  var lessons = boot.lessons || {};
  var PAGE = 40;
  var search = document.getElementById("vocab-search");
  var sourceButtons = Array.prototype.slice.call(document.querySelectorAll("[data-source]"));
  var levelButtons = Array.prototype.slice.call(document.querySelectorAll("[data-level]"));
  var levelRow = document.getElementById("hsk-levels");
  var headers = Array.prototype.slice.call(document.querySelectorAll("#vocab-table th button[data-sort]"));
  var empty = document.getElementById("vocab-empty");
  var countEl = document.getElementById("vocab-count");
  var statusEl = document.getElementById("vocab-status");
  var pager = document.getElementById("vocab-pager");
  var pageStatus = document.getElementById("page-status");
  var prevBtn = document.getElementById("page-prev");
  var nextBtn = document.getElementById("page-next");

  var sortKey = "date";
  var sortDir = -1;
  var page = 1;
  var rows = (boot.words || []).map(lessonRow);

  function fold(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function lessonRow(word) {
    var tags = word.tags || [];
    return {
      id: word.id || ((word.hanzi || "") + "|" + (word.pinyin || "")),
      hanzi: word.hanzi || "",
      trad: "",
      pinyin: word.pinyin || "",
      gloss: word.gloss || "",
      example: word.example || "",
      date: word.date || "",
      source: "lesson",
      hsk: 0,
      lesson: word.lesson || "",
      tags: tags,
      search: fold([word.hanzi, word.pinyin, word.gloss, word.example, tags.join(" ")].join(" "))
    };
  }

  function plecoRow(word) {
    var tags = word.tags || [];
    var source = word.kind === "saved" ? "saved" : "hsk";
    return {
      id: word.id || ((word.hanzi || "") + "|" + (word.pinyin || "")),
      hanzi: word.hanzi || "",
      trad: word.traditional || "",
      pinyin: word.pinyin || "",
      gloss: word.gloss || "",
      example: word.example || "",
      date: word.date || "",
      source: source,
      hsk: word.hsk || 0,
      lesson: "",
      tags: tags,
      search: fold([word.hanzi, word.traditional, word.pinyin, word.gloss, word.example, tags.join(" ")].join(" "))
    };
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pressedSet(buttons, attr) {
    var set = {};
    buttons.forEach(function (button) {
      if (button.getAttribute("aria-pressed") === "true") {
        set[button.getAttribute(attr)] = true;
      }
    });
    return set;
  }

  function sourceRank(row) {
    if (row.source === "lesson") return "0" + (row.lesson || "");
    if (row.source === "saved") return "1";
    return "2" + String(row.hsk || 0);
  }

  function matches(row, sources, levels, query) {
    if (!sources[row.source]) return false;
    if (row.source === "hsk" && !levels[String(row.hsk)]) return false;
    if (!query) return true;
    return row.search.indexOf(query) !== -1;
  }

  function sourceCell(row) {
    if (row.source === "lesson") {
      var lesson = lessons[row.lesson];
      var label = lesson ? lesson.title : row.lesson;
      var tags = row.tags.length ? '<span class="row-tags">' + escapeHtml(row.tags.join(" · ")) + "</span>" : "";
      if (lesson) {
        return '<a href="' + escapeHtml(lesson.url) + '">' + escapeHtml(label) + "</a>" + tags;
      }
      return escapeHtml(label) + tags;
    }
    if (row.source === "saved") return "自存";
    return "HSK " + row.hsk;
  }

  function render(list) {
    var pages = Math.max(1, Math.ceil(list.length / PAGE));
    if (page > pages) page = pages;
    var start = (page - 1) * PAGE;
    var slice = list.slice(start, start + PAGE);
    var html = slice.map(function (row) {
      var example = row.example
        ? '<span class="row-example">' + escapeHtml(row.example.length > 160 ? row.example.slice(0, 157) + "…" : row.example) + "</span>"
        : "";
      return (
        "<tr>" +
        '<td class="hanzi">' + escapeHtml(row.hanzi) + "</td>" +
        '<td class="trad">' + escapeHtml(row.trad) + "</td>" +
        '<td class="pinyin">' + escapeHtml(row.pinyin) + "</td>" +
        '<td lang="en">' + escapeHtml(row.gloss) + example + "</td>" +
        '<td class="num">' + escapeHtml(row.date) + "</td>" +
        "<td>" + sourceCell(row) + "</td>" +
        "</tr>"
      );
    }).join("");
    tbody.innerHTML = html;

    var from = list.length ? start + 1 : 0;
    var to = start + slice.length;
    if (countEl) {
      countEl.textContent = list.length + " 条" + (list.length ? " · " + from + "–" + to : "");
    }
    if (empty) empty.hidden = list.length !== 0;
    if (pager) pager.hidden = list.length <= PAGE;
    if (pageStatus) pageStatus.textContent = "第 " + page + " / " + pages + " 页";
    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= pages;

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

  function apply() {
    var sources = pressedSet(sourceButtons, "data-source");
    var levels = pressedSet(levelButtons, "data-level");
    var query = fold(search ? search.value.trim() : "");
    if (levelRow) levelRow.hidden = !sources.hsk;
    var list = rows.filter(function (row) {
      return matches(row, sources, levels, query);
    });
    list.sort(function (a, b) {
      var va;
      var vb;
      if (sortKey === "source") {
        va = sourceRank(a);
        vb = sourceRank(b);
      } else if (sortKey === "pinyin" || sortKey === "gloss") {
        va = fold(a[sortKey]);
        vb = fold(b[sortKey]);
      } else if (sortKey === "trad") {
        va = a.trad || "";
        vb = b.trad || "";
      } else {
        va = a[sortKey] || "";
        vb = b[sortKey] || "";
      }
      var locale = sortKey === "hanzi" || sortKey === "trad" ? "zh-Hans" : "en";
      return String(va).localeCompare(String(vb), locale, { numeric: true, sensitivity: "base" }) * sortDir;
    });
    render(list);
  }

  sourceButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var on = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", on ? "false" : "true");
      page = 1;
      apply();
    });
  });

  levelButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var on = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", on ? "false" : "true");
      page = 1;
      apply();
    });
  });

  headers.forEach(function (button) {
    button.addEventListener("click", function () {
      var key = button.getAttribute("data-sort");
      if (key === sortKey) {
        sortDir = -sortDir;
      } else {
        sortKey = key;
        sortDir = key === "date" ? -1 : 1;
      }
      page = 1;
      apply();
    });
  });

  if (search) {
    search.addEventListener("input", function () {
      page = 1;
      apply();
    });
  }
  if (prevBtn) {
    prevBtn.addEventListener("click", function () {
      if (page > 1) {
        page -= 1;
        apply();
        document.getElementById("vocab-table").scrollIntoView({ block: "nearest" });
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      page += 1;
      apply();
      document.getElementById("vocab-table").scrollIntoView({ block: "nearest" });
    });
  }

  apply();
  if (statusEl) statusEl.textContent = "正在载入 Pleco 词库…";
  fetch(boot.pleco)
    .then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    })
    .then(function (payload) {
      var words = (payload && payload.words) || [];
      words.forEach(function (word) {
        rows.push(plecoRow(word));
      });
      if (statusEl) statusEl.textContent = "";
      apply();
    })
    .catch(function () {
      if (statusEl) statusEl.textContent = "Pleco 词库没有载入。课文生词仍然可以查。";
    });
})();
