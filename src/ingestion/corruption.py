from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Simulate realistic data corruption scenarios across clean dataset rows.

    Corruptions introduced:
    1. Drop latest records (Data completeness / missing records bug)
    2. Blank summaries (Empty field / completeness bug)
    3. Inject text noise into summary (Corrupted text bug)
    4. Truncate titles (Schema/truncation bug)
    5. Make publication date stale (Data freshness bug)
    6. Duplicate existing rows (Duplication bug)
    """
    if df.empty or len(df) < 5:
        write_json(Path(output_log_path), {"status": "no_data_to_corrupt", "corruptions": []})
        return df.copy()

    df_corrupted = df.copy().reset_index(drop=True)
    n_rows = len(df_corrupted)
    log_entries: list[dict[str, Any]] = []

    # 1. Drop top latest records (Indices 0, 1 if available)
    drop_count = min(2, n_rows // 5 if n_rows >= 10 else 1)
    dropped_rows = df_corrupted.iloc[:drop_count]
    dropped_ids = dropped_rows["paper_id"].tolist()
    df_corrupted = df_corrupted.iloc[drop_count:].reset_index(drop=True)
    log_entries.append({
        "type": "drop_latest_records",
        "description": f"Dropped top {drop_count} latest records",
        "affected_paper_ids": dropped_ids,
    })
    
    n_rows = len(df_corrupted)

    # 2. Blank summary for selected rows (Indices 0, 1 of current df)
    blank_indices = list(range(0, min(2, n_rows)))
    blank_ids = []
    for idx in blank_indices:
        blank_ids.append(df_corrupted.at[idx, "paper_id"])
        df_corrupted.at[idx, "summary"] = ""
        df_corrupted.at[idx, "summary_chars"] = 0
    log_entries.append({
        "type": "blank_summary",
        "description": f"Blanked summary for {len(blank_indices)} rows",
        "affected_paper_ids": blank_ids,
    })

    # 3. Inject noise into summary for selected rows (Indices 2, 3 of current df)
    noise_indices = [idx for idx in range(2, min(4, n_rows)) if idx not in blank_indices]
    noise_ids = []
    for idx in noise_indices:
        noise_ids.append(df_corrupted.at[idx, "paper_id"])
        noise_text = "[CORRUPTED NOISE %$&*^#@ DATA PIPELINE BUG] " * 3
        df_corrupted.at[idx, "summary"] = noise_text + str(df_corrupted.at[idx, "summary"])
        df_corrupted.at[idx, "summary_chars"] = len(df_corrupted.at[idx, "summary"])
    log_entries.append({
        "type": "inject_noise",
        "description": f"Injected noise into summary for {len(noise_indices)} rows",
        "affected_paper_ids": noise_ids,
    })

    # 4. Truncate titles for selected rows (Indices 4, 5 of current df)
    trunc_indices = [idx for idx in range(4, min(6, n_rows))]
    trunc_ids = []
    for idx in trunc_indices:
        trunc_ids.append(df_corrupted.at[idx, "paper_id"])
        orig_title = str(df_corrupted.at[idx, "title"])
        df_corrupted.at[idx, "title"] = orig_title[:8]
    log_entries.append({
        "type": "truncate_title",
        "description": f"Truncated title for {len(trunc_indices)} rows",
        "affected_paper_ids": trunc_ids,
    })

    # 5. Make publication date stale for selected rows (Indices 6, 7 of current df)
    stale_indices = [idx for idx in range(6, min(8, n_rows))]
    stale_ids = []
    for idx in stale_indices:
        stale_ids.append(df_corrupted.at[idx, "paper_id"])
        df_corrupted.at[idx, "published"] = "2010-01-01"
        df_corrupted.at[idx, "age_days"] = int(df_corrupted.at[idx, "age_days"]) + 5000
    log_entries.append({
        "type": "stale_date",
        "description": f"Changed published date to 2010-01-01 for {len(stale_indices)} rows",
        "affected_paper_ids": stale_ids,
    })

    # 6. Add duplicate rows (Duplicate first 2 rows of current df)
    dup_indices = list(range(0, min(2, n_rows)))
    dup_rows = df_corrupted.iloc[dup_indices].copy()
    dup_ids = dup_rows["paper_id"].tolist()
    df_corrupted = pd.concat([df_corrupted, dup_rows], ignore_index=True)
    log_entries.append({
        "type": "add_duplicates",
        "description": f"Duplicated {len(dup_indices)} rows",
        "affected_paper_ids": dup_ids,
    })

    # 7. Rebuild `text_for_embedding` for all rows
    df_corrupted["text_for_embedding"] = df_corrupted.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Published: {row['published']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )

    write_json(Path(output_log_path), {"total_corruptions": len(log_entries), "log": log_entries})
    return df_corrupted

