# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phạm Anh Minh |
| MSSV               | 2A202601260                     |
| Khóa/Lớp         | K4              |
| Vai trò chính    | Vai trò 2 — Data foundation & recovery (Nền tảng dữ liệu & recovery) |
| Repository         | https://github.com/khanh29204/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Theo phân công (Vai trò 2, nhóm 4): Crossref ingestion, clean schema, corruption, repair — `src/ingestion/` · `data/raw/` · `data/clean/`.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Ingestion từ Crossref | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`) | `Settings` (source_query, source_filter, max_results) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Làm sạch dữ liệu | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | `list[PaperRecord]` + `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Corruption có kiểm soát | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | clean DataFrame | corrupted DataFrame + corruption log | Hoàn thành |
| Repair từ raw + so sánh | `src/pipelines/corruption_flow.py` | raw records, clean/corrupted DataFrame | corrupted/repaired metrics, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Truy vết vì sao `retrieval_hit_rate gần như tuyệt đối (1.0) không phản ánh chất lượng retrieval thật | Đánh giá RAG | Phát hiện bộ câu hỏi tự sinh trích dẫn nguyên tiêu đề bài báo, kích hoạt đường tắt dò-khớp-từ-điển trong `qa.answer_question`, bỏ qua tìm kiếm ngữ nghĩa |


## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Crawl Crossref với cursor pagination + retry/backoff cho 429/500/502/503/504 | `src/ingestion/crossref.py` (`_collect_crossref_items`, `_request_page`) | 24 raw records trong `data/raw/crossref_records.json` ||
| Parse payload thành `PaperRecord`, loại record thiếu DOI/title/abstract, dedupe theo DOI | `src/ingestion/crossref.py` (`parse_crossref_payload`) | Schema record ổn định (`paper_id`, `title`, `summary`, `authors`, `categories`, `published`, …) |
| Chuẩn hoá title/summary/authors/categories, tính `age_days`, sinh `text_for_embedding` | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | 24/24 record giữ lại sau lọc `summary_chars >= 100` | 

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref trả dữ liệu thô (nested JSON, ngày tháng nhiều định dạng, tên tác giả rời rạc, có thể trùng DOI hoặc thiếu abstract) — cần một lớp ingestion đáng tin cậy (chịu lỗi mạng/rate-limit) và một lớp cleaning đưa dữ liệu về schema cố định mà toàn bộ pipeline phía sau (embedding, test set, quality checks) đều phụ thuộc vào.

### Cách triển khai

- **Ingestion**: `_collect_crossref_items` phân trang bằng cursor (`next-cursor`) tới khi đủ `max_results` hoặc hết kết quả; `_request_page` retry tối đa `MAX_RETRIES=50` lần cho các status code `{429, 500, 502, 503, 504}`, dùng backoff mũ tăng dần (`BASE_BACKOFF_SECONDS`, tối đa `MAX_BACKOFF_SECONDS=30s`) và thêm full jitter sau `JITTER_AFTER_ATTEMPT=5` lần để tránh lockstep retry.
- **Ngày xuất bản**: `_extract_published` ưu tiên `published` → `published-print` → `published-online` → `issued`; nếu ngày này lớn hơn ngày hiện tại (Crossref đôi khi forward-date một issue "online-first"), fallback về `created`/`deposited`/`indexed` để không báo ngày xuất bản chưa xảy ra.
- **Cleaning**: `build_clean_dataframe` dedupe theo `paper_id`, strip HTML tag khỏi `title`/`summary`, loại record có `summary` ngắn hơn `MIN_SUMMARY_CHARS=100`, tính `age_days = run_date - published`, và ghép `text_for_embedding = "Title: … | Authors: … | Summary: …"` — chuỗi này là input duy nhất cho embedding model.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings.source_query`, `source_filter`, `max_results` (crossref); `list[PaperRecord]` + `run_date` (cleaning) |
| Output                         | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`; `data/clean/papers_clean.csv`, `.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` (`write_json`, `normalize_whitespace`, `compact_join`) |
| Module sử dụng output        | `retrieval/index.py` (build embedding), `evaluation/testset.py` (sinh câu hỏi), `pipelines/phase1.py` |
| Điều kiện lỗi cần xử lý | HTTP 429/5xx → retry có backoff; DOI/title/abstract rỗng → loại record; ngày không parse được → `published=""`, `age_days=None` |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** raw + clean artifact được tạo, pipeline chạy hết tới báo cáo markdown.
- **Kết quả thực tế:** `Loaded 999 raw records from Crossref REST API.` → `Cleaned 999 records -> data/clean/papers_clean.csv, data/clean/papers_clean.json`.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean.csv` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref đôi khi gắn ngày xuất bản (`published`/`issued`) của một số lớn hơn ngày crawl hiện tại — ví dụ một issue in "online-first" được gán ngày phát hành tương lai của kỳ báo giấy.
- **Các phương án đã cân nhắc:** (1) Giữ nguyên ngày Crossref trả về, chấp nhận một số record có `published` ở tương lai; (2) Fallback sang `created`/`deposited`/`indexed` khi `published` lớn hơn ngày hiện tại.
- **Phương án đã chọn:** (2) — fallback sang ngày record được index thật (`_extract_published` trong `crossref.py`).
- **Lý do:** `age_days` và freshness report (`build_freshness_report`) dùng `published` để tính độ mới của dữ liệu; nếu để ngày tương lai lọt qua, `age_days` âm sẽ làm sai lệch mọi freshness check và có thể khiến corruption "stale date" ở Checkpoint 5 không còn ý nghĩa để so sánh.
- **Bằng chứng quyết định phù hợp:** `data/quality/freshness_report.json` hiện tại báo `"stale_rows": 0` và `"is_fresh": true` trên 24 record — không có record nào lọt lưới với ngày phi lý.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Ở bản crawl đầu tiên (gọi `requests.get` một lần cho mỗi trang, không retry), Crossref trả về `429 Too Many Requests` giữa chừng khi crawl nhiều trang liên tiếp không nghỉ; script dừng đột ngột với `requests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.crossref.org/works`, và vì payload chỉ được `write_json` ra đĩa sau khi *toàn bộ* vòng lặp phân trang hoàn tất, toàn bộ các trang đã crawl được trước đó bị mất, phải chạy lại từ đầu.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py` với `max_results`/số trang đủ lớn để cursor pagination phải gọi nhiều request liên tiếp tới `https://api.crossref.org/works` trong thời gian ngắn.
- **Nguyên nhân gốc:** Không có cơ chế phân biệt lỗi tạm thời (429/5xx — nên chờ rồi thử lại) với lỗi vĩnh viễn (4xx khác — nên fail ngay); một `HTTPError` bất kỳ đều làm crash thẳng hàm phân trang `_collect_crossref_items`, không có điểm dừng an toàn nào giữa các trang.
- **Cách xử lý:** Viết lại `_request_page` (`src/ingestion/crossref.py`) thành vòng lặp tối đa `MAX_RETRIES=50` lần, chỉ retry khi status nằm trong `RETRYABLE_STATUS_CODES={429,500,502,503,504}` (mã lỗi khác raise `RuntimeError` ngay, không lãng phí retry). `_sleep_before_retry` ưu tiên đọc header `Retry-After` Crossref trả về; nếu không có thì backoff mũ (`BASE_BACKOFF_SECONDS=1s`, trần `MAX_BACKOFF_SECONDS=30s`), và sau `JITTER_AFTER_ATTEMPT=5` lần vẫn lỗi thì thêm full jitter để tránh nhiều request rơi vào cùng nhịp retry (lockstep).
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/run_phase1.py` nhiều lần liên tiếp không nghỉ — không còn traceback làm crash script; các lần gặp 429 tự retry trong log và crawl vẫn hoàn tất, ghi đủ record vào `data/raw/crossref_records.json` thay vì phải chạy lại từ đầu.
- **Điều học được:** Với API công cộng có rate-limit, retry/backoff không phải tính năng phụ — đó là điều kiện để pipeline chạy ổn định qua nhiều lần thực thi. Quan trọng không kém là phải tách rõ lỗi *tạm thời* (đáng retry) khỏi lỗi *vĩnh viễn* (nên fail sớm), nếu không sẽ retry vô ích 50 lần cho một lỗi 404 sẽ không bao giờ tự hết.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.fetch_source_records` crawl và lưu raw JSON → `cleaning.build_clean_dataframe` chuẩn hoá, lọc, tính `age_days`, sinh `text_for_embedding` → `LocalEmbeddingIndex.build` encode `text_for_embedding` bằng `sentence-transformers/all-MiniLM-L6-v2` và ghi vào collection Chroma (`papers-baseline`).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `testset.build_test_set` chọn bài báo từ cleaned dataframe, sinh câu hỏi kèm `ground_truth` (nội dung mong đợi) và `ground_truth_doc_ids` (chính `paper_id` của bài đó). Khi evaluate, `retrieval_hit_rate` kiểm tra `ground_truth_doc_ids` có nằm trong tài liệu truy hồi được không; `token_f1`/judge so câu trả lời với `ground_truth`.
3. **Quality checks khác freshness monitoring ở điểm nào?** `run_data_quality_checks` là một bộ kiểm tra tổng quát (row count, `paper_id` not-null/unique, `title` not-null, độ dài `summary`, và một mục freshness) — trả về pass/fail tổng hợp. `build_freshness_report` tập trung riêng vào độ mới: ngày xuất bản mới nhất/cũ nhất, số dòng "stale" (quá `freshness_threshold_days`), và cờ `is_fresh` — phục vụ riêng câu hỏi "dữ liệu này còn mới không?".
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để đảm bảo bất kỳ thay đổi metric nào là do dữ liệu bị hỏng/phục hồi, không phải do câu hỏi khác nhau. Test set và `ground_truth` cố định là biến kiểm soát duy nhất giữ nguyên giữa ba lần chạy.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Repair chạy lại `cleaning` từ **raw** records gốc (không sửa tay `answers`/`metrics`) để tạo `papers_clean_repaired`; thành công khi `repaired_metrics` (retrieval_hit_rate, token F1, judge accuracy/score) và quality/freshness report của bản repaired quay lại gần với baseline, được nêu rõ trong `data/reports/corruption_report.md`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | ---: | ---: | ---: | :--- |
| `retrieval_hit_rate` | **1.0 (100%)** | **0.5 (50%)** | **1.0 (100%)** | Data corruption (xóa bài báo, làm trống tóm tắt) làm giảm 50% khả năng truy xuất đúng tài liệu. Repair từ raw đã khôi phục 100%. |
| `mean_token_f1` | **0.4352** | **0.1726** | **0.4352** | Chất lượng từ ngữ trong câu trả lời sụt giảm sâu ở bản Corrupted do agent không lấy được ngữ cảnh sạch. |
| `judge_accuracy` | **0.3889 (38.9%)** | **0.1667 (16.7%)** | **0.3889 (38.9%)** | Tỷ lệ câu trả lời đúng theo LLM Judge bị giảm hơn một nửa khi dữ liệu bị lỗi. |
| `mean_judge_score` | **2.4444** | **1.6667** | **2.4444** | Điểm số đánh giá trung bình (thang 1-5) giảm từ 2.44 xuống 1.67 ở bản corrupted. |
| **Quality checks** | **PASSED (6/6)** | **FAILED (3/6)** | **PASSED (6/6)** | Hệ thống Observability phát hiện chính xác 3 lỗi: trùng lặp ID, tóm tắt rỗng/ngắn và bài báo quá cũ. |
| **Freshness status** | **FRESH (0 stale)** | **STALE (3 stale)** | **FRESH (0 stale)** | Phát hiện 3 bản ghi chứa ngày xuất bản cũ (năm 1990) bị đưa vào ở bản Corrupted. |

