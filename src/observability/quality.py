from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings


from core.utils import write_json, now_utc

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks."""
    import os
    
    # 1. Check row count
    row_count = len(df)
    row_count_passed = row_count > 0
    row_count_details = f"Found {row_count} rows."
    
    # 2. Check paper_id not null and unique
    null_paper_ids = df["paper_id"].isnull().sum() if "paper_id" in df.columns else 1
    paper_id_null_passed = null_paper_ids == 0
    paper_id_null_details = f"{null_paper_ids} null paper_ids."
    
    unique_paper_ids = df["paper_id"].nunique() if "paper_id" in df.columns else 0
    paper_id_unique_passed = unique_paper_ids == row_count and row_count > 0
    paper_id_unique_details = f"All paper_ids are unique." if paper_id_unique_passed else f"{row_count - unique_paper_ids} duplicate paper_ids."
    
    # 3. Check title not null and not empty
    null_titles = df["title"].isnull().sum() + (df["title"] == "").sum() if "title" in df.columns else 1
    title_null_passed = null_titles == 0
    title_null_details = f"{null_titles} null or empty titles."
    
    # 4. Check summary length (should be at least 100 characters)
    if "summary" in df.columns:
        short_summaries = (df["summary"].isnull()) | (df["summary"].str.len() < 100)
        short_summaries_count = short_summaries.sum()
    else:
        short_summaries_count = row_count
    summary_length_passed = short_summaries_count == 0
    summary_length_details = f"0 short summaries." if summary_length_passed else f"{short_summaries_count} summaries are empty or less than 100 characters."
    
    # 5. Check freshness using age_days
    if "age_days" in df.columns:
        stale_papers = df["age_days"].isnull() | (df["age_days"] > settings.freshness_threshold_days)
        stale_count = stale_papers.sum()
    else:
        stale_count = row_count
    freshness_passed = stale_count == 0
    freshness_details = f"0 stale rows." if freshness_passed else f"{stale_count} rows are older than {settings.freshness_threshold_days} days or have no valid publish date."
    
    overall_passed = (
        row_count_passed and
        paper_id_null_passed and
        paper_id_unique_passed and
        title_null_passed and
        summary_length_passed and
        freshness_passed
    )
    
    checks = {
        "row_count_check": {
            "passed": bool(row_count_passed),
            "details": row_count_details
        },
        "paper_id_null_check": {
            "passed": bool(paper_id_null_passed),
            "details": paper_id_null_details
        },
        "paper_id_unique_check": {
            "passed": bool(paper_id_unique_passed),
            "details": paper_id_unique_details
        },
        "title_null_check": {
            "passed": bool(title_null_passed),
            "details": title_null_details
        },
        "summary_length_check": {
            "passed": bool(summary_length_passed),
            "details": summary_length_details
        },
        "freshness_check": {
            "passed": bool(freshness_passed),
            "details": freshness_details
        }
    }
    
    report = {
        "report_name": report_name,
        "timestamp": now_utc().isoformat(),
        "row_count": row_count,
        "checks": checks,
        "overall_passed": bool(overall_passed)
    }
    
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_file_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_file_path, report)
    
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report."""
    total_rows = len(df)
    
    if total_rows == 0:
        report = {
            "latest_published": "",
            "oldest_published": "",
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": True
        }
        write_json(report_path, report)
        return report

    published_dates = df["published"].dropna()
    published_dates = published_dates[published_dates != ""]
    
    if len(published_dates) > 0:
        latest_published = published_dates.max()
        oldest_published = published_dates.min()
    else:
        latest_published = ""
        oldest_published = ""

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"].isnull() | (df["age_days"] > settings.freshness_threshold_days)).sum())
    else:
        stale_rows = total_rows

    is_fresh = stale_rows == 0
    
    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": bool(is_fresh)
    }
    
    write_json(report_path, report)
    return report

