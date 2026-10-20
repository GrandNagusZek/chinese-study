(function () {
  var data = window.STUDY || { vocab: [], lessons: [] };
  var vocab = (data.vocab || []).map(function (word) {
    word.source = "lesson";
    word.hsk = 0;
    word.traditional = word.traditional || "";
    return word;
  });
  var KEY = "zh-study-review-v1";

  var dirSelect = document.getElementById("review-dir");
  var scopeSelect = document.getElementById("review-scope");
  var progress = document.getElementById("review-progress");
  var card = document.getElementById("card-flip");
  var kicker = document.getElementById("card-kicker");
  var prompt = document.getElementById("card-prompt");
  var answer = document.getElementById("card-answer");
  var showBtn = document.getElementById("review-show");
  var noBtn = document.getElementById("review-no");
  var yesBtn = document.getElementById("review-yes");
  var againBtn = document.getElementById("review-again");
  var empty = document.getElementById("review-empty");
  var statsEl = document.getElementById("review-stats");
  var resetBtn = document.getElementById("review-reset");
  var flashcard = document.getElementById("flashcard");

  if (!dirSelect || !card) return;

  var queue = [];
  var index = 0;
  var revealed = false;
  var finished = false;
  var repeated = {};
  var roundSeen = 0;
  var roundKnown = 0;

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return { cards: {} };
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object" || !parsed.cards) return { cards: {} };
      return parsed;
    } catch (e) {
      return { cards: {} };
    }
  }

  function save(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {}
  }

  function cardId(word, dir) {
    return word.hanzi + "::" + dir;
  }

  function shuffle(list) {
    var copy = list.slice();
    for (var i = copy.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = copy[i];
      copy[i] = copy[j];
      copy[j] = tmp;
    }
    return copy;
  }

  function filtered() {
    var scope = scopeSelect.value || "default";
    return vocab.filter(function (word) {
      if (!word || !word.hanzi) return false;
      if (scope === "default") return word.source === "lesson" || word.source === "saved";
      if (scope === "lesson") return word.source === "lesson";
      if (scope === "saved") return word.source === "saved";
      if (scope === "hsk") return word.source === "hsk";
      if (scope.indexOf("hsk:") === 0) {
        return word.source === "hsk" && String(word.hsk) === scope.slice(4);
      }
      if (scope === "all") return true;
      if (scope.indexOf("lesson:") === 0) return word.lesson === scope.slice(7);
      if (scope.indexOf("tag:") === 0) {
        var tag = scope.slice(4);
        return word.source === "lesson" && (word.tags || []).indexOf(tag) !== -1;
      }
      return true;
    });
  }

  function setHidden(node, hidden) {
    if (node) node.hidden = hidden;
  }

  function renderStats() {
    var state = load();
    var dirs = [
      ["hanzi", "看汉字"],
      ["gloss", "看意思"]
    ];
    var parts = dirs.map(function (pair) {
      var seen = 0;
      var known = 0;
      Object.keys(state.cards).forEach(function (id) {
        if (id.slice(-pair[0].length - 2) !== "::" + pair[0]) return;
        var row = state.cards[id];
        seen += row.seen || 0;
        known += row.known || 0;
      });
      return pair[1] + "：认识 " + known + " 次 / 见过 " + seen + " 次";
    });
    statsEl.textContent = parts.join("。") + "。";
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function showDone() {
    finished = true;
    setHidden(flashcard, true);
    setHidden(showBtn, true);
    setHidden(noBtn, true);
    setHidden(yesBtn, true);
    setHidden(againBtn, false);
    progress.textContent = "这一轮完了。认识 " + roundKnown + " / " + roundSeen + "。";
  }

  function renderCard() {
    if (index >= queue.length) {
      showDone();
      return;
    }
    var word = queue[index];
    var dir = dirSelect.value;
    revealed = false;
    finished = false;
    setHidden(flashcard, false);
    setHidden(againBtn, true);
    setHidden(showBtn, false);
    setHidden(noBtn, true);
    setHidden(yesBtn, true);
    setHidden(answer, true);
    answer.innerHTML = "";

    kicker.textContent = dir === "hanzi" ? "说出意思" : "写出汉字";
    prompt.textContent = dir === "hanzi" ? word.hanzi : word.gloss;
    prompt.classList.toggle("is-gloss", dir !== "hanzi");
    prompt.classList.toggle("hanzi", dir === "hanzi");
    progress.textContent = "第 " + (index + 1) + " / " + queue.length;
  }

  function reveal() {
    if (finished || revealed) return;
    var word = queue[index];
    if (!word) return;
    var dir = dirSelect.value;
    revealed = true;
    var tags = (word.tags || []).join(" · ");
    var hanziBlock = '<span class="hanzi">' + escapeHtml(word.hanzi) + "</span>";
    if (word.traditional) {
      hanziBlock += '<span class="trad">' + escapeHtml(word.traditional) + "</span>";
    }
    var pinyinBlock = '<span class="pinyin">' + escapeHtml(word.pinyin) + "</span>";
    var glossBlock = '<span class="gloss" lang="en">' + escapeHtml(word.gloss) + "</span>";
    var exampleBlock = word.example ? '<span class="example">' + escapeHtml(word.example) + "</span>" : "";
    var tagBlock = tags ? '<span class="tags-inline">' + escapeHtml(tags) + "</span>" : "";
    var tradBlock = dir === "hanzi" && word.traditional
      ? '<span class="trad">' + escapeHtml(word.traditional) + "</span>"
      : "";
    answer.innerHTML = [dir === "hanzi" ? glossBlock : hanziBlock, tradBlock, pinyinBlock, exampleBlock, tagBlock].join("");
    setHidden(answer, false);
    setHidden(showBtn, true);
    setHidden(noBtn, false);
    setHidden(yesBtn, false);
  }

  function mark(known) {
    if (!revealed || finished) return;
    var word = queue[index];
    var dir = dirSelect.value;
    var state = load();
    var id = cardId(word, dir);
    var row = state.cards[id] || { seen: 0, known: 0 };
    row.seen += 1;
    if (known) row.known += 1;
    state.cards[id] = row;
    save(state);

    roundSeen += 1;
    if (known) roundKnown += 1;
    if (!known && !repeated[id]) {
      repeated[id] = true;
      queue.push(word);
    }
    index += 1;
    renderStats();
    renderCard();
  }

  function start() {
    queue = shuffle(filtered());
    index = 0;
    repeated = {};
    roundSeen = 0;
    roundKnown = 0;
    finished = false;
    setHidden(empty, queue.length !== 0);
    if (queue.length === 0) {
      setHidden(flashcard, true);
      setHidden(showBtn, true);
      setHidden(noBtn, true);
      setHidden(yesBtn, true);
      setHidden(againBtn, true);
      progress.textContent = "";
      return;
    }
    renderCard();
  }

  card.addEventListener("click", reveal);
  showBtn.addEventListener("click", reveal);
  noBtn.addEventListener("click", function () { mark(false); });
  yesBtn.addEventListener("click", function () { mark(true); });
  againBtn.addEventListener("click", start);
  dirSelect.addEventListener("change", start);
  scopeSelect.addEventListener("change", start);

  document.addEventListener("keydown", function (event) {
    var tag = (event.target && event.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "select" || tag === "textarea") return;
    if (event.key === " ") {
      event.preventDefault();
      reveal();
    } else if (event.key === "1") {
      mark(false);
    } else if (event.key === "2") {
      mark(true);
    }
  });

  resetBtn.addEventListener("click", function () {
    if (!window.confirm("清除这台浏览器里的闪卡进度？")) return;
    try {
      localStorage.removeItem(KEY);
    } catch (e) {}
    renderStats();
  });

  function addPleco(words) {
    (words || []).forEach(function (word) {
      vocab.push({
        hanzi: word.hanzi,
        traditional: word.traditional || "",
        pinyin: word.pinyin || "",
        gloss: word.gloss || "",
        example: word.example || "",
        tags: word.tags || [],
        lesson: "",
        source: word.kind === "saved" ? "saved" : "hsk",
        hsk: word.hsk || 0
      });
    });
  }

  renderStats();
  var plecoUrl = document.getElementById("review-app").getAttribute("data-pleco");
  progress.textContent = "正在载入 Pleco…";
  fetch(plecoUrl)
    .then(function (response) {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    })
    .then(function (payload) {
      addPleco(payload && payload.words);
      start();
    })
    .catch(function () {
      progress.textContent = "Pleco 词库没有载入，先用课文生词。";
      start();
    });
})();
