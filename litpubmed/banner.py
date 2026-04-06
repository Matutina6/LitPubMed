"""交互启动时的像素风 ANSI 标识（TTY 上色，遵守 NO_COLOR / FORCE_COLOR）。"""

from __future__ import annotations

import os
import re
import sys

from litpubmed import __version__

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _want_color() -> bool:
    if os.environ.get("NO_COLOR", "").strip():
        return False
    if os.environ.get("FORCE_COLOR", "").strip() or os.environ.get("CLICOLOR_FORCE", "").strip():
        return True
    return sys.stdout.isatty()


def _rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _norm(rows: list[str]) -> list[str]:
    w = max(len(r) for r in rows)
    return [r.ljust(w) for r in rows]


def _hjoin(
    glyphs: list[list[str]],
    colors: list[tuple[int, int, int]],
    *,
    gap: int = 2,
    color: bool = True,
) -> list[str]:
    glyphs = [_norm(g) for g in glyphs]
    h = len(glyphs[0])
    gsp = " " * gap
    out: list[str] = []
    for row in range(h):
        parts: list[str] = []
        for i, g in enumerate(glyphs):
            cell = g[row]
            if color:
                r, gr, b = colors[i % len(colors)]
                parts.append(_rgb(r, gr, b) + cell)
            else:
                parts.append(cell)
        out.append(gsp.join(parts) + (RESET if color else ""))
    return out


def _rainbow_bar(width: int) -> str:
    palette = (
        (255, 99, 132),
        (255, 159, 64),
        (255, 205, 86),
        (75, 192, 192),
        (54, 162, 235),
        (153, 102, 255),
        (201, 203, 207),
    )
    chunks: list[str] = []
    for i in range(width):
        r, g, b = palette[i % len(palette)]
        chunks.append(_rgb(r, g, b) + "█")
    return "".join(chunks) + RESET


_STRIP_ANSI = re.compile(r"\033\[[0-9;]*m")


def _visible_len(s: str) -> int:
    return len(_STRIP_ANSI.sub("", s))


def print_startup_banner(*, width: int = 52) -> None:
    """在交互 REPL 启动时打印（非 TTY 自动降级为无 ANSI）。"""
    use = _want_color()
    w = max(40, min(width, 78))

    L = ["█    ", "█    ", "█    ", "█    ", "█████"]
    I = ["█████", " ███ ", " ███ ", " ███ ", "█████"]
    T = ["█████", "  █  ", "  █  ", "  █  ", "  █  "]
    P = ["████ ", "█   █", "████ ", "█    ", "█    "]
    U = ["█   █", "█   █", "█   █", "█   █", " ███ "]
    B = ["████ ", "█   █", "████ ", "█   █", "████ "]
    M = ["█   █", "██ ██", "█ █ █", "█   █", "█   █"]
    E = ["█████", "█    ", "████ ", "█    ", "█████"]
    D = ["████ ", "█   █", "█   █", "█   █", "████ "]

    candy = [
        (0, 212, 255),
        (255, 105, 180),
        (255, 230, 109),
        (94, 234, 212),
        (167, 139, 250),
        (251, 191, 36),
        (52, 211, 153),
        (96, 165, 250),
        (244, 114, 182),
    ]

    row_lit = _hjoin([L, I, T], candy[:3], gap=3, color=use)
    row_pub = _hjoin([P, U, B], candy[3:6], gap=3, color=use)
    row_med = _hjoin([M, E, D], candy[6:9], gap=3, color=use)

    logo_lines = [row_lit[i] + "  " + row_pub[i] + "  " + row_med[i] for i in range(5)]

    title_plain = f"LitPubMed  v{__version__}"
    sub_parts_plain = "PubMed · edirect · Qwen"

    if not use:
        bar = "═" * w
        print()
        print(bar)
        for line in logo_lines:
            print("  " + line)
        print(f"  {title_plain}")
        print(f"  {sub_parts_plain}")
        print(bar)
        print()
        return

    title = f"{BOLD}{_rgb(248, 248, 242)}{title_plain}{RESET}"
    sub = (
        f"{DIM}{_rgb(130, 170, 255)}PubMed{RESET}"
        f"{_rgb(68, 71, 90)} · {RESET}"
        f"{DIM}{_rgb(189, 147, 249)}edirect{RESET}"
        f"{_rgb(68, 71, 90)} · {RESET}"
        f"{DIM}{_rgb(241, 250, 140)}Qwen{RESET}"
    )

    max_logo = max(_visible_len(l) for l in logo_lines)
    max_text = max(_visible_len(title), _visible_len(sub))
    w = max(w, max_logo + 4, max_text + 4)
    inner_w = w - 2

    def _framed_row(text: str) -> str:
        pad = max(0, (inner_w - _visible_len(text)) // 2)
        row = " " * pad + text
        tail = max(0, inner_w - _visible_len(row))
        return row + " " * tail

    c_frame = _rgb(98, 114, 164)
    c_glow = _rgb(68, 71, 90)

    bar_line = _rainbow_bar(w)
    top = c_frame + "╭" + "─" * (w - 2) + "╮" + RESET
    bot = c_frame + "╰" + "─" * (w - 2) + "╯" + RESET

    print()
    print(bar_line)
    print(top)
    for line in logo_lines:
        print(c_frame + "│" + RESET + _framed_row(line) + c_frame + "│" + RESET)
    print(c_frame + "│" + RESET + _framed_row(title) + c_frame + "│" + RESET)
    print(c_frame + "│" + RESET + _framed_row(sub) + c_frame + "│" + RESET)
    print(c_glow + "│" + RESET + " " * inner_w + c_glow + "│" + RESET)
    print(bot)
    print(bar_line)
    print()
