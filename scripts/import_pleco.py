#!/usr/bin/env python3
"""Import a Pleco 2.0 flashcard XML export into _data/pleco.json.

The hand-curated lesson list in _data/vocab.yml is left alone. Every reading
of a headword already in that file is skipped. Within the export, the same
simplified headword with a different reading is kept; only an exact
headword-plus-reading repeat is collapsed. Re-running replaces _data/pleco.json.

    python3 scripts/import_pleco.py path/to/export.xml
    python3 scripts/import_pleco.py --self-test

Do not commit the raw XML. Commit the generated JSON.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "_data" / "pleco.json"
DEFAULT_VOCAB = ROOT / "_data" / "vocab.yml"

# Longest finals first so "iang" wins over "ia" and "ang" wins over "a".
_FINAL = (
    "uang|iang|iong|ueng|u:an|uan|van|"
    "u:e|üe|ve|ue|"
    "iao|ian|uai|ing|ang|eng|ong|"
    "u:n|ün|vn|"
    "ai|ei|ao|ou|an|en|ia|ie|iu|in|ua|uo|ui|un|"
    "er|a|o|e|i|u:|ü|v|u|r"
)
# zh/ch/sh are tried before the single-letter class so "zh" is not read as "z".
_SYLLABLE = re.compile(
    rf"(?P<syl>(?:zh|ch|sh|[bpmfdtnlgkhjqxzcsryw])?(?:{_FINAL}))(?P<tone>[1-5])",
    re.IGNORECASE,
)

_TONE = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
}

_LABEL = re.compile(
    r"^(?:"
    r"measure word|common phrase|bound form|polite expression|"
    r"noun|verb|adjective|adverb|pronoun|preposition|conjunction|interjection|"
    r"number|numeral|auxiliary|idiom|affix|particle|prefix|suffix|classifier|"
    r"morpheme|onomatopoeia|determiner|"
    r"literary|colloquial|dialect|dated|formal|informal|figurative|vulgar|"
    r"archaic|abbreviation|transliteration|honorific|humble|written|spoken|"
    r"\d+|\(-//-\)"
    r")\b[\s:,;-]*",
    re.IGNORECASE,
)
_DOMAIN = re.compile(
    r"^(?:mathematics|physics|chemistry|botany|zoology|medicine|computing|"
    r"finance|sports|music|printing|law|military)\s+(?=\S)",
    re.IGNORECASE,
)

_TONE_MARK = re.compile(
    r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛŃŇǸ]"
)
# Plain finals for "is this already tone-marked pinyin?" — no tone digits, no bare r.
_PLAIN_FINAL = (
    "uang|iang|iong|ueng|uan|"
    "iao|ian|uai|ing|ang|eng|ong|"
    "ai|ei|ao|ou|an|en|ia|ie|iu|in|ua|uo|ui|un|ve|ue|vn|"
    "er|a|o|e|i|u|v"
)
_PLAIN_SYLLABLE = re.compile(
    rf"(?:zh|ch|sh|[bpmfdtnlgkhjqxzcsryw])?(?:{_PLAIN_FINAL})"
)
_TONE_FOLD = str.maketrans(
    {
        "ā": "a", "á": "a", "ǎ": "a", "à": "a",
        "ē": "e", "é": "e", "ě": "e", "è": "e",
        "ī": "i", "í": "i", "ǐ": "i", "ì": "i",
        "ō": "o", "ó": "o", "ǒ": "o", "ò": "o",
        "ū": "u", "ú": "u", "ǔ": "u", "ù": "u",
        "ǖ": "v", "ǘ": "v", "ǚ": "v", "ǜ": "v", "ü": "v",
        "ń": "n", "ň": "n", "ǹ": "n", "ḿ": "m",
        "Ā": "a", "Á": "a", "Ǎ": "a", "À": "a",
        "Ē": "e", "É": "e", "Ě": "e", "È": "e",
        "Ī": "i", "Í": "i", "Ǐ": "i", "Ì": "i",
        "Ō": "o", "Ó": "o", "Ǒ": "o", "Ò": "o",
        "Ū": "u", "Ú": "u", "Ǔ": "u", "Ù": "u",
        "Ǖ": "v", "Ǘ": "v", "Ǚ": "v", "Ǜ": "v",
        "Ń": "n", "Ň": "n", "Ǹ": "n",
    }
)
# Single toneless syllables that are also ordinary English words.
_ENGLISH_SYLLABLE = {
    "a", "an", "go", "he", "she", "me", "you", "in", "can", "long", "or", "ha",
}
_POS_WORD = re.compile(
    r"\b(?:measure word|common phrase|bound form|polite expression|"
    r"noun|verb|adjective|adverb|pronoun|preposition|conjunction|interjection|"
    r"auxiliary|idiom|affix|particle|prefix|suffix|classifier|"
    r"morpheme|onomatopoeia|determiner)\b",
    re.IGNORECASE,
)


def _tone_index(syllable: str) -> int:
    if "a" in syllable:
        return syllable.index("a")
    if "e" in syllable:
        return syllable.index("e")
    ou = syllable.find("ou")
    if ou != -1:
        return ou
    idx = -1
    for i, ch in enumerate(syllable):
        if ch in "iouü":
            idx = i
    return idx


def _apply_tone(raw: str, tone: int) -> str:
    capital = raw[:1].isupper()
    syllable = raw.lower().replace("u:", "ü").replace("v", "ü")
    if tone != 5:
        index = _tone_index(syllable)
        if index >= 0:
            vowel = syllable[index]
            marked = _TONE.get(vowel)
            if marked:
                syllable = syllable[:index] + marked[tone - 1] + syllable[index + 1 :]
    if syllable[:1] in "jqxy":
        syllable = syllable.replace("ü", "u")
    if capital and syllable:
        syllable = syllable[0].upper() + syllable[1:]
    return syllable


_NG_TONE = {1: "n̄g", 2: "ńg", 3: "ňg", 4: "ǹg", 5: "ng"}


def _convert_group(group: str) -> tuple[str, str | None]:
    nasal = re.fullmatch(r"(ng|m|hm|hng)([1-5])", group, re.IGNORECASE)
    if nasal:
        tone = int(nasal.group(2))
        base = nasal.group(1).lower()
        if base == "ng":
            return _NG_TONE[tone], None
        if base == "m":
            marked = {1: "m̄", 2: "ḿ", 3: "m̌", 4: "m̀", 5: "m"}[tone]
            return marked, None
        return base if tone == 5 else base, None
    pieces: list[str] = []
    pos = 0
    while pos < len(group):
        match = _SYLLABLE.match(group, pos)
        if not match:
            return group, group[pos:]
        pieces.append(_apply_tone(match.group("syl"), int(match.group("tone"))))
        pos = match.end()
    merged: list[str] = []
    for piece in pieces:
        if piece == "r" and merged:
            merged[-1] += "r"
        else:
            merged.append(piece)
    return "".join(merged), None


def tone_numbers_to_marks(pron: str) -> tuple[str, list[str]]:
    """Convert Pleco numeric pinyin to tone marks.

    Spaces stay spaces, hyphens stay hyphens, and // (separable) becomes ·.
    A trailing neutral 'r5' is erhua and sticks to the previous syllable.
    """
    problems: list[str] = []
    if not pron or not pron.strip():
        return "", problems
    parts = re.split(r"(\s+|//+|-+|'|’|…+|\.\.\.+)", pron.strip())
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.isspace():
            out.append(" ")
        elif part.startswith("//"):
            out.append("·")
        elif part.startswith("-"):
            out.append("-")
        elif part in ("'", "’"):
            out.append("'")
        elif part.startswith("…") or part.startswith("..."):
            out.append("…")
        else:
            cleaned = part.strip("….,;:!?，。、·")
            if not cleaned:
                continue
            converted, problem = _convert_group(cleaned)
            if problem:
                problems.append(pron)
            out.append(converted)
    text = "".join(out)
    text = re.sub(r"\s+", " ", text).strip()
    return text, problems


def _clean_defn(defn: str) -> str:
    text = defn.replace("\r", "\n")
    text = re.sub(r"[\uE000-\uF8FF]+", " ", text)
    text = re.sub(r"See\s+\d+\s+\S+(?:\s+\S+){0,3}", " ", text)
    text = re.sub(r"VARIANT OF\s+\d+\s+\S+(?:\s+\S+){0,4}", " ", text, flags=re.I)
    text = text.replace("&apos;", "'").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_labels(text: str) -> str:
    previous = None
    while text and text != previous:
        previous = text
        nxt = _LABEL.sub("", text).strip()
        if nxt == text:
            nxt = _DOMAIN.sub("", text).strip()
        # A lone label is the meaning ("dialect", "number"), not a prefix.
        if not nxt:
            break
        text = nxt
    return text


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _syllable_count(token: str) -> int:
    """How many plain pinyin syllables `token` splits into, or 0 if it doesn't."""
    bare = token.strip(".,;:!?，。！？…\"'“”()（）[]【】—-·")
    bare = re.sub(r"\d+$", "", bare)
    if not bare or bare in {"'", "’"}:
        return 0
    plain = bare.translate(_TONE_FOLD).replace("u:", "v").replace("ü", "v").replace("'", "")
    if not plain or not re.fullmatch(r"[A-Za-z]+", plain):
        return 0
    lower = plain.lower()
    pos = 0
    count = 0
    while pos < len(lower):
        match = _PLAIN_SYLLABLE.match(lower, pos)
        if not match or match.start() != pos:
            if lower[pos] == "r" and count and _TONE_MARK.search(bare):
                pos += 1
                continue
            return 0
        pos = match.end()
        count += 1
    return count


