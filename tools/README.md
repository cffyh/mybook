# EPUB 构建工具

把本仓库里的文章编译成 EPUB 电子书。**只依赖 Python 3.10+ 标准库**——不需要
pandoc、calibre，也不需要 pip 装任何东西。

```bash
python3 tools/build_epub.py                 # 精编版 → dist/两极之间.epub
python3 tools/build_epub.py --edition full  # 全集（另附原始笔记）
python3 tools/build_epub.py --edition all   # 两个版本都出
```

产物在 `dist/`。两个版本都通过 [epubcheck](https://github.com/w3c/epubcheck)
5.2.1 校验，零错误零警告。

| 版本 | 内容 | 规模 |
|---|---|---|
| `main` | 各书稿、关键文章、札记、独立长文、附录 | 10 卷 216 篇，约 1.4 MB |
| `full` | 以上全部，再加 `backup/` 下的原始笔记与早期 Word 原稿 | 11 卷 1012 篇，约 4.7 MB |

## 分卷结构

书名、作者、分卷次序、每卷收哪些目录、卷首语，全部写在
[`book.json`](book.json) 里，**改结构不用改代码**。

```json
{
  "id": "zonglun",
  "title": "第四卷 · 总论与专论",
  "subtitle": "书稿 5",
  "intro": "项目里最新、最厚的一卷……",
  "sources": [
    { "path": "书稿 5/总论", "title": "总论" },
    { "path": "书稿 5", "title": "专论散篇", "recursive": false }
  ]
}
```

一条 `source` 可以是一个文件路径，也可以是一个对象：

- `path`：文件或目录，相对仓库根目录。
- `title`：给了标题，这个来源就整体收成卷内的一辑；不给则直接铺在卷下。
- `recursive`：默认 `true`（子目录各成一辑）。设 `false` 时只收该目录下的散篇——
  用来在若干子目录已单独列出之后，兜住剩下的顶层文件。
- `order`：一串文件名前缀，按这个顺序排在最前；其余仍按自然序。
- `exclude`：路径里含这些片段的文件跳过。

`sources` 的书写顺序就是书里的顺序，篇与辑混排也照写的来。

分卷次序与篇目取舍依据仓库自带的[《全书总纲》](../全书总纲.md)与
[《书稿定位与查漏策略》](../书稿定位与查漏策略.md)，没有改动任何一篇的正文。

## 编纂时做了什么

- **三种源格式**：Markdown（206 篇）、HTML 成稿（`书稿 4/` 等 11 篇）、
  Word 文档（`.docx`，读 `word/document.xml` 取正文、标题层级、粗体与列表）。
- **篇目排序**：整数按数值比，小数部分按字符串比——因为作者用 `1.21` 表示
  `1.2` 的细化，顺序应是 1.1 → 1.2 → 1.21 → 1.3，而不是读成小数。中文序数
  （第六章、乐章五）先折算成数字。`README` 永远排在最前。
- **交叉引用**：篇与篇之间的相对链接改写成书内跳转。仓库里不少互链因为改名、
  挪目录或漏掉数字前缀而失效，这类会按文件名再找一次（约 117 处能接回来）；
  同名分不清的宁可退化成纯文字，也不乱指。目标不在本书内的链接同样只留文字，
  书里不会出现断链。
- **转址占位文件**：正文已迁往别处、只剩一句「请改读」的文件会跳过，构建时列出。
- **内容去重**：`backup/` 下与正式目录一字不差的副本按内容哈希去重。
- **覆盖检查**：每次构建都会比对仓库里所有在范围内的文稿，把没进书的列出来，
  免得悄悄漏掉。
- **中文排版**：首行缩进 2 em、`inter-ideograph` 两端对齐、着重号代替中文斜体、
  行高 1.8。不内嵌字体——CJK 字体动辄十几兆，阅读器自带的中文字体通常更合用，
  样式表只给一份字体族优先级。
- **公式**：短公式（`$F=mg$`、`$0.8^4 \approx 41\%$`）转成 Unicode 与
  `<sup>`/`<sub>`。阅读器基本不支持 MathJax，也别指望 MathML。
- **目录**：`nav.xhtml` 按卷 → 辑 → 篇嵌套（最深四层），另出一份 `toc.ncx`
  给只认 NCX 的老阅读器。加 `--deep-toc` 可以把每篇的一级小标题也列进目录。
- **可复现**：`dcterms:modified` 取最近一次提交时间，zip 条目顺序与时间戳固定。
  同一份文稿反复构建得到字节一致的 EPUB，重跑不会在 git 里留下假 diff。
  用 `SOURCE_DATE_EPOCH` 可以覆盖。

每篇正文末尾都有一行小字标注它在仓库里的原始路径，便于回查与订正。

## 校验

```bash
# 下载 epubcheck 解压到 tools/epubcheck/，或用 EPUBCHECK_JAR 指向 jar
python3 tools/build_epub.py --check
```

## 封面

`assets/cover.png` 随仓库提交，所以日常构建不需要 Pillow，也不需要中文字体。
改了书名想重画封面时：

```bash
pip install pillow
python3 tools/make_cover.py --font /path/to/NotoSerifSC-Bold.otf
```

封面图缺失时会自动退回一张纯文字 SVG 封面，构建不会失败。

## 其他选项

| 选项 | 作用 |
|---|---|
| `--deep-toc` | 目录里连每篇的一级小标题一起列出 |
| `--keep-stubs` | 保留「正文已迁走」的转址占位文件 |
| `-v` | 打印被降级的链接、去重的篇目等细节 |
| `--config` | 换一份 book.json |

## 代码结构

| 文件 | 职责 |
|---|---|
| `build_epub.py` | 命令行入口、前后附页、目录树、构建报告 |
| `epubgen/structure.py` | 篇目收集、排序、分卷、交叉引用改写 |
| `epubgen/mdconv.py` | Markdown → XHTML |
| `epubgen/htmlconv.py` | HTML 成稿 → XHTML |
| `epubgen/docxconv.py` | .docx → XHTML |
| `epubgen/texmath.py` | 简单 TeX → XHTML |
| `epubgen/epub.py` | EPUB 3 打包（OPF / nav / NCX / zip） |
| `epubgen/cover.py` | 封面（位图优先，退回 SVG） |
| `assets/style.css` | 中文排版样式表 |

Markdown 转换刻意不支持三样东西：setext 标题（全仓库为零）、下划线强调
（`_x_` 在 `第六章_小与大` 这类文件名里全是误报）、Markdown 里的内联 HTML
（也为零）。少支持一点，换来的是不会把正文里的普通字符错认成标记。
