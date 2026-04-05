from __future__ import annotations

import argparse
import shlex
import sys
from typing import List

from litpubmed.config import Settings
from litpubmed.service import LitPubMedService


def _resolve_query_with_optional_llm(svc: LitPubMedService, q_in: str, *, what: str) -> str:
    """what: 用于失败提示，如「检索」或「导入」。"""
    q = q_in
    if svc.llm.configured:
        try:
            q = svc.llm.pubmed_query_from_natural_language(q_in)
        except Exception as e:
            print(f"LLM 解析失败: {e}")
            print(f"已按原文{what}。")
    return q


def _print_paper_short(p: dict) -> None:
    top = (p.get("topic") or "").strip()
    mark = f"「{top[:40]}」 " if top else ""
    print(f"  [{p.get('id', '-')}] {mark}PMID {p.get('pmid')} — {p.get('title', '')[:120]}")


def _cmd_help() -> None:
    print(
        """
命令:
  /help                 帮助
  /find <描述>          PubMed 检索（已配置 LLM 时先将自然语言转为检索式；否则原文检索）
  /findraw <query>      直接按 PubMed 检索式检索，不经过 LLM
  /import <描述或检索式> [n]  导入（已配置 LLM 时先将自然语言转为检索式，与 /find 一致）
  /importraw <query> [n]      按原文 PubMed 检索式导入，不经过 LLM
  /add <pmid>           按 PMID 拉取并加入库
  /papers [n] [topic <关键字>]  列出文献；可选按主题字段子串筛选（不区分大小写）
  /topics               列出已分配主题及文献条数
  /topic <id> <text>    设置主题（用于分桶管理，如「T2DM-综述」）
  /show <id>            查看库内条目详情
  /rm <id> [id ...]     从本地库删除文献（数据库 id，可多条）
  /note <id> <text>     笔记
  /tag <id> <tags>      标签（自由关键词，与主题独立）
  /select <id,...>      为综合模式选择文献（数据库 id）
  /mode normal|synthesis 切换模式
  /depth abstract|title_only  传给模型的正文深度
  /config show | set model <m> | set base <url> | save
  /quit 或 /exit        退出

综合模式 (synthesis) 下直接输入问题，将基于 /select 的文献调用 LLM。
默认模型: qwen-max（百炼 DashScope OpenAI 兼容）；可用环境变量 LITPUBMED_LLM_MODEL
或 /config set model <id> 后 /config save 修改。
"""
    )


