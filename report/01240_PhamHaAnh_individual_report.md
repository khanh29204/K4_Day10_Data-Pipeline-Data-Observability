# BÁO CÁO CÁ NHÂN (INDIVIDUAL REPORT) - VAI TRÒ 3
**Thành viên thực hiện**: Phạm Hà Anh  
**Vai trò phụ trách**: Vai trò 3 - Phụ trách RAG & Agent (Nhóm 4 người)  
**Phạm vi phụ trách**: MiniLM, Chroma, search, lookup  
**Thư mục làm việc chính**: `src/retrieval/` (bao gồm `embeddings.py`, `index.py`, `agent.py`, `qa.py`, `llm.py`), `data/embeddings/`, `data/chroma/`

---

## 1. Nhiệm vụ và Các phần việc đã hoàn thành

Trong đợt làm việc này, tôi chịu trách nhiệm chính về mặt công nghệ tìm kiếm ngữ nghĩa, cơ sở dữ liệu vector và tích hợp mô hình ngôn ngữ lớn (LLM) cho Agent. Dưới đây là các phần việc tôi đã hoàn thành:

### A. Tích hợp Mô hình Embedding MiniLM (`embeddings.py`)
- Sử dụng mô hình nguồn mở **`sentence-transformers/all-MiniLM-L6-v2`** để chuyển đổi toàn bộ trường dữ liệu văn bản `text_for_embedding` (bao gồm tiêu đề, tác giả và tóm tắt bài báo) thành các vector biểu diễn ngữ nghĩa 384 chiều.
- Cấu hình và tối ưu hóa bộ nhớ đệm (`lru_cache`) cho quá trình sinh vector nhằm giảm thiểu thời gian xử lý khi hệ thống gọi trùng lặp các văn bản giống nhau.

### B. Xây dựng và Quản trị Cơ sở dữ liệu Vector ChromaDB (`index.py`)
- Triển khai lớp **`LocalEmbeddingIndex`** giúp quản trị toàn bộ hoạt động lưu trữ và truy vấn trên cơ sở dữ liệu vector ChromaDB (`chromadb.PersistentClient`) lưu cục bộ tại đường dẫn vật lý [`data/chroma/`](file:///d:/Vin_AI/K4_Day10_Data-Pipeline-Data-Observability/data/chroma).
- Thiết lập cấu hình tính toán độ tương đồng dựa trên **Cosine Similarity** (`space: cosine`) để đảm bảo chất lượng so sánh ngữ nghĩa tối ưu nhất.
- Phát triển tính năng xuất file **Manifest định dạng JSON** chứa cấu trúc tài liệu và metadata của bài báo. Điều này giúp hệ thống chỉ cần sinh vector một lần duy nhất lúc tạo (`build`) và dễ dàng nạp lại cơ sở dữ liệu (`load`) ở các phiên chạy sau mà không mất công sinh lại embedding.
- Tạo lập độc lập và quản lý riêng biệt **3 collection vector** đại diện cho 3 trạng thái dữ liệu của toàn bộ dự án nhằm ngăn chặn việc ghi đè hay làm bẩn tệp baseline:
  1. `papers-baseline`
  2. `papers-corrupted`
  3. `papers-repaired`

### C. Triển khai Logic Search & Lookup (`index.py`, `qa.py`)
- **Semantic Search (Tìm kiếm ngữ nghĩa)**: Hoàn thiện hàm `search()` chuyển đổi câu hỏi người dùng thành vector, truy vấn vào ChromaDB và lấy ra danh sách các bài báo có độ tương đồng ngữ nghĩa cao nhất.
- **Exact Lookup (Truy xuất chính xác)**: Phát triển hàm `lookup()`. Khi người dùng truy vấn theo mã định danh cụ thể `paper_id` (DOI) hoặc tên tiêu đề chính xác, thuật toán sẽ lấy trực tiếp bản ghi từ từ điển ánh xạ (hash map) cục bộ. Việc này giúp bỏ qua bước tính toán vector và giảm đáng kể độ trễ phản hồi của hệ thống.

### D. Đóng gói Agent Tools & Tránh xung đột Môi trường (`agent.py`, `llm.py`)
- **Xây dựng LangChain Tools**: Chuyển đổi hai hàm truy xuất trên thành các langchain tools (`@tool`):
  - `semantic_search_papers`
  - `lookup_paper`
- **Tích hợp Agent**: Đóng gói các công cụ này vào LangChain Agent nhằm hỗ trợ Agent tự động phân tích câu hỏi của người dùng và gọi công cụ phù hợp để tìm ngữ cảnh chính xác từ Vector DB trước khi trả lời, triệt tiêu hiện tượng ảo tưởng (hallucination).
- **Khắc phục lỗi Import động (`llm.py`)**: Tối ưu hóa hàm khởi tạo LLM bằng cách đưa các thư viện langchain provider (`langchain_google_genai`, `langchain_anthropic`,...) vào trong điều kiện import động thay vì import ở đầu file. Điều này giúp hệ thống khởi chạy bình thường trên môi trường ảo `bot_env` mà không bị lỗi crash hệ thống do thiếu các thư viện LLM không sử dụng.

---

## 2. Kết quả Đóng góp cho Dự án (Project Deliverables & Impact)

Những đóng góp của tôi trong vai trò phụ trách RAG & Agent đã đem lại hiệu quả thực tế rõ rệt:

1. **Khởi tạo thành công 3 cơ sở dữ liệu vector và Manifest độc lập**:
   *   Baseline Manifest: [`data/embeddings/papers_embeddings.json`](file:///d:/Vin_AI/K4_Day10_Data-Pipeline-Data-Observability/data/embeddings/papers_embeddings.json)
   *   Corrupted Manifest: [`data/embeddings/papers_embeddings_corrupted.json`](file:///d:/Vin_AI/K4_Day10_Data-Pipeline-Data-Observability/data/embeddings/papers_embeddings_corrupted.json)
   *   Repaired Manifest: [`data/embeddings/papers_embeddings_repaired.json`](file:///d:/Vin_AI/K4_Day10_Data-Pipeline-Data-Observability/data/embeddings/papers_embeddings_repaired.json)
2. **Chứng minh tác động thực tế của dữ liệu lên khả năng tìm kiếm**:
   *   Khi chạy thử nghiệm với cùng một truy vấn baseline trên cả 3 index, tôi đã giúp nhóm đưa ra bằng chứng định lượng rõ ràng:
     - Trên index **Baseline**, tìm thấy đúng bài viết mẫu với điểm số Cosine tối đa `1.0000`.
     - Trên index **Corrupted**, hệ thống bị mất dấu bài viết và phải trả về bài báo khác có điểm tương đồng rất thấp (`0.5109`).
     - Trên index **Repaired**, điểm số và kết quả tìm kiếm ngữ nghĩa phục hồi hoàn hảo về mức `1.0000`.
3. **Agent Tools hoạt động chính xác**: Các bài kiểm tra Agent Tools (`lookup_paper` và `semantic_search_papers`) chạy trên dữ liệu sửa lỗi (`papers-repaired`) đều trích xuất chính xác tiêu đề, nội dung tóm tắt đầy đủ phục vụ cho câu trả lời của Agent.

---
*Hà Nội, ngày 06 tháng 08 năm 2026*  
**Người làm báo cáo**  
*(Đã ký)*  
**Phạm Hà Anh**
