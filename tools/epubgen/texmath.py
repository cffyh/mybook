"""把简单的 TeX 片段渲染成可在电子书阅读器里直接显示的 XHTML。

阅读器基本不支持 MathJax，也不能指望它们渲染 MathML。仓库里的公式都很短
（$F=mg$、$0.8^4 \\approx 41\\%$ 之类），所以这里做一件事：把常见符号换成
Unicode、把上下标换成 <sup>/<sub>，其余原样保留。遇到看不懂的命令不会报错，
只会退化成朴素文本。
"""

from __future__ import annotations

import re

SYMBOLS = {
    # 关系与运算
    "approx": "≈", "neq": "≠", "ne": "≠", "leq": "≤", "le": "≤",
    "geq": "≥", "ge": "≥", "times": "×", "cdot": "·", "cdots": "⋯",
    "ldots": "…", "dots": "…", "div": "÷", "pm": "±", "mp": "∓",
    "equiv": "≡", "sim": "∼", "propto": "∝", "ll": "≪", "gg": "≫",
    "circ": "∘", "ast": "∗", "star": "⋆", "oplus": "⊕", "otimes": "⊗",
    # 箭头
    "to": "→", "rightarrow": "→", "Rightarrow": "⇒", "leftarrow": "←",
    "Leftarrow": "⇐", "leftrightarrow": "↔", "Leftrightarrow": "⇔",
    "mapsto": "↦", "longrightarrow": "⟶", "implies": "⟹", "iff": "⟺",
    # 集合与逻辑
    "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆",
    "supset": "⊃", "supseteq": "⊇", "cup": "∪", "cap": "∩",
    "emptyset": "∅", "varnothing": "∅", "forall": "∀", "exists": "∃",
    "neg": "¬", "lnot": "¬", "land": "∧", "lor": "∨", "therefore": "∴",
    # 分析
    "infty": "∞", "partial": "∂", "nabla": "∇", "sum": "∑", "prod": "∏",
    "int": "∫", "iint": "∬", "oint": "∮", "sqrt": "√", "lim": "lim",
    "log": "log", "ln": "ln", "exp": "exp", "sin": "sin", "cos": "cos",
    "tan": "tan", "max": "max", "min": "min", "deg": "°",
    # 希腊字母
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    # 空白与转义
    "quad": " ", "qquad": "  ", ",": " ", ";": " ", ":": " ", "!": "",
    " ": " ", "%": "%", "&": "&", "#": "#", "$": "$", "_": "_",
    "{": "{", "}": "}", "\\": "",
}

# 只取内容、丢掉字体语义的命令
UNWRAP = {
    "mathrm", "mathbf", "mathit", "mathsf", "mathtt", "mathcal", "mathbb",
    "text", "textrm", "textbf", "textit", "operatorname", "boldsymbol",
    "bm", "rm", "bf", "it", "left", "right", "displaystyle", "limits",
}

_SUP = str.maketrans("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ")
_SUB = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _read_group(src: str, pos: int) -> tuple[str, int]:
    """读取 `{...}` 或紧跟其后的单个字符，返回 (内容, 新位置)。"""
    if pos >= len(src):
        return "", pos
    if src[pos] != "{":
        if src[pos] == "\\":
            m = re.compile(r"\\([A-Za-z]+|.)").match(src, pos)
            if m:
                return m.group(0), m.end()
        return src[pos], pos + 1
    depth = 0
    for i in range(pos, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[pos + 1:i], i + 1
    return src[pos + 1:], len(src)


def _script(inner: str, tag: str) -> str:
    """上下标：能用 Unicode 就用，否则退回 <sup>/<sub>。"""
    plain = render(inner)
    if "<" not in plain:
        table = _SUP if tag == "sup" else _SUB
        if plain and all(ch in table for ch in map(ord, plain)):
            return plain.translate(table)
    return f"<{tag}>{plain}</{tag}>"


def render(tex: str) -> str:
    """把一段 TeX 渲染成 XHTML 行内片段。"""
    out: list[str] = []
    i, n = 0, len(tex)
    while i < n:
        ch = tex[i]
        if ch == "\\":
            m = re.compile(r"\\([A-Za-z]+|.)").match(tex, i)
            if not m:
                out.append("\\")
                i += 1
                continue
            name = m.group(1)
            i = m.end()
            if name == "frac":
                num, i = _read_group(tex, i)
                den, i = _read_group(tex, i)
                out.append(f"{render(num)}/{render(den)}")
            elif name in UNWRAP:
                inner, i = _read_group(tex, i)
                out.append(render(inner))
            elif name in SYMBOLS:
                out.append(_esc(SYMBOLS[name]))
            else:
                out.append(_esc(name))
        elif ch in "^_":
            inner, i = _read_group(tex, i + 1)
            out.append(_script(inner, "sup" if ch == "^" else "sub"))
        elif ch in "{}":
            i += 1
        else:
            out.append(_esc(ch))
            i += 1
    return "".join(out)


def inline(tex: str) -> str:
    """行内公式 → <span class="math">…</span>"""
    return f'<span class="math">{render(tex.strip())}</span>'


def block(tex: str) -> str:
    """行间公式 → <p class="math-block">…</p>"""
    lines = [render(line.strip()) for line in tex.strip().split("\n") if line.strip()]
    return '<p class="math-block">' + "<br/>".join(lines) + "</p>"
