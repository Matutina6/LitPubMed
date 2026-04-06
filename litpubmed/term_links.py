"""终端 PubMed 链接：OSC 8 超链接（支持时）+ 可复制的 https URL。"""

from __future__ import annotations

import os
import sys


def pubmed_article_url(pmid: str) -> str:
    p = str(pmid).strip()
    return f"https://pubmed.ncbi.nlm.nih.gov/{p}/"


_ST = "\033\\"


def _osc8(url: str, label: str) -> str:
    return f"\033]8;;{url}{_ST}{label}\033]8;;{_ST}"


def terminal_hyperlinks_enabled() -> bool:
    if os.environ.get("LITPUBMED_NO_HYPERLINK", "").strip():
        return False
    if os.environ.get("NO_HYPERLINK", "").strip():
        return False
    if os.environ.get("LITPUBMED_FORCE_HYPERLINK", "").strip():
        return True
    if os.environ.get("FORCE_HYPERLINK", "").strip():
        return True
    return sys.stdout.isatty()


def format_pubmed_hit_line(
    pmid: str,
    title: str,
    *,
    title_max: int = 100,
    indent: str = "  ",
) -> str:
    """一行展示；支持 OSC 8 时整行可点击，否则标题行 + 缩进 URL 行。"""
    p = str(pmid or "").strip()
    t = (title or "")[:title_max]
    label = f"PMID {p} — {t}" if p else t
    url = pubmed_article_url(p) if p else ""
    if not url:
        return f"{indent}{label}"
    if terminal_hyperlinks_enabled():
        return f"{indent}{_osc8(url, label)}"
    return f"{indent}{label}\n{indent}  {url}"


def format_pubmed_tab_line(pmid: str, title: str, *, include_url: bool = True) -> str:
    """用于非 TTY / 管道：PMID、标题、URL 用制表符分隔。"""
    p = str(pmid or "").strip()
    t = title or ""
    if include_url and p:
        return f"{p}\t{t}\t{pubmed_article_url(p)}"
    return f"{p}\t{t}"


def format_pubmed_url_line(pmid: str, *, indent: str = "  ", prefix: str = "PubMed: ") -> str:
    p = str(pmid or "").strip()
    if not p:
        return ""
    url = pubmed_article_url(p)
    lab = f"{prefix}{url}"
    if terminal_hyperlinks_enabled():
        return f"{indent}{_osc8(url, lab)}"
    return f"{indent}{lab}"
