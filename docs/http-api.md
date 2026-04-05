# HTTP API

## 启动

```bash
litpubmed-api
```

可选参数：

```bash
litpubmed-api --host 0.0.0.0 --port 8765
```

默认监听见环境变量 `LITPUBMED_API_HOST`、`LITPUBMED_API_PORT`（一般为 `127.0.0.1:8765`）。

## 鉴权

- **`GET /health`**：健康检查，无需 Token。
- 若设置了 `LITPUBMED_API_TOKEN`，其余业务接口需在请求头携带：`Authorization: Bearer <token>`。
- 未设置 `LITPUBMED_API_TOKEN` 时，业务接口不校验 Bearer。

## 主要端点

实现细节与请求体字段见源码 `litpubmed/api_server.py`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/v1/pubmed/search` | body 为 **已构造好的** PubMed `query`（**不**经过 LLM 自然语言解析） |
| POST | `/v1/pubmed/fetch` | 按 PMID 拉取 |
| POST | `/v1/library/add` | 按 PMID 加入库（**不**写入主题） |
| POST | `/v1/library/import` | 按检索式导入（**不**写入主题；导入后用 `POST /v1/library/topic`） |
| GET | `/v1/library/papers` | 列表；查询参数 `topic` 可选，为主题子串筛选 |
| GET | `/v1/library/topics` | 已分配主题及条数 |
| GET | `/v1/library/papers/{id}` | 单条（`paper` 中含 `topic`） |
| DELETE | `/v1/library/papers/{id}` | 从本地库删除该条 |
| POST | `/v1/library/note` | 笔记 |
| POST | `/v1/library/tag` | 标签 |
| POST | `/v1/library/topic` | body：`paper_id`、`topic` |
| POST | `/v1/synthesize` | 基于库内 `paper_ids` 与 `question` 调用 LLM |

## 主题与导入

`POST /v1/library/import` 与 `POST /v1/library/add` 的响应里带有每条文献的 **`id`**（库内主键）。**主题不在导入接口中设置**，请在导入成功后调用 **`POST /v1/library/topic`**（`paper_id` + `topic`）。汇总与筛选用 **`GET /v1/library/topics`**、`GET /v1/library/papers?topic=...`。

## OpenAPI

服务启动后可在浏览器打开 **`/docs`** 查看交互式 OpenAPI 文档。

返回：[文档首页](README.md)
