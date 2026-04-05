# LitPubMed 文档

PubMed **检索**走 NCBI **E-utilities**（`esearch.fcgi`），**题录拉取**用 Entrez Direct 的 **`efetch`**；本地 **SQLite** 管理文献。可选接入 **阿里云百炼（DashScope）OpenAI 兼容接口**，实现自然语言生成 PubMed 检索式与多篇文献综合问答。

## 目录

| 文档 | 内容 |
|------|------|
| [安装与配置](setup.md) | 依赖、虚拟环境、环境变量、本地数据路径 |
| [命令行 CLI](cli.md) | 交互式命令、`/find`、导入后设置主题、综合模式 |
| [HTTP API](http-api.md) | 启动方式、鉴权、主要端点 |
| [说明与限制](notes.md) | PubMed 语言、生成式检索式、合规提示 |

从仓库根目录安装并启动后，可运行 `litpubmed`（CLI）或 `litpubmed-api`（API）。详见 [安装与配置](setup.md)。