def _token_is_pinyin(token: str, nxt: str | None, already: bool) -> bool:
    if already and re.fullmatch(r"\d+[.,]?", token):
        return True
    count = _syllable_count(token)
    if count == 0:
        return False
    bare = token.strip(".,;:!?，。！？…\"'“”()（）[]")
    # Several syllables in one token ("chībude", "Zhōngguóhuà") carry a tone
    # mark. Capitalized English like "Chinese" or "Peking" does not.
    if count >= 2:
        return bool(_TONE_MARK.search(bare))
    if _TONE_MARK.search(bare):
        return True
    # A lone toneless syllable is pinyin inside a reading, except words that
    # usually start the English ("a tiger", "in addition").
    if bare.lower() in _ENGLISH_SYLLABLE:
        return bool(nxt) and bool(_TONE_MARK.search(nxt))
    if already:
        return True
    return bool(nxt) and _syllable_count(nxt) > 0 and (
        _TONE_MARK.search(nxt) or _syllable_count(nxt) >= 2 or nxt.strip(".,;:!?")[:1].islower()
    )


def _trim_english(english: str) -> str:
    english = english.strip()
    cut = re.search(r"[\u4e00-\u9fff]|\[", english)
    if cut:
        english = english[: cut.start()]
    pos = _POS_WORD.search(english)
    if pos and pos.start() > 0:
        english = english[: pos.start()]
    sense = re.search(r"\s+\d{1,2}\s+(?=[A-Za-z[])", english)
    if sense and sense.start() > 0:
        english = english[: sense.start()]
    english = re.sub(r"\s+", " ", english).strip()
    period = re.search(r"[.?!]", english)
    if period and period.start() > 0:
        english = english[: period.end()]
    english = re.sub(r"\s+\d+\s*$", "", english).strip(" ;,-")
    if len(re.sub(r"[^A-Za-z]", "", english)) < 2:
        return ""
    return english


