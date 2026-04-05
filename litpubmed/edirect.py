from __future__ import annotations

import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from xml.etree import ElementTree as ET

EUTILS_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(argv: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _id_list_from_esearch_xml(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    err = root.find(".//ERROR")
    if err is not None and (err.text or "").strip():
        raise RuntimeError((err.text or "").strip())
    id_list = root.find(".//IdList")
    if id_list is None:
        return []
    return [el.text.strip() for el in id_list.findall("Id") if el.text]


def esearch_pubmed_pmids(query: str, retmax: int = 20) -> list[str]:
    """返回 PubMed PMID 列表。始终走 NCBI E-utilities `esearch.fcgi`，以便稳定使用 `retmax` 控制条数。

    新版 Entrez Direct 的 `esearch` 命令行常无 `-retmax`；若去掉该参数再调本地脚本，
    则只能依赖服务端默认条数，无法保证与 `max_results` 一致。故检索步不再调用本地 `esearch`。
    """
    cap = max(1, min(int(retmax), 100_000))
    params = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": query,
            "retmax": str(cap),
            "retmode": "xml",
            "tool": "litpubmed",
        }
    )
    url = f"{EUTILS_ESEARCH}?{params}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LitPubMed/0.1 (urllib; PubMed esearch)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"PubMed esearch 失败: {e}") from e
    except OSError as e:
        raise RuntimeError(f"PubMed esearch 网络错误: {e}") from e
    return _id_list_from_esearch_xml(body)


def efetch_pubmed_medline(pmids: list[str]) -> str:
    if not pmids:
        return ""
    efetch = _which("efetch")
    if not efetch:
        raise RuntimeError("未找到 `efetch`。请安装 Entrez Direct 并加入 PATH。")
    args = [efetch, "-db", "pubmed", "-format", "medline", "-id", ",".join(pmids)]
    cp = _run(args)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"efetch 失败 (code {cp.returncode})")
    return cp.stdout


def parse_medline_records(medline: str) -> list[dict[str, Any]]:
    """Parse concatenated MEDLINE records (rough but practical)."""
    raw = medline.strip()
    if not raw:
        return []
    chunks = re.split(r"\n\n+", raw)
    out: list[dict[str, Any]] = []
    for chunk in chunks:
        rec = _parse_one_medline(chunk)
        if rec.get("pmid"):
            out.append(rec)
    return out


def _parse_one_medline(chunk: str) -> dict[str, Any]:
    pmid = ""
    title_parts: list[str] = []
    authors: list[str] = []
    year: int | None = None
    abstract_parts: list[str] = []
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal pmid, year, current, buf
        if not current:
            return
        text = " ".join(x.strip() for x in buf if x.strip())
        if current == "PMID":
            pmid = text
        elif current == "TI":
            title_parts.append(text)
        elif current == "AU":
            authors.append(text)
        elif current == "DP":
            m = re.search(r"(19|20)\d{2}", text)
            if m:
                year = int(m.group(0))
        elif current == "AB":
            abstract_parts.append(text)
        current = None
        buf = []

    for line in chunk.splitlines():
        if re.match(r"^[A-Z]{2,4}\s*-\s", line):
            flush()
            key, rest = line.split("-", 1)
            current = key.strip()
            buf = [rest.lstrip()]
        elif line.startswith("      ") and current:
            buf.append(line.strip())
        elif current:
            buf.append(line.strip())
    flush()
    return {
        "pmid": pmid,
        "title": " ".join(title_parts).strip(),
        "authors": "; ".join(authors),
        "year": year,
        "abstract": " ".join(abstract_parts).strip(),
    }


def search_pubmed(query: str, max_results: int = 20) -> list[dict[str, Any]]:
    pmids = esearch_pubmed_pmids(query, retmax=max_results)
    if not pmids:
        return []
    med = efetch_pubmed_medline(pmids)
    return parse_medline_records(med)


def fetch_pubmed_paper(pmid: str) -> dict[str, Any] | None:
    med = efetch_pubmed_medline([pmid.strip()])
    recs = parse_medline_records(med)
    return recs[0] if recs else None
