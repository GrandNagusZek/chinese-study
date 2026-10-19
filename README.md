# 日课 · chinese-study

Static study site for a daily Chinese lesson: new words, a short reading, near-synonym and grammar notes, exercises with answers hidden until clicked, and a writing prompt. Simplified characters. No analytics, no accounts, no external fonts or scripts.

The published site is [https://grandnaguszek.github.io/chinese-study/](https://grandnaguszek.github.io/chinese-study/).

Adding a lesson does not require Node, Ruby, or any other tool on your machine. Commit one Markdown file. When the lesson has new words or a new weak point, append to two YAML files. GitHub Actions builds the site. The home page, archive, vocabulary table, and flashcards pick up the new files on their own. There is no index to edit.

## Enable GitHub Pages

Do this once, in the repository on GitHub:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.

Do not choose “Deploy from a branch”. The branch contains the Markdown sources. The workflow builds HTML and deploys that.

3. Merge to `main` (or run **Actions → Deploy to GitHub Pages → Run workflow** after the workflow file is on `main`).
4. When the deploy job is green, the site is at [https://grandnaguszek.github.io/chinese-study/](https://grandnaguszek.github.io/chinese-study/).

The repository is public, which is what GitHub Pages needs on a free account. Nothing else has to be toggled: no custom domain, no secrets, no environment variables.

If the first deploy fails because the `github-pages` environment does not exist yet, confirm the Pages source is **GitHub Actions**, then re-run the workflow.

`baseurl` in `_config.yml` is `/chinese-study`. Change it only if the repository is renamed.

## How to add a daily lesson

### 1. Add one lesson file

Create `_lessons/YYYY-MM-DD-short-slug.md`. The filename is the whole index entry. Copy this template and replace the placeholders:

```markdown
---
layout: lesson
title: "第二课：标题"
date: 2026-10-19
lesson_id: 2026-10-19-short-slug
summary: "一句话说明这一课在练什么。"
---

## 阅读

短文或文稿摘录。口诀、引文用引用块：

> 引文。

## 辨析

### 甲 · 乙

**甲**的说明。

> 例句。

**乙**的说明。

## 语法

补语、搭配或语体上要注意的一点。

## 练习

**1.** 题目正文。空格写成 \_\_\_，避免成串下划线被 Markdown 吃掉。

<details class="reveal">
<summary>查看答案</summary>
<div class="answer">
<p>答案写在这里。默认折叠，读者点击「查看答案」才打开。</p>
</div>
</details>

## 写作

一句写作要求。

<details class="reveal">
<summary>参考说法</summary>
<div class="answer">
<p>可对照的说法。没有标准答案就删掉这一块。</p>
</div>
</details>
```

Rules:

- `lesson_id` must be exactly the filename without `.md`. The URL will be `/lessons/<lesson_id>/`.
- `date` is unquoted `YYYY-MM-DD`. The archive sorts on it, newest first.
- Keep the filename in ASCII: digits, lowercase letters, hyphens.
- The five headings (`阅读`, `辨析`, `语法`, `练习`, `写作`) are the lesson body. The word list above them is not written in this file.
- On the day you push, if `date` is that build’s date, the home page labels the lesson 今日课程. Otherwise the newest lesson already due is labeled 最近一课 and still sits at the top.

### 2. Append vocabulary

Add new words at the **end** of `_data/vocab.yml`. One block per word. `lesson` must equal that lesson’s `lesson_id`, or the word will not show on the lesson page.

```yaml
- hanzi: "例词"
  pinyin: "lìcí"
  gloss: "English gloss, specific enough to quiz"
  example: "一句包含该词的例句。"
  date: "2026-10-19"
  lesson: "2026-10-19-short-slug"
  tags: ["near-synonym"]
```

Field rules:

- Quote `hanzi`, `pinyin`, `gloss`, `example`, and `date`.
- `date` is the day the word was added, `"YYYY-MM-DD"`.
- `lesson` is the lesson id, unquoted if it has no special characters.
- `tags` is a list. Reuse these when they fit: `near-synonym`, `collocation`, `complement`, `文言`. An empty list is `[]`.
- Do not duplicate a word that is already in the file. The vocabulary table and the flashcards both read only this file.

The lesson page lists every entry whose `lesson` equals its `lesson_id`, in file order.

### 3. Append a focus area, when there is one

Skip this when the lesson does not add a weak point. Otherwise append to `_data/focus.yml`:

```yaml
- id: short-ascii-id
  title: "短标题"
  summary: "一行说明，用在首页。"
  status: active
  since: "2026-10-19"
  notes: |
    具体笔记。可以用 Markdown 列表。

    - 第一点。
    - 第二点。
```

- `id` is a unique ASCII slug. It becomes the anchor `/focus/#short-ascii-id`.
- `status: active` shows the item on the home page. Set `status: resolved` to keep the note on the focus page and drop it from the home panel.
- `notes: |` keeps the line breaks. Indent the note body with two spaces.

## Layout

```
_config.yml                 site title, baseurl, lesson collection
_data/vocab.yml             every word learned so far
_data/focus.yml             weak points
_lessons/*.md               one file per lesson
_layouts/                   page and lesson templates
index.html                  home: latest lesson, recent lessons, focus panel
lessons.html                archive, newest first
vocab.html                  sortable, filterable table
focus.html                  weak points
review.html                 flashcards (progress in localStorage only)
assets/css/style.css
assets/js/                  theme, table sort/filter, flashcards
.github/workflows/pages.yml build on pull requests; deploy on push to main
```

Flashcard progress and the light/dark choice live in the browser under `zh-study-review-v1` and `zh-study-theme`. The site never receives them.

## Local preview

You do not need this to publish. To preview:

```bash
bundle install
bundle exec jekyll serve
```

Open `http://127.0.0.1:4000/chinese-study/`. Ruby 3.2 and the `Gemfile` are enough. Production uses the same build in GitHub Actions (`bundle exec jekyll build`), then deploys `_site`.
