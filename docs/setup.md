# 安装与配置

## 依赖

| 项目 | 说明 |
|------|------|
| Python | 3.10 及以上 |
| Entrez Direct | 仅需 **`efetch`** 拉取 MEDLINE；**PubMed 检索（PMID 列表）** 由程序通过 NCBI **E-utilities HTTPS** `esearch.fcgi` 完成（需能访问外网），不依赖本地 `esearch`。（[NCBI 安装说明](https://www.ncbi.nlm.nih.gov/books/NBK179288/)） |
| 百炼 API Key | 可选；不设 Key 时仍可做 PubMed 检索与入库，但 **无** 自然语言 `/find` 解析与综合问答 |

## 确认 `efetch` 可用

在终端执行：

```bash
which efetch
efetch
```

- 若出现 **`ERROR: Missing -db argument`**：说明已找到 NCBI 的 `efetch`，只是未带参数，**属于正常**；LitPubMed 运行时会自动传入 `-db pubmed` 等。
- 若出现 **`command not found`**：说明 PATH 未包含 edirect 目录，或命令名拼错（应为 **`efetch`**，不是 `efecth`）。

可选试拉一条 MEDLINE（将 `40866916` 换成任意真实 PMID）：

```bash
efetch -db pubmed -id 40866916 -format medline | head -20
```

## 安装

在项目根目录（建议使用虚拟环境）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -e ".[dev]"
```

WSL / Linux 下一键脚本：

```bash
bash scripts/setup_venv.sh
```

安装后可用入口：

- `litpubmed`：命令行交互或一次性检索/导入
- `litpubmed-api`：HTTP 服务

## 环境变量

复制仓库根目录的 `.env.example` 为 `.env` 并按需填写。程序会在启动时 `load_dotenv()` 加载项目根目录下的 `.env`。

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` / `BAILIAN_API_KEY` / `LITPUBMED_LLM_API_KEY` | 百炼密钥（任选其一） |
| `LITPUBMED_LLM_MODEL` | 模型 id，默认 `qwen-max` |
| `LITPUBMED_LLM_API_BASE` | OpenAI 兼容 endpoint，默认北京兼容地址 |
| `LITPUBMED_API_TOKEN` | 若设置，则 HTTP API 需携带 `Authorization: Bearer <token>` |
| `LITPUBMED_API_HOST` / `LITPUBMED_API_PORT` | API 监听地址与端口（默认 `127.0.0.1:8765`） |

修改 Key 或部分环境变量后需 **重新启动** 进程。

模型与 base 还可通过 CLI `/config set` + `/config save` 写入 `~/.litpubmed/config.json`；**API Key 仅能通过环境变量或 `.env` 配置**。

## 本地数据与配置

| 路径 | 内容 |
|------|------|
| `~/.litpubmed/litpubmed.db` | 文献库 |
| `~/.litpubmed/config.json` | 持久化的 `llm_model`、`llm_api_base` |

返回：[文档首页](README.md)