def run_repl(svc: LitPubMedService) -> None:
    try:
        import readline  # noqa: F401
    except ImportError:
        pass

    s = svc.settings
    print(
        f"LLM: {s.llm_model} @ {s.llm_api_base}（/config show；"
        f"综合模式与 /find 自然语言解析依赖 API Key）"
    )

    mode = "normal"
    depth = "abstract"
    selected_ids: List[int] = []
    prompt_normal = "litpubmed> "
    prompt_synth = "synthesis ▸ "

    while True:
        try:
            line = input(prompt_synth if mode == "synthesis" else prompt_normal).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit", "exit", "quit"):
            break

        if line.startswith("/"):
            parts = shlex.split(line)
            cmd = parts[0].lower()
            args = parts[1:]
        else:
            if mode == "synthesis":
                if not selected_ids:
                    print("请先用 /select 选择库内文献。")
                    continue
                papers = svc.db.get_many_by_ids(selected_ids)
                if not papers:
                    print("所选 id 无效。")
                    continue
                try:
                    for piece in svc.llm.synthesize_stream(line, papers, depth=depth):
                        print(piece, end="", flush=True)
                    print()
                except Exception as e:
                    print(f"LLM 错误: {e}")
                continue
            print("未知命令。输入 /help")
            continue

        try:
            if cmd == "/help":
                _cmd_help()
            elif cmd == "/find":
                if not args:
                    print("用法: /find <自然语言或检索式>")
                    continue
                q_in = " ".join(args)
                q = _resolve_query_with_optional_llm(svc, q_in, what="检索")
                print(f"PubMed 检索式: {q}")
                hits = svc.search_remote(q, max_results=15)
                for h in hits:
                    print(f"  PMID {h.get('pmid')} — {h.get('title', '')[:100]}")
                if not hits:
                    print("无结果。")
            elif cmd == "/findraw":
                if not args:
                    print("用法: /findraw <query>")
                    continue
                q = " ".join(args)
                print(f"PubMed 检索式: {q}")
                hits = svc.search_remote(q, max_results=15)
                for h in hits:
                    print(f"  PMID {h.get('pmid')} — {h.get('title', '')[:100]}")
                if not hits:
                    print("无结果。")
            elif cmd == "/import":
                if not args:
                    print("用法: /import <自然语言或检索式> [n]")
                    continue
                n = 10
                if args[-1].isdigit():
                    n = int(args[-1])
                    q_in = " ".join(args[:-1])
                else:
                    q_in = " ".join(args)
                q = _resolve_query_with_optional_llm(svc, q_in, what="导入")
                print(f"PubMed 检索式: {q}")
                rows = svc.import_search_results(q, max_results=n)
                print(f"已导入/更新 {len(rows)} 条。")
                for r in rows[:20]:
                    _print_paper_short(r.as_dict())
            elif cmd == "/importraw":
                if not args:
                    print("用法: /importraw <PubMed检索式> [n]")
                    continue
                n = 10
                if args[-1].isdigit():
                    n = int(args[-1])
                    q = " ".join(args[:-1])
                else:
                    q = " ".join(args)
                print(f"PubMed 检索式: {q}")
                rows = svc.import_search_results(q, max_results=n)
                print(f"已导入/更新 {len(rows)} 条。")
                for r in rows[:20]:
                    _print_paper_short(r.as_dict())
            elif cmd == "/add":
                if not args:
                    print("用法: /add <pmid>")
                    continue
                ins, row = svc.add_to_library(args[0])
                if row:
                    print(("已添加: " if ins else "已在库中: ") + f"PMID {row.pmid} id={row.id}")
                else:
                    print("拉取失败，检查 PMID、网络与 PATH 中的 efetch。")
            elif cmd == "/papers":
                lim = 20
                topic_sub: str | None = None
                i = 0
                if args and args[0].isdigit():
                    lim = int(args[0])
                    i = 1
                if i < len(args) and args[i].lower() == "topic":
                    rest = " ".join(args[i + 1 :]).strip()
                    if not rest:
                        print("用法: /papers [n] topic <主题子串>")
                        continue
                    topic_sub = rest
                elif i < len(args):
                    print("用法: /papers [n] [topic <主题子串>]")
                    continue
                rows = svc.db.list_papers(limit=lim, topic_substring=topic_sub)
                for r in rows:
                    _print_paper_short(r.as_dict())
                if topic_sub and not rows:
                    print("(无匹配主题子串的文献。)")
            elif cmd == "/topics":
                rows = svc.db.list_topic_counts()
                if not rows:
                    print("尚无已分配主题。使用 /topic <id> <名称> 设置。")
                else:
                    for name, c in rows:
                        print(f"  {c:4d}  {name}")
            elif cmd == "/topic":
                if len(args) < 2 or not args[0].isdigit():
                    print("用法: /topic <id> <主题名称>")
                    continue
                pid = int(args[0])
                text = " ".join(args[1:])
                if svc.db.set_topic(pid, text):
                    print("已保存主题。")
                else:
                    print("无此 id。")
            elif cmd == "/rm":
                if not args:
                    print("用法: /rm <id> [id ...]（数据库 id，见 /papers）")
                    continue
                ids_rm: List[int] = []
                for a in args:
                    if a.isdigit():
                        ids_rm.append(int(a))
                    else:
                        print(f"跳过非数字参数: {a}")
                if not ids_rm:
                    print("未指定有效 id。")
                    continue
                n_ok = 0
                missing: List[int] = []
                deleted_ids: set[int] = set()
                for pid in ids_rm:
                    if svc.db.delete_paper(pid):
                        n_ok += 1
                        deleted_ids.add(pid)
                    else:
                        missing.append(pid)
                print(f"已删除 {n_ok} 条。")
                if missing:
                    print("无此 id（未删除）:", ", ".join(str(x) for x in missing))
                if deleted_ids:
                    selected_ids = [x for x in selected_ids if x not in deleted_ids]
            elif cmd == "/show":
                if not args or not args[0].isdigit():
                    print("用法: /show <id>")
                    continue
                r = svc.db.get_by_id(int(args[0]))
                if not r:
                    print("无此 id。")
                    continue
                d = r.as_dict()
                for k in ("id", "pmid", "title", "authors", "year", "topic", "tags", "notes"):
                    print(f"{k}: {d.get(k)}")
                print("abstract:\n", d.get("abstract", ""))
            elif cmd == "/note":
                if len(args) < 2 or not args[0].isdigit():
                    print("用法: /note <id> <text>")
                    continue
                pid = int(args[0])
                text = " ".join(args[1:])
                if svc.db.set_note(pid, text):
                    print("已保存笔记。")
                else:
                    print("无此 id。")
            elif cmd == "/tag":
                if len(args) < 2 or not args[0].isdigit():
                    print("用法: /tag <id> <tags>")
                    continue
                pid = int(args[0])
                tags = " ".join(args[1:])
                if svc.db.set_tags(pid, tags):
                    print("已保存标签。")
                else:
                    print("无此 id。")
            elif cmd == "/select":
                if not args:
                    print("用法: /select <id,id,...>")
                    continue
                ids: List[int] = []
                for chunk in " ".join(args).replace(",", " ").split():
                    if chunk.isdigit():
                        ids.append(int(chunk))
                selected_ids = ids
                print("已选择:", selected_ids)
            elif cmd == "/mode":
                if not args:
                    print("用法: /mode normal|synthesis")
                    continue
                m = args[0].lower()
                if m == "synthesis":
                    mode = "synthesis"
                    print("进入综合模式。")
                elif m == "normal":
                    mode = "normal"
                    print("返回常规模式。")
                else:
                    print("模式应为 normal 或 synthesis。")
            elif cmd == "/depth":
                if not args:
                    print("用法: /depth abstract|title_only")
                    continue
                d = args[0].lower()
                if d in ("abstract", "title_only"):
                    depth = d
                    print("depth =", depth)
                else:
                    print("不支持该深度。")
            elif cmd == "/config":
                if not args or args[0] == "show":
                    svc.settings.load_json_overrides()
                    print("model:", svc.settings.llm_model)
                    print("base:", svc.settings.llm_api_base)
                    print("api_key:", "[SET]" if svc.settings.llm_api_key else "[NOT SET]")
                elif args[0] == "set" and len(args) >= 3:
                    if args[1] == "model":
                        svc.settings.llm_model = args[2]
                        print("model ->", svc.settings.llm_model)
                    elif args[1] == "base":
                        svc.settings.llm_api_base = args[2]
                        print("base ->", svc.settings.llm_api_base)
                    else:
                        print("未知项，使用 model 或 base。")
                elif args[0] == "save":
                    svc.settings.save_json()
                    print("已写入", svc.settings.config_file)
                else:
                    print("用法: /config show | set model <m> | set base <url> | save")
            else:
                print("未知命令，/help 查看帮助。")
        except RuntimeError as e:
            print(str(e))
        except Exception as e:
            print(f"错误: {e}")