def _example_at(text: str, start: int):
    """Parse one dictionary example that begins at a Chinese run."""
    n = len(text)
    j = start
    while j < n and j - start < 80:
        ch = text[j]
        if _is_cjk(ch) or ch in "，、；：。！？…—·《》「」『』":
            j += 1
            continue
        if ch.isdigit() or ch in "（）()\"'“”":
            j += 1
            continue
        if ch == " " and j + 1 < n and (text[j + 1].isdigit() or text[j + 1] in "（）()"):
            j += 1
            continue
        break
    while j > start and text[j - 1] == " ":
        j -= 1
    hanzi = text[start:j].strip(" ，、；：\"'“”")
    if not hanzi or not re.search(r"[\u4e00-\u9fff]", hanzi):
        return None
    k = j
    while k < n and text[k].isspace():
        k += 1
    if k >= n or not (text[k].isascii() and text[k].isalpha()) and not _TONE_MARK.search(text[k]):
        return None
    rest = text[k : k + 360]
    tokens = rest.split()
    if not tokens:
        return None
    pinyin: list[str] = []
    index = 0
    while index < len(tokens) and len(pinyin) < 18:
        nxt = tokens[index + 1] if index + 1 < len(tokens) else None
        if _token_is_pinyin(tokens[index], nxt, bool(pinyin)):
            pinyin.append(tokens[index].strip("，、；：\"'“”"))
            index += 1
            continue
        break
    if not pinyin or not any(_TONE_MARK.search(tok) or _syllable_count(tok) >= 2 for tok in pinyin):
        return None
    english_raw = " ".join(tokens[index:])
    english = _trim_english(english_raw)
    if not english:
        return None
    kept = english
    pin_len = 0
    seen = 0
    while seen < index and pin_len < len(rest):
        if rest[pin_len].isspace():
            pin_len += 1
            continue
        while pin_len < len(rest) and not rest[pin_len].isspace():
            pin_len += 1
        seen += 1
    end = k + pin_len
    located = text.find(kept, end, end + len(kept) + 30)
    if located >= 0:
        end = located + len(kept)
    tail = text[end : end + 180]
    alternative = re.match(
        r"\s*(?:—|–|-|or)\s+[A-Z][^。\u4e00-\u9fff]{0,140}?[.?!]",
        tail,
    )
    if alternative:
        end = min(n, end + alternative.end())
    pinyin_text = " ".join(tok.strip(".,;:!?") for tok in pinyin if tok.strip(".,;:!?"))
    example = f"{hanzi} {pinyin_text} {kept}"
    if len(example) > 220:
        example = example[:217].rstrip() + "…"
    return start, end, example


