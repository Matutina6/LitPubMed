"""解析综合模式中的结构化表格块，并按显示宽度重绘为对齐框线表。"""

from __future__ import annotations

import json
from typing import Any

from litpubmed.terminal_table import render_table

TABLE_START = "<<LITPUBMED_TABLE_JSON>>"
TABLE_END = "<<END_LITPUBMED_TABLE_JSON>>"


def _parse_table_obj(
    obj: Any,
    *,
    default_max_cell_width: int | None = None,
    default_wrap_width: int = 30,
) -> str | None:
    if not isinstance(obj, dict):
        return None
    headers = obj.get("headers")
    rows = obj.get("rows")
    if not isinstance(headers, list) or not headers:
        return None
    if not isinstance(rows, list):
        return None
    hs = [str(h) for h in headers]
    rs: list[list[str]] = []
    for r in rows:
        if isinstance(r, (list, tuple)):
            rs.append([str(x) if x is not None else "" for x in r])
        else:
            rs.append([str(r)])
    max_w = obj.get("max_cell_width")
    mw: int | None = default_max_cell_width
    if isinstance(max_w, int) and max_w > 4:
        mw = min(max_w, 512)

    wrap = obj.get("wrap_width")
    ww: int | None
    if isinstance(wrap, int):
        ww = None if wrap <= 0 else min(wrap, 120)
    else:
        ww = default_wrap_width if default_wrap_width > 0 else None

    return render_table(hs, rs, max_cell_width=mw, wrap_width=ww)


def _extract_json_objects(payload: str) -> tuple[Any, int] | None:
    payload = payload.lstrip()
    try:
        obj, idx = json.JSONDecoder().raw_decode(payload)
    except json.JSONDecodeError:
        return None
    return obj, idx


def format_synthesis_output(
    text: str,
    *,
    default_max_cell_width: int | None = None,
    default_wrap_width: int = 30,
) -> str:
    """将模型输出的 TABLE_JSON 块替换为 wcwidth 对齐后的表格；无块则原文返回。"""
    if TABLE_START not in text:
        return text
    out: list[str] = []
    i = 0
    while True:
        a = text.find(TABLE_START, i)
        if a < 0:
            out.append(text[i:])
            break
        out.append(text[i:a])
        b = text.find(TABLE_END, a + len(TABLE_START))
        if b < 0:
            out.append(text[a:])
            break
        raw_block = text[a + len(TABLE_START) : b].strip()
        parsed = _extract_json_objects(raw_block)
        if parsed is None:
            out.append(text[a : b + len(TABLE_END)])
        else:
            obj, _ = parsed
            rendered = _parse_table_obj(
                obj,
                default_max_cell_width=default_max_cell_width,
                default_wrap_width=default_wrap_width,
            )
            if rendered is None:
                out.append(text[a : b + len(TABLE_END)])
            else:
                out.append("\n" + rendered + "\n")
        i = b + len(TABLE_END)
    return "".join(out)
