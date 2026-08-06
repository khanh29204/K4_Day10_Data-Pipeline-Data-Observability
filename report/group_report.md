# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | TeamB |
| Repository | https://github.com/khanh29204/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trương Quang Minh | 2A202601212 | Điều phối pipeline | `src/core/`, `src/pipelines/` |
| 2 | Phạm Hà Anh | 2A202601240 | RAG & agent | `src/retrieval/`, `data/embeddings/` |
| 3 | Phạm Ngọc Quốc Khánh | 2A202601254 | Evaluation & observability | `src/evaluation/`, `src/observability/` |
| 4 | Phạm Anh Minh | 2A202601260 | Nền tảng dữ liệu & recovery | `src/ingestion/`, `data/raw/`, `data/clean/` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành baseline và corruption/repair flow cho corpus Crossref gồm 24 records. Baseline
đọc raw snapshot, tạo clean dataset, embedding manifest và ba collection ChromaDB riêng cho baseline,
corrupted và repaired. Evaluation set được giữ cố định với 18 samples; baseline đạt retrieval hit rate
100%, mean token F1 0.4352, judge accuracy 38.9% và mean judge score 2.4444/5. Corruption flow tạo có
chủ đích sáu nhóm lỗi: drop records, summary rỗng, noise, title bị truncate, ngày stale và duplicate
rows. Quality chuyển từ PASS sang FAIL với 3 duplicate IDs, 3 summary ngắn và 3 stale rows; freshness
chuyển từ FRESH sang STALE. Tác động tương ứng lên agent là retrieval hit rate giảm còn 50%, token F1 còn
0.1726, judge accuracy còn 16.7% và judge score còn 1.6667/5. Repair đọc lại raw snapshot, chạy lại
cleaning, rebuild index và đánh giá trên cùng test set; tất cả quality/freshness signals và bốn metrics
được phục hồi đúng baseline. Giới hạn còn lại là Ragas chưa chạy và clean runtime vẫn cần thống nhất
hoàn toàn với contract schema tối thiểu 8 trường.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> controlled corruption
    -> corrupted re-index và re-evaluate
    -> repair từ raw snapshot
    -> repaired re-index và re-evaluate
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API/raw response | Fetch, retry, parse `PaperRecord`, lưu raw snapshot | `data/raw/crossref_response.json`, `crossref_records.json` | Phạm Anh Minh |
| Cleaning | Raw `PaperRecord` | Normalize title/summary/metadata, dedupe, date, `age_days`, embedding text | `data/clean/papers_clean.csv/json`, cleaning log | Phạm Anh Minh |
| Embedding/index | Clean DataFrame | MiniLM embeddings, metadata và Chroma cosine collection | `data/embeddings/`, `data/chroma/` | Phạm Hà Anh |
| Evaluation | Index và test set | Retrieval, answer generation, token F1, judge metrics | `data/eval/`, `data/results/*_answers.json`, `*_metrics.json` | Phạm Ngọc Quốc Khánh |
| Observability | Clean/corrupted/repaired DataFrame | Quality checks, freshness và report evidence | `data/quality/`, phase reports | Phạm Ngọc Quốc Khánh |
| Corruption/repair | Baseline clean và raw snapshot | Inject lỗi có log; repair lại từ raw, không sửa tay JSON | Corrupted/repaired clean, logs, metrics | Phạm Anh Minh; orchestration bởi Trương Quang Minh |
| Orchestration | Settings và artifact paths | Điều phối thứ tự chạy, isolation, release checklist và demo | `src/pipelines/`, `data/reports/` | Trương Quang Minh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed, nếu có | Không cấu hình; corruption indices được cố định trong code để tái lập |

