from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


@dataclass
class PaperRow:
    id: int
    pmid: str
    title: str
    authors: str
    year: int | None
    abstract: str
    added_date: str
    notes: str | None
    tags: str | None
    topic: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "added_date": self.added_date,
            "notes": self.notes or "",
            "tags": self.tags or "",
            "topic": self.topic or "",
        }


class Database:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pmid TEXT UNIQUE NOT NULL,
                title TEXT,
                authors TEXT,
                year INTEGER,
                abstract TEXT,
                added_date TEXT,
                notes TEXT,
                tags TEXT
            )
            """
        )
        self.conn.commit()
        self._ensure_topic_column()

    def _ensure_topic_column(self) -> None:
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(papers)").fetchall()}
        if "topic" not in cols:
            self.conn.execute("ALTER TABLE papers ADD COLUMN topic TEXT")
            self.conn.commit()

    def add_paper(
        self,
        pmid: str,
        title: str,
        authors: str,
        year: int | None,
        abstract: str,
    ) -> bool:
        try:
            self.conn.execute(
                """
                INSERT INTO papers (pmid, title, authors, year, abstract, added_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (pmid, title, authors, year, abstract, datetime.now().isoformat()),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def upsert_paper(
        self,
        pmid: str,
        title: str,
        authors: str,
        year: int | None,
        abstract: str,
    ) -> int:
        cur = self.conn.execute("SELECT id FROM papers WHERE pmid = ?", (pmid,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        self.add_paper(pmid, title, authors, year, abstract)
        cur = self.conn.execute("SELECT id FROM papers WHERE pmid = ?", (pmid,))
        r2 = cur.fetchone()
        return int(r2[0]) if r2 else 0

    def list_papers(
        self,
        limit: int = 50,
        offset: int = 0,
        topic_substring: str | None = None,
    ) -> list[PaperRow]:
        sub = (topic_substring or "").strip()
        if sub:
            cur = self.conn.execute(
                """
                SELECT id, pmid, title, authors, year, abstract, added_date, notes, tags, topic
                FROM papers
                WHERE topic IS NOT NULL AND TRIM(topic) != ''
                  AND instr(lower(topic), lower(?)) > 0
                ORDER BY added_date DESC LIMIT ? OFFSET ?
                """,
                (sub, limit, offset),
            )
        else:
            cur = self.conn.execute(
                """
                SELECT id, pmid, title, authors, year, abstract, added_date, notes, tags, topic
                FROM papers ORDER BY added_date DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        return [self._row_to_paper(r) for r in cur.fetchall()]

    def list_topic_counts(self) -> list[tuple[str, int]]:
        cur = self.conn.execute(
            """
            SELECT topic, COUNT(*) AS c FROM papers
            WHERE topic IS NOT NULL AND TRIM(topic) != ''
            GROUP BY topic ORDER BY c DESC, topic ASC
            """
        )
        return [(str(r[0]), int(r[1])) for r in cur.fetchall()]

    def get_by_id(self, paper_id: int) -> PaperRow | None:
        cur = self.conn.execute(
            """
            SELECT id, pmid, title, authors, year, abstract, added_date, notes, tags, topic
            FROM papers WHERE id = ?
            """,
            (paper_id,),
        )
        r = cur.fetchone()
        return self._row_to_paper(r) if r else None

    def get_by_pmid(self, pmid: str) -> PaperRow | None:
        cur = self.conn.execute(
            """
            SELECT id, pmid, title, authors, year, abstract, added_date, notes, tags, topic
            FROM papers WHERE pmid = ?
            """,
            (pmid,),
        )
        r = cur.fetchone()
        return self._row_to_paper(r) if r else None

    def get_many_by_ids(self, ids: list[int]) -> list[PaperRow]:
        if not ids:
            return []
        q = ",".join("?" * len(ids))
        cur = self.conn.execute(
            f"""
            SELECT id, pmid, title, authors, year, abstract, added_date, notes, tags, topic
            FROM papers WHERE id IN ({q}) ORDER BY added_date DESC
            """,
            ids,
        )
        return [self._row_to_paper(r) for r in cur.fetchall()]

    def set_note(self, paper_id: int, note: str) -> bool:
        cur = self.conn.execute("UPDATE papers SET notes = ? WHERE id = ?", (note, paper_id))
        self.conn.commit()
        return cur.rowcount > 0

    def set_tags(self, paper_id: int, tags: str) -> bool:
        cur = self.conn.execute("UPDATE papers SET tags = ? WHERE id = ?", (tags, paper_id))
        self.conn.commit()
        return cur.rowcount > 0

    def set_topic(self, paper_id: int, topic: str) -> bool:
        cur = self.conn.execute("UPDATE papers SET topic = ? WHERE id = ?", (topic, paper_id))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_paper(self, paper_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _row_to_paper(r: sqlite3.Row) -> PaperRow:
        tv = r["topic"]
        topic = str(tv).strip() if tv is not None and str(tv).strip() else None
        return PaperRow(
            id=int(r["id"]),
            pmid=str(r["pmid"]),
            title=str(r["title"] or ""),
            authors=str(r["authors"] or ""),
            year=int(r["year"]) if r["year"] is not None else None,
            abstract=str(r["abstract"] or ""),
            added_date=str(r["added_date"] or ""),
            notes=str(r["notes"]) if r["notes"] is not None else None,
            tags=str(r["tags"]) if r["tags"] is not None else None,
            topic=topic,
        )
