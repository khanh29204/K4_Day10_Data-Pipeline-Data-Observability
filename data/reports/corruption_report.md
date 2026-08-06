# Data Corruption & Pipeline Observability Impact Report

## Executive Summary
This report analyzes the performance and accuracy impact of synthetic data corruptions on the RAG agent pipeline, and demonstrates how data repair from raw artifacts restores system quality.

## 1. Metrics Comparison Matrix

| Metric State | Retrieval Hit Rate | Mean Token F1 | Judge Accuracy | Data Quality Status |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline (Clean)** | `1.0000` | `1.0000` | `1.0000` | `PASS` |
| **Corrupted Data** | `0.7000` | `0.6909` | `0.6750` | `FAIL` |
| **Repaired Data** | `1.0000` | `1.0000` | `1.0000` | `PASS` |

## 2. Key Findings & Insights
1. **Corruption Impact**: Injecting blank summaries, text noise, title truncations, and stale dates caused a drop in retrieval hit rate and token F1 accuracy.
2. **Observability Detection**: Data quality checks flagged missing summary values, duplicate records, and stale publication dates.
3. **Pipeline Recovery**: Re-running ETL cleaning from raw Crossref JSON artifacts successfully restored hit rate and accuracy metrics back to baseline performance.