def _first_example(text: str):
    i = 0
    n = len(text)
    while i < n:
        if not _is_cjk(text[i]):
            i += 1
            continue
        if i > 0 and (_is_cjk(text[i - 1]) or text[i - 1].isdigit()):
            i += 1
            continue
        found = _example_at(text, i)
        if found:
            return found
        while i < n and (_is_cjk(text[i]) or text[i] in "，、；：。！？…—·"):
            i += 1
    return None


def _remove_examples(text: str) -> str:
    for _ in range(120):
        found = _first_example(text)
        if not found:
            return text
        start, end, _example = found
        if end <= start:
            return text
        text = text[:start] + " " + text[end:]
    return text


def short_gloss(defn: str) -> str:
    text = _clean_defn(defn)
    text = _remove_examples(text)
    text = re.sub(
        r"\((?:[^)]*[\u4e00-\u9fff][^)]*|opp\.[^)]*|see[^)]*|cf\.[^)]*)\)",
        " ",
        text,
        flags=re.I,
    )
    # Part-of-speech labels sit outside the square brackets. Words like
    # "verb" inside a usage note ("after a verb") are part of the gloss.
    brackets: list[str] = []

    def _hold_bracket(match: re.Match[str]) -> str:
        brackets.append(match.group(1))
        return f"\x00{len(brackets) - 1}\x00"

    text = re.sub(r"\[([^\]]*)\]", _hold_bracket, text)
    text = re.sub(r"[\u4e00-\u9fff]+", " ", text)
    text = re.sub(r"\S*" + _TONE_MARK.pattern + r"\S*", " ", text)
    text = re.sub(r"\b\d{5,}\b", " ", text)
    text = re.sub(r"\b[a-zA-Z]{1,6}[1-5](?:[a-zA-Z]{1,6}[1-5])+\b", " ", text)
    text = _POS_WORD.sub(" | ", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: " " + brackets[int(m.group(1))] + " ", text)
    text = re.sub(r"(?:^|\s)(?:[1-9]|1\d|20)\s+(?=[A-Za-z([])", " | ", text)
    text = re.sub(r"\s+", " ", text)
    parts: list[str] = []
    for part in text.split("|"):
        part = _strip_labels(part)
        part = re.sub(r"\s+", " ", part).strip(" ;,.-:|")
        if part and part not in parts:
            parts.append(part)
    if not parts:
        gloss = ""
    elif len(parts) == 1 or len(parts[0]) >= 80:
        gloss = parts[0]
    else:
        second = parts[1]
        gloss = parts[0] if second.lower() in parts[0].lower() else f"{parts[0]}; {second}"
    gloss = re.split(r"[《》]", gloss)[0]
    gloss = re.sub(r"\s*\([^)]*$", "", gloss)
    gloss = re.sub(r"\s*\[[^\]]*$", "", gloss)
    if gloss.count("(") < gloss.count(")"):
        gloss = re.sub(r"\s*\)+\s*$", "", gloss)
    if gloss.count("[") < gloss.count("]"):
        gloss = re.sub(r"\s*\]+\s*$", "", gloss)
    gloss = gloss.strip(" ;,.-")
    # A short lowercase definition sometimes keeps the next example's English
    # sentence ("length The overall length … is …"). Don't cut at capitals
    # that continue a name, like "Spring Festival".
    sentence = re.match(r"^([a-z][^A-Z]{0,60}?)\s+[A-Z].{30,}$", gloss)
    if sentence and re.search(r"\b(?:is|are|was|were|has|have)\b", gloss[len(sentence.group(1)) :]):
        gloss = sentence.group(1).rstrip(" ;,")
    if len(gloss) > 150:
        gloss = gloss[:147].rstrip(" ;,") + "…"
    return gloss


