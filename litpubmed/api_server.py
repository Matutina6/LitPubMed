from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from litpubmed.config import Settings
from litpubmed.service import LitPubMedService

_bearer = HTTPBearer(auto_error=False)
_service: LitPubMedService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service
    s = Settings()
    s.load_json_overrides()
    _service = LitPubMedService(s)
    yield
    if _service:
        _service.close()
    _service = None


app = FastAPI(
    title="LitPubMed API",
    version="0.1.0",
    lifespan=lifespan,
    description="本地文献库与 PubMed 检索；/v1/synthesize 默认使用百炼 OpenAI 兼容模型 qwen-max（LITPUBMED_LLM_MODEL）。",
)


def get_service() -> LitPubMedService:
    if _service is None:
        raise HTTPException(503, "服务未初始化")
    return _service


def verify_token(
    creds: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
    svc: Annotated[LitPubMedService, Depends(get_service)],
) -> None:
    tok = svc.settings.api_token
    if not tok:
        return
    if creds is None or creds.credentials != tok:
        raise HTTPException(401, "无效或缺失 Bearer Token")


class SearchIn(BaseModel):
    query: str
    max_results: int = Field(default=20, ge=1, le=200)


class FetchIn(BaseModel):
    pmid: str


class AddIn(BaseModel):
    pmid: str


class ImportIn(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=100)


class SynthesizeIn(BaseModel):
    question: str
    paper_ids: list[int] = Field(default_factory=list)
    depth: Literal["abstract", "title_only"] = "abstract"


class NoteIn(BaseModel):
    paper_id: int
    text: str


class TagIn(BaseModel):
    paper_id: int
    tags: str


class TopicIn(BaseModel):
    paper_id: int
    topic: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/pubmed/search", dependencies=[Depends(verify_token)])
def api_search(body: SearchIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, Any]:
    try:
        hits = svc.search_remote(body.query, max_results=body.max_results)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    return {"results": hits}


@app.post("/v1/pubmed/fetch", dependencies=[Depends(verify_token)])
def api_fetch(body: FetchIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, Any]:
    try:
        rec = svc.fetch_remote(body.pmid.strip())
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    if not rec:
        raise HTTPException(404, "未找到该 PMID")
    return {"paper": rec}


@app.post("/v1/library/add", dependencies=[Depends(verify_token)])
def api_add(body: AddIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, Any]:
    try:
        inserted, row = svc.add_to_library(body.pmid.strip())
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    if not row:
        raise HTTPException(404, "无法拉取或解析该文献")
    return {"inserted": inserted, "paper": row.as_dict()}


@app.post("/v1/library/import", dependencies=[Depends(verify_token)])
def api_import(body: ImportIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, Any]:
    try:
        rows = svc.import_search_results(body.query, max_results=body.max_results)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    return {"count": len(rows), "papers": [r.as_dict() for r in rows]}


@app.get("/v1/library/papers", dependencies=[Depends(verify_token)])
def api_papers(
    limit: int = 50,
    offset: int = 0,
    topic: str | None = None,
    svc: LitPubMedService = Depends(get_service),
) -> dict[str, Any]:
    sub = topic.strip() if topic and topic.strip() else None
    rows = svc.db.list_papers(
        limit=min(limit, 200),
        offset=max(offset, 0),
        topic_substring=sub,
    )
    return {"papers": [r.as_dict() for r in rows]}


@app.get("/v1/library/topics", dependencies=[Depends(verify_token)])
def api_topics(svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, Any]:
    return {
        "topics": [{"name": n, "count": c} for n, c in svc.db.list_topic_counts()],
    }


@app.get("/v1/library/papers/{paper_id}", dependencies=[Depends(verify_token)])
def api_paper_one(
    paper_id: int,
    svc: Annotated[LitPubMedService, Depends(get_service)],
) -> dict[str, Any]:
    r = svc.db.get_by_id(paper_id)
    if not r:
        raise HTTPException(404, "无此 id")
    return {"paper": r.as_dict()}


@app.delete("/v1/library/papers/{paper_id}", dependencies=[Depends(verify_token)])
def api_paper_delete(
    paper_id: int,
    svc: Annotated[LitPubMedService, Depends(get_service)],
) -> dict[str, bool]:
    if not svc.db.delete_paper(paper_id):
        raise HTTPException(404, "无此 id")
    return {"ok": True}


@app.post("/v1/library/note", dependencies=[Depends(verify_token)])
def api_note(body: NoteIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, bool]:
    ok = svc.db.set_note(body.paper_id, body.text)
    if not ok:
        raise HTTPException(404, "无此 id")
    return {"ok": True}


@app.post("/v1/library/tag", dependencies=[Depends(verify_token)])
def api_tag(body: TagIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, bool]:
    ok = svc.db.set_tags(body.paper_id, body.tags)
    if not ok:
        raise HTTPException(404, "无此 id")
    return {"ok": True}


@app.post("/v1/library/topic", dependencies=[Depends(verify_token)])
def api_topic(body: TopicIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, bool]:
    ok = svc.db.set_topic(body.paper_id, body.topic)
    if not ok:
        raise HTTPException(404, "无此 id")
    return {"ok": True}


@app.post("/v1/synthesize", dependencies=[Depends(verify_token)])
def api_synthesize(body: SynthesizeIn, svc: Annotated[LitPubMedService, Depends(get_service)]) -> dict[str, str]:
    papers = svc.db.get_many_by_ids(body.paper_ids)
    if not papers:
        raise HTTPException(400, "paper_ids 为空或无效")
    try:
        text = svc.llm.synthesize(body.question, papers, depth=body.depth)
    except Exception as e:
        raise HTTPException(502, f"LLM 调用失败: {e}") from e
    return {"answer": text}


def main() -> None:
    parser = argparse.ArgumentParser(description="LitPubMed HTTP API")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    ns = parser.parse_args()
    settings = Settings()
    settings.load_json_overrides()
    host = ns.host or settings.api_host
    port = ns.port or settings.api_port
    import uvicorn

    uvicorn.run("litpubmed.api_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
