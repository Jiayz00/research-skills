#!/usr/bin/env python3
"""Multi-source scholarly search with no third-party dependencies.

The script queries public scholarly APIs independently, normalizes the
results, deduplicates by DOI/arXiv ID/PMID/normalized title, and emits JSON,
Markdown, or BibTeX. A failing source is reported but never discards results
from the other sources.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


USER_AGENT = "research-skills/1.0"
DEFAULT_SOURCES = ("openalex", "crossref", "arxiv", "pubmed")
SOURCE_CHOICES = ("openalex", "crossref", "arxiv", "pubmed", "biorxiv")
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class SourceError(RuntimeError):
    """Raised when one scholarly source cannot return usable records."""


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def year_from_text(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    match = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", str(value))
    return int(match.group(1)) if match else None


def normalize_doi(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.strip()


def normalize_arxiv_id(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    text = text.replace("http://arxiv.org/abs/", "").replace("https://arxiv.org/abs/", "")
    text = text.replace("arXiv:", "").strip()
    text = re.sub(r"v\d+$", "", text, flags=re.IGNORECASE)
    return text


def normalize_title(value: Any) -> str:
    if not value:
        return ""
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def request_text(url: str, timeout: float, mailto: Optional[str] = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if mailto:
        headers["User-Agent"] = f"{USER_AGENT} (mailto:{mailto})"
    last_error: Optional[BaseException] = None
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1.0)
                continue
            raise SourceError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.5)
                continue
            raise SourceError(f"network error for {url}: {exc}") from exc
    raise SourceError(f"request failed for {url}: {last_error}")


def request_json(url: str, timeout: float, mailto: Optional[str] = None) -> Any:
    text = request_text(url, timeout, mailto)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceError(f"invalid JSON from {url}") from exc


def request_xml(url: str, timeout: float, mailto: Optional[str] = None) -> ET.Element:
    text = request_text(url, timeout, mailto)
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise SourceError(f"invalid XML from {url}") from exc


def make_record(
    source: str,
    *,
    title: Any = "",
    authors: Optional[Sequence[Any]] = None,
    year: Any = None,
    venue: Any = "",
    doi: Any = "",
    arxiv_id: Any = "",
    pmid: Any = "",
    abstract: Any = "",
    url: Any = "",
    pdf_url: Any = "",
    citation_count: Any = None,
    source_rank: Optional[int] = None,
) -> Dict[str, Any]:
    normalized_doi = normalize_doi(doi)
    normalized_arxiv = normalize_arxiv_id(arxiv_id)
    if not normalized_arxiv and normalized_doi.startswith("10.48550/arxiv."):
        normalized_arxiv = normalize_arxiv_id(normalized_doi.split("10.48550/arxiv.", 1)[1])
    return {
        "source": source,
        "source_rank": source_rank,
        "title": clean_text(title),
        "authors": [clean_text(author) for author in (authors or []) if clean_text(author)],
        "year": safe_int(year) or year_from_text(year),
        "venue": clean_text(venue),
        "doi": normalized_doi,
        "arxiv_id": normalized_arxiv,
        "pmid": clean_text(pmid),
        "abstract": clean_text(abstract),
        "url": clean_text(url),
        "pdf_url": clean_text(pdf_url),
        "citation_count": safe_int(citation_count),
    }


def openalex_abstract(index: Any) -> str:
    if not isinstance(index, dict):
        return ""
    positions: List[Tuple[int, str]] = []
    for word, locations in index.items():
        if isinstance(locations, list):
            for position in locations:
                if isinstance(position, int):
                    positions.append((position, word))
    positions.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positions)


def search_openalex(
    query: str,
    limit: int,
    from_year: Optional[int],
    to_year: Optional[int],
    rank: str,
    timeout: float,
    mailto: Optional[str] = None,
    extra_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filters: List[str] = []
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    if extra_filter:
        filters.append(extra_filter)
    params: Dict[str, str] = {
        "search": query,
        "per-page": str(max(1, min(limit, 50))),
    }
    if filters:
        params["filter"] = ",".join(filters)
    if mailto:
        params["mailto"] = mailto
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    payload = request_json(url, timeout, mailto)
    records: List[Dict[str, Any]] = []
    for position, item in enumerate(payload.get("results", []) or [], start=1):
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "")).lower()
        item_title = clean_text(item.get("title") or item.get("display_name") or "")
        if item_type in {"peer-review", "editorial"} or re.match(r"^\s*review\s+of\s*:", item_title, re.IGNORECASE):
            continue
        source = item.get("primary_location") or {}
        source_info = source.get("source") or {}
        authors = [
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in (item.get("authorships") or [])
            if isinstance(authorship, dict)
        ]
        locations = [source]
        locations.extend(item.get("locations") or [])
        if item.get("best_oa_location"):
            locations.append(item["best_oa_location"])
        arxiv_id = ""
        arxiv_pdf = ""
        arxiv_landing = ""
        for location in locations:
            if not isinstance(location, dict):
                continue
            for candidate in (location.get("pdf_url"), location.get("landing_page_url"), location.get("id")):
                if not candidate:
                    continue
                candidate_text = str(candidate)
                match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", candidate_text, re.IGNORECASE)
                if not match:
                    continue
                if not arxiv_id:
                    arxiv_id = normalize_arxiv_id(match.group(1))
                if "pdf" in candidate_text.lower() and not arxiv_pdf:
                    arxiv_pdf = candidate_text
                if "abs" in candidate_text.lower() and not arxiv_landing:
                    arxiv_landing = candidate_text
        best_oa = item.get("best_oa_location") or {}
        records.append(
            make_record(
                "openalex",
                title=item_title,
                authors=authors,
                year=item.get("publication_year"),
                venue=source_info.get("display_name", ""),
                doi=item.get("doi", ""),
                arxiv_id=arxiv_id,
                abstract=openalex_abstract(item.get("abstract_inverted_index")),
                url=first_present(arxiv_landing, item.get("doi"), source.get("landing_page_url"), item.get("id"), ""),
                pdf_url=first_present(arxiv_pdf, best_oa.get("pdf_url"), source.get("pdf_url"), ""),
                citation_count=item.get("cited_by_count"),
                source_rank=position,
            )
        )
    return records


def search_crossref(
    query: str,
    limit: int,
    from_year: Optional[int],
    to_year: Optional[int],
    rank: str,
    timeout: float,
    mailto: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filters: List[str] = []
    if from_year:
        filters.append(f"from-pub-date:{from_year}-01-01")
    if to_year:
        filters.append(f"until-pub-date:{to_year}-12-31")
    params: Dict[str, str] = {
        "query.bibliographic": query,
        "rows": str(max(1, min(limit, 50))),
    }
    if filters:
        params["filter"] = ",".join(filters)
    if mailto:
        params["mailto"] = mailto
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    payload = request_json(url, timeout, mailto)
    items = ((payload.get("message") or {}).get("items") or [])
    records: List[Dict[str, Any]] = []
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        titles = item.get("title") or []
        candidate_title = titles[0] if titles else ""
        if re.match(r"^\s*review\s+of\s*:", candidate_title, re.IGNORECASE):
            continue
        if str(item.get("type", "")).lower() == "peer-review":
            continue
        authors: List[str] = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
            authors.append(name or author.get("name", ""))
        issued = (item.get("issued") or {}).get("date-parts") or []
        year = issued[0][0] if issued and issued[0] else None
        containers = item.get("container-title") or []
        links = item.get("link") or []
        pdf_url = ""
        for link in links:
            if isinstance(link, dict) and "pdf" in str(link.get("content-type", "")).lower():
                pdf_url = link.get("URL", "")
                break
        records.append(
            make_record(
                "crossref",
                title=candidate_title,
                authors=authors,
                year=year,
                venue=containers[0] if containers else "",
                doi=item.get("DOI", ""),
                abstract=item.get("abstract", ""),
                url=item.get("URL", ""),
                pdf_url=pdf_url,
                citation_count=item.get("is-referenced-by-count"),
                source_rank=position,
            )
        )
    return records


def search_arxiv(
    query: str,
    limit: int,
    from_year: Optional[int],
    to_year: Optional[int],
    rank: str,
    timeout: float,
    mailto: Optional[str] = None,
) -> List[Dict[str, Any]]:
    date_clause = ""
    if from_year or to_year:
        start = f"{from_year or 1991}01010000"
        end = f"{to_year or 2099}12312359"
        date_clause = f" AND submittedDate:[{start} TO {end}]"
    search_query = f'all:"{query}"{date_clause}'
    params = {
        "search_query": search_query,
        "start": "0",
        "max_results": str(max(1, min(limit, 50))),
        "sortBy": "submittedDate" if rank == "recency" else "relevance",
        "sortOrder": "descending" if rank == "recency" else "ascending",
    }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    root = request_xml(url, timeout, mailto)
    records: List[Dict[str, Any]] = []
    for position, entry in enumerate(root.findall(f"{ATOM_NS}entry"), start=1):
        title = clean_text(entry.findtext(f"{ATOM_NS}title", default=""))
        summary = clean_text(entry.findtext(f"{ATOM_NS}summary", default=""))
        published = entry.findtext(f"{ATOM_NS}published", default="")
        updated = entry.findtext(f"{ATOM_NS}updated", default="")
        authors = [
            clean_text(author.findtext(f"{ATOM_NS}name", default=""))
            for author in entry.findall(f"{ATOM_NS}author")
        ]
        entry_id = entry.findtext(f"{ATOM_NS}id", default="")
        arxiv_id = normalize_arxiv_id(entry_id)
        doi = entry.findtext(f"{ARXIV_NS}doi", default="")
        journal_ref = clean_text(entry.findtext(f"{ARXIV_NS}journal_ref", default=""))
        pdf_url = ""
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
                break
        records.append(
            make_record(
                "arxiv",
                title=title,
                authors=authors,
                year=year_from_text(published or updated),
                venue=journal_ref or "arXiv",
                doi=doi,
                arxiv_id=arxiv_id,
                abstract=summary,
                url=entry_id,
                pdf_url=pdf_url,
                source_rank=position,
            )
        )
    return records


def search_pubmed(
    query: str,
    limit: int,
    from_year: Optional[int],
    to_year: Optional[int],
    rank: str,
    timeout: float,
    mailto: Optional[str] = None,
) -> List[Dict[str, Any]]:
    term = query
    if from_year or to_year:
        start = f"{from_year or 1800}"
        end = f"{to_year or 3000}"
        term = f'({query}) AND ("{start}"[Date - Publication] : "{end}"[Date - Publication])'
    esearch_params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": str(max(1, min(limit, 50))),
        "sort": "date" if rank == "recency" else "relevance",
    }
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(esearch_params)
    esearch = request_json(esearch_url, timeout, mailto)
    ids = ((esearch.get("esearchresult") or {}).get("idlist") or [])
    if not ids:
        return []
    efetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(efetch_params)
    root = request_xml(efetch_url, timeout, mailto)
    records: List[Dict[str, Any]] = []
    for position, article in enumerate(root.findall(".//PubmedArticle"), start=1):
        title = clean_text(article.findtext(".//ArticleTitle", default=""))
        journal = clean_text(article.findtext(".//Journal/Title", default=""))
        year = year_from_text(article.findtext(".//PubDate/Year", default="") or article.findtext(".//PubDate/MedlineDate", default=""))
        authors: List[str] = []
        for author in article.findall(".//AuthorList/Author"):
            collective = author.findtext("CollectiveName", default="")
            if collective:
                authors.append(clean_text(collective))
                continue
            last = clean_text(author.findtext("LastName", default=""))
            fore = clean_text(author.findtext("ForeName", default=""))
            authors.append(" ".join(part for part in [fore, last] if part))
        doi = ""
        pmid = clean_text(article.findtext(".//PMID", default=""))
        for article_id in article.findall(".//ArticleIdList/ArticleId"):
            if article_id.get("IdType") == "doi":
                doi = article_id.text or ""
                break
        abstract_parts = [
            clean_text(node.text or "")
            for node in article.findall(".//Abstract/AbstractText")
            if clean_text(node.text or "")
        ]
        records.append(
            make_record(
                "pubmed",
                title=title,
                authors=authors,
                year=year,
                venue=journal,
                doi=doi,
                pmid=pmid,
                abstract=" ".join(abstract_parts),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                pdf_url="",
                source_rank=position,
            )
        )
    return records


def search_biorxiv(
    query: str,
    limit: int,
    from_year: Optional[int],
    to_year: Optional[int],
    rank: str,
    timeout: float,
    mailto: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return search_openalex(
        query,
        limit,
        from_year,
        to_year,
        rank,
        timeout,
        mailto,
        extra_filter="primary_location.source.display_name.search:bioRxiv",
    )


SOURCE_FUNCTIONS: Dict[str, Callable[..., List[Dict[str, Any]]]] = {
    "openalex": search_openalex,
    "crossref": search_crossref,
    "arxiv": search_arxiv,
    "pubmed": search_pubmed,
    "biorxiv": search_biorxiv,
}


def merge_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for original in records:
        source = original.get("source", "")
        source_rank = original.get("source_rank")
        record = dict(original)
        keys: List[Tuple[str, str]] = []
        if record.get("doi"):
            keys.append(("doi", record["doi"]))
        if record.get("arxiv_id"):
            keys.append(("arxiv", record["arxiv_id"]))
        if record.get("pmid"):
            keys.append(("pmid", record["pmid"]))
        title_key = normalize_title(record.get("title", ""))
        if title_key:
            keys.append(("title", title_key))
        target = None
        for key in keys:
            if key in index:
                target = index[key]
                break
        if target is None:
            record["sources"] = [source] if source else []
            record["source_rank"] = {source: source_rank} if source and source_rank is not None else {}
            record.pop("source", None)
            merged.append(record)
            target = record
        else:
            if source and source not in target["sources"]:
                target["sources"].append(source)
            if source and source_rank is not None:
                target["source_rank"][source] = source_rank
            for field in ("title", "venue", "doi", "arxiv_id", "pmid", "url", "pdf_url"):
                if not target.get(field) and record.get(field):
                    target[field] = record[field]
            if len(record.get("authors") or []) > len(target.get("authors") or []):
                target["authors"] = record["authors"]
            if not target.get("year") and record.get("year"):
                target["year"] = record["year"]
            if len(record.get("abstract") or "") > len(target.get("abstract") or ""):
                target["abstract"] = record["abstract"]
            if record.get("citation_count") is not None:
                current = target.get("citation_count")
                target["citation_count"] = max(current or 0, record["citation_count"])
        for key in keys:
            index[key] = target
    return merged


def rank_records(records: List[Dict[str, Any]], rank: str) -> List[Dict[str, Any]]:
    def source_rank(record: Dict[str, Any]) -> int:
        ranks = [value for value in (record.get("source_rank") or {}).values() if isinstance(value, int)]
        return min(ranks) if ranks else 9999

    if rank == "recency":
        return sorted(records, key=lambda record: (-(record.get("year") or 0), source_rank(record)))
    if rank == "citations":
        return sorted(
            records,
            key=lambda record: (
                -(record.get("citation_count") if record.get("citation_count") is not None else -1),
                -(record.get("year") or 0),
                source_rank(record),
            ),
        )
    return sorted(records, key=source_rank)


def format_json(query: str, sources: Sequence[str], succeeded: Sequence[str], errors: Dict[str, str], rank: str, records: List[Dict[str, Any]]) -> str:
    payload = {
        "query": query,
        "sources_requested": list(sources),
        "sources_succeeded": list(succeeded),
        "errors": errors,
        "ranking": rank,
        "count": len(records),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": records,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def markdown_escape(value: Any) -> str:
    return clean_text(value).replace("|", "\\|")


def format_markdown(query: str, sources: Sequence[str], succeeded: Sequence[str], errors: Dict[str, str], rank: str, records: List[Dict[str, Any]]) -> str:
    lines = [
        f"# Scholarly search: {query}",
        "",
        f"- Sources requested: {', '.join(sources)}",
        f"- Sources succeeded: {', '.join(succeeded) if succeeded else 'none'}",
        f"- Ranking: {rank}",
        f"- Results: {len(records)}",
        "",
    ]
    if errors:
        lines.append("## Source errors")
        for source, message in errors.items():
            lines.append(f"- `{source}`: {markdown_escape(message)}")
        lines.append("")
    if not records:
        lines.append("No records returned.")
        return "\n".join(lines) + "\n"
    lines.extend([
        "| # | Title | Authors | Year | Venue | DOI / arXiv / PMID | Sources | Citations |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for number, record in enumerate(records, start=1):
        identifiers = " / ".join(
            part for part in [record.get("doi"), record.get("arxiv_id"), record.get("pmid")] if part
        )
        lines.append(
            "| {number} | [{title}]({url}) | {authors} | {year} | {venue} | {identifiers} | {sources} | {citations} |".format(
                number=number,
                title=markdown_escape(record.get("title", "")),
                url=record.get("url", ""),
                authors=markdown_escape(", ".join(record.get("authors") or [])),
                year=record.get("year") or "",
                venue=markdown_escape(record.get("venue", "")),
                identifiers=markdown_escape(identifiers),
                sources=markdown_escape(", ".join(record.get("sources") or [])),
                citations=record.get("citation_count") if record.get("citation_count") is not None else "",
            )
        )
    return "\n".join(lines) + "\n"


def bibtex_escape(value: Any) -> str:
    text = clean_text(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )


def bibtex_key(record: Dict[str, Any], used: set) -> str:
    authors = record.get("authors") or []
    first = authors[0] if authors else "unknown"
    surname = re.sub(r"[^A-Za-z0-9]", "", first.split()[-1] if first.split() else "unknown").lower() or "unknown"
    year = record.get("year") or "n.d."
    words = re.findall(r"[A-Za-z0-9]+", record.get("title", "").lower())
    stem = "".join(words[:2])[:20] or "paper"
    base = f"{surname}{year}{stem}"
    key = base
    suffix = 1
    while key in used:
        suffix += 1
        key = f"{base}{chr(ord('a') + suffix - 2)}"
    used.add(key)
    return key


def format_bibtex(records: List[Dict[str, Any]]) -> str:
    used: set = set()
    entries: List[str] = []
    for record in records:
        key = bibtex_key(record, used)
        entry_type = "article" if record.get("venue") and record.get("doi") else "misc"
        fields: List[Tuple[str, str]] = []
        if record.get("title"):
            fields.append(("title", record["title"]))
        if record.get("authors"):
            fields.append(("author", " and ".join(record["authors"])))
        if record.get("year"):
            fields.append(("year", str(record["year"])))
        if record.get("venue"):
            fields.append(("journal" if entry_type == "article" else "howpublished", record["venue"]))
        if record.get("doi"):
            fields.append(("doi", record["doi"]))
        if record.get("arxiv_id"):
            fields.append(("eprint", record["arxiv_id"]))
            fields.append(("archivePrefix", "arXiv"))
        if record.get("pmid"):
            fields.append(("note", f"PMID: {record['pmid']}"))
        if record.get("url"):
            fields.append(("url", record["url"]))
        body = ",\n".join(f"  {name} = {{{bibtex_escape(value)}}}" for name, value in fields)
        entries.append(f"@{entry_type}{{{key},\n{body}\n}}")
    return "\n\n".join(entries) + ("\n" if entries else "")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search public scholarly APIs without third-party dependencies.")
    parser.add_argument("--query", required=True, help="Search query or faithful question.")
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES), help="Comma-separated sources.")
    parser.add_argument("--limit", type=int, default=10, help="Final number of results.")
    parser.add_argument("--from-year", type=int, default=None)
    parser.add_argument("--to-year", type=int, default=None)
    parser.add_argument("--rank", choices=("relevance", "recency", "citations"), default="relevance")
    parser.add_argument("--format", choices=("json", "markdown", "bibtex"), default="json")
    parser.add_argument("--output", default=None, help="Optional output path; stdout when omitted.")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--mailto", default=None, help="Optional contact for scholarly API polite pools.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 2
    if args.from_year and args.to_year and args.from_year > args.to_year:
        print("--from-year cannot be after --to-year", file=sys.stderr)
        return 2
    sources = [source.strip().lower() for source in args.sources.split(",") if source.strip()]
    unknown = [source for source in sources if source not in SOURCE_CHOICES]
    if unknown:
        print(f"unknown source(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not sources:
        print("at least one source is required", file=sys.stderr)
        return 2

    multiplier = 5 if args.rank == "citations" else 2
    per_source = max(1, min(max(args.limit * multiplier, args.limit), 50))
    records: List[Dict[str, Any]] = []
    succeeded: List[str] = []
    errors: Dict[str, str] = {}
    for source in sources:
        function = SOURCE_FUNCTIONS[source]
        try:
            source_records = function(
                args.query,
                per_source,
                args.from_year,
                args.to_year,
                args.rank,
                args.timeout,
                args.mailto,
            )
            succeeded.append(source)
            records.extend(source_records)
        except Exception as exc:  # Each source is isolated on purpose.
            errors[source] = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)

    merged = rank_records(merge_records(records), args.rank)[: args.limit]
    if args.format == "json":
        output = format_json(args.query, sources, succeeded, errors, args.rank, merged)
    elif args.format == "markdown":
        output = format_markdown(args.query, sources, succeeded, errors, args.rank, merged)
    else:
        output = format_bibtex(merged)

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    if succeeded:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())