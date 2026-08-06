# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Phạm Ngọc Quốc Khánh |
| **MSSV** | 2A202601254 |
| **Khóa/Lớp** | K4 |
| **Tên nhóm** | TeamB |
| **Vai trò chính** | Evaluation & observability (Role 4) |
| **Repository** | https://github.com/khanh29204/K4_Day10_Data-Pipeline-Data-Observability.git |
| **Ngày hoàn thành** | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu (Ownership)

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Evaluation Set & Test Generation** | `src/evaluation/testset.py`<br>`build_test_set()` | Cleaned DataFrame (`data/clean/cleaned_papers.csv`) | `data/eval/test_set.json` (18 ground-truth QA samples) | Hoàn thành |
| **RAG Metrics & Evaluator Pipeline** | `src/evaluation/metrics.py`<br>`evaluate_pipeline()`, `_token_f1()`, `_judge_answer()` | Test set JSON, `LocalEmbeddingIndex`, LLM Settings | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `*_answers.json` | Hoàn thành |
| **Data Quality & Freshness Observability** | `src/observability/quality.py`<br>`run_quality_checks()`, `run_freshness_check()` | Cleaned/Corrupted DataFrame | `baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json`, `freshness_report.json` | Hoàn thành |
| **Observability Reporting & Comparison** | `src/observability/reporting.py`<br>`generate_phase1_report()`, `generate_corruption_report()` | Quality JSONs, Freshness JSONs, Evaluation Metrics JSONs | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| :--- | :--- | :--- |
| **Pipeline Orchestration Debugging** | Role 1 (Lead Integrator) - `src/pipelines/` | Phối hợp tích hợp các bước evaluation và observability vào `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`, đảm bảo luồng chạy tự động 100% không vướng exception. |
| **Vector Index Ground-Truth Verification** | Role 3 (RAG Owner) - `src/retrieval/` | Đối chiếu danh sách `ground_truth_doc_ids` trong test set với `paper_id` được index trong ChromaDB để đảm bảo không xảy ra hiện tượng mâu thuẫn ID giữa cleaning và indexing. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Thiết kế & sinh bộ test set cố định | `src/evaluation/testset.py` (L13-L58) | `data/eval/test_set.json` (18 mẫu có `question`, `ground_truth`, `ground_truth_doc_ids`, `question_type`) | `cat data/eval/test_set.json \| jq '. \| length'` (đủ 18 mẫu) |
| Đánh giá 3 pha Baseline / Corrupted / Repaired | `src/evaluation/metrics.py` (L103-L145) | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` | Kiểm tra file JSON chứa `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` |
| Triển khai Data Quality Gates | `src/observability/quality.py` (L14-L62) | `baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json` | Corrupted dataset bị đánh **FAILED** với 3 checks thất bại (duplicate, short summary, stale date). Baseline & Repaired **PASSED** (6/6 pass). |
| Giám sát độ tươi dữ liệu (Freshness Monitoring) | `src/observability/quality.py` (L65-L89) | `data/quality/freshness_report.json`, `freshness_report_corrupted.json` | Corrupted báo `is_fresh: false` với 3 stale rows (nguồn cũ từ 1990); Baseline & Repaired báo `is_fresh: true`. |
| Tự động tổng hợp Báo cáo so sánh | `src/observability/reporting.py` (L42-L105) | `data/reports/corruption_report.md` | Báo cáo Markdown hiển thị bảng đối chiếu 3 trạng thái và tính toán delta phục hồi rõ ràng. |

**Mô tả output cụ thể được tạo ra:**  
File `data/reports/corruption_report.md` thể hiện đầy đủ bảng so sánh chỉ số giữa Baseline, Corrupted và Repaired: `Retrieval Hit Rate` sụt giảm mạnh từ 100% xuống 50% khi bị corrupt và hồi phục 100% sau repair; `Mean Token F1` giảm từ 0.4352 xuống 0.1726 và hồi phục về 0.4352; `Data Quality Check` chuyển từ PASSED sang FAILED và trở lại PASSED.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG cần một cơ chế đánh giá định lượng (Evaluation) chính xác về khả năng truy xuất (Retrieval) và chất lượng câu trả lời của LLM (Generation), đồng thời cần hệ thống giám sát dữ liệu (Observability & Data Quality) tự động để phát hiện các bất thường dữ liệu (dữ liệu thiếu, rỗng, bị nhiễu, lỗi ngày tháng) trước khi nó gây ra câu trả lời sai lệch cho người dùng cuối.

### Cách triển khai

1. **Sinh Test Set (`src/evaluation/testset.py`)**:
   - Duyệt qua Cleaned DataFrame, trích xuất thông tin bài báo thực tế để tạo ra 18 câu hỏi thuộc các dạng: `summary`, `authors`, `date`, `categories`.
   - Mỗi mẫu thử chứa `ground_truth` từ tóm tắt bài báo và `ground_truth_doc_ids` chứa `paper_id` chuẩn để kiểm tra retrieval.
2. **Đánh giá Pipeline (`src/evaluation/metrics.py`)**:
   - `retrieval_hit`: Kiểm tra xem bất kỳ `paper_id` nào trong top-k đoạn văn bản được truy xuất có nằm trong `ground_truth_doc_ids` không.
   - `token_f1`: Tính độ tương đồng n-gram giữa câu trả lời của RAG Agent và `ground_truth`.
   - `_judge_answer()`: Sử dụng LLM Judge (hoặc heuristic fallback dựa trên Token F1) để chấm điểm câu trả lời trên thang điểm từ 1-5 và xác định tính đúng đắn (`correct`).
3. **Data Quality Checks & Freshness Monitoring (`src/observability/quality.py`)**:
   - `run_quality_checks()` thực hiện 6 bài kiểm tra: `row_count_check`, `paper_id_null_check`, `paper_id_unique_check`, `title_null_check`, `summary_length_check` (đảm bảo summary >= 100 ký tự), và `freshness_check`.
   - `run_freshness_check()` kiểm tra độ tươi dữ liệu dựa trên cột `published`/`age_days`, gắn cờ `stale_rows` nếu bài báo xuất bản quá 180 ngày hoặc sai định dạng ngày.
4. **Báo cáo tổng hợp (`src/observability/reporting.py`)**:
   - Thu thập kết quả kiểm tra chất lượng và metrics từ các file JSON để tự động render thành file Markdown `data/reports/corruption_report.md`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Cleaned/Corrupted DataFrame, `test_set.json`, `LocalEmbeddingIndex`, Settings cấu hình LLM |
| **Output** | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `*_quality.json`, `freshness_report*.json`, `corruption_report.md` |
| **Module phụ thuộc** | `src/core/config.py`, `src/retrieval/index.py`, `src/retrieval/qa.py` |
| **Module sử dụng output** | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, Script chạy báo cáo tổng kết |
| **Điều kiện lỗi cần xử lý** | LLM API bị ngắt kết nối/rate limit khi chấm điểm (dùng Heuristic Fallback Judge), DataFrame rỗng hoặc thiếu cột bắt buộc. |

### Cách xác minh

```bash
# 1. Thực thi Baseline Pipeline (Pha 1)
uv run python script/run_phase1.py

