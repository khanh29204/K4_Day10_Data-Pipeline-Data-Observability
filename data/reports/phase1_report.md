# Baseline Data Pipeline & Observability Report
    
Generated on: 2026-08-06T09:08:44.403114+00:00

## 1. Ingestion Summary
- **Source API**: Crossref REST API
- **Query**: `agentic retrieval augmented generation large language model`
- **Filter**: `from-pub-date:2026-02-07,has-abstract:true`
- **Raw Records Collected**: 24
- **Cleaned Dataset Size**: 24 papers

## 2. Data Quality & Observability
- **Overall Quality Status**: ✅ PASSED
- **Data Freshness Status**: 🟢 FRESH

### Detailed Quality Checks
| Check Name | Status | Details |
| :--- | :---: | :--- |
| row_count_check | ✅ PASS | Found 24 rows. |
| paper_id_null_check | ✅ PASS | 0 null paper_ids. |
| paper_id_unique_check | ✅ PASS | All paper_ids are unique. |
| title_null_check | ✅ PASS | 0 null or empty titles. |
| summary_length_check | ✅ PASS | 0 short summaries. |
| freshness_check | ✅ PASS | 0 stale rows. |

### Freshness Metrics
- **Oldest Published Date**: 2026-02-12
- **Latest Published Date**: 2026-08-01
- **Stale Rows Count**: 0 / 24 (0.0%)

## 3. RAG Retrieval & Evaluation Metrics
- **Evaluation Samples**: 18
- **Retrieval Hit Rate**: 100.0%
- **Mean Token F1-Score**: 0.4352
- **Mean Judge Score (1-5)**: 2.44 / 5.0
- **Mean Judge Accuracy**: 38.9%

### Ragas Framework Evaluation
*Ragas pass skipped: Set RUN_RAGAS=1 to enable the slower Ragas pass.*

---
*End of Report*
