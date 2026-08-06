from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

MIN_SUMMARY_CHARS = 100

_TAG_RE = re.compile(r"<[^>]+>")

_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "summary_chars",
    "authors",
    "authors_joined",
    "categories",
    "categories_joined",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "abs_url",
    "pdf_url",
    "comment",
    "text_for_embedding",
]


def _strip_tags(text: str) -> str:
    return normalize_whitespace(_TAG_RE.sub(" ", text or ""))


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw Crossref records into a dataframe ready for embedding."""
    if not records:
        return pd.DataFrame(columns=_COLUMNS)

    df = pd.DataFrame(asdict(record) for record in records)
    df = df.drop_duplicates(subset="paper_id", keep="first")

    df["title"] = df["title"].map(_strip_tags)
    df["summary"] = df["summary"].map(_strip_tags)
    df = df[(df["title"].str.len() > 0) & (df["summary"].str.len() >= MIN_SUMMARY_CHARS)]

    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len()

    parsed_published = df["published"].map(_parse_date)
    df["published"] = parsed_published.map(lambda dt: dt.strftime("%Y-%m-%d") if dt else "")
    run_date_naive = run_date.replace(tzinfo=None)
    df["age_days"] = pd.array(
        [(run_date_naive - dt).days if dt else None for dt in parsed_published],
        dtype="Int64",
    )

    df["text_for_embedding"] = (
        "Title: " + df["title"] + " | Authors: " + df["authors_joined"] + " | Summary: " + df["summary"]
    )

    df = df.sort_values(by=["age_days", "paper_id"], na_position="last").reset_index(drop=True)

    return df[_COLUMNS]