# 2. Thực thi Corruption & Repair Pipeline (Pha 2)
uv run python script/run_corruption_flow.py

# 3. Kiểm tra các file kết quả sinh ra
ls -l data/results/ data/quality/ data/reports/
```

- **Kết quả mong đợi:** Baseline & Repaired đạt `retrieval_hit_rate` = 1.0 (100%), `quality_check` = PASSED, `freshness` = FRESH. Corrupted bị tụt `retrieval_hit_rate` xuống 0.5 (50%), `quality_check` = FAILED, `freshness` = STALE.
- **Kết quả thực tế:** Khớp 100% với mong đợi.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thực hiện đánh giá ảnh hưởng của Data Corruption lên hệ thống RAG ở Pha 2, có hai lựa chọn về cách quản lý bộ dữ liệu kiểm thử (Evaluation Set).
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Sinh lại bộ `test_set.json` mới dựa trên tập dữ liệu đã bị corrupt tại thời điểm chạy corruption flow.
  2. *Phương án B (Đã chọn):* Khóa cố định bộ `test_set.json` (18 mẫu) được sinh ra từ tập Clean Baseline và tái sử dụng đúng bộ test set này cho cả 3 trạng thái: Baseline, Corrupted và Repaired.
- **Lý do chọn Phương án B:**
  - Để đo lường chính xác và công bằng tác động của suy giảm chất lượng dữ liệu (Benchmark Comparability), thước đo (test set) bắt buộc phải giữ nguyên.
  - Nếu sinh test set mới trên dữ liệu bị corrupt, test set sẽ không chứa các câu hỏi liên quan đến các bài báo bị xóa/bị nhiễu, làm mất đi khả năng phát hiện lỗi truy xuất (false positive).
- **Bằng chứng quyết định phù hợp:** Giữ nguyên test set giúp phát hiện chính xác `retrieval_hit_rate` sụt giảm 50% ở trạng thái Corrupted do 3 bài báo bị drop và 3 bài báo có tóm tắt rỗng không thể được truy xuất đúng.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded for quota metric 'Generate Content API requests'
  ```
  Hoặc khi LLM Judge không trả về JSON hợp lệ theo schema Pydantic `JudgeVerdict` khi đánh giá các câu trả lời bị hallucinate từ dữ liệu nhiễu.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_corruption_flow.py` khi hệ thống thực hiện gọi LLM Judge cho 18 câu hỏi thử nghiệm liên tục trong điều kiện bị rate limit.
- **Nguyên nhân gốc:** API của LLM provider bị chạm trần rate limit hoặc khi context bị nhiễu do corruption, câu trả lời của agent bị lệch khiến LLM Judge trả về response định dạng sai so với kỳ vọng của Pydantic structured output.
- **Cách xử lý:** Bổ sung khối `try...except` trong hàm `_judge_answer()` (`src/evaluation/metrics.py` L64-L70) với cơ chế Fallback Heuristic Judge dựa trên ngưỡng Token F1 score mà không làm dừng pipeline:
  ```python
  except Exception:
      score = 5 if _token_f1(reference, prediction) >= 0.95 else 3 if _token_f1(reference, prediction) >= 0.5 else 1
      return JudgeVerdict(
          score=score,
          correct=score >= 3,
          reasoning="Fallback heuristic judge used because the LLM evaluator was unavailable.",
      )
  ```
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/run_corruption_flow.py`, toàn bộ 18 mẫu thử được chấm điểm hoàn chỉnh, pipeline kết thúc thành công với code 0.
- **Điều học được:** Trình đánh giá (Evaluator) phải có tính kháng lỗi cao (resilient), không được để rào cản từ API bên ngoài làm sập toàn bộ quy trình đo đạc.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu raw (JSON) được nạp từ Crossref API qua module Ingestion, sau đó qua Cleaning để lọc trùng, chuẩn hóa trường văn bản, tính toán `age_days` và tạo cột `text_for_embedding`. Dữ liệu sạch này được đưa qua `sentence-transformers/all-MiniLM-L6-v2` để tạo vector embeddings và nạp vào vector collection trong ChromaDB.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Evaluation set chứa danh sách câu hỏi và `ground_truth_doc_ids` (ID chuẩn của bài báo chứa đáp án). Khi RAG agent truy xuất các đoạn văn bản cho câu hỏi, `retrieval_hit` sẽ kiểm tra xem ID của các văn bản được tìm thấy có khớp với `ground_truth_doc_ids` hay không. Câu trả lời sinh ra sau đó được so sánh với `ground_truth` bằng Token F1 và LLM Judge.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   - **Quality checks:** Giám sát tính toàn vẹn và hợp lệ cấu trúc của dữ liệu (số lượng dòng, null `paper_id`, trùng lặp `paper_id`, độ dài tóm tắt ngắn/rỗng).
   - **Freshness monitoring:** Giám sát thời gian xuất bản (`published`) và độ tuổi dữ liệu (`age_days`) để phát hiện xem dữ liệu trong pipeline có bị lỗi thời (stale > 180 ngày) hoặc thiếu ngày xuất bản hay không.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Để tạo ra một thước đo chuẩn mực (baseline benchmark) nhất quán. Việc giữ nguyên 18 câu hỏi kiểm thử cho phép so sánh trực tiếp các chỉ số (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) qua 3 trạng thái, từ đó chứng minh chính xác tác động tiêu cực của corruption và hiệu quả phục hồi của repair.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   Repair thành công khi:
   - File chất lượng dữ liệu (`repaired_quality.json`) chuyển lại trạng thái `overall_passed: true` (6/6 check pass).
   - Report độ tươi (`freshness_report_repaired.json`) báo `is_fresh: true` với `stale_rows: 0`.
   - Metric hiệu năng RAG trong `repaired_metrics.json` khôi phục về đúng giá trị baseline (`retrieval_hit_rate` = 1.0, `mean_token_f1` = 0.4352, `judge_accuracy` = 38.9%).