def main() -> None:
    p = argparse.ArgumentParser(
        prog="litpubmed",
        description="LitPubMed CLI（综合问答默认 qwen-max，百炼 OpenAI 兼容；见 LITPUBMED_LLM_MODEL）",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "--find",
        metavar="QUERY",
        help="单次检索后退出（已配置 LLM 时先将自然语言转为 PubMed 检索式）",
    )
    g.add_argument(
        "--find-raw",
        metavar="QUERY",
        help="单次检索后退出（原文 PubMed 检索式，不经过 LLM）",
    )
    ig = p.add_mutually_exclusive_group()
    ig.add_argument(
        "--import-query",
        metavar="QUERY",
        help="检索并导入后退出（已配置 LLM 时先将自然语言转为 PubMed 检索式）",
    )
    ig.add_argument(
        "--import-query-raw",
        metavar="QUERY",
        help="检索并导入后退出（原文 PubMed 检索式，不经过 LLM）",
    )
    p.add_argument("--max", type=int, default=15, help="检索/导入最大条数（默认 15）")
    args = p.parse_args()

    settings = Settings()
    settings.load_json_overrides()
    svc = LitPubMedService(settings)
    try:
        if args.find_raw:
            q = args.find_raw
            print(f"PubMed 检索式: {q}")
            for h in svc.search_remote(q, max_results=args.max):
                print(f"PMID {h.get('pmid')}\t{h.get('title', '')}")
            return
        if args.find:
            q_in = args.find
            q = q_in
            if svc.llm.configured:
                try:
                    q = svc.llm.pubmed_query_from_natural_language(q_in)
                except Exception as e:
                    print(f"LLM 解析失败: {e}", file=sys.stderr)
                    print("已按原文检索。", file=sys.stderr)
            print(f"PubMed 检索式: {q}")
            for h in svc.search_remote(q, max_results=args.max):
                print(f"PMID {h.get('pmid')}\t{h.get('title', '')}")
            return
        if args.import_query_raw:
            q = args.import_query_raw
            print(f"PubMed 检索式: {q}")
            rows = svc.import_search_results(q, max_results=args.max)
            print(f"导入 {len(rows)} 条。")
            return
        if args.import_query:
            q_in = args.import_query
            q = _resolve_query_with_optional_llm(svc, q_in, what="导入")
            print(f"PubMed 检索式: {q}")
            rows = svc.import_search_results(q, max_results=args.max)
            print(f"导入 {len(rows)} 条。")
            return
        run_repl(svc)
    finally:
        svc.close()


if __name__ == "__main__":
    main()
