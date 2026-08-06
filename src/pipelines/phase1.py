from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records


def main() -> None:
    """TODO(student): xay dung baseline pipeline end-to-end.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    settings = load_settings()

    raw_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_path.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(raw_path)

    print(f"Loaded {len(records)} raw records from {settings.source_api}.")

    clean_df = build_clean_dataframe(records, now_utc())
    write_csv(clean_df, settings.paths.clean_csv)

    clean_records = clean_df.to_dict(orient="records")
    for record in clean_records:
        if pd.isna(record.get("age_days")):
            record["age_days"] = None
    write_json(settings.paths.clean_json, clean_records)

    print(f"Cleaned {len(clean_df)} records -> {settings.paths.clean_csv}, {settings.paths.clean_json}")

    raise NotImplementedError(
        "Student task: indexing, evaluation, quality checks, and reporting steps are not implemented yet."
    )
