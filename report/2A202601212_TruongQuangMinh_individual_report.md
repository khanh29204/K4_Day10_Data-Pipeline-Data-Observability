# Báo cáo cá nhân — Điều phối pipeline

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | `Trương Quang Minh` |
| MSSV | `2A202601212` |
| Khóa/Lớp | K4 |
| Tên nhóm | `TeamB` |
| Vai trò chính | Điều phối pipeline và tích hợp các module |
| Repository | `https://github.com/khanh29204/K4_Day10_Data-Pipeline-Data-Observability` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Orchestration baseline | `src/pipelines/phase1.py::main`, `script/run_phase1.py` | Raw Crossref records và settings | Clean data, embedding/index, evaluation, quality/freshness report | Hoàn thành |
| Data contract và schema integration | `data/raw/crossref_records.schema.json`, `data/clean/papers_clean.schema.json`, `report/group_report.md` | `crossref_records.json`, `papers_clean.json` | Raw/Clean schema và mapping giữa các module | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py::main`, `src/ingestion/corruption.py` | Baseline clean dataset, raw snapshot và evaluation set | Corrupted/repaired datasets, metrics, quality reports và comparison report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Rà soát contract giữa ingestion, cleaning, retrieval và observability | `src/ingestion`, `src/retrieval`, `src/observability` | Đồng bộ mapping raw → clean và các trường derived |
| Kiểm tra kết quả trước/sau corruption | Nhóm 4 người | Xác nhận cùng 18 evaluation samples được dùng cho cả ba trạng thái |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Điều phối baseline end-to-end | `src/pipelines/phase1.py`, `data/reports/phase1_report.md` | 24 raw records → 24 clean records → ChromaDB → 18 evaluation samples | `data/results/baseline_metrics.json` |
| Điều phối corruption flow | `src/pipelines/corruption_flow.py`, `src/ingestion/corruption.py` | Tạo 6 nhóm lỗi, giữ 24 dòng sau khi thêm duplicate rows | `data/results/corruption_log.json` |
| Điều phối repair và re-evaluation | `src/pipelines/corruption_flow.py` | Rebuild từ raw snapshot, quality/freshness phục hồi, metrics khớp baseline | `data/results/repaired_metrics.json`, `data/quality/repaired_quality.json` |
| Tổng hợp so sánh | `src/observability/reporting.py` | Comparison report baseline/corrupted/repaired | `data/reports/corruption_report.md` |
| Đồng bộ data contract | `data/raw/*.schema.json`, `data/clean/*.schema.json`, `report/group_report.md` | Schema raw 11 trường và clean contract 8 trường được mô tả | JSON Schema và báo cáo nhóm |

Output quan trọng nhất là chuỗi so sánh hoàn chỉnh: baseline và repaired đều có retrieval hit rate
100%, trong khi corrupted giảm xuống 50%; quality và freshness cũng chuyển từ `PASS/FRESH` sang
`FAIL/STALE` rồi phục hồi về `PASS/FRESH`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline gồm nhiều module phụ thuộc theo thứ tự. Raw snapshot phải ổn định trước khi cleaning, clean
dataset phải được embed trước evaluation, còn corruption và repair phải dùng cùng test set để có thể
đo tác động của chất lượng dữ liệu một cách công bằng. Vai trò điều phối là kết nối các bước này và
kiểm tra artifact sau từng phase.

### Cách triển khai

Baseline được điều phối theo chuỗi:

1. Đọc raw Crossref snapshot hoặc fetch source khi cần.
2. Làm sạch records và ghi `papers_clean.csv/json`.
3. Tạo embedding và collection ChromaDB baseline.
4. Tạo hoặc tái sử dụng `data/eval/test_set.json` với 18 câu hỏi.
5. Chạy quality checks, freshness report và baseline evaluation.
6. Tạo corrupted DataFrame bằng sáu loại corruption: drop record, blank summary, inject noise, truncate title, stale date và duplicate rows.
7. Rebuild corrupted index, đánh giá lại trên cùng test set và ghi quality/freshness.
8. Đọc lại raw snapshot, chạy cleaning để tạo repaired dataset, rebuild index và đánh giá lại.
9. Sinh comparison report cho ba trạng thái.

Raw schema mô tả 11 trường trong `crossref_records.json`. Clean contract mục tiêu gồm `paper_id`,
`title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days` và
`text_for_embedding`. Trong runtime hiện tại, clean artifact còn giữ thêm metadata columns phục vụ
retrieval/traceability; phần schema tài liệu mô tả contract tối thiểu cho downstream modules.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/raw/crossref_records.json` gồm 24 records; `data/eval/test_set.json` gồm 18 samples; settings trong `src/core/config.py` |
| Output baseline | `papers_clean.json`, baseline embeddings/index, `baseline_metrics.json`, `baseline_quality.json`, `freshness_report.json` |
| Output corrupted | `papers_clean_corrupted.json`, corrupted embeddings/index, `corrupted_metrics.json`, `corrupted_quality.json`, `freshness_report_corrupted.json` |
| Output repaired | `papers_clean_repaired.json`, repaired embeddings/index, `repaired_metrics.json`, `repaired_quality.json`, `freshness_report_repaired.json` |
| Module sử dụng output | `retrieval.index` dùng clean text/index; `evaluation.metrics` dùng index và test set; observability dùng clean DataFrame; reporting dùng metrics và quality reports |
| Điều kiện lỗi cần xử lý | Missing raw/baseline artifact, duplicate IDs, summary/title không hợp lệ, stale date, corrupted rows và mismatch giữa schema tài liệu với runtime columns |

### Cách xác minh

```powershell
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

- **Kết quả mong đợi:** Tạo đủ artifact baseline, corrupted và repaired; comparison report có số liệu cho cả ba trạng thái.
- **Kết quả thực tế:** Flow hoàn thành; baseline/corrupted/repaired đều có 18 samples và metrics tương ứng.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/*_metrics.json`, `data/quality/*`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần tách ảnh hưởng của corruption khỏi ảnh hưởng do nguồn dữ liệu hoặc evaluation set thay đổi.
- **Các phương án đã cân nhắc:** (1) fetch Crossref và tạo test set mới ở mỗi phase; (2) giữ raw snapshot bất biến và dùng chung test set.
- **Phương án đã chọn:** Dùng `data/raw/crossref_records.json` làm source of truth, giữ nguyên `data/eval/test_set.json` cho baseline/corrupted/repaired.
- **Lý do:** Tăng reproducibility, tránh API thay đổi giữa các lần chạy và tránh ground truth bị sinh từ dữ liệu corrupted.
- **Bằng chứng quyết định phù hợp:** Cả ba metrics đều có `samples: 18`; repaired metrics khôi phục đúng các giá trị baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement corruption flow pipeline.`
- **Lệnh hoặc bước tái hiện:** `python script/run_corruption_flow.py` trước khi hoàn thiện implementation.
- **Nguyên nhân gốc:** `corruption_flow.py` và `corruption.py` ban đầu chỉ có pseudocode, chưa tạo corrupted dataset, chưa re-index và chưa re-evaluate.
- **Cách xử lý:** Implement `corrupt_clean_dataframe` để ghi corruption log, implement orchestration gồm corruption → evaluation → quality/freshness → repair → comparison.
- **Cách xác minh sau khi sửa:** Có đủ `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` và `corruption_report.md`; không còn `NotImplementedError` trong pipeline source.
- **Điều học được:** Một pipeline observability chỉ có giá trị khi corruption được tái tạo có chủ đích và repair được đo trên cùng evaluation protocol.

## 7. Hiểu biết về luồng end-to-end

1. **Từ Crossref đến vector index:** Crossref response được lưu thành raw response/records; cleaning chuẩn hóa metadata, tính `age_days` và tạo `text_for_embedding`; embedding model biến text thành vectors, sau đó ChromaDB lưu vectors cùng metadata và document ID.
2. **Evaluation set và ground truth:** Mỗi sample có `ground_truth_doc_ids`; retrieval hit rate kiểm tra document đúng có nằm trong top-k, còn token F1 và judge metrics đánh giá câu trả lời từ context được retrieve.
3. **Quality checks và freshness:** Quality checks kiểm tra row count, null/duplicate IDs, title, summary và dữ liệu hợp lệ; freshness theo dõi `published`, `age_days`, stale rows và trạng thái fresh/stale.
4. **Dùng cùng test set:** Giữ 18 câu hỏi và ground truth cố định để mọi thay đổi metric đến từ dataset/index bị corruption hoặc repair, không phải do benchmark thay đổi.
5. **Tiêu chí repair thành công:** Repaired data phải được tạo lại từ raw snapshot, quality phải PASS, freshness phải FRESH, index phải được rebuild và metrics phải phục hồi trên cùng test set. Trong run này, repaired metrics khớp baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Corruption làm mất/giảm chất lượng context; repair phục hồi hoàn toàn. |
| `mean_token_f1` | 0.4352 | 0.1726 | 0.4352 | Giảm 0.2626 khi corrupted, phục hồi đúng baseline. |
| `judge_accuracy` | 0.3889 | 0.1667 | 0.3889 | Giảm từ 38.9% xuống 16.7%, sau repair trở lại 38.9%. |
| `mean_judge_score` | 2.4444/5 | 1.6667/5 | 2.4444/5 | Giảm 0.7778 điểm và được phục hồi. |
| Quality checks | PASS | FAIL | PASS | Corrupted có 3 duplicate IDs và 3 summary ngắn. |
| Freshness status | FRESH | STALE | FRESH | Corrupted có 3 stale rows với ngày `1990-01-01`. |

### Kết luận từ số liệu

1. **Data corruption → signal → agent metric:** Sáu corruption được inject trên dataset 24 dòng; quality phát hiện 3 duplicate IDs, 3 summary ngắn và 3 stale rows. Cùng lúc, retrieval hit rate giảm từ 100% xuống 50%, mean token F1 từ 0.4352 xuống 0.1726 và judge accuracy từ 38.9% xuống 16.7%.
2. **Repair action → signal → agent metric:** Repair đọc lại raw snapshot và re-clean/re-index; quality trở lại PASS, freshness trở lại FRESH, retrieval hit rate về 100% và ba answer metrics khớp baseline.

Corruption ảnh hưởng rõ nhất là nhóm làm mất hoặc làm hỏng context retrieval: drop 3 latest records,
blank summary và inject noise. Truncate title, stale dates và duplicate rows đồng thời làm quality
checks fail; tuy nhiên run hiện tại là combined corruption nên không thể tách riêng đóng góp của từng
loại lỗi nếu không chạy ablation riêng.

Kết quả đáng chú ý là repaired metrics khớp baseline hoàn toàn dù corrupted dataset vẫn giữ tổng cộng
24 dòng sau khi thêm duplicate rows. Điều này cho thấy repair từ raw snapshot có thể loại bỏ tác động
của corruption mà không phụ thuộc vào việc sửa thủ công từng dòng corrupted.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Điều phối pipeline cần quản lý cả thứ tự thực thi và data contract giữa ingestion, cleaning, index, evaluation và observability.
2. Quality/freshness signals có thể báo lỗi dữ liệu trước khi chỉ số RAG giảm; trong run này các signal FAIL/STALE đi cùng mức giảm rõ rệt của metrics.
3. Raw snapshot bất biến và test set dùng chung là nền tảng để chứng minh repair thực sự phục hồi chất lượng, thay vì chỉ tạo một kết quả mới khó so sánh.

### Nếu có thêm thời gian

Tách từng loại corruption thành các ablation run để định lượng riêng tác động của missing records,
summary rỗng, noise, title ngắn, stale date và duplicate rows. Đồng thời bổ sung validation runtime
cho clean schema 8 trường và thống nhất ngưỡng summary giữa schema, cleaning và quality checks; đo cải
thiện bằng số lỗi schema, quality pass rate, freshness status và độ lệch metrics so với baseline.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc điều phối và kết quả đã có artifact xác minh.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Các kết luận về baseline/corrupted/repaired đều có metric hoặc report để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này được viết theo vai trò điều phối, không sao chép nguyên văn báo cáo nhóm.

**Họ và tên:** `Truong Quang Minh`  
**Ngày xác nhận:** 2026-08-06
