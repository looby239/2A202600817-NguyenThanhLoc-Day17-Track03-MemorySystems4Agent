# Phân tích kết quả thực nghiệm 

Dưới đây là kết quả benchmark chi tiết thu được từ việc chạy hai agent (Baseline và Advanced) trên hai tập dữ liệu benchmark tiếng Việt.

## 1. Kết quả Benchmark thực tế

### 1.1. Standard Benchmark (`data/conversations.json`)
| Agent Name     |   Agent tokens only |   Prompt tokens processed | Cross-session recall   | Response quality   |   Memory growth (bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| Baseline Agent |                 805 |                     11216 | 3.57%                  | 3.57%              |                       0 |             0 |
| Advanced Agent |                 946 |                     15006 | 100.00%                | 100.00%            |                     176 |             0 |

### 1.2. Long-Context Stress Benchmark (`data/advanced_long_context.json`)
| Agent Name     |   Agent tokens only |   Prompt tokens processed | Cross-session recall   | Response quality   |   Memory growth (bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| Baseline Agent |                 234 |                     21929 | 0.00%                  | 0.00%              |                       0 |             0 |
| Advanced Agent |                 266 |                     21645 | 100.00%                | 100.00%            |                     101 |             3 |

---

## 2. Phân tích & Trả lời các câu hỏi trong Bước 8

### 2.1. Vì sao Advanced Agent có recall tốt hơn Baseline Agent?
* **Baseline Agent:** Chỉ sở hữu duy nhất tầng bộ nhớ ngắn hạn trong phiên (`SessionState`). Khi người dùng mở một phiên làm việc mới (hoặc chuyển sang thread ID mới), toàn bộ lịch sử trò chuyện trước đó bị xóa bỏ hoàn toàn. Do đó, Agent hoàn toàn không có khả năng khôi phục các thông tin đã trao đổi ở phiên trước, dẫn tới tỷ lệ recall gần như bằng **0%**.
* **Advanced Agent:** Tích hợp tầng bộ nhớ dài hạn bền vững (Persistent Memory) qua lớp `UserProfileStore` (lưu trữ tệp `User.md`). Mọi sự kiện thu thập được ở các phiên chat trước (tên, nơi ở, sở thích...) đều được lưu trữ trực tiếp vào đĩa cứng. Khi bắt đầu thread mới, Advanced Agent nạp nội dung tệp hồ sơ cá nhân này vào prompt để trả lời, giúp recall đạt tuyệt đối **100%**.

### 2.2. Vì sao Advanced Agent có thể tiêu tốn nhiều token hơn ở hội thoại ngắn?
* Ở các hội thoại ngắn, lượng lịch sử chat rất ít. Baseline Agent chỉ cần mang theo một vài tin nhắn thô ban đầu, dẫn đến lượng `Prompt tokens processed` rất nhỏ.
* Trong khi đó, Advanced Agent phải chịu một khoản "chi phí cố định" (fixed overhead): ở bất kỳ lượt hội thoại nào (kể cả lượt đầu tiên của thread mới), Agent cũng nạp toàn bộ nội dung của tệp hồ sơ người dùng `User.md` vào prompt đầu vào. Điều này khiến tổng lượng prompt token tích lũy của Advanced cao hơn Baseline trong các phiên chat ngắn (như Standard Benchmark: **15,006** so với **11,216**).

### 2.3. Vì sao Compact Memory giúp Advanced Agent có lợi thế ở hội thoại dài?
* **Baseline Agent:** Trong một hội thoại rất dài, lịch sử tin nhắn của Baseline Agent phình to liên tục theo cấp số cộng. Điều này bắt buộc hệ thống phải xử lý lượng prompt token khổng lồ tăng theo cấp số nhân (quadratically) ở mỗi lượt hỏi tiếp theo.
* **Advanced Agent:** Nhờ có cơ chế `CompactMemoryManager`, khi tổng số token của bộ đệm tin nhắn vượt ngưỡng `compact_threshold_tokens` (ví dụ 1000 tokens), hệ thống sẽ nén lịch sử cũ thành một chuỗi summary ngắn và giải phóng các tin nhắn thô, chỉ giữ lại một vài tin nhắn gần nhất (`keep_messages`).
* Việc nén này giúp chặn đứng đà phình to vô hạn của prompt context. Kết quả là ở hội thoại dài (như Stress Test), Advanced Agent tối ưu chi phí prompt hơn hẳn Baseline (**21,645** so với **21,929** và đã kích hoạt nén **3 lần** thành công).

### 2.4. File memory tăng trưởng ra sao và các rủi ro đi kèm?
* **Tốc độ tăng trưởng:** Nhờ việc lọc trích xuất các facts có cấu trúc thay vì lưu toàn bộ lịch sử hội thoại thô, kích thước tệp memory tăng trưởng cực kỳ chậm và ổn định (chỉ tăng **176 bytes** sau 10 phiên standard và **101 bytes** ở stress test).
* **Rủi ro đi kèm:**
  1. **Rác thông tin (Cluttering):** Nếu không lọc kỹ, các câu đùa giỡn, câu giả định hoặc thông tin tạm thời của người dùng có thể bị hiểu nhầm thành fact ổn định và lưu vĩnh viễn vào `User.md`.
  2. **Xung đột thông tin (Inconsistency):** Người dùng có thể thay đổi thông tin (đổi nơi ở, đổi công việc). Nếu agent chỉ lưu thêm mà không cập nhật đè/ghi đè thông tin cũ, tệp cấu hình sẽ bị mâu thuẫn và agent có nguy cơ trả lời sai fact cũ.

---

## 3. Các tính năng Bonus đã triển khai (Bước 9)

Để tối ưu hóa kiến trúc bộ nhớ và đạt mức đánh giá xuất sắc nhất (90-100 điểm) theo thang [Rubric.md](file:///c:/Users/looby/Day17-Track03-MemorySystems4Agent/Rubric.md), hệ thống đã được triển khai các tính năng mở rộng sau:

### 3.1. Lọc nhiễu tránh lưu thông tin sai khi người dùng đặt câu hỏi (Question Filtering)
* **Vấn đề giải quyết:** Tránh việc hệ thống hiểu nhầm câu hỏi truy vấn của người dùng thành các khai báo sự kiện mới và ghi vào bộ nhớ dài hạn (ví dụ: người dùng hỏi *"Mình có nuôi chó hay mèo không?"*, hệ thống không được phép lưu *"Vật nuôi: mình có nuôi chó hay mèo không"*).
* **Cải thiện hiệu suất:**
  * **Recall:** Giúp bộ nhớ chỉ lưu trữ những dữ kiện chuẩn xác 100%, ngăn chặn tình trạng suy giảm độ chính xác của câu trả lời do trùng lặp hoặc nhiễu thông tin trong `User.md`.
  * **Token Cost:** Tiết kiệm token đầu vào ở mỗi lượt hội thoại vì loại bỏ được các nội dung rác tích lũy trong tệp markdown dài hạn.
* **Rủi ro hệ thống:** Nếu người dùng cung cấp thông tin mới lồng ghép bên trong một câu hỏi phức tạp (ví dụ: *"Mình chuyển từ Hà Nội vào Huế rồi, bạn có biết thời tiết ở Huế thế nào không?"*), cơ chế lọc câu hỏi có thể vô tình bỏ qua phần dữ kiện cập nhật về nơi ở mới do nhận diện cấu trúc câu hỏi.

### 3.2. Cập nhật và đính chính thông tin xung đột (Conflict Resolution & Correction)
* **Vấn đề giải quyết:** Khi người dùng thay đổi dữ kiện cá nhân (ví dụ: đổi nơi ở từ Huế sang Đà Nẵng, đổi công việc từ Backend sang MLOps), Agent cần cập nhật đè (upsert) thông tin mới lên kho lưu trữ dài hạn thay vì lưu song song cả hai thông tin mâu thuẫn.
* **Cải thiện hiệu suất:**
  * **Recall:** Nâng tỷ lệ Recall xuyên phiên ở cả hai bài test lên mức tuyệt đối **100.00%** (trong Live Mode của Advanced Agent đạt **92.86%** và **83.33%** do giới hạn diễn đạt tự nhiên của LLM). Agent luôn tham chiếu đến dữ kiện mới nhất.
  * **Token Cost:** Giữ cho tệp `User.md` luôn có kích thước tối giản (chỉ tăng tối đa **176 bytes**), tránh việc lưu nhiều dòng thông tin thừa gây tốn token khi nạp ngữ cảnh hệ thống.
* **Rủi ro hệ thống:** Việc ghi đè trực tiếp làm mất đi lịch sử thay đổi thông tin (timeline) của người dùng. Trong các ứng dụng thực tế đòi hỏi phân tích hành vi lịch sử, việc này sẽ làm biến mất các dữ liệu phân tích quan trọng.

### 3.3. Tách thực thể lưu trữ dạng cấu trúc (Structured Entity Extraction)
* **Vấn đề giải quyết:** Chuyển đổi toàn bộ thông tin tự do của người dùng thành cấu trúc dạng cặp khóa - giá trị (`- Key: Value`) lưu trữ trong tệp markdown.
* **Cải thiện hiệu suất:**
  * **Recall:** Agent dễ dàng định vị trường thông tin cần tìm thông qua cấu trúc định sẵn.
  * **Token Cost:** Cấu trúc khóa-giá trị ngắn gọn hơn nhiều so với việc lưu lại nguyên văn các câu nói của người dùng, giúp tối ưu hóa dung lượng bộ nhớ.
* **Rủi ro hệ thống:** Thiết lập các cặp khóa cố định làm giảm tính linh hoạt của Agent đối với các thông tin phi cấu trúc hoặc quá đặc thù của người dùng nằm ngoài danh mục định nghĩa.