def short_example(defn: str) -> str:
    found = _first_example(_clean_defn(defn))
    if not found:
        return ""
    return found[2]


def lesson_headwords(path: Path) -> set[str]:
    words: set[str] = set()
    if not path.exists():
        return words
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r'\s*hanzi:\s*"([^"]*)"', line)
        if match:
            words.add(match.group(1).strip())
    return words


def _hsk_level(card: ET.Element) -> int | None:
    level = None
    for assign in card.findall("catassign"):
        name = assign.get("category") or ""
        match = re.search(r"Level\s+(\d+)", name)
        if match:
            found = int(match.group(1))
            level = found if level is None else min(level, found)
    return level


def _card_record(card: ET.Element) -> dict | None:
    entry = card.find("entry")
    if entry is None:
        return None
    simplified = ""
    traditional = ""
    for head in entry.findall("headword"):
        text = (head.text or "").strip()
        charset = (head.get("charset") or "").lower()
        if charset == "sc":
            simplified = text
        elif charset == "tc":
            traditional = text
    if not simplified:
        for head in entry.findall("headword"):
            if (head.text or "").strip():
                simplified = head.text.strip()
                break
    if not simplified:
        return None
    pron = ""
    for node in entry.findall("pron"):
        if (node.get("type") or "") in ("", "hypy") or node.get("tones") == "numbers":
            pron = (node.text or "").strip()
            if pron:
                break
    defn_node = entry.find("defn")
    defn = "".join(defn_node.itertext()) if defn_node is not None else ""
    created = int(card.get("created") or "0")
    date = (
        datetime.fromtimestamp(created, timezone.utc).strftime("%Y-%m-%d")
        if created
        else ""
    )
    level = _hsk_level(card)
    pinyin, problems = tone_numbers_to_marks(pron)
    record = {
        "id": f"{simplified}|{pinyin}",
        "hanzi": simplified,
        "pinyin": pinyin,
        "gloss": short_gloss(defn),
        "date": date,
        "tags": ["pleco", "saved" if level is None else f"HSK {level}"],
        "kind": "saved" if level is None else "hsk",
        "hsk": level,
        "_problems": problems,
        "_created": created,
    }
    if traditional and traditional != simplified:
        record["traditional"] = traditional
    example = short_example(defn)
    if example:
        record["example"] = example
    return record


