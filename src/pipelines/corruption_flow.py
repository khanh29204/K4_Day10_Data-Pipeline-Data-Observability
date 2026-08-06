import pandas as pd
from core.config import load_settings
from core.utils import read_json, write_json, write_csv, now_utc
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report

def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow."""
    settings = load_settings()

    # 1. Load baseline metrics va clean dataset
    print("Loading baseline clean dataset and metrics...")
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_csv.exists():
        print("Error: Baseline metrics or clean CSV does not exist. Please run phase 1 first.")
        return
        
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.read_csv(settings.paths.clean_csv)

    # 2. Tao corrupted dataframe
    print("\nSimulating data corruption flow...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)

    # 3. Save corrupted artifacts
    print("Saving corrupted dataset to clean files...")
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    
    corrupted_records = corrupted_df.to_dict(orient="records")
    for r in corrupted_records:
        if pd.isna(r.get("age_days")):
            r["age_days"] = None
    write_json(settings.paths.corrupted_clean_json, corrupted_records)

    # 4. Rebuild index va evaluate (corrupted)
    print("\nBuilding Chroma index for corrupted data...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    
    print("Evaluating corrupted pipeline on test set...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    # 5. Run quality checks/freshness tren corrupted data
    print("Running quality and freshness checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, 
        settings, 
        settings.paths.quality_dir / "freshness_report_corrupted.json"
    )

    # 6. Repair lai tu raw records
    print("\nRepairing dataset from raw records snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    
    print("Saving repaired dataset to clean files...")
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    
    repaired_records = repaired_df.to_dict(orient="records")
    for r in repaired_records:
        if pd.isna(r.get("age_days")):
            r["age_days"] = None
    write_json(settings.paths.repaired_clean_json, repaired_records)

    # 7. Evaluate repaired dataset
    print("\nBuilding Chroma index for repaired data...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    
    print("Evaluating repaired pipeline on test set...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    
    print("Running quality and freshness checks on repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, 
        settings, 
        settings.paths.quality_dir / "freshness_report_repaired.json"
    )

    # 8. Tao comparison report
    print("\nGenerating final comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    
    print(f"Flow complete. Comparison report written to: {settings.paths.comparison_report}")