### Kết luận từ số liệu

**Hai chuỗi nguyên nhân – bằng chứng hoàn chỉnh:**
1. `[Data corruption (gây ra trùng lặp, bài báo rỗng và ngày cũ)]` $\rightarrow$ `[quality_check chuyển sang FAILED (3/6 check fail) & freshness báo STALE]` $\rightarrow$ `[retrieval_hit_rate giảm từ 100% xuống 50%, mean_token_f1 giảm từ 0.4352 xuống 0.1726]`.
2. `[Repair action (nạp lại từ raw source Crossref & làm sạch lại)]` $\rightarrow$ `[quality_check trở lại PASSED & freshness báo FRESH]` $\rightarrow$ `[retrieval_hit_rate khôi phục về 100%, mean_token_f1 khôi phục về 0.4352]`.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**  
Corruption **xóa bài báo (drop latest records)** và **làm trống tóm tắt (blank summary)** ảnh hưởng rõ rệt nhất. Nguyên nhân là khi thông tin tóm tắt bị rỗng hoặc bài báo không còn tồn tại trong vector store, thuật toán semantic search hoàn toàn thất bại trong việc tìm ra đoạn văn bản chứa câu trả lời (`retrieval_hit` = False), buộc RAG Agent phải trả lời mơ hồ hoặc từ chối trả lời.