def _prefer(candidate: dict, current: dict) -> bool:
    """Saved cards beat HSK copies. Otherwise keep the earlier save."""
    if candidate["kind"] == "saved" and current["kind"] != "saved":
        return True
    if current["kind"] == "saved" and candidate["kind"] != "saved":
        return False
    return candidate["_created"] < current["_created"]


def import_cards(xml_path: Path, vocab_path: Path) -> dict:
    lesson = lesson_headwords(vocab_path)
    root = ET.parse(xml_path).getroot()
    cards = list(root.iter("card"))
    # One card per simplified headword plus reading, so 长 cháng and 长 zhǎng
    # both survive. A repeated export of the same reading still collapses.
    chosen: dict[tuple[str, str], dict] = {}
    missing_head = 0
    for card in cards:
        record = _card_record(card)
        if record is None:
            missing_head += 1
            continue
        key = (record["hanzi"], record["pinyin"])
        previous = chosen.get(key)
        if previous is None or _prefer(record, previous):
            chosen[key] = record

    skipped_keys = [key for key in chosen if key[0] in lesson]
    skipped = sorted({hanzi for hanzi, _pinyin in skipped_keys})
    for key in skipped_keys:
        del chosen[key]

    words = list(chosen.values())
    words.sort(key=lambda word: (word["kind"] != "saved", word["hsk"] or 0, word["date"], word["hanzi"], word["pinyin"]))

    pinyin_warnings = []
    missing_pinyin = 0
    missing_gloss = 0
    with_example = 0
    level_counts = {n: 0 for n in range(1, 7)}
    saved = 0
    for word in words:
        problems = word.pop("_problems")
        word.pop("_created")
        if problems:
            pinyin_warnings.extend(problems)
        if not word["pinyin"]:
            missing_pinyin += 1
        if not word["gloss"]:
            missing_gloss += 1
        if word.get("example"):
            with_example += 1
        if word["kind"] == "saved":
            saved += 1
        elif word["hsk"] in level_counts:
            level_counts[word["hsk"]] += 1

    counts = {
        "cards": len(cards),
        "unique_headwords": len({word["hanzi"] for word in words} | set(skipped)),
        "unique_readings": len(words) + len(skipped_keys),
        "duplicates_dropped": len(cards) - missing_head - len(words) - len(skipped_keys),
        "missing_headwords": missing_head,
        "skipped_lesson_words": skipped,
        "imported": len(words),
        "saved": saved,
        "hsk": len(words) - saved,
        "hsk1": level_counts[1],
        "hsk2": level_counts[2],
        "hsk3": level_counts[3],
        "hsk4": level_counts[4],
        "hsk5": level_counts[5],
        "hsk6": level_counts[6],
        "missing_pinyin": missing_pinyin,
        "pinyin_warnings": len(set(pinyin_warnings)),
        "missing_gloss": missing_gloss,
        "with_example": with_example,
    }
    return {"counts": counts, "words": words, "_warning_samples": sorted(set(pinyin_warnings))[:20]}


