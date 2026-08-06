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
    """Clean raw Crossref records into a dataframe ready for embedding.

    Rows dropped for duplication, missing title, or a too-short summary are
    counted (not silently discarded) and attached to the returned
    dataframe's `.attrs["drop_log"]`.
    """
    if not records:
        empty = pd.DataFrame(columns=_COLUMNS)
        empty.attrs["drop_log"] = {
            "input_rows": 0,
            "duplicate_rows": 0,
            "dropped_no_title": 0,
            "dropped_short_summary": 0,
            "kept_rows": 0,
        }
        return empty

    df = pd.DataFrame(asdict(record) for record in records)
    input_rows = len(df)

    df = df.drop_duplicates(subset="paper_id", keep="first")
    duplicate_rows = input_rows - len(df)

    df["title"] = df["title"].map(_strip_tags)
    df["summary"] = df["summary"].map(_strip_tags)
    no_title_mask = df["title"].str.len() == 0
    short_summary_mask = df["summary"].str.len() < MIN_SUMMARY_CHARS
    dropped_no_title = int(no_title_mask.sum())
    dropped_short_summary = int(short_summary_mask.sum())
    df = df[~no_title_mask & ~short_summary_mask]

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

    clean_df = df[_COLUMNS]
    clean_df.attrs["drop_log"] = {
        "input_rows": input_rows,
        "duplicate_rows": duplicate_rows,
        "dropped_no_title": dropped_no_title,
        "dropped_short_summary": dropped_short_summary,
        "kept_rows": len(clean_df),
    }
    print(
        f"Cleaned {len(clean_df)}/{input_rows} raw records "
        f"(dropped {input_rows - len(clean_df)}: {duplicate_rows} duplicate paper_id, "
        f"{dropped_no_title} missing title, {dropped_short_summary} summary under "
        f"{MIN_SUMMARY_CHARS} chars)"
    )

    return clean_df