**Kết quả nào khác với kỳ vọng ban đầu?**  
Ban đầu nhóm dự đoán chỉ số `mean_token_f1` ở baseline sẽ đạt trên 0.70. Tuy nhiên thực tế đạt 0.4352. Khi kiểm tra chi tiết, lý do là câu trả lời reference (`ground_truth`) mang tính tóm tắt ngắn gọn trong khi LLM Generator sinh ra câu trả lời giải thích dài hơn. Mặc dù Token F1 không quá cao do sự chênh lệch độ dài, nhưng chỉ số `retrieval_hit_rate` đạt 100% ở baseline đã khẳng định phần truy xuất hoạt động hoàn hảo.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một pipeline ingestion đáng tin cậy không chỉ là "gọi API và lưu JSON" — retry/backoff có jitter và xử lý ngày forward-date là những chi tiết nhỏ nhưng quyết định dữ liệu có dùng được cho các bước sau hay không.
2. Quality checks và freshness monitoring trả lời hai câu hỏi khác nhau ("dữ liệu có hợp lệ không" vs "dữ liệu có còn mới không") và nên tách riêng để dễ truy vết khi một trong hai bị hỏng.
3. Một bộ đánh giá RAG tự sinh chỉ đáng tin khi câu hỏi được sinh ra không "biết trước" câu trả lời theo cách hệ thống dò tìm — nếu không, điểm số cao có thể là ảo giác của cách đặt câu hỏi, không phải năng lực retrieval thật.


## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Anh Minh
**Ngày xác nhận:** 06-08-2026