def dump_payload(payload: dict, dest: Path) -> None:
    public = {"counts": payload["counts"], "words": payload["words"]}
    lines = [json.dumps(word, ensure_ascii=False, separators=(",", ":")) for word in public["words"]]
    body = (
        '{"counts":'
        + json.dumps(public["counts"], ensure_ascii=False, separators=(",", ":"))
        + ',\n"words":[\n'
        + ",\n".join(lines)
        + "\n]}\n"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")


def self_test() -> None:
    cases = {
        "mo4qi4": "mòqì",
        "xiang3//fu2": "xiǎng·fú",
        "chun1lian2": "chūnlián",
        "ba4ba5": "bàba",
        "Bei3jing1": "Běijīng",
        "ba2miao2-zhu4zhang3": "bámiáo-zhùzhǎng",
        "da3 dian4hua4": "dǎ diànhuà",
        "dui4bu5qi3": "duìbuqǐ",
        "nv3": "nǚ",
        "nu:3": "nǚ",
        "lv4": "lǜ",
        "lve4": "lüè",
        "nve4": "nüè",
        "xue2": "xué",
        "yue4": "yuè",
        "yi1": "yī",
        "yu3": "yǔ",
        "er2": "ér",
        "na3r5": "nǎr",
        "dong1xi5": "dōngxi",
        "Ai4": "Ài",
        "zhong1guo2": "zhōngguó",
        "xi1'an1": "xī'ān",
        "ma1ma5": "māma",
        "hou4mian5": "hòumian",
        "kan4//jian5": "kàn·jian",
        "bu4//ke4qi5": "bù·kèqi",
        "jiong3": "jiǒng",
        "shui3": "shuǐ",
        "liu4": "liù",
        "you3": "yǒu",
        "xiao3": "xiǎo",
        "duo1": "duō",
        "bao1zi5": "bāozi",
        "ban4sui2": "bànsuí",
        "zhang1": "zhāng",
        "chi1": "chī",
        "shi4": "shì",
        "cai4": "cài",
        "bai3fen1zhi1": "bǎifēnzhī",
        "ng3": "ňg",
        "bu4dan4…er2qie3…": "bùdàn…érqiě…",
        "yin1wei4…suo3yi3…": "yīnwèi…suǒyǐ…",
    }
    failed = 0
    for source, expected in cases.items():
        got, problems = tone_numbers_to_marks(source)
        if got != expected or problems:
            failed += 1
            print(f"FAIL {source!r} -> {got!r}, expected {expected!r}, problems={problems}")
    moqi = (
        "noun secret agreement 关于这个问题双方曾有默契。 Guānyú zhège wèntí shuāngfāng céng yǒu mòqì. "
        "The two sides had a secret agreement on this issue. "
        "adjective tacit agreement (or understanding) 互相默契 Hùxiāng mòqì have perfect mutual understanding "
        "这对双打选手配合默契。 Zhè duì shuāngdǎ xuǎnshǒu pèihé mòqì. This doubles pair played in perfect unison. "
        "or This doubles pair has good team work."
    )
    gloss = short_gloss(moqi)
    if gloss != "secret agreement; tacit agreement (or understanding)":
        failed += 1
        print(f"FAIL gloss {gloss!r}")
    example = short_example(moqi)
    if "The two sides had a secret agreement" not in example or not example.startswith("关于"):
        failed += 1
        print(f"FAIL example {example!r}")
    de = (
        "auxiliary 1 [after a verb or an adjective to express possibility or capability] "
        "吃不得 chībude inedible 那事做不得！ Nà shì zuò bù de! You mustn’t do that! "
        "2 [between a verb and its complement to express possibility] 那办得到。 Nà bàn de dào. That can be done."
    )
    de_gloss = short_gloss(de)
    if "possibility" not in de_gloss or "You must" in de_gloss or "Nà" in de_gloss:
        failed += 1
        print(f"FAIL de gloss {de_gloss!r}")
    vehicles = short_gloss("measure word [for vehicles] 三辆大车 sān liàng dà chē three carts")
    if vehicles != "for vehicles":
        failed += 1
        print(f"FAIL vehicles {vehicles!r}")
    if short_gloss("noun mathematics") != "mathematics":
        failed += 1
        print(f"FAIL mathematics {short_gloss('noun mathematics')!r}")
    phone = short_gloss("noun number 电话号码 diànhuà hàomǎ telephone number")
    if phone != "number":
        failed += 1
        print(f"FAIL phone {phone!r}")
    phone_ex = short_example("noun number 电话号码 diànhuà hàomǎ telephone number")
    if "telephone number" not in phone_ex:
        failed += 1
        print(f"FAIL phone example {phone_ex!r}")
    if failed:
        raise SystemExit(f"{failed} self-test failure(s)")
    print(f"self-test ok ({len(cases)} pinyin cases)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", nargs="?", type=Path, help="Pleco 2.0 XML export")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        if args.xml is None:
            return
    if args.xml is None:
        parser.error("pass the Pleco XML path, or --self-test")
    payload = import_cards(args.xml, args.vocab)
    samples = payload.pop("_warning_samples")
    dump_payload(payload, args.output)
    counts = payload["counts"]
    print(f"wrote {args.output}")
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    if samples:
        print("pinyin warnings (sample):")
        for sample in samples:
            print(" ", sample)


if __name__ == "__main__":
    main()
