from __future__ import annotations

from dataclasses import dataclass, field

from litpubmed.config import Settings
from litpubmed.db import Database, PaperRow
from litpubmed import edirect
from litpubmed.llm import LLMClient


@dataclass
class LitPubMedService:
    settings: Settings
    db: Database = field(init=False)
    llm: LLMClient = field(init=False)

    def __post_init__(self) -> None:
        self.settings.load_json_overrides()
        self.db = Database(self.settings.db_file)
        self.llm = LLMClient(self.settings)

    def search_remote(self, query: str, max_results: int = 20) -> list[dict]:
        return edirect.search_pubmed(query, max_results=max_results)

    def fetch_remote(self, pmid: str) -> dict | None:
        return edirect.fetch_pubmed_paper(pmid)

    def add_to_library(self, pmid: str) -> tuple[bool, PaperRow | None]:
        rec = self.fetch_remote(pmid)
        if not rec:
            return False, None
        pid = str(rec.get("pmid") or pmid)
        inserted = self.db.add_paper(
            pid,
            str(rec.get("title") or ""),
            str(rec.get("authors") or ""),
            rec.get("year") if isinstance(rec.get("year"), int) else None,
            str(rec.get("abstract") or ""),
        )
        row = self.db.get_by_pmid(pid)
        return inserted, row

    def import_search_results(self, query: str, max_results: int = 10) -> list[PaperRow]:
        rows: list[PaperRow] = []
        for rec in self.search_remote(query, max_results=max_results):
            pid = str(rec.get("pmid") or "")
            if not pid:
                continue
            self.db.upsert_paper(
                pid,
                str(rec.get("title") or ""),
                str(rec.get("authors") or ""),
                rec.get("year") if isinstance(rec.get("year"), int) else None,
                str(rec.get("abstract") or ""),
            )
            r = self.db.get_by_pmid(pid)
            if r:
                rows.append(r)
        return rows

    def close(self) -> None:
        self.db.close()