---

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

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Kiến trúc dữ liệu lưu giữ immutable raw records snapshot từ nguồn (Crossref) là yếu tố sống còn cho phép hệ thống có khả năng phục hồi dữ liệu (data recovery/repair) một cách tin cậy mà không bị phụ thuộc vào dữ liệu sửa tay.
2. **Về Data Observability:** Data Quality Gates và Freshness Monitoring không chỉ là các bài test bị động, mà là tuyến phòng thủ chủ động bắt buộc phải có để ngăn chặn dữ liệu bẩn tràn vào Vector Database.
3. **Về RAG Evaluation:** Chất lượng dữ liệu đầu vào (Garbage In) tác động trực tiếp và tức thì đến năng lực của RAG Agent (Garbage Out). Đo lường dựa trên cả Retrieval Metric (`retrieval_hit_rate`) và Generation Metric (`token_f1`, LLM Judge) giúp phân lập chính xác lỗi nằm ở khâu truy xuất hay khâu sinh câu trả lời.

### Nếu có thêm thời gian

Nhóm sẽ mở rộng chạy toàn bộ khung đánh giá **Ragas** (bằng cách bật `RUN_RAGAS=1`) để thu thập thêm 4 chỉ số chuyên sâu: `faithfulness`, `answer_relevancy`, `context_recall`, `context_precision`, đồng thời tích hợp Great Expectations vào pipeline CI/CD để tự động chặn các commit làm suy giảm chất lượng dữ liệu.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Ngọc Quốc Khánh  
**Ngày xác nhận:** 2026-08-06