API keys không được ghi vào report hoặc commit.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 09:08 UTC | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 09:38 UTC | `data/results/corruption_log.json`, corrupted/repaired metrics và `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter | Query `agentic retrieval augmented generation large language model`; filter `from-pub-date:2026-02-07,has-abstract:true` tại lần chạy artifact |
| Thời điểm lấy dữ liệu | Raw snapshot được giữ cố định; quality baseline timestamp `2026-08-06T09:08:44Z` |
| Số record nhận được | 24 normalized records |
| Cơ chế retry/backoff | Crossref request có retry cho lỗi mạng và HTTP 429/500/502/503/504 với exponential backoff |

### Raw và clean schema

Raw artifact là `data/raw/crossref_records.json`, một mảng gồm 24 record đã được chuẩn hóa từ
Crossref. JSON Schema tương ứng là [`crossref_records.schema.json`](../data/raw/crossref_records.schema.json).
Tất cả thuộc tính đều có mặt trong JSON; giá trị không có ở nguồn được biểu diễn bằng chuỗi rỗng hoặc
mảng rỗng.

#### Raw schema — `crossref_records.json`

| Trường | Kiểu | Bắt buộc | Ý nghĩa và xử lý khi thiếu/sai |
| --- | --- | --- | --- |
| `paper_id` | str | Có | DOI từ Crossref; bỏ record nếu thiếu hoặc trùng. |
| `title` | str | Có | Lấy title đầu tiên, normalize whitespace và strip tag; bỏ record nếu thiếu. |
| `summary` | str | Có | Abstract đã strip HTML/JATS; bỏ record nếu thiếu. |
| `authors` | list[str] | Có | Danh sách tác giả; không có tác giả → `[]`. |
| `categories` | list[str] | Có | Subject của Crossref; không có subject → `[]`. |
| `primary_category` | str | Có | Phần tử đầu của `categories`; không có category → `""`. |
| `published` | str (ISO) | Có | Ngày phát hành chuẩn hóa `YYYY-MM-DD`; không parse được → `""`. |
| `updated` | str (ISO) | Có | Ngày cập nhật từ `indexed`/`deposited`/`created`; không parse được → `""`. |
| `abs_url` | str (URI) | Có | URL Crossref, fallback về `https://doi.org/{paper_id}`. |
| `pdf_url` | str (URI) | Có | Link PDF đầu tiên; không có link → `""`. |
| `comment` | str | Có | Container/volume/issue/page được ghép lại; không có → `""`. |

Clean artifact là `data/clean/papers_clean.json`; JSON Schema tương ứng là
[`papers_clean.schema.json`](../data/clean/papers_clean.schema.json). Contract clean tối thiểu gồm:

#### Clean schema — `papers_clean.json`

| Trường | Kiểu | Bắt buộc | Xử lý khi thiếu/sai |
| --- | --- | --- | --- |
| `paper_id` | str | Có | DOI viết thường; bỏ record nếu thiếu hoặc trùng. |
| `title` | str | Có | Bỏ nếu < 10 ký tự; dedupe theo `title.lower()`. |
| `summary` | str | Có | Bỏ nếu < 80 ký tự; summary ngắn thường là `Abstract not available`. |
| `authors_joined` | str | Không | Rỗng → `Unknown`. |
| `categories_joined` | str | Không | Fallback `container-title` + `type` → `Uncategorized`. |
| `published` | str (ISO) | Có | Bỏ record nếu không parse được. |
| `age_days` | int | Có | Số ngày có dấu; âm nghĩa là ngày ở tương lai. |
| `text_for_embedding` | str | Có | Sinh lại từ title, authors, categories, published và summary. |

Mapping chính là `authors → authors_joined`, `categories → categories_joined`, `published → published`,
`title → title`, `summary → summary` và `paper_id → paper_id`. `age_days` và `text_for_embedding` là
derived fields. Fallback `container-title + type` lấy từ Crossref payload khi cleaning; nếu không có thì
dùng `Uncategorized`. Runtime artifact hiện còn các metadata columns phục vụ retrieval/traceability ngoài
contract tối thiểu này; đây là điểm cần thống nhất thêm khi enforce schema ở serializer.

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại record thiếu title hoặc summary quá ngắn | Completeness/Validity | 0 trong baseline; `cleaning_log.json` ghi `dropped_no_title=0`, `dropped_short_summary=0` | `data/clean/cleaning_log.json`, `baseline_quality.json` |
| Dedupe theo `paper_id` | Uniqueness | 0 trong baseline; corrupted có 3 duplicate IDs | `paper_id_unique_check`, `corrupted_quality.json` |
| Normalize whitespace và strip HTML/JATS | Validity | 24 records được clean | `papers_clean.json`, cleaning code |
| Parse `published` và tính signed `age_days` | Timeliness | Baseline 0 stale; corrupted inject 3 stale dates | `freshness_report*.json` |
| Sinh `text_for_embedding` từ metadata và summary | Retrieval readiness | 24 baseline documents được index | Embedding manifests và Chroma collections |

