from __future__ import annotations

import pandas as pd


from core.utils import write_json, now_utc
import numpy as np

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption."""
    if len(df) == 0:
        write_json(output_log_path, {"status": "empty_dataframe", "timestamp": now_utc().isoformat()})
        return df.copy()

    cdf = df.copy()
    log = {
        "timestamp": now_utc().isoformat(),
        "original_row_count": len(cdf),
        "corruptions": []
    }

    # 1. Drop some latest records (e.g., top 3 youngest papers based on age_days or published date)
    # Sort by age_days ascending (youngest first)
    if "age_days" in cdf.columns:
        cdf = cdf.sort_values(by="age_days", ascending=True)
    dropped_ids = list(cdf.iloc[:3]["paper_id"].values) if len(cdf) >= 3 else []
    cdf = cdf.iloc[3:] if len(cdf) >= 3 else cdf
    log["corruptions"].append({
        "type": "drop_latest_records",
        "count": len(dropped_ids),
        "details": f"Dropped paper_ids: {dropped_ids}"
    })

    # Reset index to make indexing easy for remaining modifications
    cdf = cdf.reset_index(drop=True)
    n = len(cdf)

    # 2. Blank summary for some rows
    blank_summary_indices = [i for i in [0, 1, 2] if i < n]
    for idx in blank_summary_indices:
        cdf.loc[idx, "summary"] = ""
        cdf.loc[idx, "summary_chars"] = 0
    log["corruptions"].append({
        "type": "blank_summary",
        "count": len(blank_summary_indices),
        "indices": blank_summary_indices
    })

    # 3. Inject noise into text
    noise_indices = [i for i in [3, 4, 5] if i < n]
    for idx in noise_indices:
        orig = cdf.loc[idx, "summary"]
        cdf.loc[idx, "summary"] = f"<div><b>ERROR_NOISE:</b> {orig} !!!RANDOM_GARBAGE!!!</div>"
        cdf.loc[idx, "summary_chars"] = len(cdf.loc[idx, "summary"])
    log["corruptions"].append({
        "type": "inject_noise",
        "count": len(noise_indices),
        "indices": noise_indices
    })

    # 4. Truncate title
    truncate_indices = [i for i in [6, 7, 8] if i < n]
    for idx in truncate_indices:
        orig_title = str(cdf.loc[idx, "title"])
        cdf.loc[idx, "title"] = orig_title[:10] if len(orig_title) > 10 else "Short"
    log["corruptions"].append({
        "type": "truncate_title",
        "count": len(truncate_indices),
        "indices": truncate_indices
    })

    # 5. Make published date old (stale)
    stale_indices = [i for i in [9, 10, 11] if i < n]
    for idx in stale_indices:
        cdf.loc[idx, "published"] = "1990-01-01"
        cdf.loc[idx, "age_days"] = 9999
    log["corruptions"].append({
        "type": "stale_published_date",
        "count": len(stale_indices),
        "indices": stale_indices
    })

    # 6. Add duplicate rows
    duplicate_indices = [i for i in [12, 13, 14] if i < n]
    dup_rows = cdf.iloc[duplicate_indices].copy()
    cdf = pd.concat([cdf, dup_rows], ignore_index=True)
    log["corruptions"].append({
        "type": "add_duplicate_rows",
        "count": len(duplicate_indices),
        "indices": duplicate_indices
    })

    # 7. Rebuild text_for_embedding
    cdf["text_for_embedding"] = (
        "Title: " + cdf["title"].fillna("") + 
        " | Authors: " + cdf["authors_joined"].fillna("") + 
        " | Summary: " + cdf["summary"].fillna("")
    )

    log["final_row_count"] = len(cdf)
    write_json(output_log_path, log)
    
    return cdf

