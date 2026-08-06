                          ┌──────────────────────────────────────┐
                          │  Crossref REST API                   │
                          │  query: "agentic RAG large language  │
                          │          model"                      │
                          │  filter: from-pub-date:<today-180d>, │
                          │          has-abstract:true           │
                          │  max_results: 24                     │
                          └───────────────┬──────────────────────┘
                                          │ fetch_source_records()   [STUB]
                                          │ + retry on 429/503
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RAW                                                                         │
│   data/raw/crossref_response.json   verbatim API payload (audit trail)      │
│   data/raw/crossref_records.json    list[PaperRecord]                       │
│                                                                             │
│   Contract — PaperRecord (crossref.py:9), 11 fields:                        │
│     paper_id(DOI) title summary authors[] categories[]                      │
│     primary_category published updated abs_url pdf_url comment              │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ parse_crossref_payload()  [STUB]
                │ build_clean_dataframe(records, run_date)  [STUB]
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLEAN                                                                       │
│   data/clean/papers_clean.csv + .json                                       │
│                                                                             │
│   Contract — DataFrame columns consumed downstream:                         │
│     paper_id title summary published authors_joined categories_joined       │
│     abs_url pdf_url          ← index.py:50-62 (metadata)                    │
│     text_for_embedding       ← index.py:53  (the embedded string)           │
│     age_days                 ← quality.py / freshness                       │
│     summary_chars                                                           │
│   Ops: normalize whitespace, parse dates, dedupe, drop bad rows, sort       │
└───────┬───────────────────────────────────────────┬─────────────────────────┘
        │                                           │
        │ LocalEmbeddingIndex.build()  ✅           │ build_test_set()  [STUB]
        │                                           ▼
        ▼                                  ┌────────────────────────────┐
┌───────────────────────────────────┐      │ EVAL SET                   │
│ INDEX                             │      │  data/eval/test_set.json   │
│  MiniLM-L6-v2 → 384-dim, cosine   │      │                            │
│  Chroma persist: data/chroma/     │      │  Contract (metrics.py:113):│
│  manifest: data/embeddings/       │      │   id question_type         │
│           papers_embeddings.json  │      │   question ground_truth    │
│                                   │      │   ground_truth_doc_ids[]   │
│  collection: papers-baseline      │      │  Types: summary|authors|   │
│   (corrupted / repaired variants  │      │         date|categories    │
│    auto-named, index.py:69)       │      └─────────────┬──────────────┘
└───────────────┬───────────────────┘                    │
                │                                        │
                └──────────────┬─────────────────────────┘
                               ▼
              ┌────────────────────────────────────────────┐
              │ EVALUATE  evaluate_pipeline()  ✅          │
              │   per question:                            │
              │     answer_question() → retrieve top_k=4   │
              │     _judge_answer()   → LLM 1-5 + correct  │
              │                         (falls back to F1) │
              │     _token_f1(), retrieval_hit             │
              │   optional: Ragas  (RUN_RAGAS=1)           │
              │                                            │
              │   → data/results/baseline_metrics.json     │
              │     {samples, retrieval_hit_rate,          │
              │      mean_token_f1, judge_accuracy,        │
              │      mean_judge_score, ragas}              │
              │   → data/results/baseline_answers.json     │
              └───────────────┬────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │ run_data_quality_checks()  [STUB]         │
        │ build_freshness_report()   [STUB]         │
        │   → data/quality/*, freshness_report.json │
        │   {latest_published, oldest_published,    │
        │    stale_rows, total_rows, is_fresh}      │
        │   threshold: age_days > 180               │
        └─────────────────────┬─────────────────────┘
                              ▼
              ┌────────────────────────────────────────────┐
              │ REPORT  generate_phase1_report()  [STUB]   │
              │   inputs: source_summary, metrics,         │
              │           quality, freshness               │
              │   → data/reports/phase1_report.md          │
              └────────────────────────────────────────────┘