`text_for_embedding` dùng để tạo vector và chứa title, authors, categories, published và summary theo
clean contract. Document ID trong Chroma có dạng `{paper_id}::{index}` để record ID ổn định trong từng
collection. `age_days` là chênh lệch có dấu giữa ngày chạy và `published`; freshness coi record stale khi
tuổi lớn hơn 180 ngày hoặc ngày không hợp lệ.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 18 |
| Các `question_type` | `summary` (6), `authors` (6), `date` (6) |
| Ground-truth document ID | `ground_truth_doc_ids` lấy từ `paper_id` của clean dataset |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB cosine: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | Gemini `gemini-2.5-flash` cấu hình; metrics hiện ghi rõ Ragas bị skip và dùng fallback judge |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`, 18 samples |

Test set được khóa trước khi corruption và không tạo lại từ corrupted data. Vì vậy ground truth không bị
nhiễm lỗi, top-k/evaluator giữ nguyên, và chênh lệch metrics phản ánh thay đổi của dataset/index.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | `crossref_response.json`, `crossref_records.json` — 24 records |
| Cleaned dataset | `data/clean/` | Có | Baseline, corrupted và repaired CSV/JSON cùng cleaning log |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | Manifest và collection riêng cho ba trạng thái |
| Evaluation set | `data/eval/test_set.json` | Có | 18 samples dùng chung |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | 4 metrics RAG và `samples=18` |
| Quality/freshness | `data/quality/` | Có | Baseline/corrupted/repaired quality và freshness reports |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh từ metrics, quality và freshness artifact |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 18/18 samples retrieve được ground-truth document trong top-k |
| `mean_token_f1` | 0.4352 | F1 trung bình giữa answer và ground truth |
| `judge_accuracy` | 0.3889 | 7/18 theo judge hiện tại |
| `mean_judge_score` | 2.4444/5 | Điểm judge trung bình |
| Ragas | Skipped | Chưa bật `RUN_RAGAS=1`; report dùng fallback heuristic judge |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- | --- | --- |
| Row count | Completeness | > 0 rows | PASS, 24 | PASS, 24 | PASS, 24 |
| `paper_id` null | Completeness | 0 null | PASS, 0 | PASS, 0 | PASS, 0 |
| `paper_id` unique | Uniqueness | unique | PASS, 0 duplicate | FAIL, 3 duplicate | PASS, 0 duplicate |
| Title non-empty | Completeness | 0 null/empty | PASS | PASS | PASS |
| Summary length | Validity | không dưới ngưỡng quality 100 ký tự | PASS, 0 short | FAIL, 3 short | PASS, 0 short |
| Freshness check | Timeliness | 0 stale/missing date | PASS, 0 stale | FAIL, 3 stale | PASS, 0 stale |

### Freshness

| Thuộc tính | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Freshness được đo tại | Clean DataFrame | Corrupted DataFrame | Repaired DataFrame |
| Latest published | 2026-08-01 | 2026-07-03 | 2026-08-01 |
| Oldest published | 2026-02-12 | 1990-01-01 | 2026-02-12 |
| Ngưỡng freshness | 180 ngày | 180 ngày | 180 ngày |
| Stale rows | 0 | 3 | 0 |
| Trạng thái | FRESH | STALE | FRESH |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| Drop latest records | Bỏ 3 record có `age_days` nhỏ nhất | 3 | Có thể giảm row/document coverage | Ground-truth retrieval bị mất một phần; hit rate giảm trong combined run | Reload raw snapshot |
| Blank summary | Gán summary rỗng | 3 | Summary length FAIL | Context thiếu nội dung, góp phần giảm F1/judge | Re-clean raw summary |
| Inject noise | Chèn `ERROR_NOISE` và garbage vào summary | 3 | Quality length có thể vẫn PASS | Nhiễu embedding/context, ảnh hưởng answer quality | Rebuild text từ raw |
| Truncate title | Cắt title xuống 10 ký tự | 3 | Có nguy cơ vi phạm title contract | Metadata/title retrieval kém tin cậy hơn | Re-clean title từ raw |
| Stale published date | Gán `published=1990-01-01`, `age_days=9999` | 3 | Freshness FAIL | 3 stale rows; freshness chuyển STALE | Reparse published từ raw |
| Duplicate rows | Nối thêm 3 rows đã chọn | 3 additions | Uniqueness FAIL | `paper_id_unique` báo 3 duplicate IDs | Dedupe khi rebuild từ raw |

Corruption log:

- **Đường dẫn:** `data/results/corruption_log.json`
- **Trạng thái:** Có và khớp với dataset: original 24 rows, final 24 rows sau drop 3 và add 3 duplicates.
- **Nhận xét:** Log ghi đủ sáu loại corruption, count, indices hoặc affected paper IDs và timestamp.

Repair không sửa tay corrupted JSON. `corruption_flow.py` load lại immutable
`data/raw/crossref_records.json`, gọi `build_clean_dataframe`, ghi repaired dataset riêng, rebuild
`papers-repaired`, evaluate trên test set cũ và chạy lại quality/freshness. Vì vậy repaired artifacts có
lineage từ raw source và có thể so sánh công bằng với baseline.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | -0.5000 | 100% | Retrieval phục hồi hoàn toàn |
| `mean_token_f1` | 0.4352 | 0.1726 | 0.4352 | -0.2626 | 100% | Khớp lại baseline |
| `judge_accuracy` | 0.3889 | 0.1667 | 0.3889 | -0.2222 | 100% | Khớp lại baseline |
| `mean_judge_score` | 2.4444 | 1.6667 | 2.4444 | -0.7778 | 100% | Khớp lại baseline |
| Quality checks | PASS | FAIL | PASS | FAIL | PASS | 3 duplicate, 3 summary short ở corrupted |
| Freshness status | FRESH | STALE | FRESH | STALE | FRESH | 3 stale rows ở corrupted |

Hai chuỗi nhân quả được artifacts hỗ trợ:

1. Combined corruption gồm missing/noisy content, stale date và duplicate rows → `paper_id_unique`, summary length và freshness checks fail → hit rate `1.0000 → 0.5000`, token F1 `0.4352 → 0.1726`, judge accuracy `0.3889 → 0.1667`.
2. Reload raw snapshot → re-clean/re-index/re-evaluate trên cùng test set → quality `PASS`, freshness `FRESH` và cả bốn metrics trở lại đúng baseline.

Không thể tách đóng góp riêng của từng corruption type từ run hiện tại vì chúng được inject trong cùng
một scenario; cần ablation riêng nếu muốn định lượng từng loại lỗi.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi bắt đầu flow, `run_corruption_flow.py` dừng với `NotImplementedError` và không tạo được corrupted/repaired metrics.
- **Nguyên nhân:** `src/pipelines/corruption_flow.py` chỉ có pseudocode, chưa nối các owner ingestion, retrieval, evaluation và observability.
- **Cách xử lý:** Pipeline owner hoàn thiện orchestration; data owner cung cấp corruption/repair function; RAG/evaluation/observability owners bàn giao API và artifact paths. Output baseline/corrupted/repaired được tách collection/path.
- **Cách xác minh:** Chạy hai entrypoints; kiểm tra `corruption_log.json`, sáu metrics/quality/freshness artifacts và `data/reports/corruption_report.md`.

Một điểm cần thống nhất thêm là clean runtime có metadata columns ngoài contract tối thiểu 8 trường và
quality code hiện kiểm summary dưới 100 ký tự trong khi clean schema mô tả ngưỡng 80. Đây là giới hạn
contract/documentation cần xử lý ở lần release tiếp theo, không làm mất tính hợp lệ của comparison run.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Ragas chưa chạy; metrics dùng fallback heuristic judge | Chưa có đánh giá judge độc lập bằng Ragas | Bật `RUN_RAGAS=1`, lưu output và so sánh với fallback metrics |
| Combined corruption, chưa có ablation | Không định lượng riêng tác động từng corruption type | Chạy sáu scenario độc lập với cùng test set và seed/config cố định |
| Clean schema tài liệu và runtime columns/ngưỡng chưa hoàn toàn đồng nhất | Có thể gây lỗi khi downstream enforce `additionalProperties` hoặc length threshold | Chuẩn hóa serializer/schema và thêm schema validation vào pipeline release check |
| Source filter dựa trên ngày chạy | Nếu fetch lại có thể khác số record | Giữ raw snapshot cho benchmark và ghi source timestamp/query vào manifest |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm, thành viên, repository và ngày hoàn thành chính xác.
- [x] Phân công khớp với module, artifact và ownership trong file HTML nhóm 4 người.
- [x] Lệnh baseline và corruption flow đã tạo artifact tương ứng.
- [x] Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json` với 18 samples.
- [x] Bảng metrics khớp với `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`.
- [x] Quality/freshness conclusions khớp với các file trong `data/quality/`.
- [x] Các đường dẫn report và artifact tồn tại trong workspace.
- [x] Báo cáo cá nhân của các thành viên được hoàn thành theo vai trò.
- [x] Không có `.env`, API key, token hoặc secret trong report.
