from __future__ import annotations

from typing import Iterable, Iterator

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from litpubmed.config import Settings
from litpubmed.db import PaperRow
from litpubmed.synthesis_tables import format_synthesis_output


def _normalize_pubmed_query_output(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        rest = s.split("\n", 1)[1] if "\n" in s else ""
        if "```" in rest:
            rest = rest.rsplit("```", 1)[0]
        s = rest.strip()
    line = s.split("\n", 1)[0].strip()
    if len(line) >= 2 and line[0] == line[-1] and line[0] in "\"'":
        line = line[1:-1].strip()
    return line


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key or "dummy",
            base_url=settings.llm_api_base,
            timeout=settings.llm_http_timeout_seconds(),
        )

    @property
    def configured(self) -> bool:
        return bool(self._settings.llm_api_key)

    def pubmed_query_from_natural_language(self, user_text: str) -> str:
        """将自然语言（可中文）转为一条 PubMed 检索式；需已配置 API Key。"""
        if not self.configured:
            raise RuntimeError("未配置 LLM API Key")
        text = user_text.strip()
        if not text:
            raise ValueError("描述为空")
        system = (
            "你是 PubMed / Entrez 检索式助手。用户用自然语言（可为中文）描述想找的生物医学文献。\n"
            "只输出一条可直接粘贴到 PubMed 搜索框的 query：以英文关键词为主，必要时使用 AND/OR、"
            "括号与字段标签如 [ti]、[ab]、[MeSH Terms]。不要解释，不要 markdown，不要引号包裹整句，单行。"
        )
        try:
            resp = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"用户需求:\n{text}"},
                ],
                temperature=0.1,
            )
        except APITimeoutError as e:
            raise RuntimeError(
                f"LLM 请求超时（>{self._settings.llm_http_timeout_seconds():g}s）。可检查网络、代理或提高 "
                "LITPUBMED_LLM_TIMEOUT；也可使用 /findraw 跳过 LLM。"
            ) from e
        except APIConnectionError as e:
            raise RuntimeError(
                "无法连接 LLM 服务（网络或 base_url）。请检查网络与 LITPUBMED_LLM_API_BASE。"
            ) from e
        except RateLimitError as e:
            raise RuntimeError("LLM 限流，请稍后重试或检查百炼配额。") from e
        raw = (resp.choices[0].message.content or "").strip()
        q = _normalize_pubmed_query_output(raw)
        if not q:
            raise ValueError("LLM 未返回有效检索式")
        return q

    _SYNTHESIS_SYSTEM = (
        "你是生物医学文献助理。根据用户提供的 PubMed 文献信息回答问题；"
        "引用时标明文献编号与 PMID；信息不足请明确说明。\n"
        "输出将显示在终端：不要使用 Markdown（禁止 # 标题、** 粗体、` 代码块、"
        "[链接](url)、Markdown 管道表）。\n"
        "小标题可用「一、」「二、」或（1）（2）；列表可用行首 - 或 1. 2.。\n"
        "若需要**任意列数的对比表格**（含多于三列），**不要手写 ┌│┐ 等框线**（终端里中英文显示宽度不同，手写必歪）。"
        "请先在正文里写简要说明，再在单独一行起止标记之间输出**仅一行紧凑 JSON**（合法 JSON、无注释、无换行插在字符串内）：\n"
        "<<LITPUBMED_TABLE_JSON>>\n"
        '{"headers":["列1","列2","列3"],"rows":[["a","b","c"],["d","e","f"]]}\n'
        "<<END_LITPUBMED_TABLE_JSON>>\n"
        "要求：headers 与每一行 rows 的元素个数必须一致；每个单元格用**一行字符串**（长句也写在一行内，"
        "勿在 JSON 字符串里写换行符）；程序会按终端显示宽度**自动换行**并对齐框线。\n"
        "可选键 wrap_width：整数，每格内单行最大显示宽度（默认 30）；设为 0 表示不换行、整格一行（可能很宽）。\n"
        "可选键 max_cell_width：与 wrap_width 同时存在时取较小者作为换行宽度；在不换行模式下用于截断并加省略号。\n"
        "可输出多个表格块（多组上述起止标记）。程序会用显示宽度重绘为对齐的 Unicode 框线表。\n"
        "若完全不需要表格，可只用段落与列表，不要输出上述标记。"
    )

    def _synthesis_user_content(self, question: str, papers: Iterable[PaperRow], depth: str) -> str:
        blocks: list[str] = []
        for i, p in enumerate(papers, start=1):
            body = p.abstract if depth != "title_only" else ""
            top = (p.topic or "").strip()
            top_line = f"主题: {top}\n" if top else ""
            blocks.append(
                f"---\n文献 {i} (PMID {p.pmid})\n"
                f"{top_line}"
                f"标题: {p.title}\n作者: {p.authors}\n年份: {p.year}\n"
                f"摘要:\n{body}\n"
            )
        return f"用户问题:\n{question}\n\n" + "\n".join(blocks)

    def synthesize_stream(
        self, question: str, papers: Iterable[PaperRow], depth: str = "abstract"
    ) -> Iterator[str]:
        if not self.configured:
            yield (
                "未设置 API Key。请在环境中配置 DASHSCOPE_API_KEY（百炼 / DashScope）"
                "或 BAILIAN_API_KEY，也可在项目根目录使用 .env。"
            )
            return
        user = self._synthesis_user_content(question, papers, depth)
        stream = self._client.chat.completions.create(
            model=self._settings.llm_model,
            messages=[
                {"role": "system", "content": self._SYNTHESIS_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            ch = chunk.choices[0]
            delta = ch.delta
            if delta and getattr(delta, "content", None):
                yield delta.content

    def synthesize(self, question: str, papers: Iterable[PaperRow], depth: str = "abstract") -> str:
        raw = "".join(self.synthesize_stream(question, papers, depth=depth)).strip()
        return format_synthesis_output(raw)
