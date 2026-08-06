# Data Pipeline Observability: Corruption & Repair Impact Report

This report compares the RAG system's performance and data quality metrics across three states:
1. **Baseline**: The clean dataset state.
2. **Corrupted**: Simulated data quality issues (dropping latest papers, empty summaries, truncated titles, stale dates, duplicates).
3. **Repaired**: Restored state from the raw Crossref source records.

## 1. Metrics Comparison Table

| Indicator | Baseline | Corrupted | Repaired | Recovery Delta (Repaired vs Corrupted) |
| :--- | :---: | :---: | :---: | :---: |
| **Overall Quality Check** | ✅ PASS | ❌ FAIL | ✅ PASS | Restored |
| **Freshness Check** | 🟢 FRESH | 🔴 STALE | 🟢 FRESH | Restored |
| **Total Rows** | 18 | 24 | 24 | 0 |
| **Retrieval Hit Rate** | 100.0% | 50.0% | 100.0% | +50.0% |
| **Mean Token F1** | 0.4352 | 0.1726 | 0.4352 | +0.2626 |
| **Mean Judge Score (1-5)** | 2.44 | 1.67 | 2.44 | +0.78 |
| **Mean Judge Accuracy** | 38.9% | 16.7% | 38.9% | +22.2% |

## 2. Analysis of Data Corruption Impact

- **Retrieval Hit Rate Decline**: Data corruption (dropping papers, stale publication dates, missing metadata) directly leads to a drop in the Retrieval Hit Rate. When documents requested by the evaluation set are removed or missing, semantic search fails to locate them.
- **Answer Quality Degradation**: Missing summaries and noisy texts cause the RAG agent to retrieve low-quality contexts. The token F1 score and the Judge Accuracy decline significantly because the LLM lacks proper context to form accurate answers, leading to hallucinations or "I don't know" responses.
- **Observability Warning**: The custom Data Quality Checks and Freshness Monitors successfully flagged the corrupted dataset as **FAILED** and **STALE**, indicating issues before any end-user could receive corrupted answers.

## 3. Data Repair & Quality Recovery

- **Re-ingestion & Re-cleaning**: Running the repair pipeline reads the immutable raw records snapshot from Crossref, filters duplicates, cleans out noise, checks summaries length, recalculates the freshness `age_days`, and saves the cleaned dataset.
- **Evaluation Restoration**: The restored vector database correctly stores the complete clean summaries. Evaluating the system on the same test set shows that the **Retrieval Hit Rate**, **Token F1**, and **Judge Scores** are successfully recovered back to their baseline levels.
- **Observability Success**: Post-repair quality and freshness assessments report **PASSED** and **FRESH** status.

---
*End of Report*
