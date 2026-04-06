"""用 wcwidth 按「显示宽度」对齐的 Unicode 框线表（适配中英文混排终端）。"""

from __future__ import annotations

from typing import Any

from wcwidth import wcwidth, wcswidth


def _cell_text(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(s.split())


def _clip_to_width(s: str, max_w: int) -> str:
    if max_w <= 0:
        return ""
    if wcswidth(s) <= max_w:
        return s
    out: list[str] = []
    w = 0
    for ch in s:
        cw = wcwidth(ch)
        if cw < 0:
            cw = 1
        if w + cw > max_w - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def _pad_to_width(s: str, width: int) -> str:
    s = _clip_to_width(s, width)
    pad = width - wcswidth(s)
    return s + (" " * pad if pad > 0 else "")


def _pad_only(s: str, width: int) -> str:
    """不主动加省略号，仅填充到显示宽度（换行后的行应已不超出 width）。"""
    sw = wcswidth(s)
    if sw > width:
        return _clip_to_width(s, width)
    return s + " " * (width - sw)


def _split_first_line(rest: str, max_w: int) -> tuple[str, str]:
    """从 rest 切出第一行（显示宽度 <= max_w），优先在空格处断行。"""
    if not rest:
        return "", ""
    if max_w <= 0:
        return rest[:1], rest[1:]

    w = 0
    cut = 0
    last_space = -1
    i = 0
    while i < len(rest):
        ch = rest[i]
        cw = wcwidth(ch)
        if cw < 0:
            cw = 1
        if w + cw > max_w:
            break
        if ch.isspace():
            last_space = i
        w += cw
        cut = i + 1
        i += 1

    if cut == 0:
        ch = rest[0]
        cw = wcwidth(ch)
        if cw < 0:
            cw = 1
        return rest[:1], rest[1:]

    if cut >= len(rest):
        return rest, ""

    if last_space > 0 and last_space < cut - 1:
        line = rest[: last_space + 1].rstrip()
        new_rest = rest[last_space + 1 :].lstrip()
        if line:
            return line, new_rest

    line = rest[:cut].rstrip()
    new_rest = rest[cut:].lstrip()
    return line, new_rest


def _wrap_to_lines(s: str, max_w: int) -> list[str]:
    if not s:
        return [""]
    if max_w <= 0:
        return [s]
    if wcswidth(s) <= max_w:
        return [s]
    lines: list[str] = []
    rest = s
    guard = 0
    while rest:
        guard += 1
        if guard > len(s) + 10:
            lines.append(rest)
            break
        line, rest = _split_first_line(rest, max_w)
        if line:
            lines.append(line)
        elif rest:
            ch, rest = rest[0], rest[1:]
            lines.append(ch)
    return lines if lines else [""]


def _render_wrapped_table(
    norm_headers: list[str],
    norm_rows: list[list[str]],
    *,
    wrap_w: int,
) -> str:
    cols = len(norm_headers)
    head_lines = [_wrap_to_lines(norm_headers[c], wrap_w) for c in range(cols)]
    body_line_grids: list[list[list[str]]] = []
    for r in norm_rows:
        body_line_grids.append([_wrap_to_lines(r[c], wrap_w) for c in range(cols)])

    col_widths: list[int] = []
    for c in range(cols):
        mx = 3
        for ln in head_lines[c]:
            mx = max(mx, wcswidth(ln))
        for grid in body_line_grids:
            for ln in grid[c]:
                mx = max(mx, wcswidth(ln))
        col_widths.append(mx)

    segs = ["─" * (cw + 2) for cw in col_widths]
    top = "┌" + "┬".join(segs) + "┐"
    sep = "├" + "┼".join(segs) + "┤"
    bot = "└" + "┴".join(segs) + "┘"

    def emit_physical_row(line_idx: int, cells_lines: list[list[str]]) -> str:
        parts: list[str] = []
        for c in range(cols):
            lc = cells_lines[c]
            piece = lc[line_idx] if line_idx < len(lc) else ""
            parts.append(" " + _pad_only(piece, col_widths[c]) + " ")
        return "│" + "│".join(parts) + "│"

    def emit_logical_row(cells_lines: list[list[str]]) -> list[str]:
        h = max((len(x) for x in cells_lines), default=1)
        return [emit_physical_row(i, cells_lines) for i in range(h)]

    lines: list[str] = [top]
    lines.extend(emit_logical_row(head_lines))
    lines.append(sep)
    for grid in body_line_grids:
        lines.extend(emit_logical_row(grid))
        lines.append(sep)
    if lines[-1] == sep:
        lines.pop()
    lines.append(bot)
    return "\n".join(lines)


def render_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    max_cell_width: int | None = None,
    wrap_width: int | None = None,
) -> str:
    """
    max_cell_width: 仅在不换行时生效，限制单列最大显示宽度，超出截断加「…」。
    wrap_width: >0 时单元格内按显示宽度自动换行（中英文混排）；列宽取该列各行最大宽度。
    二者同时给出时，换行宽度为 min(wrap_width, max_cell_width)。
    wrap_width 为 None 或 <=0 且未因 max_cell_width 强制换行时，保持单行逻辑。
    """
    if not headers:
        return ""
    cols = len(headers)
    norm_headers = [_cell_text(h) for h in headers]
    norm_rows: list[list[str]] = []
    for r in rows:
        if not isinstance(r, (list, tuple)):
            r = [r]
        cells = [_cell_text(x) for x in r]
        if len(cells) < cols:
            cells.extend([""] * (cols - len(cells)))
        norm_rows.append(cells[:cols])

    effective_wrap: int | None = None
    if wrap_width is not None and wrap_width > 0:
        effective_wrap = wrap_width
        if max_cell_width is not None and max_cell_width > 0:
            effective_wrap = min(effective_wrap, max_cell_width)
    elif max_cell_width is not None and max_cell_width > 0:
        # 不换行：仅用 max_cell_width 截断
        pass
    else:
        effective_wrap = None

    if effective_wrap is not None:
        return _render_wrapped_table(norm_headers, norm_rows, wrap_w=effective_wrap)

    grid: list[list[str]] = [norm_headers] + norm_rows
    col_widths: list[int] = []
    for c in range(cols):
        mx = 3
        for row in grid:
            mx = max(mx, wcswidth(row[c]))
        if max_cell_width is None or max_cell_width <= 0:
            col_widths.append(mx)
        else:
            col_widths.append(min(max_cell_width, mx))

    segs = ["─" * (cw + 2) for cw in col_widths]
    top = "┌" + "┬".join(segs) + "┐"
    sep = "├" + "┼".join(segs) + "┤"
    bot = "└" + "┴".join(segs) + "┘"

    def row_line(cells: list[str]) -> str:
        parts: list[str] = []
        for cell, cw in zip(cells, col_widths, strict=True):
            parts.append(" " + _pad_to_width(cell, cw) + " ")
        return "│" + "│".join(parts) + "│"

    lines = [top, row_line(norm_headers), sep]
    for r in norm_rows:
        lines.append(row_line(r))
        lines.append(sep)
    if lines[-1] == sep:
        lines.pop()
    lines.append(bot)
    return "\n".join(lines)
