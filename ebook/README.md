# 工厂文集

从仓库里的成熟文章生成阅读成品。

## EPUB（阅读器 / 手机）

```bash
python3 -m pip install -r ebook/requirements.txt
python3 ebook/build_epub.py
```

产出：`ebook/以小控大——工厂文集.epub`

## 离线 wiki（电脑，推荐）

点侧栏即达，正文连续滚动，没有翻页。

```bash
python3 ebook/build_wiki.py --serve
```

打开 http://127.0.0.1:8765/ 。站点在 `wiki/`。快捷键：`/` 搜索，`J` / `K` 上下篇。

## 收录范围

按 [`全书总纲.md`](../全书总纲.md) 的语料分桶分卷，收录书稿 4 / 3 / 2 / 5、书稿 1、关键文章、札记与根目录成文。不收录 `backup/`、访谈素材库、转址残篇与作者工作流文件。

三本成品书是同一批素材的三种切法，后卷会与前卷有主题回响，这是文集结构，不是目录错误。
