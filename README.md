# LitPubMed

PubMed 检索（NCBI E-utilities）、题录拉取（`efetch`）、本地 SQLite 文献库，以及可选的百炼（DashScope）OpenAI 兼容模型：**自然语言生成 PubMed 检索式**、**多篇文献综合问答**。

## 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # 填入 DASHSCOPE_API_KEY 等（可选，见文档）
litpubmed
```

完整说明见 **[文档目录](docs/README.md)**。

## 文档

| 链接 | 内容 |
|------|------|
| [docs/README.md](docs/README.md) | 总览与导航 |
| [docs/setup.md](docs/setup.md) | 安装、环境变量、数据路径 |
| [docs/cli.md](docs/cli.md) | 命令行与 `/find`、综合模式 |
| [docs/http-api.md](docs/http-api.md) | HTTP API |
| [docs/notes.md](docs/notes.md) | 限制与注意事项 |
