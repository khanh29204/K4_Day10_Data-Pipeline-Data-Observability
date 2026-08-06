from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import random
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"

# Identifies the client to Crossref; helps get into their "polite pool" (better rate limits).
USER_AGENT = "Day10-DataObservabilityLab/1.0 (student project; https://github.com/)"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 50
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0
JITTER_AFTER_ATTEMPT = 5
MAX_PAGE_SIZE = 1000  # Crossref's max `rows` per request

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_tags(text: str) -> str:
    return normalize_whitespace(_TAG_RE.sub(" ", text))


def _format_date(date_field: dict[str, Any] | None) -> str:
    if not date_field:
        return ""
    parts = date_field.get("date-parts")
    if not parts or not parts[0]:
        return ""
    year, *rest = parts[0]
    month = rest[0] if len(rest) > 0 else 1
    day = rest[1] if len(rest) > 1 else 1
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def _extract_published(item: dict[str, Any]) -> str:
    for key in ("published", "published-print", "published-online", "issued"):
        date_str = _format_date(item.get(key))
        if date_str:
            return date_str
    return ""


def _extract_updated(item: dict[str, Any]) -> str:
    for key in ("indexed", "deposited", "created"):
        date_str = _format_date(item.get(key))
        if date_str:
            return date_str
    return ""


def _extract_authors(item: dict[str, Any]) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        given = normalize_whitespace(author.get("given", "") or "")
        family = normalize_whitespace(author.get("family", "") or "")
        full_name = compact_join((given, family), sep=" ")
        if not full_name:
            full_name = normalize_whitespace(author.get("name", "") or "")
        if full_name:
            authors.append(full_name)
    return authors


def _extract_categories(item: dict[str, Any]) -> list[str]:
    return [normalize_whitespace(subject) for subject in (item.get("subject") or []) if normalize_whitespace(subject)]


def _extract_pdf_url(item: dict[str, Any]) -> str:
    links = item.get("link") or []
    for link in links:
        content_type = (link.get("content-type") or "").lower()
        url = link.get("URL", "")
        if url and "pdf" in content_type:
            return url
    return links[0].get("URL", "") if links else ""


def _extract_comment(item: dict[str, Any]) -> str:
    container_titles = item.get("container-title") or []
    container_title = normalize_whitespace(container_titles[0]) if container_titles else ""
    volume = item.get("volume", "")
    issue = item.get("issue", "")
    page = item.get("page", "")
    parts = [container_title]
    if volume:
        parts.append(f"vol. {volume}")
    if issue:
        parts.append(f"no. {issue}")
    if page:
        parts.append(f"pp. {page}")
    return compact_join(parts, sep=", ")


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a raw Crossref `/works` response into `PaperRecord`s.

    Records missing a DOI, title, or abstract are dropped as invalid, and
    duplicate DOIs are collapsed to a single record.
    """
    items = payload.get("message", {}).get("items") or []
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in items:
        doi = (item.get("DOI") or "").strip()
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""
        summary = _strip_tags(item.get("abstract") or "")

        if not doi or not title or not summary or doi in seen_ids:
            continue

        categories = _extract_categories(item)
        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=_extract_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=_extract_published(item),
                updated=_extract_updated(item),
                abs_url=item.get("URL", "") or f"https://doi.org/{doi}",
                pdf_url=_extract_pdf_url(item),
                comment=_extract_comment(item),
            )
        )
        seen_ids.add(doi)

    return records


def _sleep_before_retry(attempt: int, response: requests.Response | None) -> None:
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after is not None:
        try:
            time.sleep(float(retry_after))
            return
        except ValueError:
            pass

    capped_backoff = min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * 2**attempt)
    if attempt <= JITTER_AFTER_ATTEMPT:
        # Plain exponential backoff for the first few retries.
        wait_seconds = capped_backoff
    else:
        # Still failing after JITTER_AFTER_ATTEMPT tries: add full jitter to
        # break any lockstep retry pattern instead of continuing to double.
        wait_seconds = random.uniform(0, capped_backoff)
    time.sleep(wait_seconds)


def _request_page(params: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        response: requests.Response | None = None
        try:
            response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.HTTPError as exc:
            last_error = exc
            if response is not None and response.status_code not in RETRYABLE_STATUS_CODES:
                raise RuntimeError(f"Crossref API request failed with status {response.status_code}") from exc
        except requests.RequestException as exc:
            last_error = exc
        else:
            return response.json()

        if attempt < MAX_RETRIES:
            _sleep_before_retry(attempt, response)

    raise RuntimeError(f"Failed to fetch data from Crossref after {MAX_RETRIES} attempts") from last_error


def _collect_crossref_items(
    base_params: dict[str, Any],
    headers: dict[str, str],
    max_items: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Page through Crossref via cursor pagination.

    Collects up to `max_items` items, or every match if `max_items` is None.
    Returns the collected items plus the first page's payload (used to carry
    over metadata like `total-results` into the saved raw response).
    """
    first_payload: dict[str, Any] = {}
    all_items: list[dict[str, Any]] = []
    cursor = "*"

    while max_items is None or len(all_items) < max_items:
        payload = _request_page({**base_params, "cursor": cursor}, headers)
        if not first_payload:
            first_payload = payload

        message = payload.get("message") or {}
        items = message.get("items") or []
        if not items:
            break
        all_items.extend(items)

        next_cursor = message.get("next-cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    if max_items is not None:
        all_items = all_items[:max_items]

    return all_items, first_payload


def _combine_payload(first_payload: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    combined_message = dict(first_payload.get("message") or {})
    combined_message["items"] = items
    combined_message["items-per-page"] = len(items)
    return {**first_payload, "message": combined_message}


def _crawl_and_save(settings: Settings, base_params: dict[str, Any], max_items: int | None) -> list[PaperRecord]:
    headers = {"User-Agent": USER_AGENT}
    items, first_payload = _collect_crossref_items(base_params, headers, max_items)
    payload = _combine_payload(first_payload, items)

    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Query the Crossref API, snapshot the raw response, and parse it into records.

    Crossref's `total-results` reflects its entire index, not what a single
    request returns, so this pages through results with cursor-based
    pagination until `settings.max_results` items are collected (or the
    source runs out). If a raw-records snapshot already exists on disk, the
    crawl is skipped and that snapshot is reused instead. Use
    `fetch_all_papers` to ignore the `max_results` cap and pull every match.
    """
    raw_records_path = settings.paths.raw_records_json
    if raw_records_path.exists():
        return load_raw_records(raw_records_path)

    base_params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": min(settings.max_results, MAX_PAGE_SIZE),
    }
    return _crawl_and_save(settings, base_params, max_items=settings.max_results)


def fetch_all_papers(settings: Settings) -> list[PaperRecord]:
    """Like `fetch_source_records`, but ignores `settings.max_results` and pages
    through every Crossref result matching the query/filter.

    Crossref's `total-results` reflects its entire index (can be in the
    hundreds of thousands even for a narrow query), so this may issue many
    requests and take a long time to run. If a raw-records snapshot already
    exists on disk, the crawl is skipped and that snapshot is reused instead.
    """
    raw_records_path = settings.paths.raw_records_json
    if raw_records_path.exists():
        return load_raw_records(raw_records_path)

    base_params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": MAX_PAGE_SIZE,
    }
    return _crawl_and_save(settings, base_params, max_items=None)


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a previously saved raw-records JSON snapshot back into `PaperRecord`s."""
    payload = read_json(path)
    return [PaperRecord(**item) for item in payload]
