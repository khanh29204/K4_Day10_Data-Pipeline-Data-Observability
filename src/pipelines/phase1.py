from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records


from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report
from retrieval.qa import answer_question

def main() -> None:
    """Xay dung baseline pipeline end-to-end."""
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

    # Build Chroma Index
    print("Building Chroma index for baseline...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    print(f"Chroma index built with collection: {index.collection_name}")

    # Build or load test set
    testset_path = settings.paths.eval_testset
    if settings.refresh_test_set or not testset_path.exists():
        print("Building evaluation test set...")
        build_test_set(clean_df, testset_path)
    else:
        print(f"Reusing existing test set at {testset_path}")

    # Run data quality checks & freshness report
    print("Running baseline quality and freshness checks...")
    quality_report = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness_report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    # Evaluate pipeline
    print("Evaluating baseline pipeline on test set...")
    metrics_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=testset_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print("Baseline evaluation complete.")

    # Generate baseline markdown report
    source_summary = {
        "api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "total_results": len(records),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    # Demo agent question
    if metrics_bundle.answers:
        demo_q = metrics_bundle.answers[0]["question"]
        print(f"\nDemo Question: {demo_q}")
        ans_res = answer_question(demo_q, settings, index)
        print(f"Agent Answer: {ans_res.answer}\n")
