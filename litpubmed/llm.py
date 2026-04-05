from __future__ import annotations

from typing import Iterable, Iterator

from openai import OpenAI

from litpubmed.config import Settings
from litpubmed.db import PaperRow


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
        resp = self._client.chat.completions.create(
            model=self._settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"用户需求:\n{text}"},
            ],
            temperature=0.1,
        )
        raw = (resp.choices[0].message.content or "").strip()
        q = _normalize_pubmed_query_output(raw)
        if not q:
            raise ValueError("LLM 未返回有效检索式")
        return q

    _SYNTHESIS_SYSTEM = (
        "你是生物医学文献助理。根据用户提供的 PubMed 文献信息回答问题；"
        "引用时标明文献编号与 PMID；信息不足请明确说明。\n"
        "输出将显示在终端：请用**纯文本**排版，不要使用 Markdown（不要用 # / ## / ### 标题、"
        "不要用 ** 粗体、不要用表格线或 | 列）。小标题可用「一、」「二、」或（1）（2）；"
        "列表可用行首短横线 - 或数字 1. 2.。"
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
        return "".join(self.synthesize_stream(question, papers, depth=depth)).strip()
