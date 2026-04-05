# 说明与限制

- **PubMed 检索与 `retmax`**：一次返回多少条 PMID 由 E-utilities 的 `retmax` 控制；程序始终用 HTTPS 调 `esearch.fcgi`，与本地是否安装 `esearch` 无关。拉取文摘仍用 **`efetch`**。
- **PubMed 与语言**：索引与常用字段以英文为主；自然语言 `/find` 会尽量被模型转成英文检索式，实际命中仍以 PubMed 为准。
- **生成式检索式**：模型输出的检索式可能不精确，重要课题请核对终端打印的 **PubMed 检索式**，必要时使用 `/findraw` 或手工调整。
- **网络与合规**：综合问答与 `/find` 自然语言解析会调用百炼接口，请注意费用、配额与数据合规要求。
- **API 与 CLI 差异**：HTTP `POST /v1/pubmed/search` 与 `POST /v1/library/import` 的 `query` 均为**原文** PubMed 检索式；若需「自然语言 → 检索式」，请用 CLI 的 **`/find` / `/import`**（或 `--import-query`），或在外部调用 LLM 后再请求 API。
- **文献主题**：导入接口**不**写主题；请在入库后用 `/topic` 或 `POST /v1/library/topic` 设置。流程说明见 [命令行 CLI](cli.md) 中的「主题：仅在导入后设置」一节。

返回：[文档首页](README.md)
