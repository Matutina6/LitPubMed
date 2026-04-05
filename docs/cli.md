# 命令行 CLI

## 启动交互式界面

```bash
litpubmed
```

启动后会显示当前 LLM 模型与 API base；输入 `/help` 查看内置命令摘要。

## 非交互（一次性）

```bash
# 检索后退出（已配置 LLM 时先将输入视为自然语言并生成 PubMed 检索式）
litpubmed --find "近五年糖尿病肾病临床试验" --max 15

# 原文 PubMed 检索式，不经过 LLM
litpubmed --find-raw "diabetes mellitus[MeSH] AND kidney[ti]" --max 15

# 检索并导入（已配置 LLM 时先将自然语言转为 PubMed 检索式；不设置主题）
litpubmed --import-query "近五年高血压综述" --max 20

# 按原文 PubMed 检索式导入，不经过 LLM
litpubmed --import-query-raw "hypertension[ti] AND review[pt]" --max 20
```

`--find` 与 `--find-raw` 互斥；`--import-query` 与 `--import-query-raw` 互斥。

## 交互命令要点

| 命令 | 说明 |
|------|------|
| `/find <描述>` | 已配置 LLM 时，将自然语言（可中文）转为 PubMed 检索式并打印，再检索；未配置 Key 时整段当作检索式。LLM 失败时回退为原文检索。 |
| `/findraw <query>` | 始终按原文 PubMed 检索式检索，不调用 LLM。 |
| `/import <描述或检索式> [n]` | 与 **`/find` 相同**：已配置 LLM 时先将自然语言转为 PubMed 检索式并**打印**，再导入；未配置 Key 或 LLM 失败时整段当作检索式。末尾可选 `n`（默认 10）。**不设置主题**（见下节）。 |
| `/importraw <query> [n]` | 始终按**原文** PubMed 检索式导入，不调用 LLM。 |
| `/add <PMID>` | 按 PMID 单条入库。**不设置主题**。 |
| `/topic <id> <名称>` | 为文献设置**主题**（用于分课题/项目归档，如 `T2DM-综述`）。 |
| `/topics` | 列出当前库中已出现的主题及条数。 |
| `/papers [n] [topic <子串>]` | 浏览文献；可选 **按主题字段子串筛选**（不区分大小写，如 `topic 糖尿病`）。 |
| `/show <id>` | 查看详情（含 `topic`）；id 为 **数据库主键**，非 PMID。 |
| `/rm <id> [id ...]` | 从本地库**永久删除**文献（同上，用 `/papers` 里的 id；可一次删多条）。 |
| `/note <id> <文本>` | 笔记。 |
| `/tag <id> <文本>` | 自由**标签**，与主题独立（可混用：主题管分桶，标签管关键词）。 |
| `/select <id,...>` | 为综合模式选择文献。 |
| `/mode normal\|synthesis` | 切换普通 / 综合模式。 |
| `/depth abstract\|title_only` | 综合模式下送入模型的正文深度。 |
| `/config` | `show` / `set model` / `set base` / `save`。 |

## 主题：仅在导入后设置

本工具**刻意不把主题绑在导入命令上**：`/import`、`/add` 以及 `litpubmed --import-query` 入库时**不会**写入主题，新文献的 `topic` 为空，直到你手动分配。

推荐流程：

1. `/import …` 或 `/add …` 完成入库；  
2. `/papers` 查看 **`[id]`**（数据库主键）；  
3. `/topic <id> <名称>` 按篇或按批设置（可多次执行）；  
4. 用 `/topics` 看全局分布，用 `/papers topic <子串>` 按主题筛选。

主题与 **`/tag` 标签**独立：主题适合课题/项目分桶，标签适合自由关键词。

## 综合模式（多篇文献问答）

1. `/papers` 查看库内 **id**  
2. `/select 1,2,3`  
3. `/mode synthesis`  
4. 直接输入问题（**不要**以 `/` 开头），基于所选文献调用 LLM；回答在终端**流式逐字输出**，并尽量使用纯文本排版（少用 Markdown 标题/表格）。  

可选：`/depth abstract`（默认，含摘要）或 `/depth title_only`（仅标题等，省 token）。

## 检索式与引号

`/find`、`/findraw` 等经 `shlex` 解析。多词可直接空格分隔；含特殊结构时可用英文双引号包裹整段检索式。

返回：[文档首页](README.md)
